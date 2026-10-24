"""Actual export module behavior: preserve both formats and render bounded text errors."""
import json,shutil,subprocess
from pathlib import Path
import pytest

def test_export_errors_are_bounded_actionable_text_and_json_stays_available():
    root=Path(__file__).parents[1]
    node=shutil.which('node') or shutil.which('nodejs')
    if not node and Path('/mnt/c/Program Files/nodejs/node.exe').exists():node='/mnt/c/Program Files/nodejs/node.exe'
    if not node:pytest.skip('Node needed for actual JavaScript contract checks')
    source=(root/'static/js/xmile-download.js').read_text()
    harness=r'''
const assert=require('node:assert/strict'),vm=require('node:vm');
class Element{
 constructor(tag){this.tagName=tag;this.children=[];this.listeners={};this.textContent='';this.disabled=false;}
 appendChild(n){this.children.push(n);n.parentNode=this;return n;}
 addEventListener(k,f){this.listeners[k]=f;}setAttribute(k,v){this[k]=v;}
 click(){this.clicked=true;return this.listeners.click?.();}remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(x=>x!==this);}
 showModal(){this.open=true;}close(){this.open=false;this.closed=true;}
}
let ready;const toolbar=new Element('button');global.document={body:new Element('body'),createElement:t=>new Element(t),addEventListener:(event,fn)=>{assert.equal(event,'DOMContentLoaded');ready=fn;},getElementById:id=>{assert.equal(id,'btn-download');return toolbar;}};
let alerts=[],blobs=[],revoked=[];global.alert=t=>alerts.push(t);global.URL={createObjectURL:b=>{blobs.push(b);return'blob:fixture';},revokeObjectURL:u=>revoked.push(u)};
global.App={model:{id:'fixture',name:'Draft <name>',stocks:[{id:'x',name:'X',initial_value:1}],flows:[],variables:[],time_settings:{end:3,dt:1,discrete_period:1}}};const before=JSON.stringify(App.model);
const errorMessage=vm.runInThisContext(SOURCE+';xmileExportErrorMessage');ready();
const dialog=document.body.children[0],buttons=dialog.children.filter(n=>n.tagName==='button');assert.deepEqual(buttons.map(n=>n.textContent),['Download XMILE','Download JSON','Cancel']);
(async()=>{
 const detail='Discrete-period contracts are unsupported by this XMILE exporter; use JSON to preserve the period';
 const response=()=>new Response(JSON.stringify({detail}),{status:422,headers:{'content-type':'application/json'}});
 assert((await errorMessage(response())).includes(detail));
 assert((await errorMessage(new Response(JSON.stringify({failure:{code:'bad',message:'Typed failure'}}),{status:422,headers:{'content-type':'application/problem+json'}}))).includes('Typed failure'));
 const hostile='<img src=x onerror=bad()>\n\u0000';const plain=await errorMessage(new Response(JSON.stringify({detail:hostile}),{headers:{'content-type':'application/json'}}));assert(plain.includes('<img src=x onerror=bad()>'));assert(!plain.includes('\n')&&!plain.includes('\u0000'));
 for(const body of ['{bad json','null','{}','{"detail":[]}'])assert((await errorMessage(new Response(body,{headers:{'content-type':'application/json'}}))).includes('Choose Download JSON'));
 assert(!(await errorMessage(new Response('<html>private server error</html>',{headers:{'content-type':'text/html'}}))).includes('private server'));
 const long=await errorMessage(new Response('x'.repeat(2000),{headers:{'content-type':'text/plain'}}));assert(long.startsWith('x'.repeat(500)+' '));assert(!long.includes('x'.repeat(501)));
 let reads=0,cancels=0;const oversized={headers:new Headers({'content-type':'application/json'}),body:{getReader:()=>({read:async()=>{reads++;return{done:false,value:new Uint8Array(4000).fill(120)};},cancel:async()=>{cancels++;},releaseLock(){}})}};
 assert((await errorMessage(oversized)).includes('Choose Download JSON'));assert.equal(reads,3);assert.equal(cancels,1);
 reads=0;const emptyChunks={headers:new Headers({'content-type':'text/plain'}),body:{getReader:()=>({read:async()=>{reads++;return{done:false,value:new Uint8Array(0)};},cancel:async()=>{},releaseLock(){}})}};await errorMessage(emptyChunks);assert.equal(reads,32);
 const failedRead={headers:new Headers({'content-type':'application/json'}),body:{getReader:()=>({read:async()=>{throw new Error('failure');},cancel:async()=>{},releaseLock(){}})}};assert((await errorMessage(failedRead)).includes('Choose Download JSON'));
 const brokenReader={headers:new Headers({'content-type':'application/json'}),body:{getReader(){throw new Error('locked');}}};assert((await errorMessage(brokenReader)).includes('Choose Download JSON'));
 const originalTimer=global.setTimeout,originalClear=global.clearTimeout;let stalledCancelled=false;global.setTimeout=fn=>{queueMicrotask(fn);return 0;};global.clearTimeout=()=>{};
 const stalled={headers:new Headers({'content-type':'application/json'}),body:{getReader:()=>({read:()=>new Promise(()=>{}),cancel:async()=>{stalledCancelled=true;},releaseLock(){}})}};assert((await errorMessage(stalled)).includes('Choose Download JSON'));assert(stalledCancelled);global.setTimeout=originalTimer;global.clearTimeout=originalClear;
 let calls=0;global.fetch=async(url,opt)=>{calls++;assert.equal(url,'/api/models/export/xmile');assert.deepEqual(JSON.parse(opt.body),App.model);return response();};toolbar.click();assert(dialog.open);await buttons[0].click();assert.equal(calls,1);assert(dialog.open);assert(!buttons[0].disabled);assert(alerts[0].includes(detail));assert(alerts[0].includes('Choose Download JSON'));assert.equal(document.body.children.filter(n=>n.tagName==='img'||n.tagName==='script').length,0);
 await buttons[1].click();assert(dialog.closed);assert.equal(calls,1);assert.deepEqual(JSON.parse(await blobs.at(-1).text()),App.model);assert.equal(JSON.stringify(App.model),before);assert(revoked.includes('blob:fixture'));
 // Existing successful XMILE download and Cancel behavior remain usable.
 global.fetch=async()=>new Response('<xmile/>',{headers:{'content-type':'application/xml'}});toolbar.click();await buttons[0].click();assert.equal(await blobs.at(-1).text(),'<xmile/>');toolbar.click();buttons[2].click();assert(dialog.closed);
 console.log('Export error and preservation checks passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
    result=subprocess.run([node],input='const SOURCE='+json.dumps(source)+';\n'+harness,text=True,capture_output=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'preservation checks passed' in result.stdout
