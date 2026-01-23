"""
System dynamics simulator using PySD and custom integration methods.
Converts models to XMILE format and runs simulations.
Supports Euler and RK4 integration methods.
"""
import tempfile
import os
from typing import Optional
import numpy as np

from app.core.model import Model, TimeSettings, SimulationResult
from app.core.equations import (
    safe_eval, get_equation_variables, EquationError,
    SimulationContext
)


def normalize_name(name: str) -> str:
    """Convert a name to a valid identifier for PySD."""
    # Replace spaces and special chars with underscores
    normalized = name.replace(" ", "_").replace("-", "_")
    # Remove any remaining non-alphanumeric chars except underscore
    normalized = "".join(c if c.isalnum() or c == "_" else "_" for c in normalized)
    # Ensure it starts with a letter
    if normalized and not normalized[0].isalpha():
        normalized = "var_" + normalized
    return normalized.lower()


def model_to_xmile(model: Model) -> str:
    """Convert a Model to XMILE format for PySD."""

    # Build name mapping
    name_map = {}
    for stock in model.stocks:
        name_map[stock.id] = normalize_name(stock.name)
        name_map[stock.name] = normalize_name(stock.name)
    for flow in model.flows:
        name_map[flow.id] = normalize_name(flow.name)
        name_map[flow.name] = normalize_name(flow.name)
    for var in model.variables:
        name_map[var.id] = normalize_name(var.name)
        name_map[var.name] = normalize_name(var.name)

    def convert_equation(eq: str) -> str:
        """Convert equation variable names to normalized form."""
        if not eq:
            return "0"
        result = eq.replace("**", "^")
        # Sort by length descending to replace longer names first
        import re
        for old_name, new_name in sorted(name_map.items(), key=lambda x: -len(x[0])):
            # Use word boundaries to avoid partial replacements
            result = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, result)
        return result

    stocks_xml = []
    flows_xml = []
    aux_xml = []

    # Build stocks
    for stock in model.stocks:
        name = normalize_name(stock.name)

        # Find inflows and outflows
        inflows = []
        outflows = []
        for flow in model.flows:
            flow_name = normalize_name(flow.name)
            if flow.to_stock == stock.id or flow.to_stock == stock.name:
                inflows.append(flow_name)
            if flow.from_stock == stock.id or flow.from_stock == stock.name:
                outflows.append(flow_name)

        inflow_str = "".join(f"<inflow>{f}</inflow>" for f in inflows)
        outflow_str = "".join(f"<outflow>{f}</outflow>" for f in outflows)

        stocks_xml.append(f"""
            <stock name="{name}">
                <eqn>{stock.initial_value}</eqn>
                {inflow_str}
                {outflow_str}
            </stock>""")

    # Build flows
    for flow in model.flows:
        name = normalize_name(flow.name)
        eq = convert_equation(flow.equation) if flow.equation else "0"
        flows_xml.append(f"""
            <flow name="{name}">
                <eqn>{eq}</eqn>
            </flow>""")

    # Build auxiliary variables
    for var in model.variables:
        name = normalize_name(var.name)
        eq = convert_equation(var.equation) if var.equation else "0"
        aux_xml.append(f"""
            <aux name="{name}">
                <eqn>{eq}</eqn>
            </aux>""")

    # Combine into XMILE document
    xmile = f"""<?xml version="1.0" encoding="UTF-8"?>
<xmile version="1.0" xmlns="http://docs.oasis-open.org/xmile/ns/XMILE/v1.0">
    <header>
        <name>{model.name}</name>
        <vendor>Systems Modeler</vendor>
        <product version="1.0">Systems Modeler</product>
    </header>
    <sim_specs>
        <start>{model.time_settings.start}</start>
        <stop>{model.time_settings.end}</stop>
        <dt>{model.time_settings.dt}</dt>
    </sim_specs>
    <model>
        <variables>
            {"".join(stocks_xml)}
            {"".join(flows_xml)}
            {"".join(aux_xml)}
        </variables>
    </model>
</xmile>"""

    return xmile


