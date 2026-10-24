"""Source-defined OASIS XMILE function signatures and export boundaries."""
import math
import random
import xml.etree.ElementTree as ET
import pytest
from app.core.model import Model,LookupTable,Variable
from app.core.equations import EquationError
from app.core.simulator import simulate
from app.core.xmile_generator import generate_xmile
from app.core.xmile_parser import parse_xmile


def model(equation, **settings):
    return Model(variables=[{'name':'Output','equation':equation}],
                 time_settings={'end':2,'dt':.25,**settings})


def equations(xml):
    root=ET.fromstring(xml)
    return {node.get('name'):node.find('{*}eqn').text
            for node in root.findall('.//{*}variables/*') if node.find('{*}eqn') is not None}


def compact(equation):
    return ''.join(equation.split())


@pytest.mark.parametrize('expression,core,expected',[
    ('LOG(8)','LN(8)',math.log(8)),
    ('LOG(8,2)','(LN(8)/LN(2))',3),
    ('LOG(4,16)','(LN(4)/LN(16))',.5),
    ('LOG10(100)','LOG10(100)',2),
    ('LOG(LOG(256,2),2)','(LN((LN(256)/LN(2)))/LN(2))',3),
])
def test_logarithms_export_source_defined_core_forms(expression,core,expected):
    m=model(expression);xml=generate_xmile(m)
    assert compact(equations(xml)['Output'])==core
    assert simulate(parse_xmile(xml)).values['Output']==pytest.approx([expected]*9)


def test_stock_initializers_use_same_log_and_conditional_translation():
    m=Model(stocks=[{'name':'Level','equation':'IF(1,LOG(8,2),1/0)'}],
            flows=[{'name':'Rate','equation':'LOG(4,2)','to_stock':'Level'}],
            time_settings={'end':2,'dt':.25})
    xml=generate_xmile(m);eq=equations(xml)
    assert compact(eq['Level'])=='(IF1THEN(LN(8)/LN(2))ELSE1/0)'
    assert compact(eq['Rate'])=='(LN(4)/LN(2))'
    result=simulate(parse_xmile(xml))
    assert result.values['Level']==pytest.approx([3+2*t for t in result.time])


@pytest.mark.parametrize('alias,core,args',[
    ('SMOOTH','SMTH1','1,1,0'),('SMOOTH3','SMTH3','1,1,0'),
    ('SMOOTH_N','SMTHN','1,1,2,0'),('DELAY_FIXED','DELAY','TIME,.5,0'),
    ('DELAY_N','DELAYN','1,1,2,0'),('DELAY1','DELAY1','1,1,0'),
    ('DELAY3','DELAY3','1,1,0'),('SMTH1','SMTH1','1,1,0'),
    ('SMTHN','SMTHN','1,1,2,0'),
])
@pytest.mark.parametrize('method',['euler','rk4'])
def test_delay_and_smoothing_aliases_keep_argument_order_and_trajectories(alias,core,args,method):
    m=model(f'{alias}({args})',integration_method=method);xml=generate_xmile(m)
    assert compact(equations(xml)['Output'])==f'{core}({args})'
    if method=='rk4' and alias=='DELAY_FIXED':
        for candidate in (m,parse_xmile(xml)):
            with pytest.raises(EquationError) as failure:simulate(candidate)
            assert failure.value.code=='unsupported_method_features'
        return
    assert simulate(parse_xmile(xml)).values==simulate(m).values


def test_smooth_reference_is_independent_euler_recurrence():
    restored=parse_xmile(generate_xmile(model('SMOOTH(1,1,0)')))
    assert simulate(restored).values['Output']==pytest.approx([1-.75**n for n in range(9)])


