"""Version 1.5 scalar capability contract with independent analytic oracles.

These tests establish numerical/language behavior, never physical calibration.
No stored model definition is edited by this suite.
"""
import math
import random
from statistics import mean, pstdev
import pytest

from app.core.equations import (
    SAFE_FUNCTIONS, CONTEXT_FUNCTIONS, STATEFUL_FUNCTIONS, EquationError,
    safe_eval, SimulationContext, lookup_interp, validate_equation,
)
from app.core.model import Model, TimeSettings
from app.core.simulator import simulate

# Explicit matrix: fail when a newly advertised function lacks a reviewed row.
MATH_CASES = {
    "sin":("SIN(PI/6)", .5), "cos":("COS(PI/3)", .5),
    "tan":("TAN(PI/4)", 1), "asin":("ASIN(.5)", math.pi/6),
    "acos":("ACOS(.5)", math.pi/3), "atan":("ATAN(1)", math.pi/4),
    "atan2":("ATAN2(1,-1)", 3*math.pi/4), "sign":("SIGN(-.01)", -1),
    "exp":("EXP(2)", math.e**2), "log":("LOG(8,2)", 3),
    "ln":("LN(EXP(2))", 2), "log10":("LOG10(1000)", 3),
    "sqrt":("SQRT(81)", 9), "abs":("ABS(-7)", 7),
    "min":("MIN(3,-2,4)", -2), "max":("MAX(3,-2,4)", 4),
    "pow":("POW(3,4)", 81), "floor":("FLOOR(-1.2)", -2),
    "ceil":("CEIL(-1.2)", -1), "round":("ROUND(2.5)", 2),
    "mod":("MOD(-7,4)", 1), "IF_THEN_ELSE":("IF_THEN_ELSE(1,3,1/0)", 3),
    "IF":("IF(0,1/0,7)", 7),
    "RANDOM_UNIFORM":("RANDOM_UNIFORM(7,7,17)", 7),
    "RANDOM_NORMAL":("RANDOM_NORMAL(7,0,17)", 7),
    "arcsin":("ARCSIN(.5)", math.pi/6),
    "arccos":("ARCCOS(.5)", math.pi/3),
    "arctan":("ARCTAN(1)", math.pi/4),
    "int":("INT(-1.2)", -2), "trunc":("TRUNC(-1.2)", -1),
    "quantum":("QUANTUM(-5,2)", -4), "safediv":("SAFEDIV(1,0,7)", 7),
    "zidz":("ZIDZ(1,1e-9)", 0), "xidz":("XIDZ(1,1e-9,7)", 7),
    "modulo":("MODULO(-7,4)", -3),
}
CONTEXT_ROWS = {
    "STEP","PULSE","RAMP","LOOKUP","WITH_LOOKUP","RANDOM","NORMAL",
    "RANDOM_BINOMIAL", # v1.8 distribution/replay/budget oracles: test_binomial_v18.py
    "RANDOM_UNIFORM","RANDOM_NORMAL","DELAY1","DELAY3","DELAY_N",
    "DELAY_FIXED","SMOOTH","SMOOTH3","SMOOTH_N","SMTH1","SMTH3","SMTHN","DELAYN","DELAY",
    "STARTTIME", "STOPTIME",  # Nonzero bounds/overrides/roundtrips: test_function_compatibility_roundtrip.py
}

def run(equation, start=0, end=4, dt=.125, method="euler", variables=(), tables=()):
    m=Model(variables=[{"name":"Output","equation":equation},*variables],
            tables=list(tables),
            time_settings={"start":start,"end":end,"dt":dt,"integration_method":method,"random_seed":42})
    return simulate(m)

def accumulator(equation, start=0, end=4, dt=.125, method="euler"):
    return simulate(Model(
        stocks=[{"id":"x","name":"Accumulated"}],
        flows=[{"name":"Rate","equation":equation,"to_stock":"x"}],
        time_settings={"start":start,"end":end,"dt":dt,"integration_method":method}))

