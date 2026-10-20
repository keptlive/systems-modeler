"""Export the supported scalar XMILE subset without discarding tables or geometry."""
import ast
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from app.core.model import Model
from app.core.equations import preprocess_equation, canonical_name, decode_identifier, restore_identifiers

NS = 'http://docs.oasis-open.org/xmile/ns/XMILE/v1.0'
PROVENANCE_NS = 'https://stockandflow.live/ns/model'
ET.register_namespace('sf', PROVENANCE_NS)


def generate_xmile(model: Model) -> str:
    root = ET.Element('xmile', {'version': '1.0', 'xmlns': NS})
    header = ET.SubElement(root, 'header')
    ET.SubElement(header, 'name').text = model.name
    ET.SubElement(header, 'vendor').text = 'Systems Modeler'
    ET.SubElement(header, 'product', {'version': '1.1.0'}).text = 'Systems Modeler'
    ET.SubElement(header, 'created').text = datetime.now(timezone.utc).isoformat()
    specs = ET.SubElement(root, 'sim_specs', {'method': model.time_settings.integration_method})
    if model.time_settings.random_seed is not None:
        specs.set('{' + PROVENANCE_NS + '}random_seed', str(model.time_settings.random_seed))
    for tag, value in [('start', model.time_settings.start), ('stop', model.time_settings.end), ('dt', model.time_settings.dt)]:
        ET.SubElement(specs, tag).text = str(value)
    model_node = ET.SubElement(root, 'model')
    provenance = ET.SubElement(root, '{' + PROVENANCE_NS + '}provenance')
    for field in ('description', 'source', 'reference', 'category'):
        value = getattr(model, field)
        if value:
            ET.SubElement(provenance, '{' + PROVENANCE_NS + '}' + field).text = value
    variables = ET.SubElement(model_node, 'variables')
    tables = {table.name: table for table in model.tables}
    embedded = set()

    def graphical(parent, table, name=None):
        attrs = {'type': table.interpolation}
        if name is not None:
            attrs['name'] = name
        gf = ET.SubElement(parent, 'gf', attrs)
        ET.SubElement(gf, 'xpts').text = ','.join(str(x) for x, _ in table.points)
        ET.SubElement(gf, 'ypts').text = ','.join(str(y) for _, y in table.points)

    def equation(parent, text, element_name):
        # Embedded graphical functions export as their input expression + gf,
        # so another XMILE reader need not understand our LOOKUP convenience call.
        table_name = None
        try:
            expr = ast.parse(preprocess_equation(text), mode='eval').body
            if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id.upper() == 'LOOKUP' and len(expr.args) == 2:
                first = expr.args[0]
                table_name = decode_identifier(first.id) if isinstance(first, ast.Name) else first.value if isinstance(first, ast.Constant) else None
                if table_name in tables:
                    argument = restore_identifiers(ast.unparse(expr.args[1]))
                    text = argument if table_name == element_name else f'{canonical_name(table_name)}({argument})'
        except (SyntaxError, ValueError):
            pass
        ET.SubElement(parent, 'eqn').text = text.replace('**', '^')
        if table_name in tables and table_name == element_name:
            graphical(parent, tables[table_name], table_name)
            embedded.add(table_name)

    for stock in model.stocks:
        node = ET.SubElement(variables, 'stock', {'name': stock.name})
        ET.SubElement(node, 'eqn').text = stock.equation or str(stock.initial_value)
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