@pytest.mark.parametrize('expression,core,expected',[
    ('RANDOM_UNIFORM(2,4,17)','RANDOM(2,4,17)',2+2*random.Random(17).random()),
    ('RANDOM_NORMAL(2,4,17)','NORMAL(2,4,17)',2+4*random.Random(17).gauss(0,1)),
])
def test_random_aliases_keep_distribution_parameters_and_explicit_seed(expression,core,expected):
    m=model(expression,random_seed=0);xml=generate_xmile(m)
    assert compact(equations(xml)['Output'])==core
    result=simulate(parse_xmile(xml))
    assert result.values==simulate(m).values
    assert result.values['Output'][0]==pytest.approx(expected)


@pytest.mark.parametrize('alias',['RANDOM_UNIFORM','RANDOM_NORMAL'])
def test_simple_alias_keeps_implicit_seed_stream_at_unchanged_column(alias):
    m=model(f'{alias}(0,1)',random_seed=137)
    assert simulate(parse_xmile(generate_xmile(m))).values==simulate(m).values


def test_translation_keeps_native_vocabulary_when_implicit_stream_would_move():
    m=model('LOG(8,2)+RANDOM(0,1)',random_seed=137)
    restored=parse_xmile(generate_xmile(m))
    assert restored.variables[0].equation==m.variables[0].equation
    assert simulate(restored).values==simulate(m).values
    assert all(3<=value<=4 for value in simulate(restored).values['Output'])
    m.variables[0].equation='LOG(8,2)+RANDOM(0,1,17)'
    assert simulate(parse_xmile(generate_xmile(m))).values==simulate(m).values


def test_structured_conditional_preserves_lazy_branches_and_nested_calls():
    m=model('IF(TIME < 1, LOG(8,2), IF_THEN_ELSE(1,LOG(4,16),1/0))')
    xml=generate_xmile(m);eq=equations(xml)['Output']
    assert 'IF_THEN_ELSE' not in eq and 'THEN' in eq and 'ELSE' in eq
    assert simulate(parse_xmile(xml)).values['Output']==[3]*4+[.5]*5


def test_pulse_has_standard_magnitude_over_dt_and_interval_signature():
    m=Model(stocks=[{'name':'Accumulated'}],
            flows=[{'name':'Input','equation':'PULSE(2,1,2)','to_stock':'Accumulated'}],
            time_settings={'end':4,'dt':.25})
    result=simulate(parse_xmile(generate_xmile(m)))
    assert result.values['Input']==[8 if t in (1,3) else 0 for t in result.time]
    assert result.values['Accumulated'][-1]==4


@pytest.mark.parametrize('name',['LOG','SMOOTH','RANDOM_UNIFORM'])
def test_graphical_function_shadowing_is_preserved(name):
    m=model(f'{name}(TIME)');m.tables=[LookupTable(name=name,points=[(0,0),(2,8)])]
    xml=generate_xmile(m)
    assert compact(equations(xml)['Output'])==f'{name}(TIME)'
    assert simulate(parse_xmile(xml)).values['Output']==[4*t for t in simulate(m).time]


def test_new_core_name_cannot_silently_shadow_an_existing_graphical_function():
    m=model('LOG(8)');m.tables=[LookupTable(name='LN',points=[(0,0),(10,1)])]
    with pytest.raises(ValueError,match='conflicts'):generate_xmile(m)


@pytest.mark.parametrize('name',['LN','RANDOM','SMTH1','PREVIOUS'])
def test_unused_table_with_reserved_core_name_survives_native_profile(name):
    m=model('1');m.tables=[LookupTable(name=name,points=[(0,0),(10,1)])]
    xml=generate_xmile(m);restored=parse_xmile(xml)
    assert ET.fromstring(xml).get('{https://stockandflow.live/ns/model}compatibility')=='native-scalar-v1'
    assert [t.name for t in restored.tables]==[name]
    assert simulate(restored).values==simulate(m).values


