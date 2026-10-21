// Run the actual chat, panel lifecycle and library methods without network calls.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const fields={};
function element(){return {children:[],value:'',classList:{add(){},remove(){},toggle(){}},appendChild(n){this.children.push(n);},cloneNode(){return {...this,children:[...this.children]};},focus(){doc.activeElement=this;},addEventListener(){}};}
const doc={activeElement:null,body:element(),getElementById:id=>fields[id]||null,querySelector:()=>null,querySelectorAll:()=>[],createElement:element,addEventListener(){}};
for(const id of ['chat-input-mobile','chat-messages-mobile','chat-messages-desktop','slide-panel','slide-panel-content','slide-panel-title','overlay','library-modal','library-search'])fields[id]=element();
const box={document:doc,console,setTimeout:fn=>fn(),OpenRouterUI:{request:()=>{throw Error('Unexpected request');}}};
vm.createContext(box);
for(const [file,name] of [['app','App'],['llm-interface','LLMInterface'],['library','Library']])vm.runInContext(fs.readFileSync(path.join(__dirname,`../static/js/${file}.js`),'utf8')+`;this.${name}=${name};`,box);
const app=box.App,llm=box.LLMInterface,library=box.Library;
llm.chatMessages=fields['chat-messages-desktop'];
(async()=>{
 fields['chat-input-mobile'].value='A draft </textarea><script>bad()</script>';
 app.openSlidePanel('properties');
 assert.equal(app.mobileChatDraft,fields['chat-input-mobile'].value);
 delete fields['chat-input-mobile'];app.openSlidePanel('chat');
 assert.ok(fields['slide-panel-content'].innerHTML.includes('A draft &lt;/textarea&gt;'));
 assert.ok(!fields['slide-panel-content'].innerHTML.includes('<script>bad()'));
 fields['chat-input-mobile']=element();fields['chat-input-mobile'].value='preserved on close';
 app.closeSlidePanel();assert.equal(app.mobileChatDraft,'preserved on close');
 fields['chat-input-mobile'].value='Build a model';
 await llm.sendFromMobile();
 assert.equal(llm.chatMessages.children.length,2);
 assert.equal(fields['chat-messages-mobile'].children.length,2,'Both user and unavailable error must be visible immediately');
 assert.equal(app.mobileChatDraft,'');
 llm.addMessageToBoth('reply','assistant');assert.equal(fields['chat-messages-mobile'].children.length,3,'Compatibility helper must not duplicate messages');
 let finish;library.loadModels=()=>new Promise(resolve=>finish=resolve);library.applyFilters=()=>{};
 const opener=element();doc.activeElement=opener;
 const opening=library.open();assert.equal(doc.activeElement,fields['library-search']);
 library.close();assert.equal(doc.activeElement,opener);finish();await opening;
 assert.equal(doc.activeElement,opener,'Slow library response must not focus a closed modal');
 console.log('Mobile draft survives tab/close, escaped draft remains text, visible chat stays synchronized, and library focus survives slow close.');
})().catch(error=>{console.error(error);process.exitCode=1;});
