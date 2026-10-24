"""
API endpoints for LLM-powered model generation and modification.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from app.core.model import LLMGenerateRequest, LLMModifyRequest, Model
from app.llm.generator import generate_model, is_llm_available, LLMError
from app.llm.modifier import modify_model
from app.llm.credentials import user_ai, UserAI
from app.llm.generator import call_user_llm
from app.llm.feedback import find_equilibrium, fit_to_data, refine_model
from app.storage import models as storage

router = APIRouter()


# Request models for feedback endpoints
class FindEquilibriumRequest(BaseModel):
    model: Model
    target_stocks: Optional[list[str]] = None
    max_iterations: int = Field(default=100, ge=1, le=500)


class FitToDataRequest(BaseModel):
    model: Model
    historical_data: dict[str, list[float]]
    time_points: list[float]
    max_iterations: int = Field(default=200, ge=1, le=500)


class RefineModelRequest(BaseModel):
    model: Model
    simulation_results: dict
    feedback: str


@router.get("/status")
def llm_status(options: UserAI | None = Depends(user_ai)):
    if options is not None:
        return {"available": True, "configured": True, "verified": False, "provider": "openrouter", "model": options.model, "message": "User OpenRouter key supplied; connection not tested"}
    """Check if LLM functionality is available."""
    configured=is_llm_available()
    return {"available":configured,"configured":configured,"verified":False,
            "message":"Optional server AI configuration; use your own agent through MCP without a server-side AI account"}


@router.post("/test")
def test_user_connection(options: UserAI | None = Depends(user_ai)):
    if options is None:
        raise HTTPException(400, "Supply your OpenRouter key to test the connection.")
    try:
        call_user_llm([{"role": "user", "content": "Reply with OK."}], options, json_mode=False, max_tokens=64)
        return {"available": True, "verified": True, "provider": "openrouter", "model": options.model}
    except LLMError as error:
        raise HTTPException(error.status_code, str(error)) from None


@router.post("/generate", response_model=Model)
def generate_model_from_description(request: LLMGenerateRequest, options: UserAI | None = Depends(user_ai)):
    """
    Generate a new model from a natural language description.

    Example: "Create a model of population growth with births and deaths"
    """
    if options is None and not is_llm_available():
        raise HTTPException(
            status_code=503,
            detail="LLM not available. Set GEMINI_API_KEY or OPENROUTER_API_KEY."
        )

    try:
        model = generate_model(request.description, **({"options": options} if options else {}))
        return model
    except LLMError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None
    except Exception as e:
        raise HTTPException(status_code=502, detail="AI returned an invalid model. Try again with a simpler request.")


@router.post("/modify", response_model=Model)
def modify_existing_model(request: LLMModifyRequest, options: UserAI | None = Depends(user_ai)):
    """
    Modify an existing model based on a natural language request.

    Example: "Add immigration flow to the population model"
    """
    if options is None and not is_llm_available():
        raise HTTPException(
            status_code=503,
            detail="LLM not available. Set GEMINI_API_KEY or OPENROUTER_API_KEY."
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
        modified = modify_model(model, request.modification, **({"options": options} if options else {}))
        return modified
    except LLMError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None
    except Exception as e:
        raise HTTPException(status_code=502, detail="AI returned an invalid modification. Try again with a simpler request.")


@router.post("/find-equilibrium")
def api_find_equilibrium(request: FindEquilibriumRequest):
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
def api_fit_to_data(request: FitToDataRequest):
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
def api_refine_model(request: RefineModelRequest, options: UserAI | None = Depends(user_ai)):
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
    if options is not None:
        raise HTTPException(400, "User OpenRouter keys support generation, modification and analysis. Use Modify for this request.")
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
def tune_model_endpoint(request: TuneModelRequest, options: UserAI | None = Depends(user_ai)):
    """Multi-step AI tuning that iteratively adjusts parameters."""
    if options is not None:
        raise HTTPException(400, "User OpenRouter keys support generation, modification and analysis. Use Modify for this request.")
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
