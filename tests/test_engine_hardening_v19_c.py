"""Cross-path timing, failures, random replay and workspace boundary regressions."""
import asyncio,json,math,random,sys
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp.exceptions import ToolError
from app.api import simulate as api
from app.core.model import Model,TimeSettings,TimeSettingsPatch,SimulationRequest,SimulationResult
from app.core.simulator import simulate
from app.core.equations import EquationError
from app.core.failure_diagnostics import failure_payload
from app.core.validation import inspect_inputs
from app import mcp_server as tools
from app.storage import workspaces as w
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def client():
 app=FastAPI();app.include_router(api.router,prefix='/api')
 from app.main import invalid_request
 app.add_exception_handler(RequestValidationError,invalid_request)
 return TestClient(app)
@pytest.fixture(autouse=True)
def isolate_workspaces(monkeypatch):monkeypatch.setattr(w,'_sessions',{})
def fixture_model(method='radau',randomized=False):
 return Model(name='Boundary fixture',stocks=[{'id':'x','name':'X','initial_value':1,'units':'kg'}],
  flows=[{'id':'f','name':'Change','equation':'RANDOM(0,1)' if randomized else '-X','to_stock':'x','units':'kg/s'}],
  variables=[{'id':'status','name':'Status','role':'report','equation':"IF(X > .8, 'High', 'Low')"}],
  time_settings={'start':5,'end':6,'dt':.1,'integration_method':method,'rtol':1e-8,'atol':1e-11,'random_seed':137})
def invalid_model():
 return Model(stocks=[{'id':'x','name':'X','initial_value':0}],variables=[
  {'id':'dependent','name':'Dependent','equation':'Bad + 1'},
  {'id':'bad','name':'Bad','equation':'1/X'}],time_settings={'start':5,'end':6,'dt':.1})

@pytest.mark.parametrize('method',['euler','rk4','radau'])
def test_one_model_direct_rest_mcp_and_workspace_results_match(client,method):
 m=fixture_model(method);body=m.model_dump(mode='json');settings=TimeSettingsPatch(dt=.2).apply_to(m.time_settings)
 exact=simulate(m,settings);rest=client.post('/api/simulate',json={'model':body,'time_settings':{'dt':.2}})
 assert rest.status_code==200
 assert rest.json()==exact.model_dump(mode='json')
 mc=tools.simulate_model(model_json=body,dt=.2,max_points=2000)
 assert mc['settings']==settings.model_dump() and mc['data']['time']==exact.time
 assert mc['data']['X']==exact.values['X'] and mc['report_values']==exact.report_values
 assert mc['integration_diagnostics']==exact.integration_diagnostics
 session=w.create(body);key=session['workspace_key']
 edited=tools.edit_workspace_elements(key,[tools.WorkspaceElementEdit(element_type='stock',element_id='x',changes={'units':'kg'})],1,TimeSettingsPatch(dt=.2))
 assert edited['model']['time_settings']==settings.model_dump()
 updated=tools.run_workspace(key,2);stored=w.snapshot(key,include_result=True)['result']
 assert stored==exact.model_dump(mode='json') and updated['time_points']==len(exact.time)
 assert updated['statistics']['X']['final']==exact.values['X'][-1]

@pytest.mark.parametrize('endpoint',['simulate','validate','investigate'])
def test_all_rest_boundaries_inherit_shifted_horizon_method_and_tolerances(client,endpoint):
 m=fixture_model();result=client.post('/api/'+endpoint,json={'model':m.model_dump(mode='json'),'time_settings':{'dt':.2}})
 assert result.status_code==200,result.text
 body=result.json()
 if endpoint=='simulate':assert body['time'][0]==5 and body['time'][-1]==6 and body['integration_diagnostics']['method']=='radau'
 elif endpoint=='validate':assert body['inputs']['time_settings']==TimeSettingsPatch(dt=.2).apply_to(m.time_settings).model_dump()
 else:assert body['settings']==TimeSettingsPatch(dt=.2).apply_to(m.time_settings).model_dump()

@pytest.mark.parametrize('endpoint',['simulate','validate','investigate'])
def test_ambiguous_or_missing_model_selection_never_silently_chooses(client,endpoint):
 body=fixture_model().model_dump(mode='json')
 assert client.post('/api/'+endpoint,json={'model':body,'model_id':'ignored'}).status_code==422
 assert client.post('/api/'+endpoint,json={}).status_code==422

@pytest.mark.parametrize('endpoint',['simulate','validate','investigate'])
def test_model_resolution_missing_id_is_consistent_404(client,endpoint,monkeypatch):
 monkeypatch.setattr(api.storage,'get_model',lambda key:None)
 assert client.post('/api/'+endpoint,json={'model_id':'missing'}).status_code==404

