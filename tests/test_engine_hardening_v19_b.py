"""Independent numerical contracts for expression/stateful advanced functions."""
import math
import random

import numpy as np
import pytest

from app.core.equations import EquationError, SimulationContext, safe_eval
from app.core.model import Model
from app.core.simulator import simulate


def output(expression,*,start=0,end=12,dt=2,method='euler',seed=17):
    model=Model(variables=[{'name':'Output','equation':expression}],
                time_settings={'start':start,'end':end,'dt':dt,'integration_method':method,'random_seed':seed})
    return simulate(model)


@pytest.mark.parametrize('start',[0,1e12,1e16,-1e16])
def test_fixed_history_is_invariant_under_representable_clock_translation(start):
    # Every timestep and duration is exactly representable at these origins.
    result=output(f'DELAY(TIME-({start!r}),4,-1)',start=start,end=start+12)
    assert [t-start for t in result.time]==[0,2,4,6,8,10,12]
    assert result.values['Output']==[-1,-1,0,2,4,6,8]


@pytest.mark.parametrize('start,dt',[(0,.1),(1000,.1),(1e6,.1),(1e-10,1e-12)])
def test_fixed_history_decimal_boundaries_use_bounded_clock_roundoff(start,dt):
    result=output(f'DELAY(TIME-({start!r}),{3*dt!r},99)',start=start,end=start+10*dt,dt=dt)
    assert result.values['Output'][:3]==[99]*3
    np.testing.assert_allclose(result.values['Output'][3:],
                               [t-start for t in result.time[:-3]],rtol=0,atol=max(math.ulp(start)*4,dt*1e-14))


@pytest.mark.parametrize('expression,code',[
    ('IF(1e309>0,1,0)','non_finite_result'),
    ('IF(1e308*10>0,1,0)','non_finite_result'),
    ('MAX(1e308*10,0)>0','non_finite_result'),
    ('IF((-1)^.5,1,0)','non_real_result'),
    ('IF(pow(-1,.5),1,0)','non_real_result'),
    ('MIN(1/1e-309,7)','non_finite_result'),
])
def test_invalid_reached_intermediate_cannot_be_hidden_by_a_condition(expression,code):
    with pytest.raises(EquationError) as error:
        safe_eval(expression,{})
    assert error.value.code==code


@pytest.mark.parametrize('expression,time,dt',[
    ('IF(RAMP(1e308,0)>0,1,0)',10,1),
    ('IF(PULSE(1e308,0)>0,1,0)',0,.01),
    ('IF(TIME>0,1,0)',math.inf,1),
    ('IF(DT>0,1,0)',0,math.inf),
])
def test_reached_test_input_outputs_and_context_scalars_are_finite(expression,time,dt):
    with pytest.raises(EquationError) as error:
        safe_eval(expression,{},SimulationContext(time=time,dt=dt))
    assert error.value.code=='non_finite_result'


@pytest.mark.parametrize('expression',['1 MOD 0','MOD(1,0)','0^-1','pow(0,-1)','LOG(1,1)'])
def test_function_and_operator_domain_errors_share_machine_readable_zero_cause(expression):
    with pytest.raises(EquationError) as error:safe_eval(expression,{})
    assert error.value.code=='division_by_zero'


@pytest.mark.parametrize('expression',[
    'IF(0,1e309,7)','IF(0,(-1)^.5,7)',
    'IF 1 THEN 7 ELSE 1e308*10','IF(1 OR 1e309,7,0)',
])
def test_unreached_invalid_scalar_branch_remains_lazy(expression):
    assert safe_eval(expression,{})==7


@pytest.mark.parametrize('name',['inf','INF','infinity','nan','NaN'])
def test_float_parser_spellings_remain_ordinary_explicit_identifiers(name):
    assert safe_eval(name,{name:4})==4
    model=Model(variables=[{'name':'Output','equation':name},
                          {'name':name,'equation':'4'}],time_settings={'end':2,'dt':1})
    assert simulate(model).values['Output']==[4]*3
    with pytest.raises(EquationError):safe_eval(name,{})


@pytest.mark.parametrize('name',['e','E','pi','PI'])
@pytest.mark.parametrize('method',['euler','rk4','radau'])
def test_declared_initial_stock_shadows_constant_before_it_has_resolved(name,method):
    model=Model(stocks=[{'id':'x','name':name,'equation':'10'}],
                flows=[{'name':'Growth','equation':name,'to_stock':'x'}],
                time_settings={'end':1,'dt':1,'integration_method':method})
    result=simulate(model)
    assert result.values['Growth'][0]==10
    expected=20 if method=='euler' else 10*(1+1+1/2+1/6+1/24) if method=='rk4' else 10*math.e
    assert result.values[name][-1]==pytest.approx(expected,rel=2e-6)


