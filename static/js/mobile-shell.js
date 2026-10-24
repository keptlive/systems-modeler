/* Responsive navigation uses the existing controls, listeners and saved-model list. */
(() => {
    const header = document.querySelector('.header');
    const actions = document.querySelector('.header-icons');
    if (!header || !actions) return;
    const home = document.createComment('header actions home');
    actions.before(home);
    const quick = document.createElement('div');
    quick.className = 'mobile-header-actions';
    quick.innerHTML = '<button type="button" id="mobile-library">Library</button><button type="button" id="mobile-menu" aria-haspopup="dialog" aria-controls="mobile-actions-dialog">Menu</button>';
    header.append(quick);
    const menu = document.createElement('dialog');
    menu.id = 'mobile-actions-dialog';
    menu.setAttribute('aria-labelledby', 'mobile-actions-title');
    menu.innerHTML = '<header><div><span class="mobile-eyebrow">STOCK &amp; FLOW</span><h2 id="mobile-actions-title">Workspace menu</h2></div><button type="button" class="mobile-menu-close" aria-label="Close workspace menu">×</button></header><div class="mobile-actions-body"></div><div class="mobile-menu-extras"><button type="button" data-mobile-inspect>Inspect model</button><button type="button" data-openrouter-settings>AI settings</button></div>';
    document.body.append(menu);
    const trigger = quick.querySelector('#mobile-menu');
    trigger.addEventListener('click', () => menu.showModal());
    quick.querySelector('#mobile-library').addEventListener('click', () => Library.open());
    menu.querySelector('.mobile-menu-close').addEventListener('click', () => menu.close());
    menu.addEventListener('click', event => {
        if (event.target === menu) { const b = menu.getBoundingClientRect(); if (event.clientX < b.left || event.clientX > b.right || event.clientY < b.top || event.clientY > b.bottom) menu.close(); }
    });
    // Close before dispatching existing handlers (which may open another dialog).
    menu.addEventListener('click', event => { if (event.target.closest('.header-icons button, [data-mobile-inspect], [data-openrouter-settings]')) menu.close(); }, true);
    menu.querySelector('[data-mobile-inspect]').addEventListener('click', () => document.getElementById('btn-inspect-model')?.click());
    actions.addEventListener('change', event => { if (event.target.id === 'model-select' && event.target.value) menu.close(); });
    menu.addEventListener('close', () => trigger.focus());
    const media = window.matchMedia('(max-width: 899px)');
    const adapt = () => {
        if (media.matches) menu.querySelector('.mobile-actions-body').append(actions);
        else { if (menu.open) menu.close(); home.after(actions); }
    };
    media.addEventListener('change', adapt);
    adapt();
    const aiSettings = document.createElement('button');
    aiSettings.type = 'button'; aiSettings.className = 'ai-settings-button';
    aiSettings.setAttribute('data-openrouter-settings', ''); aiSettings.textContent = 'AI settings';
    document.querySelector('.panel-left .panel-header')?.append(aiSettings);
    // Mobile chart dimensions must follow panel expansion, rotation and keyboard resizing.
    const panel = document.getElementById('slide-panel');
    if (panel) {
        panel.setAttribute('role', 'dialog');
        panel.setAttribute('aria-modal', 'true');
        panel.setAttribute('aria-labelledby', 'slide-panel-title');
        let wasOpen = false, panelOpener;
        new MutationObserver(() => {
            const isOpen = panel.classList.contains('open');
            if (isOpen && !wasOpen) {
                panelOpener = document.activeElement;
                document.getElementById('slide-panel-close')?.focus();
            } else if (!isOpen && wasOpen && panelOpener?.isConnected) panelOpener.focus();
            wasOpen = isOpen;
        }).observe(panel, {attributes:true, attributeFilter:['class']});
        panel.addEventListener('keydown', event => {
            if (event.key !== 'Tab' || document.querySelector('dialog[open]')) return;
            const focusable = [...panel.querySelectorAll('button,input,select,textarea,summary,a[href],[tabindex="0"]')].filter(el => !el.disabled && el.getClientRects().length);
            const first = focusable[0], last = focusable[focusable.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
        });
    }
    if (panel && typeof ResizeObserver !== 'undefined') {
        let frame;
        new ResizeObserver(() => {
            cancelAnimationFrame(frame);
            frame = requestAnimationFrame(() => {
                if (App.activePanel === 'results' && document.getElementById('tab-chart-mobile')?.classList.contains('active')) App.renderMobileChart();
            });
        }).observe(panel);
    }
})();