def test_advertised_functions_have_explicit_matrix_rows():
    assert set(SAFE_FUNCTIONS)==set(MATH_CASES)
    assert CONTEXT_FUNCTIONS==CONTEXT_ROWS

@pytest.mark.parametrize("name",sorted(MATH_CASES))
def test_every_advertised_scalar_function(name):
    expression, expected=MATH_CASES[name]
    assert safe_eval(expression,{}) == pytest.approx(expected,abs=1e-13)

@pytest.mark.parametrize("expression",[
    "SQRT(-1)","LN(0)","LOG10(-1)","ASIN(1.001)","ACOS(-1.001)",
    "LOG(2,1)","EXP(1000)","POW(-1,.5)","1/0","MOD(1,0)",
    "SIGN()","ATAN2(1)","SQRT(1,2)","IF(1,2)","IF_THEN_ELSE(0,1,2,3)",
    "MIN()","MAX()","ROUND(1,2,3)","1e309","1e309-1e309",
])
def test_nonreal_nonfinite_domains_and_arity_fail_explicitly(expression):
    with pytest.raises(EquationError):
        run(expression,end=1,dt=1)

@pytest.mark.parametrize("expression,expected",[
    ("IF 0 THEN 1/0 ELSE IF 1 THEN 2 ELSE 3",2),
    ("IF THEN ELSE(0,1/0,MIN(2,3))",2),
    ("0 AND (1/0)",0),("1 OR (1/0)",1),
    ("NOT 0+1=2 AND 3>2>1=0",1),
    ("(IF 1 THEN 2 ELSE 3)+(IF 0 THEN 4 ELSE 5)",7),
    ("IF 1 THEN (2 if 0 else 3) ELSE 1/0",3),
])
def test_nested_conditionals_boolean_results_and_lazy_domain_branches(expression,expected):
    assert safe_eval(expression,{})==expected

@pytest.mark.parametrize("expression",[
    "PREVIOUS(X,0)","INIT(X)","EXPRND(1)","LOGNORMAL(1,1)","TREND(X,1)",
    "INTEG(1,0)","RANDOM()","RANDOM_NORMAL(-1,1,0,1,17)","STEP(3)",
    "DELAY(X,1,0,4)","X[0]","[1,2]","__import__('os')","X.real",
])
def test_unsupported_dialects_cannot_silently_succeed(expression):
    with pytest.raises(EquationError):
        run(expression,variables=[{"name":"X","equation":"2"}])

@pytest.mark.parametrize("interpolation",["extrapolate","continuous","discrete"])
@pytest.mark.parametrize("call",["Curve(TIME)","LOOKUP(Curve,TIME)","LOOKUP('Curve',TIME)"])
def test_named_graphs_all_modes_and_boundaries(interpolation,call):
    result=run(call,start=-1,end=2,dt=.5,
        tables=[{"name":"Curve","points":[(0,0),(.5,2),(1,0)],"interpolation":interpolation}])
    # independent triangular function table sampled at -1,-.5,0,.5,1,1.5,2
    oracle = {"extrapolate":[-4,-2,0,2,0,-2,-4],
              "continuous":[0,0,0,2,0,0,0],"discrete":[0,0,0,2,0,0,0]}[interpolation]
    assert result.values["Output"]==oracle
    assert lookup_interp(.25,[(0,0),(.5,2),(1,0)],interpolation)==(
        0 if interpolation=="discrete" else 1)

@pytest.mark.parametrize("pairs",["((1,3),(0,1),(2,5))","[[1,3],[0,1],[2,5]]"])
def test_inline_lookups_affine_oracle_and_composition(pairs):
    result=run(f"WITH_LOOKUP(TIME,{pairs})",start=-1,end=3,dt=.125)
    assert result.values["Output"]==pytest.approx([2*t+1 for t in result.time])
    nested=run(f"IF TIME<1 THEN WITH_LOOKUP(TIME,{pairs}) ELSE SQRT(TIME)^2")
    assert nested.values["Output"]==pytest.approx([2*t+1 if t<1 else t for t in nested.time])