def simulate_with_pysd(model: Model, time_settings: Optional[TimeSettings] = None) -> SimulationResult:
    """
    Run simulation using PySD library.

    Args:
        model: The system dynamics model to simulate
        time_settings: Optional override for time settings

    Returns:
        SimulationResult with time series data
    """
    import pysd

    settings = time_settings or model.time_settings

    # Convert model to XMILE
    xmile_content = model_to_xmile(model)

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xmile", delete=False) as f:
        f.write(xmile_content)
        temp_path = f.name

    try:
        # Load and run with PySD
        pysd_model = pysd.read_xmile(temp_path)

        # Get all variable names to return
        return_columns = []
        name_to_original = {}

        for stock in model.stocks:
            norm_name = normalize_name(stock.name)
            return_columns.append(norm_name)
            name_to_original[norm_name] = stock.name

        for flow in model.flows:
            norm_name = normalize_name(flow.name)
            return_columns.append(norm_name)
            name_to_original[norm_name] = flow.name

        for var in model.variables:
            norm_name = normalize_name(var.name)
            return_columns.append(norm_name)
            name_to_original[norm_name] = var.name

        # Run simulation
        results = pysd_model.run(
            initial_condition="original",
            return_columns=return_columns,
            time_step=settings.dt,
            final_time=settings.end
        )

        # Convert results to our format
        time_values = results.index.tolist()
        values = {}

        for col in results.columns:
            original_name = name_to_original.get(col, col)
            values[original_name] = results[col].tolist()

        return SimulationResult(time=time_values, values=values)

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


def create_simulation_context(model: Model, time: float, dt: float,
                              delay_state: dict, smooth_state: dict) -> SimulationContext:
    """Create a SimulationContext from model data."""
    # Convert lookup tables to dictionary format
    tables = {}
    for table in model.tables:
        tables[table.name] = table.to_list()

    return SimulationContext(
        time=time,
        dt=dt,
        tables=tables,
        delay_state=delay_state,
        smooth_state=smooth_state
    )


def evaluate_variables(model: Model, current_values: dict, context: SimulationContext) -> None:
    """Evaluate all variables in dependency order."""
    # Simple approach: try to evaluate each variable, retry if dependencies not met
    max_iterations = len(model.variables) + 1
    evaluated = set()

    for _ in range(max_iterations):
        progress = False
        for var in model.variables:
            if var.name in evaluated:
                continue
            try:
                current_values[var.name] = safe_eval(var.equation, current_values, context)
                evaluated.add(var.name)
                progress = True
            except EquationError:
                # Dependency not yet available
                pass

        if len(evaluated) == len(model.variables):
            break

        if not progress and len(evaluated) < len(model.variables):
            # Couldn't make progress - use 0 for remaining
            for var in model.variables:
                if var.name not in evaluated:
                    current_values[var.name] = 0.0


def evaluate_flows(model: Model, current_values: dict, context: SimulationContext) -> dict:
    """Evaluate all flows and return their values."""
    flow_values = {}
    for flow in model.flows:
        try:
            flow_values[flow.name] = safe_eval(flow.equation, current_values, context)
            current_values[flow.name] = flow_values[flow.name]
        except EquationError:
            flow_values[flow.name] = 0.0
            current_values[flow.name] = 0.0
    return flow_values


def calculate_net_flows(model: Model, flow_values: dict) -> dict:
    """Calculate net flow for each stock."""
    net_flows = {}
    for stock in model.stocks:
        net_flow = 0.0
        for flow in model.flows:
            if flow.to_stock == stock.id or flow.to_stock == stock.name:
                net_flow += flow_values.get(flow.name, 0.0)
            if flow.from_stock == stock.id or flow.from_stock == stock.name:
                net_flow -= flow_values.get(flow.name, 0.0)
        net_flows[stock.name] = net_flow
    return net_flows


