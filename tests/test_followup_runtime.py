"""Regressions for bounded input rounding and runtime ownership."""
import math
import pytest
from app.core.equations import (EquationError, SimulationContext, discover_stateful,
                                safe_eval, step_function)
from app.core.model import Model, LookupTable
from app.core.simulator import simulate

@pytest.mark.parametrize("method", ["euler", "rk4"])
def test_step_decimal_boundary_and_accepted_interval_series(method):
    model = Model(stocks=[{"id":"s","name":"Stock","initial_value":0}],
                  flows=[{"name":"Rate","equation":"STEP(10,.9)","to_stock":"s"}],
                  time_settings={"start":0,"end":1.2,"dt":.3,"integration_method":method})
    result = simulate(model)
    assert result.time[3] == .8999999999999999
    assert result.values["Rate"] == [0,0,0,10,10]
    # Rounding must not make RK4's preceding interval consume the event.
    assert result.values["Stock"] == pytest.approx([0,0,0,0,3])

@pytest.mark.parametrize("start,dt,event,end,index", [
    (.3,.1,.4,.6,1), (0,.01,.35,.4,35), (-.9,.3,0,.3,3),
])
def test_other_step_grids(start,dt,event,end,index):
    model=Model(variables=[{"name":"Value","equation":f"STEP(2,{event})"}],
                time_settings={"start":start,"end":end,"dt":dt})
    values=simulate(model).values["Value"]
    assert values[:index] == [0]*index
    assert values[index:] == [2]*(len(values)-index)

def test_step_rounding_bound_does_not_swallow_small_or_off_grid_events():
    assert step_function(10,.9,.9)==10  # original three-argument API
    assert safe_eval("STEP(10,.900000001)",{},SimulationContext(time=3*.3,dt=.3))==0
    assert safe_eval("STEP(10,1.0000001e-12)",{},SimulationContext(time=1e-12,dt=1e-12))==0
    # A huge unrelated timestep must not create a relative-time epsilon.
    assert safe_eval("STEP(10,1.000001)",{},SimulationContext(time=1,dt=1e20))==0
    # Cap the ULP allowance below a real tiny timestep even at large origins.
    t=1e12
    assert safe_eval(f"STEP(10,{math.nextafter(t,math.inf)!r})",{},SimulationContext(time=t,dt=1e-6))==0

@pytest.mark.parametrize("method", ["euler","rk4"])
def test_omitted_ramp_end_keeps_negative_start_ramping_full_series(method):
    model=Model(variables=[{"name":"Value","equation":"RAMP(1,-1)"}],
                time_settings={"start":-2,"end":2,"dt":.5,"integration_method":method})
    assert simulate(model).values["Value"] == [0,0,0,.5,1,1.5,2,2.5,3]

@pytest.mark.parametrize("expr,expected", [
    ("RAMP(1,-1,0)",[0,0,0,.5,1,1,1,1,1]),
    ("RAMP(-2,-1)",[0,0,0,-1,-2,-3,-4,-5,-6]),
    ("RAMP(1,1,0)",[0,0,0,0,0,0,0,.5,1]),
    ("RAMP(1,1,-1)",[0,0,0,0,0,0,0,.5,1]),
])
def test_explicit_ramp_contract_and_negative_slope(expr,expected):
    model=Model(variables=[{"name":"Value","equation":expr}],
                time_settings={"start":-2,"end":2,"dt":.5})
    assert simulate(model).values["Value"]==expected

@pytest.mark.parametrize("name,call",[("SMOOTH","SMOOTH"),("DELAY","delay"),("SMOOTH","\"smooth\"")])
@pytest.mark.parametrize("method",["euler","rk4"])
def test_inactive_stateful_named_table_respects_lazy_branch(name,call,method):
    model=Model(variables=[{"name":"Value","equation":f"IF_THEN_ELSE(0,{call}(1/0),1)"}],
                tables=[{"name":name,"points":[(0,10),(1,20)]}],
                time_settings={"end":1,"dt":.25,"integration_method":method})
    assert simulate(model).values["Value"]==[1]*5

def test_discovery_still_initializes_real_nested_hidden_state_once():
    context=SimulationContext(tables={"DELAY":[(0,10),(1,20)]})
    equation="IF_THEN_ELSE(0,DELAY(SMOOTH(10,1,2)),1)"
    discover_stateful(equation,{},context)
    assert not context.delay_state
    assert len(context.smooth_state)==1
    key=next(iter(context.smooth_state))
    assert context.smooth_state[key]["initial"]==2
    discover_stateful(equation,{},context)
    assert list(context.smooth_state)==[key]

