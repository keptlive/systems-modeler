"""
AI-powered analysis of simulation results using Google Gemini.
Provides automatic interpretation, pattern recognition, and recommendations.
"""
import os
import json
import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class AnalysisResult:
    """Result of AI analysis."""
    summary: str
    insights: list[str]
    recommendations: list[str]
    patterns: list[dict]
    answer: Optional[str] = None


def get_gemini_client():
    """Get configured Gemini client."""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            return genai
        except ImportError:
            pass
    return None


def compute_statistics(values: list[float]) -> dict:
    """Compute comprehensive statistics for a variable."""
    arr = np.array([v for v in values if v is not None and np.isfinite(v)])
    if len(arr) == 0:
        return {"error": "No valid values"}

    return {
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "median": float(np.median(arr)),
        "range": float(np.max(arr) - np.min(arr)),
        "initial": float(arr[0]) if len(arr) > 0 else None,
        "final": float(arr[-1]) if len(arr) > 0 else None,
        "total_change": float(arr[-1] - arr[0]) if len(arr) > 1 else 0,
        "percent_change": float((arr[-1] - arr[0]) / arr[0] * 100) if len(arr) > 1 and arr[0] != 0 else None
    }


def detect_peaks(time: list[float], values: list[float]) -> list[dict]:
    """Detect peaks and troughs in the data."""
    peaks = []
    arr = np.array(values)

    for i in range(1, len(arr) - 1):
        # Local maximum
        if arr[i] > arr[i-1] and arr[i] > arr[i+1]:
            peaks.append({
                "type": "peak",
                "time": time[i],
                "value": float(arr[i]),
                "index": i
            })
        # Local minimum
        elif arr[i] < arr[i-1] and arr[i] < arr[i+1]:
            peaks.append({
                "type": "trough",
                "time": time[i],
                "value": float(arr[i]),
                "index": i
            })

    return peaks


def detect_equilibrium(values: list[float], threshold: float = 0.01) -> Optional[dict]:
    """Detect if and when the system reaches equilibrium."""
    arr = np.array(values)
    if len(arr) < 10:
        return None

    # Check last 20% of values for stability
    check_start = int(len(arr) * 0.8)
    check_values = arr[check_start:]

    if len(check_values) < 2:
        return None

    # Calculate relative variation
    mean_val = np.mean(check_values)
    if mean_val == 0:
        return None

    variation = np.std(check_values) / abs(mean_val) if mean_val != 0 else float('inf')

    if variation < threshold:
        # Find when equilibrium started
        for i in range(len(arr) - 1, 0, -1):
            window = arr[max(0, i-10):i+1]
            if len(window) < 2:
                continue
            window_var = np.std(window) / abs(np.mean(window)) if np.mean(window) != 0 else float('inf')
            if window_var > threshold:
                return {
                    "reached": True,
                    "start_index": i,
                    "equilibrium_value": float(mean_val),
                    "variation": float(variation)
                }
        return {
            "reached": True,
            "start_index": 0,
            "equilibrium_value": float(mean_val),
            "variation": float(variation)
        }

    return {"reached": False, "variation": float(variation)}


