$(function() {
    // Canvas Pan & Zoom State
    let zoom = 1.0;
    const minZoom = 0.25;
    const maxZoom = 2.5;
    let panX = 100;
    let panY = 100;
    let isPanning = false;
    let panStartX = 0;
    let panStartY = 0;

    // Connection drawing state
    let activeWire = null;
    let drawingConnection = null; // { nodeId, portIndex, direction, type, x, y }

    // User interaction tracking (stops polling refresh while dragging)
    let isUserInteracting = false;
    let pollTimeout = null;

    // Selected state
    let selectedNodeId = null;

    // Node templates dictionary
    let nodeTemplates = {};

    // Initialization
    function init() {
        applyTransform();
        loadNodeTemplates();
        loadFlow();
        setupEventHandlers();
        
        // Start log polling
        setInterval(loadLogs, 2000);

        // Start dynamic flow value updates polling
        scheduleNextPoll(1000);
    }

    // Apply Translate & Scale to Canvas Content
    function applyTransform() {
        $('#canvas-content').css({
            'transform': `translate(${panX}px, ${panY}px) scale(${zoom})`
        });
        $('#zoom-level').text(`${Math.round(zoom * 100)}%`);
    }

    // Map Backend Nodes to Categories
    function getNodeCategory(title) {
        if (['Add', 'Subtract', 'Multiply', 'Divide'].includes(title)) return 'Math';
        if (['Number', 'String', 'Concat', 'Uppercase'].includes(title)) return 'String';
        if (['Compare', 'If/Else'].includes(title)) return 'Logic';
        if (['Random', 'Log'].includes(title)) return 'Utility';
        if (['Trigger', 'Branch', 'Counter'].includes(title)) return 'Exec';
        return 'Utility';
    }

    // API calls: Load Node Templates from Server
    function loadNodeTemplates() {
        $.getJSON('/api/nodes', function(data) {
            let libraryHtml = '';
            let categories = {};
            
            data.forEach(tpl => {
                nodeTemplates[tpl.identifier] = tpl;
                let cat = getNodeCategory(tpl.title);
                if (!categories[cat]) categories[cat] = [];
                categories[cat].push(tpl);
            });

            // Render Sidebar Node Items
            Object.keys(categories).sort().forEach(cat => {
                let catColor = '';
                libraryHtml += `
                    <div class="node-category" data-category="${cat}">
                        <div class="category-title">${cat} Nodes</div>
                `;
                categories[cat].forEach(tpl => {
                    libraryHtml += `
                        <div class="node-item" data-identifier="${tpl.identifier}" data-category="${cat}">
                            <span>${tpl.title}</span>
                            <span class="material-icons-round add-icon" title="Add to canvas">add</span>
                        </div>
                    `;
                });
                libraryHtml += `</div>`;
            });

            $('#node-library').html(libraryHtml);
            setupSidebarDrag();
        });
    }

    // API calls: Load Flow State (Nodes & Connections)
    function loadFlow() {
        $.getJSON('/api/flow', function(flowData) {
            // Update execution mode selector if needed
            $('#alg-mode-select').val(flowData.algorithm_mode);

            // Sync pause button
            updatePauseButtonState(flowData.execution_paused);

            // Render Nodes
            renderNodes(flowData.nodes);

            // Render Connections (Wires)
            renderConnections(flowData.connections);
        });
    }

    function updatePauseButtonState(paused) {
        let btn = $('#btn-pause');
        if (paused) {
            btn.removeClass('btn-secondary').addClass('btn-warning')
               .html('<span class="material-icons-round">play_arrow</span> Resume')
               .attr('title', 'Resume all execution');
        } else {
            btn.removeClass('btn-warning').addClass('btn-secondary')
               .html('<span class="material-icons-round">pause</span> Pause')
               .attr('title', 'Pause all execution');
        }
    }

    // Cache port offset coordinates relative to node card top-left
    function cacheLocalPortOffsets(nodeCardEl) {
        nodeCardEl.find('.port-handle').each(function() {
            let handle = this;
            let x = handle.offsetLeft + handle.offsetWidth / 2;
            let y = handle.offsetTop + handle.offsetHeight / 2;
            
            let parent = handle.offsetParent;
            while (parent && !parent.classList.contains('node-card')) {
                x += parent.offsetLeft;
                y += parent.offsetTop;
                parent = parent.offsetParent;
            }
            
            handle.setAttribute('data-local-x', x);
            handle.setAttribute('data-local-y', y);
        });
    }

    // Render Nodes onto Canvas
    function renderNodes(nodes) {
        let nodesLayer = $('#nodes-layer');
        
        // Remove nodes that are no longer in flow
        let currentIds = nodes.map(n => n.id.toString());
        $('.node-card').each(function() {
            let id = $(this).attr('data-id');
            if (!currentIds.includes(id)) {
                $(this).remove();
            }
        });

        // Add or Update Node Cards
        nodes.forEach(n => {
            let cat = getNodeCategory(n.title);
            let nodeEl = $(`.node-card[data-id="${n.id}"]`);

            // If node doesn't exist, create it
            if (nodeEl.length === 0) {
                nodeEl = $(`
                    <div class="node-card" data-id="${n.id}" data-category="${cat}">
                        <div class="node-header">
                            <span class="node-title">${n.title}</span>
                            <div class="node-actions">
                                <button class="node-action-btn delete-btn" title="Delete node">
                                    <span class="material-icons-round">close</span>
                                </button>
                            </div>
                        </div>
                        <div class="node-ports"></div>
                        <div class="node-timer-wrapper">
                            <div class="timer-row">
                                <label class="timer-toggle-label">
                                    <input type="checkbox" class="loop-toggle" data-node="${n.id}">
                                    <span class="material-icons-round timer-icon">schedule</span>
                                    <span class="timer-text">Repeat</span>
                                </label>
                                <input type="number" class="loop-interval" data-node="${n.id}" min="0.1" step="0.1" value="1.0">
                                <span class="timer-unit">s</span>
                            </div>
                            <div class="force-trigger-row" style="margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.03); padding-top: 4px; display: flex; align-items: center; gap: 4px;">
                                <label class="force-trigger-label" style="display: flex; align-items: center; gap: 4px; cursor: pointer; user-select: none; font-size: 0.7rem; color: var(--text-secondary);">
                                    <input type="checkbox" class="force-trigger-toggle" data-node="${n.id}">
                                    <span class="material-icons-round" style="font-size: 14px; color: var(--text-muted);">lock</span>
                                    <span>Force Trigger</span>
                                </label>
                            </div>
                        </div>
                        <div class="node-resize-handle"></div>
                    </div>
                `);
                nodesLayer.append(nodeEl);
                setupNodeDragging(nodeEl);
                setupNodeResizing(nodeEl);
            }

            // Update target node id attribute
            nodeEl.attr('data-target-node-id', n.target_node_id || '');

            // Add custom trigger button for Execute Button node
            if (n.title === 'Execute Button') {
                if (nodeEl.find('.node-custom-content').length === 0) {
                    nodeEl.find('.node-ports').after(`
                        <div class="node-custom-content" style="padding: 0 14px 10px 14px; display: flex; justify-content: center;">
                            <button class="btn btn-primary btn-trigger-action" data-node="${n.id}" style="width: 100%; justify-content: center; padding: 6px 12px; font-size: 0.8rem;">
                                <span class="material-icons-round" style="font-size: 16px;">play_arrow</span> Trigger
                            </button>
                        </div>
                    `);
                }
            } else {
                nodeEl.find('.node-custom-content').remove();
            }

            // Update Position and Dimensions
            nodeEl.css({
                left: `${n.x}px`,
                top: `${n.y}px`
            });
            nodeEl.attr('data-x', n.x).attr('data-y', n.y);

            let currentWidth = n.width || 200;
            let currentHeight = n.height || 120;
            nodeEl.attr('data-width', currentWidth).attr('data-height', currentHeight);

            if (n.width) {
                nodeEl.css('width', `${n.width}px`);
            }
            if (n.height) {
                nodeEl.css('min-height', `${n.height}px`);
            }

            // Update Ports content
            let portsContainer = nodeEl.find('.node-ports').empty();
            
            // Build input/output rows
            let maxPorts = Math.max(n.inputs.length, n.outputs.length);
            for (let i = 0; i < maxPorts; i++) {
                let row = $('<div class="port-row"></div>');
                
                // Input Port (Left side)
                if (i < n.inputs.length) {
                    let inp = n.inputs[i];
                    let isExec = inp.type === 'exec';
                    
                    let inpCol = $('<div class="port-input-container"></div>');
                    inpCol.append(`<span class="port-label">${inp.label}</span>`);
                    
                    // Render input widget if NOT connected and type is data
                    if (!isExec) {
                        // We check connection mapping during render, but for simplicity:
                        // Let's check if there's any active wire targeting this input
                        // If not connected, show input field
                        let inputWidget = $(`<input type="text" class="port-inline-input" data-node="${n.id}" data-index="${i}" value="${inp.val !== null ? inp.val : ''}">`);
                        inpCol.append(inputWidget);
                    }

                    row.append(inpCol);
                    row.append(`<div class="port-handle input ${isExec ? 'exec' : ''}" data-node="${n.id}" data-index="${i}" data-direction="input" data-type="${inp.type}" title="${inp.label} (${inp.type})"></div>`);
                }

                // Output Port (Right side)
                if (i < n.outputs.length) {
                    let out = n.outputs[i];
                    let isExec = out.type === 'exec';

                    let outCol = $('<div class="port-output-container"></div>');
                    outCol.append(`<span class="port-label">${out.label}</span>`);

                    if (!isExec && out.val !== null) {
                        outCol.append(`<span class="port-value-display" title="${out.val}">${out.val}</span>`);
                    }

                    row.append(outCol);
                    row.append(`<div class="port-handle output ${isExec ? 'exec' : ''}" data-node="${n.id}" data-index="${i}" data-direction="output" data-type="${out.type}" title="${out.label} (${out.type})"></div>`);
                }

                portsContainer.append(row);
            }

            // Cache local port offsets in DOM attributes
            cacheLocalPortOffsets(nodeEl);

            // Update looping checkbox and interval values
            let loopToggle = nodeEl.find('.loop-toggle');
            let loopInterval = nodeEl.find('.loop-interval');
            let timerIcon = nodeEl.find('.timer-icon');

            loopToggle.prop('checked', n.loop_enabled);
            loopInterval.val(n.loop_interval);
            if (n.loop_enabled) {
                nodeEl.addClass('timer-active');
                timerIcon.addClass('active');
            } else {
                nodeEl.removeClass('timer-active');
                timerIcon.removeClass('active');
            }

            // Update force-trigger checkbox
            let forceTriggerToggle = nodeEl.find('.force-trigger-toggle');
            forceTriggerToggle.prop('checked', n.force_trigger || false);

            // Restore selection state
            if (selectedNodeId === n.id.toString()) {
                nodeEl.addClass('selected');
            }
        });

        // Hide inputs that have connections (we check dynamically in jquery after drawing)
        setTimeout(updateInputsVisibility, 50);
    }

    // Update Input field visibility based on whether they have connections
    function updateInputsVisibility() {
        $('.port-inline-input').show(); // Reset
        
        // Find all wires and hide corresponding inputs
        $('.wire-path').each(function() {
            let destNode = $(this).attr('data-dest-node');
            let destPort = $(this).attr('data-dest-port');
            $(`.port-inline-input[data-node="${destNode}"][data-index="${destPort}"]`).hide();
        });
    }

    // Render Connection Wires (Bezier Curves)
    function renderConnections(connections) {
        let wiresGroup = $('#wires-group').empty();
        
        connections.forEach((conn, index) => {
            let path = calculateCurve(conn.parent_node_id, conn.output_index, conn.connected_node_id, conn.input_index);
            if (!path) return;

            let isExec = path.type === 'exec';
            let wire = $(document.createElementNS("http://www.w3.org/2000/svg", "path"))
                .attr('d', path.d)
                .attr('class', `wire-path ${isExec ? 'exec' : ''}`)
                .attr('data-parent-node', conn.parent_node_id)
                .attr('data-parent-port', conn.output_index)
                .attr('data-dest-node', conn.connected_node_id)
                .attr('data-dest-port', conn.input_index)
                .attr('title', 'Right-click wire to delete');

            wiresGroup.append(wire);
        });

        // Draw virtual trigger wires for Execute Buttons
        $('.node-card').each(function() {
            let sourceCard = $(this);
            let targetId = sourceCard.attr('data-target-node-id');
            if (targetId) {
                let targetCard = $(`.node-card[data-id="${targetId}"]`);
                if (targetCard.length > 0) {
                    let path = calculateVirtualTriggerCurve(sourceCard, targetCard);
                    if (path) {
                        let wire = $(document.createElementNS("http://www.w3.org/2000/svg", "path"))
                            .attr('d', path.d)
                            .attr('class', 'wire-path virtual-trigger')
                            .attr('data-parent-node', sourceCard.attr('data-id'))
                            .attr('data-dest-node', targetId)
                            .attr('title', 'Right-click virtual wire to delete link');
                        wiresGroup.append(wire);
                    }
                }
            }
        });
        
        updateInputsVisibility();
    }

    // Get local coordinate of a port handle, dynamically recalculating if not cached
    function getPortLocalCoords(handle) {
        let lx = parseFloat(handle.attr('data-local-x'));
        let ly = parseFloat(handle.attr('data-local-y'));

        if (isNaN(lx) || lx === 0 || isNaN(ly) || ly === 0) {
            let el = handle[0];
            let x = el.offsetLeft + el.offsetWidth / 2;
            let y = el.offsetTop + el.offsetHeight / 2;

            let parent = el.offsetParent;
            while (parent && !parent.classList.contains('node-card')) {
                x += parent.offsetLeft;
                y += parent.offsetTop;
                parent = parent.offsetParent;
            }

            if (x > 0 && y > 0) {
                handle.attr('data-local-x', x);
                handle.attr('data-local-y', y);
            }
            return { x: x || 0, y: y || 0 };
        }
        return { x: lx, y: ly };
    }

    // Calculate Bezier Curve coordinates between ports (using cached coordinates to avoid layout reflows)
    function calculateCurve(pNodeId, oIndex, cNodeId, iIndex) {
        let outHandle = $(`.port-handle.output[data-node="${pNodeId}"][data-index="${oIndex}"]`);
        let inpHandle = $(`.port-handle.input[data-node="${cNodeId}"][data-index="${iIndex}"]`);

        if (outHandle.length === 0 || inpHandle.length === 0) return null;

        let pCard = $(`.node-card[data-id="${pNodeId}"]`);
        let cCard = $(`.node-card[data-id="${cNodeId}"]`);

        let px = parseFloat(pCard.attr('data-x')) || 0;
        let py = parseFloat(pCard.attr('data-y')) || 0;
        let cx = parseFloat(cCard.attr('data-x')) || 0;
        let cy = parseFloat(cCard.attr('data-y')) || 0;

        let coords1 = getPortLocalCoords(outHandle);
        let coords2 = getPortLocalCoords(inpHandle);

        let x1 = px + coords1.x;
        let y1 = py + coords1.y;
        let x2 = cx + coords2.x;
        let y2 = cy + coords2.y;

        let portType = outHandle.attr('data-type');
        let dx = Math.abs(x2 - x1) * 0.5;
        let d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;

        return { d, type: portType };
    }

    // Calculate Bezier Curve coordinates for virtual trigger wires
    function calculateVirtualTriggerCurve(sourceCard, targetCard) {
        let sx = parseFloat(sourceCard.attr('data-x')) || 0;
        let sy = parseFloat(sourceCard.attr('data-y')) || 0;
        let sw = parseFloat(sourceCard.attr('data-width')) || 200;

        let tx = parseFloat(targetCard.attr('data-x')) || 0;
        let ty = parseFloat(targetCard.attr('data-y')) || 0;
        let tw = parseFloat(targetCard.attr('data-width')) || 200;

        // Start from the trigger output handle of the Execute Button card
        let outHandle = sourceCard.find('.port-handle.output[data-index="0"]');
        let x1, y1;
        if (outHandle.length > 0) {
            let coords = getPortLocalCoords(outHandle);
            x1 = sx + coords.x;
            y1 = sy + coords.y;
        } else {
            x1 = sx + sw;
            y1 = sy + 30;
        }

        // End at top-center of target card
        let x2 = tx + tw / 2;
        let y2 = ty + 15; // middle of header

        let dx1 = Math.min(100, Math.max(30, Math.abs(x2 - x1) * 0.3));
        let dy2 = Math.min(100, Math.max(40, Math.abs(y2 - y1) * 0.3));
        let d = `M ${x1} ${y1} C ${x1 + dx1} ${y1}, ${x2} ${y2 - dy2}, ${x2} ${y2}`;

        return { d };
    }

    // Refresh Wires Drawing
    function refreshWires() {
        $('.wire-path:not(.drawing)').each(function() {
            let pNodeId = $(this).attr('data-parent-node');
            let oIndex = $(this).attr('data-parent-port');
            let cNodeId = $(this).attr('data-dest-node');
            let iIndex = $(this).attr('data-dest-port');
            
            if ($(this).hasClass('virtual-trigger')) {
                let sourceCard = $(`.node-card[data-id="${pNodeId}"]`);
                let targetCard = $(`.node-card[data-id="${cNodeId}"]`);
                if (sourceCard.length > 0 && targetCard.length > 0) {
                    let path = calculateVirtualTriggerCurve(sourceCard, targetCard);
                    if (path) {
                        $(this).attr('d', path.d);
                    }
                }
            } else {
                let path = calculateCurve(pNodeId, oIndex, cNodeId, iIndex);
                if (path) {
                    $(this).attr('d', path.d);
                }
            }
        });
    }

    // Setup Sidebar drag and drop
    function setupSidebarDrag() {
        $('.node-item').off('click').on('click', function() {
            let identifier = $(this).attr('data-identifier');
            
            // Create at center of viewport
            let viewport = $('#canvas-viewport');
            let x = (viewport.width() / 2 - panX) / zoom;
            let y = (viewport.height() / 2 - panY) / zoom;

            createNode(identifier, x, y);
        });
    }

    // Create a new node in the backend
    function createNode(identifier, x, y) {
        $.ajax({
            url: '/api/create_node',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ identifier, x, y }),
            success: function() {
                loadFlow();
            }
        });
    }

    // Setup node dragging with zoom consideration
    function setupNodeDragging(nodeEl) {
        let isDragging = false;
        let startX, startY;

        nodeEl.find('.node-header').on('mousedown', function(e) {
            if ($(e.target).closest('.node-action-btn').length > 0) return;
            
            isDragging = true;
            isUserInteracting = true;
            nodeEl.addClass('selected');
            selectedNodeId = nodeEl.attr('data-id');
            $('.node-card').not(nodeEl).removeClass('selected');

            // Store original positions
            startX = e.clientX;
            startY = e.clientY;
            let currentX = parseFloat(nodeEl.css('left'));
            let currentY = parseFloat(nodeEl.css('top'));

            $(document).on('mousemove.drag', function(ev) {
                if (!isDragging) return;
                // Important: adjust dx and dy based on zoom level!
                let dx = (ev.clientX - startX) / zoom;
                let dy = (ev.clientY - startY) / zoom;

                let nx = currentX + dx;
                let ny = currentY + dy;
                nodeEl.css({
                    left: `${nx}px`,
                    top: `${ny}px`
                });
                nodeEl.attr('data-x', nx).attr('data-y', ny);

                // Update paths
                refreshWires();
            });

            $(document).on('mouseup.drag', function() {
                isDragging = false;
                isUserInteracting = false;
                $(document).off('.drag');

                // Save new position in backend
                let finalX = parseFloat(nodeEl.attr('data-x'));
                let finalY = parseFloat(nodeEl.attr('data-y'));
                $.ajax({
                    url: '/api/move_node',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        node_id: nodeEl.attr('data-id'),
                        x: finalX,
                        y: finalY
                    })
                });
            });
        });
    }

    // Setup node manual resizing
    function setupNodeResizing(nodeEl) {
        let isResizing = false;
        let startWidth, startHeight, startX, startY;

        nodeEl.find('.node-resize-handle').on('mousedown', function(e) {
            e.stopPropagation();
            e.preventDefault();
            isResizing = true;
            isUserInteracting = true;
            
            startX = e.clientX;
            startY = e.clientY;
            startWidth = nodeEl.outerWidth();
            startHeight = nodeEl.outerHeight();

            $(document).on('mousemove.resize', function(ev) {
                if (!isResizing) return;
                let dw = (ev.clientX - startX) / zoom;
                let dh = (ev.clientY - startY) / zoom;
                let nw = Math.max(160, startWidth + dw);
                let nh = Math.max(100, startHeight + dh);
                nodeEl.css({
                    width: `${nw}px`,
                    minHeight: `${nh}px`
                });
                nodeEl.attr('data-width', nw).attr('data-height', nh);
                refreshWires();
            });

            $(document).on('mouseup.resize', function() {
                isResizing = false;
                isUserInteracting = false;
                $(document).off('.resize');
                
                // Recalculate local port offsets since height change moves handles
                cacheLocalPortOffsets(nodeEl);
                
                // Save dimensions
                let finalWidth = nodeEl.attr('data-width');
                let finalHeight = nodeEl.attr('data-height');
                $.ajax({
                    url: '/api/move_node',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        node_id: nodeEl.attr('data-id'),
                        x: parseFloat(nodeEl.attr('data-x')),
                        y: parseFloat(nodeEl.attr('data-y')),
                        width: finalWidth,
                        height: finalHeight
                    })
                });
            });
        });
    }

    // Polling function for live value updates
    function pollFlowUpdates() {
        // Skip updates if user is interacting with canvas/nodes or if typing
        if (isUserInteracting || isPanning || drawingConnection || $('.port-inline-input:focus').length > 0) return;
        
        $.getJSON('/api/flow', function(flowData) {
            updateFlowValues(flowData);
        });
    }

    // Dynamic, focus-safe update of flow values in DOM
    function updateFlowValues(flowData) {
        flowData.nodes.forEach(n => {
            let nodeEl = $(`.node-card[data-id="${n.id}"]`);
            if (nodeEl.length === 0) return;

            // Keep target node ID synced in DOM data attribute
            nodeEl.attr('data-target-node-id', n.target_node_id || '');

            // Update inputs if they are not focused
            n.inputs.forEach((inp, idx) => {
                if (inp.type === 'data') {
                    let inputWidget = nodeEl.find(`.port-inline-input[data-index="${idx}"]`);
                    if (inputWidget.length > 0 && !inputWidget.is(':focus')) {
                        if (inputWidget.val() !== String(inp.val !== null ? inp.val : '')) {
                            inputWidget.val(inp.val !== null ? inp.val : '');
                        }
                    }
                }
            });

            // Update outputs in place
            n.outputs.forEach((out, idx) => {
                if (out.type === 'data') {
                    let outCol = nodeEl.find('.port-output-container').eq(idx);
                    let valDisplay = outCol.find('.port-value-display');
                    
                    if (out.val !== null) {
                        let textVal = String(out.val);
                        if (valDisplay.length === 0) {
                            outCol.append(`<span class="port-value-display" title="${textVal}">${textVal}</span>`);
                        } else if (valDisplay.text() !== textVal) {
                            valDisplay.text(textVal).attr('title', textVal);
                        }
                    } else {
                        valDisplay.remove();
                    }
                }
            });

            // Update looping widgets
            let loopToggle = nodeEl.find('.loop-toggle');
            let loopInterval = nodeEl.find('.loop-interval');
            let timerIcon = nodeEl.find('.timer-icon');

            if (loopToggle.length > 0 && !loopToggle.is(':active')) {
                loopToggle.prop('checked', n.loop_enabled);
            }
            if (loopInterval.length > 0 && !loopInterval.is(':focus')) {
                loopInterval.val(n.loop_interval);
            }

            if (n.loop_enabled) {
                nodeEl.addClass('timer-active');
                timerIcon.addClass('active');
            } else {
                nodeEl.removeClass('timer-active');
                timerIcon.removeClass('active');
            }

            // Update force-trigger widget
            let forceTriggerToggle = nodeEl.find('.force-trigger-toggle');
            if (forceTriggerToggle.length > 0 && !forceTriggerToggle.is(':active')) {
                forceTriggerToggle.prop('checked', n.force_trigger || false);
            }
        });
    }


    // Setup General Event Handlers
    function setupEventHandlers() {
        let viewport = $('#canvas-viewport');

        // Panning handler
        viewport.on('mousedown', function(e) {
            // Only pan if clicked directly on canvas background
            if ($(e.target).closest('.node-card, .port-handle').length > 0) return;
            
            isPanning = true;
            panStartX = e.clientX - panX;
            panStartY = e.clientY - panY;
            viewport.css('cursor', 'grabbing');

            $(document).on('mousemove.pan', function(ev) {
                if (!isPanning) return;
                panX = ev.clientX - panStartX;
                panY = ev.clientY - panStartY;
                applyTransform();
            });

            $(document).on('mouseup.pan', function() {
                isPanning = false;
                viewport.css('cursor', 'grab');
                $(document).off('.pan');
            });
        });

        // Zooming handler (Mousewheel)
        viewport.on('wheel', function(e) {
            e.preventDefault();
            let delta = e.originalEvent.deltaY;
            let zoomFactor = delta < 0 ? 1.1 : 0.9;
            
            // Zoom relative to mouse cursor
            let mouseX = e.clientX - viewport.offset().left;
            let mouseY = e.clientY - viewport.offset().top;

            let canvasMouseX = (mouseX - panX) / zoom;
            let canvasMouseY = (mouseY - panY) / zoom;

            let newZoom = Math.max(minZoom, Math.min(maxZoom, zoom * zoomFactor));
            
            panX = mouseX - canvasMouseX * newZoom;
            panY = mouseY - canvasMouseY * newZoom;
            zoom = newZoom;
            
            applyTransform();
        });

        // Click on Canvas Deselects Node
        viewport.on('click', function(e) {
            if ($(e.target).closest('.node-card').length === 0) {
                $('.node-card').removeClass('selected');
                selectedNodeId = null;
            }
        });

        // Toolbar Button handlers
        $('#btn-save').on('click', function() {
            $.post('/api/save', function(res) {
                alert(`Project saved successfully to: ${res.filepath}`);
            });
        });

        $('#btn-load').on('click', function() {
            $.post('/api/load', function() {
                loadFlow();
                addLog('Loaded saved project flow');
            }).fail(function() {
                alert('No saved project file found.');
            });
        });

        $('#btn-clear').on('click', function() {
            if (confirm('Clear entire flow?')) {
                $.post('/api/clear', function() {
                    loadFlow();
                    addLog('Cleared workspace flow');
                });
            }
        });

        $('#btn-pause').on('click', function() {
            let isCurrentlyPaused = $(this).hasClass('btn-warning');
            let newPausedState = !isCurrentlyPaused;
            $.ajax({
                url: '/api/set_paused',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ paused: newPausedState }),
                success: function() {
                    loadFlow();
                    addLog(newPausedState ? 'Paused all execution loops' : 'Resumed all execution loops');
                }
            });
        });

        $('#btn-run').on('click', function() {
            // Trigger update on NumberNodes to flow through
            $('.node-card[data-category="String"], .node-card[data-category="Math"]').each(function() {
                let id = $(this).attr('data-id');
                $.ajax({
                    url: '/api/trigger_node',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ node_id: id })
                });
            });
            setTimeout(loadFlow, 200);
            addLog('Manually triggered flow execution');
        });

        $('#alg-mode-select').on('change', function() {
            let mode = $(this).val();
            $.ajax({
                url: '/api/set_alg_mode',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ mode }),
                success: function() {
                    loadFlow();
                    addLog(`Switched execution mode to: ${mode}`);
                }
            });
        });

        // Info Modal toggle handlers
        $('#btn-mode-info').on('click', function() {
            $('#mode-info-modal').fadeIn(200);
        });

        $('#btn-close-modal, .modal-overlay').on('click', function(e) {
            if (e.target === this || $(e.target).closest('#btn-close-modal').length > 0) {
                $('#mode-info-modal').fadeOut(200);
            }
        });

        // HUD zooming Buttons
        $('#btn-zoom-in').on('click', function() {
            zoom = Math.min(maxZoom, zoom + 0.1);
            applyTransform();
        });

        $('#btn-zoom-out').on('click', function() {
            zoom = Math.max(minZoom, zoom - 0.1);
            applyTransform();
        });

        $('#btn-zoom-reset').on('click', function() {
            zoom = 1.0;
            panX = 100;
            panY = 100;
            applyTransform();
        });

        // Logs panel toggles
        $('#logs-header').on('click', function(e) {
            if ($(e.target).closest('.footer-btn').length > 0) return;
            toggleLogsPanel();
        });

        $('#btn-toggle-logs').on('click', function() {
            toggleLogsPanel();
        });

        $('#btn-clear-logs').on('click', function() {
            $.ajax({
                url: '/api/clear_logs',
                method: 'POST',
                success: function() {
                    $('#log-list').empty();
                    $('#log-count').text('0');
                    lastLogHash = "";
                }
            });
        });

        // Inline input change handler (updating defaults)
        $(document).on('change', '.port-inline-input', function() {
            let val = $(this).val();
            let nodeId = $(this).attr('data-node');
            let inputIdx = $(this).attr('data-index');

            $.ajax({
                url: '/api/update_input',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    node_id: nodeId,
                    input_index: inputIdx,
                    val: val
                }),
                success: function() {
                    loadFlow();
                }
            });
        });

        // Loop toggle checkbox handler
        $(document).on('change', '.loop-toggle', function() {
            let nodeId = $(this).attr('data-node');
            let enabled = $(this).is(':checked');
            let interval = parseFloat($(`.loop-interval[data-node="${nodeId}"]`).val()) || 1.0;

            $.ajax({
                url: '/api/update_loop',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    node_id: nodeId,
                    enabled: enabled,
                    interval: interval
                }),
                success: function() {
                    loadFlow();
                    addLog(`Toggled repeat loop for Node ${nodeId}: ${enabled ? 'Enabled (' + interval + 's)' : 'Disabled'}`);
                }
            });
        });

        // Loop interval text input change handler
        $(document).on('change', '.loop-interval', function() {
            let nodeId = $(this).attr('data-node');
            let enabled = $(`.loop-toggle[data-node="${nodeId}"]`).is(':checked');
            let interval = parseFloat($(this).val()) || 1.0;

            $.ajax({
                url: '/api/update_loop',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    node_id: nodeId,
                    enabled: enabled,
                    interval: interval
                }),
                success: function() {
                    loadFlow();
                }
            });
        });

        // Delete node button handler
        $(document).on('click', '.delete-btn', function() {
            let card = $(this).closest('.node-card');
            let nodeId = card.attr('data-id');
            
            $.ajax({
                url: '/api/delete_node',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ node_id: nodeId }),
                success: function() {
                    card.remove();
                    loadFlow();
                }
            });
        });

        // Double click to trigger Execution/Trigger Node
        $(document).on('dblclick', '.node-card[data-category="Exec"]', function() {
            let nodeId = $(this).attr('data-id');
            $.ajax({
                url: '/api/trigger_node',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ node_id: nodeId }),
                success: function() {
                    loadFlow();
                    addLog(`Double-clicked Exec node ${nodeId} to trigger execution path`);
                }
            });
        });

        // Force-trigger toggle checkbox handler
        $(document).on('change', '.force-trigger-toggle', function() {
            let nodeId = $(this).attr('data-node');
            let enabled = $(this).is(':checked');

            $.ajax({
                url: '/api/update_force_trigger',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    node_id: nodeId,
                    enabled: enabled
                }),
                success: function() {
                    loadFlow();
                    addLog(`Toggled force-trigger for Node ${nodeId}: ${enabled ? 'Enabled' : 'Disabled'}`);
                }
            });
        });

        // Trigger action button click event handler for ExecuteButtonNode
        $(document).on('click', '.btn-trigger-action', function(e) {
            e.stopPropagation();
            let nodeId = $(this).attr('data-node');
            $.ajax({
                url: '/api/trigger_node',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ node_id: nodeId }),
                success: function() {
                    loadFlow();
                    addLog(`Triggered Execute Button node ${nodeId}`);
                }
            });
        });

        // Right click wire to delete connection
        $(document).on('contextmenu', '.wire-path', function(e) {
            e.preventDefault();
            let wire = $(this);
            let pNodeId = wire.attr('data-parent-node');
            let oIndex = wire.attr('data-parent-port');
            let cNodeId = wire.attr('data-dest-node');
            let iIndex = wire.attr('data-dest-port');

            if (wire.hasClass('virtual-trigger')) {
                if (confirm('Delete this virtual trigger link?')) {
                    $.ajax({
                        url: '/api/set_button_target',
                        method: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify({
                            button_node_id: pNodeId,
                            target_node_id: null
                        }),
                        success: function() {
                            wire.remove();
                            loadFlow();
                        }
                    });
                }
                return;
            }

            if (confirm('Delete this connection?')) {
                $.ajax({
                    url: '/api/disconnect',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        parent_node_id: pNodeId,
                        output_index: oIndex,
                        connected_node_id: cNodeId,
                        input_index: iIndex
                    }),
                    success: function() {
                        wire.remove();
                        loadFlow();
                    }
                });
            }
        });

        // Ports connection drawing mouse handlers
        $(document).on('mousedown', '.port-handle', function(e) {
            e.stopPropagation();
            isUserInteracting = true;
            let handle = $(this);
            let nodeId = handle.attr('data-node');
            let portIndex = handle.attr('data-index');
            let direction = handle.attr('data-direction');
            let portType = handle.attr('data-type');

            let canvasOffset = $('#canvas-content').offset();
            let handleOffset = handle.offset();

            let x = (handleOffset.left - canvasOffset.left) / zoom + handle.outerWidth() / 2;
            let y = (handleOffset.top - canvasOffset.top) / zoom + handle.outerHeight() / 2;

            drawingConnection = { nodeId, portIndex, direction, type: portType, x, y };

            // Setup temporary active wire path
            activeWire = $('#active-wire');
            activeWire.attr('class', `wire-path drawing ${portType === 'exec' ? 'exec' : ''}`);
            activeWire.show();

            $(document).on('mousemove.wire', function(ev) {
                let curX = (ev.clientX - canvasOffset.left) / zoom;
                let curY = (ev.clientY - canvasOffset.top) / zoom;

                let d = '';
                if (direction === 'output') {
                    let dx = Math.abs(curX - x) * 0.5;
                    d = `M ${x} ${y} C ${x + dx} ${y}, ${curX - dx} ${curY}, ${curX} ${curY}`;
                } else {
                    let dx = Math.abs(x - curX) * 0.5;
                    d = `M ${curX} ${curY} C ${curX + dx} ${curY}, ${x - dx} ${y}, ${x} ${y}`;
                }
                activeWire.attr('d', d);
            });

            $(document).on('mouseup.wire', function(ev) {
                $(document).off('.wire');
                activeWire.hide();
                isUserInteracting = false;

                // Find element under cursor
                let target = $(document.elementFromPoint(ev.clientX, ev.clientY));
                let destHandle = target.closest('.port-handle');

                if (destHandle.length > 0) {
                    let destNodeId = destHandle.attr('data-node');
                    let destPortIndex = destHandle.attr('data-index');
                    let destDirection = destHandle.attr('data-direction');
                    let destPortType = destHandle.attr('data-type');

                    // Validation:
                    // 1. Output must connect to Input
                    // 2. Cannot connect to itself
                    // 3. Types must match (data to data, exec to exec)
                    if (direction !== destDirection && 
                        nodeId !== destNodeId && 
                        portType === destPortType) {
                        
                        let parentId = direction === 'output' ? nodeId : destNodeId;
                        let outIdx = direction === 'output' ? portIndex : destPortIndex;
                        let destId = direction === 'input' ? nodeId : destNodeId;
                        let inpIdx = direction === 'input' ? portIndex : destPortIndex;

                        $.ajax({
                            url: '/api/connect',
                            method: 'POST',
                            contentType: 'application/json',
                            data: JSON.stringify({
                                parent_node_id: parentId,
                                output_index: outIdx,
                                connected_node_id: destId,
                                input_index: inpIdx
                            }),
                            success: function() {
                                loadFlow();
                            },
                            error: function(err) {
                                alert('Invalid Connection: ' + (err.responseJSON ? err.responseJSON.message : 'Unknown'));
                            }
                        });
                    }
                } else {
                    // Check if starting from an Execute Button's port/handle and released on a node card
                    let sourceCard = $(`.node-card[data-id="${nodeId}"]`);
                    let isExecuteButton = sourceCard.find('.node-title').text() === 'Execute Button';
                    if (isExecuteButton) {
                        let targetCard = target.closest('.node-card');
                        if (targetCard.length > 0 && targetCard.attr('data-id') !== nodeId) {
                            $.ajax({
                                url: '/api/set_button_target',
                                method: 'POST',
                                contentType: 'application/json',
                                data: JSON.stringify({
                                    button_node_id: nodeId,
                                    target_node_id: targetCard.attr('data-id')
                                }),
                                success: function() {
                                    loadFlow();
                                    addLog(`Linked Execute Button ${nodeId} to Node ${targetCard.attr('data-id')}`);
                                }
                            });
                        }
                    }
                }
                drawingConnection = null;
            });
        });

        // Search Bar filter
        $('#node-search').on('input', function() {
            let query = $(this).val().toLowerCase();
            
            $('.node-item').each(function() {
                let name = $(this).text().toLowerCase();
                if (name.includes(query)) {
                    $(this).show();
                } else {
                    $(this).hide();
                }
            });

            // Hide empty categories
            $('.node-category').each(function() {
                let visibleItems = $(this).find('.node-item:visible').length;
                if (visibleItems === 0) {
                    $(this).hide();
                } else {
                    $(this).show();
                }
            });
        });
    }

    // Toggle Collapsible Logs Panel
    function toggleLogsPanel() {
        let panel = $('#logs-panel');
        let icon = $('#logs-toggle-icon');
        if (panel.hasClass('closed')) {
            panel.removeClass('closed').addClass('open');
            icon.text('keyboard_arrow_down');
        } else {
            panel.removeClass('open').addClass('closed');
            icon.text('keyboard_arrow_up');
        }
    }

    // Load logs list from server
    let lastLogHash = "";
    function loadLogs() {
        $.getJSON('/api/logs', function(logs) {
            if (logs.length === 0) {
                if (lastLogHash !== "") {
                    $('#log-list').empty();
                    $('#log-count').text('0');
                    lastLogHash = "";
                }
                return;
            }
            let latestLog = logs[logs.length - 1];
            let currentHash = latestLog.time + "_" + latestLog.msg + "_" + logs.length;
            if (currentHash === lastLogHash) return;
            lastLogHash = currentHash;
            
            let logList = $('#log-list');
            logList.empty();
            
            logs.forEach(log => {
                let isStudio = log.msg.startsWith('[Studio UI]:');
                let entry = $(`
                    <div class="log-entry">
                        <span class="log-time">[${log.time}]</span>
                        <span class="log-msg" ${isStudio ? 'style="color: #6366f1;"' : ''}>${log.msg}</span>
                    </div>
                `);
                logList.append(entry);
            });

            $('#log-count').text(logs.length);
            
            // Scroll to bottom
            let footerBody = $('.footer-body');
            footerBody.scrollTop(footerBody[0].scrollHeight);
        });
    }

    // Add local JS debug message
    function addLog(msg) {
        let fullMsg = `[Studio UI]: ${msg}`;
        $.ajax({
            url: '/api/add_log',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ msg: fullMsg }),
            success: function() {
                loadLogs();
            }
        });
    }

    // Adaptive polling timeout scheduler
    function scheduleNextPoll(delay) {
        clearTimeout(pollTimeout);
        pollTimeout = setTimeout(pollFlowUpdates, delay);
    }

    // Wrap the pollFlowUpdates call to support adaptive delay based on active loops
    let originalPollFlowUpdates = pollFlowUpdates;
    pollFlowUpdates = function() {
        if (isUserInteracting || isPanning || drawingConnection || $('.port-inline-input:focus').length > 0) {
            scheduleNextPoll(1000); // retry later
            return;
        }
        
        $.getJSON('/api/flow', function(flowData) {
            updateFlowValues(flowData);
            updatePauseButtonState(flowData.execution_paused);
            let activeLoops = flowData.nodes.filter(n => n.loop_enabled).length;
            let nextDelay = activeLoops > 0 ? 100 : 1000;
            scheduleNextPoll(nextDelay);
        }).fail(function() {
            scheduleNextPoll(2000); // backoff on connection error
        });
    };

    // Run app init
    init();
});
