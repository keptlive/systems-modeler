/* Optional per-browser OpenRouter credentials. Never part of a model or workspace. */
(function () {
    'use strict';
    const storageKey = 'stockflow.openrouter.key.v1';
    let key = '';
    let remembered = false;
    let dialog;
    let opener;
    let revision = 0;
    try { key = localStorage.getItem(storageKey) || ''; remembered = !!key; } catch (_) {}
    const allowed = /^\/api\/(?:llm\/(?:status|test|generate|modify|refine-model)|analyze(?:\/(?:status|ask))?)$/;
    function request(url, options = {}) {
        const target = new URL(url, window.location.href);
        if (!key || target.origin !== window.location.origin || !allowed.test(target.pathname)) return fetch(url, options);
        const headers = new Headers(options.headers || {});
        headers.set('X-OpenRouter-Key', key);
        headers.set('X-OpenRouter-Model', 'openrouter/free');
        return fetch(url, { ...options, headers, redirect: 'error' });
    }
    function refresh() {
        window.dispatchEvent(new CustomEvent('openrouterchange', { detail: { configured: !!key } }));
        if (typeof LLMInterface !== 'undefined') LLMInterface.checkStatus();
        if (typeof AIAgent !== 'undefined') AIAgent.checkAvailability();
    }
    function status(message) { dialog.querySelector('[data-status]').textContent = message; }
    function save() {
        const value = dialog.querySelector('#openrouter-key').value.trim();
        if (!value || /\s/.test(value)) { status('Enter a valid OpenRouter key without spaces.'); return false; }
        key = value;
        revision++;
        remembered = dialog.querySelector('#openrouter-remember').checked;
        try {
            localStorage.removeItem(storageKey);
            if (remembered) localStorage.setItem(storageKey, key);
        } catch (_) {
            remembered = false;
            dialog.querySelector('#openrouter-remember').checked = false;
            status('Key is active in memory. Browser storage is unavailable; it was not remembered.');
            refresh();
            return true;
        }
        status(remembered ? 'Key saved on this browser. Connection has not been tested.' : 'Key active in this tab until reload. Connection has not been tested.');
        refresh();
        return true;
    }
    async function test() {
        if (!save()) return;
        const current = revision;
        const button = dialog.querySelector('[data-test]');
        button.disabled = true;
        status('Testing a small request with OpenRouter Free…');
        try {
            const response = await request('/api/llm/test', { method: 'POST' });
            const data = await response.json();
            if (current !== revision) return;
            if (response.ok && data.available === true && data.verified === true) status('Connection verified with a successful free-model response. Free-model limits and availability still apply.');
            else status(response.status === 401 ? 'OpenRouter rejected this key. Check the key and try again.' : response.status === 429 ? 'OpenRouter is rate limited. Try again later.' : 'Connection could not be verified. Check your key, network, and free-model availability.');
        } catch (_) {
            if (current === revision) status('Connection could not be verified. Check your network and try again.');
        } finally { button.disabled = false; }
    }
    function disconnect() {
        key = ''; remembered = false; revision++;
        try { localStorage.removeItem(storageKey); } catch (_) {}
        dialog.querySelector('#openrouter-key').value = '';
        dialog.querySelector('#openrouter-remember').checked = false;
        status('Personal key cleared. The app will use its default server AI configuration when available.');
        refresh();
    }
    function create() {
        dialog = document.createElement('dialog');
        dialog.id = 'openrouter-dialog';
        dialog.setAttribute('aria-labelledby', 'openrouter-title');
        dialog.innerHTML = `<form method="dialog" class="openrouter-form">
            <div class="openrouter-heading"><h2 id="openrouter-title">AI settings</h2><button type="button" data-close aria-label="Close AI settings">×</button></div>
            <p>Use your OpenRouter key for AI tools. Connect agent through MCP also remains available.</p>
            <label for="openrouter-key">OpenRouter API key</label>
            <div class="openrouter-key-row"><input id="openrouter-key" type="password" autocomplete="off" autocapitalize="none" spellcheck="false" placeholder="Paste your key"><button type="button" data-show aria-pressed="false">Show</button></div>
            <label for="openrouter-model">Model</label><select id="openrouter-model"><option value="openrouter/free">OpenRouter Free — automatic free model</option></select>
            <p class="openrouter-note">Free models only; no paid fallback. Limits and outages apply. Your key passes through this server to OpenRouter for AI requests. It is never saved on the server or in exports.</p>
            <label class="openrouter-remember"><input type="checkbox" id="openrouter-remember"> Remember key on this browser</label>
            <p class="openrouter-note">Default: memory until reload. Remember stores your key in local storage; use only on a trusted device.</p>
            <p data-status role="status" aria-live="polite"></p>
            <div class="openrouter-actions"><button type="button" data-save>Use key</button><button type="button" data-test>Test connection</button><button type="button" data-clear>Clear / disconnect</button><button type="button" data-close>Done</button></div>
        </form>`;
        document.body.appendChild(dialog);
        dialog.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => dialog.close()));
        dialog.querySelector('[data-show]').addEventListener('click', event => {
            const input = dialog.querySelector('#openrouter-key');
            const show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            event.currentTarget.textContent = show ? 'Hide' : 'Show';
            event.currentTarget.setAttribute('aria-pressed', String(show));
        });
        dialog.querySelector('[data-save]').addEventListener('click', save);
        dialog.querySelector('[data-test]').addEventListener('click', test);
        dialog.querySelector('[data-clear]').addEventListener('click', disconnect);
        dialog.addEventListener('close', () => {
            dialog.querySelector('#openrouter-key').value = '';
            dialog.querySelector('#openrouter-key').type = 'password';
            dialog.querySelector('[data-show]').textContent = 'Show';
            dialog.querySelector('[data-show]').setAttribute('aria-pressed', 'false');
            if (opener && opener.isConnected) opener.focus();
        });
        dialog.querySelector('form').addEventListener('submit', event => { event.preventDefault(); save(); });
    }
    document.addEventListener('click', event => {
        if (event.target.closest('[data-openrouter-settings]')) window.OpenRouterUI.open();
    });
    window.OpenRouterUI = { request, hasKey: () => !!key, open() {
        if (!dialog) create();
        opener = document.activeElement;
        dialog.querySelector('#openrouter-key').value = key;
        dialog.querySelector('#openrouter-remember').checked = remembered;
        status(key ? 'Personal key configured. Test connection to verify availability.' : 'Using the app’s default server AI configuration when available.');
        if (!dialog.open) dialog.showModal();
        dialog.querySelector('#openrouter-key').focus();
    } };
})();

