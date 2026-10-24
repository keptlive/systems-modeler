const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const nodes=new Map(), downloads=[];
function node(){return {innerHTML:'',textContent:'',hidden:false,disabled:false,remove(){},appendChild(){},replaceChildren(){},before(){},click(){downloads.push(this.download)}};}
let listener, blob;
const document={body:node(),getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)},querySelector(){return node()},createElement:node,addEventListener(type,fn){listener=fn}};
const failure={code:'unresolved_equations',time:1,root_errors:[{element:'<Fault>',code:'division_by_zero',equation:'1/0'}],reproduction:{normalized_model_sha256:'abc',engine_sha256:{'app/core/simulator.py':'xyz'},settings:{start:0,end:2,dt:.5,random_seed:42}}};
const model={stocks:[],flows:[],variables:[{id:'v',name:'Fault',equation:'1/0'}],time_settings:{start:0,end:2,dt:.5}};
const context={document,d3:{schemeCategory10:[]},console:{error(){}},setTimeout(fn){fn()},Blob:class{constructor(parts){blob=parts.join('')}},URL:{createObjectURL(){return 'blob:report'},revokeObjectURL(){}},
 App:{model,modelSnapshot(){return this.model},escapeHtml(s){return String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')},showToast(){}},
 fetch:async()=>({ok:false,json:async()=>({detail:'Division by zero',failure})})};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'static/js/simulation.js'),'utf8')+';this.sim=Simulation;',context);
(async()=>{
 const s=context.sim;s.init();await s.run();
 assert.match(s.failureHTML(),/Download failure report/);assert.match(s.failureHTML(),/&lt;Fault&gt;/);assert.ok(!s.failureHTML().includes('<Fault>'));
 context.App.model.variables[0].equation='99';
 let report=s.failureReport();assert.equal(report.model.variables[0].equation,'1/0');assert.equal(report.settings.random_seed,42);assert.equal(report.failure.reproduction.engine_sha256['app/core/simulator.py'],'xyz');
 report.model.variables[0].equation='changed';assert.equal(s.failureReport().model.variables[0].equation,'1/0');
 listener({target:{closest:()=>true}});assert.deepEqual(downloads,['model-failure-report.json']);assert.equal(JSON.parse(blob).model.variables[0].equation,'1/0');
 s.invalidateIfChanged();assert.equal(s.failureReport(),null);
 s.results={time:[0,1],values:{Fault:[1,1]}};s.resultModel=JSON.parse(JSON.stringify(context.App.model));
 context.App.model.variables[0].role='report';s.invalidateIfChanged();assert.equal(s.results,null,'Changing report role invalidates old numerical results');
 s.clear();assert.equal(s.failureReport(),null);assert.ok(!s.failureHTML().includes('Download failure report'));
 console.log('Failure export preserves exact failed inputs, effective seed, engine evidence and escaped diagnostics; stale reports clear.');
})().catch(e=>{console.error(e);process.exitCode=1});