@pytest.mark.parametrize('endpoint',['simulate','validate','investigate'])
def test_partial_start_is_validated_only_after_model_merge(client,endpoint):
 m=fixture_model();m.time_settings=TimeSettings(start=199,end=201,dt=.2,integration_method='rk4')
 response=client.post('/api/'+endpoint,json={'model':m.model_dump(mode='json'),'time_settings':{'start':200}})
 assert response.status_code==200,response.text

@pytest.mark.parametrize('field',['start','end','dt','integration_method','rtol','atol'])
def test_explicit_null_is_not_an_implicit_reset(client,field):
 assert client.post('/api/simulate',json={'model':fixture_model().model_dump(mode='json'),'time_settings':{field:None}}).status_code==422

def test_seed_preserved_unless_explicitly_cleared(client,monkeypatch):
 m=fixture_model('euler',True);body=m.model_dump(mode='json');exact=simulate(m,TimeSettingsPatch(dt=.2).apply_to(m.time_settings))
 one=client.post('/api/simulate',json={'model':body,'time_settings':{'dt':.2}}).json()
 assert one['random_seed']==137 and one['values']==exact.values
 monkeypatch.setattr(random.SystemRandom,'randrange',lambda *args,**kwargs:654321)
 reset=client.post('/api/simulate',json={'model':body,'time_settings':{'dt':.2,'random_seed':None}}).json()
 assert reset['random_seed']==654321
 replay=client.post('/api/simulate',json={'model':body,'time_settings':{'dt':.2,'random_seed':654321}}).json()
 assert reset==replay
 key=w.create(body)['workspace_key'];edited=w.edit_elements(key,[{'element_type':'stock','element_id':'x','changes':{'units':'kg'}}],1,time_settings={'dt':.2,'random_seed':None})
 ts=edited['model']['time_settings'];assert ts['random_seed'] is None and ts['start']==5 and ts['end']==6 and ts['integration_method']=='euler'

def test_complete_python_time_settings_remain_complete_overrides():
 m=fixture_model();legacy=TimeSettings(end=2,dt=.5)
 request=SimulationRequest(model=m,time_settings=legacy)
 assert request.time_settings.apply_to(m.time_settings).model_dump()==legacy.model_dump()
 assert TimeSettingsPatch(dt=.2).apply_to(m.time_settings).start==5

def test_recurrence_cannot_be_erased_by_partial_timing_edits(client):
 m=Model(stocks=[{'id':'x','name':'X','initial_value':8}],flows=[{'name':'Half','equation':'-.5*X','to_stock':'x'}],time_settings={'end':3,'dt':1,'discrete_period':1})
 body=m.model_dump(mode='json')
 result=client.post('/api/simulate',json={'model':body,'time_settings':{'end':4,'discrete_period':None}})
 assert result.status_code==200 and result.json()['values']['X']==[8,4,2,1,.5]
 assert client.post('/api/simulate',json={'model':body,'time_settings':{'dt':.5,'discrete_period':None}}).status_code==422
 key=w.create(body)['workspace_key']
 w.edit_elements(key,[{'element_type':'stock','element_id':'x','changes':{'units':'items'}}],1,time_settings={'end':4,'discrete_period':None})
 assert w.snapshot(key)['model']['time_settings']['discrete_period']==1


def test_failure_cause_and_reproduction_survive_direct_rest_mcp(client):
 m=invalid_model();settings=TimeSettingsPatch(dt=.2).apply_to(m.time_settings)
 with pytest.raises(EquationError) as direct:simulate(m,settings)
 expected=failure_payload(direct.value)
 response=client.post('/api/simulate',json={'model':m.model_dump(mode='json'),'time_settings':{'dt':.2}})
 assert response.status_code==422 and response.json()['failure']==expected
 with pytest.raises(ToolError) as mc:tools.simulate_model(model_json=m.model_dump(mode='json'),dt=.2)
 assert json.loads(str(mc.value))['failure']==expected
 assert expected['root_errors'][0]['code']=='division_by_zero'
 assert expected['blocked_errors'][0]['root_cause']['element']=='Bad'
 assert expected['reproduction']['settings']['start']==5
 assert len(expected['reproduction']['normalized_model_sha256'])==64
 assert all(len(v)==64 for v in expected['reproduction']['engine_sha256'].values())
 validation=inspect_inputs(m)
 issue=next(x for x in validation['issues'] if x['code']=='numerical_input_check')
 assert issue['failure']['root_errors']==expected['root_errors']
 assert issue['failure']['blocked_errors']==expected['blocked_errors']
 assert issue['failure']['reproduction']['settings']['end']==pytest.approx(5.1)

