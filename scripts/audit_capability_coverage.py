"""Read-only corpus coverage, bounded execution, and independent test evidence.

Presence, an actually invoked function, numerical completion, independent
correctness checks and scientific source fidelity are deliberately separate.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
import multiprocessing
from pathlib import Path
from queue import Empty
import subprocess
import sys
import time

from app.core.equations import (
    SAFE_FUNCTIONS, CONTEXT_FUNCTIONS, STATEFUL_ALIASES,
    SafeEvaluator, canonical_name, decode_identifier, preprocess_equation,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "tests/fixtures/corpus-contract-v15.json"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def engine_hashes(root):
    return {p.relative_to(root).as_posix(): digest(p.read_bytes())
            for p in sorted((root / "app/core").glob("*.py"))}


def supported_functions():
    # Preserve alias spellings as separately auditable capabilities.
    return sorted({n.upper() for n in SAFE_FUNCTIONS} | set(CONTEXT_FUNCTIONS))


def scan_equation(equation, table_names=()):
    """AST inspection after the actual dialect parser; never regex-count comments."""
    if not equation or not equation.strip():
        return {"calls": {}, "table_calls": {}, "unknown_calls": {}, "parse_error": None}
    try:
        tree = ast.parse(preprocess_equation(equation), mode="eval")
    except Exception as exc:
        return {"calls": {}, "table_calls": {}, "unknown_calls": {}, "parse_error": str(exc)}
    supported = set(supported_functions())
    tables = {canonical_name(n) for n in table_names}
    calls, graphical, unknown = Counter(), Counter(), Counter()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = decode_identifier(node.func.id)
            # Table names take precedence over builtins in the evaluator.
            if canonical_name(name) in tables:
                graphical[name] += 1
            elif name.upper() in supported:
                calls[name.upper()] += 1
            else:
                unknown[name] += 1
    return {"calls": dict(calls), "table_calls": dict(graphical),
            "unknown_calls": dict(unknown), "parse_error": None}


def tracked_models(root):
    raw = subprocess.check_output(["git", "ls-files", "-z", "models"], cwd=root)
    return sorted(root / name for name in raw.decode().split("\0")
                  if name.endswith(".json"))


def model_expressions(model):
    """Include initialization expressions, not prose descriptions or connectors."""
    for kind in ("stocks", "flows", "variables"):
        for element in model.get(kind, []):
            yield element.get("id"), "equation", str(element.get("equation", ""))
            if kind == "stocks" and isinstance(element.get("initial_value"), str):
                yield element.get("id"), "initial_value", element["initial_value"]


def bound_audit_status(row, previous, engine_matches):
    if not previous:
        return "missing"
    if previous.get("sha256") != row["sha256"]:
        return "stale_model"
    if not engine_matches:
        return "stale_engine"
    return previous.get("status", "unknown")


def _run_model(raw, random_seed, queue):
    # Runs in a disposable child process. Record entry to calls, including a
    # failing call, rather than claiming every syntactic branch was exercised.
    from unittest.mock import patch
    from app.core.model import Model, TimeSettings
    from app.core.simulator import simulate
    counts = Counter()
    original = SafeEvaluator.visit_Call

    def observed(self, node):
        if isinstance(node.func, ast.Name):
            name = decode_identifier(node.func.id)
            if self._table_name(name) is not None:
                counts["GRAPHICAL_FUNCTION"] += 1
            else:
                counts[name.upper()] += 1
        return original(self, node)

    try:
        model = Model.model_validate_json(raw)
        settings = model.time_settings
        if settings.random_seed is None:
            settings = TimeSettings(**{**settings.model_dump(), "random_seed": random_seed})
        with patch.object(SafeEvaluator, "visit_Call", observed):
            result = simulate(model, settings)
        answer = {"status": "completed", "points": len(result.time)}
    except Exception as exc:
        answer = {"status": "failed", "error": str(exc)}
    answer["invocations"] = dict(counts)
    queue.put(answer)


def execute_bounded(raw, timeout, random_seed=42):
    # Spawn works on Windows and Linux; Linux fork avoids importing the entire
    # engine once per model. A process cannot outlive its explicit time budget.
    methods = multiprocessing.get_all_start_methods()
    if "fork" in methods:
        # Import once in the parent; forked workers inherit the same read-only
        # modules rather than paying Pydantic/simulator import cost 1,078 times.
        import app.core.model
        import app.core.simulator
        import unittest.mock
    context = multiprocessing.get_context("fork" if "fork" in methods else "spawn")
    queue = context.Queue()
    process = context.Process(target=_run_model, args=(raw, random_seed, queue))
    started = time.monotonic()
    process.start()
    try:
        # Drain evidence before joining: a large failure diagnostic can fill
        # the queue pipe and otherwise make a finished worker appear hung.
        answer = queue.get(timeout=timeout)
    except Empty:
        if process.is_alive():
            answer = {"status": "timeout", "invocations": {},
                      "error": "Per-model execution budget exceeded; invocation evidence unavailable"}
        else:
            answer = {"status": "worker_error", "invocations": {},
                      "error": f"Worker exited without evidence (exit code {process.exitcode})"}
    finally:
        process.join(.1)
        if process.is_alive():
            process.terminate()
            process.join(2)
        if process.is_alive():
            process.kill()
            process.join()
    queue.close()
    answer["seconds"] = round(time.monotonic() - started, 4)
    return answer


def summarize(rows, names):
    summary = {}
    for name in names:
        containing = [r for r in rows if r["calls"].get(name)]
        invoked = [r for r in rows if r["execution"].get("invocations", {}).get(name)]
        summary[name] = {
            "alias_target": STATEFUL_ALIASES.get(name),
            "static_call_sites": sum(r["calls"].get(name, 0) for r in containing),
            "containing_models": len(containing),
            "historical_completed_models": sum(r["audit_status"] == "passed" for r in containing),
            "historical_failed_models": sum(r["audit_status"] == "failed" for r in containing),
            "unbound_historical_models": sum(r["audit_status"] not in ("passed", "failed") for r in containing),
            "runtime_invoked_models": len(invoked),
            "runtime_completed_models": sum(r["execution"]["status"] == "completed" for r in invoked),
            "runtime_failed_models": sum(r["execution"]["status"] == "failed" for r in invoked),
            "absent_from_parsed_corpus": not containing,
        }
    return summary


def reference_evidence(root, contract_path, execute=False, timeout=180):
    contract = json.loads(contract_path.read_text())
    selectors = sorted({s for c in contract["cases"] for s in c["pytest_selectors"]})
    paths = sorted({c["model"] for c in contract["cases"]} |
                   {s.split("::")[0] for s in selectors} |
                   set(contract.get("evidence_files", [])))
    evidence = {"contract_sha256": digest(contract_path.read_bytes()),
                "case_count": len(contract["cases"]), "pytest_selectors": selectors,
                "files_sha256": {name: digest((root / name).read_bytes()) for name in paths},
                "status": "not_executed", "scope": contract["scope"]}
    if execute:
        try:
            run = subprocess.run([sys.executable, "-m", "pytest", "-q", *selectors],
                                 cwd=root, capture_output=True, text=True, timeout=timeout)
            evidence.update(status="passed" if run.returncode == 0 else "failed",
                            returncode=run.returncode, output=run.stdout + run.stderr)
        except subprocess.TimeoutExpired:
            evidence.update(status="timeout", output="Independent reference-check budget exceeded")
    return evidence


def build_report(root, audit_path=None, execute=False, limit=1078, timeout=5,
                 random_seed=42, references=False, contract_path=None):
    before = engine_hashes(root)
    producer_hash = digest(Path(__file__).read_bytes())
    audit = json.loads(audit_path.read_text()) if audit_path else {}
    historical = {m["file"]: m for m in audit.get("models", [])}
    engine_matches = bool(audit) and audit.get("engine_sha256") == before
    paths = tracked_models(root)
    rows = []
    for index, path in enumerate(paths):
        raw = path.read_bytes()
        row = {"file": path.relative_to(root).as_posix(), "sha256": digest(raw),
               "calls": {}, "table_calls": {}, "unknown_calls": {}, "parse_errors": [],
               "execution": {"status": "not_executed", "invocations": {}}}
        try:
            model = json.loads(raw)
            tables = [t["name"] for t in model.get("tables", [])]
            row["id"] = model.get("id")
            for element_id, field, equation in model_expressions(model):
                scanned = scan_equation(equation, tables)
                for key in ("calls", "table_calls", "unknown_calls"):
                    row[key] = dict(Counter(row[key]) + Counter(scanned[key]))
                if scanned["parse_error"]:
                    row["parse_errors"].append({"element_id": element_id, "field": field,
                                                "error": scanned["parse_error"]})
        except Exception as exc:
            row["parse_errors"].append({"error": str(exc)})
        row["audit_status"] = bound_audit_status(row, historical.get(row["file"]), engine_matches)
        if execute and index < limit:
            row["execution"] = execute_bounded(raw, timeout, random_seed)
        rows.append(row)
    reference = reference_evidence(root, contract_path or CONTRACT, references)
    after = engine_hashes(root)
    models_unchanged = all(digest((root / row["file"]).read_bytes()) == row["sha256"] for row in rows)
    return {
        "version": "1.5 corpus test contract", "scope": "All Git-tracked model JSONs; no model edits",
        "producer_sha256": producer_hash,
        "scientific_validation": "Not established. Presence and numerical completion are not correctness.",
        "engine_sha256": before, "engine_unchanged_during_run": before == after,
        "models_unchanged_during_run": models_unchanged,
        "evidence_valid_for_engine_snapshot": before == after and models_unchanged,
        "historical_audit": {"sha256": digest(audit_path.read_bytes()) if audit_path else None,
                             "engine_matches": engine_matches,
                             "meaning": "Historical outcomes bind only when model and entire engine hashes match"},
        "execution_budget": {"enabled": execute, "limit": limit, "per_model_seconds": timeout,
                             "fallback_random_seed": random_seed,
                             "unselected_models_remain_in_report": True},
        "counts": {"models": len(rows), "historical": dict(Counter(r["audit_status"] for r in rows)),
                   "execution": dict(Counter(r["execution"]["status"] for r in rows)),
                   "models_with_unknown_calls": sum(bool(r["unknown_calls"]) for r in rows),
                   "models_with_parse_errors": sum(bool(r["parse_errors"]) for r in rows)},
        "coverage": summarize(rows, supported_functions()),
        "unknown_calls": dict(sum((Counter(r["unknown_calls"]) for r in rows), Counter())),
        "unknown_call_interpretation": "Unrecognized spelling or foreign dialect candidate, not proof of an engine implementation defect",
        "trusted_reference_checks": reference, "models": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--execute", action="store_true", help="Run selected complete defaults with function invocation tracing")
    parser.add_argument("--limit", type=int, default=1078)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--reference-checks", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.limit <= 10000 or not 0 < args.timeout <= 60:
        parser.error("limit must be 0..10000 and timeout must be >0..60 seconds")
    report = build_report(ROOT, args.audit, args.execute, args.limit, args.timeout,
                          args.random_seed, args.reference_checks)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k in
                      ("counts", "engine_unchanged_during_run", "evidence_valid_for_engine_snapshot")}, indent=2))
    print("Independent reference checks:", report["trusted_reference_checks"]["status"])
    # A legacy failure is an expected diagnostic outcome, retained in the report.
    # Infrastructure drift or a trusted reference failure is a failed check.
    if not report["evidence_valid_for_engine_snapshot"] or report["trusted_reference_checks"]["status"] in ("failed", "timeout"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
