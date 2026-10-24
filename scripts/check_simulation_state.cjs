// Reproduce asynchronous analytics/model-edit races against the actual browser modules.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname,'..');
const element = () => ({hidden:false,textContent:'',innerHTML:'',className:'',appendChild(){},before(){},replaceChildren(){},remove(){}});
const nodes = new Map();
const document = {getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);},
  querySelector(){return element();},createElement(){return element();}};
const model = {stocks:[],flows:[],variables:[{id:'r',name:'Rate',equation:'1'}],tables:[],
  time_settings:{start:0,end:1,dt:1}};
let resolveAnalytics, aiContexts = [];
const sandbox = {document, d3:{schemeCategory10:[]}, console,
  App:{model, modelSnapshot(){return this.model;},escapeHtml:s=>s,showToast(){}},
  Analytics:{requestVersion:0,render(){},setResults(){return new Promise(resolve=>{resolveAnalytics=resolve;});}},
  AIAgent:{setContext(m,r){aiContexts.push({model:m,results:r});},render(){},clear(){}},
  Charts:{setResults(r){this.results=r;},render(){},container:element()}};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(root,'static/js/simulation.js'),'utf8')+';this.simulation=Simulation;',sandbox);
const simulation = sandbox.simulation;
const displayResults = simulation.displayResults;
simulation.displayResults = () => {};
(async()=>{
  const original={time:[0,1],values:{Rate:[1,1]},random_seed:null};
  const pending=simulation.acceptResults(original);
  sandbox.App.model.variables[0].equation='100';
  resolveAnalytics();
  await pending;
  assert.equal(aiContexts.length,0,'Old results must not be paired with edited equations');
  assert.equal(simulation.results,null,'Stale results must be removed');

  sandbox.App.model.variables[0].equation='1';
  const valid=simulation.acceptResults(original);
  resolveAnalytics();await valid;
  assert.equal(aiContexts.length,1);
  sandbox.App.model.variables[0].equation='2';
  assert.equal(aiContexts[0].model.variables[0].equation,'1','AI context owns its exact run snapshot');
  simulation.invalidateIfChanged();
  assert.equal(simulation.results,null);

  const waiting=simulation.acceptResults(original), version=sandbox.Analytics.requestVersion;
  simulation.clear();
  assert.ok(sandbox.Analytics.requestVersion>version,'Clear invalidates pending statistics');
  resolveAnalytics();await waiting;
  assert.equal(aiContexts.length,1,'Late completion cannot resurrect a cleared run');
  simulation.chartContainer=element();simulation.resultsContent=element();
  simulation.results={time:[0,.001,.002],values:{Rate:[1,1,1]}};
  simulation.resultModel={time_settings:{dt:.001}};
  displayResults.call(simulation);
  assert.match(simulation.resultsContent.innerHTML,/0 → 0\.002/);
  assert.match(simulation.resultsContent.innerHTML,/dt=0\.001/);
  console.log('Simulation snapshots, model edits and late analytics completion checks passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