@pytest.mark.parametrize('kind,name',[
    ('stocks','pi'),('flows','MIN'),('variables',' Smth1 '),('tables',' LN '),
])
def test_core_namespace_declarations_survive_native_profile(kind,name):
    definition={'name':name,'points':[(0,0),(1,1)]} if kind=='tables' else {'name':name}
    m=Model(**{kind:[definition]},time_settings={'end':1})
    xml=generate_xmile(m);restored=parse_xmile(xml)
    assert [e.name for e in getattr(restored,kind)]==[name]
    assert simulate(restored).values==simulate(m).values


def test_lookup_preserves_implicit_seeded_random_input_without_moving_it():
    m=model("LOOKUP('Curve',RANDOM(0,1))",random_seed=137)
    m.tables=[LookupTable(name='Curve',points=[(0,0),(1,10)])]
    restored=parse_xmile(generate_xmile(m))
    assert restored.variables[0].equation==m.variables[0].equation
    assert simulate(restored).values==simulate(m).values
    assert all(0<=value<=10 for value in simulate(restored).values['Output'])
    m.variables[0].equation="LOOKUP('Curve',RANDOM(0,1,17))"
    assert simulate(parse_xmile(generate_xmile(m))).values==simulate(m).values


@pytest.mark.parametrize('expression',[
    'RANDOM_BINOMIAL(4)','ROUND(2.5,1)','POW(2,3,5)',
    'ATAN2(1)','FLOOR(1.5,2)','CEIL(1.5,2)','MOD(5)','2 // 1',
    'LOG()','LOG(8,2,3)','SMOOTH_N(1,2)','PULSE(1)','MIN(1)',
    'LOOKUP("Curve",TIME)+1',
])
def test_unsupported_helpers_or_signatures_fail_explicitly(expression):
    with pytest.raises(ValueError):generate_xmile(model(expression))


def test_operator_conversion_does_not_touch_quoted_identifiers():
    m=model('"Gain**Rate" ** 2');m.variables.insert(0,Variable(name='Gain**Rate',equation='3'))
    xml=generate_xmile(m)
    assert '"Gain**Rate"' in equations(xml)['Output']
    assert simulate(parse_xmile(xml)).values['Output']==[9]*9


@pytest.mark.parametrize('expression,expected',[
    ('5%2',1),('-5%2',1),('5%-2',-1),('-5%-2',-1),
    ('3<2<1',1),('2=3<4',0),('2<>3',1),
    ('-2^2',-4),('NOT 1+1',1),('not 0 or 0',1),
    ('(1+2)*3-4/2',7),('1 AND 0 OR 2',1),
])
def test_bounded_operator_audit_retains_core_numeric_semantics(expression,expected):
    xml=generate_xmile(model(expression));eq=equations(xml)['Output']
    assert '%' not in eq
    if '%' in expression:assert 'MOD' in eq
    assert simulate(parse_xmile(xml)).values['Output']==[expected]*9


@pytest.mark.parametrize('expression,core,expected',[
    ('True','1.0',1),('False','0.0',0),('0x10','16.0',16),
    ('0b11','3.0',3),('0o10','8.0',8),('1_000','1000.0',1000),
    ('1e1_0','10000000000.0',1e10),('.5','.5',.5),('14.','14.',14),
    ('e','EXP(1)',math.e),('E','EXP(1)',math.e),('"e"','EXP(1)',math.e),
    ('TIME_STEP','DT',.25),
])
def test_bounded_literal_and_constant_audit(expression,core,expected):
    xml=generate_xmile(model(expression))
    assert compact(equations(xml)['Output'])==core
    assert simulate(parse_xmile(xml)).values['Output']==[expected]*9


def test_python_ternary_becomes_lazy_core_conditional_in_each_equation_kind():
    m=Model(stocks=[{'name':'Level','equation':'3 if 1 else 1/0'}],
            flows=[{'name':'Rate','equation':'2 if TIME<1 else (0 if 1 else 1/0)','to_stock':'Level'}],
            variables=[{'name':'Output','equation':'1/0 if 0 else Level'}],
            time_settings={'end':2,'dt':.25})
    xml=generate_xmile(m)
    assert all('THEN' in eq and 'ELSE' in eq for eq in equations(xml).values())
    assert simulate(parse_xmile(xml)).values==simulate(m).values


