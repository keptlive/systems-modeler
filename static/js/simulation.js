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
     * Calculate simulation time range from step count. Returns {start, end, dt}.
     */
    getTimeSettings(steps) {
        const dt = App.model.time_settings?.dt || 0.1;
        const start = App.model.time_settings?.start || 0;
        const end = start + (steps * dt);
        return { start, end, dt };
    },

    init() {
        this.chartContainer = document.getElementById('chart-container');
        this.resultsContent = document.getElementById('results-content');
    },

    /**
     * Run simulation on current model
     */
    async run() {
        // Get steps from input
        const stepsInput = document.getElementById("sim-steps");
        const steps = stepsInput ? parseInt(stepsInput.value) || 100 : 100;
        if (App.model.stocks.length === 0 && App.model.flows.length === 0) {
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

        try {
            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: App.model, time_settings: this.getTimeSettings(steps) })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Simulation failed');
            }

            this.results = await response.json();
            this.displayResults();

            // Update advanced charts module
            if (typeof Charts !== 'undefined') {
                Charts.setResults(this.results);
                // Render in desktop container
                Charts.render();
                // Also render in mobile container if it exists
                const mobileContainer = document.getElementById('chart-container-mobile');
                if (mobileContainer) {
                    const originalContainer = Charts.container;
                    Charts.container = mobileContainer;
                    Charts.render();
                    Charts.container = originalContainer;
                }
            } else {
                // Fallback to basic chart
                this.renderChart();
            }

            // Update analytics module
            if (typeof Analytics !== 'undefined') {
                await Analytics.setResults(this.results);
                Analytics.render();
            }

            // Update AI agent module
            if (typeof AIAgent !== 'undefined') {
                AIAgent.setContext(App.model, this.results);
                AIAgent.render();
            }

        } catch (error) {
            console.error('Simulation error:', error);
            this.resultsContent.innerHTML = `
                <p class="error" style="color: var(--accent-secondary);">
                    Simulation error: ${error.message}
                </p>
            `;
        } finally {
            // Re-enable both buttons
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<span class="icon-simulate">Run</span>';
            }
            if (mobileBtn) {
                mobileBtn.disabled = false;
                mobileBtn.textContent = '▶ Run';
            }

            // On mobile, show results panel after simulation completes
            if (App.isMobile && this.results) {
                App.openSlidePanel('results');
            }
        }
    },

    /**
     * Clear results
     */
    clear() {
        this.results = null;
        this.resultsContent.innerHTML = '<p class="no-results">Run a simulation to see results</p>';
        this.chartContainer.innerHTML = '';

        // Clear advanced modules
        if (typeof Charts !== 'undefined') {
            Charts.results = null;
            Charts.container.innerHTML = '';
        }
        if (typeof Analytics !== 'undefined') {
            Analytics.results = null;
            Analytics.statistics = null;
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
        if (!this.results) return;

        const varNames = Object.keys(this.results.values);
        const time = this.results.time;
        const timeSteps = time.length;
        const startTime = time[0];
        const endTime = time[time.length - 1];
        const dt = timeSteps > 1 ? (time[1] - time[0]).toFixed(2) : 0;

        let html = `
            <p><strong>Time:</strong> ${startTime} → ${endTime.toFixed(1)} (${timeSteps} pts, dt=${dt})</p>
            <p><strong>Variables:</strong> ${varNames.length}</p>
            <div style="margin-top: 0.5rem; font-size: 0.8rem;">
        `;

        // Show final values
        varNames.forEach((name, i) => {
            const values = this.results.values[name];
            const finalValue = values[values.length - 1];
            const color = this.colors[i % this.colors.length];
            html += `
                <div style="display: flex; align-items: center; gap: 0.5rem; margin: 0.25rem 0;">
                    <span style="width: 10px; height: 10px; background: ${color}; border-radius: 50%;"></span>
                    <span>${name}: ${this.formatNumber(finalValue)}</span>
                </div>
            `;
        });

        html += '</div>';
        this.resultsContent.innerHTML = html;
    },

    /**
     * Render time series chart
     */
    renderChart() {
        if (!this.results) return;

        // Clear previous chart
        this.chartContainer.innerHTML = '';

        const containerRect = this.chartContainer.getBoundingClientRect();
        const width = containerRect.width;
        const height = containerRect.height || 300;

        const innerWidth = width - this.margin.left - this.margin.right;
        const innerHeight = height - this.margin.top - this.margin.bottom;

        // Create SVG
        const svg = d3.select(this.chartContainer)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const g = svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        // Prepare data
        const time = this.results.time;
        const varNames = Object.keys(this.results.values);

        // Calculate scales
        const xScale = d3.scaleLinear()
            .domain([time[0], time[time.length - 1]])
            .range([0, innerWidth]);

        // Find min/max across all variables
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

        // Add padding to y range
        const yPadding = (yMax - yMin) * 0.1 || 1;
        const yScale = d3.scaleLinear()
            .domain([yMin - yPadding, yMax + yPadding])
            .range([innerHeight, 0]);

        // Draw axes
        const xAxis = d3.axisBottom(xScale).ticks(6);
        const yAxis = d3.axisLeft(yScale).ticks(6);

        g.append('g')
            .attr('class', 'axis x-axis')
            .attr('transform', `translate(0,${innerHeight})`)
            .call(xAxis);

        g.append('g')
            .attr('class', 'axis y-axis')
            .call(yAxis);

        // X axis label
        g.append('text')
            .attr('class', 'axis-label')
            .attr('x', innerWidth / 2)
            .attr('y', innerHeight + 35)
            .attr('fill', 'var(--text-secondary)')
            .attr('text-anchor', 'middle')
            .attr('font-size', '11px')
            .text('Time');

        // Draw lines for each variable
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

        // Legend
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

    /**
     * Format number for display
     */
    formatNumber(n) {
        if (!isFinite(n)) return 'N/A';
        if (Math.abs(n) < 0.01 || Math.abs(n) >= 10000) {
            return n.toExponential(2);
        }
        return n.toFixed(2);
    },

    /**
     * Truncate label
     */
    truncateLabel(text, maxLen) {
        if (text.length <= maxLen) return text;
        return text.substring(0, maxLen - 1) + '...';
    }
};
