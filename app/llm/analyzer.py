"""Descriptive simulation analytics; heuristics do not establish model validity."""
import os
import json
import math
from itertools import combinations
from typing import Optional
from dataclasses import dataclass

from app.core.limits import MAX_SAMPLES, MAX_ELEMENTS, MAX_RETAINED_VALUES

MAX_ANALYTIC_VALUES = MAX_RETAINED_VALUES
MAX_CORRELATION_PAIRS = 2_000


@dataclass
class AnalysisResult:
    """Result of optional AI interpretation and deterministic analytics."""
    summary: str
    insights: list[str]
    recommendations: list[str]
    patterns: list[dict]
    answer: Optional[str] = None
    ai_used: bool = False


def get_gemini_client():
    """Get configured Gemini client without exposing configuration."""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            return genai
        except ImportError:
            pass
    return None


def _numeric(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def validate_results(results: dict) -> dict:
    """Require aligned finite samples; never silently drop or coerce inputs."""
    if not isinstance(results, dict):
        raise ValueError("simulation_results must be an object")
    time, values = results.get("time"), results.get("values")
    if not isinstance(time, list) or not time or not isinstance(values, dict) or not values:
        raise ValueError("simulation_results requires nonempty 'time' and 'values'")
    if len(time) > MAX_SAMPLES or len(values) > MAX_ELEMENTS or len(time) * len(values) > MAX_ANALYTIC_VALUES:
        raise ValueError("Analytics supports at most 500 series, 100001 samples and 1000000 total values")
    if not all(_numeric(t) for t in time):
        raise ValueError("Time samples must be finite numbers")
    if any(b <= a for a, b in zip(time, time[1:])) or not math.isfinite(time[-1] - time[0]):
        raise ValueError("Time samples must strictly increase within a finite duration")
    if len(time) > 1 and any((b - a) / (time[-1] - time[0]) == 0 for a, b in zip(time, time[1:])):
        raise ValueError("Time sample spacing exceeds supported floating-point resolution")
    for name, series in values.items():
        if not isinstance(name, str) or not name:
            raise ValueError("Every series requires a nonempty string name")
        if not isinstance(series, list) or len(series) != len(time):
            raise ValueError(f"Series {name!r} must have one value for every time sample")
        if not all(_numeric(v) for v in series):
            raise ValueError(f"Series {name!r} contains a non-finite or non-numeric value")
    return results


def _finite(value):
    """JSON has no infinity; expose unrepresentable derived quantities as null."""
    return float(value) if math.isfinite(value) else None


def _moments(values):
    scale = max(map(abs, values), default=0)
    scaled = [v / scale for v in values] if scale else [0.0] * len(values)
    mean = math.fsum(scaled) / len(values)
    std = math.sqrt(math.fsum((v - mean) ** 2 for v in scaled) / len(values))
    return scale, scaled, mean, std


def compute_statistics(values: list[float], time: Optional[list[float]] = None) -> dict:
    """Population statistics of recorded samples plus a trapezoidal time average."""
    if not values or not all(_numeric(v) for v in values):
        return {"error": "Expected nonempty finite numeric values"}
    scale, scaled, mean, std = _moments(values)
    ordered = sorted(scaled)
    n = len(values)
    median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    change = scaled[-1] - scaled[0]
    pct = _finite(change / scaled[0] * 100) if scaled[0] else None
    weighted_mean = None
    if time is not None and len(time) == n and n > 1 and time[-1] > time[0]:
        duration = time[-1] - time[0]
        weighted_mean = _finite(scale * math.fsum(
            ((scaled[i] + scaled[i - 1]) / 2) * ((time[i] - time[i - 1]) / duration)
            for i in range(1, n)))
    result = {
        "min": float(min(values)), "max": float(max(values)), "mean": _finite(scale * mean),
        "std": _finite(scale * std), "median": _finite(scale * median),
        "range": _finite(scale * (max(scaled) - min(scaled))),
        "initial": float(values[0]), "final": float(values[-1]),
        "total_change": _finite(scale * change), "percent_change": pct,
        "sample_count": n, "time_weighted_mean": weighted_mean,
    }
    result["unrepresentable_metrics"] = [key for key in ("mean", "std", "median", "range", "total_change") if result[key] is None]
    return result


def detect_peaks(time: list[float], values: list[float]) -> list[dict]:
    """Strict local sample extrema; plateaus/endpoints are not called peaks."""
    peaks = []
    for i in range(1, len(values) - 1):
        kind = "peak" if values[i] > values[i - 1] and values[i] > values[i + 1] else (
            "trough" if values[i] < values[i - 1] and values[i] < values[i + 1] else None)
        if kind:
            peaks.append({"type": kind, "time": time[i], "value": float(values[i]), "index": i})
    return peaks


def detect_equilibrium(values: list[float], threshold: float = 0.01) -> Optional[dict]:
    """Legacy field name: report observed tail stability, never equilibrium proof."""
    if len(values) < 10:
        return None
    check_start = min(int(len(values) * 0.8), len(values) - 3)
    tail = values[check_start:]
    scale, scaled, mean, std = _moments(tail)
    global_scale = max(map(abs, values))
    denominator = max(abs(mean), global_scale / scale * 1e-12) if scale else 1.0
    variation = std / denominator
    span = (max(scaled) - min(scaled)) / denominator
    stable = span <= threshold
    return {
        "reached": stable, "start_index": check_start, "equilibrium_value": _finite(scale * mean),
        "variation": _finite(variation), "relative_span": _finite(span),
        "status": "nearly_stable_tail" if stable else "varying_tail",
        "assessed_samples": len(tail), "proves_equilibrium": False,
        "criterion": f"Last {len(tail)} samples span no more than {threshold * 100:g}% of their mean magnitude; near-zero floor is 1e-12 of full-series scale",
    }


def detect_pattern(time: list[float], values: list[float]) -> str:
    """Conservative descriptive shape rules respecting actual sample times."""
    if len(values) < 3:
        return "insufficient_data"
    scale = max(map(abs, values))
    normalized = [v / scale for v in values] if scale else [0.0] * len(values)
    if max(normalized) - min(normalized) <= 1e-12:
        return "constant"
    duration = time[-1] - time[0]
    deltas = [(time[i] - time[i - 1]) / duration for i in range(1, len(time))]
    slopes = [(normalized[i] - normalized[i - 1]) / deltas[i - 1] for i in range(1, len(values))]
    if not all(math.isfinite(slope) for slope in slopes):
        return "complex"
    tol = max(map(abs, slopes)) * 1e-6
    positive = all(s >= -tol for s in slopes)
    negative = all(s <= tol for s in slopes)
    if positive or negative:
        suffix = "growth" if positive else "decay"
        if max(slopes) - min(slopes) <= tol:
            return f"linear_{suffix}"
        # Curvature alone never establishes exponential behavior. Require a
        # nearly constant log rate, with at least four strictly positive samples.
        if len(values) >= 4 and min(values) > 0:
            logs = [math.log(v) for v in values]
            rates = [(logs[i] - logs[i - 1]) / deltas[i - 1] for i in range(1, len(values))]
            if max(rates) - min(rates) <= max(map(abs, rates)) * 1e-4:
                return f"exponential_{suffix}"
        curvature = [b - a for a, b in zip(slopes, slopes[1:])]
        if all(c >= -tol for c in curvature):
            return "accelerating_growth" if positive else "slowing_decline"
        if all(c <= tol for c in curvature):
            return "slowing_growth" if positive else "accelerating_decline"
        return "monotonic_growth" if positive else "monotonic_decline"
    signs = [1 if s > tol else -1 for s in slopes if abs(s) > tol]
    turns = sum(a != b for a, b in zip(signs, signs[1:]))
    if turns >= 3:
        return "oscillating"
    if turns == 1:
        return "peak_and_decline" if signs[0] > 0 else "trough_and_recovery"
    return "complex"


def correlation_records(results: dict) -> tuple[dict, list[dict], dict]:
    """Pearson sample association, scaled before centering to avoid overflow."""
    values = results.get("values", {})
    pairs = combinations(values, 2)
    count = len(values) * (len(values) - 1) // 2
    correlations, records = {}, []
    moments = {name: _moments(series) for name, series in values.items()}
    assessed = 0
    for name1, name2 in pairs:
        if assessed >= MAX_CORRELATION_PAIRS:
            break
        assessed += 1
        a, b = values[name1], values[name2]
        if len(a) < 3:
            continue
        _, x, xm, xs = moments[name1]
        _, y, ym, ys = moments[name2]
        if not xs or not ys:
            continue
        corr = math.fsum(((u - xm) / xs) * ((v - ym) / ys) / len(a) for u, v in zip(x, y))
        corr = round(min(1.0, max(-1.0, corr)), 3)
        correlations[f"{name1}|{name2}"] = corr
        records.append({"variables": [name1, name2], "correlation": corr, "samples": len(a)})
    return correlations, records, {"total_pairs": count, "assessed_pairs": assessed, "omitted_pairs": count - assessed,
                                   "limit": MAX_CORRELATION_PAIRS, "method": "Pearson sample correlation; association does not establish causation"}


def compute_correlations(results: dict) -> dict:
    return correlation_records(results)[0]


def descriptive_analysis(results: dict) -> dict:
    validate_results(results)
    time, values = results["time"], results["values"]
    stats, patterns, peaks, equilibria = {}, {}, {}, {}
    for name, series in values.items():
        stats[name] = compute_statistics(series, time)
        patterns[name] = detect_pattern(time, series)
        extrema = detect_peaks(time, series)
        if extrema:
            peaks[name] = extrema
        tail = detect_equilibrium(series)
        if tail:
            equilibria[name] = tail
    correlations, records, coverage = correlation_records(results)
    return {"statistics": stats, "patterns": patterns, "peaks": peaks, "equilibria": equilibria,
            "correlations": correlations, "correlation_pairs": records, "correlation_coverage": coverage,
            "time_range": {"start": time[0], "end": time[-1], "steps": len(time), "intervals": len(time) - 1},
            "limitations": ["Patterns and tail stability describe recorded samples, not scientific validity or proof of equilibrium.",
                            "Correlation across time series may reflect shared trends; it does not establish causal influence.",
                            "Sample mean and population standard deviation weight each recorded sample equally; time_weighted_mean uses trapezoidal integration.",
                            "Derived metrics that exceed finite floating-point range are returned as null."]}

def build_analysis_prompt(model_info: dict, results: dict, stats: dict,
                          patterns: dict, correlations: dict,
                          question: Optional[str] = None) -> str:
    """Build the prompt for AI analysis."""

    prompt = """You are a systems dynamics analyst interpreting unverified simulation inputs and recorded samples.
Do not present generated equations, source claims, heuristic patterns or finite outputs as scientific validation.
Correlations of trending time series do not prove causal influence. A nearly stable tail does not establish equilibrium.
Recommendations are hypotheses to test, not warranted real-world interventions. State uncertainty and missing evidence.
Only cite times and values actually provided below. Do not invent peak times or measurements.

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
        prompt += f"From t={time[0]} to t={time[-1]} ({len(time)} samples, {len(time)-1} intervals)\n"

    prompt += "\n## Statistics per Variable\n"
    for name, s in stats.items():
        if "error" in s:
            continue
        prompt += f"\n### {name}\n"
        prompt += f"- Range: {s['min']:.2f} to {s['max']:.2f}\n"
        prompt += f"- Sample mean: {s['mean']}, Population Std Dev: {s['std']}, Time-weighted mean: {s['time_weighted_mean']}\n"
        prompt += f"- Initial: {s['initial']:.2f}, Final: {s['final']:.2f}\n"
        if s.get('percent_change') is not None:
            prompt += f"- Total change: {s['percent_change']:.1f}%\n"
        extrema = detect_peaks(time, results['values'][name])
        if extrema:
            prompt += f"- Recorded local extrema (first 10): {json.dumps(extrema[:10])}\n"

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
    """Always compute verified descriptive metrics before optional AI interpretation."""
    report = descriptive_analysis(results)
    stats, patterns = report["statistics"], report["patterns"]
    pattern_records = [{"variable": name, "pattern": pattern, "stats": stats[name],
                        "peaks": report["peaks"].get(name, []), "equilibrium": report["equilibria"].get(name)}
                       for name, pattern in patterns.items()]
    insights = [f"{name} shows {patterns[name].replace('_', ' ')} in the recorded samples; its range is {s['min']:.6g} to {s['max']:.6g}."
                for name, s in stats.items()]
    for name, tail in report["equilibria"].items():
        if tail["reached"]:
            insights.append(f"{name} has a nearly stable final {tail['assessed_samples']} samples; this does not establish equilibrium.")
    fallback = AnalysisResult(
        summary="Descriptive analysis of the recorded samples. Model validity and causal conclusions require separate checks.",
        insights=insights[:5], recommendations=["Check equations, units, initial conditions and source assumptions before interpreting the simulation.",
                                               "Compare smaller time steps and longer horizons before drawing conclusions from apparent stability."],
        patterns=pattern_records,
        answer="Natural-language interpretation requires a configured AI provider; descriptive statistics remain available." if question else None,
    )
    client = get_gemini_client()
    if not client:
        return fallback
    prompt = build_analysis_prompt(model_info, results, stats, patterns, report["correlations"], question)
    try:
        model = client.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json", "max_output_tokens": 2048})
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        if not isinstance(data, dict) or not isinstance(data.get("summary"), str):
            raise ValueError("Invalid analysis response")
        for field in ("insights", "recommendations"):
            if not isinstance(data.get(field), list) or not all(isinstance(item, str) for item in data[field]):
                raise ValueError("Invalid analysis response")
        if data.get("answer") is not None and not isinstance(data["answer"], str):
            raise ValueError("Invalid analysis answer")
        return AnalysisResult(summary=data["summary"], insights=data["insights"], recommendations=data["recommendations"],
                              patterns=pattern_records, answer=data.get("answer") if question else None, ai_used=True)
    except Exception:
        # Provider exceptions may include configuration details. Keep the public
        # fallback useful and avoid disclosing raw SDK/network exceptions.
        fallback.summary = "AI interpretation was unavailable. Showing descriptive analysis of the recorded samples."
        if question:
            fallback.answer = "AI interpretation was unavailable; no answer was generated."
        return fallback


def is_analyzer_available() -> bool:
    """Configuration presence, not a provider health check."""
    return get_gemini_client() is not None
