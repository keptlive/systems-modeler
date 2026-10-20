/** Recorded-sample analytics. Offline fallback uses the same conservative rules as the API. */
const Analytics = {
    container: null,
    results: null,
    statistics: null,
    requestVersion: 0,
    init(containerId) { this.container = document.getElementById(containerId); },

    validateResults(results) {
        const time = results?.time, values = results?.values;
        if (!Array.isArray(time) || !time.length || !values || Array.isArray(values) || typeof values !== 'object' || !Object.keys(values).length) throw new Error('Nonempty time and value series are required.');
        if (time.length > 100001 || Object.keys(values).length > 500 || time.length * Object.keys(values).length > 1000000) throw new Error('Analytics input exceeds the supported sample limit.');
        if (!time.every(Number.isFinite) || time.some((v, i) => i && v <= time[i-1]) || !Number.isFinite(time.at(-1)-time[0])) throw new Error('Time samples must be finite and strictly increasing.');
        if (time.length > 1 && time.some((v, i) => i && (v-time[i-1])/(time.at(-1)-time[0]) === 0)) throw new Error('Time sample spacing exceeds supported numeric resolution.');
        for (const [name, series] of Object.entries(values)) {
            if (!name || !Array.isArray(series) || series.length !== time.length || !series.every(Number.isFinite)) throw new Error(`Series ${name} requires one finite numeric value per time sample.`);
        }
    },

    async setResults(results) {
        const version = ++this.requestVersion;
        this.results = results;
        this.statistics = null;
        this.error = null;
        if (!results) return;
        try { this.validateResults(results); } catch (error) { this.error = error.message; return; }
        try {
            const response = await fetch('/api/analyze/statistics', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({simulation_results:results})});
            if (!response.ok) throw new Error('Statistics service unavailable');
            const statistics = await response.json();
            if (version === this.requestVersion) this.statistics = statistics;
        } catch (error) {
            if (version === this.requestVersion) {
                this.statistics = this.computeLocalStatistics(results);
                this.statistics.offline_fallback = true;
            }
        }
    },

    finite(value) { return Number.isFinite(value) ? value : null; },
    sum(values) {
        let sum = 0, correction = 0;
        for (const value of values) {
            const next = value - correction, total = sum + next;
            correction = (total - sum) - next;
            sum = total;
        }
        return sum;
    },
    moments(values) {
        const scale = values.reduce((m,v)=>Math.max(m,Math.abs(v)),0);
        const scaled = values.map(v=>scale ? v/scale : 0);
        const mean = this.sum(scaled)/values.length;
        const std = Math.sqrt(this.sum(scaled.map(v=>(v-mean)**2))/values.length);
        return {scale,scaled,mean,std};
    },
    seriesStatistics(values, time) {
        const {scale,scaled,mean,std} = this.moments(values), n = values.length;
        const ordered = [...scaled].sort((a,b)=>a-b);
        const median = n%2 ? ordered[Math.floor(n/2)] : (ordered[n/2-1]+ordered[n/2])/2;
        const change = scaled.at(-1)-scaled[0], duration = time.at(-1)-time[0];
        const weighted = n>1 ? this.finite(scale*this.sum(scaled.slice(1).map((v,i)=>(v+scaled[i])/2*((time[i+1]-time[i])/duration)))) : null;
        const stats = {min:Math.min(...values),max:Math.max(...values),mean:this.finite(scale*mean),std:this.finite(scale*std),median:this.finite(scale*median),range:this.finite(scale*(ordered.at(-1)-ordered[0])),initial:values[0],final:values.at(-1),total_change:this.finite(scale*change),percent_change:scaled[0] ? this.finite(change/scaled[0]*100) : null,sample_count:n,time_weighted_mean:weighted};
        stats.unrepresentable_metrics = ['mean','std','median','range','total_change'].filter(key=>stats[key]===null);
        return stats;
    },
    computeLocalStatistics(results) {
        this.validateResults(results);
        const statistics=Object.create(null),patterns=Object.create(null),peaks=Object.create(null),equilibria=Object.create(null);
        for (const [name,values] of Object.entries(results.values)) {
            statistics[name]=this.seriesStatistics(values,results.time);
            patterns[name]=this.detectPattern(values,results.time);
            const extrema=this.detectPeaks(results.time,values), tail=this.detectEquilibrium(values);
            if (extrema.length) peaks[name]=extrema;
            if (tail) equilibria[name]=tail;
        }
        const correlation=this.correlationRecords(results.values);
        return {statistics,patterns,peaks,equilibria,correlations:correlation.correlations,correlation_pairs:correlation.records,correlation_coverage:correlation.coverage,time_range:{start:results.time[0],end:results.time.at(-1),steps:results.time.length,intervals:results.time.length-1}};
    },
    detectPattern(values, time=values.map((_,i)=>i)) {
        if(values.length<3) return 'insufficient_data';
        const {scaled:v}=this.moments(values);
        if(Math.max(...v)-Math.min(...v)<=1e-12) return 'constant';
        const duration=time.at(-1)-time[0], deltas=time.slice(1).map((t,i)=>(t-time[i])/duration);
        const slopes=v.slice(1).map((x,i)=>(x-v[i])/deltas[i]);
        if(!slopes.every(Number.isFinite)) return 'complex';
        const tol=Math.max(...slopes.map(Math.abs))*1e-6;
        const positive=slopes.every(s=>s>=-tol),negative=slopes.every(s=>s<=tol);
        if(positive||negative) {
            const suffix=positive?'growth':'decay';
            if(Math.max(...slopes)-Math.min(...slopes)<=tol) return `linear_${suffix}`;
            if(values.length>=4 && Math.min(...values)>0) {
                const logs=values.map(Math.log), rates=logs.slice(1).map((x,i)=>(x-logs[i])/deltas[i]);
                if(Math.max(...rates)-Math.min(...rates)<=Math.max(...rates.map(Math.abs))*1e-4) return `exponential_${suffix}`;
            }
            const curvature=slopes.slice(1).map((s,i)=>s-slopes[i]);
            if(curvature.every(c=>c>=-tol)) return positive?'accelerating_growth':'slowing_decline';
            if(curvature.every(c=>c<=tol)) return positive?'slowing_growth':'accelerating_decline';
            return positive?'monotonic_growth':'monotonic_decline';
        }
        const signs=slopes.filter(s=>Math.abs(s)>tol).map(s=>s>0?1:-1);
        const turns=signs.slice(1).filter((s,i)=>s!==signs[i]).length;
        if(turns>=3) return 'oscillating';
        if(turns===1) return signs[0]>0?'peak_and_decline':'trough_and_recovery';
        return 'complex';
    },
    detectPeaks(time,values) {
        const peaks=[];
        for(let i=1;i<values.length-1;i++) {
            const type=values[i]>values[i-1]&&values[i]>values[i+1]?'peak':values[i]<values[i-1]&&values[i]<values[i+1]?'trough':null;
            if(type) peaks.push({type,time:time[i],value:values[i],index:i});
        }
        return peaks;
    },
    detectEquilibrium(values,threshold=0.01) {
        if(values.length<10) return null;
        const start=Math.min(Math.floor(values.length*.8),values.length-3),tail=values.slice(start);
        const {scale,scaled,mean,std}=this.moments(tail),globalScale=values.reduce((m,v)=>Math.max(m,Math.abs(v)),0);
        const denominator=scale?Math.max(Math.abs(mean),globalScale/scale*1e-12):1;
        const variation=std/denominator,span=(Math.max(...scaled)-Math.min(...scaled))/denominator,stable=span<=threshold;
        return {reached:stable,start_index:start,equilibrium_value:this.finite(scale*mean),variation:this.finite(variation),relative_span:this.finite(span),status:stable?'nearly_stable_tail':'varying_tail',assessed_samples:tail.length,proves_equilibrium:false};
    },
    correlationRecords(values) {
        const names=Object.keys(values),correlations={},records=[];
        const moments=Object.fromEntries(names.map(name=>[name,this.moments(values[name])]));
        let assessed=0;
        for(let i=0;i<names.length;i++) for(let j=i+1;j<names.length;j++) {
            if(assessed>=2000) break;
            assessed++;
            const a=values[names[i]],b=values[names[j]];
            if(a.length<3) continue;
            const x=moments[names[i]],y=moments[names[j]];
            if(!x.std||!y.std) continue;
            let corr=this.sum(x.scaled.map((v,k)=>((v-x.mean)/x.std)*((y.scaled[k]-y.mean)/y.std)/a.length));
            corr=Math.round(Math.max(-1,Math.min(1,corr))*1000)/1000;
            correlations[`${names[i]}|${names[j]}`]=corr;
            records.push({variables:[names[i],names[j]],correlation:corr,samples:a.length});
        }
        const total=names.length*(names.length-1)/2;
        return {correlations,records,coverage:{total_pairs:total,assessed_pairs:assessed,omitted_pairs:total-assessed,limit:2000}};
    },
    computeCorrelations(values) { return this.correlationRecords(values).correlations; },
    deltaRate(first,last,dt) {
        const scale=Math.max(Math.abs(first),Math.abs(last));
        if(!scale) return 0;
        const delta=last/scale-first/scale;
        if(!delta) return 0;
        const direct=delta*(scale/dt);
        if(Number.isFinite(direct)&&direct!==0) return direct;
        return this.finite(Math.sign(delta)*Math.exp(Math.log(Math.abs(delta))+Math.log(scale)-Math.log(dt)));
    },
    computeDerivatives(time, values) {
        const derivatives=Object.create(null);
        for(const [name,vals] of Object.entries(values)) {
            const velocity=vals.slice(1).map((v,i)=>this.deltaRate(vals[i],v,time[i+1]-time[i]));
            const acceleration=velocity.slice(1).map((v,i)=>v===null||velocity[i]===null?null:this.deltaRate(velocity[i],v,(time[i+2]-time[i])/2));
            const maxAbs=arr=>{const finite=arr.filter(Number.isFinite);return finite.length?Math.max(...finite.map(Math.abs)):null;};
            derivatives[name]={velocity,acceleration,maxVelocity:maxAbs(velocity),avgVelocity:time.length>1?this.deltaRate(vals[0],vals.at(-1),time.at(-1)-time[0]):null,maxAcceleration:maxAbs(acceleration)};
        }
        return derivatives;
    },
    // Historical method name retained; this compares raw variance, not sensitivity.
    computeSensitivity(values) {
        const entries=Object.entries(values),result=Object.create(null);
        let globalScale=0;
        for(const [,series] of entries) for(const value of series) globalScale=Math.max(globalScale,Math.abs(value));
        const variances=Object.create(null);
        for(const [name,series] of entries) {
            const scaled=series.map(v=>globalScale?v/globalScale:0),mean=this.sum(scaled)/scaled.length;
            variances[name]=this.sum(scaled.map(v=>(v-mean)**2))/scaled.length;
        }
        const total=this.sum(Object.values(variances));
        for(const [name] of entries) {
            const share=total?variances[name]/total:0;
            result[name]={variance:this.finite(variances[name]*globalScale*globalScale),relativeContribution:share*100,impact:share>.3?'high':share>.1?'medium':'low'};
        }
        return result;
    },
    render() {
        if (!this.container) return;

        if (!this.results || !this.statistics) {
            this.container.innerHTML = `
                <div class="analytics-placeholder">
                    <p>${this.error ? App.escapeHtml(this.error) : 'Run a simulation to see analytics'}</p>
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
        html += this.renderSeriesSection();

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
        this.container.style.minWidth = '0';
        this.container.querySelectorAll('.stats-table-wrapper').forEach(wrapper => {
            wrapper.style.overflowX = 'auto';
            wrapper.tabIndex = 0;
            wrapper.setAttribute('aria-label', 'Scrollable analytics table');
        });
        this.container.querySelectorAll('th').forEach(th => th.setAttribute('scope', 'col'));
        this.container.querySelectorAll('.var-name,.pattern-var,.peak-var,.correlation-vars,.sensitivity-var').forEach(label => {
            label.style.overflowWrap = 'anywhere';
        });

        this.container.querySelector('[data-analysis-series]')?.addEventListener('change', event => {
            this.focusedSeries = event.target.value;
            this.onFocusedSeriesChanged?.(this.focusedSeries);
            this.container.querySelector('.analysis-series-detail').innerHTML = this.renderSeriesDetail(this.focusedSeries);
        });

        // Add event listeners for collapsible sections
        this.container.querySelectorAll('.analytics-section-header').forEach(header => {
            header.tabIndex = 0;
            header.setAttribute('role', 'button');
            const title = header.querySelector('.section-title').textContent;
            const expanded = this.sectionState?.[title] ?? header.parentElement.classList.contains('analytics-summary');
            header.parentElement.classList.toggle('collapsed', !expanded);
            header.setAttribute('aria-expanded', String(expanded));
            const toggle = () => {
                const section = header.parentElement;
                section.classList.toggle('collapsed');
                const open = !section.classList.contains('collapsed');
                header.setAttribute('aria-expanded', String(open));
                (this.sectionState ||= {})[title] = open;
                if (open) this.renderSparklines();
            };
            header.addEventListener('click', toggle);
            header.addEventListener('keydown', event => {
                if(event.key === 'Enter' || event.key === ' ') { event.preventDefault(); toggle(); }
            });
        });
    },

    renderSeriesSection() {
        const names = Object.keys(this.statistics.statistics);
        if (!names.includes(this.focusedSeries)) this.focusedSeries = names[0];
        return `<section class="analysis-explorer" aria-label="Series detail">
            <div class="analysis-eyebrow">Explore a series</div>
            <label class="analysis-series-label">Series<select data-analysis-series aria-label="Analysis series">${names.map(name => `<option value="${App.escapeHtml(name)}" ${name === this.focusedSeries ? 'selected' : ''}>${App.escapeHtml(name)}</option>`).join('')}</select></label>
            <div class="analysis-series-detail">${this.renderSeriesDetail(this.focusedSeries)}</div>
        </section>`;
    },
    renderSeriesDetail(name) {
        const s = this.statistics.statistics[name];
        if (!s || s.error) return '<p class="section-description">Statistics unavailable for this series.</p>';
        const pattern = this.getPatternInfo(this.statistics.patterns[name]);
        const vals = this.results.values[name], time = this.results.time;
        const scaled = this.moments(vals).scaled;
        const lo = Math.min(...scaled), hi = Math.max(...scaled), duration = time.at(-1) - time[0];
        // SVG viewBox keeps the trace crisp at any panel width; all recorded points are retained.
        const points = scaled.map((v,i) => `${duration ? 4 + (time[i]-time[0])/duration*292 : 150},${hi===lo ? 40 : 72-(v-lo)/(hi-lo)*64}`).join(' ');
        const metric = (label,value) => `<div class="analysis-metric"><dt>${label}</dt><dd>${this.formatNumber(value)}</dd></div>`;
        return `<div class="analysis-result"><span>Final value</span><strong title="${s.final}">${this.formatNumber(s.final)}</strong><span class="analysis-pattern">${pattern.label}</span></div>
            <svg class="analysis-trace" viewBox="0 0 300 80" role="img" aria-label="${App.escapeHtml(name)} over recorded time"><path d="M4 72H296" class="trace-baseline"/><polyline points="${points}"/></svg>
            <div class="analysis-time"><span>t = ${this.formatNumber(time[0])}</span><span>${this.formatNumber(time.at(-1))}</span></div>
            <dl class="analysis-metrics">${metric('Initial',s.initial)}${metric('Net change',s.total_change)}${metric('Minimum',s.min)}${metric('Maximum',s.max)}${metric('Sample mean',s.mean)}${metric('Time average',s.time_weighted_mean)}${metric('Std. deviation',s.std)}<div class="analysis-metric"><dt>Change</dt><dd>${s.percent_change == null ? 'N/A' : s.percent_change.toLocaleString('en-US',{maximumFractionDigits:1})+'%'}</dd></div></dl>
            <details class="analysis-method"><summary>How to read these metrics</summary><p>Sample mean and population standard deviation weight each recorded sample equally. Time average uses trapezoidal integration. Change is relative to the initial value; it is undefined from zero. N/A also marks an unrepresentable derived value. The trace describes recorded samples, not scientific validation.</p></details>`;
    },

    /**
     * Render summary section
     */
    renderSummarySection() {
        const timeRange = this.statistics.time_range;

        return `
            <div class="analytics-section analytics-summary">
                <div class="analytics-section-header">
                    <span class="section-icon" aria-hidden="true">&#128200;</span>
                    <span class="section-title">Simulation Summary</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    <div class="summary-grid">
                        <div class="summary-item">
                            <span class="summary-label">Time Range</span>
                            <span class="summary-value">${this.formatNumber(timeRange.start)} → ${this.formatNumber(timeRange.end)}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Recorded samples</span>
                            <span class="summary-value">${timeRange.steps}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Series</span>
                            <span class="summary-value">${Object.keys(this.statistics.statistics).length}</span>
                        </div>
                    </div>
                    <p class="section-description">${this.statistics.offline_fallback ? 'Computed locally while the statistics service was unavailable. ' : ''}These describe recorded samples. Patterns do not establish scientific validity, causation or equilibrium.</p>
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
                    <td class="var-name">${App.escapeHtml(name)}</td>
                    <td>${this.formatNumber(s.min)}</td>
                    <td>${this.formatNumber(s.max)}</td>
                    <td>${this.formatNumber(s.mean)}</td>
                    <td>${this.formatNumber(s.time_weighted_mean)}</td>
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
                    <span class="section-icon" aria-hidden="true">&#128202;</span>
                    <span class="section-title">Summary Statistics</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    <p class="table-scroll-hint">All series · scroll horizontally for every metric</p>
                    <div class="stats-table-wrapper">
                        <table class="stats-table">
                            <thead>
                                <tr>
                                    <th>Variable</th>
                                    <th>Min</th>
                                    <th>Max</th>
                                    <th>Sample mean</th>
                                    <th>Time average</th>
                                    <th>Std Dev</th>
                                    <th>Initial</th>
                                    <th>Final</th>
                                    <th>Change %</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    </div>
                    <p class="section-description">Population standard deviation weights each sample equally. Time average uses trapezoidal integration. Percent change is (final − initial) / initial; it is undefined from zero and can be counterintuitive with a negative initial value. N/A also marks an unrepresentable derived value.</p>
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

        for (const [index, [name, pattern]] of Object.entries(Object.entries(patterns))) {
            const patternInfo = this.getPatternInfo(pattern);
            const eq = equilibria[name];

            content += `
                <div class="pattern-card">
                    <div class="pattern-header">
                        <span class="pattern-var">${App.escapeHtml(name)}</span>
                        <span class="pattern-icon" style="color: ${patternInfo.color}">${patternInfo.icon}</span>
                    </div>
                    <div class="pattern-body">
                        <span class="pattern-name" style="color: ${patternInfo.color}">${patternInfo.label}</span>
                        ${eq ? `
                            <span class="equilibrium-badge ${eq.reached ? 'reached' : 'not-reached'}">
                                ${eq.reached ? `Nearly stable tail: ${this.formatNumber(eq.equilibrium_value)}` : 'Tail varies'}
                            </span>
                        ` : ''}
                    </div>
                    <div class="pattern-sparkline" data-analytics-sparkline="${index}" aria-hidden="true"></div>
                </div>
            `;
        }

        content += '</div>';

        // Render sparklines after DOM is updated
        setTimeout(() => this.renderSparklines(), 0);

        return `
            <div class="analytics-section">
                <div class="analytics-section-header">
                    <span class="section-icon" aria-hidden="true">&#128208;</span>
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
            'constant': { label: 'Constant', icon: '&#8594;', color: '#90a4ae' },
            'exponential_growth': { label: 'Approximately exponential growth', icon: '&#8679;&#8679;', color: '#4CAF50' },
            'linear_growth': { label: 'Linear Growth', icon: '&#8599;', color: '#8BC34A' },
            'exponential_decay': { label: 'Approximately exponential decay', icon: '&#8681;&#8681;', color: '#f44336' },
            'accelerating_growth': { label: 'Accelerating growth', icon: '&#8599;', color: '#4CAF50' },
            'slowing_growth': { label: 'Slowing growth', icon: '&#8599;', color: '#8BC34A' },
            'monotonic_growth': { label: 'Monotonic growth', icon: '&#8599;', color: '#8BC34A' },
            'accelerating_decline': { label: 'Accelerating decline', icon: '&#8600;', color: '#f44336' },
            'slowing_decline': { label: 'Slowing decline', icon: '&#8600;', color: '#FF5722' },
            'monotonic_decline': { label: 'Monotonic decline', icon: '&#8600;', color: '#FF5722' },
            'trough_and_recovery': { label: 'Trough and recovery', icon: '&#8595;&#8593;', color: '#2196F3' },
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

        for (const [index, [name, vals]] of Object.entries(Object.entries(values))) {
            const container = this.container.querySelector(`[data-analytics-sparkline="${index}"]`);
            if (!container) continue;

            const width = container.clientWidth || 100;
            const height = 30;

            d3.select(container).selectAll('svg').remove();
            const svg = d3.select(container)
                .append('svg')
                .attr('width', width)
                .attr('height', height);

            const validVals = this.moments(vals).scaled;
            if (validVals.length === 0) continue;

            const xScale = d3.scaleLinear()
                .domain([time[0], time.at(-1)])
                .range([2, width - 2]);

            const yScale = d3.scaleLinear()
                .domain([Math.min(...validVals), Math.max(...validVals)])
                .range([height - 2, 2]);

            const line = d3.line()
                .x((d, i) => xScale(time[i]))
                .y(d => yScale(d))
                .defined(Number.isFinite)
                .curve(d3.curveMonotoneX);

            const pattern = this.statistics.patterns[name];
            const color = this.getPatternInfo(pattern).color;

            svg.append('path')
                .datum(validVals)
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
                        <span class="section-icon" aria-hidden="true">&#128205;</span>
                        <span class="section-title">Peak Analysis</span>
                        <span class="section-toggle">&#9660;</span>
                    </div>
                    <div class="analytics-section-content">
                        <p class="no-data">No strict local sample peaks or troughs detected. Endpoints and flat plateaus are excluded.</p>
                    </div>
                </div>
            `;
        }

        // Sort by time
        allPeaks.sort((a, b) => a.time - b.time);

        // Show only top peaks per variable
        const topPeaks = Object.create(null);
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
                        <span class="peak-var">${App.escapeHtml(name)}</span>
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
                        <span class="peak-var">${App.escapeHtml(name)}</span>
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
                    <span class="section-icon" aria-hidden="true">&#128205;</span>
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
        const pairs = this.statistics.correlation_pairs
            ? this.statistics.correlation_pairs.map(record => [record.variables, record.correlation])
            : Object.entries(correlations).map(([pair,corr]) => [pair.split('|'),corr]);
        const coverage = this.statistics.correlation_coverage;
        const coverageText = coverage?.omitted_pairs ? ` ${coverage.assessed_pairs} of ${coverage.total_pairs} pairs assessed; ${coverage.omitted_pairs} pairs omitted by the computation limit.` : '';

        if (pairs.length === 0) {
            return `
                <div class="analytics-section">
                    <div class="analytics-section-header">
                        <span class="section-icon" aria-hidden="true">&#128279;</span>
                        <span class="section-title">Correlations</span>
                        <span class="section-toggle">&#9660;</span>
                    </div>
                    <div class="analytics-section-content">
                        <p class="no-data">No defined correlations: at least three aligned samples and two varying series are required.${coverageText}</p>
                    </div>
                </div>
            `;
        }

        // Sort by absolute correlation
        pairs.sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

        let content = '<div class="correlations-list">';
        pairs.forEach(([[var1, var2], corr]) => {
            const strength = Math.abs(corr) > 0.7 ? 'strong' : Math.abs(corr) > 0.4 ? 'moderate' : 'weak';
            const direction = corr > 0 ? 'positive' : 'negative';
            const barWidth = Math.abs(corr) * 100;

            content += `
                <div class="correlation-item">
                    <div class="correlation-vars">
                        <span>${App.escapeHtml(var1)}</span>
                        <span class="correlation-arrow">&#8596;</span>
                        <span>${App.escapeHtml(var2)}</span>
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
                    <span class="section-icon" aria-hidden="true">&#128279;</span>
                    <span class="section-title">Correlations</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    <p class="section-description">Pearson correlation across recorded samples measures association. Shared time trends can create strong correlations without causal influence.${coverageText}</p>
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
            const direction = d.avgVelocity === null ? 'unavailable' : d.avgVelocity > 0 ? 'increasing' :
                             d.avgVelocity < 0 ? 'decreasing' : 'stable';
            const dirClass = d.avgVelocity > 0 ? 'positive' :
                            d.avgVelocity < 0 ? 'negative' : '';
            const arrow = d.avgVelocity > 0 ? '&#9650;' :
                         d.avgVelocity < 0 ? '&#9660;' : '&#8212;';

            rows += `
                <tr>
                    <td class="var-name">${App.escapeHtml(name)}</td>
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
                    <span class="section-icon" aria-hidden="true">&#128200;</span>
                    <span class="section-title">Rate of Change</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    <p class="table-scroll-hint">All series · scroll horizontally for every metric</p>
                    <div class="stats-table-wrapper">
                        <table class="stats-table">
                            <thead>
                                <tr>
                                    <th>Variable</th>
                                    <th>Net change / duration</th>
                                    <th>Max |interval rate|</th>
                                    <th>Max |acceleration|</th>
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
                        <span class="sensitivity-var">${App.escapeHtml(name)}</span>
                        <span class="sensitivity-value">${s.relativeContribution.toFixed(1)}%</span>
                    </div>
                    <div class="sensitivity-bar-container">
                        <div class="sensitivity-bar ${impactClass}" style="width: ${barWidth}%"></div>
                    </div>
                    <div class="sensitivity-label ${impactClass}">${s.impact} variance share</div>
                </div>
            `;
        });

        content += '</div>';

        return `
            <div class="analytics-section">
                <div class="analytics-section-header">
                    <span class="section-icon" aria-hidden="true">&#9881;</span>
                    <span class="section-title">Variance Comparison</span>
                    <span class="section-toggle">&#9660;</span>
                </div>
                <div class="analytics-section-content">
                    <p class="section-description" style="color: var(--text-muted); font-size: 0.8rem; margin-bottom: 0.75rem;">
                        Shares of raw series variance depend on units and scale. This does not measure causal influence or parameter sensitivity.
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
        if (n === 0) return '0';
        if (Math.abs(n) < 0.01 || Math.abs(n) >= 1000000) {
            return n.toExponential(2);
        }
        return n.toLocaleString('en-US', {maximumFractionDigits: 2});
    }
};
