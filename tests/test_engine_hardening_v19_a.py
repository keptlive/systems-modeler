"""Independent accepted-state, hidden-state and adaptive-contract regressions."""
import math
from pathlib import Path

import pytest

from app.core.equations import EquationError
from app.core.model import Model
from app.core.simulator import simulate


def transfer(method, **settings):
    return Model(stocks=[{"id":"a","name":"A","initial_value":3},
                         {"id":"b","name":"B","initial_value":7}],
                 flows=[{"name":"Transfer","equation":".4*A","from_stock":"a","to_stock":"b"}],
                 variables=[{"name":"Total","equation":"A+B"}],
                 time_settings={"start":0,"end":1.1,"dt":.25,"integration_method":method, **settings})


@pytest.mark.parametrize("method",["euler","rk4","radau"])
def test_partial_final_interval_and_simultaneous_conservation(method):
    result=simulate(transfer(method,rtol=1e-10,atol=1e-12))
    assert result.time==[0,.25,.5,.75,1,1.1]
    expected=3.
    for i,(left,right) in enumerate(zip(result.time,result.time[1:]),1):
        z=-.4*(right-left)
        if method=="euler": expected*=1+z
        elif method=="rk4": expected*=1+z+z*z/2+z**3/6+z**4/24
        else: expected=3*math.exp(-.4*right)
        assert result.values["A"][i]==pytest.approx(expected,abs=2e-10)
    assert result.values["Total"]==pytest.approx([10]*len(result.time),abs=3e-13)
    assert result.values["Transfer"]==pytest.approx([.4*x for x in result.values["A"]])


@pytest.mark.parametrize("method",["euler","rk4","radau"])
@pytest.mark.parametrize("reverse",[False,True])
@pytest.mark.parametrize("self_loop",[False,True])
def test_cancelling_large_flows_preserve_small_net_and_element_order(method,reverse,self_loop):
    flows=[{"name":"Tiny","equation":"1","to_stock":"x"}]
    if self_loop:
        flows.append({"name":"Huge","equation":"1e20","from_stock":"x","to_stock":"x"})
    else:
        flows.extend([{"name":"LargeIn","equation":"1e20","to_stock":"x"},
                      {"name":"LargeOut","equation":"1e20","from_stock":"x"}])
    model=Model(stocks=[{"id":"x","name":"X"}],flows=list(reversed(flows)) if reverse else flows,
                time_settings={"end":1,"dt":.25,"integration_method":method,"rtol":1e-10,"atol":1e-12})
    result=simulate(model)
    assert result.values["X"]==pytest.approx(result.time,abs=2e-12)


@pytest.mark.parametrize("method",["euler","rk4"])
def test_large_finite_constant_derivative_does_not_overflow_rk_weights(method):
    model=Model(stocks=[{"id":"x","name":"X"}],
                flows=[{"name":"Rate","equation":"1e308","to_stock":"x"}],
                time_settings={"end":1e-308,"dt":1e-308,"integration_method":method})
    assert simulate(model).values["X"][-1]==pytest.approx(1,abs=2e-15)


def test_subnormal_derivative_is_not_erased_before_large_dt_restores_increment():
    model=Model(stocks=[{"id":"x","name":"X"}],
                flows=[{"name":"Rate","equation":"1e-323","to_stock":"x"}],
                time_settings={"end":1e308,"dt":1e308,"integration_method":"rk4"})
    assert simulate(model).values["X"][-1]==1e308*1e-323


def test_rk4_weighted_sum_preserves_small_terms_between_cancelling_stages():
    # These are the exact four prescribed stage samples for this one RK step.
    model=Model(stocks=[{"id":"x","name":"X"}],
                flows=[{"name":"Rate","equation":"IF(TIME=0,-1e20,IF(TIME=1,1e20,1))","to_stock":"x"}],
                time_settings={"end":1,"dt":1,"integration_method":"rk4"})
    assert simulate(model).values["X"][-1]==pytest.approx(2/3,abs=1e-15)


