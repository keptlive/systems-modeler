"""Bounded, advisory dimensional analysis; never executes authored equations."""
import ast
from fractions import Fraction
from app.core.equations import (_parse_expression, preprocess_equation,
                                canonical_name, decode_identifier, EquationError, STATEFUL_FUNCTIONS, STATEFUL_ALIASES)

# None is unknown; literals have contextual units, distinct from dimensionless {}.
_LITERAL = object()
_ALIASES = {'seconds': 'second', 'sec': 'second', 's': 'second',
            'minutes': 'minute', 'min': 'minute', 'hours': 'hour',
            'days': 'day', 'years': 'year', 'dollars': 'dollar',
            'usd': 'dollar', 'people': 'person', 'persons': 'person',
            'meters': 'meter', 'metres': 'meter', 'm': 'meter',
            'dimensionless': '1', 'unitless': '1', 'fraction': '1'}


def _combine(a, b, sign=1):
    if a is None or b is None:
        return None
    a = {} if a is _LITERAL else a
    b = {} if b is _LITERAL else b
    result = dict(a)
    for key, exponent in b.items():
        result[key] = result.get(key, Fraction(0)) + sign * exponent
        if not result[key]:
            del result[key]
    if len(result) > 32 or any(abs(v) > 64 or v.denominator > 1000 for v in result.values()):
        raise ValueError('Unit expression exceeds dimensional complexity limits')
    return result


def _literal(node):
    sign = 1
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        sign = -1 if isinstance(node.op, ast.USub) else 1
        node = node.operand
    if isinstance(node, ast.Constant) and type(node.value) in (float, int):
        value = Fraction(str(node.value)) * sign
        if abs(value) <= 64 and value.denominator <= 1000:
            return value
    return None


def parse_units(text):
    """Parse explicit symbolic units. Scale conversion is deliberately unsupported."""
    if not text or not text.strip() or text.strip().lower() in {'?', 'unknown', 'n/a'}:
        return None
    text = text.strip().lower().replace('^', '**')
    text = _ALIASES.get(text, text)
    if len(text) > 512:
        raise ValueError('Unit expression is too long')
    if not text.isascii():
        raise ValueError('Non-ASCII unit symbols require explicit supported aliases')
    tree = ast.parse(text, mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 128:
        raise ValueError('Unit expression is too complex')
    def read(node, depth=0):
        if depth > 24:
            raise ValueError('Unit expression is too deep')
        if isinstance(node, ast.Name):
            name = _ALIASES.get(node.id, node.id)
            return {} if name == '1' else {name: Fraction(1)}
        if isinstance(node, ast.Constant) and type(node.value) in (int, float) and node.value == 1:
            return {}
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, (ast.Mult, ast.Div)):
                return _combine(read(node.left, depth+1), read(node.right, depth+1),
                                -1 if isinstance(node.op, ast.Div) else 1)
            if isinstance(node.op, ast.Pow):
                exponent = _literal(node.right)
                if exponent is not None:
                    return _combine({}, {k: v*exponent for k, v in read(node.left, depth+1).items()})
        raise ValueError('Use symbolic units with *, / and bounded numeric powers')
    return read(tree.body)


def _display(unit):
    return {key: str(value) for key, value in sorted(unit.items())}


