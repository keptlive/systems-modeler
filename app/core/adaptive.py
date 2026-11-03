"""Explicit opt-in stiff integration of deterministic scalar ODE models.

DT is the retained output spacing for Radau, not an internal integration step.
Every model evaluation, including finite-difference Jacobian probes and retained
algebraic outputs, is charged. No partial solution or automatic fallback.
"""
import math
import ast
from fractions import Fraction
from scipy.integrate import solve_ivp
from app.core.equations import (EquationError, SafeEvaluator, canonical_name, symbol_identity, resolve_name,
                                decode_identifier, preprocess_equation)
from app.core.failure_diagnostics import capacity_error
from app.core.model import SimulationResult
from app.core.limits import MAX_WORK_UNITS


DISCRETE_FUNCTIONS = {'FLOOR', 'CEIL', 'ROUND', 'SIGN', 'MOD', 'MODULO', 'REM', 'INT', 'TRUNC', 'QUANTUM', 'RAMP', 'RAMP_VENSIM'}
SAFE_DIVISION_FUNCTIONS = {'SAFEDIV', 'ZIDZ', 'XIDZ'}


class _UncertifiedBoundary(Exception):
    pass


def _matching_branch_limits(condition, yes, no, aliases, resolve_key=canonical_name):
    """A bounded algebraic proof, never a numerical sampling heuristic.

    Expand algebraic aliases and require a Boolean combination of direct
    comparisons, whose equality surfaces cover every possible switch. Impose
    each surface and compare exact polynomials there. Continuous elementary
    calls can be opaque atoms; an unknown denominator or domain is deliberately
    not certified.
    This recognizes common zero-crossing feedback and piecewise friction laws
    without claiming to locate arbitrary hybrid events.
    """
    budget = [6000]

    def expand(node, active=()):
        budget[0] -= 1
        if budget[0] < 0 or len(active) > 80:
            raise _UncertifiedBoundary
        if isinstance(node, ast.Name):
            name = resolve_key(decode_identifier(node.id))
            if name in aliases:
                if name in active:
                    raise _UncertifiedBoundary
                return expand(aliases[name], (*active, name))
        result = type(node)()
        for field, value in ast.iter_fields(node):
            setattr(result, field, [expand(v, active) if isinstance(v, ast.AST) else v for v in value]
                    if isinstance(value, list) else expand(value, active) if isinstance(value, ast.AST) else value)
        return result

    def key(node):
        return ast.dump(node, include_attributes=False)

    def static_value(node):
        # Use the scalar evaluator's function and comparison semantics. Only
        # literal pure arithmetic is admitted here: never sample randomness,
        # initialize hidden state, or resolve TIME/model names during a proof.
        pure = {"LN", "LOG", "LOG10", "EXP", "SIN", "COS", "SQRT",
                "ABS", "MIN", "MAX", "TANH", "IF", "IF_THEN_ELSE"}
        function_nodes = {id(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)}
        for part in ast.walk(node):
            if isinstance(part, ast.Name) and id(part) not in function_nodes:
                raise _UncertifiedBoundary
            if isinstance(part, ast.Call) and (not isinstance(part.func,ast.Name)
                    or decode_identifier(part.func.id).upper() not in pure):
                raise _UncertifiedBoundary
        try:
            return SafeEvaluator({}).visit(node)
        except EquationError as exc:
            raise _UncertifiedBoundary from exc

    def bounded(value):
        if value.numerator.bit_length() + value.denominator.bit_length() > 8192:
            raise _UncertifiedBoundary
        return value

    def constant(node):
        budget[0] -= 1
        if budget[0] < 0: raise _UncertifiedBoundary
        return bounded(constant_expression(node))

    def constant_expression(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return Fraction(str(node.value))
        if isinstance(node, ast.UnaryOp):
            value = constant(node.operand)
            if isinstance(node.op, ast.USub): return -value
            if isinstance(node.op, ast.UAdd): return value
        if isinstance(node, ast.BinOp):
            a, b = constant(node.left), constant(node.right)
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if isinstance(node.op, ast.Div): return a / b
            if isinstance(node.op, ast.Pow):
                if b.denominator == 1 and abs(b) <= 16:
                    if (a.numerator.bit_length()+a.denominator.bit_length())*abs(b) > 8192:
                        raise _UncertifiedBoundary
                    return a ** int(b)
                value = float(a) ** float(b)
                if isinstance(value, complex) or not math.isfinite(value): raise _UncertifiedBoundary
                return Fraction(str(value))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            value = static_value(node)
            if not math.isfinite(value): raise _UncertifiedBoundary
            return Fraction(str(value))
        raise _UncertifiedBoundary

    def literal(value):
        # Preserve rational boundaries exactly rather than converting to float.
        return ast.BinOp(ast.Constant(value.numerator), ast.Div(), ast.Constant(value.denominator))

    def affine(node):
        """Return scale * one continuous expression + constant, when literal."""
        try: return Fraction(0), None, constant(node)
        except _UncertifiedBoundary: pass
        if isinstance(node, ast.BinOp):
            a, x, b = affine(node.left)
            c, y, d = affine(node.right)
            if isinstance(node.op, (ast.Add, ast.Sub)) and (x is None or y is None or key(x) == key(y)):
                sign = -1 if isinstance(node.op, ast.Sub) else 1
                return a + sign*c, x if x is not None else y, b + sign*d
            if isinstance(node.op, ast.Mult):
                if x is None: return b*c, y, b*d
                if y is None: return d*a, x, d*b
            if isinstance(node.op, ast.Div) and y is None and d:
                return a/d, x, b/d
        return Fraction(1), node, Fraction(0)

    def truth(node):
        return bool(static_value(node))

    def replace(node, replacements):
        if key(node) in replacements: return replacements[key(node)]
        result = type(node)()
        for field, value in ast.iter_fields(node):
            setattr(result, field, [replace(v, replacements) if isinstance(v, ast.AST) else v for v in value]
                    if isinstance(value, list) else replace(value, replacements) if isinstance(value, ast.AST) else value)
        return result

    def add(a, b, sign=1):
        result = dict(a)
        for term, value in b.items():
            result[term] = bounded(result.get(term, Fraction(0)) + sign*value)
            if not result[term]: del result[term]
        if len(result) > 96: raise _UncertifiedBoundary
        return result

    def multiply(a, b):
        if len(a)*len(b) > 192: raise _UncertifiedBoundary
        result = {}
        for x, av in a.items():
            for y, bv in b.items():
                term = tuple(sorted((*x, *y)))
                if len(term) > 16: raise _UncertifiedBoundary
                result[term] = bounded(result.get(term, Fraction(0)) + av*bv)
        return {k:v for k,v in result.items() if v}

    def polynomial(node):
        budget[0] -= 1
        if budget[0] < 0: raise _UncertifiedBoundary
        try:
            value = constant(node)
            return {():value} if value else {}
        except _UncertifiedBoundary: pass
        if isinstance(node, ast.Name): return {(key(node),):Fraction(1)}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return {k:v*(-1 if isinstance(node.op, ast.USub) else 1) for k,v in polynomial(node.operand).items()}
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Div):
                divisor = constant(node.right)
                if not divisor: raise _UncertifiedBoundary
                return {k:v/divisor for k,v in polynomial(node.left).items()}
            if isinstance(node.op, ast.Pow):
                exponent = constant(node.right)
                if exponent.denominator != 1 or not 0 <= exponent <= 8: raise _UncertifiedBoundary
                base = polynomial(node.left)
                result = {():Fraction(1)}
                for _ in range(int(exponent)): result = multiply(result, base)
                return result
            a, b = polynomial(node.left), polynomial(node.right)
            if isinstance(node.op, ast.Add): return add(a,b)
            if isinstance(node.op, ast.Sub): return add(a,b,-1)
            if isinstance(node.op, ast.Mult): return multiply(a,b)
        if isinstance(node, ast.IfExp): return polynomial(node.body if truth(node.test) else node.orelse)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = decode_identifier(node.func.id).upper()
            if name in {"IF", "IF_THEN_ELSE"} and len(node.args) == 3:
                return polynomial(node.args[1] if truth(node.args[0]) else node.args[2])
            if name in {"ABS", "MIN", "MAX", "SIN", "COS", "EXP", "TANH"}:
                args = tuple(tuple(sorted(polynomial(arg).items())) for arg in node.args)
                return {(repr((name, args)),):Fraction(1)}
        raise _UncertifiedBoundary

    try:
        condition, yes, no = [expand(node) for node in (condition, yes, no)]
        def comparison_leaves(node):
            # A Boolean combination switches only where one of its comparison
            # leaves can switch. Arbitrary arithmetic, numeric truth operands,
            # or conditional wrappers can introduce additional zeros that the
            # descendant comparisons do not describe.
            if isinstance(node, ast.Compare):
                if len(node.ops) != 1:
                    raise _UncertifiedBoundary
                return [node]
            if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
                return [leaf for value in node.values for leaf in comparison_leaves(value)]
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.Invert)):
                return comparison_leaves(node.operand)
            raise _UncertifiedBoundary

        comparisons = comparison_leaves(condition)
        if not comparisons: return False
        for comparison in comparisons:
            # A chained XMILE comparison can switch when an intermediate
            # Boolean crosses another operand, not only at adjacent scalar
            # equalities. Do not invent event surfaces for that syntax.
            if len(comparison.ops) != 1: return False
            for left, right in zip([comparison.left, *comparison.comparators], comparison.comparators):
                # A matching output at a nominal threshold says nothing if
                # the switching expression itself has an unproved domain or
                # a jump. Require continuous supported algebra on both sides.
                polynomial(left)
                polynomial(right)
                # Direct expression substitution handles arbitrary algebraic
                # aliases at their stated threshold. A scaled-atom substitution
                # additionally handles e.g. Re = coefficient * ABS(velocity).
                replacements = {key(left):right}
                try:
                    target = constant(right)
                    scale, atom, offset = affine(left)
                    if atom is not None and scale:
                        replacements[key(atom)] = literal((target-offset)/scale)
                except _UncertifiedBoundary: pass
                if polynomial(replace(yes, replacements)) != polynomial(replace(no, replacements)):
                    return False
        return True
    except (ArithmeticError, ValueError, TypeError, RecursionError, _UncertifiedBoundary):
        return False


