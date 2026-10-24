/** A private, revision-checked connection from the user's MCP agent to this page. */
const AgentWorkspace={
    key:null,revision:0,modelRevision:0,resultRevision:0,lastSignature:'',busy:false,conflict:false,fit:0,
    init(){
        const button=document.createElement('button');button.className='btn agent-connect';button.textContent='Connect agent';
        button.addEventListener('click',()=>this.showConnection());
        document.querySelector('.header-icons').prepend(button);
        this.banner=document.createElement('div');this.banner.className='agent-session-status';this.banner.hidden=true;
        this.message=document.createElement('span');this.banner.appendChild(this.message);
        const stop=document.createElement('button');stop.textContent='Disconnect';stop.addEventListener('click',()=>this.disconnect());this.banner.appendChild(stop);
        document.getElementById('canvas-container').appendChild(this.banner);
        const invite=document.createElement('div');invite.className='chat-message assistant';
        invite.textContent='Bring your own agent: connect through MCP to build, inspect and run a model on this page. Server-side AI drafting remains optional.';
        document.getElementById('chat-messages-desktop').prepend(invite);
        const fragment=new URLSearchParams(location.hash.slice(1)).get('workspace');
        if(fragment){history.replaceState(null,'',location.pathname+location.search);this.connect(fragment);}
        else if(sessionStorage.getItem('systems-workspace'))this.connect(sessionStorage.getItem('systems-workspace'));
        window.addEventListener('hashchange',()=>{
            const next=new URLSearchParams(location.hash.slice(1)).get('workspace');
            if(next){history.replaceState(null,'',location.pathname+location.search);this.connect(next);}
        });
    },
    status(text){this.banner.hidden=false;this.message.textContent=text;},
    async request(suffix='',options={}){
        const response=await fetch('/api/workspaces/'+this.key.split('.')[0]+suffix,{
            ...options,headers:{'Content-Type':'application/json','Authorization':'Bearer '+this.key},cache:'no-store'});
        if(!response.ok){const error=new Error(response.status===404?'Session ended or expired':'Workspace request failed');error.status=response.status;throw error;}
        return response.json();
    },
    async connect(key){
        const generation=this.generation=(this.generation||0)+1;
        clearTimeout(this.timer);
        while(this.busy)await new Promise(resolve=>setTimeout(resolve,25));
        if(generation!==this.generation)return;
        clearTimeout(this.timer);this.busy=true;
        this.key=key;this.revision=0;this.modelRevision=0;this.resultRevision=0;this.conflict=false;this.fit=0;
        sessionStorage.setItem('systems-workspace',key);this.status('Connecting agent workspace…');
        try{await this.apply(await this.request());await this.ack();}
        catch(error){this.status(error.message+' — page draft kept');this.key=null;sessionStorage.removeItem('systems-workspace');}
        finally{this.busy=false;this.schedule();}
    },
    schedule(){clearTimeout(this.timer);if(this.key)this.timer=setTimeout(()=>this.tick(),document.hidden?5000:1000);},
    async tick(){
        if(!this.key||this.busy)return;
        this.busy=true;
        try{
            if(this.conflict)return;
            if(document.activeElement?.matches('input:not([readonly]),textarea:not([readonly]),select')){
                this.status('Agent connected · waiting for page editing to finish');await this.ack('Waiting for page editing to finish');return;
            }
            const signature=JSON.stringify(App.modelSnapshot());
            if(signature!==this.lastSignature){
                let state;
                try{state=await this.request('/model',{method:'PUT',body:JSON.stringify({model:App.modelSnapshot(),expected_revision:this.revision})});}
                catch(error){
                    if(error.status!==409)throw error;
                    const latest=await this.request();
                    if(latest.model_revision!==this.modelRevision)throw error;
                    state=await this.request('/model',{method:'PUT',body:JSON.stringify({model:App.modelSnapshot(),expected_revision:latest.revision})});
                }
                await this.apply(state);this.resultRevision=0;
            }
            const state=await this.request('?after_revision='+this.revision);
            if(state.model)await this.apply(state);
            await this.ack();this.status('Agent workspace · revision '+this.revision+' · synchronized');
        }catch(error){
            if(error.status===409){this.showConflict();await this.ack('Concurrent page edits require a page choice');}
            else if(error.status===404){this.key=null;sessionStorage.removeItem('systems-workspace');this.status('Session ended · page draft kept');}
            else {this.status('Connection interrupted · page draft kept · retrying');try{await this.ack(error.message);}catch(ignored){}}
        }finally{this.busy=false;this.schedule();}
    },
    async apply(state){
        if(state.model_revision!==this.modelRevision){
            App.closeSlidePanel();App.loadModelData(state.model);this.modelRevision=state.model_revision;
            this.lastSignature=JSON.stringify(App.modelSnapshot());
        }
        if(state.result&&state.result_revision!==this.resultRevision){
            await Simulation.acceptResults(state.result);updateVariableToggles();this.resultRevision=state.result_revision;
        }
        this.revision=state.revision;
        if(state.view.fit!==this.fit){Canvas.fitToModel();this.fit=state.view.fit;}
        if(state.view.selection){
            for(const [group,type] of [['stocks','stock'],['flows','flow'],['variables','variable']]){
                if(App.model[group].some(element=>element.id===state.view.selection))App.selected={id:state.view.selection,type};
            }
            Canvas.render();App.updatePropertiesPanel();
            if(App.isMobile&&state.view.section==='diagram')App.openSlidePanel('properties');
        }
        if(['chart','analytics'].includes(state.view.section)){
            if(App.isMobile){App.openSlidePanel('results');document.querySelector(`[data-tab="${state.view.section==='chart'?'chart':'analytics'}-mobile"]`)?.click();}
            else document.querySelector(`.results-tab[data-tab="${state.view.section}"]`)?.click();
        }else if(state.view.section==='inputs'){
            if(!await ModelValidation.run(document.getElementById('btn-validate')))throw new Error('Input inspection could not be displayed');
        }
        this.status('Agent workspace · revision '+this.revision+' · synchronized');
    },
    async ack(error=null){
        let view='diagram';
        if(document.querySelector('#input-check-dialog[open]'))view='inputs';
        else if(App.isMobile){
            if(App.activePanel==='properties')view='properties';
            else if(App.activePanel==='results')view=(document.querySelector('.mobile-results-tab.active')?.dataset.tab||'chart-mobile').replace('-mobile','');
            else if(App.activePanel==='chat')view='ai';
        }else view=document.querySelector('.results-tab.active')?.dataset.tab||'diagram';
        await this.request('/ack',{method:'POST',body:JSON.stringify({applied_revision:this.revision,error,view,selection:App.selected?.id||null})});
    },
    showConflict(){
        this.conflict=true;this.status('Concurrent edits: choose which draft to keep.');
        for(const [label,keepLocal] of [['Keep page draft',true],['Load agent draft',false]]){
            const button=document.createElement('button');button.className='workspace-conflict';button.textContent=label;
            button.addEventListener('click',async()=>{
                try{
                    const state=await this.request();
                    if(keepLocal){
                        const saved=await this.request('/model',{method:'PUT',body:JSON.stringify({model:App.modelSnapshot(),expected_revision:state.revision})});
                        this.revision=saved.revision;this.modelRevision=saved.model_revision;this.lastSignature=JSON.stringify(App.modelSnapshot());
                        this.resultRevision=0;Simulation.clear();
                    }else{this.modelRevision=0;await this.apply(state);}
                    this.conflict=false;this.banner.querySelectorAll('.workspace-conflict').forEach(node=>node.remove());
                    await this.ack();this.schedule();
                }catch(error){this.status('Draft changed again; inspect before retrying.');}
            });this.banner.appendChild(button);
        }
    },
    async disconnect(){
        this.generation=(this.generation||0)+1;clearTimeout(this.timer);
        while(this.busy)await new Promise(resolve=>setTimeout(resolve,25));
        clearTimeout(this.timer);this.busy=true;
        if(this.key){try{await this.request('',{method:'DELETE'});}catch(error){} }
        clearTimeout(this.timer);this.key=null;sessionStorage.removeItem('systems-workspace');this.conflict=false;
        this.banner.querySelectorAll('.workspace-conflict').forEach(node=>node.remove());this.status('Agent disconnected · page draft kept');
        this.busy=false;
    },
    showConnection(){
        let dialog=document.getElementById('agent-connect-dialog');if(dialog){dialog.showModal();return;}
        dialog=document.createElement('dialog');dialog.id='agent-connect-dialog';dialog.className='agent-dialog';
        const heading=document.createElement('h2');heading.id='agent-dialog-title';heading.textContent='Let your agent drive this page';dialog.setAttribute('aria-labelledby',heading.id);dialog.appendChild(heading);
        const help=document.createElement('p');help.textContent='Connect your agent to the MCP endpoint below. Ask it to open_workspace, or connect the model already on this page. Your agent supplies the reasoning; these page tools use no server-side AI account.';dialog.appendChild(help);
        const endpoint=document.createElement('code');endpoint.textContent=location.origin+'/mcp/';dialog.appendChild(endpoint);
        const create=document.createElement('button');create.textContent='Connect this page';
        const instructions=document.createElement('textarea');instructions.readOnly=true;instructions.setAttribute('aria-label','Private agent connection instructions');instructions.hidden=true;
        create.addEventListener('click',async()=>{
            create.disabled=true;
            try{
                if(!this.key){
                    const response=await fetch('/api/workspaces',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:App.modelSnapshot()})});
                    if(!response.ok)throw new Error('Could not create an agent workspace');
                    await this.connect((await response.json()).workspace_key);
                }
                instructions.value='Use MCP '+location.origin+'/mcp/ to inspect_workspace with workspace_key '+this.key+'. Inspect inputs and retain sources. Use revision checks for updates. Run the model and show results on my page. Keep this session key private.';
                instructions.hidden=false;create.textContent='Connection ready';
            }catch(error){help.textContent=error.message;create.disabled=false;}
        });
        const note=document.createElement('p');note.textContent='The private key grants control of this temporary page only. Sessions expire after one idle hour or a server restart. Edits are not saved to the library until you choose Save. Disconnect revokes the key.';
        const close=document.createElement('button');close.textContent='Close';close.addEventListener('click',()=>{dialog.close();dialog.remove();});
        dialog.append(create,instructions,note,close);document.body.appendChild(dialog);dialog.showModal();
    }
};
document.addEventListener('DOMContentLoaded',()=>AgentWorkspace.init());