def test_capacity_failure_stays_machine_readable_and_json_finite(client):
 m=Model(variables=[{'name':'V','equation':'1'}],time_settings={'end':100001,'dt':1})
 response=client.post('/api/simulate',json={'model':m.model_dump(mode='json')})
 assert response.status_code==422 and response.json()['failure']['code']=='capacity_exceeded'
 with pytest.raises(ToolError) as err:tools.simulate_model(model_json=m.model_dump(mode='json'))
 data=json.loads(str(err.value));assert data['failure']==response.json()['failure']
 json.dumps(data,allow_nan=False)

def test_ambiguous_target_edits_and_selection_are_atomic():
 m=Model(variables=[{'id':'ok','name':'Other','equation':'3'},{'id':'dup','name':'First','equation':'1'},{'id':'dup','name':'Second','equation':'2'}])
 key=w.create(m.model_dump(mode='json'))['workspace_key']
 assert any(i['code']=='duplicate_element_id' for i in inspect_inputs(m,numerical_check=False)['issues'])
 with pytest.raises(w.WorkspaceError,match='Ambiguous'):
  w.edit_elements(key,[{'element_type':'variable','element_id':'ok','changes':{'equation':'9'}},{'element_type':'variable','element_id':'dup','changes':{'equation':'7'}}],1)
 assert w.snapshot(key)['revision']==1 and w.snapshot(key)['model']['variables'][0]['equation']=='3'
 with pytest.raises(w.WorkspaceError,match='Ambiguous'):w.set_view(key,selection='dup',expected_revision=1)
 assert w.snapshot(key)['revision']==1

@pytest.mark.parametrize('model,code',[
 ({'variables':[{'name':'A B','equation':'1'},{'name':'a_b','equation':'2'}]},'name_collision'),
 ({'variables':[{'name':'TIME','equation':'1'}]},'reserved_name'),
 ({'tables':[{'name':'T','points':[[0,0],[1,1]]},{'name':'t','points':[[0,0],[1,2]]}]},'duplicate_lookup_name'),
 ({'stocks':[{'id':'x','name':'First'},{'id':'other','name':'x'}]},'ambiguous_stock_reference')])
def test_static_validation_reports_structure_without_running(model,code):
 result=inspect_inputs(Model.model_validate(model),numerical_check=False)
 assert not result['valid'] and any(i['code']==code for i in result['issues'])

def test_shifted_one_step_validation_retains_nominal_dt_and_real_failure():
 m=Model(stocks=[{'id':'x','name':'X','initial_value':0}],flows=[{'name':'Step','equation':'1/DT','to_stock':'x'}],time_settings={'start':5,'end':6,'dt':.1})
 assert inspect_inputs(m)['numerical_check']=='completed_one_step'
 ts=TimeSettings(start=5,end=5.1,dt=.1)
 assert ts.dt==.1
 r=simulate(m,ts)
 assert r.values['Step']==[10,10]
 assert r.values['X'][-1]==pytest.approx(1)
 with pytest.raises(ValueError):TimeSettings(start=5,end=5.09,dt=.1)
 with pytest.raises(ValueError):TimeSettings(start=1e16,end=1e16+2,dt=2.5)

def test_real_sdk_sampling_seed_replay_and_json_error_transport():
 async def exercise():
  params=StdioServerParameters(command=sys.executable,args=['-m','app.mcp_server'],cwd=str(ROOT))
  async with stdio_client(params) as (read,write):
   async with ClientSession(read,write) as session:
    await session.initialize();m=fixture_model('euler',True).model_dump(mode='json')
    m['time_settings']['random_seed']=None
    first=await session.call_tool('simulate_model',{'model_json':m,'max_points':4})
    assert not first.isError
    data=first.structuredContent or json.loads(first.content[0].text)
    assert data['sampled'] and len(data['data']['time'])==4 and data['data']['time'][0]==5 and data['data']['time'][-1]==6
    replay=await session.call_tool('simulate_model',{'model_json':m,'max_points':4,'random_seed':data['random_seed']})
    two=replay.structuredContent or json.loads(replay.content[0].text)
    assert data['data']==two['data'] and data['summary']==two['summary'] and data['report_values']==two['report_values']
    seeded=Model.model_validate(m);seeded.time_settings.random_seed=data['random_seed'];full=simulate(seeded)
    indices=[round(i*(len(full.time)-1)/3) for i in range(4)]
    assert data['data']['X']==[full.values['X'][i] for i in indices]
    assert data['summary']['X']['mean']==pytest.approx(sum(full.values['X'])/len(full.time))
    bad=invalid_model().model_dump(mode='json')
    error=await session.call_tool('simulate_model',{'model_json':bad})
    assert error.isError
    text='\n'.join(c.text for c in error.content if hasattr(c,'text'));failure=json.loads(text[text.index('{"failure"'):])['failure']
    assert failure['code']=='unresolved_equations' and failure['root_errors'][0]['element']=='Bad'
    assert failure['blocked_errors'][0]['element']=='Dependent'
    assert len(failure['reproduction']['normalized_model_sha256'])==64
    assert failure['reproduction']['settings']['start']==5
 asyncio.run(exercise())

