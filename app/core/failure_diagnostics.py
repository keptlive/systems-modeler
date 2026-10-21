"""Runtime failure causes without evaluating extra branches or repairing inputs."""
import math
from app.core.equations import EquationError, canonical_name


def error_code(error):
    if getattr(error, "code", None):
        return error.code
    text = str(error)
    if isinstance(error, OverflowError):
        return "numeric_overflow"
    if isinstance(error, SyntaxError) or "Syntax error" in text:
        return "syntax_error"
    if "complex" in text:
        return "non_real_result"
    if "not finite" in text or "Non-finite" in text:
        return "non_finite_result"
    if "Unsupported expression" in text or "Invalid constant type" in text:
        return "unsupported_expression"
    return "equation_error"


def stalled_evaluation(model, pending, errors, time, stocks):
    """Use the actual failed symbol, not static potential references.

    Only missing *declared pending* values are blocked dependencies. Undeclared
    names and domain/signature errors remain root failures. Runtime dependency
    cycles are reported without assuming a solver or evaluating lazy branches.
    """
    elements = {e.name: e for e in [*model.stocks, *model.variables, *model.flows]}
    names = {canonical_name(name): name for name, _ in pending}
    records = {}
    edges = {}
    for name, equation in pending:
        error = errors[name]
        record = {"element": name, "element_id": elements[name].id,
                  "equation": equation, "code": error_code(error), "message": str(error)}
        record.update(getattr(error, "details", {}))
        records[name] = record
        symbol = record.get("symbol")
        if record["code"] == "unknown_variable" and symbol is not None:
            dependency = names.get(canonical_name(symbol))
            if dependency is not None:
                edges[name] = dependency
    roots = [record for name, record in records.items() if name not in edges]
    cycles = {}
    blocked = []
    for name in edges:
        path = []
        current = name
        while current in edges and current not in path:
            path.append(current)
            current = edges[current]
        if current in path:
            members = path[path.index(current):]
            key = tuple(sorted(members))
            cycles[key] = {"code": "algebraic_cycle", "elements": list(key),
                           "message": "Cyclic dependencies among unresolved values; no algebraic loop solver is selected"}
            cause = {"code": "algebraic_cycle", "elements": list(key)}
        else:
            cause = {"code": records[current]["code"], "element": current}
        blocked.append({**records[name], "code": "blocked_dependency",
                        "waiting_for": edges[name], "dependency_path": path + [current],
                        "root_cause": cause})
    roots.extend(cycles.values())
    details = {"category": "invalid_equations", "time": time,
               "root_errors": roots, "blocked_errors": blocked,
               "stock_values": dict(stocks)}
    root_text = "; ".join(
        (r["element"] + ": " + r["message"]) if "element" in r
        else ("Algebraic dependency cycle: " + " -> ".join(r["elements"]))
        for r in roots)
    blocked_text = "; ".join(f'{r["element"]} (waiting for {r["waiting_for"]})' for r in blocked)
    message = f"Unresolved or invalid equations at time {time:g}: Root causes: {root_text}"
    if blocked_text:
        message += "; Blocked dependents: " + blocked_text
    return EquationError(message, code="unresolved_equations", details=details)


def capacity_error(message, *, resource, requested, limit):
    return EquationError(message, code="capacity_exceeded",
                         details={"category": "capacity", "resource": resource,
                                  "requested": requested if math.isfinite(requested) else None, "limit": limit})


def failure_payload(error):
    """Stable additive payload for investigate/MCP/API callers."""
    return {"code": error_code(error), "message": str(error),
            **getattr(error, "details", {})}
