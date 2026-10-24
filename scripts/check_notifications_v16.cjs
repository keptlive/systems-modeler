// Real notification method: modal ownership, persistence and focus restoration.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const timers=[];let nativeOpen=true,settingsOpen=true,doc;
class Node {
 constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.attributes={};this.handlers={};this.isConnected=true;}
 append(...nodes){for(const node of nodes){node.parent=this;this.children.push(node);}}
 setAttribute(k,v){this.attributes[k]=v;}addEventListener(k,fn){this.handlers[k]=fn;}
 contains(node){return this===node||this.children.some(child=>child.contains(node));}
 remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);this.isConnected=false;}
 focus(){doc.activeElement=this;}
 querySelector(){return this.children.find(x=>x.tag==='input'||x.tag==='button')||null;}
}
const body=new Node('body'),settings=new Node('settings'),dialog=new Node('dialog');body.append(settings,dialog);
const settingsField=new Node('input'),nativeField=new Node('input');settings.append(settingsField);dialog.append(nativeField);
const findNotice=node=>node.className==='studio-toast'?node:node.children.map(findNotice).find(Boolean);
doc={body,activeElement:nativeField,addEventListener(){},createElement:tag=>new Node(tag),querySelector(selector){
 if(selector==='.studio-toast')return findNotice(body);
 // The combined-selector behavior reproduces document-order selection.
 if(selector.includes(',')&&settingsOpen)return settings;
 if(selector==='dialog[open]')return nativeOpen?dialog:null;
 if(selector==='.modal-overlay.active .modal')return settingsOpen?settings:null;
 return null;
}};
const box={document:doc,setTimeout:(fn,delay)=>timers.push({fn,delay})};vm.createContext(box);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/js/app.js'),'utf8')+';this.app=App;',box);
box.app.showToast('<img src=x>','error');let notice=findNotice(body);
assert.equal(notice.parent,dialog,'Native top-layer dialog wins over earlier settings DOM');assert.equal(notice.attributes.role,'alert');assert.equal(notice.children[0].textContent,'<img src=x>');assert.equal(timers.length,0);
notice.children[1].focus();notice.children[1].handlers.click();assert.equal(doc.activeElement,nativeField);
nativeOpen=false;settingsField.focus();box.app.showToast('Saved','success');notice=findNotice(body);assert.equal(notice.parent,settings);assert.equal(notice.attributes.role,'status');assert.equal(timers[0].delay,6000);
notice.children[1].focus();timers[0].fn();assert.equal(doc.activeElement,settingsField);
settingsField.focus();box.app.showToast('Problem','error');notice=findNotice(body);settingsField.remove();const fallbackField=new Node('input');settings.append(fallbackField);notice.children[1].focus();notice.children[1].handlers.click();assert.equal(doc.activeElement,fallbackField,'Fallback uses first surviving owner field');
settingsOpen=false;body.focus();box.app.showToast('Ready');assert.equal(findNotice(body).parent,body);
console.log('Notification modal priority, safe text, roles, persistence, expiry and focused dismissal passed.');
