"""XMILE file parser for System Dynamics models."""
import xml.etree.ElementTree as ET
from typing import Optional
import re
from .model import Model, Stock, Flow, Variable, Connector, Position, TimeSettings, LookupTable


def parse_graphical_function(gf_elem) -> list[tuple[float, float]]:
    """Parse a graphical function (lookup table) from XMILE XML."""
    points = []

    # Try xpts/ypts format (Stella/iThink style)
    xpts = gf_elem.find("xpts")
    ypts = gf_elem.find("ypts")
    if xpts is not None and ypts is not None and xpts.text and ypts.text:
        try:
            x_values = [float(x.strip()) for x in xpts.text.split(",")]
            y_values = [float(y.strip()) for y in ypts.text.split(",")]
            if len(x_values) == len(y_values):
                points = list(zip(x_values, y_values))
                return points
        except ValueError:
            pass

    # Try yscale/xscale with ypts format
    xscale = gf_elem.find("xscale")
    yscale = gf_elem.find("yscale")
    ypts_only = gf_elem.find("ypts")
    if xscale is not None and ypts_only is not None and ypts_only.text:
        try:
            x_min = float(xscale.get("min", 0))
            x_max = float(xscale.get("max", 1))
            y_values = [float(y.strip()) for y in ypts_only.text.split(",")]
            n_points = len(y_values)
            if n_points > 1:
                x_step = (x_max - x_min) / (n_points - 1)
                x_values = [x_min + i * x_step for i in range(n_points)]
                points = list(zip(x_values, y_values))
                return points
        except (ValueError, TypeError):
            pass

    # Try inline format with points as tuples
    # Sometimes stored as text like "(0,0),(1,1),(2,4)"
    text = gf_elem.text
    if text:
        try:
            import re
            matches = re.findall(r'\(([^,]+),([^)]+)\)', text)
            if matches:
                points = [(float(x), float(y)) for x, y in matches]
                return points
        except ValueError:
            pass

    return points


