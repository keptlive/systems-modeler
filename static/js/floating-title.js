// Sync floating title with hidden model name input
(function() {
    const headerInput = document.getElementById('model-name');
    const floatingInput = document.getElementById('floating-model-name');
    
    if (!headerInput || !floatingInput) return;
    
    // Sync initial value
    floatingInput.value = headerInput.value;
    
    // Sync from floating to header (when user types in floating input)
    floatingInput.addEventListener('input', () => {
        headerInput.value = floatingInput.value;
        // Trigger change event for App to detect
        headerInput.dispatchEvent(new Event('change', { bubbles: true }));
    });
    
    // Periodic sync for programmatic changes (when app loads a model)
    setInterval(() => {
        if (floatingInput.value !== headerInput.value) {
            floatingInput.value = headerInput.value;
        }
    }, 300);
})();