def test_active_table_and_real_inactive_hidden_stock_remain_distinct():
    context=SimulationContext(tables={"DELAY":[(0,10),(1,20)]})
    assert safe_eval("DELAY(.5)",{},context)==15
    discover_stateful("IF_THEN_ELSE(0,SMOOTH(10,1,2),1)",{},context)
    assert len(context.smooth_state)==1

@pytest.mark.parametrize("expr,expected",[("REM(-10,3)",-1),("REM(10,-3)",1),
                                         ("REM(-10,-3)",-1),("REM(1e16,3)",1)])
def test_rem_is_the_truncated_remainder_extension(expr,expected):
    assert safe_eval(expr,{})==expected

@pytest.mark.parametrize("expr",["REM(1,0)","REM(1e309,3)","REM(1,1e309)","REM(1)"])
def test_rem_rejects_zero_nonfinite_and_wrong_arity(expr):
    with pytest.raises(EquationError):safe_eval(expr,{})

def test_rem_lookup_table_retains_runtime_ownership():
    assert safe_eval("REM(.5)",{},SimulationContext(tables={"REM":[(0,10),(1,20)]}))==15


def test_rem_preserves_signed_zero_and_finite_extreme_ratio():
    value=safe_eval("REM(-0.0,3)",{})
    assert value==0 and math.copysign(1,value)==-1
    assert safe_eval("REM(1e308,1e-308)",{})==math.fmod(1e308,1e-308)


def test_unused_table_does_not_change_seeded_random_or_hidden_state():
    model=Model(variables=[{"name":"Draw","equation":"RANDOM(0,1)"},
                           {"name":"Hidden","equation":"SMOOTH(10,1,2)"}],
                time_settings={"end":1,"dt":.25,"random_seed":17})
    before=simulate(model)
    with_table=model.model_copy(update={"tables":[LookupTable(name="DELAY",points=[(0,10),(1,20)])]})
    assert simulate(with_table).values==before.values


@pytest.mark.parametrize("expr,time,expected",[
    ("RAMP_VENSIM(1,5,2)",5,0), ("RAMP_VENSIM(1,5,2)",6,-3),
    ("RAMP_VENSIM(1,5,5)",6,0), ("RAMP_VENSIM(-2,-1,1)",0,-2),
    ("RAMP_VENSIM(0,-1,1)",2,0), ("RAMP_VENSIM(2,0,3)",1,2),
    ("RAMP_VENSIM(2,0,3)",4,6),
])
def test_vensim_ramp_distinct_end_contract(expr,time,expected):
    assert safe_eval(expr,{},SimulationContext(time=time))==expected

@pytest.mark.parametrize("method",["euler","rk4"])
def test_vensim_ramp_accepts_dynamic_end_full_series(method):
    model=Model(variables=[{"name":"Value","equation":"RAMP_VENSIM(2,0,TIME-1)"}],
                time_settings={"end":2,"dt":.5,"integration_method":method})
    assert simulate(model).values["Value"]==[0,-1,0,1,2]

@pytest.mark.parametrize("method",["euler","rk4"])
def test_vensim_ramp_holds_stateful_arguments_at_accepted_left_state(method):
    model=Model(stocks=[{"id":"s","name":"Stock","initial_value":1}],
                flows=[{"name":"Rate","equation":"RAMP_VENSIM(Stock,0,Stock+1)","to_stock":"s"}],
                time_settings={"start":.25,"end":1.25,"dt":.25,"integration_method":method})
    assert simulate(model).values["Stock"]==pytest.approx([1,1.0625,1.1953125,1.41943359375,1.7742919921875])

@pytest.mark.parametrize("expr",["RAMP_VENSIM(1,2)","RAMP_VENSIM(1,2,3,4)",
                                  "RAMP_VENSIM(1,2,1/0)","RAMP_VENSIM(1e309,2,3)"])
def test_vensim_ramp_keeps_eager_arity_and_finite_guards(expr):
    with pytest.raises(EquationError):safe_eval(expr,{},SimulationContext(time=0))


def test_vensim_ramp_table_ownership_still_precedes_builtin():
    context=SimulationContext(tables={"RAMP_VENSIM":[(0,10),(1,20)]})
    assert safe_eval("RAMP_VENSIM(.5)",{},context)==15
