/** Presentation-only studio controls. Never writes model or simulation state. */
document.addEventListener('DOMContentLoaded', () => {
    const paths = {
        stock: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 9h10"/>',
        flow: '<path d="M2 12h4m12 0h4M6 6l12 12V6L6 18Z"/>',
        variable: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2" fill="currentColor" stroke="none"/>',
        link: '<path d="M3 18C3 6 14 4 20 8m-5-5 5 5-5 4"/>',
        delete: '<path d="M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7"/>',
        settings: '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3" fill="#1b2e44"/><circle cx="15" cy="17" r="3" fill="#1b2e44"/>',
        inspect: '<path d="M4 3h10l4 4v4M4 3v18h7M8 7h3M8 11h3"/><circle cx="16" cy="16" r="4"/><path d="m19 19 3 3"/>',
        play: '<path d="m8 4 12 8-12 8Z"/>',
        save: '<path d="M4 3h13l4 4v14H3V3Zm3 0v6h10V3M7 21v-8h10v8"/>',
        export: '<path d="M4 15v6h16v-6M12 3v13m-5-5 5 5 5-5"/>',
        compare: '<path d="M3 7h18l-4-4m4 4-4 4M21 17H3l4-4m-4 4 4 4"/>',
        expand: '<path d="M9 3H3v6m12-6h6v6M3 15v6h6m6 0h6v-6"/>',
        sidebar: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>'
    };
    const icon = (name, className='studio-icon') => {
        const template=document.createElement('template');
        template.innerHTML=`<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]}</svg>`;
        return template.content.firstElementChild;
    };
    const brand=icon('stock','studio-brand');document.querySelector('.header-title').prepend(brand);
    for(const [id,name,label] of [
        ['btn-add-stock','stock','Stock'],['btn-add-flow','flow','Flow'],['btn-add-variable','variable','Var'],
        ['btn-connect','link','Link'],['btn-delete','delete','Del'],['btn-sim-settings','settings','Settings'],
        ['btn-inspect-model','inspect','Inspect']
    ]) {
        const button=document.getElementById(id);if(!button)continue;
        const text=document.createElement('span');text.textContent=label;button.replaceChildren(icon(name),text);
    }
    // Run and animate labels are owned by simulation/chart state; retain their text.
    for(const [id,name] of [['btn-save-run','save'],['btn-export-chart','export'],['btn-compare','compare'],['btn-fullscreen','expand'],['mobile-settings-btn','settings']]){
        const button=document.getElementById(id);if(button){button.setAttribute('aria-label',button.title);button.replaceChildren(icon(name));}
    }
    const toggle=document.createElement('button');toggle.type='button';toggle.className='studio-assistant-toggle';
    toggle.id='btn-toggle-assistant';toggle.setAttribute('aria-controls','assistant-panel');toggle.setAttribute('aria-expanded','true');
    toggle.setAttribute('aria-label','Hide assistant panel');toggle.title='Show or hide the assistant panel';
    const caption=document.createElement('span');caption.textContent='Assistant';toggle.append(icon('sidebar'),caption);
    document.querySelector('.panel-left').id='assistant-panel';document.querySelector('.header-icons').prepend(toggle);
    toggle.addEventListener('click',()=>{
        const collapsed=document.querySelector('.app').classList.toggle('assistant-collapsed');
        toggle.setAttribute('aria-expanded',String(!collapsed));toggle.setAttribute('aria-label',`${collapsed?'Show':'Hide'} assistant panel`);
        // Existing ResizeObserver updates canvas dimensions without moving nodes.
    });
    const legend=document.createElement('div');legend.className='studio-legend';legend.setAttribute('aria-label','Diagram legend');
    for(const [name,label] of [['stock','Stock'],['flow','Flow'],['variable','Variable'],['link','Dependency']]){
        const item=document.createElement('span');item.append(icon(name),document.createTextNode(label));legend.append(item);
    }
    document.getElementById('canvas-container').append(legend);

    // The established settings overlay keeps its open/apply/cancel workflow.
    // Supply keyboard containment and restore focus without intercepting a
    // nested native inspection dialog.
    const settings=document.getElementById('sim-settings-modal');
    let settingsOpen=false, settingsOpener=null;
    new MutationObserver(()=>{
        const open=settings.classList.contains('active');
        if(open===settingsOpen)return;
        settingsOpen=open;
        if(open){settingsOpener=document.activeElement;document.getElementById('sim-start').focus();}
        else if(!document.querySelector('dialog[open]')&&(settings.contains(document.activeElement)||document.activeElement===document.body))settingsOpener?.focus();
    }).observe(settings,{attributes:true,attributeFilter:['class']});
    settings.addEventListener('keydown',event=>{
        if(event.key!=='Tab'||!settingsOpen||document.querySelector('dialog[open]'))return;
        const fields=[...settings.querySelectorAll('button,input,select,textarea,[tabindex]')].filter(el=>!el.disabled&&el.tabIndex>=0&&el.getClientRects().length);
        const first=fields[0],last=fields[fields.length-1];
        if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
        else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
    });
});
