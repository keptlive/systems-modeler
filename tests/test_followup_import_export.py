"""Import/export regressions: literal MDL names, GF calls and scalar extensions.

REM/XIDZ, floor/ceil/round/sign/atan2 and3arg ramp are compatibility
extensions, not a claim that arbitrary XMILE readers implement native semantics.
Vensim ramp contract: https://vensim.com/documentation/fn_ramp.html
"""
import ast
import math
import xml.etree.ElementTree as ET
import pytest
from app.core.model import Model
from app.core.simulator import simulate
from app.core.equations import EquationError,preprocess_equation
from app.core.mdl_parser import parse_mdl,MDLImportError
from app.core.xmile_parser import parse_xmile
from app.core.xmile_generator import generate_xmile

CONTROLS='INITIAL TIME=0 ~~| FINAL TIME=2 ~~| TIME STEP=.25 ~~| SAVEPER=TIME STEP ~~|'

def roundtrip(model):
    before=simulate(model)
    exported=generate_xmile(model)
    restored=parse_xmile(exported)
    after=simulate(restored)
    assert after.time==before.time
    assert after.report_values==before.report_values
    assert restored.time_settings.model_dump()==model.time_settings.model_dump()
    assert {v.name:v.role for v in restored.variables}=={v.name:v.role for v in model.variables}
    assert set(after.values)==set(before.values)
    for name in before.values:assert after.values[name]==pytest.approx(before.values[name],rel=1e-12,abs=1e-12)
    assert [(t.name,t.points,t.interpolation) for t in restored.tables]==[(t.name,t.points,t.interpolation) for t in model.tables]
    assert restored.time_settings.random_seed==model.time_settings.random_seed
    return exported,restored,before

def table_model(expression,name='Curve',variable='Output',seed=None):
    return Model(variables=[dict(name=variable,equation=expression)],
        tables=[dict(name=name,points=[(0,10),(1,20),(2,30)],interpolation='continuous')],
        time_settings=dict(start=0,end=2,dt=.25,random_seed=seed))

@pytest.mark.parametrize('operator,expected',[('-',7),('+',13),('*',30),('/',10/3),('^',1000)])
@pytest.mark.parametrize('spaced',[False,True])
def test_quoted_mdl_names_do_not_consume_unquoted_arithmetic(operator,expected,spaced):
    # Independent pysimlin0.8.5 MDL check agrees on all5arithmetic results.
    expression=f'A {operator} B' if spaced else f'A{operator}B'
    source=f'A=10 ~~| B=3 ~~| "A{operator}B"=100 ~~| Output={expression} ~~| Quoted="A{operator}B" ~~|'+CONTROLS
    parsed=parse_mdl(source);assert parsed['original_source']==source
    model=Model.model_validate(parsed['model'])
    exported,restored,result=roundtrip(model)
    assert result.values['Output']==pytest.approx([expected]*9)
    assert result.values['Quoted']==[100]*9
    assert f'A{operator}B' in [v.name for v in restored.variables]

@pytest.mark.parametrize('operator',list('+-*/^<>,') )
def test_operator_lhs_must_be_explicitly_quoted_in_mdl(operator):
    with pytest.raises(MDLImportError,match='require double quotes'):
        parse_mdl(f'A{operator}B=100 ~~|'+CONTROLS)

@pytest.mark.parametrize('expression',[
 '2*LOOKUP("Curve",TIME)', 'IF(TIME<1,LOOKUP("Curve",TIME),0)',
 'LOOKUP("curve",TIME)+LOOKUP(CURVE,TIME)',
 'LOOKUP("my table",TIME)', 'LOOKUP("my_table",TIME)',
 'LOOKUP("Curve",SMOOTH(TIME,1))+LOOKUP("Curve",TIME)',
])
def test_nested_aliased_and_stateful_lookup_roundtrip(expression):
    name='my_table' if 'my' in expression else 'Curve'
    _,_,result=roundtrip(table_model(expression,name=name))
    assert len(result.time)==9

@pytest.mark.parametrize('name',['TRUNC','QUANTUM','ZIDZ','XIDZ','FLOOR','ROUND'])
@pytest.mark.parametrize('quoted',[False,True])
def test_builtin_extension_named_tables_keep_owner_and_single_input(name,quoted):
    function=f'"{name}"' if quoted else name
    exported,_,result=roundtrip(table_model(f'{function}(TIME)',name=name))
    assert result.values['Output']==[10+10*t for t in result.time]
    assert 'LOOKUP' in exported