@pytest.mark.parametrize("points",["((0,0),(0,1))","((0,1),(2,))","((0,1),2)","()","((0,1),(1,1e309))"])
def test_inline_lookup_data_rejected_whole(points):
    with pytest.raises(EquationError):run(f"WITH_LOOKUP(TIME,{points})")

def test_lookup_extreme_finite_values_are_interpolated_without_spurious_overflow():
    assert lookup_interp(.5,[(0,-1e308),(1,1e308)])==pytest.approx(0,abs=1)
    assert lookup_interp(0,[(-1e308,-2),(1e308,2)])==pytest.approx(0,abs=1e-15)
    assert lookup_interp(.25,[(0,1e308),(1,1e308)])==1e308
    with pytest.raises(EquationError,match="interpolation"):
        lookup_interp(0,[(0,1)],"unknown")

@pytest.mark.parametrize("start,dt,first,interval",[
    (0,.01,0,.1),(2,.01,2,.1),(-2,.01,-1.9,.1),(0,.1,.3,.3),
])
def test_pulse_decimal_grid_has_exactly_one_sample_per_scheduled_event(start,dt,first,interval):
    result=run(f"PULSE(3,{first},{interval})",start=start,end=start+1,dt=dt)
    # Decimal event schedule mapped to integer grid indices, not float remainder.
    indices={round((first-start+k*interval)/dt) for k in range(20)
             if start-1e-12 <= first+k*interval <= start+1+1e-12}
    expected=[3/dt if i in indices else 0 for i in range(len(result.time))]
    assert result.values["Output"]==pytest.approx(expected)

@pytest.mark.parametrize("method",["euler","rk4"])
@pytest.mark.parametrize("start",[-3,0,2])
def test_pulse_area_and_step_boundary_at_nonzero_origins(method,start):
    dt=.125
    pulse=accumulator(f"PULSE(7,{start})",start=start,end=start+1,dt=dt,method=method)
    assert pulse.values["Accumulated"]==pytest.approx([0]+[7]*8,abs=2e-13)
    step=accumulator(f"STEP(2,{start+.5})",start=start,end=start+1,dt=dt,method=method)
    assert step.values["Accumulated"]==pytest.approx([2*max(0,t-start-.5) for t in step.time],abs=2e-13)

@pytest.mark.parametrize("method",["euler","rk4"])
def test_multiple_pulses_integrate_independent_event_areas(method):
    result=accumulator("PULSE(2,.1,.3)",end=1.2,dt=.01,method=method)
    assert result.values["Accumulated"][-1]==pytest.approx(8,abs=1e-12)

@pytest.mark.parametrize("method",["euler","rk4"])
def test_offgrid_step_and_pulse_refine_without_early_leakage(method):
    errors=[]
    for dt in [.1,.05,.025]:
        pulse=accumulator("PULSE(5,.213)",end=1,dt=dt,method=method)
        assert pulse.values["Accumulated"][-1]==pytest.approx(5,abs=1e-12)
        for t,value in zip(pulse.time,pulse.values["Accumulated"]):
            if t <= .213: assert value==0
        step=accumulator("STEP(2,.213)",end=1,dt=dt,method=method)
        errors.append(abs(step.values["Accumulated"][-1]-2*(1-.213)))
    assert errors[2] < errors[1] < errors[0]

@pytest.mark.parametrize("method",["euler","rk4"])
def test_ramp_input_hold_contract_and_refinement(method):
    errors=[]
    for dt in [.25,.125,.0625]:
        result=accumulator("RAMP(2,2,3)",start=2,end=4,dt=dt,method=method)
        # Discrete left-hold sum is independent of RK stage algebra.
        for i,value in enumerate(result.values["Accumulated"]):
            expected=sum(2*min(j*dt,1)*dt for j in range(i))
            assert value==pytest.approx(expected,abs=1e-12)
        errors.append(abs(result.values["Accumulated"][-1]-3))
    assert errors[0]/errors[1]==pytest.approx(2)
    assert errors[1]/errors[2]==pytest.approx(2)