def simulate_euler(model: Model, time_settings: Optional[TimeSettings] = None) -> SimulationResult:
    """
    Simulation using Euler method with full context support.

    Args:
        model: The system dynamics model to simulate
        time_settings: Optional override for time settings

    Returns:
        SimulationResult with time series data
    """
    settings = time_settings or model.time_settings
    dt = settings.dt

    # Initialize time array
    n_steps = int((settings.end - settings.start) / dt) + 1
    time_values = [settings.start + i * dt for i in range(n_steps)]

    # Initialize state for DELAY and SMOOTH functions
    delay_state = {}
    smooth_state = {}

    # Initialize values
    current_values = {"time": settings.start}

    # Set initial stock values
    for stock in model.stocks:
        if stock.equation:
            try:
                ctx = create_simulation_context(model, settings.start, dt, delay_state, smooth_state)
                current_values[stock.name] = safe_eval(stock.equation, current_values, ctx)
            except EquationError:
                current_values[stock.name] = stock.initial_value
        else:
            current_values[stock.name] = stock.initial_value

    # Initial context for first evaluation
    ctx = create_simulation_context(model, settings.start, dt, delay_state, smooth_state)

    # Initialize variables
    evaluate_variables(model, current_values, ctx)

    # Initialize flows
    flow_values = evaluate_flows(model, current_values, ctx)

    # Results storage
    results = {name: [current_values.get(name, 0.0)] for name in
               [s.name for s in model.stocks] +
               [f.name for f in model.flows] +
               [v.name for v in model.variables]}

    # Simulation loop
    for t_idx in range(1, n_steps):
        t = time_values[t_idx]
        current_values["time"] = t

        # Create context for this time step
        ctx = create_simulation_context(model, t, dt, delay_state, smooth_state)

        # Update variables first
        evaluate_variables(model, current_values, ctx)

        # Calculate flows
        flow_values = evaluate_flows(model, current_values, ctx)

        # Calculate net flows for each stock
        net_flows = calculate_net_flows(model, flow_values)

        # Update stocks using Euler method
        for stock in model.stocks:
            current_values[stock.name] = current_values[stock.name] + net_flows[stock.name] * dt

        # Record results
        for name in results:
            results[name].append(current_values.get(name, 0.0))

    return SimulationResult(time=time_values, values=results)


