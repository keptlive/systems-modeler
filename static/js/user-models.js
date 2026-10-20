/**
 * User Models - Manage user saved models in localStorage
 */
const UserModels = {
    STORAGE_KEY: "systems-modeler-user-models",

    getAll() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            return [];
        }
    },

    save(model) {
        const models = this.getAll();
        const id = model.id || this.generateId();
        
        const existing = models.findIndex(m => m.id === id);
        const savedModel = {
            id,
            name: model.name || "Untitled",
            description: model.description || "",
            source: model.source || null,
            reference: model.reference || null,
            category: model.category || null,
            stocks: model.stocks || [],
            flows: model.flows || [],
            variables: model.variables || [],
            connectors: model.connectors || [],
            tables: model.tables || [],
            time_settings: model.time_settings || { start: 0, end: 100, dt: 0.25 },
            savedAt: new Date().toISOString()
        };

        if (existing >= 0) {
            models[existing] = savedModel;
        } else {
            models.push(savedModel);
        }

        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(models));
        return savedModel;
    },

    get(id) {
        return this.getAll().find(m => m.id === id);
    },

    delete(id) {
        const models = this.getAll().filter(m => m.id !== id);
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(models));
    },

    generateId() {
        return "user-" + Date.now() + "-" + Math.random().toString(36).substr(2, 9);
    },

    populateDropdown() {
        const select = document.getElementById("model-select");
        if (!select) return;

        const models = this.getAll();
        select.innerHTML = "<option value=\"\">My Models...</option>";
        
        if (models.length === 0) {
            const opt = document.createElement("option");
            opt.disabled = true;
            opt.textContent = "(No saved models)";
            select.appendChild(opt);
        } else {
            models.sort((a, b) => new Date(b.savedAt) - new Date(a.savedAt));
            models.forEach(model => {
                const opt = document.createElement("option");
                opt.value = model.id;
                opt.textContent = model.name;
                select.appendChild(opt);
            });
        }
    }
};

document.addEventListener("DOMContentLoaded", () => UserModels.populateDropdown());
