"""Deterministic integration shared by HTTP, MCP and the browser.

Invalid equations fail explicitly. No fallback engine or zero substitution.
"""
import math
import sys
from fractions import Fraction
from app.core.model import Model, TimeSettings, SimulationResult, discrete_interval_count
from app.core.limits import MAX_INTERVALS, MAX_ELEMENTS, MAX_RETAINED_VALUES, MAX_WORK_UNITS
from app.core.failure_diagnostics import stalled_evaluation, capacity_error
from app.core.equations import (EquationError, safe_eval, SimulationContext,
                                discover_stateful, advance_stateful, canonical_name,
                                RandomRuntime, stateful_derivatives, equation_features)


def _rk4_increment(h, a, b, c, d):
    # Divide weights before summation so 2*b cannot overflow. For subnormal
    # rates, division could erase a contribution that a large h would restore;
    # use a bounded four-term exact float combination in that exceptional case.
    rates = (a,b,c,d)
    if not any(0 < abs(value) < 6*sys.float_info.min for value in rates):
        try:
            return h * math.fsum((a/6,b/3,c/3,d/6))
        except OverflowError:
            pass
    exact = sum((Fraction(value)*weight for value,weight in zip(rates,(1,2,2,1))),Fraction(0))
    return float(Fraction(h)*exact/6)


def simulation_context(model, t, dt, delay, smooth, random_runtime=None, input_time=None, input_snapshot=None):
    context = SimulationContext(t, dt, {table.name: table.to_list() for table in model.tables}, delay, smooth, random_runtime)
    # A declared e/pi may be awaiting its initializer or a forward auxiliary.
    # It must not temporarily fall back to the mathematical constant.
    context.declared_names = {canonical_name(element.name)
                              for element in [*model.stocks, *model.flows, *model.variables]}
    context.table_types = {table.name: table.interpolation for table in model.tables}
    context.input_time = t if input_time is None else input_time
    context.input_snapshot = input_snapshot
    return context


def evaluate(model, stocks, t, dt, delay, smooth, initial=False, random_runtime=None, input_time=None, input_snapshot=None, retry_work=None):
    values = dict(stocks)
    pending = [(e.name, e.equation) for e in [*model.variables, *model.flows]]
    if initial:
        pending += [(s.name, s.equation) for s in model.stocks if s.equation]
    context = simulation_context(model, t, dt, delay, smooth, random_runtime, input_time, input_snapshot)
    errors = {}
    attempted = set()
    while pending:
        remaining = []
        for name, equation in pending:
            # The caller already reserves one attempt per element. Forward
            # dependencies can require many more; charge each retry before it
            # runs, including attempts that still cannot resolve a dependency.
            if name in attempted and retry_work is not None:
                retry_work()
            attempted.add(name)
            context.equation_key = name
            try:
                result = safe_eval(equation, values, context)
                if isinstance(result, complex):
                    raise EquationError("result is complex; scalar equations require real numbers", code="non_real_result")
                value = float(result)
                if not math.isfinite(value):
                    raise EquationError("result is not finite", code="non_finite_result")
            except (EquationError, ValueError, OverflowError, TypeError) as exc:
                if getattr(exc, "code", None) == "capacity_exceeded":
                    raise
                remaining.append((name, equation))
                errors[name] = exc
                continue
            values[name] = value
        if len(remaining) == len(pending):
            raise stalled_evaluation(model, remaining, errors, t, stocks)
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
    from app.core.reports import prepare_reports, evaluate_report
    period = model.time_settings.discrete_period or settings.discrete_period
    if period is not None:
        try:
            discrete_interval_count(settings.start, settings.end, period)
            if settings.dt != period or settings.integration_method != "euler":
                raise ValueError("Discrete models require Euler with the declared period")
        except ValueError as exc:
            raise EquationError(str(exc), code="discrete_period_mismatch", details={"period": period}) from exc
        settings = settings.model_copy(update={"discrete_period": period})
    numeric_model, reports = prepare_reports(model)
    if not reports:
        return _integrate_numeric(model, settings)
    interval_count = (settings.end - settings.start) / settings.dt
    if not math.isfinite(interval_count) or interval_count > MAX_INTERVALS:
        raise capacity_error("Simulation exceeds interval limit", resource="intervals", requested=interval_count, limit=MAX_INTERVALS)
    steps = discrete_interval_count(settings.start, settings.end, settings.discrete_period) if settings.discrete_period is not None else math.ceil(interval_count - 1e-10)
    report_work = (steps + 1) * len(reports)
    if report_work > MAX_WORK_UNITS:
        raise capacity_error("Reports exceed work budget", resource="work_units", requested=report_work, limit=MAX_WORK_UNITS)
    import ast
    text_capacity = (steps + 1) * sum(max([len(n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)] or [0]) for _, tree in reports)
    if text_capacity > MAX_RETAINED_VALUES:
        raise capacity_error("Reports exceed 1,000,000 retained text characters", resource="report_characters", requested=text_capacity, limit=MAX_RETAINED_VALUES)
    result = _integrate_numeric(numeric_model, settings, report_work)
    for variable, tree in reports:
        del result.values[variable.name]
    tables = {canonical_name(t.name) for t in model.tables}
    result.report_values = {variable.name: [] for variable, _ in reports}
    for index, at in enumerate(result.time) if reports else []:
        values = {name: series[index] for name, series in result.values.items()}
        context = simulation_context(model, at, settings.dt, {}, {})
        for variable, tree in reports:
            try:
                result.report_values[variable.name].append(evaluate_report(tree, values, context, tables))
            except (EquationError, ValueError, TypeError, OverflowError) as exc:
                details = {"element": variable.name, "time": at}
                if result.random_seed is not None:
                    details["random_seed"] = result.random_seed
                raise EquationError(f"Report '{variable.name}' at time {at:g}: {exc}", code="invalid_report", details=details) from exc
    return result


