/**
 * Model Library Browser
 * Browse, search, and import models from the library
 */
const Library = {
    models: [],
    categories: [],
    filteredModels: [],
    currentCategory: "all",
    searchQuery: "",
    sortBy: "name",
    isOpen: false,
    expandedModel: null,
    isLoading: false,
    loadError: null,

    /**
     * Initialize library
     */
    async init() {
        this.createModal();
        this.bindEvents();
    },

    /**
     * Load models from API
     */
    async loadModels() {
        this.isLoading = true;
        this.loadError = null;
        this.showLoading();
        
        try {
            const response = await fetch("/api/models/catalog", {signal: AbortSignal.timeout(20000)});
            if (!response.ok) throw new Error(`Library request failed (${response.status})`);
            const data = await response.json();
            this.models = Array.isArray(data) ? data : (data.models || []);
            
            // Extract unique categories
            const cats = new Set();
            this.models.forEach(m => {
                if (m.category) cats.add(m.category);
            });
            this.categories = Array.from(cats).sort();
            
            this.filteredModels = [...this.models];
            this.updateCategoryDropdown();
        } catch (error) {
            console.error("Failed to load models:", error);
            this.models = [];
            this.filteredModels = [];
            this.loadError = error.message;
        } finally {
            this.isLoading = false;
            this.hideLoading();
            this.applyFilters();
        }
    },

    /**
     * Show loading state in modal
     */
    showLoading() {
        const listEl = document.getElementById("library-list");
        if (listEl) {
            listEl.innerHTML = `
                <div class="library-loading">
                    <div class="library-spinner"></div>
                    <div class="library-loading-text">Loading ${this.models.length > 0 ? this.models.length : ""} models...</div>
                    <div class="library-loading-sub">Please wait</div>
                </div>
            `;
        }
    },

    /**
     * Hide loading state
     */
    hideLoading() {
        // Loading is hidden when updateList is called
    },

    /**
     * Update category dropdown with loaded categories
     */
    updateCategoryDropdown() {
        const dropdown = document.getElementById("library-category");
        if (dropdown && this.categories.length > 0) {
            dropdown.innerHTML = `
                <option value="all">All (${this.models.length})</option>
                ${this.categories.map(c => {
                    const count = this.models.filter(m => m.category === c).length;
                    return `<option value="${c}">${this.formatCategory(c)} (${count})</option>`;
                }).join("")}
            `;
        }
    },

    /**
     * Create the modal HTML
     */
    createModal() {
        const modal = document.createElement("div");
        modal.id = "library-modal";
        modal.className = "library-modal";
        modal.setAttribute("role", "dialog");
        modal.setAttribute("aria-modal", "true");
        modal.setAttribute("aria-labelledby", "library-title");
        modal.innerHTML = `
            <div class="library-content">
                <div class="library-header">
                    <h2 id="library-title">Model Library</h2>
                    <span class="library-count" id="library-count">Loading...</span>
                    <button class="library-close" title="Close">&times;</button>
                </div>
                
                <div class="library-controls">
                    <input type="text" id="library-search" placeholder="Search models..." aria-label="Search model library" class="library-search">
                    <select id="library-category" class="library-category" aria-label="Model category">
                        <option value="all">All Categories</option>
                    </select>
                    <select id="library-sort" class="library-sort" aria-label="Sort models">
                        <option value="name">A-Z</option>
                        <option value="category">Category</option>
                    </select>
                </div>
                
                <div class="library-list" id="library-list">
                    <div class="library-loading">
                        <div class="library-spinner"></div>
                        <div class="library-loading-text">Ready to load</div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    },

    /**
     * Format category name for display
     */
    formatCategory(cat) {
        return cat.charAt(0).toUpperCase() + cat.slice(1).replace(/-/g, " ");
    },

    /**
     * Render the model list
     */
    renderModelList() {
        if (this.loadError) return '<div class="library-error">Could not load the model library. <button id="library-retry" class="btn">Retry</button></div>';
        if (this.isLoading) {
            return `
                <div class="library-loading">
                    <div class="library-spinner"></div>
                    <div class="library-loading-text">Loading models...</div>
                </div>
            `;
        }
        
        if (this.filteredModels.length === 0) {
            return `<div class="library-empty">No models found</div>`;
        }

        return this.filteredModels.map(model => {
            const isExpanded = this.expandedModel === model.id;
            const stockCount = model.stock_count ?? (model.stocks || []).length;
            const flowCount = model.flow_count ?? (model.flows || []).length;
            const varCount = model.variable_count ?? (model.variables || []).length;
            
            return `
                <div class="library-item ${isExpanded ? "expanded" : ""}" data-id="${model.id}">
                    <div class="library-item-header">
                        <div class="library-item-info" data-id="${model.id}">
                            <div class="library-item-name">
                                <span class="expand-icon">${isExpanded ? "▼" : "▶"}</span>
                    ${this.escapeHtml(model.name)}
                            </div>
                            <div class="library-item-meta">
                                <span class="library-item-category">${this.formatCategory(model.category || "other")}</span>
                                <span class="library-item-stats">${stockCount}S ${flowCount}F ${varCount}V</span>
                                <span class="model-check ${model.numerical_check === 'failed' ? 'needs-review' : ''}">${model.numerical_check === 'passed' ? 'Default run completed' : model.numerical_check === 'failed' ? 'Needs investigation' : 'Not yet checked'}</span>
                            </div>
                        </div>
                        <button class="library-item-import" data-id="${model.id}" title="Import">
                            Import
                        </button>
                    </div>
                    ${isExpanded ? this.renderModelDetails(model) : ""}
                </div>
            `;
        }).join("");
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text || "";
        return div.innerHTML;
    },

    /**
     * Render expanded model details
     */
    renderModelDetails(model) {
        const stocks = model.stocks || [];
        const flows = model.flows || [];
        const variables = model.variables || [];
        const timeSettings = model.time_settings || {};
        
        return `
            <div class="library-item-details">
                <div class="detail-section">
                    <div class="detail-label">Description</div>
                    <div class="detail-value">${this.escapeHtml(model.description) || "No description"}</div>
                </div>
                
                <div class="detail-section">
                    <div class="detail-label">Time</div>
                    <div class="detail-value">
                        ${timeSettings.start || 0} → ${timeSettings.end || 100} (dt: ${timeSettings.dt || 1})
                    </div>
                </div>
                
                ${stocks.length > 0 ? `
                <div class="detail-section">
                    <div class="detail-label">Stocks (${stocks.length})</div>
                    <div class="detail-list">
                        ${stocks.slice(0, 5).map(s => `
                            <div class="detail-item">
                                <span class="item-name">${this.escapeHtml(s.name)}</span>
                                <span class="item-value">= ${s.initial_value}</span>
                            </div>
                        `).join("")}
                        ${stocks.length > 5 ? `<div class="detail-more">+${stocks.length - 5} more...</div>` : ""}
                    </div>
                </div>
                ` : ""}
                
                ${flows.length > 0 ? `
                <div class="detail-section">
                    <div class="detail-label">Flows (${flows.length})</div>
                    <div class="detail-list">
                        ${flows.slice(0, 5).map(f => `
                            <div class="detail-item">
                                <span class="item-name">${this.escapeHtml(f.name)}</span>
                                <span class="item-equation">${this.escapeHtml(f.equation)}</span>
                            </div>
                        `).join("")}
                        ${flows.length > 5 ? `<div class="detail-more">+${flows.length - 5} more...</div>` : ""}
                    </div>
                </div>
                ` : ""}
                
                ${variables.length > 0 ? `
                <div class="detail-section">
                    <div class="detail-label">Variables (${variables.length})</div>
                    <div class="detail-list">
                        ${variables.slice(0, 5).map(v => `
                            <div class="detail-item">
                                <span class="item-name">${this.escapeHtml(v.name)}</span>
                                <span class="item-equation">${this.escapeHtml(v.equation)}</span>
                            </div>
                        `).join("")}
                        ${variables.length > 5 ? `<div class="detail-more">+${variables.length - 5} more...</div>` : ""}
                    </div>
                </div>
                ` : ""}
                
                <div class="detail-actions">
                    <button class="btn-import-full" data-id="${model.id}">Import This Model</button>
                </div>
            </div>
        `;
    },

    /**
     * Toggle model expansion
     */
    async toggleExpand(modelId) {
        if (this.expandedModel === modelId) {
            this.expandedModel = null;
        } else {
            const model = this.models.find(m => m.id === modelId);
            if (model && !model.stocks) {
                try {
                    const response = await fetch(`/api/models/${encodeURIComponent(modelId)}`, {signal: AbortSignal.timeout(20000)});
                    if (!response.ok) throw new Error('Could not load model details');
                    Object.assign(model, await response.json());
                } catch (error) {
                    this.showNotification(error.message, true);
                    return;
                }
            }
            this.expandedModel = modelId;
        }
        this.updateList();
    },

    /**
     * Update the model list display
     */
    updateList() {
        const listEl = document.getElementById("library-list");
        if (listEl) {
            listEl.innerHTML = this.renderModelList();
            this.bindItemEvents();
        }
        
        // Update count
        const countEl = document.getElementById("library-count");
        if (countEl) {
            if (this.isLoading) {
                countEl.textContent = "Loading...";
            } else {
                countEl.textContent = `${this.filteredModels.length} of ${this.models.length}`;
            }
        }
    },

    /**
     * Filter and sort models
     */
    applyFilters() {
        let filtered = [...this.models];

        // Category filter
        if (this.currentCategory !== "all") {
            filtered = filtered.filter(m => m.category === this.currentCategory);
        }

        // Search filter
        if (this.searchQuery) {
            const query = this.searchQuery.toLowerCase();
            filtered = filtered.filter(m => 
                m.name.toLowerCase().includes(query) ||
                (m.description && m.description.toLowerCase().includes(query))
            );
        }

        // Sort
        filtered.sort((a, b) => {
            if (this.sortBy === "category") {
                return (a.category || "").localeCompare(b.category || "") || 
                       a.name.localeCompare(b.name);
            }
            return a.name.localeCompare(b.name);
        });

        this.filteredModels = filtered;
        this.expandedModel = null; // Reset expansion when filtering
        this.updateList();
    },

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Close button
        document.querySelector(".library-close")?.addEventListener("click", () => this.close());

        // Click outside to close
        document.getElementById("library-modal")?.addEventListener("click", (e) => {
            if (e.target.id === "library-modal") this.close();
        });

        // Search
        document.getElementById("library-search")?.addEventListener("input", (e) => {
            this.searchQuery = e.target.value;
            this.applyFilters();
        });

        // Category filter
        document.getElementById("library-category")?.addEventListener("change", (e) => {
            this.currentCategory = e.target.value;
            this.applyFilters();
        });

        // Sort
        document.getElementById("library-sort")?.addEventListener("change", (e) => {
            this.sortBy = e.target.value;
            this.applyFilters();
        });

        // Escape key
        document.addEventListener("keydown", (e) => {
            if (!this.isOpen || document.querySelector('dialog[open]')) return;
            if (e.key === "Escape") { e.preventDefault(); this.close(); }
            if (e.key === "Tab") {
                const modal = document.getElementById("library-modal");
                const fields = [...modal.querySelectorAll('button,input,select,textarea,a[href],[tabindex]')]
                    .filter(field => !field.disabled && field.tabIndex >= 0 && field.getClientRects().length);
                const first = fields[0], last = fields[fields.length - 1];
                if (!modal.contains(document.activeElement) || (e.shiftKey && document.activeElement === first)) {
                    e.preventDefault(); (e.shiftKey ? last : first)?.focus();
                } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
            }
        });

        this.bindItemEvents();
    },

    /**
     * Bind events on list items
     */
    bindItemEvents() {
        document.getElementById('library-retry')?.addEventListener('click', () => this.loadModels());
        // Import buttons (in header)
        document.querySelectorAll(".library-item-import").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                this.importModel(id);
            });
        });

        // Full import buttons (in expanded details)
        document.querySelectorAll(".btn-import-full").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                this.importModel(id);
            });
        });

        // Model info click - toggle expand
        document.querySelectorAll(".library-item-info").forEach(item => {
            item.addEventListener("click", (e) => {
                e.stopPropagation();
                const id = item.dataset.id;
                this.toggleExpand(id);
            });
        });
    },

    /**
     * Import a model into the canvas
     */
    async importModel(modelId) {
        // Show loading on the button
        const btn = document.querySelector(`.library-item-import[data-id="${modelId}"]`);
        const originalText = btn ? btn.textContent : "Import";
        if (btn) {
            btn.textContent = "...";
            btn.disabled = true;
        }
        
        try {
            const response = await fetch(`/api/models/${modelId}`);
            if (!response.ok) {
                const text = await response.text();
                throw new Error(`Model not found: ${text}`);
            }
            
            const model = await response.json();
            
            // Load into App
            if (typeof App !== "undefined" && App.loadModel) {
                await App.loadModel(model);
                this.close();
                this.showNotification(`✓ Imported: ${model.name}`);
            }
        } catch (error) {
            console.error("Failed to import model:", error);
            this.showNotification("✗ Failed to import", true);
        } finally {
            if (btn) {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        }
    },

    /**
     * Show notification
     */
    showNotification(message, isError = false) {
        const notif = document.createElement("div");
        notif.className = "library-notification" + (isError ? " error" : "");
        notif.textContent = message;
        document.body.appendChild(notif);
        
        setTimeout(() => notif.classList.add("show"), 10);
        setTimeout(() => {
            notif.classList.remove("show");
            setTimeout(() => notif.remove(), 300);
        }, 2000);
    },

    /**
     * Open library modal
     */
    async open() {
        const modal = document.getElementById("library-modal");
        if (modal) {
            if (!this.isOpen) this.opener = document.activeElement;
            modal.classList.add("open");
            this.isOpen = true;
            document.getElementById("library-search")?.focus();
            
            // Load models when opening (with loading screen)
            await this.loadModels();
            if (this.isOpen) this.applyFilters();
        }
    },

    /**
     * Close library modal
     */
    close() {
        const modal = document.getElementById("library-modal");
        if (modal) {
            const wasOpen = this.isOpen;
            modal.classList.remove("open");
            this.isOpen = false;
            if (wasOpen && !document.querySelector('dialog[open]')) this.opener?.focus();
            this.expandedModel = null;
        }
    },

    /**
     * Toggle library modal
     */
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
};

// Initialize on load
document.addEventListener("DOMContentLoaded", () => {
    Library.init();
});