@pytest.mark.parametrize("expression",["STEP(1,1e309)","PULSE(1,1e309)","RAMP(1,1e309)","PULSE(1,0,-1)"])
def test_invalid_test_input_parameters_are_not_quietly_zero(expression):
    with pytest.raises(EquationError):run(expression)

# Every hidden-state spelling is checked through its whole analytic step curve.
EXPONENTIAL_ROWS={
 "SMOOTH":1,"SMTH1":1,"DELAY1":1,"SMOOTH3":3,"SMTH3":3,"DELAY3":3,
 "SMOOTH_N":4,"SMTHN":4,"DELAY_N":4,"DELAYN":4,
}
@pytest.mark.parametrize("function,order",EXPONENTIAL_ROWS.items())
@pytest.mark.parametrize("initial",[-2,0,3])
def test_all_exponential_aliases_against_erlang_response(function,order,initial):
    extra=f",{order}" if function in {"SMOOTH_N","SMTHN","DELAY_N","DELAYN"} else ""
    result=run(f"{function}(5,2{extra},{initial})",start=7,end=11,dt=.015625,method="rk4")
    for time,value in zip(result.time,result.values["Output"]):
        z=order*(time-7)/2
        expected=5+(initial-5)*math.exp(-z)*sum(z**k/math.factorial(k) for k in range(order))
        assert value==pytest.approx(expected,abs=3e-7)

@pytest.mark.parametrize("function",["DELAY","DELAY_FIXED"])
def test_fixed_delay_full_ramp_history_and_fractional_grid(function):
    for dt in [.25,.125]:
        r=run(f"{function}(TIME,.4,-99)",start=2,end=4,dt=dt)
        for i,(t,value) in enumerate(zip(r.time,r.values["Output"])):
            target=t-.4
            expected=-99 if target<2 else 2+math.floor((target-2)/dt+1e-10)*dt
            assert value==pytest.approx(expected)

def test_changing_smoothing_time_nested_and_visible_state_rk4():
    # s'= (1-s)/(1+t), s(0)=0 => s=t/(1+t).
    # v'=s, v(0)=0 => v=t-ln(1+t).
    r=accumulator("SMOOTH(1,TIME+1,0)",end=4,dt=.03125,method="rk4")
    for t,v,s in zip(r.time,r.values["Accumulated"],r.values["Rate"]):
        assert s==pytest.approx(t/(1+t),abs=2e-8)
        assert v==pytest.approx(t-math.log1p(t),abs=2e-8)
    # Nested independent first-order filters, both tau1:
    # y''+2y'+y=1 => y=1-(1+t)e^-t.
    nested=run("SMOOTH(SMOOTH(1,1,0),1,0)",end=4,dt=.03125,method="rk4")
    assert nested.values["Output"]==pytest.approx(
        [1-(1+t)*math.exp(-t) for t in nested.time],abs=1e-7)

def test_hidden_initial_dependencies_and_time_are_evaluated_once_at_start():
    m=Model(stocks=[{"id":"x","name":"X","equation":"Initial"},
                    {"id":"y","name":"Y","equation":"X*2"}],
            variables=[{"name":"Initial","equation":"TIME+3"},
                       {"name":"Output","equation":"SMTH1(9,2,X)"}],
            flows=[{"name":"Change","equation":"1","to_stock":"x"}],
            time_settings={"start":5,"end":7,"dt":.03125,"integration_method":"rk4"})
    r=simulate(m)
    assert r.values["X"]==pytest.approx([8+t-5 for t in r.time])
    assert r.values["Y"]==[16]*len(r.time)
    assert r.values["Output"]==pytest.approx([9-math.exp(-(t-5)/2) for t in r.time],abs=1e-9)

@pytest.mark.parametrize("expression",[
 "SMOOTH(1,0)","DELAY1(1,-1)","SMTHN(1,2,2.5)","DELAYN(1,2,101)",
 "DELAY1(1,TIME+1,0)","DELAY_FIXED(1,TIME+1,0)","SMTHN(1,2,TIME+1,0)",
])
def test_hidden_invalid_duration_and_changing_orders_remain_explicit(expression):
    with pytest.raises(EquationError):run(expression,end=2,dt=.25)

