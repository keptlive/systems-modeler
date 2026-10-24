"""Semantically equivalent scalar Vensim mappings; no guessed dialect aliases.

Primary contracts checked2026-10-24:
https://vensim.com/documentation/fn_log.html
https://vensim.com/documentation/fn_power.html
https://vensim.com/documentation/fn_smooth.html
https://vensim.com/documentation/fn_smooth3.html
Rejected differences:
fn_pulse.html (width, not impulse area),
fn_smooth_n.html (argument order, discrete timing and automatic order reduction),
fn_random.html (stream/seed/truncation), fn_delay1.html (material conservation).
"""
import math
import pytest
from app.core.equations import EquationError
from app.core.mdl_parser import parse_mdl, MDLImportError
from app.core.model import Model
from app.core.simulator import simulate


def mdl(equation,extra="",dt=.05):
    return (f"Output={equation} ~ unit ~ |\n"+extra+
            f"INITIAL TIME=0 ~ second ~ |\nFINAL TIME=2 ~ second ~ |\n"
            f"TIME STEP={dt} ~ second ~ |\nSAVEPER=TIME STEP ~ second ~ |\n")

@pytest.mark.parametrize("equation,expected",[
    ("INTEGER(-2.9)",-2),("INTEGER(2.9)",2),("INTEGER(-.9)",0),
    ("LOG(4,2)",2),("LOG(4,16)",.5),("POWER(-2,3)",-8),
    ("POWER(2,.5)",math.sqrt(2)),("LOG(POWER(2,5),2)",5),
    ("log( 16 , POWER(2,2) )",2),
])
def test_pure_numeric_mappings_preserve_argument_meaning(equation,expected):
    source=mdl(equation)
    imported=parse_mdl(source)
    assert imported['original_source']==source
    assert imported['source_format']=='vensim_mdl'
    result=simulate(Model.model_validate(imported['model']))
    assert result.values['Output']==pytest.approx([expected]*len(result.time))

@pytest.mark.parametrize("name,order,initial",[
    ('SMOOTH',1,0),('SMOOTHI',1,2),('SMOOTH3',3,0),('SMOOTH3I',3,2),
])
@pytest.mark.parametrize('method',['euler','rk4'])
def test_smooths_match_independent_explicit_stock_chain(name,order,initial,method):
    equation=f'{name}(Signal,1'+(f',{initial}' if name.endswith('I') else '')+')'
    source=mdl(equation,'Signal=STEP(10,.5) ~ unit ~ |\n')
    imported=parse_mdl(source);assert imported['original_source']==source
    model=Model.model_validate(imported['model']);model.time_settings.integration_method=method
    result=simulate(model)
    stocks=[dict(id=f's{i}',name=f'Stage{i}',initial_value=initial) for i in range(order)]
    flows=[dict(name=f'Derivative{i}',to_stock=f's{i}',equation=f'{order}*('+('STEP(10,.5)' if i==0 else f'Stage{i-1}')+f'-Stage{i})') for i in range(order)]
    expanded=Model(stocks=stocks,flows=flows,time_settings=model.time_settings)
    reference=simulate(expanded)
    assert result.time==reference.time
    assert result.values['Output']==pytest.approx(reference.values[f'Stage{order-1}'],rel=2e-6,abs=2e-6)
    assert result.values['Output'][0]==initial
    if method=='euler':
        state=[float(initial)]*order;expected=[]
        for t in result.time:
            expected.append(state[-1]);old=state[:]
            state=[old[i]+.05*order*((10 if t>=.5-1e-12 else 0) if i==0 else old[i-1])- .05*order*old[i] for i in range(order)]
        assert result.values['Output']==pytest.approx(expected,abs=1e-12)

@pytest.mark.parametrize('equation',[
 'MODULO(1)','MODULO(1,2,3)','INTEGER()','INTEGER(1,2)','LOG(4)','LOG(4,2,1)','POWER(2)','POWER(2,3,5)',
 'ZIDZ(1)','ZIDZ(1,2,3)','XIDZ(1,2)','XIDZ(1,2,3,4)',
 'SMOOTH(1,2,3)','SMOOTHI(1,2)','SMOOTH3(1,2,3)','SMOOTH3I(1,2)',
 'SMOOTH(1,)','LOG(1,,2)',
])
def test_new_mappings_reject_wrong_source_arity(equation):
    with pytest.raises(MDLImportError,match='requires'):
        parse_mdl(mdl(equation))

@pytest.mark.parametrize('equation',[
 'PULSE(.5,.25)','RAMP(1,1,0)',
 'RANDOM UNIFORM(0,1,42)','RANDOM NORMAL(-10,10,0,1,42)',
 'SMOOTH N(1,2,0,3)','DELAY1(1,1)','DELAY1I(1,1,0)',
 'DELAY FIXED(1,.13,0)',
])
def test_dialect_mismatches_still_fail_explicitly(equation):
    with pytest.raises(MDLImportError,match='Unsupported'):
        parse_mdl(mdl(equation))

def test_nested_smooth_arguments_and_quoted_comma_name():
    imported=parse_mdl(mdl('SMOOTHI("Signal, input",POWER(2,1),LOG(4,2))',
                         '"Signal, input"=10 ~ unit ~ |\n'))
    result=simulate(Model.model_validate(imported['model']))
    assert result.values['Output'][0]==2
    assert result.values['Output'][-1]>2

