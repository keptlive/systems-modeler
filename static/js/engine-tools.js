/** Optional native engine tools; authored JSON stays the editable source. */
const EngineTools = {
    add(tag,text,parent) {const el=document.createElement(tag);if(text!==null)el.textContent=text;parent.appendChild(el);return el;},
    init(){
        const button=document.createElement('button');button.className='btn btn-tool';button.id='btn-model-source';button.textContent='Source';
        button.title='Edit model JSON, dimensions and reusable modules';
        document.getElementById('btn-sim-settings')?.after(button);
        button.addEventListener('click',()=>this.source());
    },
    dialog(title){
        const dialog=document.createElement('dialog');dialog.className='engine-tools-dialog';
        const heading=this.add('h2',title,dialog);heading.id='engine-tools-heading';dialog.setAttribute('aria-labelledby',heading.id);
        const close=this.add('button','Close',dialog);close.addEventListener('click',()=>dialog.close());
        dialog.addEventListener('close',()=>dialog.remove());document.body.appendChild(dialog);return dialog;
    },
    async request(path,body){
        const response=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(30000)});
        const result=await response.json();
        if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:JSON.stringify(result.detail));
        return result;
    },
    source(){
        const dialog=this.dialog('Model source'), baseline=JSON.stringify(App.modelSnapshot());
        if(App.model.source_document){
            const original=App.model.source_document;
            this.add('p','The original imported MDL file is retained separately. It does not include subsequent edits to this draft.',dialog);
            const download=this.add('button','Download original MDL',dialog);
            download.addEventListener('click',()=>{
                const url=URL.createObjectURL(new Blob([original.text],{type:'text/plain;charset=utf-8'}));
                const link=document.createElement('a');link.href=url;link.download='original-model.mdl';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
            });
            for(const note of original.diagnostics||[])this.add('p',note.message,dialog);
        }
        this.add('p','Edit the original model, including dimensions, per-cell equations and reusable modules. Preview checks expansion without changing the model. Applying replaces the current draft; Save remains a separate action.',dialog);
        const label=this.add('label','Model JSON',dialog);label.htmlFor='engine-source-json';
        const input=this.add('textarea',null,dialog);input.id='engine-source-json';input.value=JSON.stringify(App.modelSnapshot(),null,2);input.spellcheck=false;
        const controls=this.add('div',null,dialog),preview=this.add('button','Preview expansion',controls),apply=this.add('button','Apply to draft',controls);
        const status=this.add('p','',dialog);status.setAttribute('role','status');
        const output=this.add('pre','',dialog);
        const execute=async commit=>{
            preview.disabled=apply.disabled=true;status.textContent='Checking model…';
            try{
                const candidate=JSON.parse(input.value),compiled=await this.request('compile',{model:candidate});
                const cells=Object.keys(compiled.source_map||{}).length;
                output.textContent=JSON.stringify(compiled,null,2);
                status.textContent=cells?`${cells} scalar cells. Simulation limits still apply. Original structure is preserved.`:'Scalar model; no expansion needed.';
                if(commit){
                    if(JSON.stringify(App.modelSnapshot())!==baseline)throw new Error('The current model changed while this editor was open. Reopen Source to avoid overwriting those changes.');
                    App.loadModelData(compiled.source_model);dialog.close();App.showToast('Source applied to draft.');
                }
            }catch(error){status.textContent=error.message;}
            finally{preview.disabled=apply.disabled=false;}
        };
        preview.addEventListener('click',()=>execute(false));apply.addEventListener('click',()=>execute(true));dialog.showModal();input.focus();
    },
    async feedback(button,container){
        button.disabled=true;container.textContent='Analyzing local feedback…';
        try{
            if(!Simulation.results||!Simulation.resultModel)throw new Error('Run the model first.');
            const report=await this.request('feedback',{model:Simulation.resultModel,result:Simulation.results});
            container.replaceChildren();this.add('p','Local response to small stock changes; this does not attribute loop dominance or establish scientific validity.',container);
            for(const sample of report.samples){
                const label=sample.indication?.replaceAll('_',' ')||'unresolved';
                this.add('p',`Time ${sample.time}: ${label}${sample.reason?' — '+sample.reason:''}`,container);
            }
            const details=this.add('details',null,container);this.add('summary','Matrices, eigenvalues and assumptions',details);this.add('pre',JSON.stringify(report,null,2),details);
        }catch(error){container.textContent=error.message;}
        finally{button.disabled=false;}
    }
};
document.addEventListener('DOMContentLoaded',()=>EngineTools.init());
