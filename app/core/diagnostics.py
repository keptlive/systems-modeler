"""Bounded, read-only numerical/model-input investigation shared by REST and MCP.

Every claim describes the supplied equations and checked grids. No equation repair,
scientific validation or hidden time-horizon reduction is performed here.
"""
import ast
import bisect
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from app.core.equations import (SAFE_CONSTANTS, canonical_name, decode_identifier,
                                equation_features, get_equation_variables, preprocess_equation)
from app.core.model import Model, TimeSettings
from app.core.limits import MAX_INTERVALS, MAX_RETAINED_VALUES, MAX_WORK_UNITS
from app.core.simulator import simulate
from app.core.failure_diagnostics import failure_payload
from app.core.validation import inspect_inputs

CORE_FILES = ("model.py", "simulator.py", "integration.py", "equations.py", "limits.py", "failure_diagnostics.py", "adaptive.py", "reports.py")
MAX_RUNS = 3
MAX_ELEMENT_INTERVALS_PER_RUN = MAX_WORK_UNITS


def source_hashes():
    root = Path(__file__).parent
    return {"app/core/" + name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in CORE_FILES}


def model_hash(model):
    payload = model.model_dump(mode="json", exclude={"created_at", "updated_at"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _finite(value):
    return float(value) if math.isfinite(value) else None


def equation_evidence(model):
    """Find unresolved names, syntax and sensitive operations without guessing fixes."""
    elements = [*model.stocks, *model.flows, *model.variables]
    originals = {canonical_name(e.name): e.name for e in elements}
    defined = set(originals) | {canonical_name(n) for n in SAFE_CONSTANTS} | {"time", "dt", "time_step"}
    table_names = {canonical_name(t.name) for t in model.tables}
    missing, domains, syntax, functions = [], [], [], set()
    stochastic, references_time_step = False, False
    for element in elements:
        equation = element.equation
        if not equation.strip():
            continue
        try:
            tree = ast.parse(preprocess_equation(equation), mode="eval")
        except (SyntaxError, ValueError, RecursionError) as error:
            syntax.append({"element": element.name, "equation": equation, "error": str(error)})
            continue
        except Exception as error:
            # Preprocessor EquationError is a diagnostic, not a reason to lose
            # the rest of the report for an invalid library definition.
            syntax.append({"element": element.name, "equation": equation, "error": str(error)})
            continue
        calls = {decode_identifier(n.func.id).upper() for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        references_time_step = references_time_step or any(
            canonical_name(decode_identifier(node.id)) in {"dt", "time_step"}
            for node in ast.walk(tree) if isinstance(node, ast.Name))
        functions.update(calls)
        try:
            stochastic = stochastic or bool(equation_features(equation, [t.name for t in model.tables])["random_calls"])
        except Exception as error:
            syntax.append({"element": element.name, "equation": equation, "error": str(error), "stage": "engine_feature_check"})
        absent = sorted(n for n in get_equation_variables(equation) if canonical_name(n) not in defined and canonical_name(n) not in table_names)
        if absent:
            missing.append({"element": element.name, "equation": equation, "undefined_symbols": absent})
        operations = sorted(calls & {"LOG", "LN", "LOG10", "SQRT", "ASIN", "ACOS", "POWER", "EXP"})
        if any(isinstance(n, ast.Div) for n in ast.walk(tree)):
            operations.append("division")
        if any(isinstance(n, ast.Pow) for n in ast.walk(tree)):
            operations.append("power")
        if operations:
            domains.append({"element": element.name, "equation": equation, "operations_to_review": operations})
    duplicates = sorted(n for n, count in Counter(canonical_name(e.name) for e in elements).items() if count > 1)
    return {"undefined_symbols": missing, "syntax": syntax, "ambiguous_names": duplicates,
            "domain_sensitive_equations": domains, "called_functions": sorted(functions),
            "stochastic": stochastic,
            "references_time_step": references_time_step,
            "stateful": any(name.startswith(("DELAY", "SMOOTH", "SMTH")) for name in functions)}


def closed_stock_components(model):
    """Topological sums only; physical units and source intent remain unverified."""
    refs = {ref: s.name for s in model.stocks for ref in (s.id, s.name)}
    neighbors = {s.name: set() for s in model.stocks}
    exposed, connected = set(), set()
    for flow in model.flows:
        start, end = refs.get(flow.from_stock), refs.get(flow.to_stock)
        if start: connected.add(start)
        if end: connected.add(end)
        if start and end:
            neighbors[start].add(end)
            neighbors[end].add(start)
        elif start or end:
            exposed.add(start or end)
    groups, seen = [], set()
    for stock in model.stocks:
        if stock.name in seen:
            continue
        pending, group = [stock.name], set()
        while pending:
            name = pending.pop()
            if name in group:
                continue
            group.add(name)
            pending.extend(neighbors[name] - group)
        seen.update(group)
        if not group & exposed:
            groups.append({"stocks": sorted(group), "unconnected": not bool(group & connected)})
    return groups


def conservation_evidence(model, result):
    reports = []
    for group in closed_stock_components(model):
        series = [result.values[name] for name in group["stocks"]]
        scale = max((abs(v) for values in series for v in values), default=0)
        totals = [math.fsum(values[i] / scale for values in series) if scale else 0.0 for i in range(len(result.time))]
        drift = max((abs(v - totals[0]) for v in totals), default=0)
        reports.append({**group, "initial_total": _finite(scale * totals[0]), "final_total": _finite(scale * totals[-1]),
                        "max_absolute_drift": _finite(scale * drift), "max_drift_scaled_by_largest_stock": drift,
                        "interpretation": "Algebraic closed-transfer sum; dimensional/physical conservation is not established"})
    return reports


def domain_evidence(model, result):
    evidence = []
    for stock in model.stocks:
        values = result.values[stock.name]
        negatives = [i for i, value in enumerate(values) if value < 0]
        if negatives:
            evidence.append({"code": "negative_stock_values", "stock": stock.name, "minimum": min(values),
                             "first_negative_time": result.time[negatives[0]],
                             "interpretation": "Review source domain: signed stocks can be intentional; no clamping applied"})
        if "fraction" in canonical_name(stock.name) and any(v < 0 or v > 1 for v in values):
            evidence.append({"code": "fraction_name_outside_zero_one", "stock": stock.name, "minimum": min(values), "maximum": max(values),
                             "interpretation": "Name-based review lead only; verify units and intended bounds with the source"})
    unconnected = [group["stocks"] for group in closed_stock_components(model) if group["unconnected"]]
    if unconnected:
        evidence.append({"code": "stocks_without_attached_flows", "stocks": unconnected,
                         "interpretation": "These stocks remain constant after initialization; confirm that dynamics were not lost in transcription"})
    return evidence


def compare_runs(coarse, fine, model):
    """Compare full stock trajectories at coarse times via linear interpolation."""
    differences = []
    for stock in model.stocks:
        c, f = coarse.values[stock.name], fine.values[stock.name]
        scale = max((abs(value) for value in [*c, *f]), default=0)
        normalized_c = [v / scale for v in c] if scale else [0.0] * len(c)
        normalized_f = [v / scale for v in f] if scale else [0.0] * len(f)
        deltas = []
        for time, value in zip(coarse.time, normalized_c):
            index = bisect.bisect_left(fine.time, time)
            if index == 0:
                other = normalized_f[0]
            elif index == len(fine.time):
                other = normalized_f[-1]
            elif fine.time[index] == time:
                other = normalized_f[index]
            else:
                weight = (time - fine.time[index - 1]) / (fine.time[index] - fine.time[index - 1])
                other = (1 - weight) * normalized_f[index - 1] + weight * normalized_f[index]
            deltas.append(abs(value - other))
        maximum = max(deltas, default=0)
        differences.append({"stock": stock.name, "scale": scale, "max_scaled_difference": maximum,
                            "max_absolute_difference": _finite(scale * maximum),
                            "final_scaled_difference": abs(normalized_c[-1] - normalized_f[-1]),
                            "compared_samples": len(c)})
    return {"per_stock": differences, "maximum_scaled_stock_difference": max((d["max_scaled_difference"] for d in differences), default=0),
            "comparison": "Entire horizon; refined trace interpolated linearly onto coarse sample times; scale is largest absolute stock value across both runs"}


def investigate_model(model: Model, max_runs: int = 3) -> dict:
    """Check default, half and quarter dt within <=3 engine-bounded runs.

    No provider, storage write or network call occurs. max_runs is never an
    invitation to shorten a horizon or exceed the simulator's individual limits.
    """
    if isinstance(max_runs, bool) or not isinstance(max_runs, int) or not 1 <= max_runs <= MAX_RUNS:
        raise ValueError("max_runs must be an integer between 1 and 3")
    hashes = source_hashes()
    static = inspect_inputs(model, numerical_check=False)
    equations = equation_evidence(model)
    issues = [*static["issues"]]
    if equations["ambiguous_names"]:
        issues.append({"severity": "error", "code": "ambiguous_names", "message": "Canonical element names collide", "names": equations["ambiguous_names"]})
    report = {"model": model.name, "model_id": model.id, "normalized_model_sha256": model_hash(model),
              "engine_sha256": hashes, "scientific_validation": "not established", "settings": model.time_settings.model_dump(),
              "source": model.source, "reference": model.reference, "input_issues": issues, "equation_evidence": equations,
              "runs": [], "comparisons": [], "warnings": [],
              "budget": {"max_runs": max_runs, "max_element_intervals_per_run": MAX_ELEMENT_INTERVALS_PER_RUN,
                         "total_element_intervals_upper_bound": max_runs * MAX_ELEMENT_INTERVALS_PER_RUN},
              "limitations": ["Completion, convergence and conservation of a topological sum do not establish scientific validity.",
                              "Negative stocks and domain-sensitive operations are review leads, not automatic model errors.",
                              "Only the supplied method and checked full-horizon timesteps are compared. No equations are changed."]}
    completed = []
    static_invalid = any(issue["severity"] == "error" for issue in issues) or bool(equations["syntax"])
    if equations["stochastic"]:
        report["warnings"].append("Stochastic calls detected: pathwise timestep convergence is inapplicable without a coupled-noise experiment; no refinement runs are attempted.")
    if model.time_settings.discrete_period is not None:
        report["warnings"].append("Discrete model: the declared period defines its recurrence; timestep refinement would change the model and is not attempted.")
    if equations["references_time_step"]:
        report["warnings"].append("Equations reference DT/TIME_STEP: refinement can change algebraic inputs or initial conditions as well as integration error.")
    if model.time_settings.integration_method == "radau":
        report["warnings"].append("Radau DT is retained output spacing. These runs refine output grids at unchanged adaptive tolerances; they do not refine internal solver steps or test tolerance convergence.")
    for index in range(max_runs):
        factor = 2 ** index
        ts = model.time_settings.model_copy(update={"dt": model.time_settings.dt / factor})
        row = {"run": index + 1, "dt_refinement_factor": factor, "settings": ts.model_dump(), "scope": "full supplied horizon"}
        if index and model.time_settings.discrete_period is not None:
            row.update(status="not_attempted", reason="Discrete recurrence has a fixed declared period")
            report["runs"].append(row)
            continue
        if ts.dt <= 0:
            row.update(status="not_attempted", reason="Refined dt cannot be represented at this numeric scale")
            report["runs"].append(row)
            continue
        intervals = (ts.end - ts.start) / ts.dt
        visible_work = math.ceil(intervals - 1e-10) * max(1, len(model.stocks) + len(model.flows) + len(model.variables)) if math.isfinite(intervals) else None
        row["visible_element_intervals"] = visible_work
        if index and (static_invalid or equations["stochastic"]):
            row.update(status="not_attempted", reason="Static input errors" if static_invalid else "Stochastic comparisons require coupled noise")
            report["runs"].append(row)
            continue
        if not math.isfinite(intervals) or intervals > MAX_INTERVALS or visible_work > MAX_ELEMENT_INTERVALS_PER_RUN or (math.ceil(intervals - 1e-10) + 1) * max(1, len(model.stocks) + len(model.flows) + len(model.variables)) > MAX_RETAINED_VALUES:
            row.update(status="not_attempted", reason="Requested grid exceeds existing engine workload limits; horizon was not shortened")
            report["runs"].append(row)
            continue
        try:
            result = simulate(model, TimeSettings.model_validate(ts.model_dump()))
            row.update(status="completed", samples=len(result.time),
                       effective_random_seed=getattr(result, "random_seed", None),
                       stocks=[{"name": s.name, "initial": result.values[s.name][0], "final": result.values[s.name][-1],
                                "minimum": min(result.values[s.name]), "maximum": max(result.values[s.name])} for s in model.stocks],
                       domain_leads=domain_evidence(model, result), conservation=conservation_evidence(model, result))
            if completed:
                other_index, previous = completed[-1]
                report["comparisons"].append({"coarse_run": other_index, "fine_run": index + 1, **compare_runs(previous, result, model)})
            completed.append((index + 1, result))
        except Exception as error:
            row.update(status="failed", error=str(error), failure=failure_payload(error))
            # DT-dependent initial equations can genuinely change under refinement.
            # Other identical start-time failures cannot be cured by integration.
            initial_failure = f"at time {ts.start:g}:" in str(error)
            if initial_failure and not equations["references_time_step"]:
                static_invalid = True
        report["runs"].append(row)
    report["baseline"] = report["runs"][0]
    differences = [c["maximum_scaled_stock_difference"] for c in report["comparisons"]]
    if model.time_settings.discrete_period is not None:
        conclusion = "inapplicable_for_discrete_period"
    elif equations["stochastic"]:
        conclusion = "inapplicable_for_stochastic_paths"
    elif len(differences) < 2:
        conclusion = "insufficient_completed_refinements"
    elif max(differences) <= 1e-3:
        conclusion = "small_differences_on_checked_grids"
    elif differences[-1] < differences[-2] * 0.8:
        conclusion = "differences_decrease_but_grid_sensitivity_remains"
    else:
        conclusion = "grid_sensitive_or_nonconvergent_on_checked_grids"
    report["timestep_assessment"] = {"status": conclusion, "threshold_for_small_scaled_difference": 1e-3,
                                     "interpretation": "Descriptive comparison of checked grids; no proof of convergence or scientific validity"}
    if model.time_settings.integration_method == "radau":
        report["timestep_assessment"].update(
            status="output_grid_comparison_only" if differences else "insufficient_completed_output_grids",
            grid_difference_status=conclusion,
            scope="output grids at unchanged adaptive tolerances",
            internal_tolerances_refined=False,
            rtol=model.time_settings.rtol, atol=model.time_settings.atol,
            interpretation="Radau DT controls retained output spacing. Differences include output interpolation at unchanged rtol/atol; internal adaptive steps were not explicitly refined. This is not an internal-step or tolerance convergence test and does not establish scientific validity.")
    if not model.stocks:
        report["warnings"].append("No stocks are present; stock-trajectory convergence has no dynamic state to assess.")
        report["timestep_assessment"]["status"] = "no_stocks_to_compare"
    if hashes != source_hashes():
        report["warnings"].append("Engine source changed during investigation; rerun before relying on this report.")
        report["source_changed"] = True
    else:
        report["source_changed"] = False
    return report
