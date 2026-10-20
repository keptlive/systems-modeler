// Mobile Panel Expand/Collapse functionality
(function() {
    const slidePanel = document.getElementById('slide-panel');
    const slidePanelHeader = document.querySelector('.slide-panel-header');
    
    if (!slidePanel || !slidePanelHeader) return;
    
    // Create expand button
    const expandBtn = document.createElement('button');
    expandBtn.className = 'slide-panel-expand';
    expandBtn.id = 'slide-panel-expand';
    const updateExpandButton = () => {
        const expanded = slidePanel.classList.contains('fullscreen');
        expandBtn.title = expanded ? 'Exit fullscreen' : 'Expand to fullscreen';
        expandBtn.setAttribute('aria-label', expandBtn.title);
        expandBtn.setAttribute('aria-pressed', String(expanded));
        const path = expanded ? 'M3 9h6V3m6 0v6h6M9 21v-6H3m18 0h-6v6' : 'M9 3H3v6m12-6h6v6M3 15v6h6m6 0h6v-6';
        expandBtn.innerHTML = `<svg class="studio-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${path}"/></svg>`;
    };
    updateExpandButton();
    
    // Insert before close button
    const closeBtn = document.getElementById('slide-panel-close');
    if (closeBtn) {
        slidePanelHeader.insertBefore(expandBtn, closeBtn);
    } else {
        slidePanelHeader.appendChild(expandBtn);
    }
    
    // Toggle fullscreen
    expandBtn.addEventListener('click', () => {
        slidePanel.classList.toggle('fullscreen');
        if (slidePanel.classList.contains('fullscreen')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        updateExpandButton();
    });
    
    // Exit fullscreen when panel closes
    const originalClose = document.getElementById('slide-panel-close');
    if (originalClose) {
        originalClose.addEventListener('click', () => {
            slidePanel.classList.remove('fullscreen');
            updateExpandButton();
            document.body.style.overflow = '';
        });
    }
    
    // Also handle overlay click to close
    const overlay = document.getElementById('overlay');
    if (overlay) {
        overlay.addEventListener('click', () => {
            slidePanel.classList.remove('fullscreen');
            updateExpandButton();
            document.body.style.overflow = '';
        });
    }
    // Escape and programmatic navigation also close the established sheet.
    new MutationObserver(() => {
        if (!slidePanel.classList.contains('open') && slidePanel.classList.contains('fullscreen')) {
            slidePanel.classList.remove('fullscreen');
            document.body.style.overflow = '';
            updateExpandButton();
        }
    }).observe(slidePanel, {attributes: true, attributeFilter: ['class']});
})();
