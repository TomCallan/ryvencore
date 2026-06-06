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
    let currentFlowName = 'flow_project';
    let viewUpdatesPaused = false;

    // Resize observer to watch node-card sizes, update port offsets and refresh wires
    const nodeResizeObserver = new ResizeObserver(entries => {
        entries.forEach(entry => {
            let nodeEl = $(entry.target);
            cacheLocalPortOffsets(nodeEl);
        });
        refreshWires();
    });

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
        if (['Add', 'Subtract', 'Multiply', 'Divide', 'Array Calculator'].includes(title)) return 'Math';
        if (['Number', 'String', 'Concat', 'Uppercase', 'CSV Parser'].includes(title)) return 'String';
        if (['Compare', 'If/Else', 'Python REPL', 'Python Script'].includes(title)) return 'Logic';
        if (['Random', 'Log', 'Plot', 'Execution Timer', 'Lazy File Reader'].includes(title)) return 'Utility';
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
                    let tagsHtml = (tpl.tags || []).map(t => `<span class="node-tag" data-tag="${t}">${t}</span>`).join('');
                    libraryHtml += `
                        <div class="node-item" draggable="true" data-identifier="${tpl.identifier}" data-category="${cat}">
                            <div class="node-item-main">
                                <span>${tpl.title}</span>
                                <span class="material-icons-round add-icon" title="Add to canvas">add</span>
                            </div>
                            <div class="node-item-tags">
                                ${tagsHtml}
                            </div>
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

            // Enable/disable compiled option in selector
            let optionCompiled = $('#alg-mode-select option[value="compiled"]');
            if (flowData.compiled_exists) {
                optionCompiled.prop('disabled', false).show();
            } else {
                optionCompiled.prop('disabled', true).hide();
                if (flowData.algorithm_mode === 'compiled') {
                    // Fall back to data flow if compiled mode selected but no compiled file exists
                    $.ajax({
                        url: '/api/set_alg_mode',
                        method: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify({ mode: 'data' }),
                        success: function() {
                            loadFlow();
                            addLog('[Warning]: Compiled file not found. Reverted to Data Flow mode.');
                        }
                    });
                    return;
                }
            }

            // Show/hide recompile warning badge
            if (flowData.compiled_exists && flowData.compiled_dirty) {
                if ($('#recompile-badge').is(':hidden')) {
                    $('#recompile-badge').fadeIn(200);
                    if (flowData.algorithm_mode === 'compiled') {
                        addLog('[Warning]: Flow modified since compilation. Recompilation is required to run.');
                    }
                }
            } else {
                $('#recompile-badge').fadeOut(200);
            }

            // Customize UI based on Compiled mode
            if (flowData.algorithm_mode === 'compiled') {
                $('#compiled-badge').fadeIn(200);
                $('#btn-run')
                    .html('<span class="material-icons-round">play_arrow</span> Run Compiled')
                    .css({
                        'background': 'linear-gradient(135deg, #ab47bc, #7b1fa2)',
                        'border': 'none',
                        'box-shadow': '0 0 10px rgba(171, 71, 188, 0.4)'
                    })
                    .attr('title', 'Execute compiled in-process flow logic');
                
                let select = $('#compiled-file-select');
                select.empty();
                if (flowData.compiled_files && flowData.compiled_files.length > 0) {
                    flowData.compiled_files.forEach(function(f) {
                        select.append($('<option></option>').val(f).text(f));
                    });
                    if (flowData.active_compiled_file) {
                        select.val(flowData.active_compiled_file);
                    }
                }
                $('#compiled-file-group').fadeIn(200);
            } else {
                $('#compiled-badge').fadeOut(200);
                $('#btn-run')
                    .html('<span class="material-icons-round">play_arrow</span> Run Flow')
                    .css({
                        'background': '',
                        'border': '',
                        'box-shadow': ''
                    })
                    .attr('title', 'Trigger execution update');
                $('#compiled-file-group').fadeOut(200);
            }

            // Sync pause button
            updatePauseButtonState(flowData.execution_paused);

            // Render Nodes
            renderNodes(flowData.nodes);

            // Sync all input, output values and option visibilities
            updateFlowValues(flowData);

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

    // Helper to compute port coords using getBoundingClientRect (zoom-aware)
    function computePortLocalCoords(handle) {
        let el = handle[0];
        let nodeCard = handle.closest('.node-card');
        if (nodeCard.length === 0) return { x: 0, y: 0 };
        
        let cardRect = nodeCard[0].getBoundingClientRect();
        let handleRect = el.getBoundingClientRect();
        
        if (cardRect.width === 0 || cardRect.height === 0) {
            return { x: 0, y: 0 };
        }
        
        let x = (handleRect.left + handleRect.width / 2 - cardRect.left) / zoom;
        let y = (handleRect.top + handleRect.height / 2 - cardRect.top) / zoom;
        return { x: x, y: y };
    }

    // Cache port offset coordinates relative to node card top-left
    function cacheLocalPortOffsets(nodeCardEl) {
        nodeCardEl.find('.port-handle').each(function() {
            let coords = computePortLocalCoords($(this));
            if (coords.x > 0 || coords.y > 0) {
                this.setAttribute('data-local-x', coords.x);
                this.setAttribute('data-local-y', coords.y);
            }
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
                nodeResizeObserver.unobserve(this);
                $(this).remove();
            }
        });

        // Add or Update Node Cards
        nodes.forEach(n => {
            let cat = getNodeCategory(n.title);
            let nodeEl = $(`.node-card[data-id="${n.id}"]`);

            // If node doesn't exist, create it
            if (nodeEl.length === 0) {
                let repOpt = n.repeat_option_visible || false;
                let timerOpt = n.timer_option_visible || false;
                let forceOpt = n.force_trigger_visible || false;
                let waitOpt = n.wait_complete_visible || false;
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
                        <div class="node-timer-wrapper" style="display: ${ (repOpt || timerOpt || forceOpt || waitOpt) ? 'block' : 'none' }; padding: 6px 10px; border-top: 1px solid rgba(255,255,255,0.05); background: rgba(0,0,0,0.15);">
                            <div class="timer-row" style="display: ${ (repOpt || timerOpt) ? 'flex' : 'none' }; align-items: center; justify-content: space-between; gap: 4px;">
                                <label class="timer-toggle-label" style="display: ${ repOpt ? 'flex' : 'none' }; align-items: center; gap: 2px; cursor: pointer; user-select: none; font-size: 0.65rem; color: var(--text-secondary);">
                                    <input type="checkbox" class="loop-toggle" data-node="${n.id}">
                                    <span class="material-icons-round timer-icon" style="font-size: 14px;">schedule</span>
                                    <span class="timer-text">Repeat</span>
                                </label>
                                <div class="timer-interval-wrapper" style="display: ${ timerOpt ? 'flex' : 'none' }; align-items: center; gap: 2px;">
                                    <input type="number" class="loop-interval" data-node="${n.id}" min="0.1" step="0.1" value="1.0" style="width: 45px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: #fff; font-size: 0.65rem; border-radius: 3px; padding: 1px 3px; text-align: center;">
                                    <span class="timer-unit" style="font-size: 0.6rem; color: var(--text-muted);">s</span>
                                </div>
                            </div>
                            <div class="extra-options-row" style="display: ${ (forceOpt || waitOpt) ? 'flex' : 'none' }; margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.03); padding-top: 4px; align-items: center; justify-content: space-between; gap: 4px;">
                                 <label class="force-trigger-label" style="display: ${ forceOpt ? 'flex' : 'none' }; align-items: center; gap: 2px; cursor: pointer; user-select: none; font-size: 0.65rem; color: var(--text-secondary);" title="Block automatic propagation to downstream nodes">
                                     <input type="checkbox" class="force-trigger-toggle" data-node="${n.id}">
                                     <span>Force Trigger</span>
                                 </label>
                                 <label class="wait-complete-label" style="display: ${ waitOpt ? 'flex' : 'none' }; align-items: center; gap: 2px; cursor: pointer; user-select: none; font-size: 0.65rem; color: var(--text-secondary);" title="Skip execution if previous update is still running">
                                     <input type="checkbox" class="wait-complete-toggle" data-node="${n.id}">
                                     <span>Wait Complete</span>
                                 </label>
                             </div>
                        </div>
                        <div class="node-resize-handle"></div>
                    </div>
                `);
                nodesLayer.append(nodeEl);
                setupNodeDragging(nodeEl);
                setupNodeResizing(nodeEl);
                nodeResizeObserver.observe(nodeEl[0]);
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
            } else if (n.title === 'Python REPL') {
                if (nodeEl.find('.node-custom-content').length === 0) {
                    nodeEl.find('.node-ports').after(`
                        <div class="node-custom-content" style="padding: 0 14px 10px 14px; display: flex; flex-direction: column; gap: 4px;">
                            <label style="font-size: 0.75rem; color: var(--text-secondary);">Python Code:</label>
                            <textarea class="repl-code-input" data-node="${n.id}" style="width: 100%; height: 80px; font-family: monospace; font-size: 0.75rem; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color: #fff; resize: vertical; padding: 4px; border-radius: 4px;"></textarea>
                        </div>
                    `);
                    
                    let textarea = nodeEl.find('.repl-code-input');
                    textarea.val(n.code || '');
                    
                    // Prevent node dragging when interacting with textarea
                    textarea.on('mousedown selectstart', function(e) {
                        e.stopPropagation();
                    });
                    
                    // Update on blur or change
                    textarea.on('change', function() {
                        let codeVal = $(this).val();
                        $.ajax({
                            url: '/api/update_node_property',
                            type: 'POST',
                            contentType: 'application/json',
                            data: JSON.stringify({
                                node_id: n.id,
                                name: 'code',
                                val: codeVal
                            }),
                            success: function(response) {
                                if (response.status === 'success') {
                                    // Optional: loadFlow();
                                }
                            }
                        });
                    });
                } else {
                    let textarea = nodeEl.find('.repl-code-input');
                    if (!textarea.is(':focus')) {
                        textarea.val(n.code || '');
                    }
                }
            } else if (n.title === 'Python Script') {
                if (nodeEl.find('.node-custom-content').length === 0) {
                    nodeEl.find('.node-ports').after(`
                        <div class="node-custom-content" style="padding: 0 14px 10px 14px; display: flex; flex-direction: column; gap: 4px;">
                            <label style="font-size: 0.75rem; color: var(--text-secondary);">Script Path:</label>
                            <input type="text" class="script-path-input" data-node="${n.id}" placeholder="e.g. example_script.py" style="width: 100%; font-family: monospace; font-size: 0.75rem; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color: #fff; padding: 4px; border-radius: 4px;">
                        </div>
                    `);
                    
                    let input = nodeEl.find('.script-path-input');
                    input.val(n.script_path || '');
                    
                    // Prevent node dragging when interacting with input
                    input.on('mousedown selectstart', function(e) {
                        e.stopPropagation();
                    });
                    
                    // Update on blur or change
                    input.on('change', function() {
                        let pathVal = $(this).val();
                        $.ajax({
                            url: '/api/update_node_property',
                            type: 'POST',
                            contentType: 'application/json',
                            data: JSON.stringify({
                                node_id: n.id,
                                name: 'script_path',
                                val: pathVal
                            }),
                            success: function(response) {
                                if (response.status === 'success') {
                                    loadFlow();
                                }
                            }
                        });
                    });
                } else {
                    let input = nodeEl.find('.script-path-input');
                    if (!input.is(':focus')) {
                        input.val(n.script_path || '');
                    }
                }
            } else if (n.title === 'Plot') {
                if (nodeEl.find('.node-custom-content').length === 0) {
                    nodeEl.find('.node-ports').after(`
                        <div class="node-custom-content" style="padding: 0 14px 10px 14px; display: flex; flex-direction: column; gap: 4px; align-items: center; width: 100%;">
                            <svg class="plot-svg" width="100%" height="80" style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.05); border-radius: 4px;"></svg>
                        </div>
                    `);
                }
                
                let svg = nodeEl.find('.plot-svg');
                let buffer = n.buffer || [];
                svg.empty();
                if (buffer.length > 1) {
                    let minVal = Math.min(...buffer);
                    let maxVal = Math.max(...buffer);
                    let range = maxVal - minVal;
                    if (range === 0) range = 1.0;
                    
                    let svgWidth = svg.width() || 192;
                    let svgHeight = 80;
                    let points = [];
                    
                    for (let idx = 0; idx < buffer.length; idx++) {
                        let val = buffer[idx];
                        let x = (idx / (buffer.length - 1)) * svgWidth;
                        let y = svgHeight - 8 - ((val - minVal) / range) * (svgHeight - 16);
                        points.push(`${x},${y}`);
                    }
                    
                    let polyline = $(document.createElementNS("http://www.w3.org/2000/svg", "polyline"))
                        .attr('points', points.join(' '))
                        .attr('style', 'fill:none;stroke:var(--primary);stroke-width:2');
                    svg.append(polyline);
                }
            } else if (n.title === 'Advanced Plot' || n.title === 'Orderbook Plot') {
                if (nodeEl.find('.node-custom-content').length === 0) {
                    nodeEl.find('.node-ports').after(`
                        <div class="node-custom-content" style="padding: 0 10px 10px 10px; display: flex; flex-direction: column; gap: 4px; align-items: center; width: 100%; height: 160px; box-sizing: border-box;">
                            <div class="custom-svg-container" style="width: 100%; height: 100%; border: 1px solid rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden; background: rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;"></div>
                        </div>
                    `);
                }
                let container = nodeEl.find('.custom-svg-container');
                if (n.svg_content) {
                    container.html(n.svg_content);
                } else {
                    container.html('<div style="color: var(--text-muted); font-size: 0.65rem; display: flex; align-items: center; justify-content: center; height: 100%;">No data plotted yet</div>');
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

            let defaultWidth = 200;
            let defaultHeight = 120;
            if (n.title === 'Plot') {
                defaultWidth = 220;
                defaultHeight = 180;
            } else if (n.title === 'Advanced Plot' || n.title === 'Orderbook Plot') {
                defaultWidth = 250;
                defaultHeight = 220;
            } else if (n.title === 'Array Calculator') {
                defaultWidth = 220;
                defaultHeight = 140;
            }
            let currentWidth = n.width || defaultWidth;
            let currentHeight = n.height || defaultHeight;
            nodeEl.attr('data-width', currentWidth).attr('data-height', currentHeight);

            nodeEl.css('width', `${currentWidth}px`);
            nodeEl.css('min-height', `${currentHeight}px`);

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
                    
                    if (n.title === 'Python REPL') {
                        let labelEl = $(`<input type="text" class="port-label-input" data-node="${n.id}" data-index="${i}" data-direction="input" value="${inp.label}" style="width: 60px; background: transparent; border: none; border-bottom: 1px dashed rgba(255,255,255,0.3); color: #fff; font-size: 0.75rem; padding: 2px; outline: none; margin-right: 4px;">`);
                        let deleteBtn = $(`<span class="material-icons-round delete-port-btn" data-node="${n.id}" data-index="${i}" data-direction="input" style="font-size: 12px; color: var(--text-muted); cursor: pointer; margin-right: 4px;" title="Delete input">close</span>`);
                        inpCol.append(deleteBtn).append(labelEl);
                    } else {
                        inpCol.append(`<span class="port-label">${inp.label}</span>`);
                    }
                    
                    // Render input widget if NOT connected and type is data
                    if (!isExec) {
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
                    
                    if (!isExec && out.val !== null) {
                        outCol.append(`<span class="port-value-display" title="${out.val}">${out.val}</span>`);
                    }

                    if (n.title === 'Python REPL') {
                        let labelEl = $(`<input type="text" class="port-label-input" data-node="${n.id}" data-index="${i}" data-direction="output" value="${out.label}" style="width: 60px; background: transparent; border: none; border-bottom: 1px dashed rgba(255,255,255,0.3); color: #fff; font-size: 0.75rem; padding: 2px; outline: none; text-align: right; margin-left: 4px;">`);
                        let deleteBtn = $(`<span class="material-icons-round delete-port-btn" data-node="${n.id}" data-index="${i}" data-direction="output" style="font-size: 12px; color: var(--text-muted); cursor: pointer; margin-left: 4px;" title="Delete output">close</span>`);
                        outCol.append(labelEl).append(deleteBtn);
                    } else {
                        outCol.append(`<span class="port-label">${out.label}</span>`);
                    }

                    row.append(outCol);
                    row.append(`<div class="port-handle output ${isExec ? 'exec' : ''}" data-node="${n.id}" data-index="${i}" data-direction="output" data-type="${out.type}" title="${out.label} (${out.type})"></div>`);
                }

                portsContainer.append(row);
            }

            // Clear any old add-ports-row first and insert if REPL node
            nodeEl.find('.add-ports-row').remove();
            if (n.title === 'Python REPL') {
                let addPortsRow = $(`
                    <div class="add-ports-row" style="display: flex; justify-content: space-between; padding: 4px 14px; border-top: 1px solid rgba(255,255,255,0.03);">
                        <button class="btn-add-port" data-node="${n.id}" data-direction="input" style="background: none; border: none; color: var(--text-secondary); font-size: 0.7rem; display: flex; align-items: center; gap: 2px; cursor: pointer; padding: 2px 4px; border-radius: 4px;">
                            <span class="material-icons-round" style="font-size: 12px;">add</span> Add Input
                        </button>
                        <button class="btn-add-port" data-node="${n.id}" data-direction="output" style="background: none; border: none; color: var(--text-secondary); font-size: 0.7rem; display: flex; align-items: center; gap: 2px; cursor: pointer; padding: 2px 4px; border-radius: 4px;">
                            <span class="material-icons-round" style="font-size: 12px;">add</span> Add Output
                        </button>
                    </div>
                `);
                portsContainer.after(addPortsRow);
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
            let coords = computePortLocalCoords(handle);
            if (coords.x > 0 || coords.y > 0) {
                handle.attr('data-local-x', coords.x);
                handle.attr('data-local-y', coords.y);
            }
            return coords;
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
        // Click behavior
        $('.node-item').off('click').on('click', function() {
            let identifier = $(this).attr('data-identifier');
            
            // Create at center of viewport
            let viewport = $('#canvas-viewport');
            let x = (viewport.width() / 2 - panX) / zoom;
            let y = (viewport.height() / 2 - panY) / zoom;

            createNode(identifier, x, y);
        });

        // Drag start behavior
        $('.node-item').off('dragstart').on('dragstart', function(e) {
            let identifier = $(this).attr('data-identifier');
            e.originalEvent.dataTransfer.setData('text/plain', identifier);
            e.originalEvent.dataTransfer.effectAllowed = 'copy';
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
        // Skip updates if user is typing
        if ($('.port-inline-input:focus').length > 0 || $('.port-label-input:focus').length > 0) return;
        
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

            // Update wait-complete widget
            let waitCompleteToggle = nodeEl.find('.wait-complete-toggle');
            if (waitCompleteToggle.length > 0 && !waitCompleteToggle.is(':active')) {
                waitCompleteToggle.prop('checked', n.wait_until_complete || false);
            }

            // Toggle visibility of repeat, timer, force trigger, and wait complete options
            let repOpt = n.repeat_option_visible || false;
            let timerOpt = n.timer_option_visible || false;
            let forceOpt = n.force_trigger_visible || false;
            let waitOpt = n.wait_complete_visible || false;

            let timerWrapper = nodeEl.find('.node-timer-wrapper');
            let timerRow = nodeEl.find('.timer-row');
            let timerToggleLabel = nodeEl.find('.timer-toggle-label');
            let timerIntervalWrapper = nodeEl.find('.timer-interval-wrapper');
            let extraOptionsRow = nodeEl.find('.extra-options-row');
            let forceLabel = nodeEl.find('.force-trigger-label');
            let waitLabel = nodeEl.find('.wait-complete-label');

            timerToggleLabel.css('display', repOpt ? 'flex' : 'none');
            timerIntervalWrapper.css('display', timerOpt ? 'flex' : 'none');
            timerRow.css('display', (repOpt || timerOpt) ? 'flex' : 'none');
            
            forceLabel.css('display', forceOpt ? 'flex' : 'none');
            waitLabel.css('display', waitOpt ? 'flex' : 'none');
            extraOptionsRow.css('display', (forceOpt || waitOpt) ? 'flex' : 'none');
            timerWrapper.css('display', (repOpt || timerOpt || forceOpt || waitOpt) ? 'block' : 'none');

            // Update Plot SVG if Plot Node
            if (n.title === 'Plot') {
                let svg = nodeEl.find('.plot-svg');
                if (svg.length > 0) {
                    let buffer = n.buffer || [];
                    svg.empty();
                    if (buffer.length > 1) {
                        let minVal = Math.min(...buffer);
                        let maxVal = Math.max(...buffer);
                        let range = maxVal - minVal;
                        if (range === 0) range = 1.0;
                        
                        let svgWidth = svg.width() || 192;
                        let svgHeight = 80;
                        let points = [];
                        
                        for (let idx = 0; idx < buffer.length; idx++) {
                            let val = buffer[idx];
                            let x = (idx / (buffer.length - 1)) * svgWidth;
                            let y = svgHeight - 8 - ((val - minVal) / range) * (svgHeight - 16);
                            points.push(`${x},${y}`);
                        }
                        
                        let polyline = $(document.createElementNS("http://www.w3.org/2000/svg", "polyline"))
                            .attr('points', points.join(' '))
                            .attr('style', 'fill:none;stroke:var(--primary);stroke-width:2');
                        svg.append(polyline);
                    }
                }
            } else if (n.title === 'Advanced Plot' || n.title === 'Orderbook Plot') {
                let container = nodeEl.find('.custom-svg-container');
                if (container.length > 0) {
                    if (n.svg_content) {
                        container.html(n.svg_content);
                    } else {
                        container.html('<div style="color: var(--text-muted); font-size: 0.65rem; display: flex; align-items: center; justify-content: center; height: 100%;">No data plotted yet</div>');
                    }
                }
            }
        });
    }


    // Setup General Event Handlers
    function setupEventHandlers() {
        let viewport = $('#canvas-viewport');

        // Radial Context Menu & Search Popup Variables & Helpers
        let radialX = 0;
        let radialY = 0;

        function hideRadialMenu() {
            let menu = $('#radial-menu');
            menu.removeClass('active');
            setTimeout(() => {
                if (!menu.hasClass('active')) {
                    menu.hide();
                }
            }, 300);
        }

        function hideRadialSearch() {
            let search = $('#radial-search-popup');
            search.hide();
        }

        function renderRadialSearchResults(query) {
            let container = $('#radial-search-results').empty();
            let filtered = [];
            query = query.toLowerCase().trim();

            Object.keys(nodeTemplates).forEach(id => {
                let tpl = nodeTemplates[id];
                if (!query || tpl.title.toLowerCase().includes(query)) {
                    filtered.push(tpl);
                }
            });

            filtered.forEach((tpl, idx) => {
                let cat = getNodeCategory(tpl.title);
                let item = $(`
                    <div class="radial-search-item ${idx === 0 ? 'selected' : ''}" data-identifier="${tpl.identifier}">
                        <span class="item-title">${tpl.title}</span>
                        <span class="item-category">${cat}</span>
                    </div>
                `);
                container.append(item);
            });

            if (filtered.length === 0) {
                container.append(`<div style="font-size:0.7rem; color:var(--text-muted); text-align:center; padding: 8px;">No nodes found</div>`);
            }
        }

        // Right-click viewport to trigger Radial Menu
        viewport.on('contextmenu', function(e) {
            if ($(e.target).closest('.node-card, .port-handle, .wire-path').length > 0) return;
            e.preventDefault();
            
            hideRadialSearch();

            let pageX = e.pageX;
            let pageY = e.pageY;
            
            let offset = viewport.offset();
            let clickX = e.clientX - offset.left;
            let clickY = e.clientY - offset.top;
            radialX = (clickX - panX) / zoom;
            radialY = (clickY - panY) / zoom;

            let menu = $('#radial-menu');
            menu.css({
                left: pageX + 'px',
                top: pageY + 'px',
                display: 'block'
            });
            
            setTimeout(() => {
                menu.addClass('active');
            }, 10);
        });

        let activeNodeRadialId = null;

        function hideNodeRadialMenu() {
            let menu = $('#node-radial-menu');
            menu.removeClass('active');
            setTimeout(() => {
                if (!menu.hasClass('active')) {
                    menu.css('display', 'none');
                }
            }, 200);
        }

        // Right-click node card to trigger Node Radial Menu
        $(document).on('contextmenu', '.node-card', function(e) {
            e.preventDefault();
            e.stopPropagation();

            hideRadialMenu();
            hideRadialSearch();
            hideNodeRadialMenu();

            let nodeId = $(this).attr('data-id');
            activeNodeRadialId = nodeId;

            // Check visibility states to change action text
            let nodeEl = $(`.node-card[data-id="${nodeId}"]`);
            let hasRepeat = nodeEl.find('.timer-toggle-label').css('display') !== 'none';
            let hasTimer = nodeEl.find('.timer-interval-wrapper').css('display') !== 'none';
            let hasForce = nodeEl.find('.force-trigger-label').css('display') !== 'none';
            let hasWait = nodeEl.find('.wait-complete-label').css('display') !== 'none';

            $('#node-radial-repeat-label').text(hasRepeat ? 'Remove Repeat' : 'Add Repeat');
            $('#node-radial-timer-label').text(hasTimer ? 'Remove Timer' : 'Add Timer');
            $('#node-radial-force-label').text(hasForce ? 'Remove Force' : 'Add Force');
            $('#node-radial-wait-label').text(hasWait ? 'Remove Wait' : 'Add Wait Complete');

            let pageX = e.pageX;
            let pageY = e.pageY;

            let menu = $('#node-radial-menu');
            menu.css({
                left: pageX + 'px',
                top: pageY + 'px',
                display: 'block'
            });
            
            setTimeout(() => {
                menu.addClass('active');
            }, 10);
        });

        // Hide menus on click anywhere outside
        $(document).on('mousedown', function(e) {
            if ($(e.target).closest('#radial-menu, #radial-search-popup, #node-radial-menu').length === 0) {
                hideRadialMenu();
                hideRadialSearch();
                hideNodeRadialMenu();
            }
        });

        // Click on node radial menu item
        $(document).on('click', '#node-radial-menu .radial-menu-item', function(e) {
            e.stopPropagation();
            let action = $(this).attr('data-action');
            hideNodeRadialMenu();

            if (!activeNodeRadialId) return;

            let nodeId = activeNodeRadialId;
            let nodeEl = $(`.node-card[data-id="${nodeId}"]`);

            if (action === 'toggle-repeat') {
                let hasRepeat = nodeEl.find('.timer-toggle-label').css('display') !== 'none';
                let nextVal = !hasRepeat;
                
                if (!nextVal) {
                    $.ajax({
                        url: '/api/update_node_property',
                        method: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify({ node_id: nodeId, name: 'loop_enabled', val: false })
                    });
                }
                
                $.ajax({
                    url: '/api/update_node_property',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ node_id: nodeId, name: 'repeat_option_visible', val: nextVal }),
                    success: function() {
                        loadFlow();
                        addLog(`Repeat option ${nextVal ? 'added to' : 'removed from'} Node ${nodeId}`);
                    }
                });
            } else if (action === 'toggle-timer') {
                let hasTimer = nodeEl.find('.timer-interval-wrapper').css('display') !== 'none';
                let nextVal = !hasTimer;
                
                $.ajax({
                    url: '/api/update_node_property',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ node_id: nodeId, name: 'timer_option_visible', val: nextVal }),
                    success: function() {
                        loadFlow();
                        addLog(`Timer option ${nextVal ? 'added to' : 'removed from'} Node ${nodeId}`);
                    }
                });
            } else if (action === 'toggle-force') {
                let hasForce = nodeEl.find('.force-trigger-label').css('display') !== 'none';
                let nextVal = !hasForce;
                
                if (!nextVal) {
                    $.ajax({
                        url: '/api/update_node_property',
                        method: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify({ node_id: nodeId, name: 'force_trigger', val: false })
                    });
                }

                $.ajax({
                    url: '/api/update_node_property',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ node_id: nodeId, name: 'force_trigger_visible', val: nextVal }),
                    success: function() {
                        loadFlow();
                        addLog(`Force Trigger option ${nextVal ? 'added to' : 'removed from'} Node ${nodeId}`);
                    }
                });
            } else if (action === 'toggle-wait') {
                let hasWait = nodeEl.find('.wait-complete-label').css('display') !== 'none';
                let nextVal = !hasWait;
                
                if (!nextVal) {
                    $.ajax({
                        url: '/api/update_node_property',
                        method: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify({ node_id: nodeId, name: 'wait_until_complete', val: false })
                    });
                }

                $.ajax({
                    url: '/api/update_node_property',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ node_id: nodeId, name: 'wait_complete_visible', val: nextVal }),
                    success: function() {
                        loadFlow();
                        addLog(`Wait Complete option ${nextVal ? 'added to' : 'removed from'} Node ${nodeId}`);
                    }
                });
            }
        });

        // Click on radial menu item
        $(document).on('click', '.radial-menu-item', function(e) {
            e.stopPropagation();
            let action = $(this).attr('data-action');
            if (action.startsWith('toggle-')) return; // handled by node radial click
            hideRadialMenu();

            if (action === 'add-node') {
                let menu = $('#radial-menu');
                let left = menu.css('left');
                let top = menu.css('top');
                
                let search = $('#radial-search-popup');
                search.css({
                    left: left,
                    top: top,
                    display: 'flex'
                });
                
                let input = $('#radial-search-input');
                input.val('').focus();
                renderRadialSearchResults('');
            } else if (action === 'save') {
                $('#btn-save').click();
            } else if (action === 'load') {
                $('#btn-load').click();
            } else if (action === 'clear') {
                $('#btn-clear').click();
            } else if (action === 'pause') {
                $('#btn-pause').click();
            }
        });

        // Radial Search input events
        $(document).on('input', '#radial-search-input', function() {
            let query = $(this).val();
            renderRadialSearchResults(query);
        });

        $(document).on('click', '.radial-search-item', function(e) {
            e.stopPropagation();
            let identifier = $(this).attr('data-identifier');
            createNode(identifier, radialX, radialY);
            hideRadialSearch();
        });

        $(document).on('mousedown keydown keyup', '#radial-search-input', function(e) {
            e.stopPropagation();
        });

        $(document).on('keydown', '#radial-search-input', function(e) {
            if (e.key === 'Enter') {
                let selected = $('#radial-search-results .radial-search-item.selected');
                if (selected.length > 0) {
                    let identifier = selected.attr('data-identifier');
                    createNode(identifier, radialX, radialY);
                    hideRadialSearch();
                }
            } else if (e.key === 'Escape') {
                hideRadialSearch();
            } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                let items = $('#radial-search-results .radial-search-item');
                if (items.length > 0) {
                    let current = items.filter('.selected');
                    let nextIdx = 0;
                    if (current.length > 0) {
                        let idx = items.index(current);
                        nextIdx = e.key === 'ArrowDown' ? (idx + 1) % items.length : (idx - 1 + items.length) % items.length;
                        current.removeClass('selected');
                    }
                    items.eq(nextIdx).addClass('selected');
                    items.eq(nextIdx)[0].scrollIntoView({ block: 'nearest' });
                    e.preventDefault();
                }
            }
        });

        // Setup Drag and Drop onto Canvas
        viewport.on('dragover', function(e) {
            e.preventDefault();
            e.originalEvent.dataTransfer.dropEffect = 'copy';
        });

        viewport.on('drop', function(e) {
            e.preventDefault();
            let identifier = e.originalEvent.dataTransfer.getData('text/plain');
            if (identifier) {
                let offset = viewport.offset();
                let dropX = e.originalEvent.clientX - offset.left;
                let dropY = e.originalEvent.clientY - offset.top;
                
                let x = (dropX - panX) / zoom;
                let y = (dropY - panY) / zoom;
                
                createNode(identifier, x, y);
                addLog(`Dropped new node: ${identifier}`);
            }
        });

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

        // Modal close/cancel handler
        $('.modal-cancel').on('click', function() {
            $('.modal-overlay').fadeOut(200);
        });

        $('#btn-save').on('click', function() {
            $('#save-flow-name').val(currentFlowName);
            $('#save-flow-modal').css('display', 'flex').hide().fadeIn(200);
            $('#save-flow-name').focus().select();
        });

        $('#btn-confirm-save').on('click', function() {
            let name = $('#save-flow-name').val().trim();
            if (name) {
                $.ajax({
                    url: '/api/save',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ name: name }),
                    success: function(res) {
                        currentFlowName = res.name;
                        $('#save-flow-modal').fadeOut(200);
                        addLog(`Project saved successfully as "${res.name}"`);
                    },
                    error: function(err) {
                        alert('Failed to save flow: ' + (err.responseJSON ? err.responseJSON.message : 'Unknown'));
                    }
                });
            }
        });

        $('#save-flow-name').on('keypress', function(e) {
            if (e.which === 13) {
                $('#btn-confirm-save').click();
            }
        });

        $('#btn-load').on('click', function() {
            $.getJSON('/api/list_flows', function(res) {
                let flows = res.flows || [];
                let listContainer = $('#load-flow-list').empty();
                
                if (flows.length === 0) {
                    listContainer.html('<div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 20px;">No saved flows found.</div>');
                } else {
                    flows.forEach(f => {
                        let isCurrent = (f === currentFlowName);
                        let itemHtml = `
                            <div class="flow-list-item" data-name="${f}">
                                <div class="flow-item-info">
                                    <span class="material-icons-round flow-item-icon">${isCurrent ? 'stars' : 'article'}</span>
                                    <span class="flow-item-name">${f} ${isCurrent ? '<span style="color: var(--primary); font-size: 0.75rem; font-weight: 600; margin-left: 4px;">(active)</span>' : ''}</span>
                                </div>
                                <button class="flow-item-action">Load</button>
                            </div>
                        `;
                        let item = $(itemHtml);
                        item.on('click', function() {
                            let flowName = $(this).attr('data-name');
                            $.ajax({
                                url: '/api/load',
                                method: 'POST',
                                contentType: 'application/json',
                                data: JSON.stringify({ name: flowName }),
                                success: function(loadRes) {
                                    currentFlowName = loadRes.name;
                                    loadFlow();
                                    $('#load-flow-modal').fadeOut(200);
                                    addLog(`Loaded saved project flow: ${loadRes.name}`);
                                },
                                error: function(err) {
                                    alert('Failed to load flow: ' + (err.responseJSON ? err.responseJSON.message : 'Unknown'));
                                }
                            });
                        });
                        listContainer.append(item);
                    });
                }
                
                $('#load-flow-modal').css('display', 'flex').hide().fadeIn(200);
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

        $('#btn-pause-view').on('click', function() {
            viewUpdatesPaused = !viewUpdatesPaused;
            let btn = $(this);
            if (viewUpdatesPaused) {
                btn.removeClass('btn-secondary').addClass('btn-warning')
                   .html('<span class="material-icons-round">visibility_off</span> Resume View')
                   .attr('title', 'Resume canvas node updates');
                addLog('[Studio UI]: Canvas node view updates paused');
            } else {
                btn.removeClass('btn-warning').addClass('btn-secondary')
                   .html('<span class="material-icons-round">visibility</span> Pause View')
                   .attr('title', 'Pause canvas node updates (background execution continues)');
                addLog('[Studio UI]: Canvas node view updates resumed');
                pollFlowUpdates();
            }
        });

        $('#btn-run').on('click', function() {
            let mode = $('#alg-mode-select').val();
            let recompileBadgeVisible = $('#recompile-badge').is(':visible');
            
            function triggerExecution() {
                $('.node-card').each(function() {
                    let card = $(this);
                    let title = card.find('.node-title').text();
                    let category = card.attr('data-category');
                    if (title === 'Trigger' || ['String', 'Math'].includes(category)) {
                        let id = card.attr('data-id');
                        $.ajax({
                            url: '/api/trigger_node',
                            method: 'POST',
                            contentType: 'application/json',
                            data: JSON.stringify({ node_id: id })
                        });
                    }
                });
                setTimeout(loadFlow, 250);
                addLog('Manually triggered flow execution');
            }

            if (mode === 'compiled' && recompileBadgeVisible) {
                addLog('[Warning]: Flow has modified nodes. Auto-recompiling before running...');
                $.ajax({
                    url: '/api/compile',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({}),
                    success: function(res) {
                        if (res.status === 'success') {
                            addLog('[Studio UI]: Auto-recompilation successful.');
                            triggerExecution();
                        } else {
                            alert('Auto-recompilation failed: ' + res.message);
                        }
                    },
                    error: function(err) {
                        alert('Auto-recompilation request failed: ' + (err.responseJSON ? err.responseJSON.message : 'Unknown'));
                    }
                });
            } else {
                triggerExecution();
            }
        });

        $('#btn-compile').on('click', function() {
            addLog('[Studio UI]: Compiling flow into a standalone Python file...');
            $.ajax({
                url: '/api/compile',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({}),
                success: function(res) {
                    if (res.status === 'success') {
                        loadFlow();
                        addLog('[Studio UI]: Flow successfully compiled on backend: ' + res.filename);
                    } else {
                        alert('Compilation failed: ' + res.message);
                    }
                },
                error: function(err) {
                    alert('Compilation request failed: ' + (err.responseJSON ? err.responseJSON.message : 'Unknown'));
                }
            });
        });

        $('#compiled-file-select').on('change', function() {
            let filename = $(this).val();
            $.ajax({
                url: '/api/set_compiled_file',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ filename }),
                success: function() {
                    loadFlow();
                    addLog(`Switched active compiled file to: ${filename}`);
                }
            });
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
                },
                error: function(err) {
                    let errMsg = err.responseJSON ? err.responseJSON.message : 'Failed to set algorithm mode';
                    alert(errMsg);
                    loadFlow();
                }
            });
        });

        // Info Modal toggle handlers
        $('#btn-mode-info').on('click', function() {
            $('#mode-info-modal').css('display', 'flex').hide().fadeIn(200);
        });

        $(document).on('click', '.modal-overlay', function(e) {
            if (e.target === this || $(e.target).closest('.modal-close').length > 0) {
                $(this).fadeOut(200);
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

            $.ajax({
                url: '/api/update_node_property',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    node_id: nodeId,
                    name: 'loop_enabled',
                    val: enabled
                }),
                success: function() {
                    loadFlow();
                    addLog(`Toggled repeat loop for Node ${nodeId}: ${enabled ? 'Enabled' : 'Disabled'}`);
                }
            });
        });

        // Loop interval text input change handler
        $(document).on('change', '.loop-interval', function() {
            let nodeId = $(this).attr('data-node');
            let interval = parseFloat($(this).val()) || 1.0;

            $.ajax({
                url: '/api/update_node_property',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    node_id: nodeId,
                    name: 'loop_interval',
                    val: interval
                }),
                success: function() {
                    loadFlow();
                }
            });
        });

        // Prevent node dragging/selection issues on label input
        $(document).on('mousedown selectstart', '.port-label-input, .delete-port-btn, .btn-add-port', function(e) {
            e.stopPropagation();
        });

        // Port label rename handler
        $(document).on('change', '.port-label-input', function() {
            let label = $(this).val();
            let nodeId = $(this).attr('data-node');
            let index = $(this).attr('data-index');
            let direction = $(this).attr('data-direction');

            $.ajax({
                url: '/api/rename_port',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    node_id: nodeId,
                    direction: direction,
                    index: index,
                    label: label
                }),
                success: function() {
                    loadFlow();
                }
            });
        });

        // Delete port button handler
        $(document).on('click', '.delete-port-btn', function(e) {
            e.stopPropagation();
            let nodeId = $(this).attr('data-node');
            let index = $(this).attr('data-index');
            let direction = $(this).attr('data-direction');

            $.ajax({
                url: '/api/delete_port',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    node_id: nodeId,
                    direction: direction,
                    index: index
                }),
                success: function() {
                    loadFlow();
                }
            });
        });

        // Add port button handler
        $(document).on('click', '.btn-add-port', function(e) {
            e.stopPropagation();
            let nodeId = $(this).attr('data-node');
            let direction = $(this).attr('data-direction');

            $.ajax({
                url: '/api/add_port',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    node_id: nodeId,
                    direction: direction
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
                url: '/api/update_node_property',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    node_id: nodeId,
                    name: 'force_trigger',
                    val: enabled
                }),
                success: function() {
                    loadFlow();
                    addLog(`Toggled force-trigger for Node ${nodeId}: ${enabled ? 'Enabled' : 'Disabled'}`);
                }
            });
        });

        // Wait-complete toggle checkbox handler
        $(document).on('change', '.wait-complete-toggle', function() {
            let nodeId = $(this).attr('data-node');
            let enabled = $(this).is(':checked');

            $.ajax({
                url: '/api/update_node_property',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    node_id: nodeId,
                    name: 'wait_until_complete',
                    val: enabled
                }),
                success: function() {
                    loadFlow();
                    addLog(`Toggled wait-complete for Node ${nodeId}: ${enabled ? 'Enabled' : 'Disabled'}`);
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
                        url: '/api/update_node_property',
                        method: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify({
                            node_id: pNodeId,
                            name: 'target_node_id',
                            val: null
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
                                url: '/api/update_node_property',
                                method: 'POST',
                                contentType: 'application/json',
                                data: JSON.stringify({
                                    node_id: nodeId,
                                    name: 'target_node_id',
                                    val: targetCard.attr('data-id')
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
            let query = $(this).val().toLowerCase().trim();
            
            $('.node-item').each(function() {
                let title = $(this).find('.node-item-main span').text().toLowerCase();
                let matchesTitle = title.includes(query);
                let matchesTag = false;
                $(this).find('.node-tag').each(function() {
                    if ($(this).text().toLowerCase().includes(query)) {
                        matchesTag = true;
                    }
                });
                
                if (!query || matchesTitle || matchesTag) {
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

        // Click tag to search
        $(document).on('click', '.node-tag', function(e) {
            e.stopPropagation();
            let tag = $(this).attr('data-tag');
            $('#node-search').val(tag).trigger('input');
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
        if (viewUpdatesPaused) return;
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
        if (viewUpdatesPaused) {
            scheduleNextPoll(1000); // retry later
            return;
        }
        if ($('.port-inline-input:focus').length > 0 || $('.port-label-input:focus').length > 0) {
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
