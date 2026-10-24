"""An optional scheduler must preserve evaluator semantics and actual accounting."""
from copy import deepcopy
from dataclasses import replace
import math
import pytest
from app.core.model import Model
from app.core.execution_order import derive_execution_order
from app.core.simulator import simulate
from app.core.equations import EquationError
import app.core.integration as integration

def ordered_model():
    return Model(name="DAG",stocks=[{"id":"x","name":"X","initial_value":2}],
        variables=[{"name":"twice","equation":"next * 2"},{"name":"next","equation":"X + rate"},{"name":"rate","equation":"0.1"}],
        flows=[{"name":"Growth","equation":"X * rate","to_stock":"x"}],
        time_settings={"end":2,"dt":.25,"integration_method":"rk4"})

def disable_plan(monkeypatch):
    monkeypatch.setattr(integration,"derive_execution_order",lambda model,initial=False:None)

def enable_plan(monkeypatch, counters=None):
    monkeypatch.setattr(integration,"derive_execution_order",derive_execution_order)
    original=integration._make_evaluation_plan
    def planned(model):
        plan=original(model)
        regular=derive_execution_order(model)
        initial=derive_execution_order(model,initial=True)
        return replace(plan,equations=regular if regular is not None else plan.equations,
            initial_equations=initial if initial is not None else plan.initial_equations)
    monkeypatch.setattr(integration,"_make_evaluation_plan",planned)
    if counters is not None:
        original_eval=integration.safe_eval
        original_stage=integration.evaluate
        def eval_count(*args,**kwargs):
            counters["attempts"]+=1
            return original_eval(*args,**kwargs)
        def stage_count(*args,**kwargs):
            charge=kwargs.get("retry_work")
            if charge is not None:
                def charged(*a,**k):
                    counters["retries"]+=1
                    return charge(*a,**k)
                kwargs["retry_work"]=charged
            return original_stage(*args,**kwargs)
        monkeypatch.setattr(integration,"safe_eval",eval_count)
        monkeypatch.setattr(integration,"evaluate",stage_count)

def test_stable_ready_order_and_source_unchanged():
    model=ordered_model()
    before=deepcopy(model.model_dump())
    order=derive_execution_order(model)
    assert order==(("rate","0.1"),("next","X + rate"),("twice","next * 2"),("Growth","X * rate"))
    assert isinstance(order,tuple)
    assert model.model_dump()==before
    assert derive_execution_order(Model(name="empty"))==()

@pytest.mark.parametrize("method",["euler","rk4","radau"])
def test_complete_trajectory_and_independent_growth_reference(monkeypatch,method):
    model=ordered_model()
    model.time_settings.integration_method=method
    disable_plan(monkeypatch)
    baseline=simulate(model)
    enable_plan(monkeypatch)
    scheduled=simulate(model)
    assert scheduled.time==baseline.time
    assert scheduled.values==baseline.values
    exact=[2*math.exp(.1*t) for t in scheduled.time]
    tolerance={"euler":.003,"rk4":1e-8,"radau":1e-5}[method]
    assert scheduled.values["X"]==pytest.approx(exact,rel=tolerance)

def test_initializers_and_declared_constants_have_real_dependencies(monkeypatch):
    model=Model(stocks=[{"id":"x","name":"X","equation":"factor * initial","initial_value":999},
        {"id":"s","name":"initial","initial_value":3}],
        variables=[{"name":"factor","equation":"e + pi"},{"name":"e","equation":"2"},{"name":"pi","equation":"4"}],
        time_settings={"end":1,"dt":1})
    initial=derive_execution_order(model,initial=True)
    assert [name for name,_ in initial]==["e","pi","factor","X"]
    assert [name for name,_ in derive_execution_order(model)]==["e","pi","factor"]
    disable_plan(monkeypatch)
    baseline=simulate(model)
    enable_plan(monkeypatch)
    result=simulate(model)
    assert result.values==baseline.values
    assert result.values["X"]==[18,18]

def test_quoted_unicode_aliases_follow_canonical_parser(monkeypatch):
    model=Model(variables=[{"name":"résultat","equation":'"cafe\u0301 value" + 1'},
        {"name":"café value","equation":"2"}],time_settings={"end":1,"dt":1})
    assert [name for name,_ in derive_execution_order(model)]==["café value","résultat"]
    enable_plan(monkeypatch)
    assert simulate(model).values["résultat"]==[3,3]

@pytest.mark.parametrize("equation",[
    "IF(TIME > 0, x, 0)","x if TIME else 0","x and 1","x > 0",
    "RANDOM_UNIFORM(0,1)","RANDOM_BINOMIAL(10,.5)","SMOOTH(x,1)",
    "DELAY1(x,1)","STEP(1,.5)","PULSE(1,.5)","RAMP(1,0,1)",
    "LOOKUP(Curve,x)","WITH_LOOKUP(x,((0,0),(1,1)))","missing + 1",
    "x +","'label'","1e999","UNKNOWN_FN(x)",
])
def test_unsupported_stage_returns_none_without_evaluating(equation):
    model=Model(variables=[{"name":"x","equation":"2"},{"name":"out","equation":equation}])
    assert derive_execution_order(model) is None

