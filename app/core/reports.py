"""Read-only scalar/text reports evaluated at retained times, outside the ODE.

Single quotes denote literal labels; double quotes retain XMILE identifier meaning.
No report may feed another equation. No stateful or stochastic report calls.
"""
import ast
import math
from app.core.equations import (EquationError, SafeEvaluator, _parse_expression,
    preprocess_equation, decode_identifier, canonical_name, equation_features,
    get_equation_variables, validate_equation)


def report_tree(equation, names, tables):
    valid, message = validate_equation(equation, names, tables)
    if not valid:
        raise EquationError(message, code="invalid_report")
    features = equation_features(equation, tables)
    if features["random_calls"] or features["stateful_calls"]:
        raise EquationError("Reports cannot contain random or stateful functions", code="invalid_report")
    tree = _parse_expression(preprocess_equation(equation or "0")).body
    def numeric(node):
        # LOOKUP accepts a single-quoted table name; other numeric expressions
        # cannot use text, even in an inactive branch.
        table_args = {id(n.args[0]) for n in ast.walk(node) if isinstance(n, ast.Call)
                      and isinstance(n.func, ast.Name) and decode_identifier(n.func.id).upper() == "LOOKUP" and n.args}
        for n in ast.walk(node):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in table_args:
                raise EquationError("Text is allowed only as a report result or conditional result branch", code="invalid_report")
    def check(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                node.value.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise EquationError("Report labels must contain valid Unicode scalar text", code="invalid_report") from exc
            if len(node.value) > 512:
                raise EquationError("Report labels are limited to 512 characters", code="invalid_report")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and decode_identifier(node.func.id).upper() in {"IF", "IF_THEN_ELSE"} and canonical_name(decode_identifier(node.func.id)) not in {canonical_name(t) for t in tables}:
            if len(node.args) != 3:
                raise EquationError("Report IF requires condition, true result and false result", code="invalid_report")
            numeric(node.args[0]); check(node.args[1]); check(node.args[2])
        elif isinstance(node, ast.IfExp):
            numeric(node.test); check(node.body); check(node.orelse)
        else:
            numeric(node)
    check(tree)
    return tree


def prepare_reports(model):
    reports = [v for v in model.variables if v.role == "report"]
    if not reports:
        return model, []
    report_names = {canonical_name(v.name) for v in reports}
    elements = [*model.stocks, *model.flows, *model.variables]
    names = [canonical_name(e.name) for e in elements]
    if len(set(names)) != len(names):
        raise EquationError("Element names must be unique, including case/space/punctuation aliases", code="name_collision")
    numeric_names = [e.name for e in elements if canonical_name(e.name) not in report_names]
    for e in elements:
        dependencies = {canonical_name(n) for n in get_equation_variables(e.equation)} & report_names
        if dependencies:
            raise EquationError(f"{e.name}: report outputs cannot feed equations ({', '.join(sorted(dependencies))})", code="report_feedback", details={"element": e.name, "category": "invalid_equations"})
    prepared = [(v, report_tree(v.equation, numeric_names, [t.name for t in model.tables])) for v in reports]
    # Placeholders keep original name/ID, element and retained-value accounting.
    # They are never exposed as numerical results and cannot be referenced.
    numeric_model = model.model_copy(update={"variables": [v.model_copy(update={"equation": "0", "role": "auxiliary"}) if v.role == "report" else v for v in model.variables]})
    return numeric_model, prepared


def evaluate_report(tree, values, context, tables):
    evaluator = SafeEvaluator(values, context)
    def visit(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and decode_identifier(node.func.id).upper() in {"IF", "IF_THEN_ELSE"} and canonical_name(decode_identifier(node.func.id)) not in tables:
            condition = float(evaluator.visit(node.args[0]))
            if not math.isfinite(condition):
                raise EquationError("Report condition must be finite", code="invalid_report")
            return visit(node.args[1] if condition else node.args[2])
        if isinstance(node, ast.IfExp):
            condition = float(evaluator.visit(node.test))
            if not math.isfinite(condition):
                raise EquationError("Report condition must be finite", code="invalid_report")
            return visit(node.body if condition else node.orelse)
        value = float(evaluator.visit(node))
        if not math.isfinite(value):
            raise EquationError("Numeric report results must be finite", code="invalid_report")
        return value
    return visit(tree)
