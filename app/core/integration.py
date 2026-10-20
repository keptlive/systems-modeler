"""Deterministic integration shared by HTTP, MCP and the browser.

Invalid equations fail explicitly. No fallback engine or zero substitution.
"""
import math
import re
from app.core.model import Model, TimeSettings, SimulationResult
from app.core.equations import (EquationError, safe_eval, SimulationContext,
                                discover_stateful, advance_stateful, canonical_name)


def simulation_context(model, t, dt, delay, smooth):
    context = SimulationContext(t, dt, {table.name: table.to_list() for table in model.tables}, delay, smooth)
    context.table_types = {table.name: table.interpolation for table in model.tables}
    return context


def evaluate(model, stocks, t, dt, delay, smooth, initial=False):
    values = dict(stocks)
    pending = [(e.name, e.equation) for e in [*model.variables, *model.flows]]
    if initial:
        pending += [(s.name, s.equation) for s in model.stocks if s.equation]
    context = simulation_context(model, t, dt, delay, smooth)
    errors = {}
    while pending:
        remaining = []
        for name, equation in pending:
            context.equation_key = name
            try:
                value = float(safe_eval(equation, values, context))
                if not math.isfinite(value):
                    raise EquationError("result is not finite")
            except (EquationError, ValueError, OverflowError, TypeError) as exc:
                remaining.append((name, equation))
                errors[name] = str(exc)
                continue
            values[name] = value
        if len(remaining) == len(pending):
            details = "; ".join(f"{name}: {errors[name]}" for name, _ in remaining)
            raise EquationError(f"Unresolved or invalid equations at time {t:g}: {details}")
        pending = remaining
    # A conditional controls its output, not the passage of time in hidden stocks.
    for element in ([*model.variables, *model.flows] if initial else []):
        context.equation_key = element.name
        try:
            discover_stateful(element.equation, values, context)
        except (EquationError, ValueError, OverflowError, TypeError) as exc:
            raise EquationError(f"Stateful equation '{element.name}' at time {t:g}: {exc}") from exc
    if not all(math.isfinite(value) for value in values.values()):
        raise EquationError(f"Non-finite initial stock or equation at time {t:g}")
    return values


def integrate(model: Model, settings: TimeSettings):
    elements = [*model.stocks, *model.flows, *model.variables]
    names = [canonical_name(e.name) for e in elements]
    if len(set(names)) != len(names):
        raise EquationError("Element names must be unique, including case/space/punctuation aliases")
    if any(name in {"time", "dt", "time_step"} for name in names):
        raise EquationError("TIME, DT and TIME_STEP are reserved simulation names")
    reference_owners = {}
    for stock in model.stocks:
        for reference in {stock.id, stock.name}:
            if reference in reference_owners and reference_owners[reference] is not stock:
                raise EquationError(f"Ambiguous stock reference: '{reference}'")
            reference_owners[reference] = stock
    if len({canonical_name(table.name) for table in model.tables}) != len(model.tables):
        raise EquationError("Lookup table names must be unique")
    if len(elements) > 500:
        raise EquationError("Models are limited to 500 elements per simulation")
    references = {s.id for s in model.stocks} | {s.name for s in model.stocks}
    for flow in model.flows:
        for endpoint in (flow.from_stock, flow.to_stock):
            if endpoint is not None and endpoint not in references:
                raise EquationError(f"Flow '{flow.name}' refers to unknown stock '{endpoint}'")

    step_count = (settings.end - settings.start) / settings.dt
    if not math.isfinite(step_count) or step_count > 10000:
        raise EquationError("Simulation exceeds 10,000 steps; increase dt")
    steps = math.ceil(step_count - 1e-10)
    if steps > 10000 or steps * max(1, len(elements)) > 1000000:
        raise EquationError("Simulation exceeds 10,000 steps or 1,000,000 element steps; increase dt")
    equations = " ".join(e.equation for e in elements)
    if settings.integration_method == "rk4" and re.search(
        r"\b(DELAY\w*|SMOOTH\w*|SMTH\w*|RANDOM\w*)\s*\(", equations, re.I
    ):
        raise EquationError("RK4 with stateful delay/smooth or random functions is unsupported; select Euler")

    time = [min(settings.end, settings.start + i * settings.dt) for i in range(steps + 1)]
    time[-1] = settings.end
    if any(later <= earlier for earlier, later in zip(time, time[1:])):
        raise EquationError("dt cannot be represented at this time scale; increase dt or shift the time origin")
    delay, smooth = {}, {}
    stocks = {s.name: s.initial_value for s in model.stocks if not s.equation}
    values = evaluate(model, stocks, time[0], settings.dt, delay, smooth, initial=True)
    stocks = {s.name: values[s.name] for s in model.stocks}
    results = {e.name: [values[e.name]] for e in elements}

    def derivatives(vals):
        net = {s.name: 0.0 for s in model.stocks}
        for stock in model.stocks:
            for flow in model.flows:
                if flow.to_stock in (stock.id, stock.name):
                    net[stock.name] += vals[flow.name]
                if flow.from_stock in (stock.id, stock.name):
                    net[stock.name] -= vals[flow.name]
        return net

    hidden_stages = sum(state["order"] for state in [*delay.values(), *smooth.values()])
    if steps * max(1, len(elements) + hidden_stages) > 1000000:
        raise EquationError("Simulation exceeds 1,000,000 element steps including delay/smooth stages")

    for i in range(steps):
        t, h = time[i], time[i + 1] - time[i]
        if settings.integration_method == "euler":
            k1 = derivatives(values)
            next_stocks = {name: value + h * k1[name] for name, value in stocks.items()}
            advance_stateful(values, simulation_context(model, t, settings.dt, delay, smooth), h)
            stocks = next_stocks
        else:
            def rates(at, state):
                return derivatives(evaluate(model, state, at, settings.dt, {}, {}))
            k1 = rates(t, stocks)
            k2 = rates(t + h / 2, {n: v + h * k1[n] / 2 for n, v in stocks.items()})
            k3 = rates(t + h / 2, {n: v + h * k2[n] / 2 for n, v in stocks.items()})
            k4 = rates(t + h, {n: v + h * k3[n] for n, v in stocks.items()})
            stocks = {n: v + h * (k1[n] + 2*k2[n] + 2*k3[n] + k4[n]) / 6
                      for n, v in stocks.items()}
        if not all(math.isfinite(v) for v in stocks.values()):
            raise EquationError(f"Non-finite stock at time {time[i + 1]:g}; reduce dt or check equations")
        values = evaluate(model, stocks, time[i + 1], settings.dt, delay, smooth)
        for name in results:
            results[name].append(values[name])
    return SimulationResult(time=time, values=results)
