"""Simulation entry points. All integrations use the same validated engine."""
from typing import Optional
from app.core.model import Model, TimeSettings, SimulationResult
from app.core.integration import integrate


def simulate(model: Model, time_settings: Optional[TimeSettings] = None) -> SimulationResult:
    """Run the requested method with explicit equation errors and bounded work."""
    settings = time_settings or model.time_settings
    try:
        from app.core.structured import compile_structured_model
        compiled = compile_structured_model(model.model_dump(mode="json")) if model.has_structure() else {"source_map": {}}
        execution_model = Model(**compiled["model"]) if compiled["source_map"] else model
        result = integrate(execution_model, settings)
        if compiled["source_map"]:
            result.integration_diagnostics = {
                **(result.integration_diagnostics or {}),
                "structured_source_map": compiled["source_map"],
                "structured_diagnostics": compiled["diagnostics"],
            }
        return result
    except Exception as error:
        # Preserve the original failure and its causal diagnostics. Add enough
        # context to reproduce the exact numerical request without dumping user
        # model contents, filesystem locations or provider configuration.
        from app.core.equations import EquationError
        if isinstance(error, (EquationError, ValueError, ArithmeticError)):
            from app.core.diagnostics import model_hash, source_hashes
            details = dict(getattr(error, "details", {}))
            try:
                replay_settings = settings.model_dump(mode="json")
                if details.get("random_seed") is not None:
                    replay_settings["random_seed"] = details["random_seed"]
                details["reproduction"] = {
                    "normalized_model_sha256": model_hash(model),
                    "engine_sha256": source_hashes(),
                    "settings": replay_settings,
                }
            except (OSError, ValueError, TypeError):
                # Diagnostic metadata must never replace the actual cause.
                details["reproduction"] = {"status": "unavailable"}
            error.details = details
        raise


def simulate_euler(model: Model, time_settings: Optional[TimeSettings] = None) -> SimulationResult:
    settings = (time_settings or model.time_settings).model_copy(update={'integration_method': 'euler'})
    return simulate(model, settings)


def simulate_rk4(model: Model, time_settings: Optional[TimeSettings] = None) -> SimulationResult:
    settings = (time_settings or model.time_settings).model_copy(update={'integration_method': 'rk4'})
    return simulate(model, settings)
