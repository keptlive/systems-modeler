// Execute actual editor methods; no browser or stored corpus mutations.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../static/js/app.js'),'utf8');
const handlers={},fields={},errors=[];
const field=id=>fields[id]||(fields[id]={value:'',addEventListener(type,handler){handlers[id+':'+type]=handler;},setCustomValidity(value){this.validityMessage=value;}});
const box={document:{addEventListener(){},getElementById:field},alert:message=>errors.push(message),Canvas:{render(){}},Simulation:{invalidateIfChanged(){box.invalidations++;}},invalidations:0};
vm.createContext(box);vm.runInContext(source+';this.app=App;',box);const app=box.app;
app.showToast=message=>errors.push(message);
function model(){
 return {id:'rename-test',name:'Synthetic',description:'Population provenance stays unchanged',
 stocks:[{id:'s',name:'Population',initial_value:100,equation:''}],
 variables:[{id:'v',name:'Population Growth',equation:'.1'}],
 flows:[{id:'f',name:'Births',equation:'Population*Population_Growth',from_stock:null,to_stock:'Population'},
        {id:'g',name:'Unused',equation:'0',from_stock:'s',to_stock:null}],
 connectors:[{id:'c',from_element:'Population',to_element:'Births'},{id:'d',from_element:'s',to_element:'f'}],
 tables:[],time_settings:{start:0,end:2,dt:.25}};
}
function use(m=model(),type='stock',id='s'){app.model=m;app.selected={type,id};}
use();const before=JSON.parse(JSON.stringify(app.model));
assert.equal(app.updateProperty('name','People Served'),true);
const after=JSON.parse(JSON.stringify(app.model));
assert.equal(after.stocks[0].id,'s');assert.equal(after.stocks[0].name,'People Served');
assert.equal(after.flows[0].equation,'"People Served"*Population_Growth');
assert.equal(after.flows[0].to_stock,'People Served');
assert.equal(after.flows[1].from_stock,'s');
assert.equal(after.connectors[0].from_element,'People Served');assert.equal(after.connectors[1].from_element,'s');
assert.equal(after.description,before.description);
const rename=app.renameEquationReferences.bind(app);
assert.equal(rename('Population_Growth+population+"POPULATION" { Population }','Population','New Name'),
 'Population_Growth+"New Name"+"New Name" { Population }');
assert.equal(rename('SIN(PI/2)+SIN+1e3 {SIN}','SIN','Angle'),
 'SIN(PI/2)+"Angle"+1e3 {SIN}');
assert.equal(rename('IF THEN ELSE(Population>0, Population, 0)','Population','People'),
 'IF THEN ELSE("People">0, "People", 0)');
assert.equal(rename('LOOKUP(Population,Population)+Population(2)', 'Population','People',['Population']),
 'LOOKUP(Population,"People")+Population(2)');
assert.equal(rename("LOOKUP('Population',Population)",'Population','People',['Population']),
 "LOOKUP('Population',\"People\")");
assert.equal(rename('"Flow \\"A\\"" + x','Flow "A"','New "B"'),
 '"New \\"B\\"" + x');
assert.equal(rename('Rate+RATE+1','Rate','R & D'),'"R & D"+"R & D"+1');
assert.equal(rename('")" + 1',')','Right'),'"Right" + 1');
assert.equal(app.identifierKey('Straße'),app.identifierKey('STRASSE'));
assert.equal(app.identifierKey('Total__Population'),app.identifierKey('total population'));
assert.equal(app.identifierKey('é'),app.identifierKey('e\u0301'));
// Imported literal names remain separate throughout an editor rename.
for (const literal of ['A-B','A\u2002B']) {
 use({stocks:[],flows:[],tables:[],connectors:[],variables:[
  {id:'literal',name:literal,equation:'1'},
  {id:'underscore',name:'A_B',equation:'2'},
  {id:'out',name:'Output',equation:JSON.stringify(literal)+'+A_B'}]},'variable','literal');
 assert.equal(app.updateProperty('name','Renamed'),true);
 assert.equal(app.model.variables[2].equation,'"Renamed"+A_B');
 assert.equal(app.model.variables[1].name,'A_B');
}
assert.equal(rename('Cash$Balance+1','Cash$Balance','Cash Total'),'"Cash Total"+1');
assert.equal(rename('Wall_R_Value+1','Wall R-Value','Insulation'),'"Insulation"+1');
assert.throws(()=>rename('A__B','A-B','New',[],['A-B','A.B']),/Ambiguous/);
assert.equal(rename('A_B+"A-B"','A-B','New',[],['A-B','A_B']),'A_B+"New"');
// A rename cannot steal a reference that previously used another name's
// unique legacy alias, or turn an unknown symbol into a different binding.
for (const [existing,reference,renamed] of [
 ['A-B','A_B','A_B'], ['A_B','"A-B"','A-B'],
 ['A.B','A__B','A-B'], ['Existing','Missing','Missing']
]) {
 use({stocks:[],flows:[],tables:[],connectors:[],variables:[
  {id:'x',name:'X',equation:'1'}, {id:'other',name:existing,equation:'2'},
  {id:'out',name:'Output',equation:reference+'+X'}]},'variable','x');
 const original=JSON.stringify(app.model);
 assert.equal(app.updateProperty('name',renamed),false);
 assert.equal(JSON.stringify(app.model),original);
}
// Real table arguments/functions stay in their own namespace even when a
// variable would match their spelling through a legacy alias.
use({stocks:[],flows:[],connectors:[],tables:[{name:'A-B',points:[[0,0],[1,1]]}],variables:[
 {id:'x',name:'A_B',equation:'1'},
 {id:'out',name:'Output',equation:'LOOKUP("A-B",A_B)+"A-B"(A_B)'}]},'variable','x');
