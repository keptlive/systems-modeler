/** Shared workbench behavior and accessible controls; preserves model state. */
function updateVariableToggles() {
    const container = document.getElementById('chart-variables');
    if (!container || !Charts.results) return;
    container.replaceChildren();
    const title = document.createElement('h4');
    title.textContent = 'Chart series';
    container.appendChild(title);
    const toolbar=document.createElement('div');toolbar.className='series-toolbar';
    const search=document.createElement('input');search.type='search';search.className='series-search';
    search.placeholder='Filter series…';search.setAttribute('aria-label','Filter chart series');
    search.value=Charts.seriesQuery||'';
    const actions=document.createElement('div');actions.className='series-actions';
    const names=Object.keys(Charts.options.variables);
    const stocks=Charts.getStockSeries();
    for(const [label,selection] of [['Stocks',stocks],['All',names],['Clear',[]]]){
        const button=document.createElement('button');button.type='button';button.textContent=label;
        button.setAttribute('aria-label',label==='Stocks'?'Plot only stocks':label==='All'?'Plot all series':'Clear plotted series');
        button.disabled=label==='Stocks'&&!stocks.length;
        button.addEventListener('click',()=>Charts.selectVariables(selection));actions.appendChild(button);
    }
    const count=document.createElement('p');count.className='series-count';count.setAttribute('role','status');
    toolbar.append(search,actions,count);container.appendChild(toolbar);
    const rows=new Map();
    for (const [name, option] of Object.entries(Charts.options.variables)) {
        const row = document.createElement('div');
        row.className = 'variable-toggle';
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = option.visible;
        checkbox.addEventListener('change', () => Charts.toggleVariable(name));
        label.append(checkbox, document.createTextNode(' ' + name));
        const color = document.createElement('input');
        color.type = 'color'; color.value = option.color; color.className = 'color-picker';
        color.setAttribute('aria-label', `Color for ${name}`);
        color.addEventListener('input', () => Charts.setVariableColor(name, color.value));
        row.append(label, color); container.appendChild(row);
        rows.set(name,{row,checkbox});
    }
    const empty=document.createElement('p');empty.textContent='No matching series. Try another name.';
    empty.className='series-count';container.appendChild(empty);
    const refresh=()=>{
        const matched=new Set(Charts.filterSeries(names,search.value));
        for(const [name,{row,checkbox}] of rows){row.hidden=!matched.has(name);checkbox.checked=!!Charts.options.variables[name]?.visible;}
        count.textContent=`${matched.size} of ${names.length} shown · ${Charts.getVisibleVariables().length} plotted`;
        empty.hidden=matched.size>0;
    };
    search.addEventListener('input',()=>{Charts.seriesQuery=search.value;refresh();});
    Charts.onSelectionChanged=refresh;refresh();
}
document.addEventListener('DOMContentLoaded', () => {
    const welcome = document.createElement('section');
    welcome.className = 'canvas-welcome'; welcome.setAttribute('aria-label', 'Start modeling');
    const title = document.createElement('h2'); title.textContent = 'Explore how a system behaves.';
    const intro = document.createElement('p');
    intro.textContent = 'Start with a library model, or bring your agent to build one with you. Inspect the inputs, run it, then compare what changes.';
    const actions = document.createElement('div'); actions.className = 'canvas-welcome-actions';
    for (const [label, target] of [['Browse models','btn-library'],['Connect your agent','btn-connect-agent']]) {
        const button = document.createElement('button'); button.textContent = label;
        button.addEventListener('click', () => {
            if (target==='btn-library') document.getElementById(target)?.click();
            else document.querySelector('.agent-connect')?.click();
        });
        actions.appendChild(button);
    }
    const hint = document.createElement('small'); hint.textContent = 'Building by hand? Choose Stock, Flow or Var in the toolbar, then click the canvas.';
    welcome.append(title,intro,actions,hint); document.getElementById('canvas-container').appendChild(welcome);
    const updateWelcome = () => {
        welcome.hidden = !!(App.model.stocks.length || App.model.flows.length || App.model.variables.length || App.mode !== 'select');
    };
    new MutationObserver(updateWelcome).observe(document.getElementById('canvas'),{childList:true,subtree:true});
    document.addEventListener('click', updateWelcome);
    for (const event of ['input','change','click','keydown']) {
        document.addEventListener(event, () => queueMicrotask(() => Simulation.invalidateIfChanged()));
    }
    document.addEventListener('keydown', () => queueMicrotask(updateWelcome));
    updateWelcome();
    for (const button of document.querySelectorAll('button[title]')) {
        const text = button.textContent.trim();
        if (!button.hasAttribute('aria-label') && (!text || /^[^\p{L}\p{N}]+$/u.test(text))) button.setAttribute('aria-label', button.title);
    }
    const controls = document.createElement('div'); controls.className = 'canvas-view-controls';
    for (const [label, text, action] of [
        ['Zoom out', '−', () => {Canvas.scale=Math.max(Canvas.minScale,Canvas.scale/1.2);Canvas.updateTransform();}],
        ['Fit diagram', 'Fit', () => Canvas.fitToModel()],
        ['Zoom in', '+', () => {Canvas.scale=Math.min(Canvas.maxScale,Canvas.scale*1.2);Canvas.updateTransform();}]
    ]) {
        const button=document.createElement('button');button.textContent=text;
        button.setAttribute('aria-label',label);button.title=label;button.addEventListener('click',action);
        controls.appendChild(button);
    }
    document.getElementById('canvas-container').appendChild(controls);
    const labelFields = () => {
        for (const nameField of document.querySelectorAll('#prop-name,#prop-name-mobile')) {
            const holder = nameField.closest('.properties-content') || nameField.parentElement.parentElement;
            if (!holder.querySelector('[data-input-details]')) {
                const selected = App.getSelectedElement();
                if (selected) {
                    const details = document.createElement('div'); details.dataset.inputDetails='true';
                    const fields = [['Units', 'units', selected.units || '']];
                    if (App.selected.type === 'stock') fields.unshift(['Initial equation (overrides numeric value)', 'equation', selected.equation || '']);
                    for (const [caption, property, value] of fields) {
                        const group=document.createElement('div');group.className='property-group';
                        const label=document.createElement('label');label.textContent=caption;
                        const input=document.createElement('input');input.type='text';input.value=value;
                        input.id=`${nameField.id}-${property}`;
                        input.addEventListener('input',()=>App.updateProperty(property,input.value));
                        group.append(label,input);details.appendChild(group);
                    }
                    holder.appendChild(details);
                }
            }
        }
        for(const group of document.querySelectorAll('.property-group')) {
            const field=group.querySelector('input,select,textarea'),label=group.querySelector('label');
            if(field?.id && label)label.htmlFor=field.id;
        }
        for (const field of document.querySelectorAll('#prop-initial,#prop-initial-mobile')) {
            const label=field.closest('.property-group')?.querySelector('label');
            const selected=App.getSelectedElement();
            const caption=selected?.equation?.trim() ? 'Fallback value (initial equation takes precedence)' : 'Initial value';
            if(label && label.textContent!==caption)label.textContent=caption;
        }
        for(const node of document.querySelectorAll('#canvas g.stock,#canvas g.flow,#canvas g.variable')) {
            node.setAttribute('tabindex','0');node.setAttribute('role','button');
            node.setAttribute('aria-label',`${node.classList[0]}: ${node.__data__?.name||node.querySelector('text')?.textContent||'Model element'}`);
            if(!node.dataset.keyboardReady) {
                node.dataset.keyboardReady='true';
                node.addEventListener('keydown',event=>{
                    if(event.key==='Enter'||event.key===' ') {event.preventDefault();node.querySelector('rect,path,circle')?.dispatchEvent(new MouseEvent('click',{bubbles:true}));}
                });
            }
        }
    };
    new MutationObserver(labelFields).observe(document.querySelector('.main-content'),{childList:true,subtree:true});labelFields();
    const panel=document.getElementById('chart-container');let size='';
    new ResizeObserver(entries=>{
        const rect=entries[0].contentRect,key=`${Math.round(rect.width)}:${Math.round(rect.height)}`;
        if(key!==size&&rect.width>0&&Charts.results) {size=key;requestAnimationFrame(()=>{const previous=Charts.container;Charts.container=panel;Charts.render();Charts.container=previous;});}
    }).observe(panel);
    new ResizeObserver(()=>Canvas.updateDimensions()).observe(document.getElementById('canvas-container'));
});
