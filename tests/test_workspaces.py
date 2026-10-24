"""Capability isolation, preservation and concurrent page/agent editing."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.storage import workspaces as w
from app.core.model import Model
from app.core.simulator import simulate

@pytest.fixture(autouse=True)
def isolated(monkeypatch): monkeypatch.setattr(w,'_sessions',{})

def fixture_model():
    return Model(name='Page fixture',source='https://example.org/source',reference='Synthetic',
        stocks=[{'id':'s','name':'X','initial_value':100,'units':'kg'}],
        flows=[{'id':'f','name':'Input','equation':'5','to_stock':'s','units':'kg/year'}],
        tables=[{'name':'Curve','points':[(0,0),(1,1)]}],time_settings={'start':5,'end':6,'dt':.25}).model_dump(mode='json')

def test_capabilities_cannot_cross_sessions_or_appear_in_snapshots():
    a=w.create(fixture_model());b=w.create()
    assert a['workspace_key'] not in str(w.snapshot(a['workspace_key']))
    wrong=b['workspace_id']+'.'+a['workspace_key'].split('.')[1]
    with pytest.raises(w.WorkspaceMissing):w.snapshot(wrong)
    with pytest.raises(w.WorkspaceMissing):w.snapshot(a['workspace_id'])

def test_atomic_edits_preserve_inputs_and_reject_stale_writes():
    session=w.create(fixture_model());key=session['workspace_key']
    edited=w.edit_elements(key,[{'element_type':'flow','element_id':'f','changes':{'equation':'10'}}],1)
    assert edited['model']['source']=='https://example.org/source'
    assert edited['model']['stocks'][0]['units']=='kg'
    assert edited['model']['tables'][0]['name']=='Curve'
    assert edited['model']['flows'][0]['to_stock']=='s'
    with pytest.raises(w.WorkspaceConflict):w.replace_model(key,fixture_model(),1)
    with pytest.raises(w.WorkspaceError):w.edit_elements(key,[{'element_type':'flow','element_id':'f','changes':{'id':'oops'}}],2)
    assert w.snapshot(key)['revision']==2

def test_whole_batch_rolls_back_if_one_edit_is_invalid():
    key=w.create(fixture_model())['workspace_key']
    with pytest.raises(ValueError):w.edit_elements(key,[
        {'element_type':'flow','element_id':'f','changes':{'equation':'10'}},
        {'element_type':'stock','element_id':'s','changes':{'initial_value':float('inf')}}],1)
    assert w.snapshot(key)['model']['flows'][0]['equation']=='5'

def test_result_fenced_to_exact_model_and_browser_ack_is_separate():
    key=w.create(fixture_model())['workspace_key']
    model=Model.model_validate(w.snapshot(key)['model']);result=simulate(model)
    state=w.publish_result(key,result,1)
    assert state['revision']==2 and state['view']['section']=='chart'
    assert not state['browser']['connected']
    w.acknowledge(key,2)
    assert w.snapshot(key)['browser']['connected']
    assert 'model' not in w.snapshot(key,after_revision=2,include_result=True)
    assert w.snapshot(key,include_result=True)['result']['values']['X'][-1]==105
    w.replace_model(key,fixture_model(),2)
    with pytest.raises(w.WorkspaceConflict):w.publish_result(key,result,2)
    assert w.snapshot(key,include_result=True)['result'] is None

def test_expiry_capacity_and_disconnect(monkeypatch):
    key=w.create()['workspace_key']
    monkeypatch.setattr(w,'MAX_WORKSPACES',1)
    with pytest.raises(w.WorkspaceError):w.create()
    w.close(key)
    with pytest.raises(w.WorkspaceMissing):w.snapshot(key)
    key=w.create()['workspace_key']
    w._sessions[key.split('.')[0]]['touched']-=w.IDLE_SECONDS+1
    with pytest.raises(w.WorkspaceMissing):w.snapshot(key)

def test_bounded_result_memory_and_invalid_selection(monkeypatch):
    key=w.create(fixture_model())['workspace_key']
    monkeypatch.setattr(w,'MAX_RESULT_BYTES',1)
    with pytest.raises(w.WorkspaceError):w.publish_result(key,simulate(Model.model_validate(fixture_model())),1)
    with pytest.raises(w.WorkspaceError):w.set_view(key,selection='missing')
    assert w.snapshot(key)['revision']==1

def test_http_tokens_are_headers_and_conflicts_are_409(tmp_path,monkeypatch):
    from app.storage import models
    monkeypatch.setattr(models,'MODELS_DIR',str(tmp_path))
    client=TestClient(app)
    created=client.post('/api/workspaces',json={'model':fixture_model()})
    assert created.status_code==200 and created.headers['cache-control']=='no-store'
    session=created.json();path='/api/workspaces/'+session['workspace_id']
    headers={'Authorization':'Bearer '+session['workspace_key']}
    assert client.get(path).status_code==404
    assert client.get(path+'?token='+session['workspace_key']).status_code==404
    assert client.get(path,headers=headers).status_code==200
    assert client.put(path+'/model',headers=headers,json={'model':fixture_model(),'expected_revision':1}).status_code==200
    assert client.put(path+'/model',headers=headers,json={'model':fixture_model(),'expected_revision':1}).status_code==409
    assert client.delete(path,headers=headers).status_code==200
    assert not list(tmp_path.iterdir())