@pytest.mark.parametrize("function",["RANDOM","RANDOM_UNIFORM","NORMAL","RANDOM_NORMAL"])
def test_random_family_affine_replay_and_actual_flow_integration(function):
    normal=function in {"NORMAL","RANDOM_NORMAL"}
    rng=random.Random(19)
    draws=[rng.gauss(0,1) if normal else rng.random() for _ in range(17)]
    expression=f"{function}(2,3,19)"
    r=accumulator(expression,end=4,dt=.25)
    expected=[2+3*x if normal else 2+x for x in draws]
    assert r.values["Rate"]==pytest.approx(expected)
    assert r.values["Accumulated"]==pytest.approx(
        [sum(expected[:i])*.25 for i in range(17)])

def test_run_seed_stream_reordering_retries_and_inactive_hidden_inputs():
    variables=[{"name":"Noise","equation":"RANDOM(-1,1)"},
               {"name":"Later","equation":"2"}]
    a=run("SMOOTH(Noise+Later,1,0)",variables=variables)
    b=run("SMOOTH(Noise+Later,1,0)",variables=list(reversed(variables)))
    assert a.values==b.values
    direct=run("SMOOTH(RANDOM(0,1,19),1,0)",end=4,dt=.25)
    masked=run("IF TIME<2 THEN -1 ELSE SMOOTH(RANDOM(0,1,19),1,0)",end=4,dt=.25)
    assert masked.values["Output"][8:]==direct.values["Output"][8:]
    replay=simulate(Model(variables=[{"name":"N","equation":"NORMAL(0,1)"}],
        time_settings={"end":4,"dt":.25,"random_seed":a.random_seed}))
    assert replay.random_seed==a.random_seed

@pytest.mark.parametrize("expression",[
 "RANDOM(0,1,-1)","RANDOM(0,1,.1)","RANDOM(0,1,4294967296)",
 "RANDOM(0,1,TIME)","RANDOM(1,0)","NORMAL(0,-1)","NORMAL(1e309,1)",
 "RANDOM(0,1,True)","RANDOM(0,1,0,1)",
])
def test_random_bad_seeds_domains_and_arity(expression):
    with pytest.raises(EquationError):run(expression,end=2,dt=.25)

@pytest.mark.parametrize("expression",["RANDOM(0,1)","DELAY(TIME,1,0)"])
def test_rk4_unsupported_history_and_noise_remain_explicit(expression):
    with pytest.raises(EquationError,match="unsupported"):run(expression,method="rk4")

@pytest.mark.parametrize("rate,capacity,initial",[(.7,100,3),(1.4,17,15),(-.3,50,20)])
def test_nonlinear_logistic_full_trajectory_and_fourth_order_convergence(rate,capacity,initial):
    errors=[]
    for dt in [.2,.1]:
        m=Model(stocks=[{"id":"x","name":"X","initial_value":initial}],
            flows=[{"name":"Growth","equation":f"{rate}*X*(1-X/{capacity})","to_stock":"x"}],
            time_settings={"start":3,"end":7,"dt":dt,"integration_method":"rk4"})
        result=simulate(m)
        exact=[capacity/(1+(capacity/initial-1)*math.exp(-rate*(t-3))) for t in result.time]
        errors.append(max(abs(a-b) for a,b in zip(result.values["X"],exact)))
        assert min(result.values["X"])>0
    assert errors[1]<errors[0]/10

def test_ordinary_time_remains_stage_time_under_rk4_input_hold():
    r=accumulator("TIME^3+STEP(2,2)",start=1,end=3,dt=.125,method="rk4")
    for t,value in zip(r.time,r.values["Accumulated"]):
        assert value==pytest.approx((t**4-1)/4+2*max(0,t-2),abs=1e-12)