def test_cycles_ambiguous_aliases_and_unlowered_structure_fall_back():
    cyclic=Model(variables=[{"name":"a","equation":"b"},{"name":"b","equation":"a"}])
    assert derive_execution_order(cyclic) is None
    duplicate=Model(variables=[{"name":"a b","equation":"1"},{"name":"a_b","equation":"2"}])
    assert derive_execution_order(duplicate) is None
    assert derive_execution_order(Model(variables=[{"name":"TIME","equation":"1"}])) is None
    assert derive_execution_order(Model(dimensions=[{"name":"D","elements":["a"]}],variables=[{"name":"x","equation":"1"}])) is None
    assert derive_execution_order(Model(variables=[{"name":"label","equation":"'ok'","role":"report"}])) is None

def test_unknown_references_and_cycles_keep_original_causal_errors(monkeypatch):
    models=[Model(variables=[{"name":"dependent","equation":"root+1"},{"name":"root","equation":"missing"}]),
        Model(variables=[{"name":"a","equation":"b"},{"name":"b","equation":"a"}])]
    disable_plan(monkeypatch)
    baseline=[]
    for model in models:
        with pytest.raises(EquationError) as exc:simulate(model)
        baseline.append((exc.value.code,exc.value.details))
    enable_plan(monkeypatch)
    for model,expected in zip(models,baseline):
        with pytest.raises(EquationError) as exc:simulate(model)
        assert exc.value.code==expected[0]
        assert exc.value.details==expected[1]

def test_arithmetic_domain_failure_keeps_causal_root_and_blocked_symbols(monkeypatch):
    model=Model(variables=[{"name":"dependent","equation":"root+1"},{"name":"root","equation":"1/0"}])
    disable_plan(monkeypatch)
    with pytest.raises(EquationError) as baseline:simulate(model)
    enable_plan(monkeypatch)
    with pytest.raises(EquationError) as scheduled:simulate(model)
    assert scheduled.value.code==baseline.value.code
    for key in ("root_errors","blocked_errors"):
        # Error membership and causal attribution are unchanged.
        assert sorted(scheduled.value.details[key],key=lambda x:x["element"])==sorted(baseline.value.details[key],key=lambda x:x["element"])

def test_stochastic_fallback_preserves_seeded_sequence(monkeypatch):
    model=Model(variables=[{"name":"late","equation":"draw+1"},{"name":"draw","equation":"RANDOM_UNIFORM(0,1)"}],
        time_settings={"end":2,"dt":.25,"random_seed":123})
    assert derive_execution_order(model) is None
    disable_plan(monkeypatch)
    baseline=simulate(model)
    enable_plan(monkeypatch)
    assert simulate(model).values==baseline.values

def test_reverse60_reduces_actual_attempts_and_charged_retries(monkeypatch):
    model=Model(variables=[{"name":"x"+str(i),"equation":"1" if i==0 else "x"+str(i-1)+"+1"} for i in reversed(range(60))],
        time_settings={"end":1,"dt":1})
    counters={"attempts":0,"retries":0}
    original_eval=integration.safe_eval
    original_stage=integration.evaluate
    def eval_count(*a,**k):
        counters["attempts"]+=1
        return original_eval(*a,**k)
    def stage_count(*a,**k):
        charge=k.get("retry_work")
        if charge is not None:
            def counted_charge(*ca,**ck):
                counters["retries"]+=1
                return charge(*ca,**ck)
            k["retry_work"]=counted_charge
        return original_stage(*a,**k)
    with monkeypatch.context() as local:
        disable_plan(local)
        local.setattr(integration,"safe_eval",eval_count)
        local.setattr(integration,"evaluate",stage_count)
        baseline=simulate(model)
    assert counters=={"attempts":3660,"retries":3540}
    counters={"attempts":0,"retries":0}
    enable_plan(monkeypatch,counters)
    scheduled=simulate(model)
    assert scheduled.values==baseline.values
    assert counters=={"attempts":120,"retries":0}

def test_planning_limits_return_fallback(monkeypatch):
    import app.core.execution_order as ordering
    model=ordered_model()
    monkeypatch.setattr(ordering,"MAX_PLAN_AST_NODES",1)
    assert derive_execution_order(model) is None
    monkeypatch.setattr(ordering,"MAX_PLAN_AST_NODES",100_000)
    monkeypatch.setattr(ordering,"MAX_PLAN_EDGES",0)
    assert derive_execution_order(model) is None

