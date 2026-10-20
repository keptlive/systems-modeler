/** Export structure contract; this does not substitute for browser SVG decoding. */
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');

class Element {
  constructor(tag, attrs = {}, computed = {}) {
    this.tagName = tag; this.attributes = {...attrs}; this.children = [];
    this.parentElement = null; this.computed = {...computed}; this.textContent = '';
    this.style = {values: {}, setProperty(key, value) { this.values[key] = value; }};
  }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  appendChild(node) { node.remove(); this.children.push(node); node.parentElement = this; return node; }
  insertBefore(node, before) {
    node.remove(); const index = this.children.indexOf(before);
    this.children.splice(index < 0 ? this.children.length : index, 0, node);
    node.parentElement = this; return node;
  }
  remove() {
    if (this.parentElement) {
      const list = this.parentElement.children; list.splice(list.indexOf(this), 1);
      this.parentElement = null;
    }
  }
  get firstChild() { return this.children[0] || null; }
  querySelectorAll(selector) {
    const descendants = this.children.flatMap(child => [child, ...child.querySelectorAll('*')]);
    return selector === '*' ? descendants : descendants.filter(node => node.tagName === selector);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  cloneNode(deep) {
    const copy = new Element(this.tagName, this.attributes, this.computed);
    copy.textContent = this.textContent; copy.style.values = {...this.style.values};
    if (deep) for (const child of this.children) copy.appendChild(child.cloneNode(true));
    return copy;
  }
}
const snapshot = node => ({tag: node.tagName, attrs: {...node.attributes},
  text: node.textContent, style: {...node.style.values}, children: node.children.map(snapshot)});
const measuredWidth = text => Array.from(text).reduce((total, char) => total + (char === 'W' || char.codePointAt(0) > 127 ? 11 : 6), 0);
const document = {createElement(tag) {
  assert.equal(tag, 'canvas'); return {getContext: () => ({font: '', measureText: text => ({width: measuredWidth(text)})})};
}, createElementNS(ns, tag) {
  assert.equal(ns, 'http://www.w3.org/2000/svg'); return new Element(tag);
}};
const sandbox = {document, getComputedStyle: node => ({getPropertyValue: key => node.computed[key] || ''})};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.resolve(__dirname, '../static/js/charts.js'), 'utf8') + ';this.chart = Charts;', sandbox);
const chart = sandbox.chart;
const container = new Element('div'), live = container.appendChild(new Element('svg', {width: '800', height: '350'}));
const plot = live.appendChild(new Element('g'));
const trace = plot.appendChild(new Element('path', {d: 'M0,0L100,100'}, {fill: 'none', stroke: 'rgb(20, 80, 120)', 'stroke-width': '2px', opacity: '0.8'}));
const axis = plot.appendChild(new Element('text', {x: '5', y: '15'}, {fill: 'rgb(200, 210, 220)', 'font-family': 'Arial', 'font-size': '12px'}));
axis.textContent = 'Time';
const foreign = live.appendChild(new Element('foreignObject'));
foreign.appendChild(new Element('button')).textContent = 'Live interactive legend';
chart.container = container;
const wideLabel = 'W'.repeat(96) + '漢字😀'.repeat(6);
const longLabel = '<Full & exact "series"> ' + 'Long variable name '.repeat(12);
chart.options = {variables: {
  [longLabel]: {visible: true, color: '#aabbcc'},
  Hidden: {visible: false, color: '#ff0000'},
  Second: {visible: true, color: '#112233'},
  [wideLabel]: {visible: true, color: '#445566'},
}};
chart.getDimensions = () => ({width: 800, height: 350});
const before = snapshot(live), exported = chart.buildExportSvg();
assert.deepEqual(snapshot(live), before, 'Export must not mutate the live SVG or its interactive legend');
assert.notEqual(exported.svg, live);
assert.equal(exported.width, 800);
assert.ok(exported.height > 350, 'Full legend gets space below the unchanged plot');
assert.equal(exported.svg.getAttribute('viewBox'), `0 0 800 ${exported.height}`);
assert.equal(exported.svg.querySelectorAll('foreignObject').length, 0);
assert.equal(live.querySelectorAll('foreignObject').length, 1);
const exportedTrace = exported.svg.querySelector('path');
assert.equal(exportedTrace.getAttribute('d'), trace.getAttribute('d'));
assert.equal(exportedTrace.style.values.stroke, 'rgb(20, 80, 120)');
assert.equal(exportedTrace.style.values.fill, 'none');
assert.equal(exportedTrace.style.values['stroke-width'], '2px');
assert.equal(exported.svg.querySelector('text').style.values['font-size'], '12px');
const labels = exported.svg.querySelectorAll('text').filter(node => node.querySelectorAll('tspan').length);
const labelText = node => node.querySelectorAll('tspan').map(span => span.textContent).join('');
assert.deepEqual(labels.map(labelText).sort(), [longLabel, 'Second', wideLabel].sort());
assert.ok(labels.every(node => Number(node.getAttribute('y')) > 350));
assert.ok(labels.every(node => node.children.every(span => measuredWidth(span.textContent) <= (800-32)/2-30)), 'Wide characters must fit each measured legend column');
assert.ok(labels.every(node => node.children.every(span => !/[\uD800-\uDBFF]$/.test(span.textContent))), 'Wrapping must preserve complete Unicode codepoints');
assert.ok(labels.every(node => Number(node.getAttribute('y')) + (node.children.length - 1) * 16 < exported.height));
assert.equal(labels[0].getAttribute('y'), labels[1].getAttribute('y'));
assert.ok(Number(labels[2].getAttribute('y')) > Number(labels[0].getAttribute('y')) + (labels[0].children.length - 1) * 16,
  'A multiline row must reserve enough height before the next row');
const background = exported.svg.firstChild;
assert.equal(background.tagName, 'rect');
assert.equal(background.getAttribute('height'), String(exported.height));
assert.equal(background.getAttribute('width'), '800');
assert.equal(exported.svg.querySelectorAll('rect').filter(node => node.getAttribute('fill') === '#ff0000').length, 0);

chart.getDimensions = () => ({width: 390, height: 280});
const mobile = chart.buildExportSvg();
const mobileLabels = mobile.svg.querySelectorAll('text').filter(node => node.querySelectorAll('tspan').length);
assert.equal(new Set(mobileLabels.map(node => node.getAttribute('x'))).size, 1, 'Narrow exports use one column');
assert.ok(mobile.height - 280 > exported.height - 350, 'A narrow export reserves more legend space below its plot');
for (const option of Object.values(chart.options.variables)) option.visible = false;
const empty = chart.buildExportSvg();
assert.equal(empty.height, 280, 'No selected series should not reserve an empty export legend');
assert.equal(empty.svg.querySelectorAll('tspan').length, 0);
chart.container = new Element('div');
assert.equal(chart.buildExportSvg(), null);
console.log('Export DOM contract passed: full selected labels, multiline row spacing, SVG-only styled clone, narrow layout, background and live DOM preservation. Browser PNG decode remains a separate acceptance check.');



