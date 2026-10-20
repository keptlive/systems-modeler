/** Inspect the active model's inputs without saving or rewriting it. */
const ModelValidation = {
    init() {
        const button = document.createElement('button');
        button.id = 'btn-validate';
        button.textContent = 'Check inputs';
        button.title = 'Inspect initial values, equations, connections and sources';
        button.className = document.getElementById('sim-settings-cancel')?.className || '';
        document.getElementById('sim-settings-cancel')?.before(button);
        button.addEventListener('click', () => this.run(button));
    },

    async run(button) {
        button.disabled = true;
        try {
            const response = await fetch('/api/validate', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model: App.modelSnapshot()}), signal: AbortSignal.timeout(20000)
            });
            if (!response.ok) throw new Error('Could not check model inputs');
            this.show(await response.json());
            return true;
        } catch (error) {
            App.showToast(error.message, 'error');
            return false;
        } finally {
            button.disabled = false;
        }
    },

    show(report) {
        let dialog = document.getElementById('input-check-dialog');
        if (!dialog) {
            dialog = document.createElement('dialog');
            dialog.id = 'input-check-dialog';
            dialog.style.cssText = 'background:var(--bg-secondary,#1f2937);color:var(--text-primary,#e5e7eb);border:1px solid #475569;border-radius:10px;padding:24px;width:min(750px,90vw);max-height:85vh;overflow:auto';
            document.body.appendChild(dialog);
        }
        dialog.replaceChildren();
        const add = (tag, text, parent = dialog) => {
            const element = document.createElement(tag);
            element.textContent = text;
            parent.appendChild(element);
            return element;
        };
        add('h2', 'Model input check');
        add('h3', report.model);
        add('p', report.valid ? 'The structural and one-step numerical checks completed.' : 'Some inputs need investigation before this model can run.');
        add('p', 'This check does not establish scientific validity, dimensional consistency, or agreement with the cited source.');
        const issues = add('ul', '');
        for (const issue of report.issues) {
            add('li', `${issue.severity === 'error' ? 'Needs attention' : 'Review'}${issue.element ? ` — ${issue.element}` : ''}: ${issue.message}`, issues);
        }
        const inputs = report.inputs;
        add('h3', 'Initial stocks');
        const stocks = add('ul', '');
        for (const stock of inputs.initial_stocks) {
            add('li', `${stock.name}: ${stock.initial_equation || stock.initial_value}${stock.units ? ` ${stock.units}` : ' (units not supplied)'}`, stocks);
        }
        add('h3', 'Parameters and equations');
        const variables = add('ul', '');
        for (const variable of inputs.parameters_and_auxiliaries) add('li', `${variable.name} = ${variable.equation}`, variables);
        add('h3', 'Flows');
        const flows = add('ul', '');
        for (const flow of inputs.flows) add('li', `${flow.name} = ${flow.equation}; ${flow.from_stock || 'external source'} → ${flow.to_stock || 'external sink'}`, flows);
        add('h3', 'Source and settings');
        add('p', inputs.reference || 'No reference supplied.');
        add('p', inputs.source || 'No source link supplied.');
        const ts = inputs.time_settings;
        add('p', `${ts.start} → ${ts.end}; dt ${ts.dt}; ${ts.integration_method.toUpperCase()}`);
        const close = add('button', 'Close input check');
        close.addEventListener('click', () => dialog.close());
        dialog.showModal();
    }
};
document.addEventListener('DOMContentLoaded', () => ModelValidation.init());
