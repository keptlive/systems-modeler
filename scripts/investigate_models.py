"""Reproducible full-horizon diagnostics for failed and representative library inputs.

Read-only: writes only the requested report. No model edits or AI provider calls.
Run from repository root with PYTHONPATH=. python scripts/investigate_models.py ...
"""
import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
import time
import urllib.request
from collections import Counter
from pathlib import Path

from app.core.diagnostics import investigate_model, model_hash, source_hashes
from app.core.model import Model
from app.core.simulator import simulate

REPRESENTATIVES = {"sir", "si", "sir-simple", "sales-agency-fit-adjustment", "world2-forrester-original-cla", "classic-world2-population-cla",
                   "sir-epidemic-model-epi", "simple-carbon-cycle-climate", "bank-balance", "population"}
SIR_COMMIT = "21aab02739dc5187bc9564e4d3de14e575905d2f"
SIR_BASE = f"https://raw.githubusercontent.com/SDXorg/test-models/{SIR_COMMIT}/samples/SIR/"
COOKBOOK_COMMIT = "d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4"
SI_SOURCE = f"https://raw.githubusercontent.com/SDXorg/PySD-Cookbook/{COOKBOOK_COMMIT}/source/models/Epidemic/SI.mdl"
ORIGINAL_MODEL_REVISION = "17452ee719b9b5b2cf80935f0a2d1df46dbd2489"


def verify_sir_candidate(path):
    """Test a copy against pinned primary-source output; do not repair the input."""
    raw = path.read_bytes()
    model = Model.model_validate_json(raw)
    fetched = {}
    for filename in ("SIR.mdl", "output.csv"):
        with urllib.request.urlopen(SIR_BASE + filename, timeout=30) as response:
            fetched[filename] = response.read(2_000_001)
        if len(fetched[filename]) > 2_000_000:
            raise ValueError("Unexpected source size")
    mdl = fetched["SIR.mdl"].decode()
    if "Susceptible= INTEG" not in mdl or "Total Population)" not in mdl:
        raise ValueError("Pinned primary source did not match expected initialization; review manually")
    reference = list(csv.DictReader(io.StringIO(fetched["output.csv"].decode(), newline="")))
    candidate = model.model_copy(deep=True)
    stock = next(s for s in candidate.stocks if s.name == "Susceptible")
    previous_equation = stock.equation
    stock.equation = "Total_Population"
    checks = []
    for label, definition in (("current_library_definition", model), ("source_initial_equation_restored_in_copy", candidate)):
        result = simulate(definition)
        # Upstream CSV rounds time labels to six significant figures. At this
        # horizon the largest rounding is 5e-5, far below half a timestep.
        if len(result.time) != len(reference) or any(abs(t - float(row["Time"])) > 5.01e-5 for t, row in zip(result.time, reference)):
            raise ValueError("Reference and model time grids differ; no row-by-row comparison permitted")
        differences = []
        for name in ("Susceptible", "Infectious", "Recovered"):
            actual = result.values[name]
            expected = [float(row[name]) for row in reference]
            scale = max(map(abs, [*actual, *expected]))
            maximum = max(abs(x - y) for x, y in zip(actual, expected))
            differences.append({"stock": name, "maximum_absolute_difference": maximum,
                                "maximum_scaled_difference": maximum / scale if scale else 0,
                                "model_final": actual[-1], "canonical_final": expected[-1]})
        checks.append({"case": label, "normalized_model_sha256": model_hash(definition), "settings": definition.time_settings.model_dump(),
                       "compared_samples": len(result.time), "per_stock": differences})
    if path.read_bytes() != raw:
        raise RuntimeError("Library input changed during primary-source comparison")
    return {"model_id": model.id, "file_sha256": hashlib.sha256(raw).hexdigest(),
            "proposal": {"path": "stocks[name=Susceptible].equation", "before": previous_equation, "after": "Total_Population",
                         "status": "already restored" if previous_equation == "Total_Population" else "candidate tested on a copy; no library mutation"},
            "primary_source_commit": SIR_COMMIT,
            "sources": [{"url": SIR_BASE + name, "sha256": hashlib.sha256(content).hexdigest()} for name, content in fetched.items()],
            "important_source_detail": "The original benchmark starts S=1000,I=5,R=0, so compartment sum=1005 while the infection denominator remains1000. Do not substitute995 to make the parameter equal the compartment sum.",
            "checks": checks, "scientific_validation": "benchmark fidelity only, not real-world epidemiological validation"}