def test_pure_functions_and_bare_time_symbols_are_supported():
    model=Model(variables=[{"name":"out","equation":"sin(x) + TIME + DT + TIME_STEP"},
        {"name":"x","equation":"pi / 2"}])
    assert [name for name,_ in derive_execution_order(model)]==["x","out"]



def test_named_table_that_shadows_pure_function_stays_on_existing_path():
    model=Model(variables=[{"name":"x","equation":"2"},{"name":"out","equation":"sin(x)"}],
        tables=[{"name":"sin","points":[(0,0),(3,1)]}])
    assert derive_execution_order(model) is None

def test_lazy_inactive_invalid_branch_remains_original_behavior(monkeypatch):
    model=Model(variables=[{"name":"safe","equation":"IF(1, 3, missing / 0)"}],
        time_settings={"end":1,"dt":1})
    assert derive_execution_order(model) is None
    disable_plan(monkeypatch)
    baseline=simulate(model)
    enable_plan(monkeypatch)
    assert simulate(model).values==baseline.values=={"safe":[3,3]}

def test_initializer_cycles_fall_back_but_regular_stock_levels_are_known():
    model=Model(stocks=[{"name":"A","equation":"B"},{"name":"B","equation":"A"}])
    assert derive_execution_order(model,initial=True) is None
    assert derive_execution_order(model)==()


def test_integrated_plan_is_enabled_for_reverse_dependencies():
    model=ordered_model()
    plan=integration._make_evaluation_plan(model)
    assert plan.equations == derive_execution_order(model)
    assert plan.initial_equations == derive_execution_order(model,True)

def test_multiple_causal_errors_retain_authored_order_exactly(monkeypatch):
    model=Model(variables=[
        {"name":"later_ready_root","equation":"denominator / 0"},
        {"name":"early_ready_root","equation":"sqrt(-1)"},
        {"name":"denominator","equation":"2"},
        {"name":"blocked","equation":"later_ready_root + early_ready_root"}])
    with monkeypatch.context() as local:
        disable_plan(local)
        with pytest.raises(EquationError) as baseline:simulate(model)
    with pytest.raises(EquationError) as scheduled:simulate(model)
    assert scheduled.value.code==baseline.value.code
    assert str(scheduled.value)==str(baseline.value)
    assert scheduled.value.details==baseline.value.details

def test_ineligible_regular_stage_keeps_initializer_fallback_and_source_order():
    model=Model(stocks=[{"name":"X","equation":"IF(1,2,missing)"}],
        variables=[{"name":"z","equation":"rate+1"},{"name":"rate","equation":"2"}])
    plan=integration._make_evaluation_plan(model)
    assert [name for name,_ in plan.equations]==["rate","z"]
    assert [name for name,_ in plan.initial_equations]==["z","rate","X"]

def test_actual_retry_budget_still_applies_to_unsupported_fallback(monkeypatch):
    from app.core.limits import MAX_WORK_UNITS
    model=Model(variables=[{"name":"x"+str(i),"equation":"IF(1,1,0)" if i==0 else "x"+str(i-1)+"+1"} for i in reversed(range(60))],
        time_settings={"end":1,"dt":1})
    assert derive_execution_order(model) is None
    monkeypatch.setattr(integration,"MAX_WORK_UNITS",500)
    with pytest.raises(EquationError) as exc:simulate(model)
    assert exc.value.code=="capacity_exceeded"
    assert exc.value.details["resource"]=="work_units"

def test_initializer_randomness_falls_back_only_in_its_execution_stage():
    model=Model(stocks=[{"name":"S","equation":"RANDOM_UNIFORM(0,1)"}],
        variables=[{"name":"z","equation":"x+1"},{"name":"x","equation":"2"}])
    # The initializer stage falls back; pure ordinary expressions remain eligible
    # because stocks are supplied states and no random call runs in that stage.
    assert derive_execution_order(model,initial=True) is None
    assert [name for name,_ in derive_execution_order(model)]==["x","z"]


def test_table_metadata_bound_uses_fallback_without_rejecting_model():
    model=Model(variables=[{"name":"x","equation":"1"}],
        tables=[{"name":"T"+str(i),"points":[(0,0),(1,1)]} for i in range(501)])
    assert derive_execution_order(model) is None
    plan=integration._make_evaluation_plan(model)
    assert plan.equations == (("x","1"),)


def test_unused_long_table_name_counts_toward_planner_metadata_budget(monkeypatch):
    import app.core.execution_order as ordering
    monkeypatch.setattr(ordering,"MAX_PLAN_CHARACTERS",20)
    model=Model(variables=[{"name":"x","equation":"1"}],
        tables=[{"name":"unused table name beyond budget","points":[(0,0),(1,1)]}])
    assert derive_execution_order(model) is None
    assert integration._make_evaluation_plan(model).equations == (("x","1"),)
