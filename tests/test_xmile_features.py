"""
Test XMILE/PySD compatible features.
Tests new functions: TIME, STEP, PULSE, RAMP, IF_THEN_ELSE, DELAY, SMOOTH, LOOKUP, etc.
"""
import sys
import math
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.model import Model, Stock, Flow, Variable, Position, TimeSettings, LookupTable
from app.core.equations import (
    safe_eval, EquationError, SimulationContext,
    step_function, pulse_function, ramp_function, if_then_else,
    random_uniform, random_normal, lookup_interp
)
from app.core.simulator import simulate, simulate_euler, simulate_rk4


def test_time_variable():
    """Test that TIME variable is accessible in equations."""
    print("Testing TIME variable...")

    ctx = SimulationContext(time=50.0, dt=0.25)
    result = safe_eval("TIME", {}, ctx)
    assert result == 50.0, f"Expected 50.0, got {result}"

    # Test lowercase
    result = safe_eval("time", {}, ctx)
    assert result == 50.0, f"Expected 50.0 for lowercase, got {result}"

    # Test in expression
    result = safe_eval("TIME * 2 + 1", {}, ctx)
    assert result == 101.0, f"Expected 101.0, got {result}"

    print("  PASS: TIME variable works")


def test_step_function():
    """Test STEP function."""
    print("Testing STEP function...")

    # Before step time
    ctx = SimulationContext(time=5.0, dt=0.25)
    result = safe_eval("STEP(10, 10)", {}, ctx)
    assert result == 0.0, f"Expected 0.0 before step, got {result}"

    # At step time
    ctx = SimulationContext(time=10.0, dt=0.25)
    result = safe_eval("STEP(10, 10)", {}, ctx)
    assert result == 10.0, f"Expected 10.0 at step, got {result}"

    # After step time
    ctx = SimulationContext(time=15.0, dt=0.25)
    result = safe_eval("STEP(10, 10)", {}, ctx)
    assert result == 10.0, f"Expected 10.0 after step, got {result}"

    print("  PASS: STEP function works")


def test_pulse_function():
    """Test PULSE function."""
    print("Testing PULSE function...")

    dt = 0.25

    # Before pulse
    ctx = SimulationContext(time=5.0, dt=dt)
    result = safe_eval("PULSE(1, 10, 0)", {}, ctx)
    assert result == 0.0, f"Expected 0.0 before pulse, got {result}"

    # At pulse time (magnitude/dt for one dt)
    ctx = SimulationContext(time=10.0, dt=dt)
    result = safe_eval("PULSE(1, 10, 0)", {}, ctx)
    assert result == 1.0 / dt, f"Expected {1.0/dt} at pulse, got {result}"

    # After pulse
    ctx = SimulationContext(time=10.5, dt=dt)
    result = safe_eval("PULSE(1, 10, 0)", {}, ctx)
    assert result == 0.0, f"Expected 0.0 after pulse, got {result}"

    print("  PASS: PULSE function works")


def test_ramp_function():
    """Test RAMP function."""
    print("Testing RAMP function...")

    # Before ramp
    ctx = SimulationContext(time=5.0, dt=0.25)
    result = safe_eval("RAMP(2, 10, 0)", {}, ctx)
    assert result == 0.0, f"Expected 0.0 before ramp, got {result}"

    # During ramp (slope * elapsed time)
    ctx = SimulationContext(time=15.0, dt=0.25)
    result = safe_eval("RAMP(2, 10, 0)", {}, ctx)
    assert result == 10.0, f"Expected 10.0 during ramp, got {result}"  # 2 * (15-10) = 10

    # With end time - stops at end
    ctx = SimulationContext(time=25.0, dt=0.25)
    result = safe_eval("RAMP(2, 10, 20)", {}, ctx)
    assert result == 20.0, f"Expected 20.0 after end time, got {result}"  # 2 * (20-10) = 20

    print("  PASS: RAMP function works")


def test_if_then_else():
    """Test IF_THEN_ELSE function."""
    print("Testing IF_THEN_ELSE function...")

    ctx = SimulationContext()

    # True condition
    result = safe_eval("IF_THEN_ELSE(1, 10, 20)", {}, ctx)
    assert result == 10.0, f"Expected 10.0 for true condition, got {result}"

    # False condition
    result = safe_eval("IF_THEN_ELSE(0, 10, 20)", {}, ctx)
    assert result == 20.0, f"Expected 20.0 for false condition, got {result}"

    # With comparison
    result = safe_eval("IF_THEN_ELSE(5 > 3, 100, 200)", {}, ctx)
    assert result == 100.0, f"Expected 100.0, got {result}"

    print("  PASS: IF_THEN_ELSE function works")


def test_random_functions():
    """Test random functions."""
    print("Testing random functions...")

    ctx = SimulationContext()

    # RANDOM_UNIFORM - check bounds
    for _ in range(10):
        result = safe_eval("RANDOM_UNIFORM(0, 10)", {}, ctx)
        assert 0 <= result <= 10, f"RANDOM_UNIFORM out of bounds: {result}"

    # RANDOM_NORMAL - just check it returns a number
    for _ in range(10):
        result = safe_eval("RANDOM_NORMAL(5, 1)", {}, ctx)
        assert isinstance(result, float), f"RANDOM_NORMAL returned non-float: {type(result)}"

    print("  PASS: Random functions work")