def source_repair_receipt(root):
    """Verify the exact four authorized repairs and retain source-bound evidence."""
    hashes = source_hashes()
    sir = verify_sir_candidate(root / "models/other/sir.json")
    with urllib.request.urlopen(SI_SOURCE, timeout=30) as response:
        si_source = response.read(2_000_001)
    if len(si_source) > 2_000_000:
        raise ValueError("Unexpected SI source size")
    text = " ".join(si_source.decode().split())
    for equation in ("New Reported Cases= Infection Rate", "Susceptible= INTEG ( -Infection Rate, Total Population)",
                     "Cumulative Reported Cases= INTEG ( New Reported Cases, 0)"):
        if equation not in text:
            raise ValueError("Pinned SI source differs from reviewed equations")
    rows = []
    for name, original_hash in (("sir", "3fdfe61a2d85c1b376d99453b556c18ce9ecca1146f55945a5fcbf98f045a1eb"),
                                 ("si", "e0648be3d1d90eb19eeea536859608b75741af7543f8198478e44f0120230e91"),
                                 ("sir-simple", "f7cb06fcdb4683306cfb446678fabe233f5d8debd785a66cb145d4337862f648"),
                                 ("sales-agency-fit-adjustment", "d7c0a0cd4fc1536b9e651eec426fbc67b8b4b3251f9357b6ff8a59700cd65fda")):
        relative = f"models/other/{name}.json"
        original_bytes = subprocess.run(["git", "show", f"{ORIGINAL_MODEL_REVISION}:{relative}"], cwd=root, capture_output=True, check=True).stdout
        if hashlib.sha256(original_bytes).hexdigest() != original_hash:
            raise ValueError(f"Git baseline for {name} no longer matches the reviewed original")
        current_bytes = (root / relative).read_bytes()
        original, current = json.loads(original_bytes), json.loads(current_bytes)
        reversed_repair = json.loads(current_bytes)
        if name in ("sir", "si"):
            next(s for s in reversed_repair["stocks"] if s["name"] == "Susceptible")["equation"] = ""
        if name == "si":
            reversed_repair["flows"] = [flow for flow in reversed_repair["flows"] if flow["name"] != "New_Reported_Cases"]
        if name in ("sir-simple", "sales-agency-fit-adjustment"):
            # Converted auxiliaries keep every original ID and position. Reverse
            # only the approved type/endpoint/equation changes for preservation checks.
            current_by_id = {element["id"]: element for element in [*current["variables"], *current["flows"]]}
            expected_new_ids = {"v11"} if name == "sales-agency-fit-adjustment" else set()
            if set(current_by_id) != {item["id"] for item in original["variables"]} | expected_new_ids:
                raise ValueError("Unexpected element additions or removals")
            expected_flows = ({"infect": ("susceptible", "infectious"), "recover": ("infectious", "recovered"), "report_case": (None, "cumulative_cases")}
                              if name == "sir-simple" else
                              {"Hiring_Good_Fit_Agents": (None, "Sales_Agents_with_Good_Fit"), "Hiring_Poor_Fit_Agents": (None, "Sales_Agents_with_Poor_Fit"),
                               "Turnover_of_Good_Fit_Agents": ("Sales_Agents_with_Good_Fit", None), "Turnover_of_Poor_Fit_Agents": ("Sales_Agents_with_Poor_Fit", None)})
            if {flow["name"]: (flow.get("from_stock"), flow.get("to_stock")) for flow in current["flows"]} != expected_flows:
                raise ValueError("Unexpected flow endpoints")
            if name == "sales-agency-fit-adjustment" and next(v for v in current["variables"] if v["id"] == "v11")["equation"] != "0.2":
                raise ValueError("Unexpected recovered fraction parameter")
            restored = []
            for old in original["variables"]:
                item = dict(current_by_id[old["id"]])
                item.pop("from_stock", None)
                item.pop("to_stock", None)
                if name == "sales-agency-fit-adjustment" and item["name"].startswith("Hiring_"):
                    if item["equation"] != old["equation"].replace("Good Fit Fraction", "Good_Fit_Fraction"):
                        raise ValueError("Unreviewed hiring equation change")
                    item["equation"] = old["equation"]
                restored.append(item)
            reversed_repair["variables"] = restored
            reversed_repair["flows"] = []
            if name == "sir-simple":
                reversed_repair["stocks"] = [s for s in reversed_repair["stocks"] if s["name"] != "cumulative_cases"]
                next(s for s in reversed_repair["stocks"] if s["name"] == "susceptible")["equation"] = ""
        if original != reversed_repair:
            raise ValueError(f"Unreviewed input changes found in {name}")
        rows.append({"file": relative, "old_sha256": original_hash, "new_sha256": hashlib.sha256(current_bytes).hexdigest(),
                     "unrelated_fields_preserved": True})
        cases = []
        for label, data in (("original", original), ("repaired", current)):
            definition = Model.model_validate(data)
            case = {"case": label, "settings": definition.time_settings.model_dump(), "normalized_model_sha256": model_hash(definition)}
            try:
                result = simulate(definition)
                case.update(status="completed", samples=len(result.time),
                            stocks=[{"name": stock.name, "initial": result.values[stock.name][0], "final": result.values[stock.name][-1]} for stock in definition.stocks])
            except Exception as error:
                case.update(status="failed", error=str(error))
            cases.append(case)
        rows[-1]["before_and_after_defaults"] = cases
    si_path = root / "models/other/si.json"
    si = Model.model_validate_json(si_path.read_bytes())
    baseline = simulate(si)
    refined_settings = si.time_settings.model_copy(update={"integration_method": "rk4", "dt": si.time_settings.dt / 2})
    refined = simulate(si, refined_settings)
    expected = [10001 / (1 + 10000 * math.exp(-.35 * 10001 / 10000 * t)) for t in refined.time]
    si_check = {"source_url": SI_SOURCE, "source_sha256": hashlib.sha256(si_source).hexdigest(),
                "baseline_settings": si.time_settings.model_dump(), "baseline_samples": len(baseline.time),
                "maximum_population_conservation_error": max(abs(s + i - 10001) for s, i in zip(baseline.values["Susceptible"], baseline.values["Infected"])),
                "maximum_reporting_identity_error": max(abs(c - (i - 1)) for c, i in zip(baseline.values["Cumulative_Reported_Cases"], baseline.values["Infected"])),
                "independent_analytic_equation": "I(t)=10001/(1+10000*exp(-0.35*10001/10000*t)); S=10001-I; cumulative reported=I-1",
                "analytic_check_settings": refined_settings.model_dump(), "analytic_check_samples": len(refined.time),
                "maximum_scaled_infected_error_against_analytic": max(abs(i - expected_i) for i, expected_i in zip(refined.values["Infected"], expected)) / 10001}
    cookbook_checks = []
    fixture_path = root / "tests/fixtures/cookbook-source-reference.json"
    fixtures = json.loads(fixture_path.read_text())["models"]
    for name in ("sir-simple", "sales-agency-fit-adjustment"):
        evidence = fixtures[name]
        with urllib.request.urlopen(evidence["source_url"], timeout=30) as response:
            content = response.read(2_000_001)
        if hashlib.sha256(content).hexdigest() != evidence["source_sha256"]:
            raise ValueError("Pinned Cookbook source hash changed")
        model = Model.model_validate_json((root / f"models/other/{name}.json").read_bytes())
        settings = model.time_settings.model_copy(update={"integration_method": "rk4", "dt": .03125 if name == "sir-simple" else model.time_settings.dt})
        checked = simulate(model, settings)
        per_series = {}
        for point in evidence["reference"]:
            index = round((point["time"] - settings.start) / settings.dt)
            if checked.time[index] != point["time"]:
                raise ValueError("Independent reference times differ")
            for series, expected in point.items():
                if series != "time":
                    per_series[series] = max(per_series.get(series, 0), abs(checked.values[series][index] - expected))
        cookbook_checks.append({"model_id": name, "source_url": evidence["source_url"], "source_sha256": evidence["source_sha256"],
                                "independent_reference_method": evidence["independent_reference_method"],
                                "checked_settings": settings.model_dump(), "reference_times": [point["time"] for point in evidence["reference"]],
                                "maximum_absolute_difference_at_reference_times": per_series,
                                "reference_fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest()})
    if hashes != source_hashes():
        raise RuntimeError("Engine changed during repair verification")
    return {"scope": "Four authorized source-backed repairs only; no source mutation in this verification script",
            "original_git_revision": ORIGINAL_MODEL_REVISION,
            "engine_sha256": hashes, "models": rows, "sir_canonical_comparison": sir, "si_primary_source_and_analytic_check": si_check,
            "cookbook_independent_reference_checks": cookbook_checks,
            "scientific_validation": "Source fidelity and numerical examples only, not real-world calibration"}


def summarize_report(report):
    """Compact findings without treating a completed alternative as a repair."""
    categories, runs = Counter(), Counter()
    alternatives, domains, invariants = [], [], []
    for row in report["models"]:
        default = row.get("default_method_investigation", {})
        evidence = default.get("equation_evidence", {})
        for key in ("undefined_symbols", "syntax", "ambiguous_names", "stochastic"):
            if evidence.get(key): categories[key] += 1
        if any("Unknown function:" in issue["message"] for issue in default.get("input_issues", [])):
            categories["undefined_named_functions"] += 1
        cases = (default, row.get("alternative_rk4_investigation", {}))
        completed, leads = [], []
        for case in cases:
            for run in case.get("runs", []):
                runs[run["status"]] += 1
                settings = {"method": run["settings"]["integration_method"], "dt": run["settings"]["dt"]}
                if run["status"] == "completed": completed.append(settings)
                leads.extend({**settings, **lead} for lead in run.get("domain_leads", []))
                invariants.extend({"id": row["id"], **settings, **test} for test in run.get("conservation", []) if test["max_drift_scaled_by_largest_stock"] > 1e-10)
        if default.get("runs") and default["runs"][0]["status"] != "completed" and completed:
            alternatives.append({"id": row["id"], "successful_full_horizon_grids": completed})
        if leads: domains.append({"id": row["id"], "leads": leads})
    return {**{key: value for key, value in report.items() if key not in ("models", "engine_sha256", "primary_source_candidates")},
            "static_category_counts": dict(categories), "run_counts": dict(runs),
            "refinement_or_method_recoveries": alternatives, "finite_run_domain_lead_models": domains,
            "closed_transfer_invariant_drift_leads": invariants,
            "interpretation": "Alternate-grid completion is numerical evidence only. Domain, convergence and source fidelity still require review; never change defaults automatically."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", default="operations/library-full.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output", help="Optional compact findings generated from the same exact report")
    parser.add_argument("--model", action="append", dest="models", help="Limit to these IDs; repeat for multiple models")
    parser.add_argument("--max-runs", type=int, default=3, choices=(1, 2, 3))
    parser.add_argument("--also-rk4", action="store_true", help="Separate bounded investigation using RK4 for originally Euler models; no settings are saved")
    parser.add_argument("--verify-sir-source", action="store_true", help="Fetch pinned SDX primary source and canonical output, then test an unsaved repair candidate")
    parser.add_argument("--repair-receipt", help="Write an additional receipt verifying the four authorized source-backed model repairs against their Git originals")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    audit_path = Path(args.audit)
    audit_bytes = audit_path.read_bytes()
    audit = json.loads(audit_bytes)
    selected = set(args.models or [])
    if not args.models:
        selected = {row["id"] for row in audit["models"] if row["status"] == "failed"} | REPRESENTATIVES
    hashes = source_hashes()
    rows, started = [], time.monotonic()
    for entry in sorted(audit["models"], key=lambda row: row["id"]):
        if entry["id"] not in selected:
            continue
        path = root / entry["file"]
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != entry["sha256"]:
            raise RuntimeError(f"Input changed since audit: {entry['file']}")
        row = {"id": entry["id"], "file": entry["file"], "file_sha256": digest, "audited_default_status": entry["status"]}
        try:
            model = Model.model_validate_json(raw)
            row["default_method_investigation"] = investigate_model(model, args.max_runs)
            if args.also_rk4 and model.time_settings.integration_method != "rk4" and not row["default_method_investigation"]["equation_evidence"]["stochastic"]:
                alternative = model.model_copy(deep=True)
                alternative.time_settings.integration_method = "rk4"
                row["alternative_rk4_investigation"] = investigate_model(alternative, args.max_runs)
        except Exception as error:
            row["definition_error"] = str(error)
        if path.read_bytes() != raw:
            raise RuntimeError(f"Input changed during investigation: {entry['file']}")
        rows.append(row)
        print(json.dumps({"investigated": len(rows), "id": row["id"]}), flush=True)
    if hashes != source_hashes() or any(inv.get("source_changed") for row in rows for key, inv in row.items() if key.endswith("investigation")):
        raise RuntimeError("Engine changed during the investigation; rerun against frozen source")
    report = {"scope": "Failed library definitions plus explicit finite-run review representatives; original equations preserved",
              "engine_sha256": hashes, "audit_sha256": hashlib.sha256(audit_bytes).hexdigest(),
              "scientific_validation": "not established", "seconds": round(time.monotonic() - started, 2),
              "models_investigated": len(rows),
              "default_assessments": dict(Counter(row.get("default_method_investigation", {}).get("timestep_assessment", {}).get("status", "definition_error") for row in rows)),
              "models": rows}
    if args.verify_sir_source:
        sir_entry = next(row for row in audit["models"] if row["id"] == "sir")
        report["primary_source_candidates"] = [verify_sir_candidate(root / sir_entry["file"])]
    if args.repair_receipt:
        Path(args.repair_receipt).write_text(json.dumps(source_repair_receipt(root), indent=2, allow_nan=False))
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    if args.summary_output:
        Path(args.summary_output).write_text(json.dumps(summarize_report(report), indent=2, ensure_ascii=False, allow_nan=False))
    print(json.dumps({key: value for key, value in report.items() if key not in ("models", "engine_sha256", "primary_source_candidates")}, indent=2))


if __name__ == "__main__":
    main()
