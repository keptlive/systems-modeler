// Mobile Panel Expand/Collapse functionality
(function() {
    const slidePanel = document.getElementById('slide-panel');
    const slidePanelHeader = document.querySelector('.slide-panel-header');
    
    if (!slidePanel || !slidePanelHeader) return;
    
    // Create expand button
    const expandBtn = document.createElement('button');
    expandBtn.className = 'slide-panel-expand';
    expandBtn.id = 'slide-panel-expand';
    expandBtn.innerHTML = '&#x26F6;'; // Expand icon
    expandBtn.title = 'Expand to fullscreen';
    
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
            expandBtn.innerHTML = '&#x2716;'; // X to close fullscreen
            expandBtn.title = 'Exit fullscreen';
            document.body.style.overflow = 'hidden';
        } else {
            expandBtn.innerHTML = '&#x26F6;'; // Expand icon
            expandBtn.title = 'Expand to fullscreen';
            document.body.style.overflow = '';
        }
    });
    
    // Exit fullscreen when panel closes
    const originalClose = document.getElementById('slide-panel-close');
    if (originalClose) {
        originalClose.addEventListener('click', () => {
            slidePanel.classList.remove('fullscreen');
            expandBtn.innerHTML = '&#x26F6;';
            document.body.style.overflow = '';
        });
    }
    
    // Also handle overlay click to close
    const overlay = document.getElementById('overlay');
    if (overlay) {
        overlay.addEventListener('click', () => {
            slidePanel.classList.remove('fullscreen');
            expandBtn.innerHTML = '&#x26F6;';
            document.body.style.overflow = '';
        });
    }
})();