@pytest.mark.parametrize('expression',[
 'pow(2,TIME)', 'pow(-2,3)', 'FLOOR(TIME-.5)', 'CEIL(TIME-.5)',
 'ROUND(TIME-.5)', 'SIGN(TIME-.5)', 'ATAN2(TIME,1)',
 'MODULO(-5-TIME,3)', 'MODULO(5+TIME,-3)', 'REM(-5-TIME,-3)',
 'ZIDZ(2,TIME-1)', 'XIDZ(2,TIME-1,7)',
 'RAMP(1,-1,0)', 'RAMP(1,1,0)', 'RAMP_VENSIM(1,1,0)',
])
def test_scalar_expression_and_extension_full_series_roundtrip(expression):
    model=Model(variables=[dict(name='Output',equation=expression)],time_settings=dict(start=0,end=2,dt=.25))
    xml,_,_=roundtrip(model)
    if expression.startswith('MODULO'):assert 'REM' in xml
    if expression.startswith('ZIDZ'):assert 'XIDZ' in xml

@pytest.mark.parametrize('expression',['pow(2,3,5)','ROUND(1.25,1)'])
def test_invalid_native_signatures_are_not_falsely_lowered(expression):
    model=Model(variables=[dict(name='Output',equation=expression)],time_settings=dict(start=0,end=2,dt=.25))
    with pytest.raises(EquationError):simulate(model)
    with pytest.raises(ValueError,match='requires two|signature is unsupported'):generate_xmile(model)

@pytest.mark.parametrize('expression',['XIDZ(1,2,1/0)','ZIDZ(1/0,0)','MODULO(1,0)'])
def test_exported_extensions_preserve_eager_domain_errors(expression):
    model=Model(variables=[dict(name='Output',equation=expression)],time_settings=dict(start=0,end=2,dt=.25))
    restored=parse_xmile(generate_xmile(model))
    for candidate in (model,restored):
        with pytest.raises(EquationError):simulate(candidate)

@pytest.mark.parametrize('source_equation,expected',[
 ('POWER(-2,3)',-8),('MODULO(-5,3)',-2),('ZIDZ(1,1e-7)',0),('XIDZ(1,1e-7,9)',9),
])
def test_new_mdl_expression_import_export_reimport(source_equation,expected):
    source='Output='+source_equation+' ~~|'+CONTROLS
    parsed=parse_mdl(source);assert parsed['original_source']==source
    model=Model(**parsed['model'],source_document=dict(format='vensim_mdl',text=source,diagnostics=parsed['diagnostics']))
    _,restored,result=roundtrip(model)
    assert restored.source_document.text==source
    assert result.values['Output']==[expected]*9

@pytest.mark.parametrize('expression',[
 'LOOKUP("v",RANDOM(0,1))', 'LOOKUP("V",NORMAL(0,1))',
 'LOOKUP("v",RANDOM(0,1)+NORMAL(0,1))',
 '2*LOOKUP("v",RANDOM(0,1))',
])
def test_implicit_seeded_graphical_input_preserves_entire_stream(expression):
    model=table_model(expression,name='v',variable='v',seed=42)
    exported,restored,result=roundtrip(model)
    root=ET.fromstring(exported);ns={'x':'http://docs.oasis-open.org/xmile/ns/XMILE/v1.0'}
    assert root.find('.//x:aux/x:gf',ns) is None
    assert root.find('.//x:variables/x:gf',ns) is not None
    assert len(result.values['v'])==9
    before=ast.parse(preprocess_equation(expression),mode='eval')
    after=ast.parse(preprocess_equation(restored.variables[0].equation),mode='eval')
    positions=lambda tree:[(n.lineno,n.col_offset) for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id.upper() in ('RANDOM','NORMAL')]
    assert positions(before)==positions(after)


def test_explicit_seed_graphical_input_still_embeds_and_replays():
    model=table_model('LOOKUP("v",RANDOM(0,1,7))',name='v',variable='v',seed=42)
    exported,_,_=roundtrip(model)
    assert ET.fromstring(exported).find('.//{*}aux/{*}gf') is not None


@pytest.mark.parametrize('expression',[
 'LOG(RANDOM(1,2))', 'LOG(8,2)+"RANDOM"(0,1)',
 'LOG(8,2)+"NORMAL"(0,1)', 'POW(RANDOM(1,2),2)',
])
def test_implicit_random_guard_falls_back_to_validated_native_expression(expression):
    model=Model(variables=[dict(name='Output',equation=expression)],time_settings=dict(start=0,end=2,dt=.25,random_seed=137))
    exported,restored,_=roundtrip(model)
    assert restored.variables[0].equation==expression


