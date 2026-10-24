"""Evidence accounting checks, not correctness claims from corpus completion."""
import json
from pathlib import Path
import subprocess

from app.core.equations import SAFE_FUNCTIONS, CONTEXT_FUNCTIONS
from scripts.audit_capability_coverage import (
    bound_audit_status, execute_bounded, reference_evidence,
    scan_equation, summarize, supported_functions, tracked_models, model_expressions,
)

ROOT = Path(__file__).resolve().parents[1]


def test_inventory_includes_every_function_and_alias():
    assert set(supported_functions()) == {n.upper() for n in SAFE_FUNCTIONS} | CONTEXT_FUNCTIONS
    assert {"SMTH1", "SMTH3", "SMTHN", "DELAYN", "DELAY", "NORMAL", "RANDOM"} <= set(supported_functions())


def test_calls_are_parsed_not_counted_from_comments_or_identifier_strings():
    result = scan_equation('SIN(TIME) + "COS(looks_like_a_call)" { TAN(TIME) }')
    assert result["calls"] == {"SIN": 1}
    assert result["parse_error"] is None


def test_stock_initialization_expressions_are_inventoried():
    model = {"stocks": [{"id": "s", "equation": "", "initial_value": "SIN(1)"}],
             "description": "COS(1) is prose"}
    assert list(model_expressions(model)) == [("s", "equation", ""), ("s", "initial_value", "SIN(1)")]


def test_dialect_alias_and_foreign_function_are_distinguished():
    result = scan_equation("IF THEN ELSE(1, SMTH1(2,3), FOREIGN_FUNC(4))")
    assert result["calls"] == {"IF_THEN_ELSE": 1, "SMTH1": 1}
    assert result["unknown_calls"] == {"FOREIGN_FUNC": 1}
    assert scan_equation("SIN(")["parse_error"]


def test_named_graphical_function_takes_precedence_like_runtime():
    result = scan_equation("SIN(TIME) + My_Table(TIME)", ["SIN", "My Table"])
    assert result["calls"] == {}
    assert result["table_calls"] == {"SIN": 1, "My_Table": 1}


def test_historical_results_require_both_model_and_engine_hash_binding():
    row = {"sha256": "new"}
    assert bound_audit_status(row, {"sha256": "old", "status": "passed"}, True) == "stale_model"
    assert bound_audit_status(row, {"sha256": "new", "status": "passed"}, False) == "stale_engine"
    assert bound_audit_status(row, {"sha256": "new", "status": "failed"}, True) == "failed"
    assert bound_audit_status(row, None, True) == "missing"


def raw_model(equation):
    return json.dumps({"name": "Unsaved capability probe", "variables": [
        {"id": "v", "name": "Value", "equation": equation}],
        "time_settings": {"start": 0, "end": 1, "dt": .25}}).encode()


def test_invocation_tracing_does_not_claim_unselected_lazy_branch_executed():
    result = execute_bounded(raw_model("IF(0, SIN(TIME), COS(TIME))"), timeout=10)
    assert result["status"] == "completed", result
    assert result["invocations"]["IF"] > 0
    assert result["invocations"]["COS"] > 0
    assert "SIN" not in result["invocations"]


def test_failing_corpus_run_stays_a_failure_not_a_correctness_pass():
    result = execute_bounded(raw_model("SQRT(-1)"), timeout=10)
    assert result["status"] == "failed"
    assert result["error"]


def test_large_failure_evidence_does_not_deadlock_worker_pipe():
    model = {"name": "Unsaved failure probe", "variables": [
        {"id": f"v{i}", "name": f"Value{i}", "equation": f"UndefinedVariable{i}"}
        for i in range(120)]}
    result = execute_bounded(json.dumps(model).encode(), timeout=10)
    assert result["status"] == "failed", result
    assert len(result["error"]) > 8192


def test_absent_present_historical_and_invoked_coverage_are_separate():
    rows = [{"calls": {"SIN": 2}, "audit_status": "failed",
             "execution": {"status": "completed", "invocations": {"SIN": 3}}},
            {"calls": {"SIN": 1}, "audit_status": "stale_engine",
             "execution": {"status": "not_executed", "invocations": {}}}]
    result = summarize(rows, ["SIN", "COS"])
    assert result["SIN"]["containing_models"] == 2
    assert result["SIN"]["historical_failed_models"] == 1
    assert result["SIN"]["unbound_historical_models"] == 1
    assert result["SIN"]["runtime_invoked_models"] == 1
    assert result["SIN"]["runtime_completed_models"] == 1
    assert result["COS"]["absent_from_parsed_corpus"]


def test_corpus_scope_is_tracked_and_reference_contract_is_portable():
    paths = tracked_models(ROOT)
    manifest = json.loads((ROOT / 'operations/library-curation.json').read_text())
    assert len(paths) == manifest['active_count']
    assert len(paths) + len(manifest['retired']) == manifest['baseline_count']
    assert len(set(paths)) == len(paths)
    evidence = reference_evidence(ROOT, ROOT / "tests/fixtures/corpus-contract-v15.json")
    assert evidence["case_count"] == 8
    assert evidence["status"] == "not_executed"
    assert all(len(h) == 64 for h in evidence["files_sha256"].values())
    contract = json.loads((ROOT / "tests/fixtures/corpus-contract-v15.json").read_text())
    for case in contract["cases"]:
        assert case["source_fidelity"] and case["independent_expectation"]
        assert case["source_url"].startswith("https://")


def test_reference_failure_is_retained(monkeypatch):
    def failed(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 1, "independent check failed", "")
    monkeypatch.setattr(subprocess, "run", failed)
    evidence = reference_evidence(ROOT, ROOT / "tests/fixtures/corpus-contract-v15.json", execute=True)
    assert evidence["status"] == "failed"
    assert evidence["returncode"] == 1
    assert "failed" in evidence["output"]


def test_reference_timeout_is_not_a_pass(monkeypatch):
    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
    monkeypatch.setattr(subprocess, "run", timed_out)
    evidence = reference_evidence(ROOT, ROOT / "tests/fixtures/corpus-contract-v15.json", execute=True)
    assert evidence["status"] == "timeout"
