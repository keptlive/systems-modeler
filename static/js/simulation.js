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
        return { start, end, dt, integration_method: ts.integration_method || 'euler', random_seed:ts.random_seed ?? null };
    },

    init() {
        this.chartContainer = document.getElementById('chart-container');
        this.resultsContent = document.getElementById('results-content');
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

        let snapshot, generation;
        try {
            this.clear();
            snapshot = JSON.stringify(App.modelSnapshot());
            generation = this.generation;
            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: JSON.parse(snapshot), time_settings: this.getTimeSettings() })
            });

            if (generation !== this.generation || snapshot !== JSON.stringify(App.modelSnapshot())) {
                App.showToast('The model changed while this run was computing. Run the current inputs again.', 'info');
                return;
            }
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Simulation failed');
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
            console.error("Simulation error:", error);
            if (this.resultsContent) {
                this.resultsContent.innerHTML = `
                    <p class="error" style="color: var(--accent-secondary);">
                        Simulation error: ${App.escapeHtml(error.message)}
                    </p>
                `;
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

    async acceptResults(results) {
        this.generation = (this.generation || 0) + 1;
        const generation = this.generation;
        const model = JSON.parse(JSON.stringify(App.modelSnapshot()));
        this.resultModel = model;
        this.lastError=null;
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
            Charts.setResults(this.results);
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
            variables:(model.variables || []).map(({id,name,equation})=>({id,name,equation})),
            tables:model.tables || [], time_settings:model.time_settings
        });
    },

    invalidateIfChanged() {
        if (this.results && this.resultModel && this.modelSignature(this.resultModel) !== this.modelSignature(App.model)) {
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
            <div style="margin-top: 0.5rem; font-size: 0.8rem;">
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

        html += '</div>';
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