def state_discontinuities(model):
    """Find uncertified state switches that can influence a stock derivative.

    Retained diagnostics do not affect the adaptive trajectory. MIN/MAX/ABS are
    continuous; IF needs matching branch limits. This is a conservative supported
    syntax contract, not a general proof of existence, uniqueness or accuracy.
    """
    declared = tuple(e.name for e in (*model.stocks, *model.flows, *model.variables))
    table_declarations = tuple(t.name for t in model.tables)
    key = lambda name: symbol_identity(resolve_name(name, declared) or name)
    table_key = lambda name: symbol_identity(resolve_name(name, table_declarations) or name)
    elements = {symbol_identity(e.name): e for e in [*model.variables, *model.flows]}
    trees = {name: ast.parse(preprocess_equation(e.equation), mode="eval").body
             for name,e in elements.items() if e.equation.strip()}
    stocks = {symbol_identity(s.name) for s in model.stocks}
    tables = {symbol_identity(t.name): t.interpolation for t in model.tables}

    def references(node):
        functions = {id(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)}
        return {key(decode_identifier(n.id)) for n in ast.walk(node)
                if isinstance(n, ast.Name) and id(n) not in functions}

    state_names = set(stocks)
    for _ in range(len(trees)+1):
        added = {name for name,tree in trees.items() if references(tree) & state_names} - state_names
        if not added: break
        state_names.update(added)
    needed = {symbol_identity(f.name) for f in model.flows if f.from_stock is not None or f.to_stock is not None}
    for _ in range(len(trees)+1):
        added = {ref for name in needed if name in trees for ref in references(trees[name]) if ref in trees} - needed
        if not added: break
        needed.update(added)
    findings = []
    for name in sorted(needed):
        tree = trees.get(name)
        if tree is None: continue
        condition_nodes = set()
        for node in ast.walk(tree):
            condition, yes, no = (node.test, node.body, node.orelse) if isinstance(node, ast.IfExp) else (None,None,None)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                function = decode_identifier(node.func.id).upper()
                if (table_key(function) in tables or function in {"LOOKUP", "WITH_LOOKUP"}) and references(node) & state_names:
                    # Even continuous interpolation can hide an entire narrow
                    # forcing pulse between internal steps. Table knots need
                    # event localization before this RHS contract can expand.
                    findings.append({"element":elements[name].name,"operation":"state-dependent lookup forcing"})
                elif function in {"IF", "IF_THEN_ELSE"} and len(node.args) == 3:
                    condition,yes,no = node.args
                elif function in DISCRETE_FUNCTIONS and references(node) & state_names:
                    findings.append({"element":elements[name].name,"operation":function})
                elif function in SAFE_DIVISION_FUNCTIONS and len(node.args) >= 2 and references(node.args[1]) & state_names:
                    findings.append({"element":elements[name].name,"operation":function})
            if condition is not None:
                condition_nodes.update(id(n) for n in ast.walk(condition))
                if references(condition) & state_names and not _matching_branch_limits(condition,yes,no,trees,key):
                    findings.append({"element":elements[name].name,"operation":"uncertified state-dependent conditional"})
        for node in ast.walk(tree):
            if isinstance(node, (ast.Compare, ast.BoolOp)) and id(node) not in condition_nodes and references(node) & state_names:
                findings.append({"element":elements[name].name,"operation":"state-dependent comparison value"})
            if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Mod,ast.FloorDiv)) and references(node) & state_names:
                findings.append({"element":elements[name].name,"operation":"state-dependent discrete arithmetic"})
    return [dict(items) for items in sorted({tuple(sorted(item.items())) for item in findings})]