@pytest.mark.parametrize('kind',['stocks','variables'])
def test_declared_scalar_e_keeps_its_quantity_meaning(kind):
    body={'variables':[{'name':'Output','equation':'e+1'}],
          'time_settings':{'end':2,'dt':.25}}
    body.setdefault(kind,[]).append({'name':'e',**({'initial_value':2} if kind=='stocks' else {'equation':'2'})})
    m=Model.model_validate(body);xml=generate_xmile(m)
    assert 'EXP' not in equations(xml)['Output']
    assert simulate(parse_xmile(xml)).values['Output']==[3]*9


def test_table_e_and_unshadowed_constant_e_keep_distinct_meanings():
    m=model('e + e(TIME)');m.tables=[LookupTable(name='e',points=[(0,0),(2,8)])]
    xml=generate_xmile(m);eq=equations(xml)['Output']
    assert 'EXP' in eq and 'e(' in compact(eq)
    assert simulate(parse_xmile(xml)).values['Output']==[math.e+4*t for t in simulate(m).time]


@pytest.mark.parametrize('expression,rejected',[
    ('e+RANDOM(0,1)',True), ('1 if RANDOM(0,1)>0 else 0',True),
    ('0x10+RANDOM(0,1)',False), ('True+RANDOM(0,1)',True),
    ('0b11+RANDOM(0,1)',True),
])
def test_new_syntax_translations_preserve_seed_identity_via_native_fallback(expression,rejected):
    m=model(expression,random_seed=137)
    restored=parse_xmile(generate_xmile(m))
    if rejected:
        assert restored.variables[0].equation==expression
    assert simulate(restored).values==simulate(m).values
    if expression.startswith('1 if'):
        assert simulate(restored).values['Output']==[1]*9
    m.variables[0].equation=expression.replace('RANDOM(0,1)','RANDOM(0,1,17)')
    assert simulate(parse_xmile(generate_xmile(m))).values==simulate(m).values


@pytest.mark.parametrize('expression',[
    '[1,2]','(1,2)','{1:2}','{1,2}','X[0]','X.y',
    '1<<2','1&2','1|2','1@2','1 is 1','1 in [1]',
    'lambda:1','(x:=1)',"'label'",'1j','1e309','9'*400,
])
def test_ast_audit_rejects_non_scalar_or_unsupported_syntax(expression):
    with pytest.raises(ValueError):generate_xmile(model(expression))


@pytest.mark.parametrize('expression',['RANDOM(0,1,True)','NORMAL(0,1,False)','RANDOM_UNIFORM(0,1,True)'])
def test_boolean_literal_conversion_does_not_repair_invalid_function_seeds(expression):
    m=model(expression)
    with pytest.raises(EquationError):simulate(m)
    with pytest.raises(ValueError,match='Boolean random seeds'):generate_xmile(m)

@pytest.mark.parametrize('expression,expected',[
    ('ROUND(2.5)',2),('SIGN(-1)',-1),('ATAN2(1,2)',math.atan2(1,2)),
    ('FLOOR(1.5)',1),('CEIL(1.5)',2),
])
def test_newly_admitted_scalar_extensions_keep_independent_numeric_values(expression,expected):
    m=model(expression);result=simulate(parse_xmile(generate_xmile(m)))
    assert result.values['Output']==pytest.approx([expected]*9)
    assert result.values==simulate(m).values


def test_three_argument_native_ramp_export_keeps_native_contract():
    m=model('RAMP(2,1,3)');result=simulate(parse_xmile(generate_xmile(m)))
    assert result.values['Output']==[0 if t<1 else 2*(t-1) for t in result.time]