def test_alias_conversion_cannot_capture_a_graphical_function():
    with pytest.raises(ValueError,match='conflicts'):
        generate_xmile(table_model('ZIDZ(1,0)',name='XIDZ'))
    with pytest.raises(ValueError,match='conflicts'):
        generate_xmile(table_model('MODULO(1,2)',name='REM'))


def xml(body):
    return '<xmile><sim_specs><start>0</start><stop>2</stop><dt>.25</dt></sim_specs><model><variables>'+body+'</variables></model></xmile>'

@pytest.mark.parametrize('body',[
 '<gf name="Empty"/>',
 '<gf name="Empty"><xscale min="0" max="1"/><ypts> </ypts></gf>',
 '<aux name="Empty"><eqn>1</eqn><gf/></aux>',
])
def test_empty_graphical_functions_fail_import_consistently(body):
    with pytest.raises(ValueError,match='no valid points'):parse_xmile(xml(body))


@pytest.mark.parametrize('input_xml',['','<eqn/>','<eqn>   </eqn>'])
def test_whitespace_flow_graph_requires_authored_input_without_none_or_guess(input_xml):
    body='<flow name="Rate">'+input_xml+'<gf><xscale min="0" max="1"/><ypts>10,20</ypts></gf></flow>'
    with pytest.raises(ValueError,match='nonempty input equation'):parse_xmile(xml(body))
    ordinary=parse_xmile(xml('<flow name="Rate"><eqn> </eqn></flow>'))
    assert simulate(ordinary).values['Rate']==[0]*9


def test_embedded_graph_quoted_unicode_name_and_metadata_survive():
    body='<aux name="Output"><eqn>TIME</eqn><gf name="Curve &quot;雪&quot;"><xscale min="0" max="2"/><ypts>10,30</ypts></gf></aux>'
    model=parse_xmile(xml(body));_,restored,result=roundtrip(model)
    assert restored.tables[0].name=='Curve "雪"'
    assert result.values['Output']==[10+10*t for t in result.time]

@pytest.mark.parametrize('method',['euler','rk4'])
@pytest.mark.parametrize('start,end',[(.5,1.5),(1,.5)])
def test_mdl_ramp_dynamic_endpoints_use_distinct_vensim_contract(method,start,end):
    source=f'Output=RAMP(2,Start,Finish) ~~| Start={start}+TIME*.1 ~~| Finish={end}+TIME*.2 ~~|'+CONTROLS
    parsed=parse_mdl(source);assert parsed['original_source']==source
    assert 'RAMP_VENSIM' in parsed['model']['variables'][0]['equation']
    model=Model.model_validate(parsed['model']);model.time_settings.integration_method=method
    _,_,result=roundtrip(model)
    expected=[]
    for t in result.time:
        a=start+t*.1;b=end+t*.2
        expected.append(0 if t<=a else 2*((t if t<b else b)-a))
    assert result.values['Output']==pytest.approx(expected)


SF='https://stockandflow.live/ns/model'

def test_radau_settings_survive_without_method_or_tolerance_substitution():
    model=Model(stocks=[dict(id='p',name='Population',initial_value=10)],
        flows=[dict(name='Loss',equation='.5*Population',from_stock='p')],
        time_settings=dict(start=3,end=5,dt=.25,integration_method='radau',rtol=2e-5,atol=3e-8))
    exported,restored,result=roundtrip(model)
    root=ET.fromstring(exported);specs=root.find('{*}sim_specs')
    assert specs.get('method')=='radau'
    assert root.get('{'+SF+'}compatibility')=='native-scalar-v1'
    assert result.values['Population']==pytest.approx([10*math.exp(-.5*(t-3)) for t in result.time],rel=5e-5)

@pytest.mark.parametrize('method',['euler','rk4'])
def test_nondefault_tolerances_are_retained_for_future_solver_changes(method):
    model=Model(variables=[dict(name='Value',equation='TIME')],time_settings=dict(start=0,end=2,dt=.25,integration_method=method,rtol=3e-4,atol=5e-7))
    roundtrip(model)


def test_discrete_period_recurrence_is_not_exported_as_an_ordinary_ode():
    model=Model(stocks=[dict(id='p',name='Population',initial_value=.1)],
        flows=[dict(name='Generation',to_stock='p',equation='(3.7*Population*(1-Population)-Population)/DT')],
        time_settings=dict(start=0,end=8,dt=1,discrete_period=1))
    exported,restored,result=roundtrip(model)
    assert restored.time_settings.discrete_period==1
    expected=[.1]
    for _ in range(8):expected.append(3.7*expected[-1]*(1-expected[-1]))
    assert result.values['Population']==pytest.approx(expected,abs=1e-12)


