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

    /**
     * Initialize library
     */
    async init() {
        await this.loadModels();
        this.createModal();
        this.bindEvents();
    },

    /**
     * Load models from API
     */
    async loadModels() {
        try {
            const response = await fetch("/api/models");
            const data = await response.json();
            this.models = Array.isArray(data) ? data : (data.models || []);
            
            // Extract unique categories
            const cats = new Set();
            this.models.forEach(m => {
                if (m.category) cats.add(m.category);
            });
            this.categories = Array.from(cats).sort();
            
            this.filteredModels = [...this.models];
        } catch (error) {
            console.error("Failed to load models:", error);
        }
    },

    /**
     * Create the modal HTML
     */
    createModal() {
        const modal = document.createElement("div");
        modal.id = "library-modal";
        modal.className = "library-modal";
        modal.innerHTML = `
            <div class="library-content">
                <div class="library-header">
                    <h2>📚 Model Library</h2>
                    <span class="library-count">${this.models.length} models</span>
                    <button class="library-close" title="Close">&times;</button>
                </div>
                
                <div class="library-controls">
                    <input type="text" id="library-search" placeholder="Search models..." class="library-search">
                    <select id="library-category" class="library-category">
                        <option value="all">All Categories</option>
                        ${this.categories.map(c => `<option value="${c}">${this.formatCategory(c)}</option>`).join("")}
                    </select>
                    <select id="library-sort" class="library-sort">
                        <option value="name">Sort: Name</option>
                        <option value="category">Sort: Category</option>
                    </select>
                </div>
                
                <div class="library-list" id="library-list">
                    ${this.renderModelList()}
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
        if (this.filteredModels.length === 0) {
            return `<div class="library-empty">No models found</div>`;
        }

        return this.filteredModels.map(model => `
            <div class="library-item" data-id="${model.id}">
                <div class="library-item-info">
                    <div class="library-item-name">${model.name}</div>
                    <div class="library-item-meta">
                        <span class="library-item-category">${this.formatCategory(model.category || "other")}</span>
                        <span class="library-item-desc">${model.description || ""}</span>
                    </div>
                </div>
                <button class="library-item-import" data-id="${model.id}" title="Import">
                    Import
                </button>
            </div>
        `).join("");
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
        const countEl = document.querySelector(".library-count");
        if (countEl) {
            countEl.textContent = `${this.filteredModels.length} of ${this.models.length} models`;
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
            if (e.key === "Escape" && this.isOpen) this.close();
        });

        this.bindItemEvents();
    },

    /**
     * Bind events on list items
     */
    bindItemEvents() {
        document.querySelectorAll(".library-item-import").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                this.importModel(id);
            });
        });

        document.querySelectorAll(".library-item").forEach(item => {
            item.addEventListener("click", () => {
                const id = item.dataset.id;
                this.importModel(id);
            });
        });
    },

    /**
     * Import a model into the canvas
     */
    async importModel(modelId) {
        try {
            const response = await fetch(`/api/models/${modelId}`);
            if (!response.ok) throw new Error("Model not found");
            
            const model = await response.json();
            
            // Load into App
            if (typeof App !== "undefined" && App.loadModel) {
                App.loadModel(model);
                this.close();
                
                // Show notification
                this.showNotification(`Imported: ${model.name}`);
            }
        } catch (error) {
            console.error("Failed to import model:", error);
            alert("Failed to import model");
        }
    },

    /**
     * Show notification
     */
    showNotification(message) {
        const notif = document.createElement("div");
        notif.className = "library-notification";
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
    open() {
        const modal = document.getElementById("library-modal");
        if (modal) {
            modal.classList.add("open");
            this.isOpen = true;
            document.getElementById("library-search")?.focus();
        }
    },

    /**
     * Close library modal
     */
    close() {
        const modal = document.getElementById("library-modal");
        if (modal) {
            modal.classList.remove("open");
            this.isOpen = false;
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
