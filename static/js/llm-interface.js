/**
 * Systems Modeler - LLM Interface
 * Chat-based interaction for model generation and modification
 * Supports both desktop and mobile interfaces
 */
const LLMInterface = {
    available: false,
    chatMessages: null,
    chatInput: null,
    sendBtn: null,

    /**
     * Initialize LLM interface
     */
    init() {
        // Desktop elements
        this.chatMessages = document.getElementById('chat-messages-desktop');
        this.chatInput = document.getElementById('chat-input-desktop');
        this.sendBtn = document.getElementById('btn-send-desktop');
        this.statusEl = document.getElementById('llm-status');

        // Bind events for desktop
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => this.send());
        }
        if (this.chatInput) {
            this.chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.send();
                }
            });
        }

        // Check LLM availability
        this.checkStatus();
    },

    /**
     * Check if LLM is available
     */
    async checkStatus() {
        try {
            const response = await OpenRouterUI.request('/api/llm/status');
            const data = await response.json();
            this.available = data.available;

            if (this.available) {
                this.statusEl.textContent = 'Configured';
                this.statusEl.title = 'AI configured; use AI settings to test your personal OpenRouter connection';
                this.statusEl.className = 'llm-status available';
            } else {
                this.statusEl.textContent = 'Unavailable';
                this.statusEl.className = 'llm-status unavailable';
            }
        } catch (error) {
            this.available = false;
            this.statusEl.textContent = 'Error';
            this.statusEl.className = 'llm-status unavailable';
        } finally {
            document.querySelectorAll('.chat-header .llm-status').forEach(status => {
                status.textContent = this.statusEl.textContent;
                status.className = this.statusEl.className;
                status.title = this.statusEl.title;
            });
        }
    },

    /**
     * Send a message to the LLM
     */
    async send() {
        const message = this.chatInput.value.trim();
        if (!message) return;

        // Add user message to chat
        this.addMessage(message, 'user');
        this.chatInput.value = '';

        // Check availability
        if (!this.available) {
            this.addMessage(
                'Choose AI settings to use your OpenRouter key, or Connect agent through MCP.',
                'error'
            );
            return;
        }

        // Disable input while processing
        this.setLoading(true);

        try {
            let result;

            // Determine if this is a generate or modify request
            const isModify = App.model.stocks.length > 0 || App.model.flows.length > 0 || App.model.variables.length > 0;

            if (isModify && this.isModificationRequest(message)) {
                // Modify existing model
                result = await this.modifyModel(message);
            } else {
                // Generate new model
                result = await this.generateModel(message);
            }

            // Success
            App.loadModelData(result);
            this.addMessage(
                `I've ${isModify ? 'modified' : 'created'} the model "${result.name}". ` +
                `It has ${result.stocks?.length || 0} stocks, ${result.flows?.length || 0} flows, ` +
                `and ${result.variables?.length || 0} variables. ` +
                'You can now run a simulation or continue to refine it.',
                'assistant'
            );

        } catch (error) {
            console.error('LLM error:', error);
            this.addMessage(`Error: ${error.message}`, 'error');
        } finally {
            this.setLoading(false);
        }
    },

    /**
     * Generate a new model from description
     */
    async generateModel(description) {
        const response = await OpenRouterUI.request('/api/llm/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Generation failed');
        }

        return await response.json();
    },

    /**
     * Modify existing model
     */
    async modifyModel(modification) {
        const response = await OpenRouterUI.request('/api/llm/modify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: App.modelSnapshot(),
                modification
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Modification failed');
        }

        return await response.json();
    },

    /**
     * Check if a message is likely a modification request
     */
    isModificationRequest(message) {
        const modifyKeywords = [
            'add', 'remove', 'delete', 'change', 'modify', 'update',
            'increase', 'decrease', 'rename', 'connect', 'disconnect',
            'make', 'set', 'adjust', 'tweak', 'include', 'incorporate'
        ];

        const lowerMessage = message.toLowerCase();
        return modifyKeywords.some(keyword => lowerMessage.includes(keyword));
    },

    /**
     * Add a message to the chat
     */
    addMessage(content, type) {
        const messageEl = document.createElement('div');
        messageEl.className = `chat-message ${type}`;

        if (type === 'user') {
            messageEl.textContent = content;
        } else {
            // Parse simple markdown for assistant messages
            const p = document.createElement('p');
            p.innerHTML = this.formatMessage(content);
            messageEl.appendChild(p);
        }

        this.chatMessages.appendChild(messageEl);
        const mobileMessages = document.getElementById('chat-messages-mobile');
        if (mobileMessages) mobileMessages.appendChild(messageEl.cloneNode(true));
        this.scrollToBottom();
    },

    /**
     * Simple message formatting
     */
    formatMessage(text) {
        // Escape HTML
        text = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        // Bold
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Code
        text = text.replace(/`(.*?)`/g, '<code>$1</code>');
        return text;
    },

    /**
     * Set loading state
     */
    setLoading(loading) {
        this.sendBtn.disabled = loading;
        this.chatInput.disabled = loading;

        if (loading) {
            this.sendBtn.innerHTML = '<span class="loading"></span>';
        } else {
            this.sendBtn.textContent = 'Send';
        }
    },

    /**
     * Scroll chat to bottom
     */
    scrollToBottom() {
        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
        // Also scroll mobile chat if open
        const mobileMessages = document.getElementById('chat-messages-mobile');
        if (mobileMessages) {
            mobileMessages.scrollTop = mobileMessages.scrollHeight;
        }
    },

    /**
     * Send message from mobile interface
     */
    async sendFromMobile() {
        const input = document.getElementById('chat-input-mobile');
        const sendBtn = document.getElementById('btn-send-mobile');

        if (!input) return;

        const message = input.value.trim();
        if (!message) return;

        // Add user message to both desktop and mobile
        this.addMessage(message, 'user');
        input.value = '';
        App.mobileChatDraft = '';

        // Check availability
        if (!this.available) {
            this.addMessage(
                'Choose AI settings to use your OpenRouter key, or Connect agent through MCP.',
                'error'
            );
            return;
        }

        // Disable input while processing
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.innerHTML = '<span class="loading"></span>';
        }
        if (input) {
            input.disabled = true;
        }

        try {
            let result;

            // Determine if this is a generate or modify request
            const isModify = App.model.stocks.length > 0 || App.model.flows.length > 0 || App.model.variables.length > 0;

            if (isModify && this.isModificationRequest(message)) {
                result = await this.modifyModel(message);
            } else {
                result = await this.generateModel(message);
            }

            // Success
            App.loadModelData(result);
            this.addMessage(
                `I've ${isModify ? 'modified' : 'created'} the model "${result.name}". ` +
                `It has ${result.stocks?.length || 0} stocks, ${result.flows?.length || 0} flows, ` +
                `and ${result.variables?.length || 0} variables. ` +
                'You can now run a simulation or continue to refine it.',
                'assistant'
            );

            // Close the mobile panel to show the model
            App.closeSlidePanel();

        } catch (error) {
            console.error('LLM error:', error);
            this.addMessage(`Error: ${error.message}`, 'error');
        } finally {
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.textContent = 'Send';
            }
            if (input) {
                input.disabled = false;
            }
        }
    },

    /**
     * Add message to both desktop and mobile chat containers
     */
    addMessageToBoth(content, type) {
        this.addMessage(content, type);
    }
};
