const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(require('node:path').join(__dirname, '../static/openrouter.js'), 'utf8');
const elements = {};
function element(id) { return elements[id] ||= { value: '', checked: false, type: 'password', textContent: '', isConnected: true, handlers: {}, addEventListener(type, fn) { this.handlers[type] = fn; }, setAttribute() {}, focus() {} }; }
const dialog = { ...element('dialog'), open: false, querySelector: element, querySelectorAll(selector) { return [element(selector)]; }, showModal() { this.open = true; }, close() { this.open = false; this.handlers.close(); } };
let stored = null, calls = [], changed = 0;
const context = { URL, Headers, CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init.detail; } }, localStorage: { getItem() { return stored; }, setItem(k,v) { stored=v; }, removeItem() { stored=null; } }, document: { activeElement: element('opener'), addEventListener() {}, createElement() { return dialog; }, body: { appendChild() {} } }, window: { location: { href: 'https://example.test/', origin: 'https://example.test' }, dispatchEvent() { changed++; } }, fetch: async (url, options) => { calls.push({url, options}); return {ok:true, json:async()=>({available:true,verified:true})}; } };
vm.createContext(context); vm.runInContext(source, context);
const ui = context.window.OpenRouterUI;
(async () => {
  await ui.request('/api/llm/status'); assert.equal(calls.at(-1).options.headers, undefined);
  ui.open(); assert.equal(elements['#openrouter-remember'].checked, false);
  elements['#openrouter-key'].value='sk-test-private';
  elements['[data-save]'].handlers.click(); assert.equal(stored,null); assert.ok(changed);
  for (const url of ['/api/llm/generate','/api/llm/modify','/api/llm/refine-model','/api/analyze','/api/analyze/ask','/api/analyze/status']) {
    await ui.request(url,{method:'POST',headers:{'Content-Type':'application/json'}});
    assert.equal(calls.at(-1).options.headers.get('X-OpenRouter-Key'),'sk-test-private');
    assert.equal(calls.at(-1).options.headers.get('X-OpenRouter-Model'),'openrouter/free');
    assert.equal(calls.at(-1).options.redirect,'error');
  }
  for (const url of ['/api/llm/find-equilibrium','/api/llm/fit-to-data','/api/models','/api/workspaces','https://evil.test/api/llm/generate','/api/llm/generate/extra']) {
    await ui.request(url); assert.equal(calls.at(-1).options.headers,undefined);
  }
  await elements['[data-test]'].handlers.click(); assert.match(elements['[data-status]'].textContent,/Connection verified/);
  elements['#openrouter-remember'].checked=true; elements['[data-save]'].handlers.click(); assert.equal(stored,'sk-test-private');
  elements['[data-clear]'].handlers.click(); assert.equal(stored,null); assert.equal(elements['#openrouter-key'].value,'');
  await ui.request('/api/llm/status'); assert.equal(calls.at(-1).options.headers,undefined);
  context.fetch=async()=>({ok:false,status:401,json:async()=>({detail:'never reflect arbitrary provider text'})});
  elements['#openrouter-key'].value='sk-invalid'; await elements['[data-test]'].handlers.click(); assert.match(elements['[data-status]'].textContent,/rejected/); assert.doesNotMatch(elements['[data-status]'].textContent,/verified|arbitrary/);
  dialog.close(); assert.equal(elements['#openrouter-key'].value,'');
  console.log('OpenRouter UI: scoped headers, free-only model, opt-in storage, disconnect, verified test and auth failure passed.');
})().catch(error=>{ console.error(error); process.exitCode=1; });
