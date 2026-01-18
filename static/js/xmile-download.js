// XMILE Download functionality
document.addEventListener('DOMContentLoaded', function() {
    const downloadBtn = document.getElementById('btn-download');
    if (!downloadBtn) return;
    
    downloadBtn.addEventListener('click', async function() {
        // Get current model from app
        if (!window.app || !window.app.model || !window.app.model.id) {
            alert('Please save the model first before downloading.');
            return;
        }
        
        try {
            const response = await fetch('/api/models/' + window.app.model.id + '/export/xmile');
            
            if (!response.ok) {
                throw new Error('Failed to export model');
            }
            
            const blob = await response.blob();
            const filename = window.app.model.name.replace(/\s+/g, '_') + '.xmile';
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Download error:', error);
            alert('Failed to download XMILE file. Make sure the model is saved.');
        }
    });
});
