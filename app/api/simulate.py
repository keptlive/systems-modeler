"""
API endpoint for running simulations.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.core.failure_diagnostics import failure_payload
from app.core.model import SimulationRequest, SimulationResult, Model
from app.core.simulator import simulate
from app.storage import models as storage

router = APIRouter()

@router.post("/investigate")
def investigate_inputs(request: SimulationRequest):
    """Compare full-horizon runs at three grids without changing any inputs."""
    from app.core.diagnostics import investigate_model
    try:
        if (request.model is None) == (request.model_id is None):
            raise ValueError("Provide exactly one model or model_id")
        model = request.model or storage.get_model(request.model_id)
        if model is None:
            raise HTTPException(status_code=404, detail="Model not found")
        if request.time_settings:
            model = model.model_copy(update={"time_settings": request.time_settings})
        return investigate_model(model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/validate")
def validate_inputs(request: SimulationRequest):
    """Inspect model input definitions and run one diagnostic step without saving."""
    from app.core.validation import inspect_inputs
    try:
        model = request.model or (storage.get_model(request.model_id) if request.model_id else None)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if model is None:
        raise HTTPException(status_code=400, detail="Provide a model or an existing model_id")
    if request.time_settings:
        model = model.model_copy(update={"time_settings": request.time_settings})
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
    # Get the model
    if request.model:
        model = request.model
    elif request.model_id:
        try:
            model = storage.get_model(request.model_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
    else:
        raise HTTPException(status_code=400, detail="Must provide model or model_id")

    # Run simulation
    try:
        result = simulate(model, request.time_settings)
        return result
    except (ValueError, ArithmeticError) as e:
        return JSONResponse(status_code=422, content={"detail": str(e), "failure": failure_payload(e)})
    except Exception as e:
        from app.core.equations import EquationError
        if isinstance(e, EquationError):
            return JSONResponse(status_code=422, content={"detail": str(e), "failure": failure_payload(e)})
        raise HTTPException(status_code=500, detail="Unexpected simulation error")
