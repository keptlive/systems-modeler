"""Explicit opt-in stiff integration of deterministic scalar ODE models.

DT is the retained output spacing for Radau, not an internal integration step.
Every model evaluation, including finite-difference Jacobian probes and retained
algebraic outputs, is charged. No partial solution or automatic fallback.
"""
import math
import ast
from scipy.integrate import solve_ivp
from app.core.equations import EquationError, canonical_name, decode_identifier, preprocess_equation
from app.core.failure_diagnostics import capacity_error
from app.core.model import SimulationResult
from app.core.limits import MAX_WORK_UNITS



def time_discontinuities(model):
    """Reject explicit time-triggered switching, including algebraic aliases.

    Stock state is not marked as an algebraic TIME alias: stock-dependent
    feedback conditions retain their ordinary ODE meaning. This is a conservative
    input contract, not a proof that all accepted RHS functions are smooth.
    """
    trees = {}
    table_names = {canonical_name(t.name) for t in model.tables}
    for element in [*model.variables, *model.flows]:
        if element.equation.strip():
            trees[element.name] = ast.parse(preprocess_equation(element.equation), mode="eval")
    def references(node):
        function_nodes = {id(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)}
        return {canonical_name(decode_identifier(n.id)) for n in ast.walk(node)
                if isinstance(n, ast.Name) and id(n) not in function_nodes}
    time_names = {"time"}
    changed = True
    while changed:
        changed = False
        for name, tree in trees.items():
            if canonical_name(name) not in time_names and references(tree) & time_names:
                time_names.add(canonical_name(name))
                changed = True
    findings = []
    for name, tree in trees.items():
        for node in ast.walk(tree):
            condition = node.test if isinstance(node, ast.IfExp) else None
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                function = decode_identifier(node.func.id).upper()
                # An adaptive solver can jump over an entire narrow table
                # feature even when interpolation is continuous. Output times
                # do not constrain internal steps. Until table-knot events are
                # supported, reject explicit TIME-driven lookups rather than
                # returning a successful but silently missed forcing pulse.
                if canonical_name(function) in table_names:
                    lookup_arguments = node.args
                elif function == "LOOKUP":
                    lookup_arguments = node.args[1:]  # table name is not an input
                elif function == "WITH_LOOKUP":
                    lookup_arguments = node.args  # inline points may vary too
                else:
                    lookup_arguments = []
                if any(references(argument) & time_names for argument in lookup_arguments):
                    findings.append({"element": name, "operation": "time-dependent lookup", "function": function})
                if canonical_name(function) not in table_names:
                    if function in {"IF", "IF_THEN_ELSE"} and node.args:
                        condition = node.args[0]
                    elif function in {"FLOOR", "CEIL", "ROUND", "SIGN", "MOD"} and references(node) & time_names:
                        findings.append({"element": name, "operation": function})
            if isinstance(node, (ast.Compare, ast.BoolOp)):
                condition = node
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.FloorDiv)) and references(node) & time_names:
                findings.append({"element": name, "operation": "time-dependent discrete arithmetic"})
            if condition is not None and references(condition) & time_names:
                findings.append({"element": name, "operation": "time-dependent conditional/comparison"})
    return [dict(items) for items in sorted({tuple(sorted(item.items())) for item in findings})]

def integrate_radau(model, settings, time, evaluate):
    elements = [*model.stocks, *model.flows, *model.variables]
    size = max(1, len(elements))
    work_units = 0
    model_evaluations = 0

    def checked_values(stocks, at, initial=False):
        nonlocal work_units, model_evaluations
        requested = work_units + size
        if requested > MAX_WORK_UNITS:
            raise capacity_error("Radau exceeds 1,000,000 work units including RHS, Jacobian probes and retained outputs",
                                 resource="work_units", requested=requested, limit=MAX_WORK_UNITS)
        work_units = requested
        model_evaluations += 1
        if not all(math.isfinite(value) for value in stocks.values()):
            raise EquationError(f"Non-finite Radau trial stock at time {at:g}",
                                code="non_finite_stock", details={"category": "invalid_equations", "time": at})
        return evaluate(model, stocks, at, settings.dt, {}, {}, initial=initial)

    initial_stocks = {s.name: s.initial_value for s in model.stocks if not s.equation}
    initial = checked_values(initial_stocks, time[0], initial=True)
    stock_names = [stock.name for stock in model.stocks]
    references = {reference: s.name for s in model.stocks for reference in (s.id, s.name)}
    links = [(f.name, references.get(f.from_stock), references.get(f.to_stock)) for f in model.flows]

    def rhs(at, vector):
        stocks = dict(zip(stock_names, map(float, vector)))
        values = checked_values(stocks, float(at))
        rates = {name: 0.0 for name in stock_names}
        for name, source, destination in links:
            if source is not None:
                rates[source] -= values[name]
            if destination is not None:
                rates[destination] += values[name]
        if not all(math.isfinite(value) for value in rates.values()):
            raise EquationError(f"Non-finite Radau derivative at time {at:g}",
                                code="non_finite_derivative", details={"category": "invalid_equations", "time": float(at)})
        return [rates[name] for name in stock_names]

    solution = None
    if stock_names:
        solution = solve_ivp(rhs, (time[0], time[-1]), [initial[name] for name in stock_names],
                             method="Radau", t_eval=time, rtol=settings.rtol, atol=settings.atol,
                             vectorized=False)
        if not solution.success or len(solution.t) != len(time):
            raise EquationError("Radau integration failed: " + solution.message, code="solver_failure",
                                details={"category": "numerical_solver", "method": "radau",
                                         "solver_message": solution.message,
                                         "last_retained_time": float(solution.t[-1]) if len(solution.t) else time[0]})
    results = {element.name: [initial[element.name]] for element in elements}
    for index, at in enumerate(time[1:], 1):
        stocks = {name: float(solution.y[n, index]) for n, name in enumerate(stock_names)} if solution is not None else {}
        values = checked_values(stocks, at)
        for name in results:
            results[name].append(values[name])
    metadata = {"method": "radau", "output_grid": "exact requested times",
                "internal_steps": "adaptive; dt is output spacing",
                "rtol": settings.rtol, "atol": settings.atol,
                "nfev": solution.nfev if solution is not None else 0,
                "njev": solution.njev if solution is not None else 0,
                "nlu": solution.nlu if solution is not None else 0,
                "model_evaluations": model_evaluations, "work_units": work_units,
                "work_unit_limit": MAX_WORK_UNITS,
                "work_scope": "Initial equations, every RHS/Jacobian probe, and all retained algebraic outputs"}
    return SimulationResult(time=time, values=results, integration_diagnostics=metadata)
