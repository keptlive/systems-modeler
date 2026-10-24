"""Inspect model inputs without repairing or inventing scientific assumptions."""
import math
from collections import Counter
from app.core.model import Model, TimeSettings
from app.core.equations import validate_equation
from app.core.simulator import simulate
from app.core.source_review import citation_reviews


def inspect_inputs(model: Model, numerical_check=True) -> dict:
    from app.core.structured import compile_structured_model, StructuredModelError
    try:
        compiled = compile_structured_model(model.model_dump(mode="json"))
    except StructuredModelError as exc:
        return {"model": model.name, "valid": False, "numerical_check": "not_run",
                "scientific_validation": "not established", "issues": exc.diagnostics,
                "source_reviews": [], "inputs": {"initial_stocks": [], "flows": [],
                    "parameters_and_auxiliaries": [], "time_settings": model.time_settings.model_dump(),
                    "description": model.description, "source": model.source, "reference": model.reference}}
    if compiled["source_map"]:
        report = inspect_inputs(Model(**compiled["model"]), numerical_check)
        report["structured_source_map"] = compiled["source_map"]
        return report
    issues = []
    def issue(severity, code, message, element=None, **details):
        issues.append({"severity": severity, "code": code, "element": element, "message": message, **details})
    elements = [*model.stocks, *model.flows, *model.variables]
    names = [e.name for e in elements]
    from app.core.equations import symbol_identity
    for identifier, count in Counter(e.id for e in elements).items():
        if count > 1:
            issue("error", "duplicate_element_id", "Element IDs must be unique for unambiguous edits and selection", identifier)
    for name, count in Counter(symbol_identity(e.name) for e in elements).items():
        if count > 1:
            issue("error", "name_collision", "Element names collide after case and XMILE whitespace normalization", name)
        if name in {"time", "dt", "time_step"}:
            issue("error", "reserved_name", "TIME, DT and TIME_STEP are reserved simulation names", name)
    for name, count in Counter(symbol_identity(t.name) for t in model.tables).items():
        if count > 1:
            issue("error", "duplicate_lookup_name", "Lookup names must be unique after normalization", name)
    stock_references = {}
    for stock in model.stocks:
        for reference in {stock.id, stock.name}:
            owner = stock_references.setdefault(reference, stock.id)
            if owner != stock.id:
                issue("error", "ambiguous_stock_reference", "A stock ID or name identifies multiple stocks", reference)
    from app.core.reports import prepare_reports
    from app.core.equations import EquationError
    try:
        prepare_reports(model)
    except EquationError as exc:
        issue("error", exc.code or "invalid_report", str(exc), exc.details.get("element"))
    for element in elements:
        valid, message = validate_equation(element.equation, names, [t.name for t in model.tables])
        if not valid:
            issue("error", "equation_reference_or_syntax", message, element.name)
        if not element.name.strip():
            issue("error", "empty_name", "Every element needs a name", element.name)
    for stock in model.stocks:
        if not math.isfinite(stock.initial_value):
            issue("error", "nonfinite_initial_value", "Initial stock value must be finite", stock.name)
    references = {s.id for s in model.stocks} | {s.name for s in model.stocks}
    for flow in model.flows:
        for endpoint in (flow.from_stock, flow.to_stock):
            if endpoint is not None and endpoint not in references:
                issue("error", "missing_flow_endpoint", f"Unknown stock endpoint: {endpoint}", flow.name)
        if flow.from_stock is None and flow.to_stock is None:
            issue("warning", "unconnected_flow", "This flow changes no stock; confirm that it is intentionally diagnostic", flow.name)
    stock_owners = {reference: id(stock) for stock in model.stocks for reference in (stock.id, stock.name)}
    attached = set()
    for flow in model.flows:
        source, destination = stock_owners.get(flow.from_stock), stock_owners.get(flow.to_stock)
        if source != destination:
            attached.update(owner for owner in (source, destination) if owner is not None)
    disconnected = [s for s in model.stocks if id(s) not in attached]
    for stock in disconnected:
        issue("warning", "disconnected_stock",
              "No stock-changing flow is attached; this stock remains constant after initialization. Confirm whether it is intentionally fixed. A stock equation initializes it; it does not define a derivative.",
              stock.name)
    if model.stocks and len(disconnected) == len(model.stocks):
        issue("warning", "no_dynamic_stocks",
              "No stock has an attached stock-changing flow; numerical completion cannot demonstrate the claimed dynamics.")
    changing_flows = [f for f in model.flows
                      if stock_owners.get(f.from_stock) != stock_owners.get(f.to_stock)]
    def literal_zero(equation):
        try:
            return float(equation.strip()) == 0
        except (ValueError, TypeError):
            return False
    if changing_flows and all(literal_zero(f.equation) for f in changing_flows):
        issue("warning", "zero_flow_definitions",
              "Every stock-changing flow is defined as literal zero. Stocks stay fixed; confirm whether this is an intentional baseline or an unfinished model.")
    for table in model.tables:
        xs = [x for x, _ in table.points]
        if not xs or len(set(xs)) != len(xs) or any(not math.isfinite(v) for point in table.points for v in point):
            issue("error", "invalid_lookup_points", "Lookup points must be finite, nonempty and have distinct x coordinates", table.name)
    if not elements:
        issue("warning", "empty_model", "This model contains no stocks, flows or variables")
    if elements and not all(e.units for e in elements):
        issue("warning", "units_unverified", "Units are missing for one or more elements; dimensional consistency has not been established")
    from app.core.units import analyze_units
    dimensional_analysis = analyze_units(model)
    for mismatch in dimensional_analysis["errors"]:
        issue("warning", "dimensional_inconsistency", mismatch["message"], mismatch["element"])
    if not model.source and not model.reference:
        issue("warning", "missing_provenance", "No source/reference metadata is supplied")
    reviewed_sources = citation_reviews(model)
    for review in reviewed_sources:
        issue("warning", "citation_mismatch", review["finding"])
    if model.stocks and all(s.initial_value == 0 and not s.equation for s in model.stocks):
        issue("warning", "all_stocks_zero", "All initial stocks are zero; confirm that the intended system can start from this state")
    numerical = "not_run"
    if numerical_check:
        try:
            ts = model.time_settings
            short = TimeSettings(**{**ts.model_dump(), "end": min(ts.end, ts.start + ts.dt),
                                    "dt": min(ts.dt, ts.end - ts.start)})
            simulate(model, short)
            numerical = "completed_one_step"
        except Exception as exc:
            numerical = "failed"
            from app.core.failure_diagnostics import failure_payload
            issue("error", "numerical_input_check", str(exc), failure=failure_payload(exc))
    return {"model": model.name, "valid": not any(i["severity"] == "error" for i in issues),
            "numerical_check": numerical, "scientific_validation": "not established",
            "issues": issues,
            "dimensional_analysis": dimensional_analysis,
            "source_reviews": reviewed_sources,
            "inputs": {"initial_stocks": [{"name": s.name, "initial_value": s.initial_value,
                                             "initial_equation": s.equation, "units": s.units} for s in model.stocks],
                       "parameters_and_auxiliaries": [{"name": v.name, "equation": v.equation, "units": v.units, "role": v.role} for v in model.variables],
                       "flows": [{"name": f.name, "equation": f.equation, "from_stock": f.from_stock,
                                  "to_stock": f.to_stock, "units": f.units} for f in model.flows],
                       "time_settings": model.time_settings.model_dump(),
                       "description": model.description,
                       "source": model.source, "reference": model.reference}}
