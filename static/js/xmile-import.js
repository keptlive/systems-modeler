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
            modeIndicator.textContent = 'Importing XMILE file...';
            modeIndicator.classList.add('visible');
        }
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/api/models/import/xmile', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Import failed');
            }
            
            const model = await response.json();

            // Load the imported model into the app
            if (window.App && App.loadModelData) {
                App.loadModelData(model);
            } else if (window.App && App.model) {
                // Fallback: set model directly
                App.model = model;
                document.getElementById('model-name').value = model.name;
                if (window.Canvas) {
                    Canvas.render();
                }
            }
            
            // Update model list
            if (App.loadModelList) {
                App.loadModelList();
            }
            
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