@pytest.mark.parametrize("start,dt", [(1e12,2**-12),(0,1e-12),(-1e-10,1e-12)])
def test_pulses_preserve_area_at_large_origins_and_small_time_units(start,dt):
    r=accumulator(f"PULSE(2,{start},{8*dt})",
                  start=start,end=start+32*dt,dt=dt,method="rk4")
    assert r.values["Accumulated"][-1]==pytest.approx(8,abs=1e-12)
    assert r.values["Rate"][0]==pytest.approx(2/dt)

def test_rk4_holds_primitive_arguments_at_accepted_state_time():
    # STEP(1,TIME) is always1 at an accepted time. A held clock alone would
    # evaluate its second argument at stage time and incorrectly suppress it.
    r=accumulator("STEP(1,TIME)+PULSE(2,TIME)",start=2,end=3,dt=.125,method="rk4")
    assert r.values["Accumulated"]==pytest.approx([17*(t-2) for t in r.time])
    m=Model(stocks=[{"id":"x","name":"X","initial_value":2}],
      flows=[{"name":"Gain","equation":"STEP(X,TIME)","to_stock":"x"}],
      time_settings={"start":2,"end":3,"dt":.125,"integration_method":"rk4"})
    r=simulate(m)
    assert r.values["X"]==pytest.approx([2*1.125**i for i in range(9)])

def test_extreme_lookup_extrapolation_is_finite_when_true_value_is_representable():
    assert lookup_interp(1.01,[(0,-1e308),(1,1e308)])==pytest.approx(1.02e308)
    with pytest.raises(EquationError,match="finite"):
        lookup_interp(3,[(0,-1e308),(1,1e308)])

@pytest.mark.parametrize("function,order",EXPONENTIAL_ROWS.items())
def test_default_hidden_initial_value_is_initial_input_not_zero(function,order):
    extra=f",{order}" if function in {"SMOOTH_N","SMTHN","DELAY_N","DELAYN"} else ""
    r=run(f"{function}(TIME,2{extra})",start=5,end=7,dt=.015625,method="rk4")
    tau=2/order
    for t,y in zip(r.time,r.values["Output"]):
        z=(t-5)/tau
        tail=sum((order-k)*z**k/math.factorial(k) for k in range(order))
        expected=5+(t-5)-2+tau*math.exp(-z)*tail
        assert y==pytest.approx(expected,abs=2e-8)

def test_rk4_input_hold_does_not_freeze_hidden_derivatives():
    # Held input1 with tau1 remains an ODE, not a whole-step hidden freeze.
    errors=[]
    for dt in [.25,.125]:
        r=run("SMOOTH(STEP(1,0),1,0)",end=2,dt=dt,method="rk4")
        errors.append(max(abs(y-(1-math.exp(-t))) for t,y in zip(r.time,r.values["Output"])))
    assert errors[1] < errors[0]/12


@pytest.mark.parametrize("expression,oracle",[
 ("SIN(TIME)^2+COS(TIME)^2",lambda t:1),
 ("TAN(ATAN(TIME))",lambda t:t),
 ("ASIN(SIN(TIME))",lambda t:t),
 ("ACOS(COS(TIME+1))",lambda t:t+1),
 ("ATAN2(SIN(TIME),COS(TIME))",lambda t:t),
 ("LOG(EXP(TIME))",lambda t:t),
 ("LN(EXP(TIME))",lambda t:t),
 ("LOG10(10^TIME)",lambda t:t),
 ("SQRT(POW(TIME,2))",abs),
 ("MAX(-.5,MIN(.5,TIME))",lambda t:max(-.5,min(.5,t))),
 ("SIGN(TIME)*ABS(TIME)",lambda t:t),
 ("FLOOR(TIME)+CEIL(TIME)",lambda t:math.floor(t)+math.ceil(t)),
 ("ROUND(TIME)",round),
 ("TIME MOD .5",lambda t:t-.5*math.floor(t/.5)),
])
def test_math_functions_across_parameterized_full_series(expression,oracle):
    r=run(expression,start=-1,end=1,dt=.03125)
    assert r.values["Output"]==pytest.approx([oracle(t) for t in r.time],abs=2e-14)

