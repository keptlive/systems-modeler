"""XMILE file parser for System Dynamics models."""
import xml.etree.ElementTree as ET
from typing import Optional
import re
from .model import Model, Stock, Flow, Variable, Connector, Position, TimeSettings, LookupTable
from .equations import canonical_name


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
    root = ET.fromstring(xml_content)
    metadata = root.find('{https://stockandflow.live/ns/model}provenance')
    # ElementTree resolves default and prefixed namespaces for either quote style.
    for elem in root.iter():
        elem.tag = elem.tag.rsplit("}", 1)[-1]
    if root.tag != "xmile":
        raise ValueError("Expected an XMILE document")
    if len(root.findall(".//model")) > 1 or root.find(".//dimensions") is not None:
        raise ValueError("Nested models and arrays are not supported; import a scalar root model")
    unsupported = {"conveyor", "queue", "non_negative", "macro", "macros", "leak", "overflow"}
    found = sorted({element.tag for element in root.iter()} & unsupported)
    if found:
        raise ValueError("Unsupported XMILE simulation features: " + ", ".join(found))

    # Get model name
    name = "Imported Model"
    header = root.find(".//header")
    if header is not None:
        name_elem = header.find("name")
        if name_elem is not None and name_elem.text:
            name = name_elem.text

    # Get time settings
    start, end, dt = 0.0, 100.0, 1.0
    sim_specs = root.find(".//sim_specs")
    if sim_specs is not None:
        for tag, default in [("start", 0.0), ("stop", 100.0), ("dt", 1.0)]:
            elem = sim_specs.find(tag)
            if elem is not None and elem.text:
                try:
                    if tag == "start": start = float(elem.text)
                    elif tag == "stop": end = float(elem.text)
                    elif tag == "dt":
                        dt = float(elem.text)
                        if elem.get("reciprocal", "false").lower() == "true":
                            dt = 1 / dt
                except (ValueError, ZeroDivisionError) as exc:
                    raise ValueError(f"Invalid XMILE {tag}") from exc

    method = sim_specs.get("method", "euler").lower() if sim_specs is not None else "euler"
    seed = sim_specs.get('{https://stockandflow.live/ns/model}random_seed') if sim_specs is not None else None
    try:
        seed = int(seed) if seed is not None else None
    except ValueError as exc:
        raise ValueError("Invalid Stock & Flow random seed") from exc
    time_settings = TimeSettings(start=start, end=end, dt=dt, integration_method=method, random_seed=seed)

    # Parse variables - preserve underscores in names for equation compatibility
    stocks, flows, variables, tables = [], [], [], []
    stock_inflows = {}   # stock_name -> list of flow names
    stock_outflows = {}  # stock_name -> list of flow names
    model_elem = root.find(".//model")
    if model_elem is None:
        model_elem = root
    vars_elem = model_elem.find(".//variables")

    if vars_elem is not None:
        for gf in vars_elem.findall("gf"):
            name_value = gf.get("name", "").strip()
            if not name_value:
                raise ValueError("A standalone graphical function requires a name")
            tables.append(LookupTable(name=name_value, points=parse_graphical_function(gf),
                                      interpolation=gf.get("type", "continuous")))

        def import_graph(element, name_value, equation):
            gf = element.find("gf")
            if gf is None:
                return equation
            points = parse_graphical_function(gf)
            if not points:
                raise ValueError(f"Graphical function '{name_value}' has no valid points")
            table_name = gf.get("name", name_value)
            tables.append(LookupTable(name=table_name, points=points,
                                      interpolation=gf.get("type", "continuous")))
            return f"LOOKUP({table_name!r}, ({equation}))" if equation else None

        for s in vars_elem.findall("stock"):
            n = s.get("name", "").strip()
            if n:
                eqn = s.find("eqn")
                val = 0.0
                if eqn is not None and eqn.text:
                    try: val = float(eqn.text.strip())
                    except ValueError: pass
                stocks.append(Stock(name=n, initial_value=val,
                                    units=s.findtext("units"),
                                    equation=eqn.text.strip() if eqn is not None and eqn.text else "",
                                    position=Position(x=100, y=100)))

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
                eq = import_graph(f, n, eq)
                flows.append(Flow(name=n, equation=eq, units=f.findtext("units"), position=Position(x=150, y=100)))

        for a in vars_elem.findall("aux"):
            n = a.get("name", "").strip()
            if n:
                eqn = a.find("eqn")
                eq = eqn.text.strip() if eqn is not None and eqn.text else ""
                eq = import_graph(a, n, eq)
                if eq is not None:
                    variables.append(Variable(name=n, equation=eq or "0", units=a.findtext("units"), position=Position(x=200, y=100)))

    # Set flow connections based on stock inflows/outflows
    flow_map = {}
    for flow in flows:
        key = canonical_name(flow.name)
        if key in flow_map:
            raise ValueError(f"Ambiguous XMILE flow name: {flow.name}")
        flow_map[key] = flow
    def link_flow(flow_name, stock_name, endpoint):
        flow = flow_map.get(canonical_name(flow_name))
        if flow is None:
            raise ValueError(f"Stock '{stock_name}' references missing flow '{flow_name}'")
        current = getattr(flow, endpoint)
        if current is not None and current != stock_name:
            raise ValueError(f"Flow '{flow.name}' has multiple {endpoint} connections")
        setattr(flow, endpoint, stock_name)
    for stock_name, inflow_names in stock_inflows.items():
        for flow_name in inflow_names:
            link_flow(flow_name, stock_name, "to_stock")
    for stock_name, outflow_names in stock_outflows.items():
        for flow_name in outflow_names:
            link_flow(flow_name, stock_name, "from_stock")

    # Explicit inflow/outflow links are authoritative; never guess from names.

    # Get positions from view
    view = model_elem.find(".//view")
    if view is None:
        view = model_elem.find(".//views/view")
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
        description=metadata.findtext("description", "") if metadata is not None else "",
        source=metadata.findtext("source") if metadata is not None else None,
        reference=metadata.findtext("reference") if metadata is not None else None,
        category=metadata.findtext("category") if metadata is not None else None,
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
