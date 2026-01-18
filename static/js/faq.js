// FAQ Modal functionality
document.addEventListener('DOMContentLoaded', function() {
    const faqBtn = document.getElementById('btn-faq');
    if (!faqBtn) return;
    
    // Create FAQ modal
    const modal = document.createElement('div');
    modal.id = 'faq-modal';
    modal.className = 'faq-modal';
    modal.innerHTML = `
        <div class="faq-content">
            <div class="faq-header">
                <h2>Help & FAQ</h2>
                <button class="faq-close">&times;</button>
            </div>
            <div class="faq-body">
                <div class="faq-section">
                    <h3>Getting Started</h3>
                    <p><strong>What is Systems Modeler?</strong><br>
                    A tool for creating System Dynamics models - visual diagrams that simulate how systems change over time.</p>
                    
                    <p><strong>How do I create a model?</strong><br>
                    Use the AI Assistant to describe your system in natural language, or use the + button to manually add elements.</p>
                </div>
                
                <div class="faq-section">
                    <h3>Model Elements</h3>
                    <p><strong>Stock</strong> - Accumulations that change over time (e.g., population, inventory)</p>
                    <p><strong>Flow</strong> - Rates of change into/out of stocks (e.g., birth rate, sales)</p>
                    <p><strong>Variable</strong> - Constants or calculated values (e.g., growth rate)</p>
                    <p><strong>Connector</strong> - Shows influence between elements</p>
                </div>
                
                <div class="faq-section">
                    <h3>Controls</h3>
                    <p><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg> <strong>New</strong> - Create a new model</p>
                    <p><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/></svg> <strong>Save</strong> - Save current model</p>
                    <p><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg> <strong>Import</strong> - Load XMILE file</p>
                    <p><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> <strong>Download</strong> - Export as XMILE</p>
                </div>
                
                <div class="faq-section">
                    <h3>Tips</h3>
                    <p>• Drag elements on the canvas to reposition them</p>
                    <p>• Click an element to edit its properties</p>
                    <p>• Use the Run button to simulate your model</p>
                    <p>• The AI can help you build and modify models</p>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    // Open FAQ
    faqBtn.addEventListener('click', function() {
        modal.classList.add('open');
    });
    
    // Close FAQ
    modal.querySelector('.faq-close').addEventListener('click', function() {
        modal.classList.remove('open');
    });
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.classList.remove('open');
        }
    });
});
