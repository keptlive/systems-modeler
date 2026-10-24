"""Analytic examples and malformed-input cases; no provider calls or model writes."""
import json
import math
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.llm import analyzer as a


def result(values, time=None):
    return {"time": time if time is not None else list(range(len(next(iter(values.values()))))), "values": values}


@pytest.mark.parametrize("payload", [
    {}, {"time": [], "values": {}}, result({"x": [1, 2]}, [0]),
    result({"x": [1, None]}), result({"x": [1, True]}), result({"x": [1, "2"]}),
    result({"x": [1, 2]}, [0, 0]), result({"x": [1, 2]}, [1, 0]),
    result({"x": [1, 2]}, [False, 1]), {"time": [0, 1], "values": {"x": "12"}},
])
def test_statistics_api_rejects_malformed_samples(payload):
    response = TestClient(app).post("/api/analyze/statistics", json={"simulation_results": payload})
    assert response.status_code == 400


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 10**1000])
def test_nonfinite_input_is_not_silently_filtered(value):
    with pytest.raises(ValueError, match="non-finite"):
        a.validate_results(result({"x": [1, value]}))


def test_statistics_distinguish_sample_mean_and_time_average():
    stats = a.descriptive_analysis(result({"x": [0, 10, 10]}, [0, 1, 10]))["statistics"]["x"]
    assert stats["mean"] == pytest.approx(20/3)
    assert stats["time_weighted_mean"] == pytest.approx(9.5)
    assert stats["std"] == pytest.approx(math.sqrt(200/9))
    assert stats["median"] == 10 and stats["percent_change"] is None


def test_extreme_finite_series_remain_json_serializable():
    report = a.descriptive_analysis(result({"constant": [1e308]*10, "signed": [-1e308, 1e308]*5}))
    constant, signed = report["statistics"]["constant"], report["statistics"]["signed"]
    assert constant["mean"] == 1e308 and constant["std"] == 0
    assert signed["mean"] == 0 and signed["std"] == 1e308
    assert signed["range"] is None and "range" in signed["unrepresentable_metrics"]
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("time,values,expected", [
    ([0,1,3,10], [2,4,8,22], "linear_growth"),
    ([0,1,2,3], [1,4,9,16], "accelerating_growth"),
    ([0,1,2,3], [8,4,2,1], "exponential_decay"),
    ([0,1,2,3], [1,2,4,8], "exponential_growth"),
    ([0,1,2], [0,1e-100,2e-100], "linear_growth"),
    ([0,1,2], [0,0,0], "constant"),
    ([0,1,2,3], [-1,-4,-9,-16], "accelerating_decline"),
    ([0,1,2,3,4], [0,1,0,1,0], "oscillating"),
    ([0,1,2,3,4], [0,1,2,1,0], "peak_and_decline"),
])
def test_patterns_respect_time_and_do_not_infer_equations(time, values, expected):
    assert a.detect_pattern(time, values) == expected


def test_stability_includes_zero_and_does_not_invent_onset():
    tail = a.detect_equilibrium([0]*100)
    assert tail["reached"] and tail["equilibrium_value"] == 0
    assert tail["start_index"] == 80 and not tail["proves_equilibrium"]
    assert not a.detect_equilibrium([1]*99 + [1.02])["reached"]
    assert a.detect_equilibrium([1]*9) is None


def test_correlations_scale_large_series_and_exclude_constants():
    x = [1e150 + i*1e140 for i in range(10)]
    report = a.descriptive_analysis(result({"x|quoted": x, "<second>": [-v for v in x], "constant": [2]*10}))
    assert len(report["correlation_pairs"]) == 1
    pair = report["correlation_pairs"][0]
    assert pair["variables"] == ["x|quoted", "<second>"] and pair["correlation"] == -1
    assert report["correlation_coverage"]["assessed_pairs"] == 3


def test_correlation_work_is_bounded_and_coverage_is_explicit():
    report = a.descriptive_analysis(result({str(i): [1,2,3] for i in range(65)}))
    assert len(report["correlation_pairs"]) == 2000
    assert report["correlation_coverage"]["omitted_pairs"] == 80


