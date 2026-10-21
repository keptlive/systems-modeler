"""Exact finite-trial binomial law, replay, retry identity and bounded cost."""
import math
from collections import Counter
import pytest
from app.core.equations import EquationError, RandomRuntime, SimulationContext, safe_eval
from app.core.model import Model
from app.core.simulator import simulate


def samples(expression="RANDOM_BINOMIAL(2,.25)",seed=42,end=10000):
    model=Model(variables=[{"name":"Draw","equation":expression}],time_settings={"end":end,"dt":1,"random_seed":seed})
    return simulate(model)


def test_binomial_probability_mass_against_exact_combinatorial_law():
    result=samples()
    counts=Counter(result.values["Draw"])
    assert set(counts)=={0,1,2}
    n=len(result.time)
    for k in range(3):
        probability=math.comb(2,k)*.25**k*.75**(2-k)
        # Fixed seed and6sigma bound: tests the distribution, not one arbitrary
        # application-generated expected sequence.
        sigma=math.sqrt(probability*(1-probability)/n)
        assert abs(counts[k]/n-probability)<6*sigma
    assert result.integration_diagnostics["binomial_trials"]==2*n


def test_retry_and_same_accepted_time_reuse_one_sample_and_charge_once():
    runtime=RandomRuntime(123)
    context=SimulationContext(0,1,random_runtime=runtime)
    context.equation_key="Draw"
    expression="RANDOM_BINOMIAL(200,.5)"
    first=safe_eval(expression,{},context)
    assert all(safe_eval(expression,{},context)==first for _ in range(20))
    assert runtime.binomial_trials==200
    runtime.epoch=1
    context.time=1
    safe_eval(expression,{},context)
    assert runtime.binomial_trials==400


def test_identical_text_at_different_callsites_has_independent_stream_identity():
    runtime=RandomRuntime(123)
    context=SimulationContext(0,1,random_runtime=runtime)
    context.equation_key="Draw"
    safe_eval("RANDOM_BINOMIAL(200,.5)+RANDOM_BINOMIAL(200,.5)",{},context)
    assert len(runtime.binomial_streams)==2 and runtime.binomial_trials==400


def test_replay_and_explicit_seed_override():
    assert samples(seed=1,end=100).values==samples(seed=1,end=100).values
    assert samples(seed=1,end=100).values!=samples(seed=2,end=100).values
    assert samples("RANDOM_BINOMIAL(200,.5,7)",1,100).values==samples("RANDOM_BINOMIAL(200,.5,7)",2,100).values


@pytest.mark.parametrize("n,p,expected",[(0,.5,0),(100,0,0),(100,1,100)])
def test_exact_degenerate_distributions(n,p,expected):
    assert set(samples(f"RANDOM_BINOMIAL({n},{p})",end=2).values["Draw"])=={expected}


@pytest.mark.parametrize("expression",[
 "RANDOM_BINOMIAL(-1,.5)","RANDOM_BINOMIAL(1.5,.5)","RANDOM_BINOMIAL(1000001,.5)",
 "RANDOM_BINOMIAL(2,-.1)","RANDOM_BINOMIAL(2,1.1)","RANDOM_BINOMIAL(True,.5)",
 "RANDOM_BINOMIAL(2,.5,-1)"])
def test_invalid_parameters_rejected_without_truncation_or_clamping(expression):
    with pytest.raises(EquationError):samples(expression,end=2)


@pytest.mark.parametrize("method",["rk4","radau"])
def test_only_euler_has_accepted_time_random_sampling_semantics(method):
    model=Model(variables=[{"name":"X","equation":"RANDOM_BINOMIAL(2,.5)"}],
                time_settings={"end":2,"dt":1,"integration_method":method})
    with pytest.raises(EquationError):simulate(model)


def test_trials_and_integration_share_one_work_budget():
    with pytest.raises(EquationError) as caught:samples("RANDOM_BINOMIAL(500000,.5)",end=2)
    assert caught.value.code=="capacity_exceeded"
    assert caught.value.details["limit"]==1000000
    assert caught.value.details["requested"]>1000000


def test_parameter_change_at_one_accepted_time_rejected_instead_of_redrawing():
    context=SimulationContext(0,1,random_runtime=RandomRuntime(1))
    context.equation_key="Draw"
    safe_eval("RANDOM_BINOMIAL(200,P)",{"P":.5},context)
    with pytest.raises(EquationError,match="within one accepted time"):
        safe_eval("RANDOM_BINOMIAL(200,P)",{"P":.6},context)


def test_wright_fisher_form_preserves_lattice_and_absorbing_boundaries():
    model=Model(stocks=[{"id":"p","name":"P","initial_value":.5}],
                flows=[{"name":"Change","equation":"(RANDOM_BINOMIAL(200,P)/200-P)/DT","to_stock":"p"}],
                time_settings={"end":200,"dt":1,"random_seed":42})
    result=simulate(model)
    assert all(0<=p<=1 for p in result.values["P"])
    assert all(abs(200*p-round(200*p))<1e-10 for p in result.values["P"])
    for value in [0,1]:
        model.stocks[0].initial_value=value
        assert set(simulate(model).values["P"])=={value}
