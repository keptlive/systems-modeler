const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
let personal=true, calls=[], rendered, errors=[];
const model={id:'draft',stocks:[],flows:[],variables:[]};
const context={OpenRouterUI:{hasKey:()=>personal,request:async(url,options)=>{calls.push({url,body:JSON.parse(options.body)});return {ok:true,json:async()=> personal?model:{success:true,suggestions:[],explanation:'server'}};}},console};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/js/ai-agent.js'),'utf8')+';this.agent=AIAgent;',context);
const agent=context.agent;agent.model=model;agent.results={time:[0,1],stocks:{}};agent.showFeedbackLoading=()=>{};agent.showFeedbackMessage=m=>errors.push(m);agent.renderRefinementResult=r=>rendered=r;
(async()=>{
 await agent.refineModel('slow the growth');assert.equal(calls.at(-1).url,'/api/llm/modify');assert.match(calls.at(-1).body.modification,/slow the growth/);assert.match(calls.at(-1).body.modification,/Simulation results/);assert.equal(rendered.modified_model,model);
 personal=false;await agent.refineModel('slow the growth');assert.equal(calls.at(-1).url,'/api/llm/refine-model');assert.equal(calls.at(-1).body.feedback,'slow the growth');assert.equal(rendered.explanation,'server');
 personal=true;context.OpenRouterUI.request=async()=>({ok:false,json:async()=>({detail:'Rate limited'})});assert.equal(await agent.refineModel('try again'),null);assert.match(errors.at(-1),/Rate limited/);
 console.log('OpenRouter refinement: personal key uses modification and existing review/apply UI; server flow retained; failures explicit.');
})().catch(e=>{console.error(e);process.exitCode=1;});
