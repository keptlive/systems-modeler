"""Export the supported scalar XMILE subset without discarding tables or geometry."""
import ast
import json
import io
import tokenize
import math
import re
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from app.core.model import Model
from app.core.equations import preprocess_equation, canonical_name, resolve_name, decode_identifier, restore_identifiers

NS = 'http://docs.oasis-open.org/xmile/ns/XMILE/v1.0'
PROVENANCE_NS = 'https://stockandflow.live/ns/model'
ET.register_namespace('sf', PROVENANCE_NS)
CORE_RESERVED = set(('ABS ARCCOS ARCSIN ARCTAN COS EXP INF INT LN LOG10 MAX MIN PI SIN SQRT TAN '
                     'EXPRND LOGNORMAL NORMAL POISSON RANDOM DELAY DELAY1 DELAY3 DELAYN FORCST '
                     'SMTH1 SMTH3 SMTHN TREND PULSE RAMP STEP DT STARTTIME STOPTIME TIME INIT '
                     'PREVIOUS SELF AND OR NOT IF THEN ELSE').split())


def xmile_equation(text, tables, random_seed=None, original_text=None, declared_names=()):
    """Translate verified local function aliases to OASIS XMILE 1.0 forms.

    See XMILE 1.0 sections 3.3.3, 3.5 and 3.6. Rewrites never duplicate
    arguments, so lazy branches and stochastic calls keep their evaluation count.
    """
    source = preprocess_equation(text)
    try:
        tree = ast.parse(source, mode='eval')
    except SyntaxError as exc:
        raise ValueError('Unsupported equation syntax in XMILE export; use JSON') from exc
    aliases = {'SMOOTH': 'SMTH1', 'SMOOTH3': 'SMTH3', 'SMOOTH_N': 'SMTHN',
               'DELAY_FIXED': 'DELAY', 'DELAY_N': 'DELAYN',
               'RANDOM_UNIFORM': 'RANDOM', 'RANDOM_NORMAL': 'NORMAL'}
    arities = {**{name: (2, 3) for name in ('DELAY', 'DELAY1', 'DELAY3', 'SMTH1', 'SMTH3', 'RANDOM', 'NORMAL', 'PULSE')},
               'DELAYN': (3, 4), 'SMTHN': (3, 4), 'RAMP': (2,), 'STEP': (2,),
               'LN': (1,), 'LOG10': (1,), 'ABS': (1,), 'EXP': (1,), 'SQRT': (1,),
               'SIN': (1,), 'COS': (1,), 'TAN': (1,), 'MIN': (2,), 'MAX': (2,)}
    table_names = {canonical_name(name) for name in tables}
    declared = {canonical_name(name) for name in declared_names}
    supported_nodes = (ast.Expression, ast.Constant, ast.Name, ast.Load,
                       ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
                       ast.UnaryOp, ast.UAdd, ast.USub, ast.Invert, ast.Not,
                       ast.Call, ast.Compare, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
                       ast.IfExp, ast.BoolOp, ast.And, ast.Or)
    if any(isinstance(node, ast.FloorDiv) for node in ast.walk(tree)):
        raise ValueError('Floor division is unsupported by XMILE export; use JSON')
    if any(not isinstance(node, supported_nodes) for node in ast.walk(tree)):
        raise ValueError('Unsupported expression type in XMILE export; use JSON')
    encoded = source.encode('utf-8')
    changed = False

    def render(node):
        nonlocal changed
        if isinstance(node, ast.IfExp):
            changed = True
            return f'(IF {render(node.test)} THEN {render(node.body)} ELSE {render(node.orelse)})'
        if isinstance(node, ast.Name):
            name = decode_identifier(node.id)
            if name.upper() == 'TIME_STEP':
                changed = True
                return 'DT'
            if name.lower() == 'e' and resolve_name(name, declared_names) is None:
                if resolve_name('EXP', tables) is not None:
                    raise ValueError('Constant e translation conflicts with graphical function EXP; use JSON')
                changed = True
                return 'EXP(1)'
        if isinstance(node, ast.Constant):
            try:
                number = float(node.value) if isinstance(node.value, (int, float)) else math.nan
            except OverflowError as exc:
                raise ValueError('Only finite real constants are supported by XMILE export; use JSON') from exc
            if not math.isfinite(number):
                raise ValueError('Only finite real constants are supported by XMILE export; use JSON')
            literal = encoded[node.col_offset:node.end_col_offset].decode('utf-8')
            if isinstance(node.value, bool) or not re.fullmatch(r'(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', literal):
                changed = True
                return repr(number)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.keywords:
                raise ValueError('Unsupported function syntax in XMILE export; use JSON')
            name = node.func.id.upper()
            args = [render(arg) for arg in node.args]
            # Runtime graphical-function resolution precedes built-ins. In
            # particular a table named LOG or SMOOTH must keep that meaning.
            if resolve_name(decode_identifier(node.func.id), tables) is not None:
                if len(args) != 1 or name in arities or name in {'IF', 'THEN', 'ELSE'}:
                    raise ValueError('Graphical function conflicts with XMILE built-ins or has unsupported arity; use JSON')
                return splice(node)
            if name == 'LOG':
                if len(args) not in (1, 2):
                    raise ValueError('LOG requires one or two arguments in XMILE export')
                changed = True
                if resolve_name('LN', tables) is not None:
                    raise ValueError('LOG translation conflicts with a graphical function named LN; use JSON')
                return f'LN({args[0]})' if len(args) == 1 else f'(LN({args[0]}) / LN({args[1]}))'
            if name in ('IF', 'IF_THEN_ELSE'):
                if len(args) != 3:
                    raise ValueError('IF requires three arguments in XMILE export')
                changed = True
                return f'(IF {args[0]} THEN {args[1]} ELSE {args[2]})'
            target = aliases.get(name, name)
            if (target in {'RANDOM', 'NORMAL'} and len(node.args) == 3
                    and isinstance(node.args[2], ast.Constant) and isinstance(node.args[2].value, bool)):
                raise ValueError('Boolean random seeds are unsupported by XMILE export; use an integer seed')
            if target in arities:
                if len(args) not in arities[target]:
                    raise ValueError(f'{name} signature is unsupported by XMILE export; use JSON')
            elif resolve_name(decode_identifier(node.func.id), tables) is None or len(args) != 1:
                raise ValueError(f'{name} is unsupported by XMILE export; use JSON')
            if target != name:
                if resolve_name(target, tables) is not None:
                    raise ValueError(f'{name} translation conflicts with graphical function {target}; use JSON')
                changed = True
                return f'{target}({", ".join(args)})'
        return splice(node)

    def splice(node):
        segment = encoded[node.col_offset:node.end_col_offset]
        replacements = []
        for child in ast.iter_child_nodes(node):
            if isinstance(node, ast.Call) and child is node.func:
                continue  # A graphical function named e is not the constant e.
            if hasattr(child, 'end_col_offset'):
                replacements.append((child.col_offset-node.col_offset,
                                     child.end_col_offset-node.col_offset, render(child)))
        for start, end, replacement in sorted(replacements, reverse=True):
            segment = segment[:start] + replacement.encode('utf-8') + segment[end:]
        return segment.decode('utf-8')

    rewritten = render(tree.body)
    # Keep original text when no function conversion is necessary. A rewritten
    # expression must not silently reseed implicit streams identified by column.
    output = rewritten if changed else text
    # Convert operators as tokens, never inside quoted identifiers or strings.
    tokens = []
    for token in tokenize.generate_tokens(io.StringIO(output).readline):
        value = {'**': '^', '==': '=', '!=': '<>', '%': ' MOD '}.get(token.string, token.string) if token.type == tokenize.OP else token.string
        tokens.append(token._replace(string=value))
    converted = tokenize.untokenize(tokens)
    final = restore_identifiers(converted) if changed else converted.strip()
    if random_seed is not None:
        stochastic = {'RANDOM', 'RANDOM_UNIFORM', 'NORMAL', 'RANDOM_NORMAL'}
        original_tree = ast.parse(preprocess_equation(original_text), mode='eval') if original_text is not None else tree
        before = [(n.lineno, n.col_offset) for n in ast.walk(original_tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                  and n.func.id.upper() in stochastic and len(n.args) == 2]
        after_tree = ast.parse(preprocess_equation(final), mode='eval')
        after = [(n.lineno, n.col_offset) for n in ast.walk(after_tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id.upper() in stochastic and len(n.args) == 2]
        if before != after:
            raise ValueError('XMILE translation would change implicit random stream identities; use explicit function seeds or JSON')
    return final


def generate_xmile(model: Model) -> str:
    if model.has_structure():
        raise ValueError('Structured arrays/modules require JSON export to preserve authored structure; scalar XMILE export would lose it')
    reserved = {canonical_name(name) for name in CORE_RESERVED}
    if any(canonical_name(element.name.strip()) in reserved for element in
           [*model.stocks, *model.flows, *model.variables, *model.tables]):
        raise ValueError('Element or graphical function name conflicts with reserved XMILE built-ins; use JSON')
    if model.time_settings.discrete_period is not None:
        raise ValueError("Discrete-period contracts are unsupported by this XMILE exporter; use JSON to preserve the period")
    if any(v.role == "report" for v in model.variables):
        raise ValueError("Report-only outputs are unsupported by this XMILE exporter; use JSON to preserve their roles and labels")
    if model.time_settings.integration_method == "radau":
        raise ValueError("Radau settings are unsupported by this XMILE 1.0 exporter; use JSON to preserve the method and tolerances")
    root = ET.Element('xmile', {'version': '1.0', 'xmlns': NS})
    header = ET.SubElement(root, 'header')
    ET.SubElement(header, 'name').text = model.name
    ET.SubElement(header, 'vendor').text = 'Systems Modeler'
    ET.SubElement(header, 'product', {'version': '1.1.0'}).text = 'Systems Modeler'
    ET.SubElement(header, 'created').text = datetime.now(timezone.utc).isoformat()
    specs = ET.SubElement(root, 'sim_specs', {'method': model.time_settings.integration_method})
    if model.time_settings.units:
        specs.set('time_units', model.time_settings.units)
    if model.time_settings.random_seed is not None:
        specs.set('{' + PROVENANCE_NS + '}random_seed', str(model.time_settings.random_seed))
    for tag, value in [('start', model.time_settings.start), ('stop', model.time_settings.end), ('dt', model.time_settings.dt)]:
        ET.SubElement(specs, tag).text = str(value)
    model_node = ET.SubElement(root, 'model')
    provenance = ET.SubElement(root, '{' + PROVENANCE_NS + '}provenance')
    if model.source_document is not None:
        ET.SubElement(provenance, '{' + PROVENANCE_NS + '}source_document').text = json.dumps(model.source_document.model_dump(mode='json'), ensure_ascii=False)
    for field in ('description', 'source', 'reference', 'category'):
        value = getattr(model, field)
        if value:
            ET.SubElement(provenance, '{' + PROVENANCE_NS + '}' + field).text = value
    variables = ET.SubElement(model_node, 'variables')
    tables = {table.name: table for table in model.tables}
    declared_names = [element.name for element in [*model.stocks, *model.flows, *model.variables]]
    embedded = set()

    def graphical(parent, table, name=None):
        attrs = {'type': table.interpolation}
        if name is not None:
            attrs['name'] = name
        gf = ET.SubElement(parent, 'gf', attrs)
        for field in ('input_units', 'output_units'):
            if getattr(table, field):
                gf.set('{' + PROVENANCE_NS + '}' + field, getattr(table, field))
        ET.SubElement(gf, 'xpts').text = ','.join(str(x) for x, _ in table.points)
        ET.SubElement(gf, 'ypts').text = ','.join(str(y) for _, y in table.points)

    def equation(parent, text, element_name):
        # Embedded graphical functions export as their input expression + gf,
        # so another XMILE reader need not understand our LOOKUP convenience call.
        table_name = None
        original_text = text
        try:
            expr = ast.parse(preprocess_equation(text), mode='eval').body
            if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id.upper() == 'LOOKUP' and len(expr.args) == 2:
                first = expr.args[0]
                table_name = decode_identifier(first.id) if isinstance(first, ast.Name) else first.value if isinstance(first, ast.Constant) else None
                if table_name in tables:
                    argument = restore_identifiers(ast.unparse(expr.args[1]))
                    text = argument if table_name == element_name else f'{json.dumps(table_name, ensure_ascii=False)}({argument})'
        except (SyntaxError, ValueError):
            pass
        ET.SubElement(parent, 'eqn').text = xmile_equation(text, tables, model.time_settings.random_seed, original_text, declared_names)
        if table_name in tables and table_name == element_name:
            graphical(parent, tables[table_name], table_name)
            embedded.add(table_name)

    for stock in model.stocks:
        node = ET.SubElement(variables, 'stock', {'name': stock.name})
        ET.SubElement(node, 'eqn').text = xmile_equation(stock.equation or str(stock.initial_value), tables, model.time_settings.random_seed, declared_names=declared_names)
        if stock.units:
            ET.SubElement(node, 'units').text = stock.units
        for flow in model.flows:
            if flow.to_stock in (stock.id, stock.name):
                ET.SubElement(node, 'inflow').text = flow.name
            if flow.from_stock in (stock.id, stock.name):
                ET.SubElement(node, 'outflow').text = flow.name
    for flow in model.flows:
        node = ET.SubElement(variables, 'flow', {'name': flow.name})
        equation(node, flow.equation, flow.name)
        if flow.units:
            ET.SubElement(node, 'units').text = flow.units
    for variable in model.variables:
        node = ET.SubElement(variables, 'aux', {'name': variable.name})
        equation(node, variable.equation, variable.name)
        if variable.units:
            ET.SubElement(node, 'units').text = variable.units
    for table in model.tables:
        if table.name not in embedded:
            graphical(variables, table, table.name)
    view = ET.SubElement(ET.SubElement(model_node, 'views'), 'view')
    elements = [*model.stocks, *model.flows, *model.variables]
    id_to_name = {element.id: element.name for element in elements}
    for kind, entries in [('stock', model.stocks), ('flow', model.flows), ('aux', model.variables)]:
        for element in entries:
            ET.SubElement(view, kind, {'name': element.name, 'x': str(element.position.x), 'y': str(element.position.y)})
    for i, connector in enumerate(model.connectors):
        node = ET.SubElement(view, 'connector', {'uid': str(i + 1)})
        ET.SubElement(node, 'from').text = id_to_name.get(connector.from_element, connector.from_element)
        ET.SubElement(node, 'to').text = id_to_name.get(connector.to_element, connector.to_element)
    ET.indent(root, space='  ')
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode')