assert.equal(app.updateProperty('name','Renamed'),true);
assert.equal(app.model.variables[1].equation,'LOOKUP("A-B","Renamed")+"A-B"("Renamed")');
for(const name of ['', '  ', 'TIME','dt','Population Growth']){
 use();const original=JSON.stringify(app.model);
 assert.equal(app.updateProperty('name',name),false);
 assert.equal(JSON.stringify(app.model),original);
}
for(const equation of ['Population[0]','Population(2)','LOOKUP(Population,2)','Population + (2','Population.attr','"unfinished']){
 use();app.model.variables[0].equation=equation;const original=JSON.stringify(app.model);
 assert.equal(app.updateProperty('name','People'),false);
 assert.equal(JSON.stringify(app.model),original);
}
use();assert.equal(app.updateProperty('name','v'),false);
use();app.model.tables=[{name:'People',points:[[0,0],[1,1]]}];
assert.equal(app.updateProperty('name','People'),false);
use();app.model.variables.push({id:'v2',name:'STRASSE',equation:'1'});
assert.equal(app.updateProperty('name','Straße'),false);
use();const ids=app.model.stocks.map(x=>x.id).concat(app.model.flows.map(x=>x.id),app.model.variables.map(x=>x.id));
assert.equal(app.updateProperty('name','Population'),true);
assert.deepEqual(app.model.stocks.map(x=>x.id).concat(app.model.flows.map(x=>x.id),app.model.variables.map(x=>x.id)),ids);

// Bind the real desktop and mobile listeners: drafts do not commit names.
app.updatePropertiesPanel();app.initMobilePropertyEvents();
assert.equal(handlers['prop-name:input'],undefined);
assert.equal(handlers['prop-name-mobile:input'],undefined);
assert.equal(typeof handlers['prop-name:change'],'function');
assert.equal(typeof handlers['prop-name-mobile:change'],'function');
for(const id of ['prop-initial','prop-initial-mobile']){
 const input=field(id);input.value='';input.valueAsNumber=NaN;
 handlers[id+':input']({target:input});
 assert.equal(app.model.stocks[0].initial_value,100);
 handlers[id+':change']({target:input});
 assert.equal(input.value,100);assert.equal(input.validityMessage,'');
 input.value='-2.75';input.valueAsNumber=-2.75;
 handlers[id+':input']({target:input});
 assert.equal(app.model.stocks[0].initial_value,-2.75);
 input.value='1abc';input.valueAsNumber=NaN;
 handlers[id+':change']({target:input});
 assert.equal(app.model.stocks[0].initial_value,-2.75);
 assert.equal(input.value,-2.75);
 app.model.stocks[0].initial_value=100;
}
const initial=JSON.stringify(app.model);
assert.equal(app.updateProperty('initial_value',NaN),false);
assert.equal(app.updateProperty('initial_value',Infinity),false);
assert.equal(JSON.stringify(app.model),initial);

// Rendered template preserves every control, showing the chart before filters.
box.Charts={results:{values:{Population:[100,110]},random_seed:null},options:{variables:{Population:{visible:true,color:'#123456'}},type:'line',normalize:true,scale:'linear'},colors:['#123456']};
const html=app.getResultsPanelContent();
assert(html.indexOf('chart-wrapper-mobile')<html.indexOf('Chart Options'));
assert(html.indexOf('Chart Options')<html.indexOf('series-search-mobile'));
for(const hook of ['chart-container-mobile','var-chips-mobile','results-summary-mobile','btn-normalize-mobile','btn-log-mobile','results-tabs-mobile','data-tab="chart-mobile"','data-tab="analytics-mobile"','data-tab="ai-mobile"'])assert(html.includes(hook),hook);
assert(!/>[📊📈🤖]/u.test(html));
if(process.argv.includes('--json'))console.log(JSON.stringify({before,after}));
else console.log('Property transactions, token references, collisions/rollback, both numeric inputs and mobile chart/control preservation passed.');
