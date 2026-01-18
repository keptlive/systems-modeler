"""
API endpoints for AI-powered simulation analysis.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.llm.analyzer import analyze_results, is_analyzer_available, compute_statistics, detect_pattern, detect_peaks, detect_equilibrium, compute_correlations
from app.storage.models import get_model


router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request to analyze simulation results."""
    model_id: Optional[str] = None
    model: Optional[dict] = None
    simulation_results: dict
    question: Optional[str] = None


class StatisticsRequest(BaseModel):
    """Request for pure statistical analysis without AI."""
    simulation_results: dict


@router.get("/analyze/status")
async def get_analyzer_status():
    """Check if AI analyzer is available."""
    return {
        "available": is_analyzer_available(),
        "message": "Gemini API configured" if is_analyzer_available() else "Set GEMINI_API_KEY to enable AI analysis"
    }


@router.post("/analyze")
async def analyze_simulation(request: AnalyzeRequest):
    """
    Analyze simulation results using AI.

    Provides:
    - Summary of what happened in the simulation
    - Pattern recognition (growth, decay, oscillation, equilibrium)
    - Specific insights with values and time points
    - Recommendations for model modifications
    - Answers to user questions about the results
    """
    # Get model info
    model_info = None
    if request.model:
        model_info = request.model
    elif request.model_id:
        model_info = get_model(request.model_id)
        if model_info:
            model_info = model_info.model_dump()

    if not model_info:
        model_info = {
            "name": "Unknown Model",
            "description": "",
            "stocks": [],
            "flows": [],
            "variables": []
        }

    # Validate simulation results
    results = request.simulation_results
    if "time" not in results or "values" not in results:
        raise HTTPException(
            status_code=400,
            detail="simulation_results must contain 'time' and 'values' keys"
        )

    if not results["time"] or not results["values"]:
        raise HTTPException(
            status_code=400,
            detail="simulation_results cannot be empty"
        )

    # Run analysis
    try:
        analysis = analyze_results(model_info, results, request.question)

        return {
            "summary": analysis.summary,
            "insights": analysis.insights,
            "recommendations": analysis.recommendations,
            "patterns": analysis.patterns,
            "answer": analysis.answer,
            "ai_available": is_analyzer_available()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/analyze/statistics")
async def get_statistics(request: StatisticsRequest):
    """
    Get pure statistical analysis of simulation results.
    This endpoint works without AI and provides:
    - Summary statistics (min, max, mean, std, etc.)
    - Pattern detection
    - Peak analysis
    - Equilibrium detection
    - Correlation matrix
    """
    results = request.simulation_results

    if "time" not in results or "values" not in results:
        raise HTTPException(
            status_code=400,
            detail="simulation_results must contain 'time' and 'values' keys"
        )

    time = results["time"]
    values = results["values"]

    # Compute all statistics
    stats = {}
    patterns = {}
    peaks = {}
    equilibria = {}

    for name, vals in values.items():
        stats[name] = compute_statistics(vals)
        patterns[name] = detect_pattern(time, vals)
        detected_peaks = detect_peaks(time, vals)
        if detected_peaks:
            peaks[name] = detected_peaks
        eq = detect_equilibrium(vals)
        if eq:
            equilibria[name] = eq

    correlations = compute_correlations(results)

    return {
        "statistics": stats,
        "patterns": patterns,
        "peaks": peaks,
        "equilibria": equilibria,
        "correlations": correlations,
        "time_range": {
            "start": time[0] if time else 0,
            "end": time[-1] if time else 0,
            "steps": len(time)
        }
    }


@router.post("/analyze/ask")
async def ask_about_results(request: AnalyzeRequest):
    """
    Ask a specific question about simulation results.
    Requires GEMINI_API_KEY to be set.
    """
    if not is_analyzer_available():
        raise HTTPException(
            status_code=503,
            detail="AI analysis not available. Set GEMINI_API_KEY to enable."
        )

    if not request.question:
        raise HTTPException(
            status_code=400,
            detail="Question is required for this endpoint"
        )

    # Get model info
    model_info = None
    if request.model:
        model_info = request.model
    elif request.model_id:
        model_info = get_model(request.model_id)
        if model_info:
            model_info = model_info.model_dump()

    if not model_info:
        model_info = {
            "name": "Unknown Model",
            "description": "",
            "stocks": [],
            "flows": [],
            "variables": []
        }

    results = request.simulation_results

    try:
        analysis = analyze_results(model_info, results, request.question)

        return {
            "question": request.question,
            "answer": analysis.answer,
            "supporting_insights": analysis.insights[:3],
            "ai_available": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to answer question: {str(e)}"
        )
