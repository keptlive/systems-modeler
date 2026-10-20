/** Input reports are snapshots: checking never saves or changes the model. */
const ModelValidation = {
    snapshot: null, report: null,
    init() {
        const button = document.createElement('button');
        button.id='btn-validate';button.textContent='Check inputs';button.className='btn btn-secondary';
        document.getElementById('sim-settings-cancel')?.before(button);
        button.addEventListener('click',()=>this.run(button,true));
        const quick=document.createElement('button');quick.id='btn-inspect-model';quick.className='btn btn-tool';
        quick.textContent='Inspect';quick.title='Check inputs and investigate numerical behavior';
        document.getElementById('btn-sim-settings')?.before(quick);
        quick.addEventListener('click',()=>this.run(quick));
    },
    async run(button,useSettingsDraft=false) {
        const previousLabel=button?.textContent;
        if(button){button.disabled=true;button.textContent="Checking…";button.setAttribute("aria-busy","true");}
        try {
            const snapshot=JSON.parse(JSON.stringify(App.modelSnapshot()));
            if(useSettingsDraft)snapshot.time_settings=App.readSimulationSettings();
            const response=await fetch('/api/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:snapshot}),signal:AbortSignal.timeout(20000)});
            const body=await response.json();
            if(!response.ok)throw new Error(typeof body.detail==='string'?body.detail:'Could not check model inputs');
            this.snapshot=snapshot;this.report=body;this.show(body);return true;
        }catch(error){App.showToast(error.message,'error');return false;}
        finally{if(button){button.disabled=false;button.textContent=previousLabel;button.removeAttribute("aria-busy");}}
    },
    add(tag,text,parent,className) {
        const el=document.createElement(tag);if(text!==null)el.textContent=text;
        if(className)el.className=className;parent.appendChild(el);return el;
    },
    select(name,dialog) {
        for(const [type,key] of [['stock','stocks'],['flow','flows'],['variable','variables']]) {
            const element=App.model[key].find(item=>item.name===name);
            if(element){
                dialog.close();document.getElementById('sim-settings-modal')?.classList.remove('active');
                App.selectElement(type,element.id);
                document.getElementById(App.isMobile?'prop-name-mobile':'prop-name')?.focus();
                return;
            }
        }
        App.showToast('This element has changed. Inspect the current model again.','info');
    },
    show(report) {
        let dialog=document.getElementById('input-check-dialog');
        if(!dialog){dialog=document.createElement('dialog');dialog.id='input-check-dialog';dialog.setAttribute('aria-labelledby','input-check-title');document.body.appendChild(dialog);}
        dialog.replaceChildren();const add=this.add.bind(this);
        const header=add('header',null,dialog,'inspection-header'),heading=add('div',null,header);
        add('p','MODEL INSPECTION',heading,'inspection-eyebrow');add('h2',report.model,heading).id='input-check-title';
        const close=add('button','Close',header,'inspection-close');close.setAttribute('aria-label','Close input check');close.addEventListener('click',()=>dialog.close());
        const body=add('div',null,dialog,'inspection-body');
        const status=add('section',null,body,`inspection-summary ${report.valid?'checked':'attention'}`);
        add('h3',report.valid?'Initial checks completed':'Inputs need attention',status);
        const errors=report.issues.filter(i=>i.severity==='error').length;
        add('p',`${errors} errors · ${report.issues.length-errors} review notes · ${report.numerical_check==='completed_one_step'?'One numerical step completed':'Numerical check incomplete'}`,status);
        add('p','A completed run does not verify the assumptions, units or source equations.',status,'inspection-note');
        if(report.issues.length){
            const section=add('section',null,body);add('h3','What to review',section);
            const issues=add('ul',null,section,'inspection-issues');
            for(const issue of report.issues){
                const item=add('li',null,issues,`issue-${issue.severity}`);
                add('span',issue.severity==='error'?'ERROR':'REVIEW',item,'inspection-tag');
                if(issue.element){const select=add('button',issue.element,item,'inspection-element');select.addEventListener('click',()=>this.select(issue.element,dialog));}
                add('p',issue.message,item);
            }
        }
        const investigation=add('section',null,body,'inspection-investigate');
        add('h3','Does the result depend on the time step?',investigation);
        add('p','Compare complete runs at the current step, half step and quarter step. Your model stays unchanged.',investigation);
        const investigate=add('button','Investigate numerical behavior',investigation);
        const results=add('div',null,investigation,'investigation-results');results.setAttribute('aria-live','polite');
        const snapshot=this.snapshot;
        investigate.addEventListener('click',()=>this.investigate(investigate,results,snapshot,report));
        const inputs=report.inputs,section=add('section',null,body);add('h3','Equations & initial values',section);
        const search=add('input',null,section,'inspection-search');search.type='search';search.placeholder='Find an element or equation…';search.setAttribute('aria-label','Find an element or equation');
        const searchStatus=add('p','',section,'inspection-search-status');searchStatus.setAttribute('role','status');
        const rows=add('div',null,section,'inspection-inputs');
        const endpoints=new Map((snapshot?.stocks||[]).flatMap(s=>[[s.id,s.name],[s.name,s.name]]));
        const entries=[...inputs.initial_stocks.map(s=>({...s,kind:'Initial stock',equation:s.initial_equation||String(s.initial_value)})),
            ...inputs.flows.map(f=>({...f,kind:'Flow',connection:`${endpoints.get(f.from_stock)||f.from_stock||'External source'} → ${endpoints.get(f.to_stock)||f.to_stock||'External sink'}`})),
            ...inputs.parameters_and_auxiliaries.map(v=>({...v,kind:'Variable'}))];
        for(const entry of entries){
            const row=add('article',null,rows,'inspection-input');row.dataset.search=`${entry.name} ${entry.equation} ${entry.units||''}`.toLowerCase();
            const label=add('div',null,row,'inspection-input-label');add('span',entry.kind,label,'inspection-kind');
            const select=add('button',entry.name,label,'inspection-element');select.addEventListener('click',()=>this.select(entry.name,dialog));
            add('code',entry.equation,row,'inspection-equation');add('small',entry.units||'Units not supplied',row);
            if(entry.connection)add('small',entry.connection,row);
        }
        const empty=add('p','No matching elements.',rows);empty.hidden=entries.length>0;
        const updateSearch=()=>{let found=0;for(const row of rows.querySelectorAll('.inspection-input')){row.hidden=!row.dataset.search.includes(search.value.trim().toLowerCase());if(!row.hidden)found++;}empty.hidden=found>0;searchStatus.textContent=found+' of '+entries.length+' elements';};
        search.addEventListener('input',updateSearch);updateSearch();
        const provenance=add('section',null,body);add('h3','Source & run settings',provenance);
        if(inputs.description)add('p',inputs.description,provenance,'inspection-note');
        add('p',inputs.reference||'No reference supplied.',provenance);
        if(inputs.source&&/^https?:\/\//i.test(inputs.source)){const link=add('a',inputs.source,provenance);link.href=inputs.source;link.target='_blank';link.rel='noopener noreferrer';}
        else add('p',inputs.source||'No source link supplied.',provenance);
        const ts=inputs.time_settings;add('p',`${ts.start} → ${ts.end} · Δt ${ts.dt} · ${ts.integration_method.toUpperCase()} · Seed ${ts.random_seed??'automatic'}`,provenance);
        const footer=add('footer',null,dialog,'inspection-footer');add('small','Snapshot only. Your inputs remain unchanged.',footer);
        const download=add('button','Download report',footer);download.addEventListener('click',()=>{
            const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
            const a=document.createElement('a');a.href=url;a.download='model-investigation.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
        });
        if(!dialog.open)dialog.showModal();close.focus();
    },
    async investigate(button,container,snapshot,parentReport){
        button.disabled=true;container.textContent='Checking the full horizon and finer time steps…';
        try{
            const response=await fetch('/api/investigate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:snapshot}),signal:AbortSignal.timeout(120000)});
            const report=await response.json();
            if(!response.ok)throw new Error(typeof report.detail==='string'?report.detail:'Investigation could not complete.');
            parentReport.investigation=report;this.renderInvestigation(report,container);
        }catch(error){container.textContent=error.message;}
        finally{button.disabled=false;}
    },
    renderInvestigation(report,container){
        container.replaceChildren();const add=this.add.bind(this);
        const labels={
            small_differences_on_checked_grids:'Small differences on the checked time steps',
            differences_decrease_but_grid_sensitivity_remains:'Smaller steps reduce differences; sensitivity remains',
            grid_sensitive_or_nonconvergent_on_checked_grids:'Results remain sensitive to the time step',
            insufficient_completed_refinements:'Not enough refinements to assess a convergence trend',
            inapplicable_for_stochastic_paths:'Random paths need a different convergence experiment',
            no_stocks_to_compare:'No stock trajectories to compare'
        };
        add('h4',labels[report.timestep_assessment.status]||report.timestep_assessment.status,container);
        const runs=add('div',null,container,'investigation-runs');
        for(const run of report.runs){
            const card=add('div',null,runs,'investigation-run');
            add('strong',run.dt_refinement_factor===1?'Current step':`Step ÷ ${run.dt_refinement_factor}`,card);
            add('small',`Δt ${run.settings.dt} · ${run.settings.integration_method.toUpperCase()}`,card);
            add('p',run.status==='completed'?`Completed · ${run.samples} samples`:run.status==='failed'?'Run failed':'Not attempted',card);
            if(run.error){
                const details=add('details',null,card);
                add('summary','View diagnostic',details);add('small',run.error,details);
            }else if(run.reason)add('small',run.reason,card);
        }
        const format=value=>value===null?'Not representable':Number(value).toLocaleString(undefined,{maximumSignificantDigits:4});
        for(const comparison of report.comparisons){
            add('h4',`Run ${comparison.coarse_run} → ${comparison.fine_run}: largest trajectory differences`,container);
            const wrap=add('div',null,container,'investigation-table-wrap'),table=add('table',null,wrap,'investigation-table');
            const head=add('tr',null,add('thead',null,table));
            for(const label of ['Stock','Absolute difference','Scaled difference'])add('th',label,head).scope='col';
            const body=add('tbody',null,table);
            for(const entry of comparison.per_stock){
                const row=add('tr',null,body);add('th',entry.stock,row).scope='row';
                add('td',format(entry.max_absolute_difference),row);
                add('td',format(entry.max_scaled_difference*100)+'%',row);
            }
        }
        if(report.comparisons.length)add('p','Scaled difference uses the largest absolute value of each stock across both trajectories. This is a numerical comparison, not a confidence interval.',container,'inspection-note');
        const leads=report.runs.filter(r=>r.status==='completed').flatMap(r=>(r.domain_leads||[]).map(d=>({run:r.run,...d})));
        if(leads.length){
            add('h4','Domain review leads',container);
            const list=add('ul',null,container);
            for(const lead of leads)add('li',`Run ${lead.run}: ${lead.stock||lead.stocks?.flat().join(', ')} — ${lead.interpretation}`,list);
        }
        for(const warning of report.warnings)add('p',warning,container,'inspection-note');
        add('p','Download the report for exact settings, equations, conservation checks and source hashes. Scientific validity is not established.',container,'inspection-note');
    }
};
document.addEventListener('DOMContentLoaded',()=>ModelValidation.init());
