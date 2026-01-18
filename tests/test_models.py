"""
Test models in the models/ directory.
Loads each model and runs simulation to check for errors.
"""
import os
import sys
import json
import math
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.model import Model
from app.core.simulator import simulate


def load_all_models(models_dir: str = "models") -> list:
    """Load all JSON model files from the models directory."""
    models_path = Path(__file__).parent.parent / models_dir
    models = []

    if not models_path.exists():
        print(f"Warning: Models directory not found: {models_path}")
        return []

    for file_path in models_path.glob("*.json"):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            model = Model(**data)
            models.append((file_path.name, model))
        except Exception as e:
            print(f"FAIL: Could not load {file_path.name}: {e}")

    return models


def check_for_bad_values(values: dict) -> list:
    """Check simulation results for NaN, Inf, or extreme values."""
    issues = []

    for var_name, var_values in values.items():
        for i, v in enumerate(var_values):
            if v is None:
                issues.append(f"{var_name}[{i}] is None")
            elif not isinstance(v, (int, float)):
                issues.append(f"{var_name}[{i}] is not a number: {type(v)}")
            elif math.isnan(v):
                issues.append(f"{var_name}[{i}] is NaN")
            elif math.isinf(v):
                issues.append(f"{var_name}[{i}] is Infinity")

    return issues


def _test_model_simulation(name: str, model: Model) -> tuple:
    """
    Test a single model simulation (internal helper function).
    Returns (success, message).
    """
    try:
        # Skip empty models (no stocks, flows, or variables)
        is_empty = not model.stocks and not model.flows and not model.variables
        if is_empty:
            return True, "Empty model (no elements to simulate)"

        result = simulate(model)

        # Check time array
        if not result.time:
            return False, "No time values returned"

        # Check values exist (only fail if model has elements but no results)
        if not result.values:
            return False, "No variable values returned"

        # Check for bad values
        issues = check_for_bad_values(result.values)
        if issues:
            # Only report first 3 issues
            issue_str = "; ".join(issues[:3])
            if len(issues) > 3:
                issue_str += f" (+{len(issues) - 3} more)"
            return False, f"Bad values: {issue_str}"

        # All checks passed
        return True, f"Simulated {len(result.time)} time steps, {len(result.values)} variables"

    except Exception as e:
        return False, f"Simulation error: {str(e)}"


def run_all_model_tests() -> dict:
    """Run tests on all models and return results."""
    models = load_all_models()

    if not models:
        print("No models found to test")
        return {"passed": 0, "failed": 0, "total": 0, "results": []}

    results = []
    passed = 0
    failed = 0

    for name, model in models:
        success, message = _test_model_simulation(name, model)
        results.append({
            "name": name,
            "success": success,
            "message": message
        })

        if success:
            passed += 1
            print(f"PASS: {name} - {message}")
        else:
            failed += 1
            print(f"FAIL: {name} - {message}")

    return {
        "passed": passed,
        "failed": failed,
        "total": len(models),
        "results": results
    }


def test_all_models_simulate():
    """Pytest-discoverable test that runs all model simulations."""
    results = run_all_model_tests()

    # Collect failures for better error messages
    failures = [r for r in results['results'] if not r['success']]

    if failures:
        failure_msg = "\n".join([f"  - {r['name']}: {r['message']}" for r in failures])
        assert False, f"Model simulation failures:\n{failure_msg}"

    assert results['passed'] == results['total'], f"Not all models passed: {results['passed']}/{results['total']}"


if __name__ == "__main__":
    print("=" * 50)
    print("MODEL TESTS")
    print("=" * 50)

    results = run_all_model_tests()

    print("-" * 50)
    print(f"Models: {results['passed']}/{results['total']} passing")

    if results['failed'] > 0:
        print("\nFAILURES:")
        for r in results['results']:
            if not r['success']:
                print(f"  - {r['name']}: {r['message']}")
        sys.exit(1)
    else:
        sys.exit(0)
