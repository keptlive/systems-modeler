/**
 * Systems Modeler - Canvas Editor
 * Visual editor for stocks, flows, and variables using SVG
 * Supports both mouse and touch interactions
 */
const Canvas = {
    svg: null,
    container: null,
    defs: null,
    _mainGroup: null,
    
    // Lazy getter for mainGroup - ensures it exists when accessed
    get mainGroup() {
        if (!this._mainGroup && this.svg && !this.svg.empty()) {
            this._mainGroup = this.svg.select("g.main-group");
            if (this._mainGroup.empty()) {
                this._mainGroup = this.svg.append("g").attr("class", "main-group");
            }
        }
        return this._mainGroup && !this._mainGroup.empty() ? this._mainGroup : null;
    },
    set mainGroup(val) { this._mainGroup = val; },

    // Dimensions
    width: 800,
    height: 600,

    // Element sizes
    stockWidth: 112,
    stockHeight: 64,
    flowSize: 30,
    variableRadius: 25,

    // Zoom and pan state
    scale: 1,
    minScale: 0.1,
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
            .attr('fill', '#b6a1e4');

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
            .attr('fill', '#8399b6');

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
        return this.containsPoint('stock',stock,x,y);
    },

    /**
     * Check if point is in flow
     */
    isPointInFlow(x, y, flow) {
        return this.containsPoint('flow',flow,x,y);
    },

    /**
     * Check if point is in variable
     */
    isPointInVariable(x, y, variable) {
        return this.containsPoint('variable',variable,x,y);
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

    fitToModel() {
        const elements = [...App.model.stocks, ...App.model.flows, ...App.model.variables];
        if (!elements.length) return this.resetView();
        this.updateDimensions();
        const bounds=this.modelBounds();
        const minX=bounds.minX-18,maxX=bounds.maxX+18,minY=bounds.minY-18,maxY=bounds.maxY+18;
        const availableWidth = Math.max(100, this.width - 40);
        const availableHeight = Math.max(100, this.height - 120);
        this.scale = Math.max(this.minScale, Math.min(1, availableWidth / (maxX-minX), availableHeight / (maxY-minY)));
        this.translateX = (this.width - (maxX-minX)*this.scale) / 2 - minX*this.scale;
        this.translateY = 70 + (availableHeight - (maxY-minY)*this.scale) / 2 - minY*this.scale;
        this.updateTransform();
    },

    /**
     * Render the entire canvas
     */
    render() {
        if (!this.mainGroup && this.svg) { this.mainGroup = this.svg.select("g.main-group"); if (this.mainGroup.empty()) { this.mainGroup = this.svg.append("g").attr("class", "main-group"); } } if (!this.mainGroup || this.mainGroup.empty()) {
            console.warn("Canvas not initialized");
            return;
        }
        const focused=document.activeElement;
        const focusedId=this.svg.node().contains(focused)?focused?.__data__?.id:null;
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
        if(focusedId)this.mainGroup.selectAll('[data-element-id]').filter(d=>d.id===focusedId).node()?.focus();
        
    },

    /**
     * Render stocks
     */
    /** Greedy text wrapping. Exceptional long names retain a native full-name title. */
    wrapLabel(name, columns=16, maximum=3) {
        const words=String(name||'Unnamed').trim().split(/\s+/),lines=[];
        let line='';
        for(const word of words){
            const chunks=Array.from(word);const parts=[];
            while(chunks.length>columns)parts.push(chunks.splice(0,columns).join(''));
            if(chunks.length)parts.push(chunks.join(''));
            for(const part of parts){
                if(line&&line.length+part.length+1>columns){lines.push(line);line='';}
                line+=(line?' ':'')+part;
            }
        }
        if(line)lines.push(line);
        if(lines.length>maximum){lines.length=maximum;lines[maximum-1]=lines[maximum-1].replace(/[ .…]+$/,'')+'…';}
        return lines.length?lines:['Unnamed'];
    },
    flowLabelWidth(element) {return Math.min(104,Math.max(40,...this.wrapLabel(element.name,17,3).map(line=>line.length*6+14)));},
    nodeMetrics(type,element) {
        if(type==='stock')return {width:this.stockWidth,height:this.stockHeight,radius:7};
        if(type==='flow')return {width:24,height:24,radius:0};
        return {width:110,height:42,radius:21};
    },
    nodeBounds(type,element,hit=false) {
        const {width,height}=this.nodeMetrics(type,element),p=element.position;
        let left=-width/2,right=width/2,top=-height/2,bottom=height/2;
        if(type==='flow'){
            left=-Math.max(22,this.flowLabelWidth(element)/2);right=-left;top=-22;
            bottom=26+this.wrapLabel(element.name,17,3).length*12;
        }
        const pad=hit?4:0;
        return {minX:p.x+left-pad,maxX:p.x+right+pad,minY:p.y+top-pad,maxY:p.y+bottom+pad};
    },
    containsPoint(type,element,x,y) {
        const b=this.nodeBounds(type,element,true);
        return x>=b.minX&&x<=b.maxX&&y>=b.minY&&y<=b.maxY;
    },
    /** Intersect a ray with the actual rounded node body, then leave a small gap. */
    boundaryPoint(type,element,toward,gap=3) {
        const p=element.position,m=this.nodeMetrics(type,element);
        let dx=toward.x-p.x,dy=toward.y-p.y;
        const length=Math.hypot(dx,dy);
        if(length<1e-9){dx=1;dy=0;}else{dx/=length;dy/=length;}
        const inside=distance=>{
            const x=Math.abs(dx*distance),y=Math.abs(dy*distance),r=m.radius;
            if(x>m.width/2||y>m.height/2)return false;
            if(!r)return true;
            const cx=Math.max(0,x-(m.width/2-r)),cy=Math.max(0,y-(m.height/2-r));
            return cx*cx+cy*cy<=r*r;
        };
        let low=0,high=Math.hypot(m.width,m.height);
        for(let i=0;i<32;i++){const mid=(low+high)/2;if(inside(mid))low=mid;else high=mid;}
        return {x:p.x+dx*(low+gap),y:p.y+dy*(low+gap)};
    },
    connectorGeometry(from,to) {
        const a=from.element.position,b=to.element.position,dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy);
        if(len<1e-6){
            const reach=Math.max(this.nodeMetrics(from.type,from.element).width,this.nodeMetrics(to.type,to.element).width)/2+48;
            const p=this.boundaryPoint(from.type,from.element,{x:a.x+reach,y:a.y-reach});
            const q=this.boundaryPoint(to.type,to.element,{x:b.x+reach,y:b.y+reach});
            return {path:`M${p.x},${p.y} C${a.x+reach},${a.y-reach} ${b.x+reach},${b.y+reach} ${q.x},${q.y}`,points:[p,q,{x:a.x+reach,y:a.y-reach},{x:b.x+reach,y:b.y+reach}]};
        }
        const bend=Math.min(28,len*.16),control={x:(a.x+b.x)/2-dy/len*bend,y:(a.y+b.y)/2+dx/len*bend};
        const p=this.boundaryPoint(from.type,from.element,control),q=this.boundaryPoint(to.type,to.element,control);
        return {path:`M${p.x},${p.y} Q${control.x},${control.y} ${q.x},${q.y}`,points:[p,control,q]};
    },
    modelBounds() {
        const bounds=[];
        for(const [type,key] of [['stock','stocks'],['flow','flows'],['variable','variables']]){
            for(const element of App.model[key])bounds.push(this.nodeBounds(type,element));
        }
        for(const connector of App.model.connectors){
            const from=App.findElement(connector.from_element),to=App.findElement(connector.to_element);
            if(from&&to)for(const point of this.connectorGeometry(from,to).points)bounds.push({minX:point.x,maxX:point.x,minY:point.y,maxY:point.y});
        }
        if(!bounds.length)return null;
        return {minX:Math.min(...bounds.map(b=>b.minX)),maxX:Math.max(...bounds.map(b=>b.maxX)),minY:Math.min(...bounds.map(b=>b.minY)),maxY:Math.max(...bounds.map(b=>b.maxY))};
    },
    nodeGroup(layer,type,elements) {
        const self=this;
        const groups=layer.selectAll(`g.${type}`).data(elements,d=>d.id).enter().append('g')
            .attr('class',d=>`${type} diagram-node${App.selected?.id===d.id?' is-selected':''}`)
            .attr('transform',d=>`translate(${d.position.x},${d.position.y})`)
            .attr('tabindex',0).attr('role','button').attr('data-keyboard-ready','true').attr('data-element-id',d=>d.id)
            .attr('aria-label',d=>`${type}: ${d.name}`).attr('aria-pressed',d=>App.selected?.id===d.id?'true':'false')
            .on('click',function(event,d){self.handleElementClick(type,d,event);})
            .on('mousedown',function(event,d){self.startDrag(type,d,event);})
            .on('keydown',function(event,d){if(event.key==='Enter'||event.key===' '){event.preventDefault();self.handleElementClick(type,d,event);}});
        groups.append('title').text(d=>`${d.name}${d.units?' · '+d.units:''}`);
        return groups;
    },
    appendLabel(group,name,columns,y,lineHeight=12,maximum=3) {
        const lines=this.wrapLabel(name,columns,maximum);
        const label=group.append('text').attr('class','element-label').attr('x',0);
        lines.forEach((line,index)=>label.append('tspan').attr('x',0).attr('y',y+index*lineHeight).text(line));
    },
    renderStocks(layer) {
        const self=this,groups=this.nodeGroup(layer,'stock',App.model.stocks);
        groups.append('rect').attr('class','stock-rect').attr('x',-this.stockWidth/2).attr('y',-this.stockHeight/2)
            .attr('width',this.stockWidth).attr('height',this.stockHeight).attr('rx',7);
        groups.append('path').attr('class','stock-accent').attr('d',`M${-this.stockWidth/2+10},${-this.stockHeight/2+1} H${this.stockWidth/2-10}`);
        groups.append('text').attr('class','node-eyebrow').attr('x',0).attr('y',-18).text('STOCK');
        groups.each(function(d){const lines=self.wrapLabel(d.name,17,3);self.appendLabel(d3.select(this),d.name,17,6-(lines.length-1)*6,12);});
    },
    renderFlows(layer) {
        const self=this,groups=this.nodeGroup(layer,'flow',App.model.flows);
        groups.append('rect').attr('class','node-hit').attr('x',-22).attr('y',-22).attr('width',44).attr('height',44).attr('rx',8);
        groups.append('path').attr('class','flow-valve').attr('d','M-10,-9 L10,9 L10,-9 L-10,9 Z');
        groups.append('circle').attr('class','valve-center').attr('r',2.5);
        groups.each(function(d){
            const group=d3.select(this),lines=self.wrapLabel(d.name,17,3);
            group.append('rect').attr('class','flow-label-plate').attr('x',-self.flowLabelWidth(d)/2).attr('y',19).attr('width',self.flowLabelWidth(d)).attr('height',lines.length*12+7).attr('rx',4);
            self.appendLabel(group,d.name,17,30,12);
        });
    },
    renderVariables(layer) {
        const self=this,groups=this.nodeGroup(layer,'variable',App.model.variables);
        groups.append('rect').attr('class','variable-capsule').attr('x',-55).attr('y',-21).attr('width',110).attr('height',42).attr('rx',21);
        groups.append('circle').attr('class','variable-circle').attr('cx',-43).attr('r',3.5);
        groups.each(function(d){
            const group=d3.select(this),lines=self.wrapLabel(d.name,15,3);
            const label=group.append('text').attr('class','element-label');
            lines.forEach((line,index)=>label.append('tspan').attr('x',5).attr('y',4-(lines.length-1)*5.7+index*11.4).text(line));
        });
    },
    renderFlowLines(layer) {
        for(const flow of App.model.flows){
            const valve={type:'flow',element:flow};
            if(flow.from_stock){const stock=App.model.stocks.find(s=>s.id===flow.from_stock||s.name===flow.from_stock);if(stock)this.drawFlowLine(layer,{type:'stock',element:stock},valve);}
            if(flow.to_stock){const stock=App.model.stocks.find(s=>s.id===flow.to_stock||s.name===flow.to_stock);if(stock)this.drawFlowLine(layer,valve,{type:'stock',element:stock});}
        }
    },
    drawFlowLine(layer,from,to) {
        const p=this.boundaryPoint(from.type,from.element,to.element.position,1),q=this.boundaryPoint(to.type,to.element,from.element.position,5);
        // Coincident primitives have no defined direction; keep endpoints finite.
        const dx=to.element.position.x-from.element.position.x,dy=to.element.position.y-from.element.position.y;
        if(Math.hypot(dx,dy)<1e-6||(q.x-p.x)*dx+(q.y-p.y)*dy<=0)return;
        layer.append('line').attr('class','flow-line').attr('x1',p.x).attr('y1',p.y).attr('x2',q.x).attr('y2',q.y).attr('marker-end','url(#arrowhead)');
    },
    renderConnectors(layer) {
        for(const connector of App.model.connectors){
            const from=App.findElement(connector.from_element),to=App.findElement(connector.to_element);
            if(!from||!to)continue;
            const geometry=this.connectorGeometry(from,to),selected=App.selected?.id===connector.id;
            layer.append('path').attr('class',`connector-line${selected?' selected':''}`).attr('d',geometry.path).attr('marker-end','url(#connector-arrow)');
            layer.append('path').datum(connector).attr('data-element-id',connector.id).attr('class','connector-hit').attr('d',geometry.path).attr('tabindex',0).attr('role','button')
                .attr('aria-label',`Dependency: ${from.element.name} to ${to.element.name}`)
                .on('click',event=>{event.stopPropagation();App.selectElement('connector',connector.id);})
                .on('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();App.selectElement('connector',connector.id);}});
        }
    },
    truncateLabel(text,maxLen) {return this.wrapLabel(text,maxLen,1)[0];},
    getElementPosition(nameOrId) {return App.findElement(nameOrId)?.element.position||null;}
};