/**
 * Systems Modeler - Simulation & Visualization
 * Runs simulations and displays results with D3.js charts
 */
const Simulation = {
    results: null,
    chart: null,

    // Chart configuration
    margin: { top: 20, right: 100, bottom: 40, left: 60 },
    colors: d3.schemeCategory10,

    /**
     * Get simulation time settings from model
     */
    getTimeSettings() {
        const ts = App.model.time_settings || {};
        const start = ts.start ?? 0;
        const end = ts.end ?? 100;
        const dt = ts.dt ?? 0.25;
        return { start, end, dt, discrete_period:ts.discrete_period ?? null, integration_method: ts.integration_method || 'euler', random_seed:ts.random_seed ?? null, rtol:ts.rtol ?? 1e-6, atol:ts.atol ?? 1e-9 };
    },

    init() {
        this.chartContainer = document.getElementById('chart-container');
        this.resultsContent = document.getElementById('results-content');
        if (!this.failureDownloadBound) {
            document.addEventListener('click', event => {
                if (event.target.closest('[data-simulation-action="download-failure"]')) this.downloadFailureReport();
            });
            this.failureDownloadBound = true;
        }
    },

    /**
     * Run simulation on current model
     */
    async run() {
        if (App.model.stocks.length === 0 && App.model.flows.length === 0 && App.model.variables.length === 0) {
            alert('No model to simulate. Add some stocks and flows first.');
            return;
        }

        // Get both desktop and mobile buttons
        const btn = document.getElementById('btn-simulate');
        const mobileBtn = document.getElementById('mobile-simulate-btn');

        // Disable both buttons during simulation
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Running...';
        }
        if (mobileBtn) {
            mobileBtn.disabled = true;
            mobileBtn.textContent = '⏳ Running...';
        }

        let snapshot, generation, requestedSettings;
        try {
            this.clear();
            snapshot = JSON.stringify(App.modelSnapshot());
            generation = this.generation;
            requestedSettings = this.getTimeSettings();
            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: JSON.parse(snapshot), time_settings: requestedSettings })
            });

            if (generation !== this.generation || snapshot !== JSON.stringify(App.modelSnapshot())) {
                App.showToast('The model changed while this run was computing. Run the current inputs again.', 'info');
                return;
            }
            if (!response.ok) {
                const error = await response.json();
                const failure = new Error(typeof error.detail === 'string' ? error.detail : 'Invalid simulation inputs');
                failure.diagnostics = error.failure || null;
                throw failure;
            }

            const result = await response.json();
            if (generation !== this.generation || snapshot !== JSON.stringify(App.modelSnapshot())) {
                App.showToast('The model changed while this run was computing. Run the current inputs again.', 'info');
                return;
            }
            await this.acceptResults(result);

        } catch (error) {
            if (generation !== this.generation || snapshot !== JSON.stringify(App.modelSnapshot())) return;
            this.lastError=error.message;
            this.lastFailure=error.diagnostics || null;
            this.failureModel=JSON.parse(snapshot);
            this.failureSettings=requestedSettings;
            console.error("Simulation error:", error);
            if (this.resultsContent) {
                this.resultsContent.innerHTML = this.failureHTML();
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<span class="icon-simulate">Run</span>';
            }
            if (mobileBtn) {
                mobileBtn.disabled = false;
                mobileBtn.textContent = '▶ Run';
            }
            if (App.isMobile && (this.results||this.lastError)) {
                App.openSlidePanel('results');
            }
        }
    },

    failureHTML() {
        const escape = value => App.escapeHtml(String(value ?? ''));
        const failure = this.lastFailure || {};
        const roots = failure.root_errors || [];
        const title = failure.category === 'capacity' ? 'Run exceeds its budget' : 'Run stopped';
        const when = Number.isFinite(failure.time) ? ` at t = ${failure.time}` : '';
        const messages = {division_by_zero:'Division by zero', non_finite:'The equation produced a non-finite value', domain_error:'The equation left its valid numerical domain'};
        const rootMessage = root => messages[root.code] || root.message;
        const causes = roots.length ? roots.map(root => `<li><strong>${escape(root.element || (root.elements || []).join(' → '))}</strong><p>${escape(rootMessage(root))}</p>${root.equation ? `<code>${escape(root.equation)}</code>` : ''}</li>`).join('') : `<li>${escape(this.lastError || 'Simulation failed')}</li>`;
        const blocked = failure.blocked_errors || [];
        const dependents = blocked.length ? `<details><summary>${blocked.length} dependent ${blocked.length===1?'value is':'values are'} blocked</summary><ul>${blocked.map(row=>`<li>${escape(row.element)} waits for ${escape(row.waiting_for)}.</li>`).join('')}</ul></details>` : '';
        const download = this.failureModel ? '<div class="failure-actions"><button type="button" class="btn btn-secondary" data-simulation-action="download-failure">Download failure report</button><small>Includes the exact inputs and settings for this run.</small></div>' : '';
        return `<section class="simulation-failure" role="alert"><h3>${escape(title+when)}</h3><ul>${causes}</ul>${dependents}<p class="failure-help">Inspect the named inputs and equations before running again.</p>${download}</section>`;
    },

    failureReport() {
        if (!this.failureModel || !this.lastError) return null;
        return JSON.parse(JSON.stringify({
            format_version: 1,
            model: this.failureModel,
            settings: this.lastFailure?.reproduction?.settings || this.failureSettings,
            failure: this.lastFailure || {message:this.lastError},
        }));
    },

    downloadFailureReport() {
        const report = this.failureReport();
        if (!report) return;
        const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], {type:'application/json'}));
        const link = document.createElement('a');
        link.href = url; link.download = 'model-failure-report.json';
        document.body.appendChild(link); link.click(); link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    },

    async acceptResults(results) {
        this.generation = (this.generation || 0) + 1;
        const generation = this.generation;
        const model = JSON.parse(JSON.stringify(App.modelSnapshot()));
        this.resultModel = model;
        this.lastError=null;
        this.lastFailure=null;
        this.failureModel=null;
        this.failureSettings=null;
        this.results = results;
        this.displayResults();
        let receipt = document.getElementById('run-seed-receipt');
        if (!receipt) {
            receipt = document.createElement('p'); receipt.id = 'run-seed-receipt';
            receipt.className = 'run-seed-receipt';
            document.querySelector('.results-tabs')?.before(receipt);
        }
        receipt.hidden = results.random_seed == null;
        if (!receipt.hidden) receipt.textContent = `Random seed: ${results.random_seed} · Use this in Settings to replay.`;

        // Update advanced charts module
        if (typeof Charts !== 'undefined') {
            Charts.setResults(this.results, model);
            Charts.render();
            const mobileContainer = document.getElementById('chart-container-mobile');
            if (mobileContainer) {
                const originalContainer = Charts.container;
                Charts.container = mobileContainer;
                Charts.render();
                Charts.container = originalContainer;
            }
        } else {
            this.renderChart();
        }

        // Update analytics module
        if (typeof Analytics !== 'undefined') {
            await Analytics.setResults(this.results);
            if (generation !== this.generation) return;
            if (this.modelSignature(model) !== this.modelSignature(App.model)) {
                this.clear('Inputs changed. Run the current model to see results.');
                return;
            }
            Analytics.render();
        }

        // Update AI agent module
        if (typeof AIAgent !== 'undefined') {
            AIAgent.setContext(model, results);
            AIAgent.render();
        }

    },

    modelSignature(model) {
        // Moving nodes or changing the title does not change a trajectory.
        return JSON.stringify({
            stocks:(model.stocks || []).map(({id,name,equation,initial_value})=>({id,name,equation,initial_value})),
            flows:(model.flows || []).map(({id,name,equation,from_stock,to_stock})=>({id,name,equation,from_stock,to_stock})),
            variables:(model.variables || []).map(({id,name,equation,role})=>({id,name,equation,role:role || "auxiliary"})),
            tables:model.tables || [], time_settings:model.time_settings
        });
    },

    invalidateIfChanged() {
        const baseline = this.results ? this.resultModel : (this.lastError ? this.failureModel : null);
        if (baseline && this.modelSignature(baseline) !== this.modelSignature(App.model)) {
            this.clear('Inputs changed. Run the current model to see results.');
        }
    },

    /**
     * Clear results
     */
    clear(message = 'Run a simulation to see results') {
        this.generation = (this.generation || 0) + 1;
        this.results = null;
        this.resultModel = null;
        this.lastError=null;
        this.lastFailure=null;
        this.failureModel=null;
        this.failureSettings=null;
        const receipt = document.getElementById('run-seed-receipt');
        if (receipt) receipt.hidden = true;
        document.querySelector('.mobile-results-container .run-seed-receipt')?.remove();
        document.getElementById('chart-container-mobile')?.replaceChildren();
        document.getElementById('var-chips-mobile')?.replaceChildren();
        const mobileSummary = document.getElementById('results-summary-mobile');
        if (mobileSummary) mobileSummary.textContent = message;
        if (this.resultsContent) {
            this.resultsContent.innerHTML = `<p class="no-results">${App.escapeHtml(message)}</p>`;
        }
        document.getElementById('chart-variables')?.replaceChildren();
        if (this.chartContainer) {
            this.chartContainer.innerHTML = '';
        }
        if (typeof Charts !== 'undefined') {
            Charts.results = null;
            if (Charts.container) Charts.container.innerHTML = '';
        }
        if (typeof Analytics !== 'undefined') {
            Analytics.requestVersion = (Analytics.requestVersion || 0) + 1;
            Analytics.results = null;
            Analytics.statistics = null;
            Analytics.error = null;
            Analytics.render();
        }
        if (typeof AIAgent !== 'undefined') {
            AIAgent.clear();
        }
    },

    /**
     * Display results summary
     */
    reportHTML(results) {
        const reports = Object.entries(results?.report_values || {});
        if (!reports.length) return '';
        return '<section class="run-reports" aria-label="Report outputs"><h3>Report outputs</h3><p>Read-only results at the final saved time.</p><dl>' + reports.map(([name, values]) =>
            '<div><dt>' + App.escapeHtml(name) + '</dt><dd>' + App.escapeHtml(String(values[values.length - 1] ?? '')) + '</dd></div>'
        ).join('') + '</dl></section>';
    },

    displayResults() {
        if (!this.results || !this.chartContainer) return;

        const varNames = Object.keys(this.results.values);
        const time = this.results.time;
        const timeSteps = time.length;
        const startTime = time[0];
        const endTime = time[time.length - 1];
        const dt = this.resultModel?.time_settings?.dt ?? (timeSteps > 1 ? time[1] - time[0] : 0);

        let html = `
            <p><strong>Time:</strong> ${startTime} → ${endTime} (${timeSteps} pts, nominal dt=${dt})</p>
            <p><strong>Variables:</strong> ${varNames.length}</p>
            <details class="final-values"><summary>Final values · ${varNames.length} series</summary><div class="final-values-list">
        `;

        varNames.forEach((name, i) => {
            const values = this.results.values[name];
            const finalValue = values[values.length - 1];
            const color = this.colors[i % this.colors.length];
            html += `
                <div style="display: flex; align-items: center; gap: 0.5rem; margin: 0.25rem 0;">
                    <span style="width: 10px; height: 10px; background: ${color}; border-radius: 50%;"></span>
                    <span>${App.escapeHtml(name)}: ${this.formatNumber(finalValue)}</span>
                </div>
            `;
        });

        html += '</div></details>' + this.reportHTML(this.results);
        if (this.resultsContent) this.resultsContent.innerHTML = html;
    },

    /**
     * Render time series chart
     */
    renderChart() {
        if (!this.results || !this.chartContainer) return;

        this.chartContainer.innerHTML = '';

        const containerRect = this.chartContainer.getBoundingClientRect();
        const width = containerRect.width;
        const height = containerRect.height || 300;

        const innerWidth = width - this.margin.left - this.margin.right;
        const innerHeight = height - this.margin.top - this.margin.bottom;

        const svg = d3.select(this.chartContainer)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const g = svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        const time = this.results.time;
        const varNames = Object.keys(this.results.values);

        const xScale = d3.scaleLinear()
            .domain([time[0], time[time.length - 1]])
            .range([0, innerWidth]);

        let yMin = Infinity, yMax = -Infinity;
        varNames.forEach(name => {
            const values = this.results.values[name];
            values.forEach(v => {
                if (isFinite(v)) {
                    yMin = Math.min(yMin, v);
                    yMax = Math.max(yMax, v);
                }
            });
        });

        const yPadding = (yMax - yMin) * 0.1 || 1;
        const yScale = d3.scaleLinear()
            .domain([yMin - yPadding, yMax + yPadding])
            .range([innerHeight, 0]);

        const xAxis = d3.axisBottom(xScale).ticks(6);
        const yAxis = d3.axisLeft(yScale).ticks(6);

        g.append('g')
            .attr('class', 'axis x-axis')
            .attr('transform', `translate(0,${innerHeight})`)
            .call(xAxis);

        g.append('g')
            .attr('class', 'axis y-axis')
            .call(yAxis);

        g.append('text')
            .attr('class', 'axis-label')
            .attr('x', innerWidth / 2)
            .attr('y', innerHeight + 35)
            .attr('fill', 'var(--text-secondary)')
            .attr('text-anchor', 'middle')
            .attr('font-size', '11px')
            .text('Time');

        const line = d3.line()
            .x((d, i) => xScale(time[i]))
            .y(d => yScale(d))
            .defined(d => isFinite(d));

        varNames.forEach((name, i) => {
            const values = this.results.values[name];
            const color = this.colors[i % this.colors.length];

            g.append('path')
                .datum(values)
                .attr('class', 'chart-line')
                .attr('d', line)
                .attr('stroke', color);
        });

        const legend = svg.append('g')
            .attr('class', 'legend')
            .attr('transform', `translate(${width - this.margin.right + 10}, ${this.margin.top})`);

        varNames.forEach((name, i) => {
            const color = this.colors[i % this.colors.length];
            const y = i * 18;

            legend.append('rect')
                .attr('x', 0)
                .attr('y', y)
                .attr('width', 12)
                .attr('height', 12)
                .attr('fill', color);

            legend.append('text')
                .attr('class', 'chart-legend')
                .attr('x', 16)
                .attr('y', y + 10)
                .text(this.truncateLabel(name, 10));
        });
    },

    formatNumber(n) {
        if (!isFinite(n)) return 'N/A';
        if (Math.abs(n) < 0.01 || Math.abs(n) >= 10000) {
            return n.toExponential(2);
        }
        return n.toFixed(2);
    },

    truncateLabel(text, maxLen) {
        if (text.length <= maxLen) return text;
        return text.substring(0, maxLen - 1) + '...';
    }
};
