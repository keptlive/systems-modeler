/**
 * Systems Modeler - Analytics Dashboard
 * Comprehensive statistics, pattern analysis, and data visualization
 */
const Analytics = {
    container: null,
    results: null,
    statistics: null,

    /**
     * Initialize analytics module
     */
    init(containerId) {
        this.container = document.getElementById(containerId);
    },

    /**
     * Set simulation results and compute analytics
     */
    async setResults(results) {
        this.results = results;

        if (!results || !results.time || !results.values) {
            this.statistics = null;
            return;
        }

        // Fetch statistics from backend
        try {
            const response = await fetch('/api/analyze/statistics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ simulation_results: results })
            });

            if (response.ok) {
                this.statistics = await response.json();
            } else {
                // Compute client-side if backend fails
                this.statistics = this.computeLocalStatistics(results);
            }
        } catch (error) {
            console.error('Failed to fetch statistics:', error);
            this.statistics = this.computeLocalStatistics(results);
        }
    },

    /**
     * Compute statistics client-side as fallback
     */
    computeLocalStatistics(results) {
        const stats = {};
        const patterns = {};
        const peaks = {};
        const equilibria = {};

        for (const [name, values] of Object.entries(results.values)) {
            const validValues = values.filter(v => v !== null && isFinite(v));
            if (validValues.length === 0) continue;

            // Basic statistics
            stats[name] = {
                min: Math.min(...validValues),
                max: Math.max(...validValues),
                mean: validValues.reduce((a, b) => a + b, 0) / validValues.length,
                initial: validValues[0],
                final: validValues[validValues.length - 1],
                range: Math.max(...validValues) - Math.min(...validValues)
            };

            // Standard deviation
            const mean = stats[name].mean;
            const variance = validValues.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / validValues.length;
            stats[name].std = Math.sqrt(variance);

            // Percent change
            if (stats[name].initial !== 0) {
                stats[name].percent_change = ((stats[name].final - stats[name].initial) / stats[name].initial) * 100;
            }

            // Pattern detection
            patterns[name] = this.detectPattern(values);

            // Peak detection
            const detectedPeaks = this.detectPeaks(results.time, values);
            if (detectedPeaks.length > 0) {
                peaks[name] = detectedPeaks;
            }

            // Equilibrium detection
            const eq = this.detectEquilibrium(values);
            if (eq) {
                equilibria[name] = eq;
            }
        }

        return {
            statistics: stats,
            patterns,
            peaks,
            equilibria,
            correlations: this.computeCorrelations(results.values),
            time_range: {
                start: results.time[0],
                end: results.time[results.time.length - 1],
                steps: results.time.length
            }
        };
    },

    /**
     * Detect pattern in values
     */
    detectPattern(values) {
        const validValues = values.filter(v => isFinite(v));
        if (validValues.length < 3) return 'insufficient_data';

        const diffs = [];
        for (let i = 1; i < validValues.length; i++) {
            diffs.push(validValues[i] - validValues[i - 1]);
        }

        const allPositive = diffs.every(d => d >= 0);
        const allNegative = diffs.every(d => d <= 0);

        if (allPositive) {
            const secondDiffs = [];
            for (let i = 1; i < diffs.length; i++) {
                secondDiffs.push(diffs[i] - diffs[i - 1]);
            }
            const avgSecondDiff = secondDiffs.reduce((a, b) => a + b, 0) / secondDiffs.length;
            return avgSecondDiff > 0 ? 'exponential_growth' : 'linear_growth';
        }

        if (allNegative) {
            const secondDiffs = [];
            for (let i = 1; i < diffs.length; i++) {
                secondDiffs.push(diffs[i] - diffs[i - 1]);
            }
            const avgSecondDiff = secondDiffs.reduce((a, b) => a + b, 0) / secondDiffs.length;
            return avgSecondDiff < 0 ? 'exponential_decay' : 'linear_decay';
        }

        // Check for oscillation
        let signChanges = 0;
        for (let i = 1; i < diffs.length; i++) {
            if (Math.sign(diffs[i]) !== Math.sign(diffs[i - 1]) && diffs[i] !== 0) {
                signChanges++;
            }
        }
        if (signChanges > validValues.length * 0.3) {
            return 'oscillating';
        }

        // Check for peak and decline
        const maxIdx = validValues.indexOf(Math.max(...validValues));
        if (maxIdx / validValues.length > 0.1 && maxIdx / validValues.length < 0.9) {
            return 'peak_and_decline';
        }

        return 'complex';
    },

    /**
     * Detect peaks in values
     */
    detectPeaks(time, values) {
        const peaks = [];
        for (let i = 1; i < values.length - 1; i++) {
            if (!isFinite(values[i])) continue;

            if (values[i] > values[i - 1] && values[i] > values[i + 1]) {
                peaks.push({ type: 'peak', time: time[i], value: values[i], index: i });
            } else if (values[i] < values[i - 1] && values[i] < values[i + 1]) {
                peaks.push({ type: 'trough', time: time[i], value: values[i], index: i });
            }
        }
        return peaks;
    },

    /**
     * Detect equilibrium
     */
    detectEquilibrium(values, threshold = 0.01) {
        const validValues = values.filter(v => isFinite(v));
        if (validValues.length < 10) return null;

        const checkStart = Math.floor(validValues.length * 0.8);
        const checkValues = validValues.slice(checkStart);

        if (checkValues.length < 2) return null;

        const mean = checkValues.reduce((a, b) => a + b, 0) / checkValues.length;
        if (mean === 0) return null;

        const variation = Math.sqrt(
            checkValues.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / checkValues.length
        ) / Math.abs(mean);

        if (variation < threshold) {
            return {
                reached: true,
                equilibrium_value: mean,
                variation: variation
            };
        }

        return { reached: false, variation: variation };
    },

    /**
     * Compute correlations
     */
    computeCorrelations(values) {
        const varNames = Object.keys(values);
        const correlations = {};

        for (let i = 0; i < varNames.length; i++) {
            for (let j = i + 1; j < varNames.length; j++) {
                const name1 = varNames[i];
                const name2 = varNames[j];
                const arr1 = values[name1];
                const arr2 = values[name2];

                // Compute correlation coefficient
                const n = Math.min(arr1.length, arr2.length);
                let sum1 = 0, sum2 = 0, sum1Sq = 0, sum2Sq = 0, pSum = 0;

                for (let k = 0; k < n; k++) {
                    if (!isFinite(arr1[k]) || !isFinite(arr2[k])) continue;
                    sum1 += arr1[k];
                    sum2 += arr2[k];
                    sum1Sq += arr1[k] * arr1[k];
                    sum2Sq += arr2[k] * arr2[k];
                    pSum += arr1[k] * arr2[k];
                }

                const num = pSum - (sum1 * sum2 / n);
                const den = Math.sqrt((sum1Sq - sum1 * sum1 / n) * (sum2Sq - sum2 * sum2 / n));

                if (den !== 0) {
                    correlations[`${name1}|${name2}`] = Math.round((num / den) * 1000) / 1000;
                }
            }
        }

        return correlations;
    },

    /**
     * Compute rate of change / derivatives
     */
    computeDerivatives(time, values) {
        const derivatives = {};

        for (const [name, vals] of Object.entries(values)) {
            const derivs = [];
            const accel = [];  // Second derivative

            for (let i = 0; i < vals.length; i++) {
                if (i === 0) {
                    derivs.push(0);
                } else {
                    const dt = time[i] - time[i-1];
                    if (dt !== 0 && isFinite(vals[i]) && isFinite(vals[i-1])) {
                        derivs.push((vals[i] - vals[i-1]) / dt);
                    } else {
                        derivs.push(0);
                    }
                }
            }

            // Second derivative (acceleration)
            for (let i = 0; i < derivs.length; i++) {
                if (i === 0) {
                    accel.push(0);
                } else {
                    const dt = time[i] - time[i-1];
                    if (dt !== 0 && isFinite(derivs[i]) && isFinite(derivs[i-1])) {
                        accel.push((derivs[i] - derivs[i-1]) / dt);
                    } else {
                        accel.push(0);
                    }
                }
            }

            derivatives[name] = {
                velocity: derivs,
                acceleration: accel,
                maxVelocity: Math.max(...derivs.map(Math.abs)),
                avgVelocity: derivs.reduce((a, b) => a + b, 0) / derivs.length,
                maxAcceleration: Math.max(...accel.map(Math.abs))
            };
        }

        return derivatives;
    },

    /**
     * Compute sensitivity metrics (simple approach: variance contribution)
     */
    computeSensitivity(values) {
        const sensitivity = {};
        const varNames = Object.keys(values);

        // Compute total system variance
        let totalVariance = 0;
        const variances = {};

        for (const name of varNames) {
            const vals = values[name].filter(v => isFinite(v));
            if (vals.length === 0) continue;

            const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
            const variance = vals.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / vals.length;
            variances[name] = variance;
            totalVariance += variance;
        }

        // Compute relative contribution
        for (const name of varNames) {
            if (totalVariance > 0) {
                sensitivity[name] = {
                    variance: variances[name] || 0,
                    relativeContribution: ((variances[name] || 0) / totalVariance) * 100,
                    impact: variances[name] > totalVariance * 0.3 ? 'high' :
                            variances[name] > totalVariance * 0.1 ? 'medium' : 'low'
                };
            } else {
                sensitivity[name] = {
                    variance: 0,
                    relativeContribution: 0,
                    impact: 'low'
                };
            }
        }

        return sensitivity;
    },

    /**
     * Render the analytics dashboard
     */
    render() {
        if (!this.container) return;

        if (!this.results || !this.statistics) {
            this.container.innerHTML = `
                <div class="analytics-placeholder">
                    <p>Run a simulation to see analytics</p>
                </div>
            `;
            return;
        }

        // Compute additional analytics
        this.derivatives = this.computeDerivatives(this.results.time, this.results.values);
        this.sensitivity = this.computeSensitivity(this.results.values);

        let html = '<div class="analytics-dashboard">';

        // Summary section
        html += this.renderSummarySection();

        // Statistics section
        html += this.renderStatisticsSection();

        // Rate of change section
        html += this.renderDerivativesSection();

        // Sensitivity section
        html += this.renderSensitivitySection();

        // Patterns section
        html += this.renderPatternsSection();

        // Peaks section
        html += this.renderPeaksSection();

        // Correlations section
        html += this.renderCorrelationsSection();

        html += '</div>';

        this.container.innerHTML = html;

        // Add event listeners for collapsible sections
        this.container.querySelectorAll('.analytics-section-header').forEach(header => {
            header.addEventListener('click', () => {
                const section = header.parentElement;
                section.classList.toggle('collapsed');
            });
        });
    },

    /**
     * Render summary section
     */
    renderSummarySection() {
        const timeRange = this.statistics.time_range;

        return `
            <div class="analytics-section analytics-summary">
                <div class="analytics-section-header">
                    <span class="section-icon">&#128200;</span>
                    <span class="section-title">Simulation Summary</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    <div class="summary-grid">
                        <div class="summary-item">
                            <span class="summary-label">Time Range</span>
                            <span class="summary-value">${timeRange.start} - ${timeRange.end}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Time Steps</span>
                            <span class="summary-value">${timeRange.steps}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Variables</span>
                            <span class="summary-value">${Object.keys(this.statistics.statistics).length}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Render statistics section
     */
    renderStatisticsSection() {
        const stats = this.statistics.statistics;

        let rows = '';
        for (const [name, s] of Object.entries(stats)) {
            if (s.error) continue;

            const changeClass = s.percent_change > 0 ? 'positive' : s.percent_change < 0 ? 'negative' : '';
            const changeArrow = s.percent_change > 0 ? '&#9650;' : s.percent_change < 0 ? '&#9660;' : '';

            rows += `
                <tr>
                    <td class="var-name">${name}</td>
                    <td>${this.formatNumber(s.min)}</td>
                    <td>${this.formatNumber(s.max)}</td>
                    <td>${this.formatNumber(s.mean)}</td>
                    <td>${this.formatNumber(s.std)}</td>
                    <td>${this.formatNumber(s.initial)}</td>
                    <td>${this.formatNumber(s.final)}</td>
                    <td class="change ${changeClass}">
                        ${changeArrow} ${s.percent_change != null ? s.percent_change.toFixed(1) + '%' : 'N/A'}
                    </td>
                </tr>
            `;
        }

        return `
            <div class="analytics-section">
                <div class="analytics-section-header">
                    <span class="section-icon">&#128202;</span>
                    <span class="section-title">Summary Statistics</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    <div class="stats-table-wrapper">
                        <table class="stats-table">
                            <thead>
                                <tr>
                                    <th>Variable</th>
                                    <th>Min</th>
                                    <th>Max</th>
                                    <th>Mean</th>
                                    <th>Std Dev</th>
                                    <th>Initial</th>
                                    <th>Final</th>
                                    <th>Change</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Render patterns section
     */
    renderPatternsSection() {
        const patterns = this.statistics.patterns;
        const equilibria = this.statistics.equilibria;

        let content = '<div class="patterns-grid">';

        for (const [name, pattern] of Object.entries(patterns)) {
            const patternInfo = this.getPatternInfo(pattern);
            const eq = equilibria[name];

            content += `
                <div class="pattern-card">
                    <div class="pattern-header">
                        <span class="pattern-var">${name}</span>
                        <span class="pattern-icon" style="color: ${patternInfo.color}">${patternInfo.icon}</span>
                    </div>
                    <div class="pattern-body">
                        <span class="pattern-name" style="color: ${patternInfo.color}">${patternInfo.label}</span>
                        ${eq ? `
                            <span class="equilibrium-badge ${eq.reached ? 'reached' : 'not-reached'}">
                                ${eq.reached ? `Equilibrium: ${this.formatNumber(eq.equilibrium_value)}` : 'No equilibrium'}
                            </span>
                        ` : ''}
                    </div>
                    <div class="pattern-sparkline" id="sparkline-${name.replace(/\s+/g, '-')}"></div>
                </div>
            `;
        }

        content += '</div>';

        // Render sparklines after DOM is updated
        setTimeout(() => this.renderSparklines(), 0);

        return `
            <div class="analytics-section">
                <div class="analytics-section-header">
                    <span class="section-icon">&#128208;</span>
                    <span class="section-title">Behavior Patterns</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    ${content}
                </div>
            </div>
        `;
    },

    /**
     * Get pattern display info
     */
    getPatternInfo(pattern) {
        const patterns = {
            'exponential_growth': { label: 'Exponential Growth', icon: '&#8679;&#8679;', color: '#4CAF50' },
            'linear_growth': { label: 'Linear Growth', icon: '&#8599;', color: '#8BC34A' },
            'exponential_decay': { label: 'Exponential Decay', icon: '&#8681;&#8681;', color: '#f44336' },
            'linear_decay': { label: 'Linear Decay', icon: '&#8600;', color: '#FF5722' },
            'oscillating': { label: 'Oscillating', icon: '&#8644;', color: '#9C27B0' },
            'logistic_growth': { label: 'Logistic Growth', icon: '&#8669;', color: '#2196F3' },
            'logistic_decay': { label: 'Logistic Decay', icon: '&#8656;', color: '#FF9800' },
            'peak_and_decline': { label: 'Peak & Decline', icon: '&#8657;&#8659;', color: '#E91E63' },
            'complex': { label: 'Complex Pattern', icon: '&#8767;', color: '#607D8B' },
            'insufficient_data': { label: 'Insufficient Data', icon: '?', color: '#9E9E9E' }
        };

        return patterns[pattern] || patterns['complex'];
    },

    /**
     * Render mini sparklines
     */
    renderSparklines() {
        if (!this.results) return;

        const time = this.results.time;
        const values = this.results.values;

        for (const [name, vals] of Object.entries(values)) {
            const containerId = `sparkline-${name.replace(/\s+/g, '-')}`;
            const container = document.getElementById(containerId);
            if (!container) continue;

            const width = container.clientWidth || 100;
            const height = 30;

            const svg = d3.select(container)
                .append('svg')
                .attr('width', width)
                .attr('height', height);

            const validVals = vals.filter(v => isFinite(v));
            if (validVals.length === 0) continue;

            const xScale = d3.scaleLinear()
                .domain([0, vals.length - 1])
                .range([2, width - 2]);

            const yScale = d3.scaleLinear()
                .domain([Math.min(...validVals), Math.max(...validVals)])
                .range([height - 2, 2]);

            const line = d3.line()
                .x((d, i) => xScale(i))
                .y(d => yScale(d))
                .defined(d => isFinite(d))
                .curve(d3.curveMonotoneX);

            const pattern = this.statistics.patterns[name];
            const color = this.getPatternInfo(pattern).color;

            svg.append('path')
                .datum(vals)
                .attr('d', line)
                .attr('fill', 'none')
                .attr('stroke', color)
                .attr('stroke-width', 1.5);
        }
    },

    /**
     * Render peaks section
     */
    renderPeaksSection() {
        const peaks = this.statistics.peaks;
        const allPeaks = [];

        for (const [name, varPeaks] of Object.entries(peaks)) {
            varPeaks.forEach(p => {
                allPeaks.push({ ...p, variable: name });
            });
        }

        if (allPeaks.length === 0) {
            return `
                <div class="analytics-section">
                    <div class="analytics-section-header">
                        <span class="section-icon">&#128205;</span>
                        <span class="section-title">Peak Analysis</span>
                        <span class="section-toggle">&#9660;</span>
                    </div>
                    <div class="analytics-section-content">
                        <p class="no-data">No significant peaks detected</p>
                    </div>
                </div>
            `;
        }

        // Sort by time
        allPeaks.sort((a, b) => a.time - b.time);

        // Show only top peaks per variable
        const topPeaks = {};
        allPeaks.forEach(p => {
            if (!topPeaks[p.variable]) {
                topPeaks[p.variable] = { peak: null, trough: null };
            }
            if (p.type === 'peak' && (!topPeaks[p.variable].peak || p.value > topPeaks[p.variable].peak.value)) {
                topPeaks[p.variable].peak = p;
            }
            if (p.type === 'trough' && (!topPeaks[p.variable].trough || p.value < topPeaks[p.variable].trough.value)) {
                topPeaks[p.variable].trough = p;
            }
        });

        let content = '<div class="peaks-list">';
        for (const [name, { peak, trough }] of Object.entries(topPeaks)) {
            if (peak) {
                content += `
                    <div class="peak-item peak">
                        <span class="peak-icon">&#9650;</span>
                        <span class="peak-var">${name}</span>
                        <span class="peak-info">
                            Peak of <strong>${this.formatNumber(peak.value)}</strong> at t = ${peak.time.toFixed(2)}
                        </span>
                    </div>
                `;
            }
            if (trough) {
                content += `
                    <div class="peak-item trough">
                        <span class="peak-icon">&#9660;</span>
                        <span class="peak-var">${name}</span>
                        <span class="peak-info">
                            Trough of <strong>${this.formatNumber(trough.value)}</strong> at t = ${trough.time.toFixed(2)}
                        </span>
                    </div>
                `;
            }
        }
        content += '</div>';

        return `
            <div class="analytics-section">
                <div class="analytics-section-header">
                    <span class="section-icon">&#128205;</span>
                    <span class="section-title">Peak Analysis</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    ${content}
                </div>
            </div>
        `;
    },

    /**
     * Render correlations section
     */
    renderCorrelationsSection() {
        const correlations = this.statistics.correlations;
        const pairs = Object.entries(correlations);

        if (pairs.length === 0) {
            return `
                <div class="analytics-section">
                    <div class="analytics-section-header">
                        <span class="section-icon">&#128279;</span>
                        <span class="section-title">Correlations</span>
                        <span class="section-toggle">&#9660;</span>
                    </div>
                    <div class="analytics-section-content">
                        <p class="no-data">Not enough variables for correlation analysis</p>
                    </div>
                </div>
            `;
        }

        // Sort by absolute correlation
        pairs.sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

        let content = '<div class="correlations-list">';
        pairs.forEach(([pair, corr]) => {
            const [var1, var2] = pair.split('|');
            const strength = Math.abs(corr) > 0.7 ? 'strong' : Math.abs(corr) > 0.4 ? 'moderate' : 'weak';
            const direction = corr > 0 ? 'positive' : 'negative';
            const barWidth = Math.abs(corr) * 100;

            content += `
                <div class="correlation-item">
                    <div class="correlation-vars">
                        <span>${var1}</span>
                        <span class="correlation-arrow">&#8596;</span>
                        <span>${var2}</span>
                    </div>
                    <div class="correlation-bar-container">
                        <div class="correlation-bar ${direction}" style="width: ${barWidth}%"></div>
                    </div>
                    <div class="correlation-value ${direction}">
                        ${corr.toFixed(3)}
                    </div>
                    <div class="correlation-label ${strength}">
                        ${strength} ${direction}
                    </div>
                </div>
            `;
        });
        content += '</div>';

        return `
            <div class="analytics-section">
                <div class="analytics-section-header">
                    <span class="section-icon">&#128279;</span>
                    <span class="section-title">Correlations</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    ${content}
                </div>
            </div>
        `;
    },

    /**
     * Render derivatives / rate of change section
     */
    renderDerivativesSection() {
        if (!this.derivatives) return '';

        let rows = '';
        for (const [name, d] of Object.entries(this.derivatives)) {
            const direction = d.avgVelocity > 0 ? 'increasing' :
                             d.avgVelocity < 0 ? 'decreasing' : 'stable';
            const dirClass = d.avgVelocity > 0 ? 'positive' :
                            d.avgVelocity < 0 ? 'negative' : '';
            const arrow = d.avgVelocity > 0 ? '&#9650;' :
                         d.avgVelocity < 0 ? '&#9660;' : '&#8212;';

            rows += `
                <tr>
                    <td class="var-name">${name}</td>
                    <td>${this.formatNumber(d.avgVelocity)}</td>
                    <td>${this.formatNumber(d.maxVelocity)}</td>
                    <td>${this.formatNumber(d.maxAcceleration)}</td>
                    <td class="change ${dirClass}">${arrow} ${direction}</td>
                </tr>
            `;
        }

        return `
            <div class="analytics-section">
                <div class="analytics-section-header">
                    <span class="section-icon">&#128200;</span>
                    <span class="section-title">Rate of Change</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    <div class="stats-table-wrapper">
                        <table class="stats-table">
                            <thead>
                                <tr>
                                    <th>Variable</th>
                                    <th>Avg Rate</th>
                                    <th>Max Rate</th>
                                    <th>Max Accel</th>
                                    <th>Trend</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Render sensitivity section
     */
    renderSensitivitySection() {
        if (!this.sensitivity) return '';

        // Sort by impact
        const sorted = Object.entries(this.sensitivity)
            .sort((a, b) => b[1].relativeContribution - a[1].relativeContribution);

        let content = '<div class="sensitivity-list">';

        sorted.forEach(([name, s]) => {
            const impactClass = s.impact;
            const barWidth = Math.min(s.relativeContribution, 100);

            content += `
                <div class="sensitivity-item">
                    <div class="sensitivity-header">
                        <span class="sensitivity-var">${name}</span>
                        <span class="sensitivity-value">${s.relativeContribution.toFixed(1)}%</span>
                    </div>
                    <div class="sensitivity-bar-container">
                        <div class="sensitivity-bar ${impactClass}" style="width: ${barWidth}%"></div>
                    </div>
                    <div class="sensitivity-label ${impactClass}">${s.impact} impact</div>
                </div>
            `;
        });

        content += '</div>';

        return `
            <div class="analytics-section">
                <div class="analytics-section-header">
                    <span class="section-icon">&#9881;</span>
                    <span class="section-title">Sensitivity Analysis</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    <p class="section-description" style="color: var(--text-muted); font-size: 0.8rem; margin-bottom: 0.75rem;">
                        Relative variance contribution of each variable to overall system dynamics.
                    </p>
                    ${content}
                </div>
            </div>
        `;
    },

    /**
     * Format number for display
     */
    formatNumber(n) {
        if (n === null || n === undefined || !isFinite(n)) return 'N/A';
        if (Math.abs(n) < 0.01 || Math.abs(n) >= 10000) {
            return n.toExponential(2);
        }
        return n.toFixed(2);
    }
};
