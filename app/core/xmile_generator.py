"""Generate XMILE XML from a Model."""
import html
from datetime import datetime
from app.core.model import Model


def escape_xml(text: str) -> str:
    """Escape special characters for XML."""
    if not text:
        return ""
    return html.escape(text, quote=True)


def generate_xmile(model: Model) -> str:
    """
    Convert a Model to XMILE XML format.

    This generator creates valid XMILE files that can be used with:
    - PySD library
    - Stella/iThink
    - Vensim (via conversion)
    - Other XMILE-compatible tools
    """

    # Build stocks XML with inflow/outflow tags
    stocks_xml = []
    for stock in model.stocks:
        # Find inflows and outflows for this stock
        inflows = []
        outflows = []
        for flow in model.flows:
            if flow.to_stock == stock.id or flow.to_stock == stock.name:
                inflows.append(flow.name)
            if flow.from_stock == stock.id or flow.from_stock == stock.name:
                outflows.append(flow.name)

        inflow_tags = "".join(f"\n                <inflow>{escape_xml(f)}</inflow>" for f in inflows)
        outflow_tags = "".join(f"\n                <outflow>{escape_xml(f)}</outflow>" for f in outflows)

        pos = stock.position
        stocks_xml.append(f'''
            <stock name="{escape_xml(stock.name)}">
                <eqn>{stock.initial_value}</eqn>{inflow_tags}{outflow_tags}
                <display x="{pos.x}" y="{pos.y}"/>
            </stock>''')

    # Build flows XML
    flows_xml = []
    for flow in model.flows:
        equation = escape_xml(flow.equation)
        pos = flow.position
        flows_xml.append(f'''
            <flow name="{escape_xml(flow.name)}">
                <eqn>{equation}</eqn>
                <display x="{pos.x}" y="{pos.y}"/>
            </flow>''')

    # Build variables XML
    variables_xml = []
    for var in model.variables:
        equation = escape_xml(str(var.equation))
        pos = var.position
        variables_xml.append(f'''
            <aux name="{escape_xml(var.name)}">
                <eqn>{equation}</eqn>
                <display x="{pos.x}" y="{pos.y}"/>
            </aux>''')

    # Build lookup tables XML (graphical functions)
    gf_xml = []
    for table in model.tables:
        # Format points as XMILE gf (graphical function)
        points_str = ",".join(f"({x},{y})" for x, y in table.points)
        x_pts = ",".join(str(x) for x, _ in table.points)
        y_pts = ",".join(str(y) for _, y in table.points)
        gf_xml.append(f'''
            <aux name="{escape_xml(table.name)}">
                <gf>
                    <xpts>{x_pts}</xpts>
                    <ypts>{y_pts}</ypts>
                </gf>
            </aux>''')

    # Build connectors XML
    connectors_xml = []
    for i, conn in enumerate(model.connectors):
        connectors_xml.append(f'''
            <connector uid="{i+1}">
                <from>{escape_xml(conn.from_element)}</from>
                <to>{escape_xml(conn.to_element)}</to>
            </connector>''')

    # Use actual model time settings
    ts = model.time_settings

    xmile = f'''<?xml version="1.0" encoding="UTF-8"?>
<xmile version="1.0" xmlns="http://docs.oasis-open.org/xmile/ns/XMILE/v1.0">
    <header>
        <name>{escape_xml(model.name)}</name>
        <vendor>Systems Modeler</vendor>
        <product version="1.0">Systems Modeler</product>
        <created>{datetime.now().isoformat()}</created>
    </header>
    <sim_specs>
        <start>{ts.start}</start>
        <stop>{ts.end}</stop>
        <dt>{ts.dt}</dt>
    </sim_specs>
    <model>
        <variables>{''.join(stocks_xml)}{''.join(flows_xml)}{''.join(variables_xml)}{''.join(gf_xml)}
        </variables>
        <views>
            <view>{''.join(connectors_xml)}
            </view>
        </views>
    </model>
</xmile>'''

    return xmile