def time_discontinuities(model):
    """Reject explicit time-triggered switching, including algebraic aliases.

    Stock state is not marked as an algebraic TIME alias: stock-dependent
    feedback conditions retain their ordinary ODE meaning. This is a conservative
    input contract, not a proof that all accepted RHS functions are smooth.
    """
    declared = tuple(e.name for e in (*model.stocks, *model.flows, *model.variables))
    table_declarations = tuple(t.name for t in model.tables)
    key = lambda name: symbol_identity(resolve_name(name, declared) or name)
    table_key = lambda name: symbol_identity(resolve_name(name, table_declarations) or name)
    trees = {}
    table_names = {symbol_identity(t.name) for t in model.tables}
    for element in [*model.variables, *model.flows]:
        if element.equation.strip():
            trees[element.name] = ast.parse(preprocess_equation(element.equation), mode="eval")
    def references(node):
        function_nodes = {id(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)}
        return {key(decode_identifier(n.id)) for n in ast.walk(node)
                if isinstance(n, ast.Name) and id(n) not in function_nodes}
    time_names = {"time"}
    changed = True
    while changed:
        changed = False
        for name, tree in trees.items():
            if key(name) not in time_names and references(tree) & time_names:
                time_names.add(key(name))
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
                if table_key(function) in table_names:
                    lookup_arguments = node.args
                elif function == "LOOKUP":
                    lookup_arguments = node.args[1:]  # table name is not an input
                elif function == "WITH_LOOKUP":
                    lookup_arguments = node.args  # inline points may vary too
                else:
                    lookup_arguments = []
                if any(references(argument) & time_names for argument in lookup_arguments):
                    findings.append({"element": name, "operation": "time-dependent lookup", "function": function})
                if table_key(function) not in table_names:
                    if function in {"IF", "IF_THEN_ELSE"} and node.args:
                        condition = node.args[0]
                    elif function in DISCRETE_FUNCTIONS and references(node) & time_names:
                        findings.append({"element": name, "operation": function})
                    elif function in SAFE_DIVISION_FUNCTIONS and len(node.args) >= 2 and references(node.args[1]) & time_names:
                        findings.append({"element": name, "operation": function})
            if isinstance(node, (ast.Compare, ast.BoolOp)):
                condition = node
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.FloorDiv)) and references(node) & time_names:
                findings.append({"element": name, "operation": "time-dependent discrete arithmetic"})
            if condition is not None and references(condition) & time_names:
                findings.append({"element": name, "operation": "time-dependent conditional/comparison"})
    return [dict(items) for items in sorted({tuple(sorted(item.items())) for item in findings})]

