// Native structured results must remain usable in every existing chart control.
// Runs against the production Charts/workspace code and native Python simulation.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
class Element {
  constructor(tag='div') { this.tagName=tag; this.children=[]; this.events={}; this.attributes={}; this.value=''; this.hidden=false; this.disabled=false; this.textContent=''; this.classList={toggle(){},add(){},remove(){}}; }
  append(...items){this.children.push(...items);}
  appendChild(item){this.append(item);return item;}
  replaceChildren(...items){this.children=[...items];}
  setAttribute(name,value){this.attributes[name]=value;}
  addEventListener(name,fn){this.events[name]=fn;}
  click(){if(!this.disabled)this.events.click?.({target:this});}
}
const host=new Element();
const document={getElementById:id=>id==='chart-variables'?host:null,createElement:tag=>new Element(tag),createTextNode:text=>({textContent:text}),addEventListener(){},querySelectorAll:()=>[]};
const sandbox={document,console,Simulation:{resultModel:null}};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(root,'static/js/charts.js'),'utf8')+';this.charts=Charts;',sandbox);
vm.runInContext(fs.readFileSync(path.join(root,'static/js/workspace.js'),'utf8'),sandbox);
const charts=sandbox.charts;
let renders=0;charts.render=()=>renders++;
const freeze=value=>{if(value&&typeof value==='object'){Object.freeze(value);Object.values(value).forEach(freeze);}return value;};
const buttons=()=>host.children[1].children[1].children;
const names=value=>Array.from(value);
const small=freeze({stocks:[{name:'Population',dimensions:['Region']}],dimensions:[{name:'Region',elements:['North','South']}]});
const result=freeze({time:[0,1],values:{'Population[North]':[10,11],'Population[South]':[20,22],Total:[30,33]},integration_diagnostics:{structured_source_map:{
 'structured:Population[North]':{id:'structured:Population[North]',name:'Population[North]',kind:'stock',path:'$.stocks[0]',indices:{Region:'North'}},
 'structured:Population[South]':{name:'Population[South]',kind:'stock',path:'$.stocks[0]',indices:{Region:'South'}},
 'structured:Total':{name:'Total',kind:'variable',path:'$.variables[0]',indices:{}}
}}});
const sourceBefore=JSON.stringify(small);
charts.setResults(result,small);
assert.deepEqual(names(charts.getStockSeries()),['Population[North]','Population[South]']);
assert.equal(charts.getVisibleVariables().length,3);
sandbox.updateVariableToggles();
assert.equal(buttons()[0].disabled,false);
buttons()[0].click();
assert.deepEqual(names(charts.getVisibleVariables()),['Population[North]','Population[South]']);
buttons()[1].click();assert.equal(charts.getVisibleVariables().length,3);
buttons()[2].click();assert.equal(charts.getVisibleVariables().length,0);
assert.equal(JSON.stringify(small),sourceBefore);
assert.equal(charts.resultModel,small);
charts.setVariableColor('Population[North]','#123456');
assert.equal(charts.options.variables['Population[North]'].color,'#123456');
charts.selectVariables(['Population[North]','Population[South]']);
charts.toggleVariable('Population[South]');
assert.deepEqual(names(charts.getVisibleVariables()),['Population[North]']);
assert.deepEqual(names(charts.filterSeries(Object.keys(result.values),'population north')),['Population[North]']);
// Older saved results expose path metadata without kind.
const legacy=JSON.parse(JSON.stringify(result));
Object.values(legacy.integration_diagnostics.structured_source_map).forEach(row=>delete row.kind);
assert.deepEqual(names(charts.getStockSeries(legacy,small)),['Population[North]','Population[South]']);
// Never classify an auxiliary just because its name begins with a stock name.
const misleading={values:{PopulationTotal:[1],Unknown:[2]},integration_diagnostics:{structured_source_map:{x:{name:'PopulationTotal',kind:'variable',path:'$.variables[0]'},y:{name:'not an output',kind:'stock',path:'$.stocks[0]'}}}};
assert.deepEqual(names(charts.getStockSeries(misleading,small)),[]);
// Scalar results retain stock selection and all established chart settings.
charts.options.type='phase';charts.options.scale='log';charts.options.normalize=true;charts.options.showComparison=true;
charts.setResults({time:[0,1],values:{X:[1,2],Rate:[.1,.1]}},{stocks:[{name:'X'}]});
assert.deepEqual(names(charts.getStockSeries()),['X']);
assert.equal(charts.options.type,'phase');assert.equal(charts.options.scale,'log');assert.equal(charts.options.normalize,true);assert.equal(charts.options.showComparison,true);
// Exercise a real bounded 30-cell native simulation and nested reusable modules.
const localPython=path.join(root,'.venv/bin/python');
const python=process.env.PYTHON || (fs.existsSync(localPython)?localPython:'python');
const probe=String.raw`import json
from app.core.model import Model
from app.core.simulator import simulate
array={"name":"Large array","dimensions":[{"name":"Region","elements":["R"+str(i) for i in range(30)]}],"stocks":[{"name":"Population","dimensions":["Region"],"initial_value":10}],"flows":[{"name":"Growth","dimensions":["Region"],"equation":"Population[Region] * rate","to_stock":"Population[Region]"}],"variables":[{"name":"rate","equation":"0.1"},{"name":"Total","equation":"SUM(Population[Region])"}],"time_settings":{"end":1,"dt":0.25}}
modules={"name":"Nested modules","module_definitions":{"Tank":{"inputs":[],"outputs":{"value":"Water"},"stocks":[{"name":"Water","initial_value":3}]},"Pair":{"inputs":[],"outputs":{"left":"a.value"},"modules":[{"name":"a","definition":"Tank"},{"name":"b","definition":"Tank"}]}},"modules":[{"name":"pair","definition":"Pair"}],"time_settings":{"end":1,"dt":.25}}
print(json.dumps([{"model":raw,"result":simulate(Model(**raw)).model_dump(mode="json")} for raw in (array,modules)]))
`;
const fixtures=JSON.parse(execFileSync(python,['-c',probe],{cwd:root,encoding:'utf8'}));
for(const [i,fixture] of fixtures.entries()){
  freeze(fixture);const before=JSON.stringify(fixture.model);
  charts.setResults(fixture.result,fixture.model);
  const stockNames=charts.getStockSeries();
  assert.equal(stockNames.length,i===0?30:2);
  if(i===0){assert.ok(Object.keys(fixture.result.values).length>24);assert.equal(charts.getVisibleVariables().length,30);}
  sandbox.updateVariableToggles();
  assert.equal(buttons()[0].disabled,false);buttons()[0].click();
  assert.equal(charts.getVisibleVariables().length,stockNames.length);
  buttons()[1].click();assert.equal(charts.getVisibleVariables().length,Object.keys(fixture.result.values).length);
  assert.equal(JSON.stringify(fixture.model),before);
}
assert.ok(renders>0);
console.log('Structured chart classification, stock/all/clear controls, legacy/scalar behavior, preserved settings/source, 30-cell and nested-module native simulation passed.');

