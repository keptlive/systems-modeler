"""Opt-in local feedback response analysis, using the canonical scalar evaluator."""
import math
import numpy as np
from app.core.equations import equation_features, EquationError, canonical_name
from app.core.integration import evaluate


def analyze_feedback(model, result, sample_count=8, relative_step=1e-4):
    """Estimate d(net stock rates)/d(stocks) at supplied trajectory states.

    This is local linearization, not Loops That Matter attribution/dominance.
    No full simulations are run and neither supplied model nor result is mutated.
    """
    if type(sample_count) is not int or not 1 <= sample_count <= 16:
        raise ValueError('sample_count must be an integer from 1 to 16')
    if not math.isfinite(relative_step) or not 1e-7 <= relative_step <= 1e-2:
        raise ValueError('relative_step must be between 1e-7 and 1e-2')
    elements = [*model.stocks, *model.flows, *model.variables]
    if not 1 <= len(model.stocks) <= 16 or len(elements) > 128:
        raise ValueError('Feedback analysis supports 1-16 stocks and at most 128 elements')
    from app.core.diagnostics import model_hash
    analyzed_hash = model_hash(model)
    declared_hash = (result.integration_diagnostics or {}).get('normalized_model_sha256')
    if declared_hash is not None and declared_hash != analyzed_hash:
        raise ValueError('Trajectory provenance hash does not match the analyzed model')
    provenance = dict(status='declared_hash_matches' if declared_hash else 'unverified',
                      analyzed_model_sha256=analyzed_hash,
                      requirement='Caller must supply a trajectory from this exact model and effective time settings; an absent hash cannot establish that association.')
    numeric_model = model.model_copy(update={'variables':[v for v in model.variables if getattr(v,'role',None) != 'report']})
    names = [s.name for s in model.stocks]
    if len({canonical_name(e.name) for e in elements}) != len(elements):
        raise ValueError('Ambiguous element names cannot be analyzed')
    if model.time_settings.discrete_period is not None:
        raise ValueError('Continuous-time feedback analysis does not support discrete recurrences')
    table_names = [t.name for t in model.tables]
    for element in [*numeric_model.variables, *numeric_model.flows]:
        features = equation_features(element.equation, table_names)
        if features.get('stateful_calls') or features.get('random_calls'):
            raise ValueError('Hidden-state delays/smooths and stochastic equations require expanded-state analysis')
    time = result.time
    if len(time)>100001:
        raise ValueError('Feedback trajectory exceeds 100001 retained states')
    if not time or any(not math.isfinite(t) for t in time) or any(b <= a for a,b in zip(time,time[1:])):
        raise ValueError('Trajectory times must be finite and strictly increasing')
    for name in names:
        values = result.values.get(name)
        if values is None or len(values) != len(time) or any(not math.isfinite(v) for v in values):
            raise ValueError(f'Trajectory stock series missing or invalid: {name}')
    ids = {s.id:i for i,s in enumerate(model.stocks)}
    signs = []
    for flow in model.flows:
        if any(target is not None and target not in ids for target in (flow.from_stock, flow.to_stock)):
            raise ValueError('Flow references a missing stock')
        signs.append([(ids[target], sign) for target,sign in
                      ((flow.from_stock,-1), (flow.to_stock,1)) if target is not None])
    budget = 200000
    work = 0
    evaluations = 0
    def charge(amount=1):
        nonlocal work
        work += amount
        if work > budget:
            raise ValueError('Feedback analysis equation evaluation budget exceeded')
    def rates(state, t, trajectory_index=None):
        nonlocal evaluations
        evaluations += 1
        charge(len(model.variables)+len(model.flows))
        values = evaluate(numeric_model, dict(zip(names,state)), t, model.time_settings.dt,
                          {}, {}, retry_work=charge)
        if trajectory_index is not None:
            for element in [*numeric_model.variables,*model.flows]:
                supplied = result.values.get(element.name)
                if supplied is None:
                    continue
                if len(supplied) != len(time) or not math.isfinite(supplied[trajectory_index]):
                    raise ValueError('Supplied auxiliary/flow series is invalid')
                if not math.isclose(values[element.name], supplied[trajectory_index], rel_tol=1e-7,abs_tol=1e-9):
                    raise ValueError(f'Supplied trajectory disagrees with current model equation: {element.name}')
        output = np.zeros(len(names))
        for flow, targets in zip(model.flows, signs):
            for index, sign in targets:
                output[index] += sign*values[flow.name]
        if not np.all(np.isfinite(output)):
            raise ValueError('Net stock rates are not finite')
        return output
    count = min(sample_count, len(time))
    indices = sorted({round(i*(len(time)-1)/max(1,count-1)) for i in range(count)})
    samples = []
    for index in indices:
        t = time[index]
        state = np.array([result.values[name][index] for name in names], dtype=float)
        try:
            base = rates(state,t,index)
            matrices = []
            for scale in (1., .5):
                jac = np.zeros((len(names),len(names)))
                for column in range(len(names)):
                    h = scale*relative_step*max(1.,abs(state[column]))
                    plus, minus = state.copy(), state.copy()
                    plus[column] += h
                    minus[column] -= h
                    denominator = plus[column]-minus[column]
                    if not math.isfinite(denominator) or denominator == 0:
                        raise ValueError('Perturbation cannot be represented at this state')
                    jac[:,column] = (rates(plus,t)-rates(minus,t))/denominator
                if not np.all(np.isfinite(jac)):
                    raise ValueError('Sensitivity matrix is not finite')
                matrices.append(jac)
            coarse, jac = matrices
            discrepancy = float(np.max(np.abs(jac-coarse)))
            if not math.isfinite(discrepancy):
                raise ValueError('Perturbation comparison is not finite')
            tolerance = 1e-7+1e-3*float(np.max(np.abs(jac)))
            # Compare one-sided slopes too: symmetric differences can conceal cusps.
            nonsmooth = False
            for column in range(len(names)):
                h = relative_step*.5*max(1.,abs(state[column]))
                plus = state.copy()
                plus[column] += h
                forward = (rates(plus,t)-base)/(plus[column]-state[column])
                if not np.all(np.isfinite(forward)):
                    raise ValueError('One-sided sensitivity is not finite')
                if float(np.max(np.abs(forward-jac[:,column]))) > tolerance:
                    nonsmooth = True
            eigen = np.linalg.eigvals(jac)
            if not np.all(np.isfinite(eigen)):
                raise ValueError('Local eigenvalues are not finite')
            reliable = discrepancy <= tolerance and not nonsmooth
            spectral = float(max(eigen.real))
            threshold = 1e-7*max(1.,float(np.max(np.abs(eigen))))
            indication = ('unresolved' if not reliable else 'locally_amplifying' if spectral > threshold
                          else 'locally_contracting' if spectral < -threshold else 'marginal_or_neutral')
            samples.append(dict(time=t, state=dict(zip(names,state.tolist())), net_rates=base.tolist(),
                                jacobian=jac.tolist(), eigenvalues=[dict(real=float(v.real),imag=float(v.imag)) for v in eigen],
                                spectral_abscissa=spectral, indication=indication,
                                perturbation_check=dict(half_step_difference=discrepancy, tolerance=tolerance,
                                                        one_sided_disagreement=nonsmooth),
                                self_feedback=[dict(stock=name, gain=float(jac[i,i]),
                                                    polarity='reinforcing' if jac[i,i]>threshold else 'balancing' if jac[i,i]<-threshold else 'neutral')
                                               for i,name in enumerate(names)]))
        except (EquationError, ValueError, ArithmeticError, np.linalg.LinAlgError) as exc:
            samples.append(dict(time=t, status='unresolved', reason=str(exc)))
            if work > budget:
                break
    return dict(method='local_stock_rate_jacobian', status='complete' if all('jacobian' in s for s in samples) and len(samples)==len(indices) else 'partial',
                stock_order=names, provenance=provenance, samples=samples, evaluations=evaluations, equation_work=work,
                limits=dict(max_stocks=16,max_elements=128,max_samples=16,equation_work_budget=budget),
                assumptions=['Supplied stock trajectory belongs to this model; provenance is caller responsibility.',
                             'Other stocks and time are held fixed while algebraic auxiliaries and flows are recomputed.',
                             'Eigenvalues describe infinitesimal autonomous frozen-time response, not global or transient stability.',
                             'Jacobian entry row i column j has units stock_i/(stock_j*time); eigenvalues have inverse-time units.',
                             'Perturbations may cross branch, lookup or physical-domain boundaries; disagreement marks unresolved.',
                             'Report-only text variables are excluded from numeric rate evaluation.',
                             'Self-feedback is the net response through all algebraic pathways, not an attribution to individual loops.'],
                dominance='not_computed', scientific_validity='not_established')


