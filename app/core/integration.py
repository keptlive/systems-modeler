"""Deterministic integration shared by HTTP, MCP and the browser.

Invalid equations fail explicitly. No fallback engine or zero substitution.
"""
import math
from app.core.model import Model, TimeSettings, SimulationResult
from app.core.equations import (EquationError, safe_eval, SimulationContext,
                                discover_stateful, advance_stateful, canonical_name,
                                RandomRuntime, stateful_derivatives, equation_features)


def simulation_context(model, t, dt, delay, smooth, random_runtime=None, input_time=None, input_snapshot=None):
    context = SimulationContext(t, dt, {table.name: table.to_list() for table in model.tables}, delay, smooth, random_runtime)
    context.table_types = {table.name: table.interpolation for table in model.tables}
    context.input_time = t if input_time is None else input_time
    context.input_snapshot = input_snapshot
    return context


def evaluate(model, stocks, t, dt, delay, smooth, initial=False, random_runtime=None, input_time=None, input_snapshot=None):
    values = dict(stocks)
    pending = [(e.name, e.equation) for e in [*model.variables, *model.flows]]
    if initial:
        pending += [(s.name, s.equation) for s in model.stocks if s.equation]
    context = simulation_context(model, t, dt, delay, smooth, random_runtime, input_time, input_snapshot)
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
    features = [equation_features(element.equation, [table.name for table in model.tables])
                for element in elements]
    random_calls = sum(feature["random_calls"] for feature in features)
    if settings.integration_method == "rk4" and (
        random_calls or any(feature["fixed_delay"] for feature in features)
    ):
        raise EquationError("RK4 with fixed-history delays or random functions is unsupported; select Euler")

    time = [min(settings.end, settings.start + i * settings.dt) for i in range(steps + 1)]
    time[-1] = settings.end
    if any(later <= earlier for earlier, later in zip(time, time[1:])):
        raise EquationError("dt cannot be represented at this time scale; increase dt or shift the time origin")
    delay, smooth = {}, {}
    random_runtime = RandomRuntime(getattr(settings, "random_seed", None))
    stocks = {s.name: s.initial_value for s in model.stocks if not s.equation}
    values = evaluate(model, stocks, time[0], settings.dt, delay, smooth, initial=True, random_runtime=random_runtime)
    stocks = {s.name: values[s.name] for s in model.stocks}
    results = {e.name: [values[e.name]] for e in elements}

    flow_links = [(flow.name,
                   reference_owners[flow.from_stock].name if flow.from_stock is not None else None,
                   reference_owners[flow.to_stock].name if flow.to_stock is not None else None)
                  for flow in model.flows]

    def derivatives(vals):
        net = {stock.name: 0.0 for stock in model.stocks}
        for name, source, destination in flow_links:
            if source is not None:
                net[source] -= vals[name]
            if destination is not None:
                net[destination] += vals[name]
        return net

    hidden_stages = sum(state["order"] for state in [*delay.values(), *smooth.values()])
    # RK4 requires four derivative evaluations and an accepted-output evaluation.
    work_per_step = max(1, len(elements) + hidden_stages + random_calls)
    work_per_step *= 5 if settings.integration_method == "rk4" else 1
    if steps * work_per_step > 1000000:
        raise EquationError("Simulation exceeds 1,000,000 work units including delay/smooth stages, stochastic calls and RK4 evaluations")

    for i in range(steps):
        t, h = time[i], time[i + 1] - time[i]
        if settings.integration_method == "euler":
            k1 = derivatives(values)
            next_stocks = {name: value + h * k1[name] for name, value in stocks.items()}
            advance_stateful(values, simulation_context(model, t, settings.dt, delay, smooth, random_runtime), h)
            stocks = next_stocks
        else:
            # Every exponential delay/smooth stage is an ordinary hidden stock.
            # Evaluate all four RK stages from matching visible and hidden states.
            hidden = {key: list(state["stages"]) for collection in (delay, smooth)
                      for key, state in collection.items()}

            input_snapshot = (values, simulation_context(model, t, settings.dt, delay, smooth, random_runtime))

            def rates(at, state, hidden_state):
                trial_delay = {key: {**entry, "stages": hidden_state[key]} for key, entry in delay.items()}
                trial_smooth = {key: {**entry, "stages": hidden_state[key]} for key, entry in smooth.items()}
                vals = evaluate(model, state, at, settings.dt, trial_delay, trial_smooth,
                                random_runtime=random_runtime, input_time=t, input_snapshot=input_snapshot)
                context = simulation_context(model, at, settings.dt, trial_delay, trial_smooth, random_runtime, input_time=t, input_snapshot=input_snapshot)
                return derivatives(vals), stateful_derivatives(vals, context)

            def trial_stocks(rates_at_stage, fraction):
                return {name: value + h * fraction * rates_at_stage[name] for name, value in stocks.items()}

            def trial_hidden(rates_at_stage, fraction):
                return {key: [value + h * fraction * rate for value, rate in zip(stage_values, rates_at_stage[key])]
                        for key, stage_values in hidden.items()}

            k1, q1 = rates(t, stocks, hidden)
            k2, q2 = rates(t + h / 2, trial_stocks(k1, .5), trial_hidden(q1, .5))
            k3, q3 = rates(t + h / 2, trial_stocks(k2, .5), trial_hidden(q2, .5))
            k4, q4 = rates(t + h, trial_stocks(k3, 1), trial_hidden(q3, 1))
            stocks = {name: value + h * (k1[name] + 2*k2[name] + 2*k3[name] + k4[name]) / 6
                      for name, value in stocks.items()}
            changes = {key: [value + h * (a + 2*b + 2*c + d) / 6
                              for value, a, b, c, d in zip(stage_values, q1[key], q2[key], q3[key], q4[key])]
                       for key, stage_values in hidden.items()}
            if not all(math.isfinite(value) for stage_values in changes.values() for value in stage_values):
                raise EquationError(f"Non-finite delay/smooth state at time {time[i + 1]:g}; reduce dt or check equations")
            for collection in (delay, smooth):
                for key, state in collection.items():
                    state["stages"] = changes[key]
        if not all(math.isfinite(v) for v in stocks.values()):
            raise EquationError(f"Non-finite stock at time {time[i + 1]:g}; reduce dt or check equations")
        random_runtime.epoch = i + 1
        values = evaluate(model, stocks, time[i + 1], settings.dt, delay, smooth, random_runtime=random_runtime)
        for name in results:
            results[name].append(values[name])
    return SimulationResult(time=time, values=results, random_seed=random_runtime.seed if random_calls else None)