@pytest.mark.parametrize('name',['SMOOTH','SMOOTHI','SMOOTH3','SMOOTH3I'])
def test_import_does_not_expand_radau_hidden_state_contract(name):
    equation=f'{name}(1,2'+(',0' if name.endswith('I') else '')+')'
    model=Model.model_validate(parse_mdl(mdl(equation))['model'])
    model.time_settings.integration_method='radau'
    with pytest.raises(EquationError,match='Radau supports'):
        simulate(model)

# Primary Vensim fn_xidz.html: abs(denominator)<1e-6, strict boundary.
# pysimlin0.8.5 MDL translates these to exact-zero SAFEDIV instead; do not use
# that translation as an oracle for the nonzero near-zero cases below.
@pytest.mark.parametrize('denominator',[0,5e-7,-5e-7,1e-6,-1e-6,2e-6,-2e-6,
 math.nextafter(1e-6,0),math.nextafter(1e-6,math.inf),
 math.nextafter(-1e-6,0),math.nextafter(-1e-6,-math.inf)])
@pytest.mark.parametrize('name,fallback',[('ZIDZ',0),('XIDZ',7)])
def test_guarded_division_preserves_documented_vensim_threshold(denominator,name,fallback):
    expression=f'{name}(2,{denominator}'+(',7' if name=='XIDZ' else '')+')'
    source=mdl(expression)
    imported=parse_mdl(source);assert imported['original_source']==source
    equation=imported['model']['variables'][0]['equation']
    assert name in equation and 'SAFEDIV' not in equation
    result=simulate(Model.model_validate(imported['model']))
    expected=fallback if abs(denominator)<1e-6 else 2/denominator
    assert result.values['Output']==pytest.approx([expected]*len(result.time))

@pytest.mark.parametrize('name,order',[('SMOOTH',1),('SMOOTH3',3)])
def test_continuous_ramp_smooth_matches_closed_form_and_pinned_simlin(name,order):
    # Pinned pysimlin0.8.5 MDL,41samples dt.05, TIME input: Euler/RK4
    # maxabs6.67e-16 for all four smooth forms (including explicit initial2).
    # STEP-boundary RK4 differs, so its oracle remains explicit stock chains.
    model=Model.model_validate(parse_mdl(mdl(f'{name}(TIME,1)',dt=.0125))['model'])
    model.time_settings.integration_method='rk4'
    result=simulate(model)
    expected=[t-1+math.exp(-t) if order==1 else
              t-1+math.exp(-3*t)*(1+2*t+1.5*t*t) for t in result.time]
    assert result.values['Output']==pytest.approx(expected,abs=2e-8)

@pytest.mark.parametrize('equation',['LOG(0,2)','LOG(2,1)','POWER(-2,.5)'])
def test_new_numeric_functions_do_not_replace_invalid_domains_with_values(equation):
    model=Model.model_validate(parse_mdl(mdl(equation))['model'])
    with pytest.raises(EquationError):simulate(model)


def test_initial_and_final_time_references_follow_effective_run_override():
    source=mdl('INITIAL TIME+FINAL TIME')
    imported=parse_mdl(source);assert imported['original_source']==source
    assert imported['model']['time_settings']['start']==0
    assert imported['model']['time_settings']['end']==2
    model=Model.model_validate(imported['model'])
    assert simulate(model).values['Output']==[2]*41
    model.time_settings.start=5;model.time_settings.end=6
    result=simulate(model)
    assert result.values['Output']==[11]*21

@pytest.mark.parametrize('control,declared',[('INITIAL TIME','STARTTIME'),('FINAL TIME','STOPTIME')])
def test_dynamic_control_does_not_silently_bind_to_authored_bound_name(control,declared):
    with pytest.raises(MDLImportError,match='Dynamic simulation control'):
        parse_mdl(mdl(control,f'{declared}=99 ~ unit ~ |\n'))
    # Existing authored name remains legal when no conflicting control is used.
    imported=parse_mdl(mdl(declared,f'{declared}=99 ~ unit ~ |\n'))
    assert simulate(Model.model_validate(imported['model'])).values['Output']==[99]*41


# Vensim fn_modulo.html specifies C remainder: result follows dividend sign.
@pytest.mark.parametrize('numerator,denominator,expected',[
    (5,3,2),(-5,3,-2),(5,-3,2),(-5,-3,-2),
    (5.5,3,2.5),(-5.5,3,-2.5),(5.5,-3,2.5),(-5.5,-3,-2.5),
    (0,-3,0),(-6,3,0),
])
def test_modulo_uses_c_remainder_not_python_mod(numerator,denominator,expected):
    source=mdl(f'MODULO({numerator},{denominator})')
    imported=parse_mdl(source);assert imported['original_source']==source
    assert imported['model']['variables'][0]['equation'].startswith('MODULO(')
    result=simulate(Model.model_validate(imported['model']))
    assert result.values['Output']==pytest.approx([expected]*41)


def test_modulo_zero_divisor_is_explicit_error():
    model=Model.model_validate(parse_mdl(mdl('MODULO(5,0)'))['model'])
    with pytest.raises(EquationError):simulate(model)
