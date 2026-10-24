// Execute actual tooltip handlers with touch-shaped input and distinct chart owners.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=[];
class Selection{
 constructor(tag='root'){this.tag=tag;this.attrs={};this.styles={};this.handlers={};this.children=[];this.dom={offsetWidth:200,offsetHeight:70};nodes.push(this);}
 append(tag){const child=new Selection(tag);this.children.push(child);return child;}
 attr(k,v){this.attrs[k]=v;return this;}
 style(k,v){this.styles[k]=v;return this;}
 select(){return this;}
 selectAll(){return this;}
 empty(){return false;}
 node(){return this.dom;}
 html(value){this.htmlValue=value;return this;}
 on(type,fn,options){this.handlers[type]={fn,options};return this;}
}
let expectedOverlay;
const tooltip=new Selection('tooltip');
const owner={scrollLeft:0,scrollTop:0,getBoundingClientRect:()=>({left:100,top:200,width:320,height:250})};
const box={console,setTimeout:()=>1,clearTimeout(){},App:{escapeHtml:s=>s},d3:{schemeCategory10:[],select:n=>{assert.equal(n,owner);return tooltip;},bisector:()=>({left:(arr,x)=>{const i=arr.findIndex(v=>v>=x);return i<0?arr.length:i;}}),pointer:(event,node)=>{assert.equal(node,expectedOverlay);return [event.clientX-110,event.clientY-210];}}};
vm.createContext(box);vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/js/charts.js'),'utf8')+';this.charts=Charts;',box);
const charts=box.charts;charts.container=owner;charts.options.showTooltip=true;charts.options.variables={Population:{visible:true,color:'#fff'}};
const group=new Selection();const scale=x=>x;scale.invert=x=>x;
charts.addTooltip(null,group,scale,scale,{innerWidth:300,innerHeight:180},[0,10,20],{Population:[1,2,3]});
const overlay=group.children.find(n=>n.attrs.class==='overlay');expectedOverlay=overlay.dom;
charts.container={getBoundingClientRect(){throw Error('Wrong chart container');}};
const read=(type,x)=>overlay.handlers[type].fn({touches:[{clientX:110+x,clientY:240}],preventDefault(){throw Error('Must allow page scrolling');}});
read('touchstart',1);assert.match(tooltip.htmlValue,/t = 0.00/);
read('touchmove',8);assert.match(tooltip.htmlValue,/t = 10.00/);
read('touchmove',15);assert.match(tooltip.htmlValue,/t = 10.00/,'Ties choose the earlier sample');
read('touchmove',100);assert.match(tooltip.htmlValue,/t = 20.00/);
read('touchmove',-100);assert.match(tooltip.htmlValue,/t = 0.00/);
for(const value of [tooltip.styles.left,tooltip.styles.top])assert.match(value,/^\d+(\.\d+)?px$/);
assert.equal(overlay.handlers.touchstart.options.passive,true);assert.equal(overlay.handlers.touchmove.options.passive,true);
overlay.handlers.touchcancel.fn();assert.equal(tooltip.styles.opacity,0);
overlay.handlers.mousemove.fn({clientX:118,clientY:240});assert.match(tooltip.htmlValue,/t = 10.00/);
console.log('Chart touch coordinates stay finite in their rendered owner, mouse/touch select the nearest sample, and touch reading permits vertical scrolling.');
