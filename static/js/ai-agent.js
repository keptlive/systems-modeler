/**
 * Systems Modeler - AI Analysis Agent
 * Provides AI-powered insights, recommendations, and Q&A about simulation results
 */
const AIAgent = {
    container: null,
    results: null,
    model: null,
    analysis: null,
    conversationHistory: [],
    isAvailable: false,

    /**
     * Initialize AI agent
     */
    init(containerId) {
        this.container = document.getElementById(containerId);
        this.checkAvailability();
    },

    /**
     * Check if AI analysis is available
     */
    async checkAvailability() {
        try {
            const response = await OpenRouterUI.request('/api/analyze/status');
            if (response.ok) {
                const data = await response.json();
                this.isAvailable = data.available;
            }
        } catch (error) {
            console.error('Failed to check AI availability:', error);
            this.isAvailable = false;
        }
    },

    /**
     * Set the model and results for analysis
     */
    setContext(model, results) {
        this.model = model;
        this.results = results;
        this.analysis = null;
        this.conversationHistory = [];
    },

    /**
     * Run AI analysis on current results
     */
    async analyze() {
        if (!this.results || !this.model) {
            return null;
        }

        this.setLoading(true);

        try {
            const response = await OpenRouterUI.request('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: {...this.model,id:this.model.id||'draft'},
                    simulation_results: this.results
                })
            });

            if (!response.ok) {
                throw new Error('Analysis failed');
            }

            this.analysis = await response.json();
            this.isAvailable = this.analysis.ai_available;
            this.render();
            return this.analysis;

        } catch (error) {
            console.error('AI analysis error:', error);
            this.renderError(error.message);
            return null;
        } finally {
            this.setLoading(false);
        }
    },

    /**
     * Ask a question about the results
     */
    async askQuestion(question) {
        if (!this.results || !this.model) {
            return null;
        }

        // Add to conversation history
        this.conversationHistory.push({
            role: 'user',
            content: question
        });
        this.renderConversation();

        try {
            const response = await OpenRouterUI.request('/api/analyze/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: {...this.model,id:this.model.id||'draft'},
                    simulation_results: this.results,
                    question: question
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to get answer');
            }

            const data = await response.json();

            this.conversationHistory.push({
                role: 'assistant',
                content: data.answer,
                insights: data.supporting_insights
            });

            this.renderConversation();
            return data;

        } catch (error) {
            this.conversationHistory.push({
                role: 'error',
                content: error.message
            });
            this.renderConversation();
            return null;
        }
    },

    /**
     * Render the AI analysis panel
     */
    render() {
        if (!this.container) return;

        if (!this.results) {
            this.container.innerHTML = `
                <div class="ai-agent-placeholder">
                    <div class="ai-icon">&#129302;</div>
                    <p>Run a simulation to get AI insights</p>
                </div>
            `;
            return;
        }

        if (!this.analysis) {
            this.container.innerHTML = `
                <div class="ai-agent-placeholder">
                    <div class="ai-icon">&#129302;</div>
                    <p>Click "Analyze" to get AI insights</p>
                    <button class="btn btn-primary btn-analyze" onclick="AIAgent.analyze()">
                        &#10024; Analyze results
                    </button>
                </div>
            `;
            return;
        }

        let html = '<div class="ai-agent-content">';
        html += `<p class="ai-analysis-status">${this.analysis.ai_used ? 'AI interpretation completed. Check its claims against the inputs and results.' : 'Statistical interpretation. An AI response was not used.'}</p>`;

        // Summary section
        html += `
            <div class="ai-section ai-summary">
                <h3><span class="ai-icon">&#128161;</span> Summary</h3>
                <p>${App.escapeHtml(this.analysis.summary)}</p>
            </div>
        `;

        // Insights section
        if (this.analysis.insights && this.analysis.insights.length > 0) {
            html += `
                <div class="ai-section ai-insights">
                    <h3><span class="ai-icon">&#128270;</span> Key Insights</h3>
                    <ul class="insights-list">
                        ${this.analysis.insights.map(insight => `
                            <li class="insight-item">
                                <span class="insight-bullet">&#9679;</span>
                                <span class="insight-text">${App.escapeHtml(insight)}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `;
        }

        // Recommendations section
        if (this.analysis.recommendations && this.analysis.recommendations.length > 0) {
            html += `
                <div class="ai-section ai-recommendations">
                    <h3><span class="ai-icon">&#128640;</span> Recommendations</h3>
                    <ul class="recommendations-list">
                        ${this.analysis.recommendations.map(rec => `
                            <li class="recommendation-item">
                                <span class="rec-bullet">&#10148;</span>
                                <span class="rec-text">${App.escapeHtml(rec)}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `;
        }

        // Q&A section
        html += `
            <div class="ai-section ai-qa">
                <h3><span class="ai-icon">&#128172;</span> Ask AI</h3>
                <div class="ai-conversation" id="ai-conversation">
                    ${this.renderConversationContent()}
                </div>
                <div class="ai-input-container">
                    <input type="text"
                           id="ai-question-input"
                           class="ai-question-input"
                           placeholder="Ask about the simulation results..."
                           ${!this.isAvailable ? 'disabled' : ''}
                    >
                    <button class="btn btn-primary btn-ask"
                            onclick="AIAgent.handleAsk()"
                            ${!this.isAvailable ? 'disabled' : ''}>
                        Ask
                    </button>
                </div>
                ${!this.isAvailable ? `
                    <p class="ai-unavailable-notice">
                        &#9888; Server AI Q&amp;A is unavailable. Your connected agent can interpret these results through MCP.
                    </p>
                ` : ''}
            </div>
        `;

        // Add the Model Feedback panel
        html += this.renderFeedbackPanel();

        html += '</div>';

        this.container.innerHTML = html;

        // Add enter key handler for question input
        const input = document.getElementById('ai-question-input');
        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.handleAsk();
                }
            });
        }
    },

    /**
     * Render conversation content
     */
    renderConversationContent() {
        if (this.conversationHistory.length === 0) {
            return `
                <div class="conversation-placeholder">
                    <p>Ask questions about your simulation results...</p>
                    <div class="example-questions">
                        <button class="example-question" onclick="AIAgent.askExample('Why did population decline?')">
                            "Why did population decline?"
                        </button>
                        <button class="example-question" onclick="AIAgent.askExample('What was the peak value?')">
                            "What was the peak value?"
                        </button>
                        <button class="example-question" onclick="AIAgent.askExample('How can I increase growth?')">
                            "How can I increase growth?"
                        </button>
                    </div>
                </div>
            `;
        }

        return this.conversationHistory.map(msg => {
            if (msg.role === 'user') {
                return `
                    <div class="conversation-message user">
                        <div class="message-content">${this.escapeHtml(msg.content)}</div>
                    </div>
                `;
            } else if (msg.role === 'assistant') {
                return `
                    <div class="conversation-message assistant">
                        <div class="message-content">${msg.content}</div>
                        ${msg.insights && msg.insights.length > 0 ? `
                            <div class="supporting-insights">
                                <small>Supporting insights:</small>
                                <ul>
                                    ${msg.insights.map(i => `<li>${i}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                `;
            } else if (msg.role === 'error') {
                return `
                    <div class="conversation-message error">
                        <div class="message-content">&#9888; ${this.escapeHtml(msg.content)}</div>
                    </div>
                `;
            }
            return '';
        }).join('');
    },

    /**
     * Render conversation (update just the conversation area)
     */
    renderConversation() {
        const conversationEl = document.getElementById('ai-conversation');
        if (conversationEl) {
            conversationEl.innerHTML = this.renderConversationContent();
            conversationEl.scrollTop = conversationEl.scrollHeight;
        }
    },

    /**
     * Handle ask button click
     */
    handleAsk() {
        const input = document.getElementById('ai-question-input');
        if (input && input.value.trim()) {
            this.askQuestion(input.value.trim());
            input.value = '';
        }
    },

    /**
     * Ask an example question
     */
    askExample(question) {
        const input = document.getElementById('ai-question-input');
        if (input) {
            input.value = question;
        }
        this.askQuestion(question);
    },

    /**
     * Set loading state
     */
    setLoading(loading) {
        if (!this.container) return;

        if (loading) {
            this.container.innerHTML = `
                <div class="ai-agent-loading">
                    <div class="loading-spinner"></div>
                    <p>Analyzing simulation results...</p>
                </div>
            `;
        }
    },

    /**
     * Render error state
     */
    renderError(message) {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="ai-agent-error">
                <div class="error-icon">&#9888;</div>
                <p>Analysis failed: ${this.escapeHtml(message)}</p>
                <button class="btn btn-secondary" onclick="AIAgent.analyze()">
                    Try Again
                </button>
            </div>
        `;
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Clear analysis
     */
    clear() {
        this.analysis = null;
        this.conversationHistory = [];
        this.render();
    },

    // ==========================================
    // AI MODEL FEEDBACK SYSTEM
    // ==========================================

    /**
     * Find equilibrium parameters for the model
     */
    async findEquilibrium(targetStocks = null) {
        if (!this.model) {
            this.showFeedbackMessage('No model loaded', 'error');
            return null;
        }

        this.showFeedbackLoading('Finding equilibrium parameters...');

        try {
            const response = await OpenRouterUI.request('/api/llm/find-equilibrium', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: {...this.model,id:this.model.id||'draft'},
                    target_stocks: targetStocks,
                    max_iterations: 100
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Equilibrium search failed');
            }

            const result = await response.json();
            this.renderEquilibriumResult(result);
            return result;

        } catch (error) {
            this.showFeedbackMessage(`Equilibrium search failed: ${error.message}`, 'error');
            return null;
        }
    },

    /**
     * Fit model to historical data
     */
    async fitToData(historicalData, timePoints) {
        if (!this.model) {
            this.showFeedbackMessage('No model loaded', 'error');
            return null;
        }

        this.showFeedbackLoading('Fitting model to data...');

        try {
            const response = await OpenRouterUI.request('/api/llm/fit-to-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: {...this.model,id:this.model.id||'draft'},
                    historical_data: historicalData,
                    time_points: timePoints,
                    max_iterations: 200
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Data fitting failed');
            }

            const result = await response.json();
            this.renderFitResult(result);
            return result;

        } catch (error) {
            this.showFeedbackMessage(`Data fitting failed: ${error.message}`, 'error');
            return null;
        }
    },

    /**
     * Get AI suggestions to refine model based on feedback
     */
    async refineModel(feedback) {
        if (!this.model || !this.results) {
            this.showFeedbackMessage('Run a simulation first', 'error');
            return null;
        }

        this.showFeedbackLoading('Getting AI suggestions...');

        try {
            // Keep the server refinement flow; personal free keys use modification.
            const personalKey = OpenRouterUI.hasKey();
            const response = await OpenRouterUI.request(personalKey ? '/api/llm/modify' : '/api/llm/refine-model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: {...this.model,id:this.model.id||'draft'},
                    ...(personalKey ? {
                        modification: `Refine this model using this feedback: ${feedback}\nSimulation results for context: ${JSON.stringify(this.results)}`
                    } : {
                        simulation_results: this.results,
                        feedback: feedback
                    })
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Refinement failed');
            }

            const payload = await response.json();
            const result = personalKey ? {
                success: true,
                suggestions: [],
                modified_model: payload,
                explanation: 'A free model proposed a revised model using your feedback and simulation results. Review it before applying; AI output may contain errors.'
            } : payload;
            this.renderRefinementResult(result);
            return result;

        } catch (error) {
            this.showFeedbackMessage(`Refinement failed: ${error.message}`, 'error');
            return null;
        }
    },

    /**
     * Render equilibrium search result
     */
    renderEquilibriumResult(result) {
        const container = document.getElementById('feedback-result');
        if (!container) return;

        let html = `<div class="feedback-result ${result.found ? 'success' : 'partial'}">`;
        html += `<h4>${result.found ? '✓ Equilibrium Found!' : '⚠ Partial Result'}</h4>`;
        html += `<p class="feedback-message">${result.message}</p>`;

        if (Object.keys(result.parameters).length > 0) {
            html += '<div class="feedback-params">';
            html += '<h5>Optimized Parameters:</h5>';
            html += '<ul>';
            for (const [param, value] of Object.entries(result.parameters)) {
                html += `<li><strong>${param}:</strong> ${typeof value === 'number' ? value.toFixed(4) : value}</li>`;
            }
            html += '</ul></div>';
        }

        if (Object.keys(result.equilibrium_values).length > 0) {
            html += '<div class="feedback-equilibrium">';
            html += '<h5>Equilibrium Values:</h5>';
            html += '<ul>';
            for (const [stock, value] of Object.entries(result.equilibrium_values)) {
                html += `<li><strong>${stock}:</strong> ${typeof value === 'number' ? value.toFixed(2) : value}</li>`;
            }
            html += '</ul></div>';
        }

        if (result.convergence_time > 0) {
            html += `<p class="convergence-time">Converges at t = ${result.convergence_time.toFixed(2)}</p>`;
        }

        html += `<button class="btn btn-primary" onclick="AIAgent.applyParameters(${JSON.stringify(result.parameters).replace(/"/g, '&quot;')})">
            Apply Parameters
        </button>`;
        html += '</div>';

        container.innerHTML = html;
    },

    /**
     * Render data fitting result
     */
    renderFitResult(result) {
        const container = document.getElementById('feedback-result');
        if (!container) return;

        const goodFit = result.r_squared > 0.8;
        let html = `<div class="feedback-result ${goodFit ? 'success' : result.success ? 'partial' : 'error'}">`;

        if (result.success) {
            html += `<h4>${goodFit ? '✓ Good Fit!' : '⚠ Fit Complete'}</h4>`;
            html += `<p class="feedback-message">${result.message}</p>`;

            html += '<div class="feedback-metrics">';
            html += `<div class="metric"><span class="metric-label">R²</span><span class="metric-value ${goodFit ? 'good' : ''}">${result.r_squared.toFixed(4)}</span></div>`;
            html += `<div class="metric"><span class="metric-label">RMSE</span><span class="metric-value">${result.rmse.toFixed(4)}</span></div>`;
            html += '</div>';

            if (Object.keys(result.parameters).length > 0) {
                html += '<div class="feedback-params">';
                html += '<h5>Fitted Parameters:</h5>';
                html += '<ul>';
                for (const [param, value] of Object.entries(result.parameters)) {
                    html += `<li><strong>${param}:</strong> ${typeof value === 'number' ? value.toFixed(4) : value}</li>`;
                }
                html += '</ul></div>';
            }

            html += `<button class="btn btn-primary" onclick="AIAgent.applyParameters(${JSON.stringify(result.parameters).replace(/"/g, '&quot;')})">
                Apply Fitted Parameters
            </button>`;
        } else {
            html += '<h4>✗ Fitting Failed</h4>';
            html += `<p class="feedback-message">${result.message}</p>`;
        }

        html += '</div>';
        container.innerHTML = html;
    },

    /**
     * Render model refinement result
     */
    renderRefinementResult(result) {
        const container = document.getElementById('feedback-result');
        if (!container) return;

        let html = `<div class="feedback-result ${result.success ? 'success' : 'error'}">`;

        if (result.success) {
            html += '<h4>✓ AI Suggestions</h4>';
            html += `<p class="feedback-explanation">${result.explanation}</p>`;

            if (result.suggestions && result.suggestions.length > 0) {
                html += '<div class="feedback-suggestions">';
                html += '<h5>Suggested Changes:</h5>';
                result.suggestions.forEach((suggestion, i) => {
                    html += `<div class="suggestion-item">
                        <div class="suggestion-header">
                            <strong>${suggestion.parameter}</strong>
                            <span class="suggestion-change">
                                ${suggestion.current_value?.toFixed?.(4) ?? suggestion.current_value}
                                → ${suggestion.suggested_value?.toFixed?.(4) ?? suggestion.suggested_value}
                            </span>
                        </div>
                        <p class="suggestion-reason">${suggestion.reasoning}</p>
                    </div>`;
                });
                html += '</div>';
            }

            if (result.modified_model) {
                html += `<button class="btn btn-primary" onclick="AIAgent.applyModifiedModel()">
                    Apply All Suggestions
                </button>`;
                // Store modified model for later application
                this.pendingModifiedModel = result.modified_model;
            }
        } else {
            html += '<h4>✗ Refinement Failed</h4>';
            html += `<p class="feedback-message">${result.explanation}</p>`;
        }

        html += '</div>';
        container.innerHTML = html;
    },

    /**
     * Apply parameters to the current model
     */
    applyParameters(params) {
        if (!App || !App.model) return;

        for (const [param, value] of Object.entries(params)) {
            // Check if it's a stock initial value
            if (param.endsWith('_initial')) {
                const stockName = param.replace('_initial', '');
                const stock = App.model.stocks.find(s => s.name === stockName);
                if (stock) {
                    stock.initial_value = value;
                }
            } else {
                // Check variables
                const variable = App.model.variables.find(v => v.name === param);
                if (variable) {
                    variable.equation = String(value);
                }
            }
        }

        // Update canvas display
        if (typeof Canvas !== 'undefined') {
            Canvas.draw();
        }

        this.showFeedbackMessage('Parameters applied! Run simulation to see results.', 'success');
    },

    /**
     * Apply the modified model from refinement
     */
    applyModifiedModel() {
        if (!this.pendingModifiedModel || !App) return;

        // Update App.model with the modified model
        App.model = this.pendingModifiedModel;

        // Update UI
        if (typeof Canvas !== 'undefined') {
            Canvas.draw();
        }

        this.pendingModifiedModel = null;
        this.showFeedbackMessage('Model updated! Run simulation to see results.', 'success');
    },

    /**
     * Show feedback loading state
     */
    showFeedbackLoading(message) {
        const container = document.getElementById('feedback-result');
        if (container) {
            container.innerHTML = `
                <div class="feedback-loading">
                    <div class="loading-spinner"></div>
                    <p>${message}</p>
                </div>
            `;
        }
    },

    /**
     * Show feedback message
     */
    showFeedbackMessage(message, type = 'info') {
        const container = document.getElementById('feedback-result');
        if (container) {
            container.innerHTML = `
                <div class="feedback-message ${type}">
                    <p>${message}</p>
                </div>
            `;
        }
    },

    /**
     * Render the feedback panel (call this to add feedback UI to AI tab)
     */
    renderFeedbackPanel() {
        return `
            <div class="ai-section ai-feedback">
                <h3><span class="ai-icon">🎯</span> Model Feedback</h3>

                <div class="feedback-tools">
                    <!-- Find Equilibrium -->
                    <div class="feedback-tool">
                        <h4>Find Equilibrium</h4>
                        <p>Automatically adjust parameters to achieve steady state.</p>
                        <button class="btn btn-secondary" onclick="AIAgent.findEquilibrium()">
                            ⚖️ Find Equilibrium
                        </button>
                    </div>

                    <!-- Refine Model -->
                    <div class="feedback-tool">
                        <h4>Refine Model</h4>
                        <p>Describe what you want to change:</p>
                        <div class="refine-input-container">
                            <input type="text"
                                   id="refine-feedback-input"
                                   class="refine-feedback-input"
                                   placeholder="e.g., 'Population should peak higher'">
                            <button class="btn btn-secondary" onclick="AIAgent.handleRefine()">
                                ✨ Get Suggestions
                            </button>
                        </div>
                    </div>

                    <!-- Fit to Data -->
                    <div class="feedback-tool">
                        <h4>Fit to Data</h4>
                        <p>Enter historical data (one value per line):</p>
                        <div class="fit-data-container">
                            <select id="fit-variable-select" class="fit-variable-select">
                                ${this.getVariableOptions()}
                            </select>
                            <textarea id="fit-data-input"
                                      class="fit-data-input"
                                      placeholder="Time,Value&#10;0,100&#10;10,150&#10;20,200"
                                      rows="4"></textarea>
                            <button class="btn btn-secondary" onclick="AIAgent.handleFitData()">
                                📈 Fit Model
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Results container -->
                <div id="feedback-result" class="feedback-result-container"></div>
            </div>
        `;
    },

    /**
     * Get options for variable select
     */
    getVariableOptions() {
        if (!this.model) return '<option value="">No model</option>';

        let options = '';
        this.model.stocks.forEach(stock => {
            options += `<option value="${stock.name}">${stock.name}</option>`;
        });
        return options || '<option value="">No variables</option>';
    },

    /**
     * Handle refine button click
     */
    handleRefine() {
        const input = document.getElementById('refine-feedback-input');
        if (input && input.value.trim()) {
            this.refineModel(input.value.trim());
        }
    },

    /**
     * Handle fit data button click
     */
    handleFitData() {
        const varSelect = document.getElementById('fit-variable-select');
        const dataInput = document.getElementById('fit-data-input');

        if (!varSelect || !dataInput) return;

        const varName = varSelect.value;
        const dataText = dataInput.value.trim();

        if (!varName || !dataText) {
            this.showFeedbackMessage('Please select a variable and enter data', 'error');
            return;
        }

        // Parse CSV data
        const lines = dataText.split('\n').filter(l => l.trim());
        const timePoints = [];
        const values = [];

        for (const line of lines) {
            const parts = line.split(',').map(p => parseFloat(p.trim()));
            if (parts.length >= 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
                timePoints.push(parts[0]);
                values.push(parts[1]);
            }
        }

        if (timePoints.length < 2) {
            this.showFeedbackMessage('Need at least 2 data points (Time,Value format)', 'error');
            return;
        }

        const historicalData = { [varName]: values };
        this.fitToData(historicalData, timePoints);
    }
};