def integrate_radau(model, settings, time, evaluate, report_work=0):
    elements = [*model.stocks, *model.flows, *model.variables]
    size = max(1, len(elements))
    work_units = report_work
    model_evaluations = 0
    dependency_retries = 0

    def charge_retry():
        nonlocal work_units, dependency_retries
        dependency_retries += 1
        work_units += 1
        if work_units > MAX_WORK_UNITS:
            raise capacity_error("Radau equation dependency retries exceed work budget",
                                 resource="work_units", requested=work_units, limit=MAX_WORK_UNITS)

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
        return evaluate(model, stocks, at, settings.dt, {}, {}, initial=initial, retry_work=charge_retry)

    initial_stocks = {s.name: s.initial_value for s in model.stocks if not s.equation}
    initial = checked_values(initial_stocks, time[0], initial=True)
    stock_names = [stock.name for stock in model.stocks]
    references = {reference: s.name for s in model.stocks for reference in (s.id, s.name)}
    links = [(f.name, references.get(f.from_stock), references.get(f.to_stock)) for f in model.flows]

    def rhs(at, vector):
        stocks = dict(zip(stock_names, map(float, vector)))
        values = checked_values(stocks, float(at))
        terms = {name: [] for name in stock_names}
        for name, source, destination in links:
            if source is not None:
                terms[source].append(-values[name])
            if destination is not None:
                terms[destination].append(values[name])
        rates = {name: math.fsum(values) for name,values in terms.items()}
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
                "dependency_retries": dependency_retries,
                "report_evaluations": report_work,
                "work_unit_limit": MAX_WORK_UNITS,
                "work_scope": "Initial equations, every RHS/Jacobian probe, all retained algebraic outputs, and dependency retries"}
    return SimulationResult(time=time, values=results, integration_diagnostics=metadata)
