/**
 * Systems Modeler - Advanced Charts Module
 * Beautiful, interactive D3.js charts with multiple chart types,
 * zoom/pan, export, and animation support.
 */
const Charts = {
    // Chart configuration
    container: null,
    svg: null,
    results: null,
    previousRuns: [],

    margin: { top: 30, right: 120, bottom: 50, left: 70 },

    // Default options
    options: {
        type: 'line',          // line, area, stacked, phase
        scale: 'linear',       // linear, log
        showGrid: true,
        showLegend: true,
        animate: false,
        animationDuration: 2000,
        animationSpeed: 1,     // 1x, 2x, 4x speed multiplier
        showTooltip: true,
        showComparison: false,
        normalize: false,     // Optional scaling of each variable to 0-100%
        variables: {}          // { 'Population': { visible: true, color: '#4CAF50' } }
    },

    // Animation state
    animationFrame: null,
    animationProgress: 0,
    isAnimating: false,

    // Color palette
    colors: [
        '#4CAF50', '#2196F3', '#FF9800', '#E91E63', '#9C27B0',
        '#00BCD4', '#FFEB3B', '#795548', '#607D8B', '#8BC34A'
    ],

    variableKey(name) {
        return 'v-' + Array.from(name, character => character.codePointAt(0).toString(16)).join('-');
    },

    /**
     * Initialize charts module
     */
    init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Chart container not found:', containerId);
            return;
        }
    },

    /**
     * Set simulation results
     */
    setResults(results, model = null) {
        this.results = results;

        // Clear old variable options when loading new results
        this.options.variables = {};

        // Initialize variable options if not set
        if (results && results.values) {
            const varNames = Object.keys(results.values);
            const stockNames = new Set((model?.stocks || []).map(stock => stock.name));
            const startWithStocks = varNames.length > 24 && varNames.some(name => stockNames.has(name));
            varNames.forEach((name, i) => {
                if (!this.options.variables[name]) {
                    this.options.variables[name] = {
                        visible: !startWithStocks || stockNames.has(name),
                        color: this.colors[i % this.colors.length]
                    };
                }
            });
        }
    },

    /**
     * Save current run for comparison
     */
    saveRun(label = null) {
        if (!this.results) return;

        this.previousRuns.push({
            label: label || `Run ${this.previousRuns.length + 1}`,
            results: JSON.parse(JSON.stringify(this.results)),
            timestamp: new Date().toISOString()
        });
    },

    /**
     * Clear previous runs
     */
    clearPreviousRuns() {
        this.previousRuns = [];
    },

    /**
     * Update chart options
     */
    setOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
        if (this.results) {
            this.render();
        }
    },

    /**
     * Toggle variable visibility
     */
    toggleVariable(name) {
        if (this.options.variables[name]) {
            this.options.variables[name].visible = !this.options.variables[name].visible;
            this.render();
            this.onSelectionChanged?.();
        }
    },

    selectVariables(names) {
        const selected = new Set(names);
        for (const [name, option] of Object.entries(this.options.variables)) {
            option.visible = selected.has(name);
        }
        this.render();
        this.onSelectionChanged?.();
    },

    filterSeries(names, query) {
        const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
        return names.filter(name => terms.every(term => name.toLocaleLowerCase().includes(term)));
    },

    /**
     * Set variable color
     */
    setVariableColor(name, color) {
        if (this.options.variables[name]) {
            this.options.variables[name].color = color;
            this.render();
        }
    },

    /**
     * Main render function
     */
    render() {
        if (!this.container || !this.results) return;

        // Clear previous chart
        this.container.innerHTML = '';

        switch (this.options.type) {
            case 'area':
                this.renderAreaChart();
                break;
            case 'stacked':
                this.renderStackedAreaChart();
                break;
            case 'phase':
                this.renderPhaseChart();
                break;
            case 'line':
            default:
                this.renderLineChart();
                break;
        }
    },

    /**
     * Get chart dimensions
     */
    getDimensions() {
        const rect = this.container.getBoundingClientRect();
        // :empty hides the plot while render clears its old SVG. Measure the
        // parent as a fallback rather than creating a scaled-down 600px chart.
        const width = rect.width || this.container.parentElement.clientWidth || 600;
        const height = rect.height || parseFloat(getComputedStyle(this.container).height) || 350;
        this.margin = {top:24, right:width < 500 ? 16 : width < 800 ? 148 : 200, bottom:44, left:68};

        return {
            width,
            height,
            innerWidth: width - this.margin.left - this.margin.right,
            innerHeight: height - this.margin.top - this.margin.bottom
        };
    },

    /**
     * Get visible variables
     */
    getVisibleVariables() {
        return Object.entries(this.options.variables)
            .filter(([_, opt]) => opt.visible)
            .map(([name, _]) => name);
    },


    /**
     * Get normalization info for each variable (min, max, range)
     */
    getNormalizationInfo(values) {
        const info = {};
        Object.keys(values).forEach(name => {
            const vals = values[name].filter(v => isFinite(v));
            if (vals.length > 0) {
                const min = Math.min(...vals);
                const max = Math.max(...vals);
                info[name] = { min, max, range: max - min || 1 };
            } else {
                info[name] = { min: 0, max: 1, range: 1 };
            }
        });
        return info;
    },

    /**
     * Normalize a value to 0-100 range
     */
    normalizeValue(value, info) {
        if (!isFinite(value) || info.range === 0) return 50;
        return ((value - info.min) / info.range) * 100;
    },

    /**
     * Create scales
     */
    createScales(dim, time, values) {
        const visibleVars = this.getVisibleVariables();

        // X scale (time)
        const xScale = d3.scaleLinear()
            .domain([time[0], time[time.length - 1]])
            .range([0, dim.innerWidth]);

        // Y scale
        let yMin = Infinity, yMax = -Infinity;
        visibleVars.forEach(name => {
            if (values[name]) {
                values[name].forEach(v => {
                    if (isFinite(v)) {
                        yMin = Math.min(yMin, v);
                        yMax = Math.max(yMax, v);
                    }
                });
            }
        });

        // Handle edge cases
        if (!isFinite(yMin)) yMin = 0;
        if (!isFinite(yMax)) yMax = 1;
        if (yMin === yMax) {
            yMin -= 1;
            yMax += 1;
        }

        const yPadding = (yMax - yMin) * 0.1;

        const yScale = this.options.scale === 'log' && yMin > 0
            ? d3.scaleLog()
                .domain([Math.max(yMin, 0.001), yMax])
                .range([dim.innerHeight, 0])
            : d3.scaleLinear()
                .domain([yMin - yPadding, yMax + yPadding])
                .range([dim.innerHeight, 0]);

        return { xScale, yScale };
    },

    /**
     * Create SVG with zoom behavior
     */
    createSvg(dim) {
        this._plotId = 'plot-' + (this._plotSequence = (this._plotSequence || 0) + 1);
        const svg = d3.select(this.container)
            .append('svg')
            .attr('width', dim.width)
            .attr('height', dim.height)
            .attr('class', 'chart-svg');

        // Add defs for gradients and clip paths
        const defs = svg.append('defs');

        // Clip path for chart area
        defs.append('clipPath')
            .attr('id', this._plotId + '-clip')
            .append('rect')
            .attr('width', dim.innerWidth)
            .attr('height', dim.innerHeight);

        // Add gradients for each variable
        this.getVisibleVariables().forEach(name => {
            const color = this.options.variables[name]?.color || '#4CAF50';
            const gradient = defs.append('linearGradient')
                .attr('id', `gradient-${this._plotId}-${this.variableKey(name)}`)
                .attr('x1', '0%').attr('y1', '0%')
                .attr('x2', '0%').attr('y2', '100%');

            gradient.append('stop')
                .attr('offset', '0%')
                .attr('stop-color', color)
                .attr('stop-opacity', 0.4);

            gradient.append('stop')
                .attr('offset', '100%')
                .attr('stop-color', color)
                .attr('stop-opacity', 0.05);
        });

        return svg;
    },

    /**
     * Add axes to chart
     */
    addAxes(g, xScale, yScale, dim) {
        const xAxis = d3.axisBottom(xScale).ticks(Math.max(3, Math.floor(dim.innerWidth / 55)));
        const yAxis = d3.axisLeft(yScale).ticks(5).tickFormat(d3.format('~s'));

        // X axis
        g.append('g')
            .attr('class', 'axis x-axis')
            .attr('transform', `translate(0,${dim.innerHeight})`)
            .call(xAxis);

        // Y axis
        g.append('g')
            .attr('class', 'axis y-axis')
            .call(yAxis);

        // Grid lines
        if (this.options.showGrid) {
            g.append('g')
                .attr('class', 'grid x-grid')
                .attr('transform', `translate(0,${dim.innerHeight})`)
                .call(xAxis.tickSize(-dim.innerHeight).tickFormat(''))
                .selectAll('line')
                .attr('stroke', 'var(--border-color)')
                .attr('stroke-opacity', 0.3);

            g.append('g')
                .attr('class', 'grid y-grid')
                .call(yAxis.tickSize(-dim.innerWidth).tickFormat(''))
                .selectAll('line')
                .attr('stroke', 'var(--border-color)')
                .attr('stroke-opacity', 0.3);
        }

        // Axis labels
        g.append('text')
            .attr('class', 'axis-label')
            .attr('x', dim.innerWidth / 2)
            .attr('y', dim.innerHeight + 40)
            .attr('fill', 'var(--text-secondary)')
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .text('Time: ' + this.results.time[0] + ' → ' + this.results.time[this.results.time.length-1]);

        g.append('text')
            .attr('class', 'axis-label')
            .attr('transform', 'rotate(-90)')
            .attr('x', -dim.innerHeight / 2)
            .attr('y', -(this.margin.left - 14))
            .attr('fill', 'var(--text-secondary)')
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .text(this.options.normalize && this.options.type === 'line' ? 'Normalized (%)' : 'Value');
    },

    /**
     * Add interactive legend
     */
    addLegend(svg, dim) {
        if (dim.width < 500) return;
        if (!this.options.showLegend) return;

        const width = this.margin.right - 20;
        const legend = svg.append('foreignObject')
            .attr('x', dim.width - this.margin.right + 12).attr('y', this.margin.top)
            .attr('width', width).attr('height', Math.max(50,dim.innerHeight));
        const list = legend.append('xhtml:div').attr('class','chart-legend-list')
            .attr('role','group').attr('aria-label','Chart series');
        for (const [name,opt] of Object.entries(this.options.variables)) {
            const item = list.append('xhtml:button').attr('type','button')
                .attr('aria-pressed',String(opt.visible)).attr('title',name)
                .on('click',()=>{
                    this.toggleVariable(name);
                    [...this.container.querySelectorAll('.chart-legend-list button')].find(button=>button.title===name)?.focus();
                });
            item.append('xhtml:span').attr('class','legend-swatch')
                .style('border-color',opt.color).style('background',opt.visible ? opt.color : 'transparent');
            item.append('xhtml:span').text(name);
        }
    },

    /**
     * Add tooltip
     */
    addTooltip(svg, g, xScale, yScale, dim, time, values) {
        if (!this.options.showTooltip) return;

        const visibleVars = this.getVisibleVariables();

        // Vertical line
        const hoverLine = g.append('line')
            .attr('class', 'hover-line')
            .attr('y1', 0)
            .attr('y2', dim.innerHeight)
            .attr('stroke', 'var(--text-muted)')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '4,4')
            .style('opacity', 0);

        // Tooltip div
        let tooltip = d3.select(this.container).select('.chart-tooltip');
        if (tooltip.empty()) {
            tooltip = d3.select(this.container)
                .append('div')
                .attr('class', 'chart-tooltip')
                .style('opacity', 0);
        }

        // Hover dots
        const hoverDots = g.append('g').attr('class', 'hover-dots');
        visibleVars.forEach(name => {
            hoverDots.append('circle')
                .attr('class', `hover-dot-${this.variableKey(name)}`)
                .attr('r', 5)
                .attr('fill', this.options.variables[name]?.color || '#4CAF50')
                .attr('stroke', 'white')
                .attr('stroke-width', 2)
                .style('opacity', 0);
        });

        // Overlay for mouse tracking
        const overlay = g.append('rect')
            .attr('class', 'overlay')
            .attr('width', dim.innerWidth)
            .attr('height', dim.innerHeight)
            .attr('fill', 'transparent');

        const bisect = d3.bisector(d => d).left;

        // Unified handler for both mouse and touch
        const showTooltip = (event) => {
            const [mx] = d3.pointer(event);
            const x0 = xScale.invert(mx);
            const i = bisect(time, x0, 1);
            const i0 = Math.max(0, Math.min(i, time.length - 1));

            const t = time[i0];

            hoverLine
                .attr('x1', xScale(t))
                .attr('x2', xScale(t))
                .style('opacity', 1);

            let tooltipHtml = `<div class="tooltip-time">t = ${t.toFixed(2)}</div>`;

            visibleVars.forEach(name => {
                const val = values[name]?.[i0];
                if (val !== undefined && isFinite(val)) {
                    const color = this.options.variables[name]?.color || '#4CAF50';
                    tooltipHtml += `<div class="tooltip-row">
                        <span class="tooltip-color" style="background:${color}"></span>
                        <span class="tooltip-name">${App.escapeHtml(name)}:</span>
                        <span class="tooltip-value">${this.formatNumber(val)}</span>
                    </div>`;

                    hoverDots.select(`.hover-dot-${this.variableKey(name)}`)
                        .attr('cx', xScale(t))
                        .attr('cy', yScale(val))
                        .style('opacity', 1);
                }
            });

            // Calculate tooltip position, keeping it within bounds
            let tooltipX = event.offsetX + 15;
            let tooltipY = event.offsetY - 10;

            // Adjust for mobile - keep tooltip visible
            const containerRect = this.container.getBoundingClientRect();
            if (tooltipX + 200 > containerRect.width) {
                tooltipX = event.offsetX - 180;
            }
            if (tooltipY < 10) {
                tooltipY = 10;
            }

            tooltip
                .html(tooltipHtml)
                .style('left', `${tooltipX}px`)
                .style('top', `${tooltipY}px`)
                .style('opacity', 1);
        };

        const hideTooltip = () => {
            hoverLine.style('opacity', 0);
            hoverDots.selectAll('circle').style('opacity', 0);
            tooltip.style('opacity', 0);
        };

        // Mouse events
        overlay.on('mousemove', showTooltip);
        overlay.on('mouseleave', hideTooltip);

        // Touch events for mobile
        overlay.on('touchstart', (event) => {
            event.preventDefault();
            if (event.touches.length === 1) {
                showTooltip(event.touches[0]);
            }
        });

        overlay.on('touchmove', (event) => {
            event.preventDefault();
            if (event.touches.length === 1) {
                showTooltip(event.touches[0]);
            }
        });

        overlay.on('touchend', () => {
            // Keep tooltip visible for a moment on touch end
            setTimeout(hideTooltip, 1500);
        });
    },

    /**
     * Render line chart
     */
    renderLineChart() {
        const dim = this.getDimensions();
        const time = this.results.time;
        const rawValues = this.results.values;
        const visibleVars = this.getVisibleVariables();

        if (visibleVars.length === 0) {
            this.container.innerHTML = '<div class="no-data">No variables selected</div>';
            return;
        }

        // Normalize values if enabled
        let values = rawValues;
        let normInfo = null;
        if (this.options.normalize) {
            normInfo = this.getNormalizationInfo(rawValues);
            values = {};
            Object.keys(rawValues).forEach(name => {
                values[name] = rawValues[name].map(v =>
                    this.normalizeValue(v, normInfo[name])
                );
            });
        }

        const svg = this.createSvg(dim);
        const { xScale, yScale } = this.createScales(dim, time, values);

        const g = svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        this.addAxes(g, xScale, yScale, dim);

        // Chart area with clipping
        const chartArea = g.append('g')
            .attr('clip-path', `url(#${this._plotId}-clip)`);

        // Line generator
        const line = d3.line()
            .x((d, i) => xScale(time[i]))
            .y(d => yScale(d))
            .defined(d => isFinite(d))
            .curve(d3.curveMonotoneX);

        // Draw lines for each visible variable
        visibleVars.forEach(name => {
            const vals = values[name];
            if (!vals) return;

            const color = this.options.variables[name]?.color || '#4CAF50';

            const path = chartArea.append('path')
                .datum(vals)
                .attr('class', `chart-line line-${this.variableKey(name)}`)
                .attr('d', line)
                .attr('fill', 'none')
                .attr('stroke', color)
                .attr('stroke-width', 2.5);

            // Animation
            if (this.options.animate) {
                const totalLength = path.node().getTotalLength();
                path
                    .attr('stroke-dasharray', `${totalLength} ${totalLength}`)
                    .attr('stroke-dashoffset', totalLength)
                    .transition()
                    .duration(this.options.animationDuration)
                    .ease(d3.easeLinear)
                    .attr('stroke-dashoffset', 0);
            }
        });

        // Draw comparison runs
        this.previousRuns.forEach((run, runIdx) => {
            visibleVars.forEach(name => {
                const vals = run.results.values[name];
                if (!vals) return;

                const color = this.options.variables[name]?.color || '#4CAF50';

                chartArea.append('path')
                    .datum(vals)
                    .attr('class', `chart-line comparison-line`)
                    .attr('d', line)
                    .attr('fill', 'none')
                    .attr('stroke', color)
                    .attr('stroke-width', 1.5)
                    .attr('stroke-dasharray', '5,5')
                    .attr('opacity', 0.5);
            });
        });

        this.addLegend(svg, dim);
        this.addTooltip(svg, g, xScale, yScale, dim, time, values);
        this.addZoom(svg, g, xScale, yScale, dim, time, values);
    },

    /**
     * Render area chart
     */
    renderAreaChart() {
        const dim = this.getDimensions();
        const time = this.results.time;
        const values = this.results.values;
        const visibleVars = this.getVisibleVariables();

        if (visibleVars.length === 0) {
            this.container.innerHTML = '<div class="no-data">No variables selected</div>';
            return;
        }

        const svg = this.createSvg(dim);
        const { xScale, yScale } = this.createScales(dim, time, values);

        const g = svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        this.addAxes(g, xScale, yScale, dim);

        const chartArea = g.append('g')
            .attr('clip-path', `url(#${this._plotId}-clip)`);

        // Area generator
        const area = d3.area()
            .x((d, i) => xScale(time[i]))
            .y0(dim.innerHeight)
            .y1(d => yScale(d))
            .defined(d => isFinite(d))
            .curve(d3.curveMonotoneX);

        const line = d3.line()
            .x((d, i) => xScale(time[i]))
            .y(d => yScale(d))
            .defined(d => isFinite(d))
            .curve(d3.curveMonotoneX);

        // Draw areas and lines
        visibleVars.forEach(name => {
            const vals = values[name];
            if (!vals) return;

            const color = this.options.variables[name]?.color || '#4CAF50';
            const gradientId = `gradient-${this._plotId}-${this.variableKey(name)}`;

            // Area
            chartArea.append('path')
                .datum(vals)
                .attr('class', `chart-area area-${this.variableKey(name)}`)
                .attr('d', area)
                .attr('fill', `url(#${gradientId})`);

            // Line
            chartArea.append('path')
                .datum(vals)
                .attr('class', `chart-line line-${this.variableKey(name)}`)
                .attr('d', line)
                .attr('fill', 'none')
                .attr('stroke', color)
                .attr('stroke-width', 2);
        });

        this.addLegend(svg, dim);
        this.addTooltip(svg, g, xScale, yScale, dim, time, values);
    },

    /**
     * Render stacked area chart
     */
    renderStackedAreaChart() {
        const dim = this.getDimensions();
        const time = this.results.time;
        const values = this.results.values;
        const visibleVars = this.getVisibleVariables();

        if (visibleVars.length === 0) {
            this.container.innerHTML = '<div class="no-data">No variables selected</div>';
            return;
        }

        const svg = this.createSvg(dim);

        // Prepare stacked data
        const stackData = time.map((t, i) => {
            const row = { time: t };
            visibleVars.forEach(name => {
                row[name] = values[name]?.[i] ?? 0;
            });
            return row;
        });

        const stack = d3.stack()
            .keys(visibleVars)
            .order(d3.stackOrderNone)
            .offset(d3.stackOffsetDiverging);

        const series = stack(stackData);

        // Y scale for stacked data
        const yMax = d3.max(series, s => d3.max(s, d => d[1]));
        const yMin = d3.min(series, s => d3.min(s, d => d[0]));

        const xScale = d3.scaleLinear()
            .domain([time[0], time[time.length - 1]])
            .range([0, dim.innerWidth]);

        const yScale = d3.scaleLinear()
            .domain(yMin === yMax ? [yMin-1,yMax+1] : [Math.min(0,yMin*1.1),Math.max(0,yMax*1.1)])
            .range([dim.innerHeight, 0]);

        const g = svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        this.addAxes(g, xScale, yScale, dim);

        const chartArea = g.append('g')
            .attr('clip-path', `url(#${this._plotId}-clip)`);

        const area = d3.area()
            .x((d, i) => xScale(time[i]))
            .y0(d => yScale(d[0]))
            .y1(d => yScale(d[1]))
            .curve(d3.curveMonotoneX);

        // Draw stacked areas
        series.forEach((s, i) => {
            const name = visibleVars[i];
            const color = this.options.variables[name]?.color || this.colors[i % this.colors.length];

            chartArea.append('path')
                .datum(s)
                .attr('class', `stacked-area area-${this.variableKey(name)}`)
                .attr('d', area)
                .attr('fill', color)
                .attr('fill-opacity', 0.7)
                .attr('stroke', color)
                .attr('stroke-width', 1);
        });

        this.addLegend(svg, dim);
    },

    /**
     * Render phase diagram (variable vs variable)
     */
    renderPhaseChart() {
        const dim = this.getDimensions();
        const values = this.results.values;
        const visibleVars = this.getVisibleVariables();

        if (visibleVars.length < 2) {
            this.container.innerHTML = '<div class="no-data">Select at least 2 variables for phase diagram</div>';
            return;
        }

        const xVar = visibleVars[0];
        const yVar = visibleVars[1];
        const xVals = values[xVar];
        const yVals = values[yVar];

        const svg = this.createSvg(dim);

        // Create scales
        const xExtent = d3.extent(xVals.filter(v => isFinite(v)));
        const yExtent = d3.extent(yVals.filter(v => isFinite(v)));

        const xPad = (xExtent[1] - xExtent[0]) * 0.1 || 1;
        const yPad = (yExtent[1] - yExtent[0]) * 0.1 || 1;

        const xScale = d3.scaleLinear()
            .domain([xExtent[0] - xPad, xExtent[1] + xPad])
            .range([0, dim.innerWidth]);

        const yScale = d3.scaleLinear()
            .domain([yExtent[0] - yPad, yExtent[1] + yPad])
            .range([dim.innerHeight, 0]);

        const g = svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        // Axes
        g.append('g')
            .attr('class', 'axis x-axis')
            .attr('transform', `translate(0,${dim.innerHeight})`)
            .call(d3.axisBottom(xScale).ticks(6));

        g.append('g')
            .attr('class', 'axis y-axis')
            .call(d3.axisLeft(yScale).ticks(5).tickFormat(d3.format('~s')));

        // Axis labels
        g.append('text')
            .attr('x', dim.innerWidth / 2)
            .attr('y', dim.innerHeight + 40)
            .attr('fill', 'var(--text-secondary)')
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .text(xVar);

        g.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('x', -dim.innerHeight / 2)
            .attr('y', -(this.margin.left - 14))
            .attr('fill', 'var(--text-secondary)')
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .text(yVar);

        // Phase path
        const lineData = xVals.map((x, i) => [x, yVals[i]])
            .filter(([x, y]) => isFinite(x) && isFinite(y));

        const line = d3.line()
            .x(d => xScale(d[0]))
            .y(d => yScale(d[1]))
            .curve(d3.curveLinear);

        const color = this.options.variables[xVar]?.color || '#4CAF50';

        // Draw path with gradient
        g.append('path')
            .datum(lineData)
            .attr('class', 'phase-path')
            .attr('d', line)
            .attr('fill', 'none')
            .attr('stroke', color)
            .attr('stroke-width', 2);

        // Start point
        if (lineData.length > 0) {
            g.append('circle')
                .attr('cx', xScale(lineData[0][0]))
                .attr('cy', yScale(lineData[0][1]))
                .attr('r', 6)
                .attr('fill', '#2ecc71')
                .attr('stroke', 'white')
                .attr('stroke-width', 2);

            // End point
            g.append('circle')
                .attr('cx', xScale(lineData[lineData.length - 1][0]))
                .attr('cy', yScale(lineData[lineData.length - 1][1]))
                .attr('r', 6)
                .attr('fill', '#e74c3c')
                .attr('stroke', 'white')
                .attr('stroke-width', 2);
        }

        // Direction arrows along path
        const arrowPositions = [0.25, 0.5, 0.75];
        arrowPositions.forEach(pos => {
            const idx = Math.floor(pos * lineData.length);
            if (idx > 0 && idx < lineData.length - 1) {
                const p1 = lineData[idx - 1];
                const p2 = lineData[idx + 1];
                const angle = Math.atan2(
                    yScale(p2[1]) - yScale(p1[1]),
                    xScale(p2[0]) - xScale(p1[0])
                );

                const px = xScale(lineData[idx][0]);
                const py = yScale(lineData[idx][1]);

                g.append('polygon')
                    .attr('points', '-5,-4 5,0 -5,4')
                    .attr('fill', color)
                    .attr('transform', `translate(${px},${py}) rotate(${angle * 180 / Math.PI})`);
            }
        });
    },

    /**
     * Add zoom and pan behavior with touch support
     */
    addZoom(svg, g, xScale, yScale, dim, time, values) {
        const visibleVars = this.getVisibleVariables();
        const self = this;

        const zoom = d3.zoom()
            .scaleExtent([1, 10])
            .extent([[0, 0], [dim.innerWidth, dim.innerHeight]])
            .translateExtent([[0, 0], [dim.innerWidth, dim.innerHeight]])
            .on('zoom', (event) => {
                const newXScale = event.transform.rescaleX(xScale);
                const newYScale = event.transform.rescaleY(yScale);

                // Update axes
                g.select('.x-axis').call(d3.axisBottom(newXScale).ticks(8));
                g.select('.y-axis').call(d3.axisLeft(newYScale).ticks(5).tickFormat(d3.format('~s')));

                // Update grid
                g.select('.x-grid').call(
                    d3.axisBottom(newXScale).tickSize(-dim.innerHeight).tickFormat('')
                );
                g.select('.y-grid').call(
                    d3.axisLeft(newYScale).tickSize(-dim.innerWidth).tickFormat('')
                );

                // Update lines
                const line = d3.line()
                    .x((d, i) => newXScale(time[i]))
                    .y(d => newYScale(d))
                    .defined(d => isFinite(d))
                    .curve(d3.curveMonotoneX);

                visibleVars.forEach(name => {
                    g.select(`.line-${this.variableKey(name)}`)
                        .attr('d', line(values[name]));
                });
            });

        svg.call(zoom);

        // Double-click/double-tap to reset zoom
        svg.on('dblclick.zoom', () => {
            svg.transition()
                .duration(750)
                .call(zoom.transform, d3.zoomIdentity);
        });

        // Enhanced touch support for mobile devices
        this.addTouchGestures(svg, zoom, dim);
    },

    /**
     * Add touch gesture support for pinch-to-zoom and swipe-to-pan
     */
    addTouchGestures(svg, zoom, dim) {
        const svgNode = svg.node();
        if (!svgNode) return;

        let lastTouchEnd = 0;
        let touchStartDistance = 0;
        let touchStartCenter = null;
        let initialTransform = d3.zoomIdentity;

        // Prevent default touch behaviors to enable custom gestures
        svgNode.addEventListener('touchstart', (e) => {
            if (e.touches.length === 2) {
                e.preventDefault();
                touchStartDistance = this.getTouchDistance(e.touches);
                touchStartCenter = this.getTouchCenter(e.touches);
                initialTransform = d3.zoomTransform(svgNode);
            }
        }, { passive: false });

        svgNode.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2) {
                e.preventDefault();

                const currentDistance = this.getTouchDistance(e.touches);
                const currentCenter = this.getTouchCenter(e.touches);

                // Calculate scale change (pinch)
                const scaleChange = currentDistance / touchStartDistance;
                const newScale = Math.min(10, Math.max(1, initialTransform.k * scaleChange));

                // Calculate translation (pan)
                const dx = currentCenter.x - touchStartCenter.x;
                const dy = currentCenter.y - touchStartCenter.y;

                const newX = initialTransform.x + dx;
                const newY = initialTransform.y + dy;

                // Apply transform
                const transform = d3.zoomIdentity
                    .translate(newX, newY)
                    .scale(newScale);

                svg.call(zoom.transform, transform);
            }
        }, { passive: false });

        // Double-tap to reset zoom
        svgNode.addEventListener('touchend', (e) => {
            const now = Date.now();
            if (now - lastTouchEnd < 300 && e.touches.length === 0) {
                e.preventDefault();
                svg.transition()
                    .duration(750)
                    .call(zoom.transform, d3.zoomIdentity);
            }
            lastTouchEnd = now;
        });
    },

    /**
     * Calculate distance between two touch points
     */
    getTouchDistance(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    },

    /**
     * Calculate center point between two touches
     */
    getTouchCenter(touches) {
        return {
            x: (touches[0].clientX + touches[1].clientX) / 2,
            y: (touches[0].clientY + touches[1].clientY) / 2
        };
    },

    /**
     * Export chart as image
     */
    buildExportSvg() {
        const live = this.container.querySelector('svg');
        if (!live) return null;
        const svg = live.cloneNode(true), dim = this.getDimensions();
        // Freeze computed SVG styles: downloaded files do not have the app stylesheet.
        const originals = [live,...live.querySelectorAll('*')], copies = [svg,...svg.querySelectorAll('*')];
        originals.forEach((node,index) => {
            const style = getComputedStyle(node);
            for (const key of ['fill','stroke','stroke-width','font-family','font-size','font-weight','opacity'])
                copies[index].style.setProperty(key,style.getPropertyValue(key));
        });
        svg.querySelectorAll('foreignObject').forEach(node=>node.remove());
        const ns = 'http://www.w3.org/2000/svg';
        const add = (tag,attributes,parent=svg) => {
            const node=document.createElementNS(ns,tag);
            for(const [key,value] of Object.entries(attributes)) node.setAttribute(key,String(value));
            parent.appendChild(node); return node;
        };
        const columns = dim.width >= 600 ? 2 : 1, colWidth = (dim.width-32)/columns;
        const measure = document.createElement('canvas').getContext('2d');
        measure.font = '11px sans-serif';
        const wrapLabel = name => {
            const lines=[]; let line='';
            for (const char of Array.from(name)) {
                if (line && measure.measureText(line+char).width > colWidth-30) { lines.push(line); line=''; }
                line+=char;
            }
            lines.push(line); return lines;
        };
        const entries=Object.entries(this.options.variables).filter(([,option])=>option.visible);
        let y=dim.height+20;
        for(let i=0;i<entries.length;i+=columns) {
            let rowHeight=24;
            for(let c=0;c<columns && i+c<entries.length;c++) {
                const [name,option]=entries[i+c],x=16+c*colWidth;
                const lines=wrapLabel(name);
                add('rect',{x,y:y-9,width:9,height:9,rx:2,fill:option.color});
                const label=add('text',{x:x+18,y,fill:'#dce9f6','font-family':'sans-serif','font-size':11});
                lines.forEach((line,j)=>{add('tspan',{x:x+18,dy:j?16:0},label).textContent=line;});
                rowHeight=Math.max(rowHeight,lines.length*16+10);
            }
            y+=rowHeight;
        }
        const height=entries.length ? y+12 : dim.height;
        svg.setAttribute('width',dim.width);svg.setAttribute('height',height);
        svg.setAttribute('viewBox',`0 0 ${dim.width} ${height}`);
        const background=add('rect',{x:0,y:0,width:dim.width,height,fill:'#14263a'});
        svg.insertBefore(background,svg.firstChild);
        return {svg,width:dim.width,height};
    },

    exportAs(format = 'png') {
        const exported = this.buildExportSvg();
        if (!exported) return;
        const {svg} = exported;
        const svgData = new XMLSerializer().serializeToString(svg);
        const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });

        if (format === 'svg') {
            const url = URL.createObjectURL(svgBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'chart.svg';
            a.click();
            URL.revokeObjectURL(url);
            return;
        }

        // PNG export
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();

        const dim = exported;
        canvas.width = dim.width * 2;  // 2x for retina
        canvas.height = dim.height * 2;
        ctx.scale(2, 2);

        const imageUrl = URL.createObjectURL(svgBlob);
        img.onerror = () => { URL.revokeObjectURL(imageUrl); App.showToast('Chart export failed. Try the SVG format.', 'error'); };
        img.onload = () => {
            URL.revokeObjectURL(imageUrl);
            ctx.fillStyle = '#14263a';  // Background color
            ctx.fillRect(0, 0, dim.width, dim.height);
            ctx.drawImage(img, 0, 0, dim.width, dim.height);

            const pngUrl = canvas.toDataURL('image/png');
            const dialog = document.createElement('dialog');
            dialog.className = 'chart-export-dialog';
            dialog.setAttribute('aria-label','Export chart');
            dialog.innerHTML = '<header><h2>Export chart</h2><button type="button" aria-label="Close chart export">×</button></header><p>Your chart with all selected series. PNG is rendered at twice the display resolution.</p><div class="chart-export-preview"></div><footer></footer>';
            const picture=document.createElement('img');picture.src=pngUrl;picture.alt='Chart export preview';
            dialog.querySelector('.chart-export-preview').appendChild(picture);
            const svgUrl=URL.createObjectURL(svgBlob);
            for(const [label,href,filename] of [['Save PNG',pngUrl,'chart.png'],['Save SVG',svgUrl,'chart.svg']]) {
                const link=document.createElement('a');link.textContent=label;link.href=href;link.download=filename;
                dialog.querySelector('footer').appendChild(link);
            }
            const opener=document.activeElement;
            dialog.querySelector('button').addEventListener('click',()=>dialog.close());
            dialog.addEventListener('close',()=>{URL.revokeObjectURL(svgUrl);dialog.remove();opener?.focus();},{once:true});
            document.body.appendChild(dialog);dialog.showModal();
        };

        img.src = imageUrl;
    },

    /**
     * Utility functions
     */
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
    },

    /**
     * Start animated playback of simulation
     */
    startAnimation() {
        if (!this.results || this.isAnimating) return;

        this.isAnimating = true;
        this.animationProgress = 0;
        this.animateFrame();
    },

    /**
     * Stop animation
     */
    stopAnimation() {
        this.isAnimating = false;
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
    },

    /**
     * Toggle animation play/pause
     */
    toggleAnimation() {
        if (this.isAnimating) {
            this.stopAnimation();
        } else {
            this.startAnimation();
        }
        return this.isAnimating;
    },

    /**
     * Reset animation to beginning
     */
    resetAnimation() {
        this.stopAnimation();
        this.animationProgress = 0;
        this.render();
    },

    /**
     * Animation frame update
     */
    animateFrame() {
        if (!this.isAnimating || !this.results) return;

        const totalSteps = this.results.time.length;
        const progressIncrement = (this.options.animationSpeed * 2) / totalSteps;

        this.animationProgress += progressIncrement;

        if (this.animationProgress >= 1) {
            this.animationProgress = 1;
            this.isAnimating = false;
            this.renderAnimatedFrame(1);
            this.onAnimationComplete();
            return;
        }

        this.renderAnimatedFrame(this.animationProgress);
        this.animationFrame = requestAnimationFrame(() => this.animateFrame());
    },

    /**
     * Render a single animated frame
     */
    renderAnimatedFrame(progress) {
        if (!this.container || !this.results) return;

        const totalSteps = this.results.time.length;
        const currentStep = Math.floor(progress * (totalSteps - 1));

        // Clear and render partial data
        this.container.innerHTML = '';

        const partialResults = {
            time: this.results.time.slice(0, currentStep + 1),
            values: {}
        };

        for (const [name, values] of Object.entries(this.results.values)) {
            partialResults.values[name] = values.slice(0, currentStep + 1);
        }

        // Temporarily set results for rendering
        const fullResults = this.results;
        this.results = partialResults;

        // Use full scales from original data
        const dim = this.getDimensions();
        const visibleVars = this.getVisibleVariables();

        if (visibleVars.length === 0) {
            this.results = fullResults;
            return;
        }

        // Render with animation indicator
        this.renderLineChartAnimated(fullResults, currentStep);

        this.results = fullResults;

        // Update animation progress indicator
        this.updateAnimationIndicator(progress, currentStep, totalSteps);
    },

    /**
     * Render line chart during animation (uses full scales)
     */
    renderLineChartAnimated(fullResults, currentStep) {
        const dim = this.getDimensions();
        const time = fullResults.time;
        const values = fullResults.values;
        const visibleVars = this.getVisibleVariables();

        const svg = this.createSvg(dim);
        const { xScale, yScale } = this.createScales(dim, time, values);

        const g = svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        this.addAxes(g, xScale, yScale, dim);

        const chartArea = g.append('g')
            .attr('clip-path', `url(#${this._plotId}-clip)`);

        // Line generator
        const line = d3.line()
            .x((d, i) => xScale(time[i]))
            .y(d => yScale(d))
            .defined(d => isFinite(d))
            .curve(d3.curveMonotoneX);

        // Draw lines up to current step
        visibleVars.forEach(name => {
            const vals = values[name].slice(0, currentStep + 1);
            if (!vals || vals.length === 0) return;

            const color = this.options.variables[name]?.color || '#4CAF50';

            chartArea.append('path')
                .datum(vals)
                .attr('class', `chart-line line-${this.variableKey(name)}`)
                .attr('d', line)
                .attr('fill', 'none')
                .attr('stroke', color)
                .attr('stroke-width', 2.5);

            // Add current point marker
            if (currentStep < values[name].length) {
                const currentVal = values[name][currentStep];
                if (isFinite(currentVal)) {
                    chartArea.append('circle')
                        .attr('cx', xScale(time[currentStep]))
                        .attr('cy', yScale(currentVal))
                        .attr('r', 6)
                        .attr('fill', color)
                        .attr('stroke', 'white')
                        .attr('stroke-width', 2);
                }
            }
        });

        this.addLegend(svg, dim);
    },

    /**
     * Update animation progress indicator
     */
    updateAnimationIndicator(progress, currentStep, totalSteps) {
        let indicator = this.container.querySelector('.animation-indicator');

        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'animation-indicator';
            indicator.style.cssText = `
                position: absolute;
                top: 10px;
                left: 50%;
                transform: translateX(-50%);
                background: var(--bg-secondary);
                padding: 0.5rem 1rem;
                border-radius: var(--radius-sm);
                font-size: 0.85rem;
                color: var(--text-primary);
                z-index: 10;
                border: 1px solid var(--border-color);
            `;
            this.container.style.position = 'relative';
            this.container.appendChild(indicator);
        }

        const currentTime = this.results.time[currentStep] ?? '0';
        const endTime = this.results.time[totalSteps - 1] ?? '?';
        indicator.innerHTML = `
            <span>t = ${currentTime} / ${endTime}</span>
            <span style="margin-left: 1rem; color: var(--text-muted);">${Math.round(progress * 100)}%</span>
        `;
    },

    /**
     * Animation complete callback
     */
    onAnimationComplete() {
        const indicator = this.container?.querySelector('.animation-indicator');
        if (indicator) {
            indicator.innerHTML += '<span style="margin-left: 0.5rem; color: var(--accent-success);">Complete</span>';
            setTimeout(() => {
                if (indicator.parentNode) {
                    indicator.remove();
                }
            }, 2000);
        }
    },

    /**
     * Toggle comparison mode
     */
    toggleComparison() {
        this.options.showComparison = !this.options.showComparison;
        this.render();
        return this.options.showComparison;
    },

    /**
     * Get comparison runs for display
     */
    getComparisonRuns() {
        if (!this.options.showComparison) return [];
        return this.previousRuns;
    }
};
