"""Differential contracts for immutable expression dispatch plans."""
import pytest
from app.core.equations import (EquationError, SafeEvaluator, SimulationContext,
    _execution_plan, _parse_expression, preprocess_equation, safe_eval)


@pytest.mark.parametrize("equation", [
    "a + b * 3 - a / 2", "-a ^ 2 + b % 3", "a ** b ** 2",
    "IF(a > 0, a + 2, unknown / 0)", "IF a < 0 THEN unknown ELSE b + 1",
    "0 AND unknown", "1 OR unknown", "NOT a", "a < b < 9",
    "TIME + DT + a", '"Growth Rate" * a', "sqrt(a) + max(a,b)",
    "1e308 * 1e308 / 1e308", "1 / (a-a)", "(-1)^0.5",
    "unknown + 2", "a.real", "[a,b]", "min(a=1)",
])
def test_plan_matches_interpreter_values_and_errors(equation):
    variables = {"a": 2.0, "b": 3.0, "Growth Rate": 0.25}
    normalized = preprocess_equation(equation)
    tree = _parse_expression(normalized)
    def outcome(call):
        try:
            return ("value", call())
        except Exception as error:
            return ("error", type(error), str(error), getattr(error, "code", None), getattr(error, "details", None))
    reference = outcome(lambda: SafeEvaluator(variables, SimulationContext(time=4,dt=.5)).visit(tree))
    compiled = outcome(lambda: _execution_plan(normalized)(SafeEvaluator(variables, SimulationContext(time=4,dt=.5))))
    assert compiled == reference


def test_cached_plan_never_retains_values_or_context():
    assert safe_eval("TIME + a", {"a": 1}, SimulationContext(time=2)) == 3
    assert safe_eval("TIME + a", {"a": 8}, SimulationContext(time=7)) == 15
    assert _execution_plan.cache_info().maxsize == 8192


def test_symbol_alias_cache_preserves_ambiguity_and_declared_constants():
    assert safe_eval("Growth_Rate + 1", {"Growth Rate": 3}) == 4
    with pytest.raises(EquationError, match="Ambiguous variable alias"):
        safe_eval("growth_rate+1", {"Growth Rate": 3, "GROWTH RATE": 4})
    context = SimulationContext()
    context.declared_names = {"pi"}
    with pytest.raises(EquationError) as error:
        safe_eval("pi+1", {}, context)
    assert error.value.code == "unknown_variable"


def test_existing_error_wrapper_and_intermediate_guard():
    with pytest.raises(EquationError) as error:
        safe_eval("1e308*1e308/1e308", {})
    assert "1e308*1e308/1e308" in str(error.value)
    with pytest.raises(EquationError) as error:
        safe_eval("1/0", {})
    assert error.value.code == "division_by_zero"