def parse_xmile(xml_content: str) -> Model:
    """Parse XMILE XML and return Model."""
    # Strip namespace prefixes for easier parsing
    xml_content = re.sub(r"xmlns[^=]*=\"[^\"]*\"", "", xml_content)
    xml_content = re.sub(r"<(/?)\w+:", r"<\1", xml_content)

    root = ET.fromstring(xml_content)

    # Get model name
    name = "Imported Model"
    header = root.find(".//header")
    if header is not None:
        name_elem = header.find("name")
        if name_elem is not None and name_elem.text:
            name = name_elem.text

    # Get time settings
    start, end, dt = 0.0, 100.0, 0.25
    sim_specs = root.find(".//sim_specs")
    if sim_specs is not None:
        for tag, default in [("start", 0.0), ("stop", 100.0), ("dt", 0.25)]:
            elem = sim_specs.find(tag)
            if elem is not None and elem.text:
                try:
                    if tag == "start": start = float(elem.text)
                    elif tag == "stop": end = float(elem.text)
                    elif tag == "dt": dt = float(elem.text)
                except: pass

    time_settings = TimeSettings(start=start, end=end, dt=dt)

    # Parse variables - preserve underscores in names for equation compatibility
    stocks, flows, variables, tables = [], [], [], []
    stock_inflows = {}   # stock_name -> list of flow names
    stock_outflows = {}  # stock_name -> list of flow names
    model_elem = root.find(".//model") or root
    vars_elem = model_elem.find(".//variables")

    if vars_elem is not None:
        for s in vars_elem.findall("stock"):
            n = s.get("name", "").strip()
            if n:
                eqn = s.find("eqn")
                val = 0.0
                if eqn is not None and eqn.text:
                    try: val = float(eqn.text.strip())
                    except: pass
                stocks.append(Stock(name=n, initial_value=val, position=Position(x=100, y=100)))

                # Parse inflows and outflows
                stock_inflows[n] = []
                stock_outflows[n] = []
                for inflow in s.findall("inflow"):
                    if inflow.text:
                        stock_inflows[n].append(inflow.text.strip())
                for outflow in s.findall("outflow"):
                    if outflow.text:
                        stock_outflows[n].append(outflow.text.strip())

        for f in vars_elem.findall("flow"):
            n = f.get("name", "").strip()
            if n:
                eqn = f.find("eqn")
                eq = "0"
                if eqn is not None and eqn.text:
                    eq = eqn.text.strip()
                flows.append(Flow(name=n, equation=eq, position=Position(x=150, y=100)))

        for a in vars_elem.findall("aux"):
            n = a.get("name", "").strip()
            if n:
                # Check if this is a graphical function (lookup table)
                gf = a.find("gf")
                if gf is not None:
                    # Parse graphical function
                    points = parse_graphical_function(gf)
                    if points:
                        tables.append(LookupTable(name=n, points=points))
                    else:
                        # Fallback to regular variable with equation "0"
                        variables.append(Variable(name=n, equation="0", position=Position(x=200, y=100)))
                else:
                    eqn = a.find("eqn")
                    eq = "0"
                    if eqn is not None and eqn.text:
                        eq = eqn.text.strip()
                    variables.append(Variable(name=n, equation=eq, position=Position(x=200, y=100)))

    # Set flow connections based on stock inflows/outflows
    flow_map = {f.name.lower(): f for f in flows}
    for stock_name, inflow_names in stock_inflows.items():
        for flow_name in inflow_names:
            f = flow_map.get(flow_name.lower())
            if f:
                f.to_stock = stock_name
    for stock_name, outflow_names in stock_outflows.items():
        for flow_name in outflow_names:
            f = flow_map.get(flow_name.lower())
            if f:
                f.from_stock = stock_name

    # If no inflows/outflows defined, infer from flow names and equations
    stock_names = {s.name.lower(): s.name for s in stocks}
    for flow in flows:
        if flow.to_stock is None and flow.from_stock is None:
            flow_lower = flow.name.lower()
            # Try to infer from common naming patterns
            # "births" -> stock "Population" if Population in equation
            # "deaths" -> from stock "Population" if Population in equation
            from app.core.equations import get_equation_variables
            eq_vars = get_equation_variables(flow.equation)
            for var in eq_vars:
                var_lower = var.lower()
                if var_lower in stock_names:
                    stock_name = stock_names[var_lower]
                    # Check if it's an inflow or outflow based on naming conventions
                    if any(kw in flow_lower for kw in ['birth', 'growth', 'increase', 'add', 'in', 'gain', 'create']):
                        flow.to_stock = stock_name
                    elif any(kw in flow_lower for kw in ['death', 'decay', 'decrease', 'remove', 'out', 'loss', 'destroy']):
                        flow.from_stock = stock_name
                    break
    
    # Get positions from view
    view = model_elem.find(".//view") or model_elem.find(".//views/view")
    if view is not None:
        stock_map = {s.name.lower(): s for s in stocks}
        flow_map = {f.name.lower(): f for f in flows}
        var_map = {v.name.lower(): v for v in variables}

        for elem in view.findall(".//stock"):
            n = elem.get("name", "").strip().lower()
            if n in stock_map:
                stock_map[n].position = Position(
                    x=float(elem.get("x", 100)),
                    y=float(elem.get("y", 100))
                )
        for elem in view.findall(".//flow"):
            n = elem.get("name", "").strip().lower()
            if n in flow_map:
                flow_map[n].position = Position(
                    x=float(elem.get("x", 150)),
                    y=float(elem.get("y", 100))
                )
        for elem in view.findall(".//aux"):
            n = elem.get("name", "").strip().lower()
            if n in var_map:
                var_map[n].position = Position(
                    x=float(elem.get("x", 200)),
                    y=float(elem.get("y", 100))
                )
    
    # Create the model first, then auto-generate connectors
    from app.core.model import generate_connectors_from_equations

    model = Model(
        name=name,
        stocks=stocks,
        flows=flows,
        variables=variables,
        connectors=[],
        tables=tables,
        time_settings=time_settings
    )

    # Auto-generate connectors from equations
    model.connectors = generate_connectors_from_equations(model)

    return model