def test_single_sample_and_negative_baseline_are_defined():
    stats = a.descriptive_analysis(result({"x": [5]}, [10]))
    assert stats["statistics"]["x"]["time_weighted_mean"] is None
    assert stats["patterns"]["x"] == "insufficient_data"
    assert a.compute_statistics([-10,-5])["percent_change"] == -50


def test_ai_fallback_retains_diagnostics_without_provider_call(monkeypatch):
    monkeypatch.setattr(a, "get_gemini_client", lambda: None)
    analysis = a.analyze_results({}, result({"x": [0]*10}), "Why?")
    assert not analysis.ai_used and analysis.answer
    assert analysis.patterns[0]["equilibrium"]["proves_equilibrium"] is False
    assert "equilibrium" not in analysis.summary.lower()


def test_ai_failure_does_not_disclose_raw_provider_exception(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("sensitive-provider-configuration")
    monkeypatch.setattr(a, "get_gemini_client", lambda: SimpleNamespace(GenerativeModel=fail))
    analysis = a.analyze_results({}, result({"x": [1,2,3]}), "Why?")
    assert not analysis.ai_used and "sensitive-provider" not in analysis.summary
    assert analysis.patterns and "unavailable" in analysis.answer


def test_successful_mock_ai_is_identified_separately_from_configuration(monkeypatch):
    data={"summary":"Mock interpretation", "insights":["A finding"], "recommendations":["Check inputs"], "answer":"Mock answer"}
    fake = SimpleNamespace(GenerativeModel=lambda _: SimpleNamespace(generate_content=lambda *args, **kwargs: SimpleNamespace(text=json.dumps(data))))
    monkeypatch.setattr(a, "get_gemini_client", lambda: fake)
    analysis = a.analyze_results({}, result({"x": [1,2,3]}), "Why?")
    assert analysis.ai_used and analysis.answer == "Mock answer"


def test_every_analysis_route_validates_before_ai(monkeypatch):
    monkeypatch.setattr(a, "get_gemini_client", lambda: pytest.fail("Provider must not be reached"))
    for endpoint in ("/api/analyze", "/api/analyze/ask"):
        response=TestClient(app).post(endpoint,json={"simulation_results":result({"x":[1,None]}),"question":"Why?"})
        assert response.status_code == 400


def test_browser_fallback_matches_api_math_and_safe_markup():
    node = shutil.which("node")
    if not node and Path("/mnt/c/Program Files/nodejs/node.exe").exists():
        node = "/mnt/c/Program Files/nodejs/node.exe"
    if not node:
        pytest.skip("Node is required to verify browser fallback")
    source=(Path(__file__).parents[1]/"static/js/analytics.js").read_text()
    payload = result({"<img src=x onerror=bad>|x": [2,4,8,22], "negative": [-2,-4,-8,-22], "zero": [0]*4}, [0,1,3,10])
    code=source+"\nconst results="+json.dumps(payload)+";\n"+r'''
const App={escapeHtml:s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))};
Analytics.statistics=Analytics.computeLocalStatistics(results);
Analytics.results=results;
const derivative=Analytics.computeDerivatives([0,1,3],{x:[1,2,4]});
const sensitivity=Analytics.computeSensitivity({large:[-1e308,1e308],small:[-1e307,1e307]});
console.log(JSON.stringify({report:Analytics.statistics,derivative,sensitivity,markup:Analytics.renderCorrelationsSection()}));
'''
    completed=subprocess.run([node],input=code,capture_output=True,text=True)
    assert completed.returncode == 0, completed.stderr
    actual=json.loads(completed.stdout)
    expected=a.descriptive_analysis(payload)
    assert actual["report"]["patterns"] == expected["patterns"]
    assert actual["report"]["correlation_pairs"] == expected["correlation_pairs"]
    for name,stats in expected["statistics"].items():
        for key in ("mean","std","time_weighted_mean","total_change","median"):
            assert actual["report"]["statistics"][name][key] == pytest.approx(stats[key])
    assert actual["derivative"]["x"]["velocity"] == [1,1]
    assert actual["derivative"]["x"]["acceleration"] == [0]
    assert actual["sensitivity"]["large"]["relativeContribution"] == pytest.approx(100/1.01)
    assert "<img src=x" not in actual["markup"] and "&lt;img" in actual["markup"]
