const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
let active, mutation, resize, media, chart=0, frames=[], cancelled=[], nativeDialogOpen=false;
class Element {
 constructor(id=''){this.id=id;this.handlers={};this.children=[];this.attrs={};this.open=false;this.isConnected=true;this.disabled=false;this.classes=new Set();this.classList={contains:x=>this.classes.has(x)};}
 append(el){if(el.parent)el.parent.children=el.parent.children.filter(x=>x!==el);this.children.push(el);el.parent=this;}
 before(el){this.parent.append(el);}
 after(el){this.parent.append(el);}
 setAttribute(k,v){this.attrs[k]=v;}
 addEventListener(type,fn,capture=false){(this.handlers[type]||=[]).push({fn,capture});}
 emit(type,event={}){for(const h of this.handlers[type]||[])h.fn(event);}
 focus(){active=this;}
 showModal(){this.open=true;}
 close(){this.open=false;this.emit('close');}
 getClientRects(){return this.hidden?[]:[{}];}
 querySelector(sel){return this.queries?.[sel]||null;}
 querySelectorAll(){return this.focusables||[];}
 getBoundingClientRect(){return {left:0,right:100,top:0,bottom:100};}
}
const header=new Element('header'),actions=new Element('actions'),originalButton=new Element('original'),panel=new Element('slide-panel'),panelClose=new Element('slide-panel-close'),panelLast=new Element('panel-last'),disabled=new Element('disabled'),hidden=new Element('hidden'),tab=new Element('tab-chart-mobile'),leftHeader=new Element('left-header');
header.append(actions);actions.append(originalButton);disabled.disabled=true;hidden.hidden=true;panel.focusables=[panelClose,disabled,hidden,panelLast];
let originalCalls=0;originalButton.addEventListener('click',()=>{assert.equal(menu.open,false,'menu closes before original button handler');originalCalls++;});
let menu,quick;
const ids={'slide-panel':panel,'slide-panel-close':panelClose,'tab-chart-mobile':tab,'btn-inspect-model':new Element('inspect')};
const document={get activeElement(){return active;},body:new Element('body'),querySelector(sel){return {'.header':header,'.header-icons':actions,'.panel-left .panel-header':leftHeader}[sel]||(sel==='dialog[open]'&&nativeDialogOpen?new Element():null);},getElementById:id=>ids[id],createComment:()=>new Element('home'),createElement(tag){const el=new Element();if(tag==='div'){quick=el;el.queries={'#mobile-menu':new Element('trigger'),'#mobile-library':new Element('library')};}if(tag==='dialog'){menu=el;el.queries={'.mobile-menu-close':new Element('close'),'.mobile-actions-body':new Element('body'),'[data-mobile-inspect]':new Element('inspect-action')};}return el;}};
const context={document,window:{matchMedia(query){assert.equal(query,'(max-width: 899px)');media={matches:true,addEventListener(type,fn){this.change=fn;}};return media;}},Library:{open(){}},App:{activePanel:'results',renderMobileChart(){chart++;}},MutationObserver:class{constructor(fn){mutation=fn;}observe(){}},ResizeObserver:class{constructor(fn){resize=fn;}observe(el){assert.equal(el,panel);}},requestAnimationFrame(fn){frames.push(fn);return frames.length;},cancelAnimationFrame(id){cancelled.push(id);}};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/js/mobile-shell.js'),'utf8'),context);
assert.equal(actions.parent,menu.queries['.mobile-actions-body']);assert.equal(actions.children[0],originalButton);
quick.queries['#mobile-menu'].emit('click');assert.equal(menu.open,true);
const event={target:{closest:()=>originalButton}};
for(const h of menu.handlers.click.filter(x=>x.capture))h.fn(event);originalButton.emit('click');assert.equal(originalCalls,1);assert.equal(active,quick.queries['#mobile-menu']);
media.matches=false;media.change();assert.equal(actions.parent,header);assert.equal(actions.children[0],originalButton);media.matches=true;media.change();assert.equal(actions.parent,menu.queries['.mobile-actions-body']);assert.equal(originalButton.handlers.click.length,1);
const opener=new Element('opener');opener.focus();panel.classes.add('open');mutation();assert.equal(active,panelClose);
let prevented=false;panelLast.focus();panel.emit('keydown',{key:'Tab',shiftKey:false,preventDefault(){prevented=true;}});assert.equal(active,panelClose);assert.equal(prevented,true);
prevented=false;panel.emit('keydown',{key:'Tab',shiftKey:true,preventDefault(){prevented=true;}});assert.equal(active,panelLast);assert.equal(prevented,true);
nativeDialogOpen=true;panelLast.focus();panel.emit('keydown',{key:'Tab',shiftKey:false,preventDefault(){throw Error('nested dialog must own focus');}});assert.equal(active,panelLast);nativeDialogOpen=false;
panel.classes.delete('open');mutation();assert.equal(active,opener);
resize();tab.classes.add('active');frames.pop()();assert.equal(chart,1,'checks current chart state at animation time');
resize();context.App.activePanel='ai';frames.pop()();assert.equal(chart,1);
context.App.activePanel='results';resize();tab.classes.delete('active');frames.pop()();assert.equal(chart,1);
resize();resize();assert.ok(cancelled.at(-1)>0);
console.log('Mobile shell mocked behavior: same controls/listeners at breakpoint, capture close ordering, panel focus trap/restore, nested dialog exception, current chart resize state.');
