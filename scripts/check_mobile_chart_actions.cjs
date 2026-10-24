// Actual mobile result actions, chart owner lifecycle, phase selection and CSV escaping.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const fields={};
function field(id){return fields[id]||(fields[id]={id,value:'',isConnected:true,handlers:{},textContent:'',classList:{toggle(){}},setAttribute(k,v){this[k]=v;},addEventListener(k,fn){this.handlers[k]=fn;}});}
for(const id of ['mobile-save-run','mobile-compare','mobile-animate','mobile-run-status','mobile-export-chart','mobile-export-format','mobile-phase-x','mobile-phase-y','chart-container-mobile'])field(id);
let blob,clicked=false;
const box={console,Blob,document:{getElementById:id=>fields[id]||null,querySelectorAll:()=>[],addEventListener(){},createElement:()=>({click(){clicked=true;}})},d3:{schemeCategory10:[]},URL:{createObjectURL:value=>{blob=value;return 'blob:test';},revokeObjectURL(){}},setTimeout(){},requestAnimationFrame:()=>1,cancelAnimationFrame(){}};
vm.createContext(box);
for(const [file,name] of [['charts','Charts'],['app','App']])vm.runInContext(fs.readFileSync(path.join(__dirname,`../static/js/${file}.js`),'utf8')+`;this.${name}=${name};`,box);
const c=box.Charts,a=box.App;
c.results={time:[0,1],values:{'A,"quoted"':[1,2],B:[3,4]}};c.options.variables={'A,"quoted"':{visible:true,color:'#fff'},B:{visible:true,color:'#000'}};
box.Simulation={resultModel:{stocks:[]}};
a.updateMobileResultsSummary=()=>{};let rendered=0;a.renderMobileChart=()=>rendered++;
const desktop={id:'desktop'},mobile=fields['chart-container-mobile'];c.container=desktop;
a.initMobileResultsEvents();
fields['mobile-save-run'].handlers.click();assert.equal(c.previousRuns.length,1);assert.match(fields['mobile-run-status'].textContent,/1 saved run/);
fields['mobile-compare'].handlers.click();assert.equal(c.options.showComparison,true);assert.equal(rendered,1);
const exportAs=c.exportAs;c.exportAs=function(format){assert.equal(this.container,mobile);assert.equal(format,'svg');};fields['mobile-export-format'].value='svg';fields['mobile-export-chart'].handlers.click();assert.equal(c.container,desktop);c.exportAs=exportAs;
fields['mobile-phase-x'].value='B';fields['mobile-phase-x'].handlers.change();assert.equal(c.options.type,'phase');
assert.deepEqual(Array.from(c.getPhaseVariables()),['B','A,"quoted"']);
c.options.phaseY='B';assert.deepEqual(Array.from(c.getPhaseVariables()),['B','A,"quoted"'],'Duplicate axes fall back to a distinct visible series');
c.options.animationSpeed=.01;let frames=0;c.renderAnimatedFrame=function(){assert.equal(this.container,mobile);frames++;};
fields['mobile-animate'].handlers.click();assert.equal(c.container,desktop);assert.equal(c.animationContainer,mobile);assert.equal(frames,1);
c.animateFrame();assert.equal(c.container,desktop);assert.equal(frames,2);
mobile.isConnected=false;c.animateFrame();assert.equal(c.isAnimating,false);assert.equal(c.container,desktop);
// A mobile phase/scale choice must update the desktop controls before resizing.
const modes = ['line','phase'].map(chartType => ({dataset:{chartType},classList:{toggle(key,value){this.active=value;}},setAttribute(){}}));
const scales = ['linear','log'].map(scale => ({dataset:{scale},classList:{toggle(key,value){this.active=value;}},setAttribute(){}}));
box.document.querySelectorAll = selector => selector === '[data-chart-type]' ? modes : selector === '[data-scale]' ? scales : [];
const normalization = field('btn-normalize');normalization.classList.toggle = (key,value)=>normalization.active=value;
c.options.type='phase';c.options.scale='log';c.options.normalize=true;
const results=c.results;c.results=null;c.render();c.results=results;
assert.equal(modes[0].classList.active,false);assert.equal(modes[1].classList.active,true);
assert.equal(scales[0].classList.active,false);assert.equal(scales[1].classList.active,true);assert.equal(normalization.active,true);

(async()=>{c.exportAs('csv');assert.ok(clicked);assert.match(await blob.text(),/"Time","A,""quoted""","B"\r\n"0","1","3"/);const html=a.getResultsPanelContent();for(const id of ['mobile-save-run','mobile-compare','mobile-animate','mobile-export-chart','mobile-phase-x','mobile-phase-y'])assert.ok(html.includes(`id="${id}"`));console.log('Mobile chart save/compare/export/animation actions preserve owner and status; distinct phase axes and escaped CSV work.');})().catch(e=>{console.error(e);process.exitCode=1;});
