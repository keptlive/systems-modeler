"""Real HTTP alias loading and actual browser load/save method preservation."""
import json, shutil, subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.model import Model
from app.core.simulator import simulate
from app.storage import models as storage
ROOT=Path(__file__).resolve().parents[1]
CANONICAL='may-chaos-population-eco'
def canonical():
    return Model.model_validate_json((ROOT/'models/economics/may-chaos-population-eco.json').read_bytes())
def setup(monkeypatch,models):
    monkeypatch.setattr(storage,'get_model',lambda key:models.get(key))
    def forbidden(*args,**kwargs):raise AssertionError('GET must never write storage')
    for n in ('create_model','update_model','delete_model'):monkeypatch.setattr(storage,n,forbidden)
    return TestClient(app)
@pytest.mark.parametrize('old,rate',[('may-logistic-chaos',3.7),('may-ecological-chaos-eco',3.8)])
def test_alias_is_fresh_preset_draft_with_no_writes_and_exact_population_reference(monkeypatch,old,rate):
    m=canonical();before=m.model_dump(mode='json');client=setup(monkeypatch,{CANONICAL:m})
    a=client.get('/api/models/'+old);b=client.get('/api/models/'+old)
    assert a.status_code==b.status_code==200
    assert a.json()['id'] not in (old,CANONICAL,b.json()['id'])
    assert a.headers['cache-control']=='no-store'
    assert 'unsaved' in a.headers['x-model-migration'] and 'columns differ' in a.headers['x-model-migration']
    draft=Model.model_validate(a.json())
    assert next(v.equation for v in draft.variables if v.name=='r')==str(rate)
    assert m.model_dump(mode='json')==before
    result=simulate(draft);values=[.1]
    for _ in range(100):values.append(values[-1]+(rate*values[-1]*(1-values[-1])-values[-1]))
    assert result.values['Population']==values
    assert result.time==list(range(101))
@pytest.mark.parametrize('old',['may-logistic-chaos','may-ecological-chaos-eco'])
def test_existing_old_definition_wins_unchanged(monkeypatch,old):
    existing=canonical();existing.id=old;existing.name='Private existing copy'
    response=setup(monkeypatch,{old:existing,CANONICAL:canonical()}).get('/api/models/'+old)
    assert response.json()==existing.model_dump(mode='json')
    assert 'x-model-migration' not in response.headers
def test_absent_and_incompatible_canonical_fail_clearly(monkeypatch):
    client=setup(monkeypatch,{})
    assert client.get('/api/models/may-logistic-chaos').status_code==404
    assert client.get('/api/models/unknown').status_code==404
    for change in ('period','missing_r','duplicate_r','stock'):
        m=canonical()
        if change=='period':m.time_settings.discrete_period=None
        elif change=='missing_r':m.variables=[v for v in m.variables if v.name!='r']
        elif change=='duplicate_r':m.variables.append(next(v for v in m.variables if v.name=='r').model_copy(deep=True))
        else:m.stocks.append(m.stocks[0].model_copy(deep=True))
        response=setup(monkeypatch,{CANONICAL:m}).get('/api/models/may-logistic-chaos')
        assert response.status_code==409 and 'contract changed' in response.json()['detail']
def test_actual_old_url_load_and_save_creates_new_never_overwrites(monkeypatch):
    node=shutil.which('node') or shutil.which('nodejs')
    if not node:pytest.skip('Node needed for actual browser load/save method checks')
    m=canonical();before=m.model_dump(mode='json')
    response=setup(monkeypatch,{CANONICAL:m}).get('/api/models/may-logistic-chaos')
    harness=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map(),notices=[],calls=[],saved=new Map();
global.document={getElementById:id=>{if(!elements.has(id))elements.set(id,{value:''});return elements.get(id);}};
global.window={location:{search:'?model=may-logistic-chaos'},addEventListener(){}};
global.Canvas={init(){},render(){},fitToModel(){}};
global.LLMInterface={init(){}};global.Simulation={init(){},clear(){}};
global.UserModels={get:id=>saved.get(id),save:m=>saved.set(m.id,m),populateDropdown(){}};
let load;global.setTimeout=fn=>{load=fn();return 0;};
global.fetch=async(url,opt)=>{
 calls.push({url,opt});
 if(!opt)return {ok:true,json:async()=>PAYLOAD,headers:new Headers({'X-Model-Migration':NOTICE})};
 assert.equal(opt.method,'POST');assert.equal(url,'/api/models');
 return {ok:true,json:async()=>({id:'user-new-copy'})};
};
const app=vm.runInThisContext(SOURCE+';App');
for(const n of ['checkMobile','bindEvents','initSimSettings','generateMissingConnectors','updatePropertiesPanel'])app[n]=()=>{};
app.showToast=message=>notices.push(message);
(async()=>{
 app.init();await load;
 assert.equal(calls[0].url,'/api/models/may-logistic-chaos');
 assert.equal(app.model.id,PAYLOAD.id);assert(notices.includes(NOTICE));
 assert.equal(saved.size,0);assert.equal(calls.length,1);
 await app.saveModel();assert.equal(calls.length,2);assert.equal(calls[1].opt.method,'POST');
 const body=JSON.parse(calls[1].opt.body);assert(!Object.hasOwn(body,'id'));
 assert.equal(body.variables.find(v=>v.name==='r').equation,'3.7');
 assert.equal(app.model.id,'user-new-copy');assert.equal(saved.size,1);
 assert(!calls.some(c=>c.opt?.method==='PUT'));
 const oldLocal={...PAYLOAD,id:'may-logistic-chaos',name:'Existing local private copy'};
 saved.set(oldLocal.id,oldLocal);const beforeCalls=calls.length;
 await app.loadModel(oldLocal.id);
 assert.equal(calls.length,beforeCalls);assert.equal(app.model,oldLocal);
 const fallback=[];
 global.fetch=async(url,opt)=>{
  fallback.push({url,opt});
  if(opt.method==='PUT')return {ok:false,status:404};
  assert.equal(url,'/api/models');assert.equal(opt.method,'POST');
  return {ok:true,json:async()=>({id:'user-local-preserved'})};
 };
 await app.saveModel();
 assert.deepEqual(fallback.map(c=>c.opt.method),['PUT','POST']);
 assert.equal(app.model.id,'user-local-preserved');
 assert.equal(JSON.parse(fallback[1].opt.body).name,'Existing local private copy');
 // Existing server/private old IDs still update normally, never POST.
 const realOld={...PAYLOAD,id:'may-ecological-chaos-eco'};saved.set(realOld.id,realOld);
 await app.loadModel(realOld.id);fallback.length=0;
 global.fetch=async(url,opt)=>{fallback.push({url,opt});return {ok:true,status:200,json:async()=>({id:realOld.id})};};
 await app.saveModel();assert.deepEqual(fallback.map(c=>c.opt.method),['PUT']);
 // A server error is not permission to create a duplicate.
 fallback.length=0;global.fetch=async(url,opt)=>{fallback.push({url,opt});return {ok:false,status:500};};
 await app.saveModel();assert.deepEqual(fallback.map(c=>c.opt.method),['PUT']);
 console.log('Actual old URL load and separate Save passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
    script='const SOURCE='+json.dumps((ROOT/'static/js/app.js').read_text())+';const PAYLOAD='+json.dumps(response.json())+';const NOTICE='+json.dumps(response.headers['x-model-migration'])+';'+harness
    result=subprocess.run([node],input=script,text=True,capture_output=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr
    assert m.model_dump(mode='json')==before
