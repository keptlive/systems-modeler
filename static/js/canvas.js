/**
 * Systems Modeler - Canvas Editor
 * Visual editor for stocks, flows, and variables using SVG
 * Supports both mouse and touch interactions
 */
const Canvas = {
    svg: null,
    container: null,
    defs: null,

    // Dimensions
    width: 800,
    height: 600,

    // Element sizes
    stockWidth: 100,
    stockHeight: 60,
    flowSize: 30,
    variableRadius: 25,

    // Zoom and pan state
    scale: 1,
    minScale: 0.5,
    maxScale: 3,
    translateX: 0,
    translateY: 0,

    // Dragging state
    dragging: null,
    dragOffset: { x: 0, y: 0 },

    // Touch state
    touchState: {
        active: false,
        lastTap: 0,
        initialDistance: 0,
        initialScale: 1,
        startX: 0,
        startY: 0,
        isPinching: false,
        isPanning: false
    },

    /**
     * Initialize the canvas
     */
    init() {
        this.container = document.getElementById('canvas-container');
        this.svg = d3.select('#canvas');
        this.zoomIndicator = document.getElementById('zoom-indicator');

        // Set up dimensions
        this.updateDimensions();
        window.addEventListener('resize', () => this.updateDimensions());

        // Create definitions for markers (arrowheads)
        this.defs = this.svg.append('defs');

        // Arrowhead marker for flows
        this.defs.append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 8)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#9b59b6');

        // Arrowhead for connectors
        this.defs.append('marker')
            .attr('id', 'connector-arrow')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 8)
            .attr('refY', 0)
            .attr('markerWidth', 5)
            .attr('markerHeight', 5)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#7f8c8d');

        // Create main group for zoom/pan
        this.mainGroup = this.svg.append('g').attr('class', 'main-group');

        // Mouse event handlers
        this.svg.on('click', (event) => this.handleCanvasClick(event));
        this.svg.on('mousedown', (event) => this.handleMouseDown(event));
        this.svg.on('mousemove', (event) => this.handleMouseMove(event));
        this.svg.on('mouseup', () => this.handleMouseUp());
        this.svg.on('mouseleave', () => this.handleMouseUp());

        // Touch event handlers
        this.container.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: false });
        this.container.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
        this.container.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: false });
        this.container.addEventListener('touchcancel', (e) => this.handleTouchEnd(e), { passive: false });

        // Mouse wheel zoom
        this.container.addEventListener('wheel', (e) => this.handleWheel(e), { passive: false });

        // Initial render
        this.render();
    },

    /**
     * Update canvas dimensions based on container
     */
    updateDimensions() {
        const rect = this.container.getBoundingClientRect();
        this.width = rect.width;
        this.height = rect.height;
        this.svg.attr('viewBox', `0 0 ${this.width} ${this.height}`);
        this.updateTransform();
    },

    /**
     * Update zoom indicator
     */
    updateZoomIndicator() {
        if (this.zoomIndicator) {
            this.zoomIndicator.textContent = `${Math.round(this.scale * 100)}%`;
        }
    },

    /**
     * Update the transform of the main group
     */
    updateTransform() {
        if (this.mainGroup) {
            this.mainGroup.attr('transform',
                `translate(${this.translateX}, ${this.translateY}) scale(${this.scale})`
            );
        }
        this.updateZoomIndicator();
    },

    /**
     * Convert screen coordinates to canvas coordinates
     */
    screenToCanvas(screenX, screenY) {
        const rect = this.container.getBoundingClientRect();
        const x = (screenX - rect.left - this.translateX) / this.scale;
        const y = (screenY - rect.top - this.translateY) / this.scale;
        return { x, y };
    },

    /**
     * Handle mouse wheel zoom
     */
    handleWheel(event) {
        event.preventDefault();

        const delta = event.deltaY > 0 ? 0.9 : 1.1;
        const newScale = Math.max(this.minScale, Math.min(this.maxScale, this.scale * delta));

        if (newScale !== this.scale) {
            // Zoom towards mouse position
            const rect = this.container.getBoundingClientRect();
            const mouseX = event.clientX - rect.left;
            const mouseY = event.clientY - rect.top;

            this.translateX = mouseX - (mouseX - this.translateX) * (newScale / this.scale);
            this.translateY = mouseY - (mouseY - this.translateY) * (newScale / this.scale);
            this.scale = newScale;

            this.updateTransform();
        }
    },

    /**
     * Handle touch start
     */
    handleTouchStart(event) {
        const touches = event.touches;

        if (touches.length === 1) {
            // Single touch - could be tap, drag, or pan
            const touch = touches[0];
            this.touchState.active = true;
            this.touchState.startX = touch.clientX;
            this.touchState.startY = touch.clientY;
            this.touchState.isPinching = false;
            this.touchState.isPanning = false;

            // Check for double tap
            const now = Date.now();
            if (now - this.touchState.lastTap < 300) {
                // Double tap - reset zoom
                this.scale = 1;
                this.translateX = 0;
                this.translateY = 0;
                this.updateTransform();
                event.preventDefault();
            }
            this.touchState.lastTap = now;

            // Try to start element drag
            const canvasPos = this.screenToCanvas(touch.clientX, touch.clientY);
            const element = this.findElementAtPosition(canvasPos.x, canvasPos.y);

            if (element && App.mode === 'select') {
                this.startDragTouch(element.type, element.element, touch);
                event.preventDefault();
            }
        } else if (touches.length === 2) {
            // Two touches - pinch to zoom
            event.preventDefault();
            this.touchState.isPinching = true;
            this.touchState.initialDistance = this.getTouchDistance(touches[0], touches[1]);
            this.touchState.initialScale = this.scale;
            this.touchState.centerX = (touches[0].clientX + touches[1].clientX) / 2;
            this.touchState.centerY = (touches[0].clientY + touches[1].clientY) / 2;

            // Cancel any element drag
            this.dragging = null;
        }
    },

    /**
     * Handle touch move
     */
    handleTouchMove(event) {
        const touches = event.touches;

        if (touches.length === 2 && this.touchState.isPinching) {
            // Pinch zoom
            event.preventDefault();

            const newDistance = this.getTouchDistance(touches[0], touches[1]);
            const scaleFactor = newDistance / this.touchState.initialDistance;
            const newScale = Math.max(this.minScale, Math.min(this.maxScale,
                this.touchState.initialScale * scaleFactor));

            if (newScale !== this.scale) {
                const rect = this.container.getBoundingClientRect();
                const centerX = (touches[0].clientX + touches[1].clientX) / 2 - rect.left;
                const centerY = (touches[0].clientY + touches[1].clientY) / 2 - rect.top;

                this.translateX = centerX - (centerX - this.translateX) * (newScale / this.scale);
                this.translateY = centerY - (centerY - this.translateY) * (newScale / this.scale);
                this.scale = newScale;

                this.updateTransform();
            }
        } else if (touches.length === 1 && this.touchState.active) {
            const touch = touches[0];

            if (this.dragging) {
                // Dragging an element
                event.preventDefault();
                const canvasPos = this.screenToCanvas(touch.clientX, touch.clientY);
                const newX = Math.max(50, Math.min((this.width / this.scale) - 50,
                    canvasPos.x - this.dragOffset.x));
                const newY = Math.max(30, Math.min((this.height / this.scale) - 30,
                    canvasPos.y - this.dragOffset.y));

                this.dragging.element.position.x = newX;
                this.dragging.element.position.y = newY;
                this.render();
            } else {
                // Check if we should start panning
                const dx = touch.clientX - this.touchState.startX;
                const dy = touch.clientY - this.touchState.startY;

                if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
                    this.touchState.isPanning = true;
                }

                if (this.touchState.isPanning) {
                    event.preventDefault();
                    this.translateX += dx;
                    this.translateY += dy;
                    this.touchState.startX = touch.clientX;
                    this.touchState.startY = touch.clientY;
                    this.updateTransform();
                }
            }
        }
    },

    /**
     * Handle touch end
     */
    handleTouchEnd(event) {
        if (this.touchState.active && !this.touchState.isPanning && !this.dragging) {
            // This was a tap - handle as click
            const changedTouches = event.changedTouches;
            if (changedTouches.length > 0) {
                const touch = changedTouches[0];
                const canvasPos = this.screenToCanvas(touch.clientX, touch.clientY);

                // Check if tap was on an element
                const element = this.findElementAtPosition(canvasPos.x, canvasPos.y);

                if (element) {
                    if (App.mode === 'connect') {
                        if (!App.connectFrom) {
                            App.connectFrom = { type: element.type, id: element.element.id };
                        } else {
                            App.addConnector(App.connectFrom.id, element.element.id);
                            App.connectFrom = null;
                        }
                    } else {
                        App.selectElement(element.type, element.element.id);
                    }
                } else {
                    // Tap on empty canvas
                    this.handleCanvasTap(canvasPos.x, canvasPos.y);
                }
            }
        }

        this.touchState.active = false;
        this.touchState.isPinching = false;
        this.touchState.isPanning = false;
        this.dragging = null;
    },

    /**
     * Handle tap on empty canvas area
     */
    handleCanvasTap(x, y) {
        switch (App.mode) {
            case 'add-stock':
                App.addElement('stock', x, y);
                break;
            case 'add-flow':
                App.addElement('flow', x, y);
                break;
            case 'add-variable':
                App.addElement('variable', x, y);
                break;
            case 'select':
                App.clearSelection();
                break;
            case 'connect':
                App.connectFrom = null;
                break;
        }
    },

    /**
     * Get distance between two touches
     */
    getTouchDistance(touch1, touch2) {
        const dx = touch1.clientX - touch2.clientX;
        const dy = touch1.clientY - touch2.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    },

    /**
     * Find element at position
     */
    findElementAtPosition(x, y) {
        // Check stocks
        for (const stock of App.model.stocks) {
            if (this.isPointInStock(x, y, stock)) {
                return { type: 'stock', element: stock };
            }
        }

        // Check flows
        for (const flow of App.model.flows) {
            if (this.isPointInFlow(x, y, flow)) {
                return { type: 'flow', element: flow };
            }
        }

        // Check variables
        for (const variable of App.model.variables) {
            if (this.isPointInVariable(x, y, variable)) {
                return { type: 'variable', element: variable };
            }
        }

        return null;
    },

    /**
     * Check if point is in stock
     */
    isPointInStock(x, y, stock) {
        const halfWidth = this.stockWidth / 2;
        const halfHeight = this.stockHeight / 2;
        return x >= stock.position.x - halfWidth &&
               x <= stock.position.x + halfWidth &&
               y >= stock.position.y - halfHeight &&
               y <= stock.position.y + halfHeight;
    },

    /**
     * Check if point is in flow
     */
    isPointInFlow(x, y, flow) {
        const halfSize = this.flowSize / 2 + 10; // Extra padding for easier touch
        return x >= flow.position.x - halfSize &&
               x <= flow.position.x + halfSize &&
               y >= flow.position.y - halfSize &&
               y <= flow.position.y + halfSize;
    },

    /**
     * Check if point is in variable
     */
    isPointInVariable(x, y, variable) {
        const dx = x - variable.position.x;
        const dy = y - variable.position.y;
        return Math.sqrt(dx * dx + dy * dy) <= this.variableRadius + 10; // Extra padding
    },

    /**
     * Start dragging with touch
     */
    startDragTouch(type, element, touch) {
        this.dragging = { type, element };
        const canvasPos = this.screenToCanvas(touch.clientX, touch.clientY);
        this.dragOffset = {
            x: canvasPos.x - element.position.x,
            y: canvasPos.y - element.position.y
        };
        App.selectElement(type, element.id);
    },

    /**
     * Handle mouse down for panning
     */
    handleMouseDown(event) {
        if (event.target === this.svg.node() && App.mode === 'select') {
            // Start panning with middle mouse or when holding space
            if (event.button === 1) {
                event.preventDefault();
                this.isPanning = true;
                this.panStart = { x: event.clientX, y: event.clientY };
            }
        }
    },

    /**
     * Handle mouse move
     */
    handleMouseMove(event) {
        if (this.isPanning) {
            const dx = event.clientX - this.panStart.x;
            const dy = event.clientY - this.panStart.y;
            this.translateX += dx;
            this.translateY += dy;
            this.panStart = { x: event.clientX, y: event.clientY };
            this.updateTransform();
        }
    },

    /**
     * Handle mouse up
     */
    handleMouseUp() {
        this.isPanning = false;
    },

    /**
     * Handle clicks on the canvas
     */
    handleCanvasClick(event) {
        // Only handle direct clicks on SVG, not on elements
        if (event.target !== this.svg.node()) return;

        const [screenX, screenY] = d3.pointer(event);
        const canvasPos = this.screenToCanvas(
            event.clientX,
            event.clientY
        );

        switch (App.mode) {
            case 'add-stock':
                App.addElement('stock', canvasPos.x, canvasPos.y);
                break;
            case 'add-flow':
                App.addElement('flow', canvasPos.x, canvasPos.y);
                break;
            case 'add-variable':
                App.addElement('variable', canvasPos.x, canvasPos.y);
                break;
            case 'select':
                App.clearSelection();
                break;
            case 'connect':
                // If we were connecting, cancel
                App.connectFrom = null;
                break;
        }
    },

    /**
     * Handle element click
     */
    handleElementClick(type, element, event) {
        event.stopPropagation();

        if (App.mode === 'connect') {
            if (!App.connectFrom) {
                // Start connection
                App.connectFrom = { type, id: element.id };
            } else {
                // Complete connection
                App.addConnector(App.connectFrom.id, element.id);
                App.connectFrom = null;
            }
        } else {
            App.selectElement(type, element.id);
        }
    },

    /**
     * Start dragging an element (mouse)
     */
    startDrag(type, element, event) {
        if (App.mode !== 'select') return;

        event.stopPropagation();

        this.dragging = { type, element };
        const canvasPos = this.screenToCanvas(event.clientX, event.clientY);

        this.dragOffset = {
            x: canvasPos.x - element.position.x,
            y: canvasPos.y - element.position.y
        };

        // Add move and up listeners
        this.svg.on('mousemove.drag', (e) => this.onDrag(e));
        this.svg.on('mouseup.drag', () => this.endDrag());
    },

    /**
     * Handle drag movement
     */
    onDrag(event) {
        if (!this.dragging) return;

        const canvasPos = this.screenToCanvas(event.clientX, event.clientY);
        const canvasWidth = this.width / this.scale;
        const canvasHeight = this.height / this.scale;

        const newX = Math.max(50, Math.min(canvasWidth - 50, canvasPos.x - this.dragOffset.x));
        const newY = Math.max(30, Math.min(canvasHeight - 30, canvasPos.y - this.dragOffset.y));

        this.dragging.element.position.x = newX;
        this.dragging.element.position.y = newY;

        this.render();
    },

    /**
     * End dragging
     */
    endDrag() {
        this.dragging = null;
        this.svg.on('mousemove.drag', null);
        this.svg.on('mouseup.drag', null);
    },

    /**
     * Reset zoom and pan
     */
    resetView() {
        this.scale = 1;
        this.translateX = 0;
        this.translateY = 0;
        this.updateTransform();
    },

    /**
     * Render the entire canvas
     */
    render() {
        // Clear previous content (except defs)
        this.mainGroup.selectAll('g').remove();

        // Create layers
        const connectorsLayer = this.mainGroup.append('g').attr('class', 'connectors-layer');
        const flowLinesLayer = this.mainGroup.append('g').attr('class', 'flow-lines-layer');
        const elementsLayer = this.mainGroup.append('g').attr('class', 'elements-layer');

        // Render connectors first (below everything)
        this.renderConnectors(connectorsLayer);

        // Render flow lines
        this.renderFlowLines(flowLinesLayer);

        // Render elements
        this.renderStocks(elementsLayer);
        this.renderFlows(elementsLayer);
        this.renderVariables(elementsLayer);
    },

    /**
     * Render stocks
     */
    renderStocks(layer) {
        const self = this;
        const stocks = layer.selectAll('.stock')
            .data(App.model.stocks, d => d.id)
            .enter()
            .append('g')
            .attr('class', 'stock')
            .attr('transform', d => `translate(${d.position.x}, ${d.position.y})`);

        // Rectangle
        stocks.append('rect')
            .attr('class', d => `stock-rect ${App.selected?.id === d.id ? 'selected' : ''}`)
            .attr('x', -this.stockWidth / 2)
            .attr('y', -this.stockHeight / 2)
            .attr('width', this.stockWidth)
            .attr('height', this.stockHeight)
            .attr('rx', 5)
            .on('click', function(event, d) { self.handleElementClick('stock', d, event); })
            .on('mousedown', function(event, d) { self.startDrag('stock', d, event); });

        // Label
        stocks.append('text')
            .attr('class', 'element-label')
            .attr('y', 5)
            .text(d => this.truncateLabel(d.name, 12));
    },

    /**
     * Render flows
     */
    renderFlows(layer) {
        const self = this;
        const flows = layer.selectAll('.flow')
            .data(App.model.flows, d => d.id)
            .enter()
            .append('g')
            .attr('class', 'flow')
            .attr('transform', d => `translate(${d.position.x}, ${d.position.y})`);

        // Valve shape (hourglass/bowtie)
        flows.append('path')
            .attr('class', d => `flow-valve ${App.selected?.id === d.id ? 'selected' : ''}`)
            .attr('d', `M${-this.flowSize/2},${-this.flowSize/2}
                       L${this.flowSize/2},${-this.flowSize/2}
                       L0,0
                       L${this.flowSize/2},${this.flowSize/2}
                       L${-this.flowSize/2},${this.flowSize/2}
                       L0,0Z`)
            .on('click', function(event, d) { self.handleElementClick('flow', d, event); })
            .on('mousedown', function(event, d) { self.startDrag('flow', d, event); });

        // Label
        flows.append('text')
            .attr('class', 'element-label')
            .attr('y', this.flowSize / 2 + 15)
            .text(d => this.truncateLabel(d.name, 10));
    },

    /**
     * Render variables
     */
    renderVariables(layer) {
        const self = this;
        const variables = layer.selectAll('.variable')
            .data(App.model.variables, d => d.id)
            .enter()
            .append('g')
            .attr('class', 'variable')
            .attr('transform', d => `translate(${d.position.x}, ${d.position.y})`);

        // Circle
        variables.append('circle')
            .attr('class', d => `variable-circle ${App.selected?.id === d.id ? 'selected' : ''}`)
            .attr('r', this.variableRadius)
            .on('click', function(event, d) { self.handleElementClick('variable', d, event); })
            .on('mousedown', function(event, d) { self.startDrag('variable', d, event); });

        // Label
        variables.append('text')
            .attr('class', 'element-label')
            .attr('y', 5)
            .text(d => this.truncateLabel(d.name, 8));
    },

    /**
     * Render flow lines connecting flows to stocks
     */
    renderFlowLines(layer) {
        App.model.flows.forEach(flow => {
            const flowPos = flow.position;

            // From stock to flow
            if (flow.from_stock) {
                const fromStock = App.model.stocks.find(
                    s => s.id === flow.from_stock || s.name === flow.from_stock
                );
                if (fromStock) {
                    this.drawFlowLine(layer, fromStock.position, flowPos);
                }
            }

            // From flow to stock
            if (flow.to_stock) {
                const toStock = App.model.stocks.find(
                    s => s.id === flow.to_stock || s.name === flow.to_stock
                );
                if (toStock) {
                    this.drawFlowLine(layer, flowPos, toStock.position);
                }
            }
        });
    },

    /**
     * Draw a flow line with arrow
     */
    drawFlowLine(layer, from, to) {
        layer.append('line')
            .attr('class', 'flow-line')
            .attr('x1', from.x)
            .attr('y1', from.y)
            .attr('x2', to.x)
            .attr('y2', to.y)
            .attr('marker-end', 'url(#arrowhead)');
    },

    /**
     * Render connectors between elements
     */
    renderConnectors(layer) {
        const self = this;
        App.model.connectors.forEach(connector => {
            const fromEl = App.findElement(connector.from_element);
            const toEl = App.findElement(connector.to_element);

            if (fromEl && toEl) {
                const fromPos = fromEl.element.position;
                const toPos = toEl.element.position;

                // Draw curved connector line
                const midX = (fromPos.x + toPos.x) / 2;
                const midY = (fromPos.y + toPos.y) / 2;
                const offset = 30;

                // Calculate perpendicular offset for curve
                const dx = toPos.x - fromPos.x;
                const dy = toPos.y - fromPos.y;
                const len = Math.sqrt(dx * dx + dy * dy);
                const nx = -dy / len * offset;
                const ny = dx / len * offset;

                const path = `M${fromPos.x},${fromPos.y} Q${midX + nx},${midY + ny} ${toPos.x},${toPos.y}`;

                layer.append('path')
                    .attr('class', 'connector-line')
                    .attr('d', path)
                    .attr('marker-end', 'url(#connector-arrow)')
                    .on('click', function(event) {
                        event.stopPropagation();
                        App.selectElement('connector', connector.id);
                    });
            }
        });
    },

    /**
     * Truncate label to fit
     */
    truncateLabel(text, maxLen) {
        if (text.length <= maxLen) return text;
        return text.substring(0, maxLen - 2) + '..';
    },

    /**
     * Get element position for connector endpoints
     */
    getElementPosition(nameOrId) {
        const result = App.findElement(nameOrId);
        if (result) {
            return result.element.position;
        }
        return null;
    }
};