def test_rk4_coupled_visible_hidden_stocks_have_fourth_order_convergence():
    # X'=Z, Z'=X-Z, X(0)=1, Z(0)=0; independent characteristic roots.
    rplus=(-1+math.sqrt(5))/2
    rminus=(-1-math.sqrt(5))/2
    def exact(t):
        return (-rminus*math.exp(rplus*t)+rplus*math.exp(rminus*t))/(rplus-rminus)
    errors=[]
    for dt in [.1,.05,.025]:
        model=Model(stocks=[{"id":"x","name":"X","initial_value":1}],
                    flows=[{"name":"Growth","equation":"SMOOTH(X,1,0)","to_stock":"x"}],
                    time_settings={"end":2,"dt":dt,"integration_method":"rk4"})
        result=simulate(model)
        errors.append(abs(result.values["X"][-1]-exact(2)))
        assert result.values["Growth"][0]==0
    assert 12<errors[0]/errors[1]<20
    assert 12<errors[1]/errors[2]<20


@pytest.mark.parametrize("method",["euler","rk4","radau"])
@pytest.mark.parametrize("reverse",[False,True])
def test_lazy_forward_initializers_are_order_independent(method,reverse):
    variables=[{"name":"A","equation":"IF(0,B,1)"},{"name":"B","equation":"A"},
               {"name":"Initial","equation":"2*B"}]
    model=Model(stocks=[{"id":"x","name":"X","equation":"Initial"}],
                variables=list(reversed(variables)) if reverse else variables,
                flows=[{"name":"Growth","equation":"X","to_stock":"x"}],
                time_settings={"end":1,"dt":1,"integration_method":method,"rtol":1e-10,"atol":1e-12})
    result=simulate(model)
    expected={"euler":4,"rk4":2*(1+1+.5+1/6+1/24),"radau":2*math.e}[method]
    assert result.values["X"][0]==2
    assert result.values["Growth"][0]==2
    assert result.values["X"][-1]==pytest.approx(expected,abs=2e-10)


def pulse_model(expression,clock="1",tables=None):
    return Model(stocks=[{"id":"x","name":"X","initial_value":1},
                         {"id":"y","name":"Y"}],
                 flows=[{"name":"Clock","equation":clock,"to_stock":"x"},
                        {"name":"Pulse","equation":expression,"to_stock":"y"}],
                 tables=tables or [],
                 time_settings={"end":20,"dt":.25,"integration_method":"radau","rtol":1e-9,"atol":1e-12})


@pytest.mark.parametrize("clock",["1","X"])
def test_radau_cannot_silently_skip_narrow_state_pulse(clock):
    # Exact integral is .001 for X'=1, log(2.001/2) for X'=X.
    model=pulse_model("IF(X>2 AND X<2.001,1,0)",clock)
    with pytest.raises(EquationError) as caught:simulate(model)
    assert caught.value.code=="unsupported_method_features"
    assert caught.value.details["state_discontinuities"]==[
        {"element":"Pulse","operation":"uncertified state-dependent conditional"}]


@pytest.mark.parametrize("interpolation",["continuous","discrete"])
@pytest.mark.parametrize("expression",["Forcing(X)","LOOKUP(Forcing,X)"])
def test_radau_rejects_state_lookup_rhs_until_knots_are_localized(interpolation,expression):
    model=pulse_model(expression,"X",[{"name":"Forcing","interpolation":interpolation,
                                     "points":[[0,0],[2,0],[2.00025,1],[2.00075,1],[2.001,0],[100,0]]}])
    with pytest.raises(EquationError) as caught:simulate(model)
    assert caught.value.code=="unsupported_method_features"
    assert caught.value.details["state_discontinuities"][0]["operation"]=="state-dependent lookup forcing"


def test_discontinuous_and_lookup_diagnostics_do_not_restrict_radau_trajectory():
    model=pulse_model("0","X")
    model.variables=Model(variables=[{"name":"Regime","equation":"IF(X>2 AND X<2.1,1,0)"},
                                     {"name":"Display","equation":"Forcing(X)"}]).variables
    model.tables=Model(tables=[{"name":"Forcing","points":[[0,0],[2,1],[3,0]]}]).tables
    model.time_settings.end=1
    result=simulate(model)
    assert result.values["X"][-1]==pytest.approx(math.e,abs=2e-9)
    assert result.values["Y"]==[0]*len(result.time)


