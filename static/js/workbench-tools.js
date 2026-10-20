/** Additive workbench navigation. Never changes equations, settings or results. */
const WorkbenchTools = {
    filter(items, query) {
        const normalized=query.trim().toLocaleLowerCase();
        const words=normalized.split(/\s+/).filter(Boolean);
        const rank=item=>{
            const label=item.label.toLocaleLowerCase();
            return label===normalized?0:label.startsWith(normalized)?1:label.includes(normalized)?2:3;
        };
        return items.map((item,index)=>({item,index}))
            .filter(({item})=>words.every(word=>`${item.label} ${item.detail||''}`.toLocaleLowerCase().includes(word)))
            .sort((a,b)=>rank(a.item)-rank(b.item)||a.index-b.index).map(({item})=>item);
    },
    state(model, simulation, running) {
        const count=(model.stocks?.length||0)+(model.flows?.length||0)+(model.variables?.length||0);
        if(running)return {kind:'running',label:'Running simulation…'};
        if(simulation.lastError)return {kind:'error',label:'Run failed · inspect inputs'};
        if(simulation.results)return {kind:'complete',label:`Run complete · ${simulation.results.time?.length||0} samples`};
        return {kind:'idle',label:count?'Ready to run':'Add a model to begin'};
    },
    init() {
        const header=document.querySelector('.header-icons');
        const launch=document.createElement('button');
        launch.id='btn-workbench-search';launch.className='workbench-search';launch.type='button';
        const label=document.createElement('span');label.textContent='Find / commands';
        const shortcut=document.createElement('kbd');shortcut.textContent='Ctrl K';shortcut.setAttribute('aria-hidden','true');
        launch.append(label,shortcut);launch.setAttribute('aria-label','Find model elements and commands (Control or Command K)');
        header.prepend(launch);launch.addEventListener('click',()=>this.open());
        const strip=document.createElement('div');strip.className='workbench-context';
        strip.setAttribute('aria-label','Current model and run status');
        this.inventory=document.createElement('span');this.inventory.className='workbench-inventory';
        this.settings=document.createElement('button');this.settings.type='button';this.settings.className='workbench-settings';
        this.settings.title='Applied simulation settings — click to edit';this.settings.addEventListener('click',()=>document.getElementById('btn-sim-settings').click());
        this.status=document.createElement('span');this.status.className='workbench-status';this.status.setAttribute('role','status');this.status.setAttribute('aria-live','polite');
        strip.append(this.inventory,this.settings,this.status);
        document.querySelector('.canvas-toolbar').after(strip);
        const runGroup=document.createElement('div');runGroup.className='workbench-run-controls';
        const steps=document.querySelector('.steps-control');const run=document.getElementById('btn-simulate');
        if(steps&&run){steps.before(runGroup);runGroup.append(steps,run);}
        this.createDialog();
        let scheduled=false;
        const refresh=()=>{if(!scheduled){scheduled=true;requestAnimationFrame(()=>{scheduled=false;this.refresh();});}};
        for(const id of ['canvas','results-content']){
            const target=document.getElementById(id);
            if(target)new MutationObserver(refresh).observe(target,{childList:true,subtree:true,characterData:true});
        }
        for(const id of ['btn-simulate','mobile-simulate-btn']){
            const target=document.getElementById(id);
            if(target)new MutationObserver(refresh).observe(target,{attributes:true,attributeFilter:['disabled']});
        }
        for(const name of ['input','change','click'])document.addEventListener(name,refresh);
        document.addEventListener('keydown',event=>{
            if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){
                if(document.querySelector('dialog[open]')&&!this.dialog.open)return;
                event.preventDefault();this.open();
            }
        });
        this.refresh();
    },
    refresh() {
        const m=App.model, ts=m.time_settings||{};
        const inventory=`${m.stocks.length} stocks · ${m.flows.length} flows · ${m.variables.length} variables`;
        if(this.inventory.textContent!==inventory)this.inventory.textContent=inventory;
        const settings=`${(ts.integration_method||'euler').toUpperCase()} · Δt ${ts.dt??.25} · ${ts.start??0}–${ts.end??100}`;
        if(this.settings.textContent!==settings)this.settings.textContent=settings;
        this.settings.setAttribute('aria-label',`Simulation settings: ${settings}`);
        const state=this.state(m,Simulation,document.getElementById('btn-simulate')?.disabled);
        if(this.status.textContent!==state.label)this.status.textContent=state.label;
        this.status.dataset.state=state.kind;
    },
    commands() {
        const action=(label,detail,id)=>({label,detail,run:()=>document.getElementById(id)?.click()});
        const commands=[
            action('Browse model library','Explore and import examples','btn-library'),
            action('Inspect model inputs','Check equations, units and numerical behavior','btn-inspect-model'),
            action('Simulation settings','Time range, integration method and random seed','btn-sim-settings'),
            action('Run simulation','Compute the current model','btn-simulate'),
            action('Save model','Save using the existing model workflow','btn-save'),
            action('Import model','XMILE, XML or JSON','btn-import'),
            action('Export model','Download the current model','btn-download'),
            action('Help and documentation','Modeling and application help','btn-faq'),
            {label:'Fit diagram',detail:'Bring the entire model into view',run:()=>Canvas.fitToModel()},
            {label:'Connect your agent',detail:'Open the existing agent connection workflow',run:()=>document.querySelector('.agent-connect')?.click()},
            ...[['Stock','add-stock'],['Flow','add-flow'],['Variable','add-variable'],['Link','connect']].map(([label,mode])=>({label:`Add ${label.toLowerCase()}`,detail:'Choose a tool, then click the diagram',run:()=>App.setMode(mode)}))
        ];
        for(const [kind,key] of [['Stock','stocks'],['Flow','flows'],['Variable','variables']]){
            for(const element of App.model[key])commands.push({label:element.name,detail:`${kind} · ${element.equation||'Initial value: '+element.initial_value}`,run:()=>{
                App.selectElement(kind.toLowerCase(),element.id);
                document.getElementById(App.isMobile?'prop-name-mobile':'prop-name')?.focus();
            }});
        }
        return commands;
    },
    createDialog() {
        const dialog=document.createElement('dialog');dialog.id='workbench-command-dialog';
        dialog.setAttribute('aria-labelledby','workbench-command-title');
        const top=document.createElement('header');
        const heading=document.createElement('h2');heading.id='workbench-command-title';heading.textContent='Find in your workbench';
        const close=document.createElement('button');close.type='button';close.textContent='Close';close.addEventListener('click',()=>dialog.close());
        top.append(heading,close);
        const input=document.createElement('input');input.type='search';input.placeholder='Search commands, elements or equations…';
        input.setAttribute('aria-label','Search commands, elements or equations');input.setAttribute('aria-controls','workbench-command-results');
        const count=document.createElement('p');count.className='command-count';count.setAttribute('role','status');
        const list=document.createElement('div');list.id='workbench-command-results';list.className='command-results';
        const hint=document.createElement('footer');hint.textContent='↑ ↓ to move · Enter to choose · Esc to close';
        dialog.append(top,input,count,list,hint);document.body.append(dialog);
        this.dialog=dialog;this.input=input;this.list=list;this.count=count;
        input.addEventListener('input',()=>this.render());
        dialog.addEventListener('keydown',event=>{
            if(event.key==='Escape'){event.preventDefault();event.stopPropagation();dialog.close();return;}
            const buttons=[...list.querySelectorAll('button')];const current=buttons.indexOf(document.activeElement);
            if(event.key==='ArrowDown'||event.key==='ArrowUp'){
                event.preventDefault();const next=current<0?(event.key==='ArrowDown'?0:buttons.length-1):(current+(event.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length;
                buttons[next]?.focus();
            }else if(event.key==='Enter'&&event.target===input){event.preventDefault();buttons[0]?.click();}
        });
        // Native dialog restores focus; element commands may then focus their property field.
    },
    open() {
        if(this.dialog.open){this.input.focus();return;}
        if(document.querySelector('dialog[open], .modal-overlay.active, .library-modal.open'))return;
        this.opener=document.activeElement;this.input.value='';this.render();this.dialog.showModal();this.input.focus();
    },
    render() {
        const matches=this.filter(this.commands(),this.input.value);this.list.replaceChildren();
        this.count.textContent=matches.length?`${matches.length} matches${matches.length>100?' · first 100 shown':''}`:'No matching commands or elements. Try a name or equation.';
        for(const item of matches.slice(0,100)){
            const button=document.createElement('button');button.type='button';button.className='command-item';
            const title=document.createElement('strong');title.textContent=item.label;
            const detail=document.createElement('small');detail.textContent=item.detail;
            button.append(title,detail);button.addEventListener('click',()=>{this.dialog.close();item.run();});this.list.append(button);
        }
    }
};
document.addEventListener('DOMContentLoaded',()=>WorkbenchTools.init());
