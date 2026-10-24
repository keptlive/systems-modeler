// XMILE File Import functionality
(function() {
    const importBtn = document.getElementById('btn-import');
    const fileInput = document.getElementById('xmile-file-input');
    
    if (!importBtn || !fileInput) return;
    
    // Click import button triggers file dialog
    importBtn.addEventListener('click', () => {
        fileInput.click();
    });
    
    // Handle file selection
    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        // Show loading indicator
        const modeIndicator = document.getElementById('mode-indicator');
        if (modeIndicator) {
            modeIndicator.textContent = 'Importing model file...';
            modeIndicator.classList.add('visible');
        }
        
        try {
            let response;
            if (file.name.toLowerCase().endsWith('.json')) {
                response = await fetch('/api/models', {method:'POST',headers:{'Content-Type':'application/json'},body:await file.text()});
            } else {
                const formData = new FormData();
                formData.append('file', file);
                const format=file.name.toLowerCase().endsWith('.mdl')?'mdl':'xmile';
                response = await fetch('/api/models/import/'+format, {method:'POST',body:formData});
            }
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Import failed');
            }
            
            const model = await response.json();

            // Load the imported model into the app
            if (typeof App !== 'undefined' && App.loadModelData) {
                App.loadModelData(model);
            } else if (typeof App !== 'undefined' && App.model) {
                // Fallback: set model directly
                App.model = model;
                document.getElementById('model-name').value = model.name;
                if (typeof Canvas !== 'undefined') {
                    Canvas.render();
                }
            }
            
            // Update model list
            UserModels.save(model);
            UserModels.populateDropdown();
            if(model.source_document?.diagnostics?.length) App.showToast('Imported with notes: '+model.source_document.diagnostics.map(d=>d.message).join(' '),'info');
            
            if (modeIndicator) {
                modeIndicator.textContent = 'Model imported successfully!';
                setTimeout(() => modeIndicator.classList.remove('visible'), 2000);
            }
            
        } catch (error) {
            console.error('XMILE import error:', error);
            if (modeIndicator) {
                modeIndicator.textContent = 'Import failed: ' + error.message;
                modeIndicator.style.background = 'var(--accent-secondary)';
                setTimeout(() => {
                    modeIndicator.classList.remove('visible');
                    modeIndicator.style.background = '';
                }, 3000);
            }
        }
        
        // Reset file input
        fileInput.value = '';
    });
})();