def analyze_units(model, time_units=None):
    """Return JSON-safe evidence; incomplete metadata can never produce a pass."""
    if len(model.stocks)+len(model.flows)+len(model.variables) > 500 or len(model.tables) > 500:
        raise ValueError('Dimensional analysis supports at most 500 elements and 500 tables')
    if sum(len(e.equation) + len(e.units or '') for e in [*model.stocks,*model.flows,*model.variables]) > 2_000_000:
        raise ValueError('Dimensional analysis model text budget exceeded')
    report = dict(errors=[], warnings=[], unknown=[], inferred=[])
    seen = set()
    current = 'model'
    def note(kind, code, message):
        entry = (kind, current, code, message)
        if entry not in seen:
            seen.add(entry)
            report[kind].append(dict(element=current, code=code, message=message))
    def declared(text):
        try:
            value = parse_units(text)
        except (ValueError, SyntaxError, RecursionError) as exc:
            note('unknown', 'unsupported_units', str(exc))
            return None
        if value is None:
            note('unknown', 'missing_units', 'Units are not declared')
        return value
    clock = declared(time_units if time_units is not None else getattr(model.time_settings, 'units', None))
    elements = [*model.stocks, *model.flows, *model.variables]
    exact, aliases, units = {}, {}, {}
    for element in elements:
        current = element.name
        exact[element.name] = element
        aliases.setdefault(canonical_name(element.name), []).append(element)
        units[element.id] = declared(element.units)
    for key, entries in aliases.items():
        if len(entries) > 1:
            current = 'model'
            note('unknown', 'ambiguous_alias', f'Multiple elements share alias {key}')
    if len({e.id for e in elements}) != len(elements):
        current = 'model'
        note('unknown', 'duplicate_id', 'Element IDs must be unique for unit checking')
    tables = {}
    table_units = {}
    for table in model.tables:
        current = table.name
        key = canonical_name(table.name)
        if key in tables:
            note('unknown', 'ambiguous_table', f'Multiple tables share alias {key}')
        tables[key] = table
        table_units[key] = (declared(getattr(table, 'input_units', None)), declared(getattr(table, 'output_units', None)))
    visited = 0
    def match(a, b, context):
        if a is _LITERAL:
            return b
        if b is _LITERAL:
            return a
        if a is not None and b is not None and a != b:
            note('errors', 'unit_mismatch', f'{context}: {_display(a)} differs from {_display(b)}')
            return None
        return None if a is None or b is None else a
    def expr(node, depth=0):
        nonlocal visited
        visited += 1
        if visited > 100000:
            raise ValueError('Dimensional analysis expression work budget exceeded')
        if depth > 64:
            note('unknown', 'analysis_limit', 'Expression exceeds dimensional analysis depth limit')
            return None
        visit = lambda n: expr(n, depth+1)
        if isinstance(node, ast.Constant):
            if type(node.value) is bool:
                return {}
            if type(node.value) in (int, float):
                return _LITERAL
            note('unknown', 'unsupported_literal', 'Only numeric and boolean scalar literals have units')
            return None
        if isinstance(node, ast.Name):
            name = decode_identifier(node.id)
            if name.upper() in {'TIME', 'DT', 'TIME_STEP'}:
                return clock
            element = exact.get(name)
            matches = aliases.get(canonical_name(name), [])
            if element is None and len(matches) == 1:
                element = matches[0]
            if element is not None:
                return units[element.id]
            if name.upper() in {'TIME', 'DT', 'TIME_STEP'}:
                return clock
            if name.lower() in {'pi', 'e', 'true', 'false'}:
                return {}
            note('unknown', 'unknown_symbol', f'Cannot resolve units for {name}')
            return None
        if isinstance(node, ast.UnaryOp):
            value = visit(node.operand)
            if isinstance(node.op, (ast.Not, ast.Invert)):
                match(value, {}, 'Logical operand')
                return {}
            return value
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, (ast.Add, ast.Sub, ast.Mod)):
                return match(left, right, 'Arithmetic operands')
            if isinstance(node.op, ast.Pow):
                match(right, {}, 'Power exponent')
                power = _literal(node.right)
                if power is None:
                    match(left, {}, 'Nonliteral power base')
                    return {} if left == {} else None
                if left is None or left is _LITERAL:
                    return left
                return _combine({}, {key: value*power for key, value in left.items()})
            if isinstance(node.op, (ast.Mult, ast.Div, ast.FloorDiv)):
                if left is _LITERAL and right is _LITERAL:
                    return _LITERAL
                return _combine(left, right, -1 if isinstance(node.op, (ast.Div, ast.FloorDiv)) else 1)
        if isinstance(node, ast.Compare):
            values = [visit(node.left), *[visit(n) for n in node.comparators]]
            for a, b in zip(values, values[1:]):
                match(a, b, 'Comparison operands')
            return {}
        if isinstance(node, ast.BoolOp):
            for n in node.values:
                match(visit(n), {}, 'Logical operand')
            return {}
        if isinstance(node, ast.IfExp):
            match(visit(node.test), {}, 'Condition')
            return match(visit(node.body), visit(node.orelse), 'Conditional branches')
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = decode_identifier(node.func.id)
            upper = name.upper()
            if canonical_name(name) in tables or upper in {'LOOKUP', 'WITH_LOOKUP'}:
                key = canonical_name(name)
                input_node = node.args[0] if node.args else None
                if upper == 'LOOKUP' and key not in tables:
                    table_arg = node.args[0] if node.args else None
                    requested = (decode_identifier(table_arg.id) if isinstance(table_arg, ast.Name) else
                                 table_arg.value if isinstance(table_arg, ast.Constant) and isinstance(table_arg.value,str) else '')
                    key = canonical_name(requested)
                    input_node = node.args[1] if len(node.args)>1 else None
                if key in tables:
                    if len(node.args) != (2 if upper == 'LOOKUP' and canonical_name(name) not in tables else 1):
                        note('unknown', 'function_signature', 'Lookup has an invalid argument count')
                        return None
                    inp, output = table_units[key]
                    match(visit(input_node), inp, 'Lookup input axis')
                    if inp is None or output is None:
                        note('unknown', 'lookup_axis_units', 'Lookup input/output axis units are not declared')
                    return output
                if input_node is not None:
                    visit(input_node)
                note('unknown', 'lookup_axis_units', 'Inline or unresolved lookup has no declared input/output axis units')
                return None
            args = [visit(n) for n in node.args]
            counts = {'SIN':(1,1),'COS':(1,1),'TAN':(1,1),'ASIN':(1,1),'ACOS':(1,1),'ATAN':(1,1),
                      'ATAN2':(2,2),'EXP':(1,1),'LOG':(1,2),'LN':(1,2),'LOG10':(1,1),'SQRT':(1,1),
                      'ABS':(1,1),'FLOOR':(1,1),'CEIL':(1,1),'ROUND':(1,2),'SIGN':(1,1),
                      'POW':(2,3),'MOD':(2,2),'IF':(3,3),'IF_THEN_ELSE':(3,3),
                      'STEP':(2,2),'PULSE':(2,3),'RAMP':(2,3),
                      'RANDOM':(2,3),'RANDOM_UNIFORM':(2,3),'RANDOM_NORMAL':(2,3),'NORMAL':(2,3),
                      'RANDOM_BINOMIAL':(2,3),'MIN':(2,1000),'MAX':(2,1000)}
            if upper in STATEFUL_FUNCTIONS:
                is_n = STATEFUL_ALIASES.get(upper, upper) in {'DELAY_N','SMOOTH_N'}
                counts[upper] = (3,4) if is_n else (2,3)
            if node.keywords or (upper in counts and not counts[upper][0] <= len(args) <= counts[upper][1]):
                note('unknown', 'function_signature', f'Invalid dimensional signature for {upper}')
                return None
            if upper == 'POW':
                if len(args) == 3:
                    match(args[0],args[2],'POW modulus')
                    note('unknown','unsupported_function','Three-argument POW units are not established')
                    return None
                return visit(ast.BinOp(left=node.args[0], op=ast.Pow(), right=node.args[1]))
            if upper == 'MOD':
                return match(args[0],args[1],'MOD arguments')
            if upper == 'RANDOM_BINOMIAL':
                for value in args:
                    match(value, {}, 'Binomial argument')
                return {}
            if upper in {'IF', 'IF_THEN_ELSE'} and len(args) == 3:
                match(args[0], {}, 'Condition')
                return match(args[1], args[2], 'Conditional branches')
            if upper in {'SIN','COS','TAN','ASIN','ACOS','ATAN','EXP','LOG','LN','LOG10'}:
                for value in args:
                    match(value, {}, f'{upper} argument')
                return {}
            if upper == 'ATAN2' and len(args) == 2:
                match(*args, 'ATAN2 arguments')
                return {}
            if upper == 'SQRT' and len(args) == 1:
                return args[0] if args[0] is None or args[0] is _LITERAL else _combine({}, {k:v/2 for k,v in args[0].items()})
            if upper in {'ABS','FLOOR','CEIL','ROUND'} and args:
                if upper == 'ROUND' and len(args)>1:
                    match(args[1], {}, 'ROUND precision')
                return args[0]
            if upper == 'SIGN' and args:
                return {}
            if upper in {'MIN','MAX','RANDOM','RANDOM_UNIFORM','RANDOM_NORMAL','NORMAL'} and args:
                result = args[0]
                for value in args[1:2] if upper not in {'MIN','MAX'} else args[1:]:
                    result = match(result, value, f'{upper} arguments')
                if len(args) == 3 and upper not in {'MIN','MAX'}:
                    match(args[2], {}, 'Random seed')
                return result
            if upper in STATEFUL_FUNCTIONS and len(args) >= 2:
                match(args[1], clock, f'{upper} duration')
                is_n = STATEFUL_ALIASES.get(upper, upper) in {'DELAY_N', 'SMOOTH_N'}
                initial_index = 3 if is_n else 2
                if is_n and len(args) >= 3:
                    match(args[2], {}, f'{upper} order')
                if len(args) > initial_index:
                    match(args[0], args[initial_index], f'{upper} initial value')
                return args[0]
            if upper in {'STEP','PULSE','RAMP'} and len(args) >= 2:
                for value in args[1:]:
                    match(value, clock, f'{upper} timing')
                return _combine(args[0], clock, -1 if upper == 'PULSE' else 1) if upper != 'STEP' else args[0]
            note('unknown', 'unsupported_function', f'No dimensional rule for {name}')
            return None
        note('unknown', 'unsupported_expression', f'No dimensional rule for {type(node).__name__}')
        return None
    for element in elements:
        current = element.name
        if not element.equation.strip():
            if element not in model.stocks:
                note('unknown', 'missing_equation', 'Element has no equation to check')
            continue
        if getattr(element, 'role', None) == 'report':
            note('unknown', 'report_expression', 'Text report expressions are outside numeric dimensional analysis')
            continue
        try:
            result = expr(_parse_expression(preprocess_equation(element.equation)).body)
            match(units[element.id], result, 'Initializer' if element in model.stocks else 'Equation result')
            if units[element.id] is None and result is not None and result is not _LITERAL:
                report['inferred'].append(dict(element=current, units=_display(result), source='equation', advisory=True))
        except (SyntaxError, ValueError, RecursionError, TypeError, EquationError) as exc:
            note('unknown', 'analysis_error', str(exc))
    stocks = {s.id:s for s in model.stocks}
    for flow in model.flows:
        current = flow.name
        for target in (flow.from_stock, flow.to_stock):
            if target in stocks:
                try:
                    match(units[flow.id], _combine(units[target], clock, -1), f'Flow into/from {stocks[target].name} requires stock/time')
                except ValueError as exc:
                    note('unknown', 'analysis_limit', str(exc))
            elif target is not None:
                note('unknown', 'unknown_stock', 'Flow references an unknown stock')
    report['status'] = 'inconsistent' if report['errors'] else ('incomplete' if report['unknown'] else 'consistent')
    report['scientific_validity'] = 'not_established'
    report['warnings'].append(dict(element='model', code='symbolic_units_only', message='Unit scale conversions, calibration and scientific validity are not established; numeric literals take contextual units.'))
    return report