@pytest.mark.parametrize("expression",[
    "IF(X>0,X,0)","IF(0<X,X,0)","IF(X>0,2*X,-X)",
    "IF(X^2>1,X^2-1,0)","MAX(X,0)","MIN(X,0)",
])
def test_continuous_feedback_remains_supported(expression):
    model=pulse_model(expression)
    model.time_settings.end=1
    result=simulate(model)
    assert len(result.time)==5
    assert all(math.isfinite(value) for series in result.values.values() for value in series)


@pytest.mark.parametrize("expression",[
    "IF(X>0,1,0)","IF(X>0,SIN(1/X),0)","IF(1/X>0,1/X,0)",
    "IF(X>LOG(100),X,2)","IF(X>0,IF(2<1<1,1,0),0)",
    "IF(X>0,IF(2=1<1,0,1),0)","(X>2)*X", "SIGN(X)",
    "IF(X<2<Y,(X-2)*(Y-2),0)",
])
def test_uncertified_or_discontinuous_rhs_is_explicitly_rejected(expression):
    with pytest.raises(EquationError) as caught:simulate(pulse_model(expression))
    assert caught.value.code=="unsupported_method_features"
    assert caught.value.details["state_discontinuities"]


def dependency_chain(count,reverse=True,method="euler"):
    variables=[{"name":f"V{i}","equation":f"V{i+1}" if i<count-1 else "1"} for i in range(count)]
    return Model(variables=variables if reverse else list(reversed(variables)),
                 time_settings={"end":1,"dt":1,"integration_method":method})


@pytest.mark.parametrize("method",["euler","rk4","radau"])
def test_failed_forward_dependency_attempts_are_bounded_work(monkeypatch,method):
    import app.core.integration as integration
    import app.core.adaptive as adaptive
    monkeypatch.setattr(integration,"MAX_WORK_UNITS",1000)
    monkeypatch.setattr(adaptive,"MAX_WORK_UNITS",1000)
    # Exercise the authored retry fallback, not the eligible DAG scheduler.
    monkeypatch.setattr(integration,"derive_execution_order",lambda model,initial=False:None)
    attempts=0
    original=integration.safe_eval
    def counted(*args,**kwargs):
        nonlocal attempts
        attempts+=1
        return original(*args,**kwargs)
    monkeypatch.setattr(integration,"safe_eval",counted)
    with pytest.raises(EquationError) as caught:simulate(dependency_chain(40,method=method))
    assert caught.value.code=="capacity_exceeded"
    assert caught.value.details["resource"]=="work_units"
    assert attempts<=1000
    assert simulate(dependency_chain(40,reverse=False,method=method)).values["V0"]==[1,1]


def test_retry_accounting_matches_actual_scalar_attempts(monkeypatch):
    import app.core.integration as integration
    # Unsupported stages still charge their real forward-dependency retries.
    monkeypatch.setattr(integration,"derive_execution_order",lambda model,initial=False:None)
    result=simulate(dependency_chain(8))
    assert result.integration_diagnostics["work_units"]==2*sum(range(1,9))
    assert result.integration_diagnostics["dependency_retries"]==2*sum(range(8))


def test_failed_random_run_retains_effective_generated_seed(monkeypatch):
    import app.core.equations as equations
    monkeypatch.setattr(equations.random.SystemRandom,"randrange",lambda *_:73129)
    model=Model(variables=[{"name":"Noise","equation":"RANDOM(0,1)"},
                           {"name":"Invalid","equation":"IF(TIME<1,1,1/0)"}],
                time_settings={"end":2,"dt":1})
    with pytest.raises(EquationError) as caught:simulate(model)
    assert caught.value.details["random_seed"]==73129
    model.time_settings.random_seed=73129
    with pytest.raises(EquationError) as repeated:simulate(model)
    assert repeated.value.code==caught.value.code
    assert repeated.value.details["time"]==caught.value.details["time"]==1


@pytest.mark.parametrize("model_id",["navier-stokes-pipe-flow-phy","common-value-auction-eco","dmp-search-matching-eco"])
def test_saved_continuous_branch_boundaries_are_certified(model_id):
    from app.core.adaptive import state_discontinuities
    path=next(Path("models").rglob(model_id+".json"))
    assert state_discontinuities(Model.model_validate_json(path.read_text()))==[]
