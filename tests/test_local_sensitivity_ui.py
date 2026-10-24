"""Dependency-free behavioral checks for the additive Inspect panel."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_local_sensitivity_ui_contract():
    root = Path(__file__).resolve().parents[1]
    node = shutil.which('node') or shutil.which('nodejs')
    if not node and Path('/mnt/c/Program Files/nodejs/node.exe').exists():
        node = '/mnt/c/Program Files/nodejs/node.exe'
    if not node:
        pytest.skip('Node required for browser-independent UI checks')
    source = (root / 'static/js/local-sensitivity.js').read_text()
    harness = r'''
const assert=require('node:assert/strict'),vm=require('node:vm');
class E {
 constructor(tag){this.tagName=tag;this.children=[];this.listeners={};this.value='';this._text='';this.className='';}
 appendChild(n){n.remove();this.children.push(n);n.parentNode=this;return n;}
 append(...ns){for(const n of ns)this.appendChild(n);}
 remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(x=>x!==this);this.parentNode=null;}
 after(n){const p=this.parentNode;n.remove();p.children.splice(p.children.indexOf(this)+1,0,n);n.parentNode=p;}
 replaceChildren(){for(const n of this.children)n.parentNode=null;this.children=[];this._text='';}
 set textContent(t){this.replaceChildren();this._text=String(t);}get textContent(){return this._text+this.children.map(n=>n.textContent).join(' ');}
 setAttribute(k,v){this[k]=v;} addEventListener(k,f){(this.listeners[k]??=[]).push(f);}removeEventListener(k,f){this.listeners[k]=(this.listeners[k]||[]).filter(x=>x!==f);}
 querySelector(q){return this.children.flatMap(n=>[n,...n.all()]).find(n=>q[0]==='#'?n.id===q.slice(1):q[0]==='.'?n.className.split(' ').includes(q.slice(1)):n.tagName===q)||null;}
 all(){return this.children.flatMap(n=>[n,...n.all()]);}get isConnected(){return this===document.body||this===document.head||Boolean(this.parentNode?.isConnected);}
}
global.document={createElement:t=>new E(t),body:new E('body'),head:new E('head'),addEventListener(){},getElementById(id){return this.body.querySelector('#'+id);}};
global.MutationObserver=class{observe(){}};
const model={name:'Fixture',stocks:[{id:'stock-id',name:'Stock',units:'kg'}],flows:[],variables:[{id:'p-id',name:'Parameter',equation:'2',units:'s'},{id:'q-id',name:'Other',equation:'3'},{id:'computed',equation:'2+3'}]};
let current=structuredClone(model);global.App={modelSnapshot:()=>current};global.ModelValidation={snapshot:model};
global.Simulation=Object.freeze({results:Object.freeze({sentinel:1})});const unchanged=JSON.stringify([model,Simulation]);
const ui=vm.runInThisContext(UI_SOURCE+';LocalSensitivity');
const dialog=document.createElement('dialog');dialog.id='input-check-dialog';document.body.appendChild(dialog);const body=document.createElement('div');body.className='inspection-body';dialog.appendChild(body);const existing=document.createElement('section');existing.className='inspection-investigate';existing.textContent='Existing timestep refinement';body.appendChild(existing);
ui.init();const s=ui.session;assert(s);assert.equal(s.rows[0].step.value,'');assert.equal(s.parameters.length,2);ui.reconcile();assert.equal(body.all().filter(n=>n.id==='local-sensitivity-panel').length,1);assert(body.textContent.includes('Existing timestep refinement'));
assert.equal(ui.literal('1e309'),null);assert.equal(ui.literal('2+3'),null);assert.equal(ui.literal('-0x10'),-16);assert.equal(ui.format(null),'Unavailable');assert.notEqual(ui.format(1e-100),'0');
assert.throws(()=>ui.payload(s),/stock/);s.output.value='stock-id';s.rows[0].select.value='p-id';for(const h of ['', '0','-1','Infinity']){s.rows[0].step.value=h;assert.throws(()=>ui.payload(s),/positive finite/);}s.rows[0].step.value='.01';assert.deepEqual(ui.payload(s).parameters,[{id:'p-id',step:.01}]);
ui.addParameter(s);s.rows[1].select.value='p-id';s.rows[1].step.value='.1';assert.throws(()=>ui.payload(s),/only once/);s.rows[1].select.value='q-id';
const report={status:'partial_failure',baseline_output:4,output_units:'kg',actual_final_sample_time:10,rows:[{parameter_id:'p-id',parameter_name:'<script>bad</script>',parameter_units:'s',status:'locally_consistent',derivative:2,elasticity:null,elasticity_undefined_reason:'elasticity_underflow',small_baseline_warning:true,resolution_warning:true},{parameter_id:'q-id',status:'failed',failures:[{code:'simulation_failed',message:'Exact failure'}]}]};
(async()=>{let calls=0;global.fetch=async(url,opt)=>{calls++;assert.equal(url,'/api/sensitivity/local');assert.equal(JSON.parse(opt.body).output_stock_id,'stock-id');return{ok:true,json:async()=>report};};await ui.run(s);assert.equal(calls,1);assert(s.results.textContent.includes('kg / (s)'));assert(s.results.textContent.includes('elasticity underflow'));assert(s.results.textContent.includes('Exact failure'));assert(s.results.textContent.includes('Baseline output is very small'));assert(s.results.textContent.includes('<script>bad</script>'));assert.equal(s.results.all().filter(n=>n.tagName==='script').length,0);assert.equal(JSON.stringify([model,Simulation]),unchanged);
for(const event of ['input','change']){ui.render(report,s.results);s.form.listeners[event][0]();assert.equal(s.results.children.length,0);assert(s.status.textContent.includes('Selections changed'));}
ui.render(report,s.results);s.rows[1].remove.listeners.click[0]();assert.equal(s.results.children.length,0);ui.render(report,s.results);ui.addParameter(s);assert.equal(s.results.children.length,0);s.rows[1].select.value='q-id';s.rows[1].step.value='.1';
current={...current,name:'Changed'};await ui.run(s);assert.equal(calls,1);assert(s.status.textContent.includes('reopen Inspect'));current=structuredClone(model);
global.fetch=async()=>({ok:false,json:async()=>({failure:{code:'sensitivity_busy',message:'Try later'}})});await ui.run(s);assert(s.status.textContent.includes('sensitivity_busy'));assert.equal(s.results.children.length,0);
let resolve;global.fetch=(_,opt)=>new Promise(r=>{resolve=r;assert(!opt.signal.aborted);});const pending=ui.run(s);assert(s.busy);s.cancel.listeners.click[0]();assert(s.controller.signal.aborted);resolve({ok:true,json:async()=>report});await pending;assert.equal(s.results.children.length,0);assert(!s.busy);
global.fetch=()=>new Promise(r=>{resolve=r;});const closing=ui.run(s);s.close();assert(s.controller.signal.aborted);resolve({ok:true,json:async()=>report});await closing;assert.equal(s.results.children.length,0);
const timer=global.setTimeout;let fire;global.setTimeout=fn=>{fire=fn;return 0;};const timeoutRun=ui.run(s);fire();resolve({ok:true,json:async()=>report});await timeoutRun;global.setTimeout=timer;assert(s.status.textContent.includes('Request timed out'));assert.equal(s.results.children.length,0);
s.root.remove();ui.reconcile();assert(s.disposed);console.log('Local sensitivity UI checks passed');})().catch(e=>{console.error(e);process.exitCode=1;});
'''
    result = subprocess.run([node], input='const UI_SOURCE='+json.dumps(source)+';\n'+harness,
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'UI checks passed' in result.stdout