def detect_pattern(time: list[float], values: list[float]) -> str:
    """Detect the overall pattern in the data."""
    arr = np.array(values)
    if len(arr) < 3:
        return "insufficient_data"

    # Calculate first derivative
    diffs = np.diff(arr)

    # Check for monotonic behavior
    all_positive = np.all(diffs >= 0)
    all_negative = np.all(diffs <= 0)

    if all_positive:
        # Check for exponential vs linear
        second_diff = np.diff(diffs)
        if len(second_diff) > 0 and np.mean(second_diff) > 0:
            return "exponential_growth"
        return "linear_growth"

    if all_negative:
        second_diff = np.diff(diffs)
        if len(second_diff) > 0 and np.mean(second_diff) < 0:
            return "exponential_decay"
        return "linear_decay"

    # Check for oscillation
    sign_changes = np.sum(np.diff(np.sign(diffs)) != 0)
    if sign_changes > len(arr) * 0.3:
        return "oscillating"

    # Check for logistic/S-curve (growth that slows)
    first_half_growth = np.mean(diffs[:len(diffs)//2])
    second_half_growth = np.mean(diffs[len(diffs)//2:])

    if first_half_growth > 0 and second_half_growth < first_half_growth * 0.3:
        return "logistic_growth"

    if first_half_growth < 0 and second_half_growth > first_half_growth * 0.3:
        return "logistic_decay"

    # Check for peak then decline
    max_idx = np.argmax(arr)
    if 0.1 < max_idx / len(arr) < 0.9:
        return "peak_and_decline"

    return "complex"


def compute_correlations(results: dict) -> dict:
    """Compute correlation matrix between all variables."""
    values = results.get("values", {})
    var_names = list(values.keys())

    if len(var_names) < 2:
        return {}

    correlations = {}
    for i, name1 in enumerate(var_names):
        for name2 in var_names[i+1:]:
            arr1 = np.array(values[name1])
            arr2 = np.array(values[name2])

            # Remove NaN/Inf values
            valid = np.isfinite(arr1) & np.isfinite(arr2)
            if np.sum(valid) < 3:
                continue

            corr = np.corrcoef(arr1[valid], arr2[valid])[0, 1]
            if np.isfinite(corr):
                correlations[f"{name1}|{name2}"] = round(corr, 3)

    return correlations


def build_analysis_prompt(model_info: dict, results: dict, stats: dict,
                          patterns: dict, correlations: dict,
                          question: Optional[str] = None) -> str:
    """Build the prompt for AI analysis."""

    prompt = """You are an expert systems dynamics analyst. Analyze the following simulation results and provide insights.

## Model Information
"""
    prompt += f"Name: {model_info.get('name', 'Unknown')}\n"
    prompt += f"Description: {model_info.get('description', 'No description')}\n"

    prompt += "\n## Stocks\n"
    for stock in model_info.get('stocks', []):
        prompt += f"- {stock['name']}: initial_value={stock.get('initial_value', 0)}\n"

    prompt += "\n## Flows\n"
    for flow in model_info.get('flows', []):
        prompt += f"- {flow['name']}: {flow.get('equation', 'N/A')}\n"

    prompt += "\n## Variables\n"
    for var in model_info.get('variables', []):
        prompt += f"- {var['name']}: {var.get('equation', 'N/A')}\n"

    prompt += f"\n## Simulation Time\n"
    time = results.get('time', [])
    if time:
        prompt += f"From t={time[0]} to t={time[-1]} ({len(time)} time steps)\n"

    prompt += "\n## Statistics per Variable\n"
    for name, s in stats.items():
        if "error" in s:
            continue
        prompt += f"\n### {name}\n"
        prompt += f"- Range: {s['min']:.2f} to {s['max']:.2f}\n"
        prompt += f"- Mean: {s['mean']:.2f}, Std Dev: {s['std']:.2f}\n"
        prompt += f"- Initial: {s['initial']:.2f}, Final: {s['final']:.2f}\n"
        if s.get('percent_change') is not None:
            prompt += f"- Total change: {s['percent_change']:.1f}%\n"

    prompt += "\n## Detected Patterns\n"
    for name, pattern in patterns.items():
        prompt += f"- {name}: {pattern}\n"

    if correlations:
        prompt += "\n## Correlations\n"
        for pair, corr in correlations.items():
            strength = "strong" if abs(corr) > 0.7 else "moderate" if abs(corr) > 0.4 else "weak"
            direction = "positive" if corr > 0 else "negative"
            prompt += f"- {pair.replace('|', ' vs ')}: {corr} ({strength} {direction})\n"

    prompt += """

## Your Task
Provide a comprehensive analysis in JSON format with these fields:

1. "summary": A 2-3 sentence high-level summary of what the simulation shows
2. "insights": An array of 3-5 specific insights about the system behavior, each insight should be a complete sentence that references specific values or time points
3. "recommendations": An array of 2-4 actionable recommendations for modifying the model or its parameters to achieve different outcomes
4. "key_findings": An array of the most important quantitative findings (e.g., "Population peaked at 9,500 at time t=45")

"""

    if question:
        prompt += f"""
## User Question
The user asks: "{question}"

Include an "answer" field in your JSON response that directly answers this question based on the simulation results.
"""

    prompt += """
Respond with ONLY valid JSON, no markdown code blocks or other text."""

    return prompt


def analyze_results(model_info: dict, results: dict, question: Optional[str] = None) -> AnalysisResult:
    """
    Analyze simulation results using AI.

    Args:
        model_info: The model definition (stocks, flows, variables)
        results: Simulation results with 'time' and 'values' keys
        question: Optional user question about the results

    Returns:
        AnalysisResult with summary, insights, recommendations, and optional answer
    """
    client = get_gemini_client()

    time = results.get("time", [])
    values = results.get("values", {})

    # Compute statistics for all variables
    stats = {}
    for name, vals in values.items():
        stats[name] = compute_statistics(vals)

    # Detect patterns for all variables
    patterns = {}
    for name, vals in values.items():
        patterns[name] = detect_pattern(time, vals)

    # Compute correlations
    correlations = compute_correlations(results)

    # Detect peaks for all variables
    all_peaks = {}
    for name, vals in values.items():
        peaks = detect_peaks(time, vals)
        if peaks:
            all_peaks[name] = peaks

    # Detect equilibrium for all variables
    equilibria = {}
    for name, vals in values.items():
        eq = detect_equilibrium(vals)
        if eq:
            equilibria[name] = eq

    # If no AI available, generate basic analysis
    if not client:
        insights = []
        recommendations = []

        for name, s in stats.items():
            if "error" in s:
                continue
            pattern = patterns.get(name, "unknown")
            insights.append(f"{name} shows {pattern.replace('_', ' ')} behavior, ranging from {s['min']:.2f} to {s['max']:.2f}")

            if pattern == "exponential_growth":
                recommendations.append(f"Consider adding limiting factors to {name} to prevent unbounded growth")
            elif pattern == "exponential_decay":
                recommendations.append(f"Review inflows to {name} - currently declining rapidly")

        if equilibria:
            for name, eq in equilibria.items():
                if eq.get("reached"):
                    insights.append(f"{name} reaches equilibrium at approximately {eq['equilibrium_value']:.2f}")

        return AnalysisResult(
            summary="Analysis completed using statistical methods. Enable Gemini API for AI-powered insights.",
            insights=insights[:5],
            recommendations=recommendations[:4],
            patterns=[{"variable": k, "pattern": v, "stats": stats.get(k, {})} for k, v in patterns.items()],
            answer="AI analysis unavailable. Please set GEMINI_API_KEY for natural language answers." if question else None
        )

    # Build prompt and call AI
    prompt = build_analysis_prompt(model_info, results, stats, patterns, correlations, question)

    try:
        model = client.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "max_output_tokens": 2048,
            }
        )

        # Parse response
        response_text = response.text

        # Clean up response if needed
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()

        data = json.loads(response_text)

        return AnalysisResult(
            summary=data.get("summary", "Analysis complete."),
            insights=data.get("insights", []),
            recommendations=data.get("recommendations", []),
            patterns=[{"variable": k, "pattern": v, "stats": stats.get(k, {}),
                      "peaks": all_peaks.get(k, []), "equilibrium": equilibria.get(k)}
                     for k, v in patterns.items()],
            answer=data.get("answer") if question else None
        )

    except Exception as e:
        # Fallback to basic analysis on error
        return AnalysisResult(
            summary=f"AI analysis encountered an error: {str(e)}. Showing statistical analysis.",
            insights=[f"{name} ranges from {s['min']:.2f} to {s['max']:.2f}"
                     for name, s in stats.items() if "error" not in s][:5],
            recommendations=["Review model equations for potential issues"],
            patterns=[{"variable": k, "pattern": v, "stats": stats.get(k, {})} for k, v in patterns.items()],
            answer=None
        )


def is_analyzer_available() -> bool:
    """Check if AI analyzer is available."""
    return get_gemini_client() is not None