def test_report_roles_and_raw_unicode_labels_survive_as_reports():
    expression="IF(TIME==0,'Undefined & 雪 at start',1/TIME)"
    model=Model(variables=[dict(name='Status',equation=expression,role='report')],
        time_settings=dict(start=0,end=2,dt=.25))
    exported,restored,result=roundtrip(model)
    assert restored.variables[0].equation==expression
    assert restored.variables[0].role=='report'
    assert result.report_values['Status']==['Undefined & 雪 at start']+[1/t for t in result.time[1:]]
    assert 'Status' not in result.values

@pytest.mark.parametrize('name',['Delay','Pi','LOG10','RANDOM','IF'])
def test_reserved_scalar_declaration_preserved_with_explicit_native_profile(name):
    model=Model(variables=[dict(name=name,equation='7'),dict(name='Output',equation=f'"{name}"+TIME')],
        time_settings=dict(start=0,end=2,dt=.25))
    exported,restored,result=roundtrip(model)
    assert ET.fromstring(exported).get('{'+SF+'}compatibility')=='native-scalar-v1'
    assert result.values['Output']==[7+t for t in result.time]

@pytest.mark.parametrize('name',['MIN','IF','SIN'])
def test_reserved_table_namespace_keeps_native_lookup_ownership(name):
    _,_,result=roundtrip(table_model(f'"{name}"(TIME)',name=name))
    assert result.values['Output']==[10+10*t for t in result.time]

@pytest.mark.parametrize('expression',[
 'MOD(-5-TIME,3)','MIN(3,TIME,1,2)','MAX(3,TIME,1,2)',
 'RANDOM_BINOMIAL(8,.25)','"RANDOM_BINOMIAL"(8,.25)',
 'LOG(8,2)+RANDOM_BINOMIAL(8,.25)','LOG(8,2)+"RANDOM_BINOMIAL"(8,.25)',
])
def test_additional_native_expressions_survive_full_series_and_seed_identity(expression):
    model=Model(variables=[dict(name='Output',equation=expression)],time_settings=dict(start=0,end=2,dt=.25,random_seed=137))
    _,_,result=roundtrip(model)
    if expression.startswith('MOD('):assert result.values['Output']==[(-5-t)%3 for t in result.time]
    if expression.startswith('MIN('):assert result.values['Output']==[min(3,t,1,2) for t in result.time]
    if expression.startswith('MAX('):assert result.values['Output']==[max(3,t,1,2) for t in result.time]

@pytest.mark.parametrize('expression',['RANDOM_BINOMIAL(True,.5)','RANDOM_BINOMIAL(8,.5,True)'])
def test_binomial_boolean_parameters_are_not_repaired_by_export(expression):
    model=Model(variables=[dict(name='Output',equation=expression)],time_settings=dict(start=0,end=2,dt=.25))
    with pytest.raises(EquationError):simulate(model)
    with pytest.raises(ValueError,match='Boolean'):generate_xmile(model)


def native_xml(spec_attrs='',root_attrs='',aux_attrs=''):
    return f'<xmile xmlns:sf="{SF}" sf:compatibility="native-scalar-v1" {root_attrs}><sim_specs {spec_attrs}><start>0</start><stop>2</stop><dt>.25</dt></sim_specs><model><variables><aux name="Value" {aux_attrs}><eqn>1</eqn></aux></variables></model></xmile>'

@pytest.mark.parametrize('spec_attrs',[
 'sf:rtol="NaN"','sf:atol="inf"','sf:rtol=""','sf:rtol="1"',
 'sf:atol="0"','sf:discrete_period=".5"','sf:discrete_period="-1"',
 'sf:unknown_setting="1"',
])
def test_malformed_or_unknown_native_settings_are_not_ignored(spec_attrs):
    with pytest.raises(ValueError):parse_xmile(native_xml(spec_attrs=spec_attrs))

@pytest.mark.parametrize('aux_attrs',['sf:role=""','sf:role="stock"','sf:unknown="report"'])
def test_native_auxiliary_metadata_is_narrowly_validated(aux_attrs):
    with pytest.raises(ValueError):parse_xmile(native_xml(aux_attrs=aux_attrs))


