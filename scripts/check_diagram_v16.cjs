// Independent geometry expectations; no browser or model mutation required.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const sandbox={};vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/js/canvas.js'),'utf8')+';this.canvas=Canvas;',sandbox);
const c=sandbox.canvas,element=(id,name,x,y)=>({id,name,position:{x,y}});
const stock=element('s','Drug in Central Compartment',0,0),variable=element('v','Critical Vaccination Threshold',200,100),flow=element('f','Systemic absorption',100,0);
assert.deepEqual(Array.from(c.wrapLabel('Total Population',15,3)),['Total','Population']);
assert(!c.wrapLabel(variable.name,15,3).join(' ').includes('…'));
assert(c.wrapLabel('Very '.repeat(40),15,3).at(-1).endsWith('…'));
const edge=c.boundaryPoint('stock',stock,{x:100,y:0});assert(Math.abs(edge.x-59)<1e-6);assert.equal(edge.y,0);
const left=c.boundaryPoint('stock',stock,{x:-100,y:0});assert(Math.abs(left.x+59)<1e-6);
const cap=c.boundaryPoint('variable',variable,{x:300,y:100});assert(Math.abs(cap.x-258)<1e-6);
assert(c.isPointInStock(58,0,stock));assert(!c.isPointInStock(70,0,stock));
assert(c.isPointInVariable(253,100,variable));assert(!c.isPointInVariable(270,100,variable));
assert(c.isPointInFlow(100,35,flow));assert(!c.isPointInFlow(100,85,flow));
const source={type:'stock',element:stock},target={type:'variable',element:variable};
for(const pair of [[source,target],[source,source],[source,{type:'variable',element:element('same','Different element',0,0)}]]){
 const geometry=c.connectorGeometry(...pair);assert(!/NaN|Infinity/.test(geometry.path));
 assert(geometry.points.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)));
}
const fixture={stocks:[stock],flows:[flow],variables:[variable],connectors:[{id:'link',from_element:'s',to_element:'v'},{id:'self',from_element:'s',to_element:'s'}]};
sandbox.App={model:fixture,findElement(id){return [source,target,{type:'flow',element:flow}].find(x=>x.element.id===id);}};
const before=JSON.stringify(fixture),bounds=c.modelBounds();assert(bounds.minX<=-56&&bounds.maxX>=255);assert(bounds.minY<-60);
assert.equal(JSON.stringify(fixture),before);
c.width=700;c.height=500;c.updateDimensions=()=>{};c.updateTransform=()=>{};c.fitToModel();
assert(bounds.minX*c.scale+c.translateX>=19);assert(bounds.maxX*c.scale+c.translateX<=681);
assert(bounds.minY*c.scale+c.translateY>=69);assert(bounds.maxY*c.scale+c.translateY<=451);
let lines=0;const layer={append(){lines++;return {attr(){return this;}};}};
c.drawFlowLine(layer,source,target);assert.equal(lines,1);c.drawFlowLine(layer,source,source);assert.equal(lines,1);
const anderson=JSON.parse(fs.readFileSync(path.join(__dirname,'../models/epidemiology/anderson-may-herd-immunity-epi.json'),'utf8'));
for(const v of anderson.variables)assert(!c.wrapLabel(v.name,15,3).join(' ').includes('…'),v.name);
assert.equal(JSON.stringify(fixture),before);
console.log('Diagram clipping, self/coincident links, fit bounds, wrapping, hit zones and position preservation passed.');
c.drawFlowLine(layer,source,{type:'flow',element:element('close','Close',20,0)});assert.equal(lines,1,'Overlapping shapes must not create a reversed material arrow');