def _integrate_numeric(model: Model, settings: TimeSettings, report_work=0):
    elements = [*model.stocks, *model.flows, *model.variables]
    names = [canonical_name(e.name) for e in elements]
    if len(set(names)) != len(names):
        raise EquationError("Element names must be unique, including case/space/punctuation aliases", code="name_collision", details={"category": "invalid_structure", "conflicting_names": [e.name for e in elements if names.count(canonical_name(e.name)) > 1]})
    if any(name in {"time", "dt", "time_step"} for name in names):
        raise EquationError("TIME, DT and TIME_STEP are reserved simulation names", code="reserved_name", details={"category": "invalid_structure", "names": [e.name for e in elements if canonical_name(e.name) in {"time", "dt", "time_step"}]})
    reference_owners = {}
    for stock in model.stocks:
        for reference in {stock.id, stock.name}:
            if reference in reference_owners and reference_owners[reference] is not stock:
                raise EquationError(f"Ambiguous stock reference: '{reference}'")
            reference_owners[reference] = stock
    if len({canonical_name(table.name) for table in model.tables}) != len(model.tables):
        raise EquationError("Lookup table names must be unique")
    if len(elements) > MAX_ELEMENTS:
        raise capacity_error("Models are limited to 500 elements per simulation", resource="elements", requested=len(elements), limit=MAX_ELEMENTS)
    references = {s.id for s in model.stocks} | {s.name for s in model.stocks}
    for flow in model.flows:
        for endpoint in (flow.from_stock, flow.to_stock):
            if endpoint is not None and endpoint not in references:
                raise EquationError(f"Flow '{flow.name}' refers to unknown stock '{endpoint}'")

    step_count = (settings.end - settings.start) / settings.dt
    if not math.isfinite(step_count) or step_count > MAX_INTERVALS:
        raise capacity_error("Simulation exceeds 100,000 intervals; shorten the horizon or increase dt", resource="intervals", requested=step_count, limit=MAX_INTERVALS)
    steps = discrete_interval_count(settings.start, settings.end, settings.discrete_period) if settings.discrete_period is not None else math.ceil(step_count - 1e-10)
    if steps > MAX_INTERVALS:
        raise capacity_error("Simulation exceeds 100,000 intervals; shorten the horizon or increase dt", resource="intervals", requested=step_count, limit=MAX_INTERVALS)
    if (steps + 1) * max(1, len(elements)) > MAX_RETAINED_VALUES:
        raise capacity_error("Simulation exceeds 1,000,000 retained scalar values; reduce elements or intervals", resource="retained_scalar_values", requested=(steps + 1) * max(1, len(elements)), limit=MAX_RETAINED_VALUES)
    features = []
    for element in elements:
        try:
            features.append(equation_features(element.equation, [table.name for table in model.tables]))
        except EquationError as exc:
            raise EquationError(f"{element.name}: {exc}", code=getattr(exc, "code", None) or "syntax_error",
                                details={"category": "invalid_equations", "element": element.name,
                                         "element_id": element.id, "equation": element.equation}) from exc
    random_calls = sum(feature["random_calls"] for feature in features)
    if settings.integration_method == "rk4" and (
        random_calls or any(feature["fixed_delay"] for feature in features)
    ):
        raise EquationError("RK4 with fixed-history delays or random functions is unsupported; select Euler", code="unsupported_method_features", details={"category": "unsupported_capability", "method": "rk4", "random_calls": random_calls, "fixed_delay": any(feature["fixed_delay"] for feature in features)})

    if settings.integration_method == "radau":
        unsupported = sorted({call for feature in features
                              for call in feature["stateful_calls"] + feature["test_input_calls"]})
        if random_calls or unsupported:
            raise EquationError("Radau supports deterministic ODEs without random, delay/smooth or STEP/PULSE/RAMP primitives",
                                code="unsupported_method_features",
                                details={"category": "unsupported_capability", "method": "radau",
                                         "random_calls": random_calls, "unsupported_functions": unsupported})

    time = [min(settings.end, settings.start + i * settings.dt) for i in range(steps + 1)]
    time[-1] = settings.end
    if any(later <= earlier for earlier, later in zip(time, time[1:])):
        raise EquationError("dt cannot be represented at this time scale; increase dt or shift the time origin")
    if settings.integration_method == "radau":
        from app.core.adaptive import integrate_radau, time_discontinuities, state_discontinuities
        switches = time_discontinuities(model)
        if switches:
            raise EquationError("Radau does not support explicit time-triggered switches or time-driven lookup forcing, including algebraic aliases to TIME",
                                code="unsupported_method_features",
                                details={"category": "unsupported_capability", "method": "radau",
                                         "time_discontinuities": switches})
        state_switches = state_discontinuities(model)
        if state_switches:
            raise EquationError("Radau requires continuous stock feedback; state-triggered branches need certified matching limits or explicit event localization",
                                code="unsupported_method_features",
                                details={"category":"unsupported_capability", "method":"radau",
                                         "state_discontinuities":state_switches})
        return integrate_radau(model, settings, time, evaluate, report_work)
    random_runtime = RandomRuntime(getattr(settings, "random_seed", None))
    try:
        return _integrate_explicit(model, settings, time, steps, elements, reference_owners,
                                   random_calls, report_work, random_runtime)
    except EquationError as exc:
        if random_calls:
            exc.details.setdefault("random_seed", random_runtime.seed)
        raise


