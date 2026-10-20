"""Evidence for every failed model, separating engine coverage from model assumptions.

Static evidence is a diagnostic lead, not a scientific verdict. Inputs are never edited.
"""
import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from app.core.equations import preprocess_equation, SAFE_FUNCTIONS, CONTEXT_FUNCTIONS, SAFE_CONSTANTS, EquationError, decode_identifier, canonical_name

parser = argparse.ArgumentParser()
parser.add_argument("--audit", required=True)
parser.add_argument("--previous")
parser.add_argument("--output", required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
audit = json.loads(Path(args.audit).read_text())
latest = {m["id"]: m for m in audit["models"]}
previous = json.loads(Path(args.previous).read_text()) if args.previous else audit
candidate_ids = {m["id"] for m in previous["models"] if m["status"] == "failed"}
candidate_ids.update(m["id"] for m in audit["models"] if m["status"] == "failed")

def canonical(name):
    return canonical_name(name)

rows = []
for mid in sorted(candidate_ids):
    entry = latest.get(mid)
    if entry is None:
        continue
    path = root / entry["file"]
    raw = path.read_bytes()
    data = json.loads(raw)
    elements = [*data.get("stocks", []), *data.get("flows", []), *data.get("variables", [])]
    names = [canonical(e["name"]) for e in elements]
    defined = set(names) | {canonical(n) for n in SAFE_CONSTANTS} | {"time", "dt", "time_step"}
    table_names = {canonical(t["name"]) for t in data.get("tables", [])}
    defined |= table_names
    known_functions = {n.casefold() for n in SAFE_FUNCTIONS} | {n.casefold() for n in CONTEXT_FUNCTIONS}
    missing, unsupported, syntax = [], [], []
    for element in elements:
        equation = str(element.get("equation", ""))
        if not equation:
            continue
        try:
            tree = ast.parse(preprocess_equation(equation), mode="eval")
        except (SyntaxError, EquationError) as exc:
            syntax.append({"element": element["name"], "equation": equation, "error": str(exc)})
            continue
        calls = {decode_identifier(n.func.id) for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        refs = {decode_identifier(n.id) for n in ast.walk(tree) if isinstance(n, ast.Name)} - calls
        absent = sorted(n for n in refs if canonical(n) not in defined)
        if absent:
            missing.append({"element": element["name"], "equation": equation, "undefined_symbols": absent})
        unknown_calls = sorted(n for n in calls if n.casefold() not in known_functions and canonical(n) not in table_names)
        if unknown_calls:
            unsupported.append({"element": element["name"], "equation": equation, "functions": unknown_calls})
    duplicate = sorted(name for name, count in Counter(names).items() if count > 1)
    findings = []
    if entry["status"] == "passed":
        findings.append("now_completes_after_engine_repairs")
    else:
        if unsupported: findings.append("engine_function_coverage_or_nonstandard_function")
        if syntax: findings.append("engine_syntax_coverage_or_malformed_expression")
        if missing: findings.append("unresolved_symbols_in_model_definition")
        if duplicate: findings.append("ambiguous_element_names")
        if "exceeds" in entry.get("error", ""): findings.append("configured_workload_limit")
        if not findings: findings.append("numerical_domain_instability_or_dependency_cycle")
    rows.append({"id": mid, "file": entry["file"], "sha256": hashlib.sha256(raw).hexdigest(),
                 "current_numerical_status": entry["status"], "current_error": entry.get("error", ""),
                 "findings": findings, "undefined_symbol_evidence": missing,
                 "function_evidence": unsupported, "syntax_evidence": syntax,
                 "ambiguous_names": duplicate,
                 "interpretation": "Diagnostic evidence only; missing symbols may require restoring an omitted equation, not inventing one. A completed run does not establish scientific validity."})
report = {"models_investigated": len(rows),
          "findings": dict(Counter(f for row in rows for f in row["findings"])),
          "engine_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted((root / "app" / "core").glob("*.py"))},
          "models": rows}
Path(args.output).write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k not in ("models", "engine_sha256")}, indent=2))
