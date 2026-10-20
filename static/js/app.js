/**
 * Systems Modeler - Main Application
 * Supports both desktop and mobile interfaces
 */
const App = {
    // Current model state
    model: {
        id: null,
        name: 'Untitled Model',
        description: '',
        stocks: [],
        flows: [],
        variables: [],
        connectors: [],
        time_settings: { start: 0, end: 100, dt: 0.25 }
    },

    // Selected element
    selected: null,

    // Current tool mode
    mode: 'select', // 'select', 'add-stock', 'add-flow', 'add-variable', 'connect'

    // Connect mode state
    connectFrom: null,

    // Mobile state
    isMobile: false,
    activePanel: null,

    /**
     * Initialize the application
     */
    init() {
        this.checkMobile();
        this.bindEvents();
        UserModels.populateDropdown();
        Canvas.init();
        LLMInterface.init();
        Simulation.init();
        // Load model from URL param if present
        const urlParams = new URLSearchParams(window.location.search);
        const modelId = urlParams.get("model");
        if (modelId) {
            setTimeout(() => this.loadModel(modelId), 1500);
        }
        this.initSimSettings();
        this.syncStepCount();

        // Handle resize
        window.addEventListener('resize', () => this.handleResize());
    },

    /**
     * Check if we're on mobile
     */
    checkMobile() {
        this.isMobile = window.innerWidth < 900;
    },

    /**
     * Handle window resize
     */
    handleResize() {
        const wasMobile = this.isMobile;
        this.checkMobile();

        // Close panel when switching to desktop
        if (wasMobile && !this.isMobile) {
            this.closeSlidePanel();
        }
    },

    /**
     * Bind UI events
     */
    bindEvents() {
        document.getElementById('sim-steps')?.addEventListener('change', (event) => {
            const steps = Number(event.target.value);
            if (!Number.isInteger(steps) || steps < 1 || steps > 10000) {
                this.syncStepCount();
                return;
            }
            const settings = this.model.time_settings;
            settings.dt = (settings.end - settings.start) / steps;
        });
        // Header buttons
        document.getElementById('btn-new').addEventListener('click', () => this.newModel());
        document.getElementById('btn-save').addEventListener('click', () => this.saveModel());
        document.getElementById('model-select').addEventListener('change', (e) => {
            if (e.target.value) {
                this.loadModel(e.target.value);
            }
        });

        // Model name input
        document.getElementById('model-name').addEventListener('change', (e) => {
            this.model.name = e.target.value;
        });

        // Desktop toolbar buttons
        document.getElementById('btn-add-stock').addEventListener('click', () => this.setMode('add-stock'));
        document.getElementById('btn-add-flow').addEventListener('click', () => this.setMode('add-flow'));
        document.getElementById('btn-add-variable').addEventListener('click', () => this.setMode('add-variable'));
        document.getElementById('btn-connect').addEventListener('click', () => this.setMode('connect'));
        document.getElementById('btn-delete').addEventListener('click', () => this.deleteSelected());
        document.getElementById('btn-simulate').addEventListener('click', () => Simulation.run());

        // Mobile FAB (Floating Action Button)
        this.bindFABEvents();

        // Mobile simulate button
        const mobileSimulateBtn = document.getElementById('mobile-simulate-btn');
        if (mobileSimulateBtn) {
            mobileSimulateBtn.addEventListener('click', () => Simulation.run());
        }

        // Mobile tab bar
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const panel = e.currentTarget.dataset.panel;
                this.openSlidePanel(panel);
            });
        });

        // Slide panel close
        const closeBtn = document.getElementById('slide-panel-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeSlidePanel());
        }

        // Overlay click closes panel
        const overlay = document.getElementById('overlay');
        if (overlay) {
            overlay.addEventListener('click', () => this.closeSlidePanel());
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Delete' || e.key === 'Backspace') {
                if (!['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName) && !document.activeElement.isContentEditable && !document.querySelector('dialog[open]')) {
                    this.deleteSelected();
                }
            }
            if (e.key === 'Escape') {
                this.setMode('select');
                this.connectFrom = null;
                this.closeSlidePanel();
            }
        });
    },

    /**
     * Open a mobile slide-up panel
     */
    openSlidePanel(panelType) {
        this.restoreResultPanels();
        const slidePanel = document.getElementById('slide-panel');
        const panelContent = document.getElementById('slide-panel-content');
        const panelTitle = document.getElementById('slide-panel-title');
        const overlay = document.getElementById('overlay');

        // Update tab states
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.panel === panelType);
        });

        this.activePanel = panelType;

        switch (panelType) {
            case 'chat':
                panelTitle.textContent = 'AI Assistant';
                panelContent.innerHTML = this.getChatPanelContent();
                this.initMobileChatEvents();
                break;
            case 'properties':
                panelTitle.textContent = 'Properties';
                panelContent.innerHTML = this.getPropertiesPanelContent();
                this.initMobilePropertyEvents();
                break;
            case 'results':
                panelTitle.textContent = 'Simulation Results';
                panelContent.innerHTML = this.getResultsPanelContent();
                this.initMobileResultsEvents();
                // Render charts in mobile container if results exist
                if (typeof Charts !== 'undefined' && Charts.results) {
                    setTimeout(() => this.renderMobileChart(), 50);  // Small delay to ensure DOM is ready
                }
                for (const [module, targetId] of [[Analytics, 'analytics-container-mobile'], [AIAgent, 'ai-agent-container-mobile']]) {
                    const target = document.getElementById(targetId);
                    if (module?.container && target) {
                        const placeholder = document.createComment('result panel home');
                        module.container.before(placeholder);
                        this.movedResults = this.movedResults || [];
                        this.movedResults.push({node:module.container, placeholder});
                        target.appendChild(module.container);
                        if (module === AIAgent) module.render();
                    }
                }
                break;
        }

        slidePanel.classList.add('open');
        overlay.classList.add('visible');
    },

    /**
     * Close the slide-up panel
     */
    restoreResultPanels() {
        for (const {node, placeholder} of this.movedResults || []) placeholder.replaceWith(node);
        this.movedResults = [];
    },

    closeSlidePanel() {
        this.restoreResultPanels();
        const slidePanel = document.getElementById('slide-panel');
        const overlay = document.getElementById('overlay');

        slidePanel.classList.remove('open');
        overlay.classList.remove('visible');

        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });

        this.activePanel = null;
    },

    /**
     * Get chat panel HTML content for mobile
     */
    getChatPanelContent() {
        const desktopMessages = document.getElementById('chat-messages-desktop');
        const messagesHTML = desktopMessages ? desktopMessages.innerHTML : '';
        const status = document.getElementById('llm-status');
        const statusClass = status ? status.className : 'llm-status';
        const statusText = status ? status.textContent : 'Checking...';

        return `
            <div class="chat-container">
                <div class="chat-header">
                    <span>AI Assistant</span>
                    <span class="${statusClass}">${statusText}</span>
                </div>
                <div class="chat-messages" id="chat-messages-mobile">
                    ${messagesHTML}
                </div>
                <div class="chat-input-container">
                    <textarea id="chat-input-mobile" class="chat-input" placeholder="Describe what you want..." rows="2"></textarea>
                    <button id="btn-send-mobile" class="btn btn-primary btn-send">Send</button>
                </div>
            </div>
        `;
    },

    /**
     * Initialize mobile chat events
     */
    initMobileChatEvents() {
        const input = document.getElementById('chat-input-mobile');
        const sendBtn = document.getElementById('btn-send-mobile');

        if (sendBtn) {
            sendBtn.addEventListener('click', () => {
                LLMInterface.sendFromMobile();
            });
        }

        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    LLMInterface.sendFromMobile();
                }
            });
        }
    },

    /**
     * Get properties panel HTML content
     */
    getPropertiesPanelContent() {
        if (!this.selected) {
            return '<p class="no-selection">Select an element to edit its properties</p>';
        }

        const element = this.getSelectedElement();
        if (!element) {
            return '<p class="no-selection">Element not found</p>';
        }

        let html = `
            <div class="properties-content">
                <div class="property-group">
                    <label>Name</label>
                    <input type="text" id="prop-name-mobile" value="${this.escapeHtml(element.name)}">
                </div>
        `;

        if (this.selected.type === 'stock') {
            html += `
                <div class="property-group">
                    <label>Initial Value</label>
                    <input type="number" id="prop-initial-mobile" value="${element.initial_value}">
                </div>
            `;
        }

        if (this.selected.type === 'flow' || this.selected.type === 'variable') {
            html += `
                <div class="property-group">
                    <label>Equation</label>
                    <input type="text" id="prop-equation-mobile" value="${this.escapeHtml(element.equation || '')}">
                </div>
            `;
        }

        if (this.selected.type === 'flow') {
            const stockOptions = this.model.stocks.map(s =>
                `<option value="${this.escapeHtml(s.name)}" ${element.from_stock === s.name || element.from_stock === s.id ? 'selected' : ''}>${this.escapeHtml(s.name)}</option>`
            ).join('');

            const toStockOptions = this.model.stocks.map(s =>
                `<option value="${this.escapeHtml(s.name)}" ${element.to_stock === s.name || element.to_stock === s.id ? 'selected' : ''}>${this.escapeHtml(s.name)}</option>`
            ).join('');

            html += `
                <div class="property-group">
                    <label>From Stock</label>
                    <select id="prop-from-stock-mobile">
                        <option value="">None (source)</option>
                        ${stockOptions}
                    </select>
                </div>
                <div class="property-group">
                    <label>To Stock</label>
                    <select id="prop-to-stock-mobile">
                        <option value="">None (sink)</option>
                        ${toStockOptions}
                    </select>
                </div>
            `;
        }

        html += '</div>';
        return html;
    },

    /**
     * Initialize mobile property events
     */
    initMobilePropertyEvents() {
        const nameInput = document.getElementById('prop-name-mobile');
        if (nameInput) {
            nameInput.addEventListener('input', (e) => this.updateProperty('name', e.target.value));
        }

        const initialInput = document.getElementById('prop-initial-mobile');
        if (initialInput) {
            initialInput.addEventListener('input',e=>{if(Number.isFinite(e.target.valueAsNumber))this.updateProperty('initial_value',e.target.valueAsNumber);});
            initialInput.addEventListener('change', (e) => this.updateProperty('initial_value', parseFloat(e.target.value)));
        }

        const equationInput = document.getElementById('prop-equation-mobile');
        if (equationInput) {
            equationInput.addEventListener('input', (e) => this.updateProperty('equation', e.target.value));
        }

        const fromStockSelect = document.getElementById('prop-from-stock-mobile');
        if (fromStockSelect) {
            fromStockSelect.addEventListener('change', (e) => this.updateProperty('from_stock', e.target.value || null));
        }

        const toStockSelect = document.getElementById('prop-to-stock-mobile');
        if (toStockSelect) {
            toStockSelect.addEventListener('change', (e) => this.updateProperty('to_stock', e.target.value || null));
        }
    },

    /**
     * Get results panel HTML content - MOBILE
     */
    getResultsPanelContent() {
        const hasResults = typeof Charts !== "undefined" && Charts.results;
        
        // Build variable toggles if we have results
        let variableTogglesHTML = "";
        if (hasResults) {
            const stockNames = Object.keys(Charts.results.values);
            
            variableTogglesHTML = stockNames.map((name, i) => {
                const opt = Charts.options.variables[name];
                const isVisible = opt ? opt.visible : true;
                const color = opt ? opt.color : Charts.colors[i % Charts.colors.length];
                return `
                    <button class="var-chip ${isVisible ? "active" : ""}" data-var="${this.escapeHtml(name)}" aria-pressed="${isVisible}">
                        <span class="var-chip-dot" style="background:${color}"></span>
                        <span class="var-chip-name">${this.escapeHtml(name)}</span>
                    </button>
                `;
            }).join("");
        }
        
        // Get current chart options
        const chartType = hasResults ? (Charts.options.type || "line") : "line";
        const isNormalized = hasResults ? Charts.options.normalize : true;
        const isLog = hasResults ? (Charts.options.scale === "log") : false;

        return `
            <div class="mobile-results-container">
                <div class="mobile-results-tabs" id="results-tabs-mobile">
                    <button class="mobile-results-tab active" data-tab="chart-mobile">📊 Chart</button>
                    <button class="mobile-results-tab" data-tab="analytics-mobile">📈 Stats</button>
                    <button class="mobile-results-tab" data-tab="ai-mobile">🤖 AI</button>
                </div>

                <div class="mobile-tab-content active" id="tab-chart-mobile">
                    ${hasResults ? `
                        <div class="mobile-chart-section">
                            <label class="section-label">Variables (tap to toggle)</label>
                            <div class="var-chips-container" id="var-chips-mobile">
                                ${variableTogglesHTML || "<span class=\"no-vars\">No stocks in model</span>"}
                            </div>
                        </div>
                        
                        <div class="mobile-chart-section">
                            <label class="section-label">Chart Options</label>
                            <div class="chart-controls-mobile">
                                <div class="chart-type-btns">
                                    <button class="chart-type-btn ${chartType === "line" ? "active" : ""}" data-chart-type="line">Line</button>
                                    <button class="chart-type-btn ${chartType === "area" ? "active" : ""}" data-chart-type="area">Area</button>
                                    <button class="chart-type-btn ${chartType === "stacked" ? "active" : ""}" data-chart-type="stacked">Stacked</button>
                                    <button class="chart-type-btn ${chartType === "phase" ? "active" : ""}" data-chart-type="phase">Phase</button>
                                </div>
                                <div class="chart-toggle-btns">
                                    <button class="chart-toggle-btn ${isNormalized ? "active" : ""}" id="btn-normalize-mobile" title="Normalize to %">Norm</button>
                                    <button class="chart-toggle-btn ${isLog ? "active" : ""}" id="btn-log-mobile" title="Log scale">Log</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="chart-wrapper-mobile">
                            <div class="chart-container" id="chart-container-mobile"></div>
                        </div>
                        
                        <div class="mobile-chart-section">
                            <label class="section-label">Final Values</label>
                            <div class="results-summary-mobile" id="results-summary-mobile"></div>
                        </div>
                    ` : `
                        <div class="no-results-mobile">
                            <div class="no-results-icon">📊</div>
                            <p>${Simulation.lastError ? 'Simulation failed: '+this.escapeHtml(Simulation.lastError) : 'Run a simulation to see results'}</p>
                        </div>
                    `}
                </div>

                <div class="mobile-tab-content" id="tab-analytics-mobile">
                    <div id="analytics-container-mobile"></div>
                </div>

                <div class="mobile-tab-content" id="tab-ai-mobile">
                    <div id="ai-agent-container-mobile"></div>
                </div>
            </div>
        `;
    },

    escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
    },

    modelSnapshot() {
        return {...this.model,id:this.model.id||'draft'};
    },

    /**
     * Initialize mobile results events
     */
    initMobileResultsEvents() {
        const self = this;
        
        // Tab switching
        document.querySelectorAll("#results-tabs-mobile .mobile-results-tab").forEach(tab => {
            tab.addEventListener("click", function() {
                const tabId = this.dataset.tab;
                document.querySelectorAll("#results-tabs-mobile .mobile-results-tab").forEach(t => t.classList.remove("active"));
                this.classList.add("active");
                document.querySelectorAll(".mobile-tab-content").forEach(c => c.classList.remove("active"));
                const target = document.getElementById("tab-" + tabId);
                if (target) target.classList.add("active");
            });
        });

        // Variable chip toggles
        document.querySelectorAll("#var-chips-mobile .var-chip").forEach(chip => {
            chip.addEventListener("click", function() {
                const varName = this.dataset.var;
                if (typeof Charts !== "undefined" && Charts.options.variables[varName]) {
                    // Toggle visibility
                    Charts.options.variables[varName].visible = !Charts.options.variables[varName].visible;
                    this.classList.toggle("active");
                    this.setAttribute('aria-pressed', Charts.options.variables[varName].visible);
                    self.renderMobileChart();
                }
            });
        });

        // Chart type buttons
        document.querySelectorAll(".chart-type-btn[data-chart-type]").forEach(btn => {
            btn.addEventListener("click", function() {
                document.querySelectorAll(".chart-type-btn[data-chart-type]").forEach(b => b.classList.remove("active"));
                this.classList.add("active");
                if (typeof Charts !== "undefined") {
                    Charts.options.type = this.dataset.chartType;
                    self.renderMobileChart();
                }
            });
        });

        // Normalize toggle
        const normBtn = document.getElementById("btn-normalize-mobile");
        if (normBtn) {
            normBtn.addEventListener("click", function() {
                if (typeof Charts !== "undefined") {
                    Charts.options.normalize = !Charts.options.normalize;
                    this.classList.toggle("active");
                    self.renderMobileChart();
                }
            });
        }

        // Log scale toggle
        const logBtn = document.getElementById("btn-log-mobile");
        if (logBtn) {
            logBtn.addEventListener("click", function() {
                if (typeof Charts !== "undefined") {
                    Charts.options.scale = Charts.options.scale === "log" ? "linear" : "log";
                    this.classList.toggle("active");
                    self.renderMobileChart();
                }
            });
        }

        // Populate summary
        this.updateMobileResultsSummary();
    },

    /**
     * Update mobile results summary
     */
    updateMobileResultsSummary() {
        const container = document.getElementById("results-summary-mobile");
        if (!container || typeof Charts === "undefined" || !Charts.results) return;

        const values = Charts.results.values;
        const time = Charts.results.time;
        const stockNames = Object.keys(values);
        
        let html = "<div class=\"summary-grid\">";
        
        stockNames.forEach((name, i) => {
            if (values[name]) {
                const finalVal = values[name][values[name].length - 1];
                const opt = Charts.options.variables[name];
                const color = opt ? opt.color : Charts.colors[i % Charts.colors.length];
                html += "<div class=\"summary-item\">" +
                    "<span class=\"summary-dot\" style=\"background:" + color + "\"></span>" +
                    "<span class=\"summary-name\">" + this.escapeHtml(name) + "</span>" +
                    "<span class=\"summary-value\">" + this.formatNumShort(finalVal) + "</span>" +
                    "</div>";
            }
        });
        
        html += "</div>";
        container.innerHTML = html;
    },

    /**
     * Format number short
     */
    formatNumShort(n) {
        if (!isFinite(n)) return "N/A";
        if (Math.abs(n) >= 1000000) return (n/1000000).toFixed(1) + "M";
        if (Math.abs(n) >= 1000) return (n/1000).toFixed(1) + "K";
        if (Math.abs(n) < 0.01 && n !== 0) return n.toExponential(1);
        return n.toFixed(1);
    },

    /**
     * Render chart to mobile container
     */
    renderMobileChart() {
        if (typeof Charts === "undefined" || !Charts.results) return;
        const mobileContainer = document.getElementById("chart-container-mobile");
        if (mobileContainer) {
            const originalContainer = Charts.container;
            Charts.container = mobileContainer;
            Charts.render();
            Charts.container = originalContainer;
        }
    },

    /**
    /**
     * Set the current tool mode
     */
    setMode(mode) {
        this.mode = mode;
        this.connectFrom = null;

        // Update button states
        document.querySelectorAll('.btn-tool').forEach(btn => btn.classList.remove('active'));
        if (mode !== 'select') {
            const btnId = 'btn-' + mode.replace('add-', 'add-');
            const btn = document.getElementById(btnId);
            if (btn) btn.classList.add('active');
        }

        // Update cursor
        const canvas = document.getElementById('canvas-container');
        canvas.style.cursor = mode === 'select' ? 'default' : 'crosshair';

        // Show mode indicator
        this.showModeIndicator(mode);
    },

    /**
     * Show mode indicator briefly
     */
    showModeIndicator(mode) {
        const indicator = document.getElementById('mode-indicator');
        if (!indicator) return;

        const modeNames = {
            'select': 'Select Mode',
            'add-stock': 'Add Stock - Tap Canvas',
            'add-flow': 'Add Flow - Tap Canvas',
            'add-variable': 'Add Variable - Tap Canvas',
            'connect': 'Connect - Tap Elements'
        };

        indicator.textContent = modeNames[mode] || mode;
        indicator.classList.add('visible');

        setTimeout(() => {
            indicator.classList.remove('visible');
        }, 2000);
    },

    /**
     * Create a new model
     */
    newModel() {
        this.model = {
            id: null,
            name: 'Untitled Model',
            description: '',
            stocks: [],
            flows: [],
            variables: [],
            connectors: [],
            time_settings: { start: 0, end: 100, dt: 0.25 }
        };
        document.getElementById('model-name').value = this.model.name;
        this.syncStepCount();
        document.getElementById('model-select').value = '';
        this.selected = null;
        this.updatePropertiesPanel();
        Canvas.render();
        Canvas.resetView();
        Simulation.clear();
    },

    /**
     * Save the current model
     */
    async saveModel() {
        try {
            const data = {
                name: this.model.name,
                description: this.model.description,
                source: this.model.source || null,
                reference: this.model.reference || null,
                category: this.model.category || null,
                stocks: this.model.stocks,
                flows: this.model.flows,
                variables: this.model.variables,
                connectors: this.model.connectors,
                tables: this.model.tables || [],
                time_settings: this.model.time_settings
            };

            let response;
            if (this.model.id && UserModels.get(this.model.id)) {
                // Update existing
                response = await fetch(`/api/models/${this.model.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
            } else {
                // Create new
                response = await fetch('/api/models', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
            }

            if (!response.ok) throw new Error('Save failed');

            const saved = await response.json();
            this.model.id = saved.id;
            // Also save to localStorage
            UserModels.save({...this.model, id: saved.id});
            UserModels.populateDropdown();
            this.showToast('Model saved!');
        } catch (error) {
            console.error('Save error:', error);
            this.showToast('Failed to save: ' + error.message, 'error');
        }
    },

    /**
     * Show a toast notification
     */
    showToast(message, type = 'success') {
        // Simple alert for now - could be replaced with a toast UI
        if (type === 'error') {
            alert(message);
        } else {
            // For success, show a brief indicator
            const indicator = document.getElementById('mode-indicator');
            if (indicator) {
                indicator.textContent = message;
                indicator.classList.add('visible');
                setTimeout(() => indicator.classList.remove('visible'), 2000);
            }
        }
    },

    /**
     * Load a model by ID
     */
    async loadModel(idOrModel) {
        try {
            let model;
            
            // If passed an object, use it directly (from Library import)
            if (typeof idOrModel === "object") {
                model = idOrModel;
            }
            // Check UserModels (localStorage) first  
            else if (typeof idOrModel === "string" && idOrModel.startsWith("user-")) {
                model = UserModels.get(idOrModel);
                if (!model) throw new Error("Model not found in saved models");
            }
            // Fall back to API for library models
            else {
                const response = await fetch(`/api/models/${idOrModel}`);
                if (!response.ok) throw new Error("Load failed");
                model = await response.json();
            }
            
            this.model = model;

            this.syncStepCount();

            this.generateMissingConnectors();
            document.getElementById("model-name").value = model.name;
            this.selected = null;
            this.updatePropertiesPanel();
            Canvas.render();
            Canvas.fitToModel();
            Simulation.clear();
        } catch (error) {
            console.error("Load error:", error);
            this.showToast("Failed to load model: " + error.message, "error");
        }
    },

    /**
     * Load model with data object (for LLM-generated models)
     */
    loadModelData(modelData) {
        this.model = {
            id: modelData.id || null,
            name: modelData.name || 'Generated Model',
            description: modelData.description || '',
            source: modelData.source || null,
            reference: modelData.reference || null,
            category: modelData.category || null,
            stocks: modelData.stocks || [],
            flows: modelData.flows || [],
            variables: modelData.variables || [],
            connectors: modelData.connectors || [],
            tables: modelData.tables || [],
            time_settings: modelData.time_settings || { start: 0, end: 100, dt: 0.25 }
        };
        // Auto-generate missing connectors based on equation dependencies
        this.syncStepCount();
        this.generateMissingConnectors();
        document.getElementById('model-name').value = this.model.name;
        this.syncStepCount();
        this.selected = null;
        this.updatePropertiesPanel();
        Canvas.render();
        Canvas.fitToModel();
        Simulation.clear();
    },

    /**
     * Load the list of available models
     */
    async loadModelList() {
        try {
            const response = await fetch('/api/models');
            if (!response.ok) throw new Error('Failed to load models');

            const models = await response.json();
            const select = document.getElementById('model-select');

            // Clear and rebuild options
            select.innerHTML = '<option value="">Load...</option>';
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.name;
                select.appendChild(option);
            });

            // Select current model if loaded
            if (this.model.id) {
                select.value = this.model.id;
            }
        } catch (error) {
            console.error('Failed to load model list:', error);
        }
    },

    /**
     * Add a new element to the model
     */
    addElement(type, x, y) {
        const id = this.generateId();
        const name = this.generateName(type);

        const element = {
            id,
            name,
            position: { x, y }
        };

        switch (type) {
            case 'stock':
                element.initial_value = 100;
                element.equation = '';
                this.model.stocks.push(element);
                break;
            case 'flow':
                element.equation = '0';
                element.from_stock = null;
                element.to_stock = null;
                this.model.flows.push(element);
                break;
            case 'variable':
                element.equation = '0';
                this.model.variables.push(element);
                break;
        }

        Canvas.render();
        this.selectElement(type, id);
        this.setMode('select');
    },

    /**
     * Add a connector between two elements
     */
    addConnector(fromId, toId) {
        // Check if connector already exists
        const exists = this.model.connectors.some(
            c => c.from_element === fromId && c.to_element === toId
        );

        if (!exists && fromId !== toId) {
            this.model.connectors.push({
                id: this.generateId(),
                from_element: fromId,
                to_element: toId
            });
            Canvas.render();
        }
    },

    /**
     * Parse an equation and extract referenced variable/stock names.
     * Excludes common math functions and constants.
     */
    parseEquationReferences(equation) {
        if (!equation || equation.trim() === '') return [];

        // Math functions and constants to exclude
        const mathNames = new Set([
            'sin', 'cos', 'tan', 'exp', 'log', 'log10', 'sqrt', 'abs',
            'min', 'max', 'pow', 'floor', 'ceil', 'round', 'pi', 'e',
            'if', 'else', 'and', 'or', 'not', 'true', 'false'
        ]);

        // Find all identifier-like tokens (letters followed by alphanumeric/underscore)
        const identifierPattern = /[a-zA-Z_][a-zA-Z0-9_]*/g;
        const matches = equation.match(identifierPattern) || [];

        // Filter out math functions/constants and duplicates
        const references = [];
        const seen = new Set();
        for (const match of matches) {
            const lower = match.toLowerCase();
            if (!mathNames.has(lower) && !seen.has(match)) {
                seen.add(match);
                references.push(match);
            }
        }
        return references;
    },

    /**
     * Generate missing connectors by parsing equations.
     * Creates connectors from referenced elements to the elements using them.
     * Handles both underscore and space variations in names (e.g., "birth_rate" matches "birth rate").
     */
    generateMissingConnectors() {
        // Build a map of element names to their IDs with normalization
        // Store multiple variants: original, lowercase, with underscores, with spaces
        const nameToId = new Map();
        const idToName = new Map();

        const addVariants = (name, id) => {
            const lower = name.toLowerCase();
            nameToId.set(name, id);
            nameToId.set(id, id);
            nameToId.set(lower, id);
            nameToId.set(lower.replace(/ /g, '_'), id);
            nameToId.set(lower.replace(/_/g, ' '), id);
            idToName.set(id, name);
        };

        for (const stock of this.model.stocks) {
            addVariants(stock.name, stock.id);
        }
        for (const flow of this.model.flows) {
            addVariants(flow.name, flow.id);
        }
        for (const variable of this.model.variables) {
            addVariants(variable.name, variable.id);
        }

        // Build a set of existing connectors for quick lookup (normalized to IDs)
        const existingConnectors = new Set();
        for (const connector of this.model.connectors) {
            // Try to resolve names to IDs
            const fromId = nameToId.get(connector.from_element) ||
                           nameToId.get(connector.from_element.toLowerCase()) ||
                           connector.from_element;
            const toId = nameToId.get(connector.to_element) ||
                         nameToId.get(connector.to_element.toLowerCase()) ||
                         connector.to_element;
            existingConnectors.add(`${fromId}->${toId}`);
        }

        // Helper to find element ID with normalization
        const findElementId = (ref) => {
            // Try exact match first
            if (nameToId.has(ref)) return nameToId.get(ref);
            // Try lowercase
            const lower = ref.toLowerCase();
            if (nameToId.has(lower)) return nameToId.get(lower);
            // Try with underscores replaced by spaces
            if (nameToId.has(lower.replace(/_/g, ' '))) return nameToId.get(lower.replace(/_/g, ' '));
            // Try with spaces replaced by underscores
            if (nameToId.has(lower.replace(/ /g, '_'))) return nameToId.get(lower.replace(/ /g, '_'));
            return null;
        };

        // Helper to add connector if it doesn't exist
        const addIfMissing = (fromRef, toId) => {
            const fromId = findElementId(fromRef);
            if (!fromId || fromId === toId) return;
            const key = `${fromId}->${toId}`;
            if (!existingConnectors.has(key)) {
                existingConnectors.add(key);
                // Use the element name for display, not ID
                const fromName = idToName.get(fromId) || fromId;
                const toName = idToName.get(toId) || toId;
                this.model.connectors.push({
                    id: this.generateId(),
                    from_element: fromName,
                    to_element: toName
                });
            }
        };

        // Parse flow equations
        for (const flow of this.model.flows) {
            const refs = this.parseEquationReferences(flow.equation);
            for (const ref of refs) {
                addIfMissing(ref, flow.id);
            }
        }

        // Parse variable equations
        for (const variable of this.model.variables) {
            const refs = this.parseEquationReferences(variable.equation);
            for (const ref of refs) {
                addIfMissing(ref, variable.id);
            }
        }
    },

    /**
     * Select an element
     */
    selectElement(type, id) {
        this.selected = { type, id };
        this.updatePropertiesPanel();
        Canvas.render();

        // On mobile, auto-open properties panel
        if (this.isMobile && type !== 'connector') {
            this.openSlidePanel('properties');
        }
    },

    /**
     * Clear selection
     */
    clearSelection() {
        this.selected = null;
        this.updatePropertiesPanel();
        Canvas.render();
    },

    /**
     * Delete the selected element
     */
    deleteSelected() {
        if (!this.selected) return;

        const { type, id } = this.selected;

        // Remove element
        switch (type) {
            case 'stock':
                this.model.stocks = this.model.stocks.filter(s => s.id !== id);
                // Also remove flows connected to this stock
                this.model.flows.forEach(f => {
                    if (f.from_stock === id) f.from_stock = null;
                    if (f.to_stock === id) f.to_stock = null;
                });
                break;
            case 'flow':
                this.model.flows = this.model.flows.filter(f => f.id !== id);
                break;
            case 'variable':
                this.model.variables = this.model.variables.filter(v => v.id !== id);
                break;
            case 'connector':
                this.model.connectors = this.model.connectors.filter(c => c.id !== id);
                break;
        }

        // Remove any connectors involving this element
        if (type !== 'connector') {
            const elementName = this.getElementName(id);
            this.model.connectors = this.model.connectors.filter(
                c => c.from_element !== id && c.to_element !== id &&
                     c.from_element !== elementName && c.to_element !== elementName
            );
        }

        this.selected = null;
        this.updatePropertiesPanel();
        Canvas.render();
    },

    /**
     * Update the properties panel (desktop)
     */
    updatePropertiesPanel() {
        const content = document.getElementById('properties-content');

        if (!this.selected) {
            content.innerHTML = '<p class="no-selection">Select an element to edit its properties</p>';
            return;
        }

        const element = this.getSelectedElement();
        if (!element) {
            content.innerHTML = '<p class="no-selection">Element not found</p>';
            return;
        }

        let html = `
            <div class="property-group">
                <label>Name</label>
                <input type="text" id="prop-name" value="${this.escapeHtml(element.name)}">
            </div>
        `;

        if (this.selected.type === 'stock') {
            html += `
                <div class="property-group">
                    <label>Initial Value</label>
                    <input type="number" id="prop-initial" value="${element.initial_value}">
                </div>
            `;
        }

        if (this.selected.type === 'flow' || this.selected.type === 'variable') {
            html += `
                <div class="property-group">
                    <label>Equation</label>
                    <input type="text" id="prop-equation" value="${this.escapeHtml(element.equation || '')}">
                </div>
            `;
        }

        if (this.selected.type === 'flow') {
            const stockOptions = this.model.stocks.map(s =>
                `<option value="${this.escapeHtml(s.name)}" ${element.from_stock === s.name || element.from_stock === s.id ? 'selected' : ''}>${this.escapeHtml(s.name)}</option>`
            ).join('');

            const toStockOptions = this.model.stocks.map(s =>
                `<option value="${this.escapeHtml(s.name)}" ${element.to_stock === s.name || element.to_stock === s.id ? 'selected' : ''}>${this.escapeHtml(s.name)}</option>`
            ).join('');

            html += `
                <div class="property-group">
                    <label>From Stock</label>
                    <select id="prop-from-stock">
                        <option value="">None (source)</option>
                        ${stockOptions}
                    </select>
                </div>
                <div class="property-group">
                    <label>To Stock</label>
                    <select id="prop-to-stock">
                        <option value="">None (sink)</option>
                        ${toStockOptions}
                    </select>
                </div>
            `;
        }

        content.innerHTML = html;

        // Bind property change events
        const nameInput = document.getElementById('prop-name');
        if (nameInput) {
            nameInput.addEventListener('input', (e) => this.updateProperty('name', e.target.value));
        }

        const initialInput = document.getElementById('prop-initial');
        if (initialInput) {
            initialInput.addEventListener('input',e=>{if(Number.isFinite(e.target.valueAsNumber))this.updateProperty('initial_value',e.target.valueAsNumber);});
            initialInput.addEventListener('change', (e) => this.updateProperty('initial_value', parseFloat(e.target.value)));
        }

        const equationInput = document.getElementById('prop-equation');
        if (equationInput) {
            equationInput.addEventListener('input', (e) => this.updateProperty('equation', e.target.value));
        }

        const fromStockSelect = document.getElementById('prop-from-stock');
        if (fromStockSelect) {
            fromStockSelect.addEventListener('change', (e) => this.updateProperty('from_stock', e.target.value || null));
        }

        const toStockSelect = document.getElementById('prop-to-stock');
        if (toStockSelect) {
            toStockSelect.addEventListener('change', (e) => this.updateProperty('to_stock', e.target.value || null));
        }
    },

    /**
     * Update a property of the selected element
     */
    updateProperty(property, value) {
        const element = this.getSelectedElement();
        if (property === 'initial_value' && !Number.isFinite(value)) {
            alert('Initial value must be a finite number.');
            this.updatePropertiesPanel();
            return;
        }
        if (element) {
            element[property] = value;
            Canvas.render();
        }
    },

    /**
     * Get the currently selected element
     */
    getSelectedElement() {
        if (!this.selected) return null;

        switch (this.selected.type) {
            case 'stock':
                return this.model.stocks.find(s => s.id === this.selected.id);
            case 'flow':
                return this.model.flows.find(f => f.id === this.selected.id);
            case 'variable':
                return this.model.variables.find(v => v.id === this.selected.id);
            case 'connector':
                return this.model.connectors.find(c => c.id === this.selected.id);
        }
        return null;
    },

    /**
     * Get element name by ID
     */
    getElementName(id) {
        let el = this.model.stocks.find(s => s.id === id);
        if (el) return el.name;
        el = this.model.flows.find(f => f.id === id);
        if (el) return el.name;
        el = this.model.variables.find(v => v.id === id);
        if (el) return el.name;
        return id;
    },

    /**
     * Find element by name or ID
     */
    findElement(nameOrId) {
        let el = this.model.stocks.find(s => s.id === nameOrId || s.name === nameOrId);
        if (el) return { type: 'stock', element: el };
        el = this.model.flows.find(f => f.id === nameOrId || f.name === nameOrId);
        if (el) return { type: 'flow', element: el };
        el = this.model.variables.find(v => v.id === nameOrId || v.name === nameOrId);
        if (el) return { type: 'variable', element: el };
        return null;
    },

    /**
     * Generate a unique ID
     */
    generateId() {
        return 'el_' + Math.random().toString(36).substr(2, 9);
    },

    /**
     * Generate a default name for a new element
     */
    generateName(type) {
        let count;
        switch (type) {
            case 'stock':
                count = this.model.stocks.length + 1;
                return `Stock ${count}`;
            case 'flow':
                count = this.model.flows.length + 1;
                return `Flow ${count}`;
            case 'variable':
                count = this.model.variables.length + 1;
                return `Variable ${count}`;
        }
        return 'Element';
    },

    /**
     * Bind FAB (Floating Action Button) events for mobile
     */
    bindFABEvents() {
        const fabMain = document.getElementById('fab-main');
        const fabMenu = document.getElementById('fab-menu');
        const fabContainer = document.getElementById('fab-container');

        if (!fabMain || !fabMenu) return;

        // Toggle menu on FAB click
        fabMain.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleFABMenu();
        });

        // Handle menu item clicks
        document.querySelectorAll('.fab-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = item.dataset.action;
                this.handleFABAction(action);
                this.closeFABMenu();
            });
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!fabContainer.contains(e.target)) {
                this.closeFABMenu();
            }
        });

        // Close menu on scroll
        document.addEventListener('scroll', () => {
            this.closeFABMenu();
        }, { passive: true });
    },

    /**
     * Toggle FAB menu open/closed
     */
    toggleFABMenu() {
        const fabMain = document.getElementById('fab-main');
        const fabMenu = document.getElementById('fab-menu');

        if (fabMain && fabMenu) {
            fabMain.classList.toggle('open');
            fabMenu.classList.toggle('open');
        }
    },

    /**
     * Close FAB menu
     */
    closeFABMenu() {
        const fabMain = document.getElementById('fab-main');
        const fabMenu = document.getElementById('fab-menu');

        if (fabMain && fabMenu) {
            fabMain.classList.remove('open');
            fabMenu.classList.remove('open');
        }
    },

    /**
     * Handle FAB menu action
     */
    handleFABAction(action) {
        switch (action) {
            case 'add-stock':
                this.setMode('add-stock');
                break;
            case 'add-flow':
                this.setMode('add-flow');
                break;
            case 'add-variable':
                this.setMode('add-variable');
                break;
            case 'connect':
                this.setMode('connect');
                break;
            case 'delete':
                this.deleteSelected();
                break;
        }
    },

    /**
     * Initialize simulation settings modal
     */
    initSimSettings() {
        const modal = document.getElementById('sim-settings-modal');
        const openBtn = document.getElementById('btn-sim-settings');
        const closeBtn = document.getElementById('sim-settings-close');
        const cancelBtn = document.getElementById('sim-settings-cancel');
        const applyBtn = document.getElementById('sim-settings-apply');
        const startInput = document.getElementById('sim-start');
        const endInput = document.getElementById('sim-end');
        const dtInput = document.getElementById('sim-dt');
        const stepsInfo = document.getElementById('sim-steps-info');

        if (!modal) return;

        // Update steps display when inputs change
        const updateSteps = () => {
            const start = parseFloat(startInput.value) || 0;
            const end = parseFloat(endInput.value) || 100;
            const dt = parseFloat(dtInput.value) || 0.25;
            const steps = Math.ceil((end - start) / dt);
            stepsInfo.textContent = `Steps: ${steps}`;
        };

        // Sync inputs with current model settings
        const syncInputs = () => {
            const ts = this.model?.time_settings || { start: 0, end: 100, dt: 0.25 };
            startInput.value = ts.start ?? 0;
            endInput.value = ts.end ?? 100;
            dtInput.value = ts.dt ?? 0.25;
            document.getElementById('sim-method').value = ts.integration_method || 'euler';
            updateSteps();
        };

        // Open modal
        openBtn?.addEventListener('click', () => {
            syncInputs();
            modal.classList.add('active');
        });

        // Mobile settings button
        const mobileSettingsBtn = document.getElementById('mobile-settings-btn');
        if (mobileSettingsBtn) {
            mobileSettingsBtn.onclick = () => {
                syncInputs();
                modal.classList.add('active');
            };
        }

        // Close modal
        const closeModal = () => {
            modal.classList.remove('active');
        };

        closeBtn?.addEventListener('click', closeModal);
        cancelBtn?.addEventListener('click', closeModal);

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                closeModal();
            }
        });

        // Update steps on input change
        startInput?.addEventListener('input', updateSteps);
        endInput?.addEventListener('input', updateSteps);
        dtInput?.addEventListener('input', updateSteps);

        // Presets
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const preset = btn.dataset.preset;
                const start = parseFloat(startInput.value) || 0;
                const end = parseFloat(endInput.value) || 100;
                const duration = end - start;

                switch (preset) {
                    case 'quick':
                        dtInput.value = (duration / 100).toFixed(4);
                        break;
                    case 'normal':
                        dtInput.value = (duration / 400).toFixed(4);
                        break;
                    case 'detailed':
                        dtInput.value = (duration / 1000).toFixed(4);
                        break;
                }
                updateSteps();
            });
        });

        // Apply and run
        applyBtn?.addEventListener('click', () => {
            const start = Number(startInput.value);
            const end = Number(endInput.value);
            const dt = Number(dtInput.value);
            if (![start, end, dt].every(Number.isFinite) || end <= start || dt <= 0 || dt > end - start || Math.ceil((end - start) / dt) > 10000) {
                this.showToast('Use a positive time step, an end after the start, and at most 10,000 steps.', 'error');
                return;
            }
            this.model.time_settings = {
                start,
                end,
                dt: parseFloat(dtInput.value),
                integration_method: document.getElementById('sim-method').value
            };
            this.syncStepCount();
            closeModal();
            Simulation.run();
        });
    },

    syncStepCount() {
        const ts = this.model.time_settings;
        const steps = document.getElementById('sim-steps');
        if (ts && steps) steps.value = Math.ceil((ts.end - ts.start) / ts.dt);
    }
};