def _integrate_explicit(model, settings, time, steps, elements, reference_owners,
                        random_calls, report_work, random_runtime):
    delay, smooth = {}, {}
    evaluations = steps * (5 if settings.integration_method == "rk4" else 1) + 1
    ordinary_work = evaluations * max(1, len(elements) + random_calls) + report_work
    retry_units = 0

    def retry_work():
        nonlocal retry_units
        retry_units += 1
        requested = ordinary_work + retry_units
        if requested > MAX_WORK_UNITS:
            raise capacity_error("Equation dependency retries exceed work budget", resource="work_units",
                                 requested=requested, limit=MAX_WORK_UNITS)
        random_runtime.reserve_work(requested)

    if ordinary_work > MAX_WORK_UNITS:
        raise capacity_error("Simulation exceeds work budget including initial evaluation", resource="work_units",
                             requested=ordinary_work, limit=MAX_WORK_UNITS)
    random_runtime.reserve_work(ordinary_work)
    stocks = {s.name: s.initial_value for s in model.stocks if not s.equation}
    values = evaluate(model, stocks, time[0], settings.dt, delay, smooth, initial=True, random_runtime=random_runtime, retry_work=retry_work)
    stocks = {s.name: values[s.name] for s in model.stocks}
    results = {e.name: [values[e.name]] for e in elements}

    flow_links = [(flow.name,
                   reference_owners[flow.from_stock].name if flow.from_stock is not None else None,
                   reference_owners[flow.to_stock].name if flow.to_stock is not None else None)
                  for flow in model.flows]

    def derivatives(vals):
        terms = {stock.name: [] for stock in model.stocks}
        for name, source, destination in flow_links:
            if source is not None:
                terms[source].append(-vals[name])
            if destination is not None:
                terms[destination].append(vals[name])
        return {name: math.fsum(values) for name,values in terms.items()}

    hidden_stages = sum(state["order"] for state in [*delay.values(), *smooth.values()])
    # RK4 requires four derivative evaluations and an accepted-output evaluation.
    work_per_step = max(1, len(elements) + hidden_stages + random_calls)
    work_per_step *= 5 if settings.integration_method == "rk4" else 1
    ordinary_work = steps * work_per_step + max(1, len(elements) + random_calls) + report_work
    if ordinary_work + retry_units > MAX_WORK_UNITS:
        raise capacity_error("Simulation exceeds 1,000,000 work units including delay/smooth stages, stochastic calls and RK4 evaluations", resource="work_units", requested=ordinary_work + retry_units, limit=MAX_WORK_UNITS)

    random_runtime.reserve_work(ordinary_work + retry_units)

    for i in range(steps):
        t, h = time[i], settings.discrete_period if settings.discrete_period is not None else time[i + 1] - time[i]
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
                                random_runtime=random_runtime, input_time=t, input_snapshot=input_snapshot, retry_work=retry_work)
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
            stocks = {name: value + _rk4_increment(h,k1[name],k2[name],k3[name],k4[name])
                      for name, value in stocks.items()}
            changes = {key: [value + _rk4_increment(h,a,b,c,d)
                              for value, a, b, c, d in zip(stage_values, q1[key], q2[key], q3[key], q4[key])]
                       for key, stage_values in hidden.items()}
            if not all(math.isfinite(value) for stage_values in changes.values() for value in stage_values):
                raise EquationError(f"Non-finite delay/smooth state at time {time[i + 1]:g}; reduce dt or check equations")
            for collection in (delay, smooth):
                for key, state in collection.items():
                    state["stages"] = changes[key]
        if not all(math.isfinite(v) for v in stocks.values()):
            raise EquationError(f"Non-finite stock at time {time[i + 1]:g}; reduce dt or check equations", code="non_finite_stock", details={"category": "invalid_equations", "time": time[i + 1], "stocks": [name for name, value in stocks.items() if not math.isfinite(value)], "previous_stock_values": {s.name: values[s.name] for s in model.stocks}})
        random_runtime.epoch = i + 1
        values = evaluate(model, stocks, time[i + 1], settings.dt, delay, smooth, random_runtime=random_runtime, retry_work=retry_work)
        for name in results:
            results[name].append(values[name])
    return SimulationResult(time=time, values=results, random_seed=random_runtime.seed if random_calls else None,
                            integration_diagnostics={"method": settings.integration_method,
                                                     "binomial_trials": random_runtime.binomial_trials,
                                                     "work_units": ordinary_work + retry_units + random_runtime.binomial_trials,
                                                     "dependency_retries": retry_units,
                                                     "report_evaluations": report_work,
                                                     "work_unit_limit": MAX_WORK_UNITS}
                            if random_runtime.binomial_streams or report_work or retry_units else None)