@pytest.mark.parametrize("function",["SMOOTH","DELAY1","SMTH1"])
def test_euler_random_hidden_state_matches_closed_form_discrete_convolution(function):
    rng=random.Random(19)
    draws=[rng.random() for _ in range(17)]
    r=run(f"{function}(RANDOM(0,1,19),1,0)",end=4,dt=.25)
    expected=[.25*sum(.75**(i-1-j)*draws[j] for j in range(i)) for i in range(17)]
    assert r.values["Output"]==pytest.approx(expected,abs=1e-14)

def test_random_time_varying_parameters_reuse_unit_draw_with_correct_affine_transform():
    rng=random.Random(19)
    r=run("RANDOM(TIME,TIME+1,19)",start=2,end=4,dt=.125)
    assert r.values["Output"]==pytest.approx([t+rng.random() for t in r.time])

def test_initial_cycles_fail_but_forward_parameter_dependencies_resolve():
    good=Model(stocks=[{"id":"x","name":"X","equation":"Later*TIME"}],
       variables=[{"name":"First","equation":"Later+1"},{"name":"Later","equation":"3"}],
       time_settings={"start":2,"end":3,"dt":.25})
    r=simulate(good)
    assert r.values["X"]==[6]*5 and r.values["First"]==[4]*5
    bad=Model(stocks=[{"id":"x","name":"X","equation":"Y"},{"id":"y","name":"Y","equation":"X"}])
    with pytest.raises(EquationError,match="Unresolved"):simulate(bad)

@pytest.mark.parametrize("expression,expected",[
 ("2^3^2",512),("-2^2",-4),("(-2)^2",4),("2^-2",.25),
 ("NOT 0^0",0),("8/4*2",4),("2=2<3",0),("2=2=1",1),
])
def test_operator_association_against_xmile_precedence(expression,expected):
    assert safe_eval(expression,{})==expected


def test_rk4_held_input_containing_hidden_function_preserves_call_identity():
    # A primitive with a hidden-state argument must read its accepted instance,
    # while that same hidden instance evolves through the RK derivative stages.
    r=accumulator("STEP(SMOOTH(TIME,1,0),0)",end=2,dt=.125,method="rk4")
    # At accepted t, smooth(TIME) approximates t-1+exp(-t).
    expected=0.
    for i,t in enumerate(r.time):
        assert r.values["Accumulated"][i]==pytest.approx(expected,abs=2e-6)
        expected+=(t-1+math.exp(-t))*.125


@pytest.mark.parametrize("interval",[100.,1e20,1e300])
@pytest.mark.parametrize("first",[.2,.8])
def test_distant_pulse_repetition_cannot_change_first_offgrid_event(interval,first):
    # Repetition beyond the horizon must be identical to the independent single
    # pulse. In particular the active sample at t1 cannot disappear because a
    # far-away interval has a huge ULP.
    repeating=accumulator(f"PULSE(7,{first},{interval})",end=3,dt=1)
    single=accumulator(f"PULSE(7,{first},0)",end=3,dt=1)
    assert repeating.values["Rate"]==[0,7,0,0]
    assert repeating.values==single.values

@pytest.mark.parametrize("x,points,expected",[
 (5.,[(0.,-1e308),(1.,-5e307)],1.5e308),
 (-5.,[(0.,1e308),(1.,5e307)],None),
 (1e308,[(0.,0.),(5e-324,5e-324)],1e308),
])
def test_lookup_extrapolation_avoids_intermediate_overflow(x,points,expected):
    from fractions import Fraction
    (x1,y1),(x2,y2)=points
    rational=Fraction(y1)+(Fraction(x)-Fraction(x1))*(Fraction(y2)-Fraction(y1))/(Fraction(x2)-Fraction(x1))
    try: reference=float(rational)
    except OverflowError: reference=math.inf
    if not math.isfinite(reference):
        with pytest.raises(EquationError,match="finite"):lookup_interp(x,points)
    else:
        assert lookup_interp(x,points)==pytest.approx(reference,rel=2e-15)
        if expected is not None: assert lookup_interp(x,points)==pytest.approx(expected,rel=2e-15)
