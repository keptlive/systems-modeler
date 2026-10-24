/** Local final-stock analysis, isolated from draft and simulation-result state. */
const LocalSensitivity = {
    session:null, sequence:0,
    add(tag,text,parent,className){const node=document.createElement(tag);if(text!==null)node.textContent=text;if(className)node.className=className;parent.appendChild(node);return node;},
    literal(equation){
        const text=String(equation??'').trim();
        // Selector discovery only; the server's canonical parser admits models.
        const decimal=/^[+-]?(?:(?:\d(?:_?\d)*(?:\.(?:\d(?:_?\d)*)?)?|\.\d(?:_?\d)*)(?:[eE][+-]?\d(?:_?\d)*)?)$/;
        const base=/^[+-]?0(?:[xX][\da-fA-F](?:_?[\da-fA-F])*|[bB][01](?:_?[01])*|[oO][0-7](?:_?[0-7])*)$/;
        if(!decimal.test(text)&&!base.test(text))return null;
        const sign=text.startsWith('-')?-1:1,value=sign*Number(text.replace(/^[+-]/,'').replaceAll('_',''));
        return Number.isFinite(value)?value:null;
    },
    candidates(model){return (model.variables||[]).filter(v=>(!v.role||v.role==='auxiliary')&&this.literal(v.equation)!==null);},
    format(value){return typeof value==='number'&&Number.isFinite(value)?(value===0?'0':value.toPrecision(6)):'Unavailable';},
    init(){
        if(this.observer)return;
        const style=this.add('style',null,document.head);style.id='local-sensitivity-style';
        style.textContent=`#local-sensitivity-panel summary{cursor:pointer;font-weight:600;min-height:36px;line-height:2}#local-sensitivity-panel label{display:block;margin-top:10px}#local-sensitivity-panel select,#local-sensitivity-panel input{display:block;box-sizing:border-box;max-width:100%;width:100%;min-height:44px;margin:5px 0;padding:8px;background:#111e32;color:#edf2fa;border:1px solid #6b8ab0;border-radius:5px;font:inherit}#local-sensitivity-panel .local-parameter{border:1px solid #466082;padding:10px;margin:10px 0;border-radius:6px}#local-sensitivity-panel .local-actions{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}#local-sensitivity-panel .local-actions button{flex:0 1 auto}#local-sensitivity-panel .local-evidence{font-size:12px;line-height:1.6}#local-sensitivity-panel .local-evidence p{margin:4px 0}#local-sensitivity-panel th,#local-sensitivity-panel td{vertical-align:top;overflow-wrap:anywhere}#local-sensitivity-panel td small{display:block}#local-sensitivity-panel [role=status]{margin:12px 0}#local-sensitivity-panel .local-results:empty{display:none}`;
        this.observer=new MutationObserver(()=>this.reconcile());this.observer.observe(document.body,{childList:true,subtree:true});this.reconcile();
    },
    reconcile(){
        if(this.session&&!this.session.root.isConnected)this.dispose(this.session);
        const dialog=document.getElementById('input-check-dialog'),body=dialog?.querySelector('.inspection-body');
        if(!body||body.querySelector('#local-sensitivity-panel')||typeof ModelValidation==='undefined'||!ModelValidation.snapshot)return;
        this.mount(body,dialog,ModelValidation.snapshot);
    },
    dispose(session){session.disposed=true;session.controller?.abort();session.dialog.removeEventListener('close',session.close);if(this.session===session)this.session=null;},
    mount(body,dialog,model){
        if(this.session)this.dispose(this.session);
        const snapshot=JSON.parse(JSON.stringify(model)),root=this.add('section',null,body,'inspection-investigate');root.id='local-sensitivity-panel';
        const anchor=body.querySelector('.inspection-investigate');if(anchor&&anchor!==root)anchor.after(root);
        const details=this.add('details',null,root);this.add('summary','Local parameter sensitivity',details);
        this.add('p','Estimate how one final stock changes near selected parameter values. Choose explicit absolute steps; this is local analysis, not a global importance ranking.',details);
        const ts=snapshot.time_settings||{};
        this.add('p',`Inspection snapshot: ${snapshot.name||'Untitled model'} · ${(ts.integration_method||'euler').toUpperCase()} · ${ts.start??0}–${ts.end??100} · Δt ${ts.dt??.25}. Reopen Inspect after editing.`,details,'inspection-note');
        this.add('p','Your draft, simulation charts, variance analytics and AI tools stay unchanged.',details,'inspection-note');
        const session={root,dialog,snapshot,rows:[],disposed:false,busy:false,serial:0,controls:[]};
        session.draft=typeof App!=='undefined'?JSON.stringify(App.modelSnapshot()):null;
        session.close=()=>{session.controller?.abort();};dialog.addEventListener('close',session.close);this.session=session;
        const count=['stocks','flows','variables'].reduce((n,key)=>n+(snapshot[key]?.length||0),0);
        if(count>100||!(snapshot.stocks||[]).length){this.add('p','Local analysis requires a model with stocks and at most 100 elements.',details);return session;}
        session.parameters=this.candidates(snapshot);
        if(!session.parameters.length){this.add('p','No numeric literal parameter variables are available. Computed auxiliaries and stock initial values are not parameter selectors.',details);return session;}
        const form=this.add('form',null,details);form.noValidate=true;session.form=form;
        const label=this.add('label','Final stock output',form);label.htmlFor='local-sensitivity-output';
        const output=this.add('select',null,form);output.id='local-sensitivity-output';output.required=true;
        this.option(output,'','Choose a stock');for(const stock of snapshot.stocks)this.option(output,stock.id,`${stock.name} (${stock.id})${stock.units?' · '+stock.units:''}`);
        session.output=output;session.controls.push(output);
        session.list=this.add('div',null,form);
        const actions=this.add('div',null,form,'local-actions');
        const add=this.add('button','Add parameter',actions);add.type='button';session.add=add;session.controls.push(add);add.addEventListener('click',()=>this.addParameter(session));
        const run=this.add('button','Analyze final stock',actions);run.type='submit';session.run=run;session.controls.push(run);
        const cancel=this.add('button','Cancel analysis',actions);cancel.type='button';cancel.disabled=true;session.cancel=cancel;
        cancel.addEventListener('click',()=>{session.controller?.abort();session.results.replaceChildren();session.status.textContent='Cancellation requested. No further results from this request will be shown.';});
        session.status=this.add('p','Select 1–8 different constants and supply a positive absolute step h for each.',details);session.status.setAttribute('role','status');session.status.setAttribute('aria-live','polite');session.status.setAttribute('aria-atomic','true');
        session.results=this.add('div',null,details,'local-results');
        this.addParameter(session);form.addEventListener('submit',event=>{event.preventDefault();this.run(session);});
        for(const event of ['input','change'])form.addEventListener(event,()=>this.invalidate(session));
        return session;
    },
    option(select,value,text){const option=this.add('option',text,select);option.value=value;return option;},
    invalidate(session){if(!session.busy&&session.results?.children.length){session.results.replaceChildren();session.status.textContent='Selections changed. Analyze again for the current output, parameters and steps.';}},
    addParameter(session){
        if(session.busy||session.rows.length>=8)return;
        this.invalidate(session);
        const row={key:++this.sequence},box=this.add('div',null,session.list,'local-parameter');row.box=box;
        const label=this.add('label','Parameter variable',box);label.htmlFor=`local-parameter-${row.key}`;
        const select=this.add('select',null,box);select.id=label.htmlFor;select.required=true;row.select=select;
        this.option(select,'','Choose a numeric constant');for(const p of session.parameters)this.option(select,p.id,`${p.name} (${p.id}) · ${p.equation}${p.units?' '+p.units:''}`);
        const stepLabel=this.add('label','Absolute perturbation step h',box);stepLabel.htmlFor=`local-step-${row.key}`;
        const step=this.add('input',null,box);step.id=stepLabel.htmlFor;step.type='number';step.step='any';step.inputMode='decimal';step.required=true;step.min='0';step.placeholder='Enter an absolute step';row.step=step;
        const hint=this.add('p','Runs use p−h, p−h/2, p+h/2 and p+h.',box,'inspection-note');row.hint=hint;
        select.addEventListener('change',()=>{step.value='';const p=session.parameters.find(p=>p.id===select.value);hint.textContent=p?`Baseline p = ${p.equation}; h has ${p.units||'unspecified parameter units'}.`:'Runs use p−h, p−h/2, p+h/2 and p+h.';});
        const remove=this.add('button','Remove parameter',box);remove.type='button';row.remove=remove;
        remove.addEventListener('click',()=>{if(session.busy||session.rows.length===1)return;this.invalidate(session);box.remove();session.rows=session.rows.filter(item=>item!==row);session.controls=session.controls.filter(item=>![select,step,remove].includes(item));this.buttons(session);});
        session.rows.push(row);session.controls.push(select,step,remove);this.buttons(session);
    },
    buttons(session){for(const control of session.controls)control.disabled=session.busy;session.add.disabled=session.busy||session.rows.length>=Math.min(8,session.parameters.length);for(const row of session.rows)row.remove.disabled=session.busy||session.rows.length===1;session.cancel.disabled=!session.busy;session.form.setAttribute('aria-busy',String(session.busy));},
    payload(session){
        if(!session.output.value)throw new Error('Choose one final stock output.');
        const seen=new Set(),parameters=[];
        for(const row of session.rows){
            if(!row.select.value)throw new Error('Choose a numeric constant in every parameter row.');
            if(seen.has(row.select.value))throw new Error('Select each parameter only once.');seen.add(row.select.value);
            const text=row.step.value.trim(),step=Number(text);
            if(!text||!Number.isFinite(step)||step<=0)throw new Error('Every absolute step h must be a positive finite number.');
            parameters.push({id:row.select.value,step});
        }
        return {model:session.snapshot,parameters,output_stock_id:session.output.value};
    },
    async run(session){
        if(session.busy||session.disposed)return;
        let payload;
        try{
            if(session.draft!==null&&JSON.stringify(App.modelSnapshot())!==session.draft)throw new Error('The draft changed after this inspection. Close and reopen Inspect before analyzing it.');
            payload=this.payload(session);
        }catch(error){session.status.textContent=error.message;return;}
        session.busy=true;this.buttons(session);session.results.replaceChildren();session.status.textContent='Running bounded local final-stock analysis…';
        const serial=++session.serial,controller=new AbortController();session.controller=controller;
        let timedOut=false;
        const timeout=setTimeout(()=>{timedOut=true;controller.abort();if(!session.disposed&&serial===session.serial)session.status.textContent='Request timed out; server cancellation requested. No further results from this request will be shown.';},35000);
        try{
            const response=await fetch('/api/sensitivity/local',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal});
            const report=await response.json();if(session.disposed||controller.signal.aborted||serial!==session.serial)return;
            if(!response.ok){const failure=report.failure||{};throw new Error(`${failure.code?failure.code+': ':''}${failure.message||(typeof report.detail==='string'?report.detail:'Local analysis could not run.')}`);}
            this.render(report,session.results);session.status.textContent=`Local analysis: ${String(report.status||'unavailable').replaceAll('_',' ')}.`;
            if(JSON.stringify(App.modelSnapshot())!==session.draft)session.status.textContent+=' The draft changed while it ran; these results describe the inspected snapshot.';
        }catch(error){if(!session.disposed&&serial===session.serial)session.status.textContent=controller.signal.aborted?(timedOut?'Request timed out; server cancellation requested. No further results from this request will be shown.':'Cancellation requested. No further results from this request will be shown.'):error.message;}
        finally{clearTimeout(timeout);if(serial===session.serial){session.controller=null;session.busy=false;if(!session.disposed)this.buttons(session);}}
    },
    render(report,container){
        container.replaceChildren();this.add('h3','Local final-stock response',container);
        this.add('p',`Baseline final output: ${this.format(report.baseline_output)}${report.output_units?' '+report.output_units:''} · time ${this.format(report.actual_final_sample_time??report.requested_end)}`,container);
        if(report.error)this.add('p',`${report.error.code||'Analysis failed'}: ${report.error.message||'No valid result.'}`,container);
        if(report.rows?.length){
            const wrap=this.add('div',null,container,'investigation-table-wrap');wrap.tabIndex=0;wrap.setAttribute('aria-label','Local sensitivity results');
            const table=this.add('table',null,wrap,'investigation-table'),caption=this.add('caption','One-parameter partials at the inspected baseline',table);caption.className='inspection-note';
            const head=this.add('tr',null,this.add('thead',null,table));for(const title of ['Parameter','Final-stock derivative','Elasticity','Evidence']){const th=this.add('th',title,head);th.scope='col';}
            const body=this.add('tbody',null,table);
            for(const row of report.rows){
                const tr=this.add('tr',null,body),name=this.add('td',row.parameter_name||row.parameter_id,tr);this.add('small',`ID: ${row.parameter_id}`,name);
                const derivative=this.add('td',row.status==='failed'?'Unavailable':this.format(row.derivative),tr);
                this.add('small',report.output_units&&row.parameter_units?`${report.output_units} / (${row.parameter_units})`:'Derivative units not fully supplied',derivative);
                const elasticity=this.add('td',row.status==='failed'?'Unavailable':this.format(row.elasticity),tr);
                if(row.elasticity_undefined_reason)this.add('small',row.elasticity_undefined_reason.replaceAll('_',' '),elasticity);
                const evidence=this.add('td',null,tr,'local-evidence');this.add('strong',row.status==='locally_consistent'?'Locally consistent':row.status==='failed'?'Failed perturbation':'Refinement or asymmetry warning',evidence);
                if(row.status!=='failed')this.add('p',`h refinement: ${this.format(row.refinement_disagreement)}; left/right: ${this.format(row.one_sided_disagreement)}`,evidence);
                if(row.resolution_warning)this.add('p','Some outputs equal baseline; zero influence is unresolved at this precision.',evidence);
                if(row.small_baseline_warning)this.add('p','Baseline output is very small relative to sampled outputs; interpret elasticity cautiously.',evidence);
                for(const failure of row.failures||[])this.add('p',`${failure.code||'Failure'}: ${failure.message||'Perturbation failed.'}`,evidence);
            }
        }
        this.add('p','Agreement at two steps does not prove differentiability or remove timestep error. This is not a confidence interval or global importance score.',container,'inspection-note');
        const details=this.add('details',null,container);this.add('summary','Sample values, settings, work and provenance',details);this.add('pre',JSON.stringify(report,null,2),details);
        const download=this.add('button','Download sensitivity report',container);download.type='button';download.addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='local-sensitivity-report.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
    }
};
document.addEventListener('DOMContentLoaded',()=>LocalSensitivity.init());