def test_native_extension_requires_supported_root_profile_and_exact_namespace():
    valid=native_xml(spec_attrs='sf:rtol=".001"',aux_attrs='sf:role="report"')
    assert parse_xmile(valid).variables[0].role=='report'
    with pytest.raises(ValueError):parse_xmile(valid.replace(' sf:compatibility="native-scalar-v1"',''))
    with pytest.raises(ValueError):parse_xmile(valid.replace('native-scalar-v1','native-scalar-v2'))
    with pytest.raises(ValueError):parse_xmile(valid.replace(SF,'urn:shadow'))
    with pytest.raises(ValueError):parse_xmile(native_xml(spec_attrs='sf:role="report"'))


def test_native_profile_keeps_literal_names_flow_references_views_and_raw_report_text():
    model=Model(stocks=[dict(id='s',name=' Stock ',initial_value=1,position=dict(x=11,y=22))],
        flows=[dict(name=' Flow ',equation='1',to_stock='s',position=dict(x=33,y=44))],
        variables=[dict(name=' Report ',role='report',equation="  IF(TIME=0,'label 雪',2)  ",position=dict(x=55,y=66))],
        tables=[dict(name=' Curve ',points=[(0,1),(1,2)])],time_settings=dict(start=0,end=2,dt=.25))
    _,restored,_=roundtrip(model)
    for kind in ('stocks','flows','variables'):
        assert [e.name for e in getattr(restored,kind)]==[e.name for e in getattr(model,kind)]
        assert [e.position for e in getattr(restored,kind)]==[e.position for e in getattr(model,kind)]
    assert restored.variables[0].equation==model.variables[0].equation
    legacy=parse_xmile(xml('<aux name=" Trim "><eqn>1</eqn></aux>'))
    assert legacy.variables[0].name=='Trim'

@pytest.mark.parametrize('extra',['<sim_specs/>','<sim_specs sf:rtol="NaN"/>'])
def test_native_profile_rejects_duplicate_simulation_settings_even_if_first_is_valid(extra):
    source=native_xml().replace('<model>',extra+'<model>')
    with pytest.raises(ValueError,match='unambiguous sim_specs'):parse_xmile(source)


def test_native_settings_and_role_extensions_cannot_hide_in_nested_core_wrappers():
    settings=f'<xmile xmlns:sf="{SF}" sf:compatibility="native-scalar-v1"><wrapper><xmile><sim_specs sf:rtol=".001"/></xmile></wrapper><model><variables/></model></xmile>'
    role=f'<xmile xmlns:sf="{SF}" sf:compatibility="native-scalar-v1"><wrapper><variables><aux name="Value" sf:role="report"><eqn>1</eqn></aux></variables></wrapper></xmile>'
    for source in (settings,role):
        with pytest.raises(ValueError):parse_xmile(source)


@pytest.mark.parametrize('change', ['bytes', 'add', 'remove'])
def test_roundtrip_audit_rejects_changed_tracked_model_manifest(tmp_path, change):
    import importlib.util
    import subprocess
    from pathlib import Path
    script=Path(__file__).resolve().parents[1]/'scripts/audit_xmile_roundtrips.py'
    spec=importlib.util.spec_from_file_location('roundtrip_audit',script)
    audit=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    models=tmp_path/'models'; models.mkdir()
    original=models/'original.json'; original.write_text('{"value":1}')
    subprocess.run(['git','add','models'],cwd=tmp_path,check=True)
    manifest=audit.tracked_model_hashes(tmp_path)
    audit.assert_model_manifest(tmp_path,manifest)
    if change=='bytes':
        original.write_text('{"value":2}')
    elif change=='add':
        (models/'new.json').write_text('{}')
        subprocess.run(['git','add','models/new.json'],cwd=tmp_path,check=True)
    else:
        subprocess.run(['git','rm','--cached','-q','models/original.json'],cwd=tmp_path,check=True)
    with pytest.raises(AssertionError,match='inventory or bytes changed'):
        audit.assert_model_manifest(tmp_path,manifest)


def test_full_tracked_library_xmile_roundtrip_audit(tmp_path):
    """Run the complete library gate through the existing pytest CI entry point."""
    import json
    import subprocess
    import sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    receipt=tmp_path/'xmile-roundtrips.json'
    subprocess.run([sys.executable,str(root/'scripts/audit_xmile_roundtrips.py'),
                    '--output',str(receipt)],cwd=root,check=True)
    result=json.loads(receipt.read_text())
    assert result['models']
    assert all(row['status']=='passed' for row in result['models'])
    assert result['counts']=={'passed':len(result['models'])}
