"""Conservative, bounded dependency scheduling for the existing scalar evaluator.

This module derives metadata only: it never evaluates equations or changes source.
None means retain the authored stage order and its established retry behavior.
"""
import ast
import heapq
import math
from app.core.equations import (
    _parse_expression, preprocess_equation, get_equation_variables,
    decode_identifier, canonical_name, SAFE_CONSTANTS, EquationError,
)
from app.core.limits import MAX_ELEMENTS

MAX_PLAN_CHARACTERS = 2_000_000
MAX_PLAN_AST_NODES = 100_000
MAX_PLAN_EDGES = 100_000
# Deliberately explicit: additions to the evaluator are not automatically eligible.
PURE_FUNCTIONS = frozenset({
    'ARCSIN', 'ARCCOS', 'ARCTAN', 'INT', 'TRUNC',
    'QUANTUM', 'SAFEDIV', 'ZIDZ', 'XIDZ', 'MODULO', 'REM',
    "SIN", "COS", "TAN", "ASIN", "ACOS", "ATAN", "ATAN2", "SIGN",
    "EXP", "LOG", "LN", "LOG10", "SQRT", "ABS", "MIN", "MAX", "POW",
    "FLOOR", "CEIL", "ROUND", "MOD",
})
ARITHMETIC = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv)
ALLOWED_NODES = (
    ast.Expression, ast.Constant, ast.Name, ast.Load, ast.BinOp, ast.UnaryOp,
    ast.Call, ast.UAdd, ast.USub, *ARITHMETIC,
)


def derive_execution_order(model, initial=False):
    """Return immutable ordered (name, equation) pairs, or None for safe fallback.

    Only unconditional, pure numeric scalar DAGs are eligible. The caller must
    pass the actual numeric execution model, after structured lowering and report
    separation, and keep its existing validation, evaluator and work accounting.
    Stock levels are known during regular evaluation; during initialization only
    stocks without authored initializer equations are known.
    """
    try:
        return _derive(model, initial)
    except (EquationError, SyntaxError, ValueError, TypeError, RecursionError, OverflowError):
        # Optimization cannot replace established runtime errors or diagnostics.
        return None


def _derive(model, initial):
    if type(initial) is not bool:
        return None
    if any(getattr(model, key, None) for key in ("dimensions", "modules", "module_definitions")):
        return None
    stocks, flows, variables = model.stocks, model.flows, model.variables
    elements = [*stocks, *flows, *variables]
    if len(elements) > MAX_ELEMENTS or len(model.tables) > MAX_ELEMENTS or any(getattr(v, "role", "auxiliary") == "report" for v in variables):
        return None
    authored = [(e.name, e.equation) for e in (*variables, *flows)]
    if initial:
        authored.extend((s.name, s.equation) for s in stocks if s.equation)
    text_size = sum(len(eq) for _, eq in authored)
    text_size += sum(len(e.name) for e in elements) + sum(len(t.name) for t in model.tables)
    if text_size > MAX_PLAN_CHARACTERS:
        return None
    aliases = {}
    for element in elements:
        key = canonical_name(element.name)
        if not key or key in aliases or key in {"time", "dt", "time_step"}:
            return None
        aliases[key] = element.name
    known = {
        canonical_name(s.name) for s in stocks
        if not initial or not s.equation
    }
    positions = {canonical_name(name): i for i, (name, _) in enumerate(authored)}
    if len(positions) != len(authored):
        return None
    table_names = {canonical_name(table.name) for table in model.tables}
    dependencies = []
    ast_nodes = 0
    edge_count = 0
    for _, equation in authored:
        if not isinstance(equation, str) or not equation.strip():
            return None
        tree = _parse_expression(preprocess_equation(equation))
        nodes = list(ast.walk(tree))
        ast_nodes += len(nodes)
        if ast_nodes > MAX_PLAN_AST_NODES:
            return None
        for node in nodes:
            if not isinstance(node, ALLOWED_NODES):
                return None
            if isinstance(node, ast.Constant):
                if type(node.value) not in (int, float) or not math.isfinite(float(node.value)):
                    return None
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.keywords:
                    return None
                function = decode_identifier(node.func.id)
                if canonical_name(function) in table_names:
                    return None
                if function.upper() not in PURE_FUNCTIONS:
                    return None
        incoming = set()
        for reference in get_equation_variables(equation):
            key = canonical_name(reference)
            if key in known:
                continue
            if key in positions:
                incoming.add(positions[key])
                continue
            # A model's declared e/pi shadows the evaluator's constant fallback.
            if key in aliases:
                return None
            if reference.lower() in SAFE_CONSTANTS:
                continue
            return None
        edge_count += len(incoming)
        if edge_count > MAX_PLAN_EDGES:
            return None
        dependencies.append(incoming)
    consumers = [[] for _ in authored]
    indegree = []
    for target, incoming in enumerate(dependencies):
        indegree.append(len(incoming))
        for source in incoming:
            consumers[source].append(target)
    ready = [i for i, degree in enumerate(indegree) if degree == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        source = heapq.heappop(ready)
        ordered.append(authored[source])
        for target in consumers[source]:
            indegree[target] -= 1
            if indegree[target] == 0:
                heapq.heappush(ready, target)
    return tuple(ordered) if len(ordered) == len(authored) else None

