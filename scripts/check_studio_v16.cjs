// Execute real mobile sheet code against deterministic DOM/observer controls.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const listeners={},attributes={},classes=new Set(),body={style:{overflow:''}};
let callback,removals=0,button;
const sheet={classList:{contains:x=>classes.has(x),toggle(x){classes.has(x)?classes.delete(x):classes.add(x);return classes.has(x);},remove(x){removals++;classes.delete(x);}}};
const close={addEventListener(type,fn){listeners['close:'+type]=fn;}},overlay={addEventListener(type,fn){listeners['overlay:'+type]=fn;}};
const header={insertBefore(node){button=node;}};
const box={document:{body,getElementById(id){return {'slide-panel':sheet,'slide-panel-close':close,overlay}[id]||null;},querySelector(){return header;},createElement(){return {setAttribute(k,v){attributes[k]=v;},addEventListener(type,fn){listeners['button:'+type]=fn;}};}},MutationObserver:class{constructor(fn){callback=fn;}observe(){}}};
vm.createContext(box);vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/js/mobile-expand.js'),'utf8'),box);
assert.equal(attributes['aria-pressed'],'false');
classes.add('open');listeners['button:click']();assert(classes.has('fullscreen'));assert.equal(body.style.overflow,'hidden');assert.equal(attributes['aria-pressed'],'true');
classes.delete('open');callback();assert(!classes.has('fullscreen'));assert.equal(body.style.overflow,'');assert.equal(attributes['aria-pressed'],'false');
const previous=removals;callback();assert.equal(removals,previous,'Observer does not repeatedly mutate an already closed sheet');
classes.add('open');listeners['button:click']();listeners['close:click']();assert.equal(attributes['aria-pressed'],'false');
listeners['button:click']();listeners['overlay:click']();assert(!classes.has('fullscreen'));assert.equal(body.style.overflow,'');
console.log('Mobile fullscreen button, close/overlay and programmatic/Escape exit state passed.');
