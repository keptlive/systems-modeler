"""
API endpoint for running simulations.
"""
from fastapi import APIRouter, HTTPException
from app.core.model import SimulationRequest, SimulationResult, Model
from app.core.simulator import simulate
from app.storage import models as storage

router = APIRouter()


@router.post("/simulate", response_model=SimulationResult)
async def run_simulation(request: SimulationRequest):
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
        model = storage.get_model(request.model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
    else:
        raise HTTPException(status_code=400, detail="Must provide model or model_id")

    # Run simulation
    try:
        result = simulate(model, request.time_settings)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")
