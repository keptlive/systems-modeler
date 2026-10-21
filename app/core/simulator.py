"""Simulation entry points. All integrations use the same validated engine."""
from typing import Optional
from app.core.model import Model, TimeSettings, SimulationResult
from app.core.integration import integrate


def simulate(model: Model, time_settings: Optional[TimeSettings] = None) -> SimulationResult:
    """Run the requested method with explicit equation errors and bounded work."""
    settings = time_settings or model.time_settings
    try:
        return integrate(model, settings)
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