@pytest.mark.parametrize('field,value',[
 ('time',[0,float('nan')]),('values',{'X':[0,float('inf')]}),
 ('report_values',{'Label':[float('-inf')]}),
 ('integration_diagnostics',{'nested':[{'work':float('nan')}]}),
 ('integration_diagnostics',{'nested':{float('nan'):1}}),
 ('integration_diagnostics',{'nested':[{'key'+chr(0xd800):1}]}),
 ('report_values',{'Label':[chr(0xd800)]})])
def test_results_reject_nonfinite_and_non_unicode_text(field,value):
 data={'time':[0,1],'values':{'X':[0,1]},field:value}
 with pytest.raises(ValueError):SimulationResult.model_validate(data)

def test_result_text_labels_remain_text():
 result=SimulationResult(time=[0,1],values={'X':[0,1]},report_values={'Label':['Infinity','NaN']})
 assert result.report_values['Label']==['Infinity','NaN']
 json.dumps(result.model_dump(mode='json'),allow_nan=False)

@pytest.mark.parametrize('unvalidated',[False,True])
def test_invalid_result_publication_is_atomic(unvalidated):
 session=w.create(fixture_model().model_dump(mode='json'));key=session['workspace_key']
 result=simulate(fixture_model());w.publish_result(key,result,1)
 before=w.snapshot(key,include_result=True)
 bad=result.model_copy(deep=True) if unvalidated else result.model_dump(mode='json')
 if unvalidated:bad.values['X'][0]=float('inf')
 else:bad['integration_diagnostics']={'nested':[float('nan')]}
 with pytest.raises(w.WorkspaceError,match='finite JSON'):w.publish_result(key,bad,2)
 assert w.snapshot(key,include_result=True)==before

def test_unicode_scalar_names_roundtrip_without_normalization(client):
 name='Population '+chr(0x1f30d)+' e'+chr(0x301)
 m=Model(variables=[{'name':name,'equation':'1'}],time_settings={'end':1})
 expected=simulate(m).model_dump(mode='json')
 # Raw escaped JSON also exercises correct decoding of supplementary pairs.
 response=client.post('/api/simulate',content=json.dumps({'model':m.model_dump(mode='json')}),headers={'content-type':'application/json'})
 assert response.status_code==200 and response.json()==expected
 assert list(response.json()['values'])==[name]
 assert tools.simulate_model(model_json=m.model_dump(mode='json'))['data'][name]==expected['values'][name]

def test_invalid_unicode_model_rejected_before_transport(client):
 bad={'variables':[{'name':chr(0xd800),'equation':'1'}],'time_settings':{'end':1}}
 with pytest.raises(ValueError,match='Unicode scalar'):Model.model_validate(bad)
 response=client.post('/api/simulate',content=json.dumps({'model':bad}),headers={'content-type':'application/json'})
 assert response.status_code==422
 session=w.create(fixture_model().model_dump(mode='json'));key=session['workspace_key'];before=w.snapshot(key)
 with pytest.raises(ValueError):w.replace_model(key,bad,1)
 assert w.snapshot(key)==before

def test_failed_auto_seed_run_keeps_replay_context_across_transports(client,monkeypatch):
 monkeypatch.setattr(random.SystemRandom,'randrange',lambda *args:654321)
 m=invalid_model();m.stocks[0].equation='RANDOM(1,2)';m.variables[1].equation='IF(TIME > 5, 1/(X-X), X)';m.time_settings.random_seed=None
 with pytest.raises(EquationError) as failed:simulate(m)
 expected=failure_payload(failed.value);seed=expected['random_seed']
 assert seed==654321 and expected['reproduction']['settings']['random_seed']==seed
 assert 1<=expected['stock_values']['X']<=2
 override=TimeSettingsPatch(random_seed=seed).apply_to(m.time_settings)
 with pytest.raises(EquationError) as replay:simulate(m,override)
 assert failure_payload(replay.value)==expected
 response=client.post('/api/simulate',json={'model':m.model_dump(mode='json'),'time_settings':{'random_seed':seed}})
 assert response.status_code==422 and response.json()['failure']==expected
 with pytest.raises(ToolError) as mc:tools.simulate_model(model_json=m.model_dump(mode='json'),random_seed=seed)
 assert json.loads(str(mc.value))['failure']==expected
