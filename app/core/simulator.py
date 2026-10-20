"""Simulation entry points. All integrations use the same validated engine."""
from typing import Optional
from app.core.model import Model, TimeSettings, SimulationResult
from app.core.integration import integrate


def simulate(model: Model, time_settings: Optional[TimeSettings] = None) -> SimulationResult:
    """Run the requested method with explicit equation errors and bounded work."""
    return integrate(model, time_settings or model.time_settings)


def simulate_euler(model: Model, time_settings: Optional[TimeSettings] = None) -> SimulationResult:
    settings = (time_settings or model.time_settings).model_copy(update={'integration_method': 'euler'})
    return integrate(model, settings)


def simulate_rk4(model: Model, time_settings: Optional[TimeSettings] = None) -> SimulationResult:
    settings = (time_settings or model.time_settings).model_copy(update={'integration_method': 'rk4'})
    return integrate(model, settings)