def test_lookup_interp():
    """Test lookup table interpolation."""
    print("Testing lookup interpolation...")

    points = [(0, 0), (10, 100), (20, 50)]

    # Exact point
    result = lookup_interp(10, points)
    assert result == 100.0, f"Expected 100.0 at x=10, got {result}"

    # Interpolation
    result = lookup_interp(5, points)
    assert result == 50.0, f"Expected 50.0 at x=5, got {result}"  # Linear between (0,0) and (10,100)

    # Extrapolation below
    result = lookup_interp(-5, points)
    assert result == -50.0, f"Expected -50.0 at x=-5, got {result}"

    # Extrapolation above
    result = lookup_interp(25, points)
    assert result == 25.0, f"Expected 25.0 at x=25, got {result}"

    print("  PASS: Lookup interpolation works")


def test_lookup_function():
    """Test LOOKUP function with tables."""
    print("Testing LOOKUP function...")

    tables = {"test_table": [(0, 0), (10, 100), (20, 50)]}
    ctx = SimulationContext(tables=tables)

    result = safe_eval("LOOKUP(test_table, 5)", {}, ctx)
    assert result == 50.0, f"Expected 50.0, got {result}"

    print("  PASS: LOOKUP function works")


def test_delay_smooth_simulation():
    """Test DELAY and SMOOTH in a full simulation."""
    print("Testing DELAY/SMOOTH in simulation...")

    # Create a simple model with DELAY
    model = Model(
        name="Delay Test",
        stocks=[
            Stock(name="Stock1", initial_value=0, position=Position(x=100, y=100))
        ],
        flows=[
            Flow(name="Inflow", equation="STEP(10, 5)", to_stock="Stock1",
                 position=Position(x=50, y=100))
        ],
        variables=[
            Variable(name="Delayed", equation="SMOOTH(Stock1, 5)",
                    position=Position(x=200, y=100))
        ],
        time_settings=TimeSettings(start=0, end=50, dt=0.5)
    )

    result = simulate_euler(model)

    # Check that simulation completed
    assert len(result.time) > 0, "No time values"
    assert "Stock1" in result.values, "Stock1 not in results"
    assert "Delayed" in result.values, "Delayed not in results"

    # Stock should accumulate after time 5
    final_stock = result.values["Stock1"][-1]
    assert final_stock > 0, f"Stock should be positive, got {final_stock}"

    # Delayed should be less than stock (it lags behind)
    final_delayed = result.values["Delayed"][-1]
    assert final_delayed < final_stock, f"Delayed {final_delayed} should be less than Stock {final_stock}"

    print("  PASS: DELAY/SMOOTH simulation works")


def test_rk4_vs_euler():
    """Test that RK4 and Euler produce similar results for simple models."""
    print("Testing RK4 vs Euler...")

    # Simple exponential growth model
    model = Model(
        name="Growth Test",
        stocks=[
            Stock(name="Population", initial_value=100, position=Position(x=100, y=100))
        ],
        flows=[
            Flow(name="Growth", equation="Population * 0.1", to_stock="Population",
                 position=Position(x=50, y=100))
        ],
        variables=[],
        time_settings=TimeSettings(start=0, end=10, dt=0.1)
    )

    euler_result = simulate_euler(model)
    rk4_result = simulate_rk4(model)

    # Both should complete
    assert len(euler_result.time) == len(rk4_result.time), "Different number of time steps"

    # Results should be similar (RK4 more accurate)
    euler_final = euler_result.values["Population"][-1]
    rk4_final = rk4_result.values["Population"][-1]

    # Analytical solution: 100 * e^(0.1*10) = 100 * e = ~271.8
    analytical = 100 * math.exp(0.1 * 10)

    print(f"  Euler: {euler_final:.2f}, RK4: {rk4_final:.2f}, Analytical: {analytical:.2f}")

    # RK4 should be closer to analytical
    euler_error = abs(euler_final - analytical)
    rk4_error = abs(rk4_final - analytical)

    assert rk4_error <= euler_error, f"RK4 error {rk4_error} should be <= Euler error {euler_error}"

    print("  PASS: RK4 is more accurate than Euler")


def test_model_with_lookup_table():
    """Test a model that uses lookup tables."""
    print("Testing model with lookup table...")

    model = Model(
        name="Lookup Test",
        stocks=[
            Stock(name="Stock1", initial_value=50, position=Position(x=100, y=100))
        ],
        flows=[
            Flow(name="Inflow", equation="LOOKUP(effect_curve, Stock1)",
                 to_stock="Stock1", position=Position(x=50, y=100))
        ],
        tables=[
            LookupTable(name="effect_curve", points=[(0, 10), (50, 5), (100, 0)])
        ],
        time_settings=TimeSettings(start=0, end=20, dt=0.5)
    )

    result = simulate_euler(model)

    assert len(result.time) > 0, "No time values"
    assert "Stock1" in result.values, "Stock1 not in results"

    # Stock should grow (inflow is positive based on lookup)
    initial = result.values["Stock1"][0]
    final = result.values["Stock1"][-1]
    assert final > initial, f"Stock should grow from {initial} to {final}"

    print("  PASS: Model with lookup table works")


def run_all_tests():
    """Run all XMILE feature tests."""
    print("=" * 60)
    print("XMILE/PySD FEATURE TESTS")
    print("=" * 60)

    tests = [
        test_time_variable,
        test_step_function,
        test_pulse_function,
        test_ramp_function,
        test_if_then_else,
        test_random_functions,
        test_lookup_interp,
        test_lookup_function,
        test_delay_smooth_simulation,
        test_rk4_vs_euler,
        test_model_with_lookup_table,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  FAIL: {test.__name__}: {e}")

    print("-" * 60)
    print(f"Tests: {passed}/{passed + failed} passed")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
