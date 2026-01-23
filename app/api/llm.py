"""
API endpoints for LLM-powered model generation and modification.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.model import LLMGenerateRequest, LLMModifyRequest, Model
from app.llm.generator import generate_model, is_llm_available, LLMError
from app.llm.modifier import modify_model
from app.llm.feedback import find_equilibrium, fit_to_data, refine_model
from app.storage import models as storage

router = APIRouter()


# Request models for feedback endpoints
class FindEquilibriumRequest(BaseModel):
    model: Model
    target_stocks: Optional[list[str]] = None
    max_iterations: int = 100


class FitToDataRequest(BaseModel):
    model: Model
    historical_data: dict[str, list[float]]
    time_points: list[float]
    max_iterations: int = 200


class RefineModelRequest(BaseModel):
    model: Model
    simulation_results: dict
    feedback: str


@router.get("/status")
async def llm_status():
    """Check if LLM functionality is available."""
    return {"available": is_llm_available()}


@router.post("/generate", response_model=Model)
async def generate_model_from_description(request: LLMGenerateRequest):
    """
    Generate a new model from a natural language description.

    Example: "Create a model of population growth with births and deaths"
    """
    if not is_llm_available():
        raise HTTPException(
            status_code=503,
            detail="LLM not available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    try:
        model = generate_model(request.description)
        return model
    except LLMError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/modify", response_model=Model)
async def modify_existing_model(request: LLMModifyRequest):
    """
    Modify an existing model based on a natural language request.

    Example: "Add immigration flow to the population model"
    """
    if not is_llm_available():
        raise HTTPException(
            status_code=503,
            detail="LLM not available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    # Get the model
    if request.model:
        model = request.model
    elif request.model_id:
        model = storage.get_model(request.model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
    else:
        raise HTTPException(status_code=400, detail="Must provide model or model_id")

    try:
        modified = modify_model(model, request.modification)
        return modified
    except LLMError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Modification failed: {str(e)}")


@router.post("/find-equilibrium")
async def api_find_equilibrium(request: FindEquilibriumRequest):
    """
    Find parameter values that lead the system to equilibrium.

    The optimizer will adjust model parameters (stock initial values and
    variable constants) to minimize instability at the end of simulation.

    Returns:
        - found: Whether equilibrium was achieved
        - parameters: Optimized parameter values
        - equilibrium_values: Final stable values for each stock
        - convergence_time: When stability was achieved
    """
    try:
        result = find_equilibrium(
            request.model,
            target_stocks=request.target_stocks,
            max_iterations=request.max_iterations
        )
        return {
            "found": result.found,
            "parameters": result.parameters,
            "equilibrium_values": result.equilibrium_values,
            "convergence_time": result.convergence_time,
            "message": result.message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Equilibrium search failed: {str(e)}")


@router.post("/fit-to-data")
async def api_fit_to_data(request: FitToDataRequest):
    """
    Fit model parameters to match historical data.

    Uses optimization to minimize the error between simulation output
    and provided historical data points.

    Returns:
        - success: Whether fitting succeeded
        - parameters: Optimized parameter values
        - r_squared: Coefficient of determination (1.0 = perfect fit)
        - rmse: Root mean squared error
        - fitted_values: Simulation values at historical time points
    """
    try:
        result = fit_to_data(
            request.model,
            historical_data=request.historical_data,
            time_points=request.time_points,
            max_iterations=request.max_iterations
        )
        return {
            "success": result.success,
            "parameters": result.parameters,
            "r_squared": result.r_squared,
            "rmse": result.rmse,
            "fitted_values": result.fitted_values,
            "message": result.message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data fitting failed: {str(e)}")


@router.post("/refine-model")
async def api_refine_model(request: RefineModelRequest):
    """
    Use AI to suggest model refinements based on user feedback.

    The AI analyzes the current model, simulation results, and user feedback
    to suggest specific parameter changes.

    Example feedback:
    - "Population should peak higher"
    - "The infection rate seems too fast"
    - "Make the economy grow slower"

    Returns:
        - success: Whether AI could generate suggestions
        - suggestions: List of parameter change recommendations
        - modified_model: Model with suggested changes applied
        - explanation: AI's explanation of the changes
    """
    try:
        result = refine_model(
            request.model,
            simulation_results=request.simulation_results,
            feedback=request.feedback
        )
        return {
            "success": result.success,
            "suggestions": result.suggestions,
            "modified_model": result.modified_model,
            "explanation": result.explanation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model refinement failed: {str(e)}")


# Tuning endpoint
class TuneModelRequest(BaseModel):
    model: Model
    goal: str
    max_iterations: int = 10


@router.post("/tune")
async def tune_model_endpoint(request: TuneModelRequest):
    """Multi-step AI tuning that iteratively adjusts parameters."""
    from app.llm.tuner import tune_model
    
    result = tune_model(
        request.model.model_dump(),
        request.goal,
        request.max_iterations
    )
    
    return {
        "success": result.success,
        "iterations": result.iterations,
        "final_model": result.final_model,
        "summary": result.summary,
        "steps": [
            {
                "iteration": s.iteration,
                "parameters": s.parameters,
                "results_summary": s.results_summary,
                "ai_analysis": s.ai_analysis,
                "suggested_changes": s.suggested_changes
            }
            for s in result.steps
        ]
    }