def simulate_rk4(model: Model, time_settings: Optional[TimeSettings] = None) -> SimulationResult:
    """
    Simulation using 4th-order Runge-Kutta method.
    More accurate than Euler for stiff systems.

    Args:
        model: The system dynamics model to simulate
        time_settings: Optional override for time settings

    Returns:
        SimulationResult with time series data
    """
    settings = time_settings or model.time_settings
    dt = settings.dt

    # Initialize time array
    n_steps = int((settings.end - settings.start) / dt) + 1
    time_values = [settings.start + i * dt for i in range(n_steps)]

    # Initialize state for DELAY and SMOOTH functions
    delay_state = {}
    smooth_state = {}

    # Initialize stock values
    stock_values = {}
    current_values = {"time": settings.start}

    for stock in model.stocks:
        if stock.equation:
            try:
                ctx = create_simulation_context(model, settings.start, dt, delay_state, smooth_state)
                stock_values[stock.name] = safe_eval(stock.equation, current_values, ctx)
            except EquationError:
                stock_values[stock.name] = stock.initial_value
        else:
            stock_values[stock.name] = stock.initial_value
        current_values[stock.name] = stock_values[stock.name]

    # Initial context
    ctx = create_simulation_context(model, settings.start, dt, delay_state, smooth_state)

    # Initialize variables and flows
    evaluate_variables(model, current_values, ctx)
    evaluate_flows(model, current_values, ctx)

    # Results storage
    results = {name: [current_values.get(name, 0.0)] for name in
               [s.name for s in model.stocks] +
               [f.name for f in model.flows] +
               [v.name for v in model.variables]}

    def compute_derivatives(t: float, stock_vals: dict) -> dict:
        """Compute derivatives (net flows) at given time and stock values."""
        vals = {"time": t}
        vals.update(stock_vals)

        ctx_local = create_simulation_context(model, t, dt, delay_state, smooth_state)
        evaluate_variables(model, vals, ctx_local)
        flow_vals = evaluate_flows(model, vals, ctx_local)

        return calculate_net_flows(model, flow_vals)

    # RK4 Simulation loop
    for t_idx in range(1, n_steps):
        t = time_values[t_idx - 1]

        # Current stock values
        y = {s.name: stock_values[s.name] for s in model.stocks}

        # k1 = f(t, y)
        k1 = compute_derivatives(t, y)

        # k2 = f(t + dt/2, y + dt/2 * k1)
        y2 = {name: y[name] + dt / 2 * k1[name] for name in y}
        k2 = compute_derivatives(t + dt / 2, y2)

        # k3 = f(t + dt/2, y + dt/2 * k2)
        y3 = {name: y[name] + dt / 2 * k2[name] for name in y}
        k3 = compute_derivatives(t + dt / 2, y3)

        # k4 = f(t + dt, y + dt * k3)
        y4 = {name: y[name] + dt * k3[name] for name in y}
        k4 = compute_derivatives(t + dt, y4)

        # Update: y(t + dt) = y(t) + dt/6 * (k1 + 2*k2 + 2*k3 + k4)
        for stock in model.stocks:
            name = stock.name
            stock_values[name] = y[name] + dt / 6 * (
                k1[name] + 2 * k2[name] + 2 * k3[name] + k4[name]
            )
            current_values[name] = stock_values[name]

        # Update time and recalculate for recording
        t_new = time_values[t_idx]
        current_values["time"] = t_new

        ctx = create_simulation_context(model, t_new, dt, delay_state, smooth_state)
        evaluate_variables(model, current_values, ctx)
        evaluate_flows(model, current_values, ctx)

        # Record results
        for name in results:
            results[name].append(current_values.get(name, 0.0))

    return SimulationResult(time=time_values, values=results)


def simulate(model: Model, time_settings: Optional[TimeSettings] = None) -> SimulationResult:
    """
    Run simulation on a model.
    Uses the integration method specified in time_settings.
    Falls back to custom methods if PySD fails.

    Args:
        model: The system dynamics model to simulate
        time_settings: Optional override for time settings

    Returns:
        SimulationResult with time series data
    """
    settings = time_settings or model.time_settings
    integration_method = getattr(settings, 'integration_method', 'euler')

    # Check if model uses advanced features not supported by PySD
    uses_advanced_features = bool(model.tables) or any(
        'DELAY' in (f.equation or '').upper() or
        'SMOOTH' in (f.equation or '').upper() or
        'PULSE' in (f.equation or '').upper() or
        'STEP' in (f.equation or '').upper() or
        'IF' in (f.equation or '').upper() or
        '<' in (f.equation or '') or
        '>' in (f.equation or '') or
        'RAMP' in (f.equation or '').upper()
        for f in model.flows
    ) or any(
        'DELAY' in (v.equation or '').upper() or
        'SMOOTH' in (v.equation or '').upper() or
        'PULSE' in (v.equation or '').upper() or
        'STEP' in (v.equation or '').upper() or
        'IF' in (v.equation or '').upper() or
        '<' in (v.equation or '') or
        '>' in (v.equation or '') or
        'RAMP' in (v.equation or '').upper()
        for v in model.variables
    )

    # Use custom integration for advanced features
    if uses_advanced_features:
        if integration_method == 'rk4':
            return simulate_rk4(model, time_settings)
        return simulate_euler(model, time_settings)

    # Try PySD first for basic models
    try:
        return simulate_with_pysd(model, time_settings)
    except Exception as e:
        print(f"PySD simulation failed, using custom integration: {e}")

    # Fall back to custom integration
    if integration_method == 'rk4':
        return simulate_rk4(model, time_settings)
    return simulate_euler(model, time_settings)
