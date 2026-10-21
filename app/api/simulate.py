"""
API endpoint for running simulations.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.core.failure_diagnostics import failure_payload
from app.core.model import SimulationRequest, SimulationResult
from app.core.simulator import simulate
from app.storage import models as storage

router = APIRouter()


def requested_model(request, apply_time_settings=True):
    """Resolve one unambiguous target and merge only explicitly supplied edits."""
    if request.model is not None and request.model_id is not None:
        raise HTTPException(status_code=422, detail="Provide exactly one model or model_id")
    if request.model is None and request.model_id is None:
        raise HTTPException(status_code=422, detail="Provide exactly one model or model_id")
    try:
        model = request.model if request.model is not None else storage.get_model(request.model_id)
        if model is None:
            raise HTTPException(status_code=404, detail="Model not found")
        if apply_time_settings and request.time_settings is not None:
            model = model.model_copy(update={"time_settings": request.time_settings.apply_to(model.time_settings)})
        return model
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.post("/investigate")
def investigate_inputs(request: SimulationRequest):
    """Compare full-horizon runs at three grids without changing any inputs."""
    from app.core.diagnostics import investigate_model
    try:
        model = requested_model(request)
        return investigate_model(model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/validate")
def validate_inputs(request: SimulationRequest):
    """Inspect model input definitions and run one diagnostic step without saving."""
    from app.core.validation import inspect_inputs
    model = requested_model(request)
    return inspect_inputs(model)


@router.post("/simulate", response_model=SimulationResult)
def run_simulation(request: SimulationRequest):
    """
    Run a simulation on a model.

    Can provide either:
    - model_id: ID of a saved model to simulate
    - model: Full model object to simulate directly

    Optionally provide time_settings to override model defaults.
    """
    model = requested_model(request, apply_time_settings=False)

    # Run simulation
    try:
        settings = request.time_settings.apply_to(model.time_settings) if request.time_settings is not None else None
        result = simulate(model, settings)
        return result
    except (ValueError, ArithmeticError) as e:
        return JSONResponse(status_code=422, content={"detail": str(e), "failure": failure_payload(e)})
    except Exception as e:
        from app.core.equations import EquationError
        if isinstance(e, EquationError):
            return JSONResponse(status_code=422, content={"detail": str(e), "failure": failure_payload(e)})
        raise HTTPException(status_code=500, detail="Unexpected simulation error")