def test_math_constants_and_lazy_initial_dependency_still_work():
    assert safe_eval('e+pi',{})==math.e+math.pi
    model=Model(variables=[{'name':'A','equation':'IF(0,pi,1)'},
                          {'name':'pi','equation':'A'}],time_settings={'end':1,'dt':1})
    assert simulate(model).values['A']==[1,1]


@pytest.mark.parametrize('method',['euler','rk4'])
@pytest.mark.parametrize('order',[1,3,8])
def test_exponential_delay_chain_step_response_matches_independent_matrix(method,order):
    from scipy.linalg import expm
    duration=4.;dt=.01;end=2.
    expression=f'DELAY_N(1,{duration},{order},0)'
    got=output(expression,end=end,dt=dt,method=method)
    # x'=M*x+b. Augment constant forcing to obtain a reference unrelated to AST.
    matrix=np.zeros((order+1,order+1));rate=order/duration
    for i in range(order):
        matrix[i,i]=-rate
        matrix[i,order if i==0 else i-1]=rate
    initial=np.zeros(order+1);initial[-1]=1
    exact=(expm(matrix*end)@initial)[order-1]
    error=abs(got.values['Output'][-1]-exact)
    assert error<(2e-3 if method=='euler' else 1e-9)


def test_seeded_distribution_draws_match_independent_generators_and_composition():
    uniform=output('RANDOM_UNIFORM(-2,3,17)',end=4,dt=1).values['Output']
    normal=output('NORMAL(2,3,17)',end=4,dt=1).values['Output']
    u=random.Random(17);n=random.Random(17)
    assert uniform==pytest.approx([-2+5*u.random() for _ in range(5)],abs=1e-15)
    assert normal==pytest.approx([2+3*n.gauss(0,1) for _ in range(5)],abs=1e-14)
    # Explicit equal seeds intentionally couple equivalent per-call streams.
    assert output('RANDOM(0,1,17)+RANDOM(0,1,17)',end=4,dt=1).values['Output']==pytest.approx([2*(x+2)/5 for x in uniform])


@pytest.mark.parametrize('method',['euler','rk4'])
def test_composed_material_delays_conserve_mass_including_hidden_contents(method):
    model=Model(stocks=[{'id':'source','name':'Source','equation':'100'},
                        {'id':'sink','name':'Sink','equation':'0'}],
                flows=[{'name':'Departure','equation':'1','from_stock':'source'},
                       {'name':'Arrival','equation':'DELAY1(Inner,3,0)','to_stock':'sink'}],
                variables=[{'name':'Inner','equation':'DELAY1(Departure,2,0)'},
                           {'name':'Nested','equation':'DELAY1(DELAY1(Departure,2,0),3,0)'}],
                time_settings={'end':4,'dt':.025,'integration_method':method})
    result=simulate(model)
    # First-order delay stores duration * outflow units of material. The two
    # independent calls in Nested must be discovered and integrated as well.
    total=np.array(result.values['Source'])+result.values['Sink']
    total+=2*np.array(result.values['Inner'])+3*np.array(result.values['Arrival'])
    np.testing.assert_allclose(total,100,rtol=0,atol=2e-12)
    np.testing.assert_allclose(result.values['Nested'],result.values['Arrival'],rtol=0,atol=1e-14)
    exact=1-(3*math.exp(-4/3)-2*math.exp(-4/2))
    assert result.values['Arrival'][-1]==pytest.approx(exact,abs=2e-3 if method=='euler' else 1e-10)
    assert min(result.values['Arrival'])>=0


def test_named_function_table_inside_smoothing_preserves_native_table_resolution():
    # SMOOTH is a table here: native lookup objects must never be subjected to
    # scalar validation, and the outer stateful call still integrates its input.
    model=Model(tables=[{'name':'SMOOTH','points':[[0,0],[4,8]],'interpolation':'continuous'}],
                variables=[{'name':'Output','equation':'DELAY1(SMOOTH(TIME),2,0)'}],
                time_settings={'end':4,'dt':.025,'integration_method':'rk4'})
    result=simulate(model)
    expected=[2*(t-2+2*math.exp(-t/2)) for t in result.time]
    np.testing.assert_allclose(result.values['Output'],expected,rtol=0,atol=3e-9)
