"""Validated descriptive analytics and optional AI interpretation."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.core.model import Model
from app.llm.analyzer import analyze_results, is_analyzer_available, descriptive_analysis, validate_results
from app.storage.models import get_model

router = APIRouter()


class AnalyzeRequest(BaseModel):
    model_id: Optional[str] = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")
    model: Optional[Model] = None
    simulation_results: dict
    question: Optional[str] = Field(default=None, max_length=10000)


class StatisticsRequest(BaseModel):
    simulation_results: dict


def _validated(results):
    try:
        return validate_results(results)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _model_info(request):
    if request.model is not None:
        return request.model.model_dump()
    if request.model_id:
        model = get_model(request.model_id)
        if model is None:
            raise HTTPException(status_code=404, detail="Model not found")
        return model.model_dump()
    return {"name": "Unknown Model", "description": "", "stocks": [], "flows": [], "variables": []}


@router.get("/analyze/status")
def get_analyzer_status():
    available = is_analyzer_available()
    return {"available": available, "message": "Gemini configured; provider health not checked" if available else "Set GEMINI_API_KEY to enable AI interpretation"}


@router.post("/analyze")
def analyze_simulation(request: AnalyzeRequest):
    results = _validated(request.simulation_results)
    model_info = _model_info(request)
    analysis = analyze_results(model_info, results, request.question)
    return {"summary": analysis.summary, "insights": analysis.insights, "recommendations": analysis.recommendations,
            "patterns": analysis.patterns, "answer": analysis.answer, "ai_available": is_analyzer_available(), "ai_used": analysis.ai_used}


@router.post("/analyze/statistics")
def get_statistics(request: StatisticsRequest):
    """Deterministic recorded-sample analytics. No AI calls or model writes."""
    return descriptive_analysis(_validated(request.simulation_results))


@router.post("/analyze/ask")
def ask_about_results(request: AnalyzeRequest):
    results = _validated(request.simulation_results)
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question is required for this endpoint")
    if not is_analyzer_available():
        raise HTTPException(status_code=503, detail="AI analysis not available. Set GEMINI_API_KEY to enable.")
    analysis = analyze_results(_model_info(request), results, request.question)
    return {"question": request.question, "answer": analysis.answer, "supporting_insights": analysis.insights[:3],
            "ai_available": True, "ai_used": analysis.ai_used}
