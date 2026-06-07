/**
 * Node cards — rendering, dragging, resizing, port I/O, custom content (REPL, Plot, etc.)
 */
import { state } from './state.js';
import * as API from './api.js';
import * as Wires from './wires.js';
import { loadFlow } from './events.js';
import { ChartRenderer } from './plotting.js';

// Track renderers per node for cleanup
const _chartRenderers = new Map();

const NS = 'http://www.w3.org/2000/svg';
const COLORS = ['#6366f1', '#22c55e', '#ef4444', '#f59e0b', '#06b6d4', '#a855f7', '#3b82f6', '#10b981'];

/** Visible category for a node title — clear taxonomy */
export function getNodeCategory(title) {
    // Math & Stats
    if (['Add', 'Subtract', 'Multiply', 'Divide', 'Array Calculator', 'Stats', 'Moving Average', 'Normalize', 'Correlation'].includes(title)) return 'Math & Stats';
    // Data & I/O
    if (['Parquet Reader', 'DuckDB Query', 'CSV Parser', 'Lazy File Reader', 'DataFrame'].includes(title)) return 'Data & I/O';
    // Logic & Control Flow
    if (['Compare', 'If/Else', 'Branch', 'Counter', 'Trigger', 'Execute Button', 'Filter'].includes(title)) return 'Control Flow';
    // Scripting
    if (['Python REPL', 'Python Script'].includes(title)) return 'Scripting';
    // Plotting & Charts
    if (['Plot', 'Advanced Plot', 'Orderbook Plot', 'Chart'].includes(title)) return 'Charts & Plots';
    // Neural Networks
    if (['Linear Layer', 'ReLU', 'Sigmoid', 'MSE Loss', 'SGD Optimizer', 'NN Inference', 'NN Trainer', 'NN Data Generator'].includes(title)) return 'Neural Nets';
    // Utilities
    if (['Random', 'Log', 'Execution Timer', 'Number', 'String', 'Concat', 'Uppercase'].includes(title)) return 'Utilities';
    return 'Utilities';
}

const DEFAULT_SIZES = {
    Plot: [220, 180],
    'Advanced Plot': [250, 220],
    'Orderbook Plot': [250, 220],
    'Array Calculator': [220, 140],
};

export function renderNodes(nodes) {
    const layer = $('#nodes-layer');
    const currentIds = nodes.map(n => n.id.toString());

    // Remove stale
    $('.node-card').each(function () {
        if (!currentIds.includes($(this).attr('data-id'))) {
            Wires.unobserve($(this));
            $(this).remove();
        }
    });

    nodes.forEach(n => {
        const cat = getNodeCategory(n.title);
        let $el = $(`.node-card[data-id="${n.id}"]`);

        if ($el.length === 0) {
            const repOpt = n.repeat_option_visible || false;
            const timerOpt = n.timer_option_visible || false;
            const forceOpt = n.force_trigger_visible || false;
            const waitOpt = n.wait_complete_visible || false;
            const hasOpts = repOpt || timerOpt || forceOpt || waitOpt;

            $el = $(`
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
                    <div class="node-timer-wrapper" style="display:${hasOpts ? 'block' : 'none'};">
                        <div class="timer-row" style="display:${(repOpt || timerOpt) ? 'flex' : 'none'};">
                            <label class="timer-toggle-label" style="display:${repOpt ? 'flex' : 'none'};">
                                <input type="checkbox" class="loop-toggle" data-node="${n.id}">
                                <span class="material-icons-round timer-icon">schedule</span>
                                <span class="timer-text">Repeat</span>
                            </label>
                            <div class="timer-interval-wrapper" style="display:${timerOpt ? 'flex' : 'none'};">
                                <input type="number" class="loop-interval" data-node="${n.id}" min="0.1" step="0.1" value="1.0">
                                <span class="timer-unit">s</span>
                            </div>
                        </div>
                        <div class="extra-options-row" style="display:${(forceOpt || waitOpt) ? 'flex' : 'none'}; margin-top:6px; border-top:1px solid rgba(255,255,255,0.03); padding-top:4px; justify-content:space-between;">
                            <label class="force-trigger-label" style="display:${forceOpt ? 'flex' : 'none'};">
                                <input type="checkbox" class="force-trigger-toggle" data-node="${n.id}">
                                <span>Force Trigger</span>
                            </label>
                            <label class="wait-complete-label" style="display:${waitOpt ? 'flex' : 'none'};">
                                <input type="checkbox" class="wait-complete-toggle" data-node="${n.id}">
                                <span>Wait Complete</span>
                            </label>
                        </div>
                    </div>
                    <div class="node-resize-handle"></div>
                </div>
            `);
            layer.append($el);
            setupDragging($el);
            setupResizing($el);
            Wires.initObserver($el);
        }

        // Position & size
        $el.attr({ 'data-target-node-id': n.target_node_id || '', 'data-x': n.x, 'data-y': n.y });
        $el.css({ left: `${n.x}px`, top: `${n.y}px` });

        const [defW, defH] = DEFAULT_SIZES[n.title] || [200, 120];
        const w = n.width || defW, h = n.height || defH;
        $el.attr({ 'data-width': w, 'data-height': h }).css({ width: `${w}px`, minHeight: `${h}px` });

        // Timer / checkbox state
        $el.find('.loop-toggle').prop('checked', n.loop_enabled);
        $el.find('.loop-interval').val(n.loop_interval);
        $el.find('.force-trigger-toggle').prop('checked', n.force_trigger || false);
        $el.find('.wait-complete-toggle').prop('checked', n.wait_until_complete || false);

        const timerIcon = $el.find('.timer-icon');
        if (n.loop_enabled) { $el.addClass('timer-active'); timerIcon.addClass('active'); }
        else { $el.removeClass('timer-active'); timerIcon.removeClass('active'); }

        if (state.selectedNodeId === n.id.toString()) $el.addClass('selected');

        // --- Ports ---
        const portsCtr = $el.find('.node-ports').empty();
        const maxP = Math.max(n.inputs.length, n.outputs.length);
        for (let i = 0; i < maxP; i++) {
            const row = $('<div class="port-row"></div>');

            if (i < n.inputs.length) {
                const inp = n.inputs[i];
                const isExec = inp.type === 'exec';
                const col = $('<div class="port-input-container"></div>');

                if (n.title === 'Python REPL') {
                    col.append($(`<span class="material-icons-round delete-port-btn" data-node="${n.id}" data-index="${i}" data-direction="input" style="font-size:12px;color:var(--text-muted);cursor:pointer;margin-right:4px;" title="Delete input">close</span>`));
                    col.append($(`<input type="text" class="port-label-input" data-node="${n.id}" data-index="${i}" data-direction="input" value="${inp.label}" style="width:60px;background:transparent;border:none;border-bottom:1px dashed rgba(255,255,255,0.3);color:#fff;font-size:0.75rem;padding:2px;outline:none;margin-right:4px;">`));
                } else {
                    col.append(`<span class="port-label">${inp.label}</span>`);
                }
                if (!isExec) col.append($(`<input type="text" class="port-inline-input" data-node="${n.id}" data-index="${i}" value="${inp.val !== null ? inp.val : ''}">`));

                row.append(col);
                row.append(`<div class="port-handle input ${isExec ? 'exec' : ''}" data-node="${n.id}" data-index="${i}" data-direction="input" data-type="${inp.type}" title="${inp.label} (${inp.type})"></div>`);
            }

            if (i < n.outputs.length) {
                const out = n.outputs[i];
                const isExec = out.type === 'exec';
                const col = $('<div class="port-output-container"></div>');

                if (!isExec && out.val !== null) col.append(`<span class="port-value-display" title="${out.val}">${out.val}</span>`);

                if (n.title === 'Python REPL') {
                    col.append($(`<input type="text" class="port-label-input" data-node="${n.id}" data-index="${i}" data-direction="output" value="${out.label}" style="width:60px;background:transparent;border:none;border-bottom:1px dashed rgba(255,255,255,0.3);color:#fff;font-size:0.75rem;padding:2px;outline:none;text-align:right;margin-left:4px;">`));
                    col.append($(`<span class="material-icons-round delete-port-btn" data-node="${n.id}" data-index="${i}" data-direction="output" style="font-size:12px;color:var(--text-muted);cursor:pointer;margin-left:4px;" title="Delete output">close</span>`));
                } else {
                    col.append(`<span class="port-label">${out.label}</span>`);
                }

                row.append(col);
                row.append(`<div class="port-handle output ${isExec ? 'exec' : ''}" data-node="${n.id}" data-index="${i}" data-direction="output" data-type="${out.type}" title="${out.label} (${out.type})"></div>`);
            }

            portsCtr.append(row);
        }

        // REPL add-port buttons
        $el.find('.add-ports-row').remove();
        if (n.title === 'Python REPL') {
            portsCtr.after($(`
                <div class="add-ports-row" style="display:flex;justify-content:space-between;padding:4px 14px;border-top:1px solid rgba(255,255,255,0.03);">
                    <button class="btn-add-port" data-node="${n.id}" data-direction="input" style="background:none;border:none;color:var(--text-secondary);font-size:0.7rem;cursor:pointer;display:flex;align-items:center;gap:2px;">
                        <span class="material-icons-round" style="font-size:12px;">add</span> Add Input
                    </button>
                    <button class="btn-add-port" data-node="${n.id}" data-direction="output" style="background:none;border:none;color:var(--text-secondary);font-size:0.7rem;cursor:pointer;display:flex;align-items:center;gap:2px;">
                        <span class="material-icons-round" style="font-size:12px;">add</span> Add Output
                    </button>
                </div>
            `));
        }

        Wires.cachePortOffsets($el);

        // --- Custom node content ---
        renderCustomContent($el, n);
    });

    setTimeout(() => $('.port-inline-input').show(), 50);
}

function renderCustomContent($el, n) {
    if (n.title === 'Execute Button') {
        if (!$el.find('.node-custom-content').length) {
            $el.find('.node-ports').after(`
                <div class="node-custom-content" style="padding:0 14px 10px; display:flex; justify-content:center;">
                    <button class="btn btn-primary btn-trigger-action" data-node="${n.id}" style="width:100%;justify-content:center;padding:6px 12px;font-size:0.8rem;">
                        <span class="material-icons-round" style="font-size:16px;">play_arrow</span> Trigger
                    </button>
                </div>
            `);
        }
    } else if (n.title === 'Python REPL') {
        if (!$el.find('.node-custom-content').length) {
            $el.find('.node-ports').after(`
                <div class="node-custom-content" style="padding:0 14px 10px; display:flex; flex-direction:column; gap:4px;">
                    <label style="font-size:0.75rem;color:var(--text-secondary);">Python Code:</label>
                    <textarea class="repl-code-input" data-node="${n.id}" style="width:100%;height:80px;font-family:monospace;font-size:0.75rem;background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.1);color:#fff;resize:vertical;padding:4px;border-radius:4px;"></textarea>
                </div>
            `);
            const ta = $el.find('.repl-code-input');
            ta.val(n.code || '');
            ta.on('mousedown selectstart', e => e.stopPropagation());
            ta.on('change', function () {
                API.updateNodeProp(n.id, 'code', $(this).val());
            });
        } else {
            const ta = $el.find('.repl-code-input');
            if (!ta.is(':focus')) ta.val(n.code || '');
        }
    } else if (n.title === 'Python Script') {
        if (!$el.find('.node-custom-content').length) {
            $el.find('.node-ports').after(`
                <div class="node-custom-content" style="padding:0 14px 10px; display:flex; flex-direction:column; gap:4px;">
                    <label style="font-size:0.75rem;color:var(--text-secondary);">Script Path:</label>
                    <input type="text" class="script-path-input" data-node="${n.id}" placeholder="e.g. example_script.py" style="width:100%;font-family:monospace;font-size:0.75rem;background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.1);color:#fff;padding:4px;border-radius:4px;">
                </div>
            `);
            const inp = $el.find('.script-path-input');
            inp.val(n.script_path || '');
            inp.on('mousedown selectstart', e => e.stopPropagation());
            inp.on('change', function () {
                API.updateNodeProp(n.id, 'script_path', $(this).val()).then(loadFlow);
            });
        } else {
            const inp = $el.find('.script-path-input');
            if (!inp.is(':focus')) inp.val(n.script_path || '');
        }
    } else if (n.title === 'Plot') {
        // Replace or create plot container
        let ctr = $el.find('.node-custom-content');
        if (!ctr.length) {
            $el.find('.node-ports').after(`<div class="node-custom-content" style="padding:0 10px 10px;display:flex;flex-direction:column;gap:4px;align-items:center;width:100%;height:100px;box-sizing:border-box;"><div class="plot-canvas" style="width:100%;height:100%;border:1px solid rgba(255,255,255,0.05);border-radius:4px;overflow:hidden;"></div></div>`);
            ctr = $el.find('.node-custom-content');
        }
        // Lazily create ChartRenderer
        const nid = n.id.toString();
        if (!_chartRenderers.has(nid)) {
            const canvas = ctr.find('.plot-canvas');
            const cr = new ChartRenderer(canvas[0], { title: n.title, bg: 'rgba(0,0,0,0.35)' });
            _chartRenderers.set(nid, cr);
        }
        const cr = _chartRenderers.get(nid);
        // Parse buffer: array of numbers or array of arrays
        const buf = n.buffer || [];
        let series;
        if (buf.length > 0 && Array.isArray(buf[0])) {
            series = buf.map((arr, i) => ({ data: arr, color: COLORS[i % COLORS.length], label: n.series_labels?.[i] || '' }));
        } else {
            series = [{ data: buf, color: '#6366f1', label: '', fill: true }];
        }
        cr.setData(series);
    } else if (n.title === 'Advanced Plot' || n.title === 'Orderbook Plot') {
        if (!$el.find('.node-custom-content').length) {
            $el.find('.node-ports').after(`<div class="node-custom-content" style="padding:0 10px 10px;display:flex;flex-direction:column;gap:4px;align-items:center;width:100%;height:160px;box-sizing:border-box;"><div class="custom-svg-container" style="width:100%;height:100%;border:1px solid rgba(255,255,255,0.05);border-radius:4px;overflow:hidden;background:rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:center;"></div></div>`);
        }
        const ctr = $el.find('.custom-svg-container');
        ctr.html(n.svg_content || '<div style="color:var(--text-muted);font-size:0.65rem;display:flex;align-items:center;justify-content:center;height:100%;">No data plotted yet</div>');
    } else {
        $el.find('.node-custom-content').remove();
    }
}

// --- Dragging ---
function setupDragging($el) {
    let dragging = false, startX, startY, origX, origY;
    $el.find('.node-header').on('mousedown', function (e) {
        if ($(e.target).closest('.node-action-btn').length) return;
        dragging = true; state.userInteracting = true;
        $el.addClass('selected'); state.selectedNodeId = $el.attr('data-id');
        $('.node-card').not($el).removeClass('selected');

        startX = e.clientX; startY = e.clientY;
        origX = parseFloat($el.css('left')); origY = parseFloat($el.css('top'));

        $(document).on('mousemove.drag', ev => {
            if (!dragging) return;
            const dx = (ev.clientX - startX) / state.zoom;
            const dy = (ev.clientY - startY) / state.zoom;
            const nx = origX + dx, ny = origY + dy;
            $el.css({ left: `${nx}px`, top: `${ny}px` }).attr({ 'data-x': nx, 'data-y': ny });
            Wires.refreshAll();
        }).on('mouseup.drag', () => {
            dragging = false; state.userInteracting = false;
            $(document).off('.drag');
            const id = $el.attr('data-id');
            if (id) {
                API.moveNode(id, parseFloat($el.attr('data-x')), parseFloat($el.attr('data-y')));
            }
        });
    });
}

// --- Resizing ---
function setupResizing($el) {
    let resizing = false, sX, sY, sW, sH;
    $el.find('.node-resize-handle').on('mousedown', function (e) {
        e.stopPropagation(); e.preventDefault();
        resizing = true; state.userInteracting = true;
        sX = e.clientX; sY = e.clientY;
        sW = $el.outerWidth(); sH = $el.outerHeight();

        $(document).on('mousemove.resize', ev => {
            if (!resizing) return;
            const nw = Math.max(160, sW + (ev.clientX - sX) / state.zoom);
            const nh = Math.max(100, sH + (ev.clientY - sY) / state.zoom);
            $el.css({ width: `${nw}px`, minHeight: `${nh}px` }).attr({ 'data-width': nw, 'data-height': nh });
            Wires.refreshAll();
        }).on('mouseup.resize', () => {
            resizing = false; state.userInteracting = false;
            $(document).off('.resize');
            Wires.cachePortOffsets($el);
            const id = $el.attr('data-id');
            if (id) {
                API.moveNode(id, parseFloat($el.attr('data-x')), parseFloat($el.attr('data-y')), $el.attr('data-width'), $el.attr('data-height'));
            }
        });
    });
}

// --- Live value polling update (no full re-render) ---
export function updateFlowValues(flowData) {
    flowData.nodes.forEach(n => {
        const $el = $(`.node-card[data-id="${n.id}"]`);
        if (!$el.length) return;
        $el.attr('data-target-node-id', n.target_node_id || '');

        n.inputs.forEach((inp, idx) => {
            if (inp.type === 'data') {
                const w = $el.find(`.port-inline-input[data-index="${idx}"]`);
                if (w.length && !w.is(':focus') && w.val() !== String(inp.val ?? '')) w.val(inp.val ?? '');
            }
        });
        n.outputs.forEach((out, idx) => {
            if (out.type === 'data') {
                const col = $el.find('.port-output-container').eq(idx);
                let vd = col.find('.port-value-display');
                if (out.val !== null) {
                    const t = String(out.val);
                    if (!vd.length) { col.append(`<span class="port-value-display" title="${t}">${t}</span>`); }
                    else if (vd.text() !== t) { vd.text(t).attr('title', t); }
                } else { vd.remove(); }
            }
        });

        // Loop toggle
        const lt = $el.find('.loop-toggle');
        if (lt.length && !lt.is(':active')) lt.prop('checked', n.loop_enabled);
        const li = $el.find('.loop-interval');
        if (li.length && !li.is(':focus')) li.val(n.loop_interval);

        const ti = $el.find('.timer-icon');
        if (n.loop_enabled) { $el.addClass('timer-active'); ti.addClass('active'); }
        else { $el.removeClass('timer-active'); ti.removeClass('active'); }

        // Force/Wait toggles
        const ft = $el.find('.force-trigger-toggle');
        if (ft.length && !ft.is(':active')) ft.prop('checked', n.force_trigger || false);
        const wt = $el.find('.wait-complete-toggle');
        if (wt.length && !wt.is(':active')) wt.prop('checked', n.wait_until_complete || false);

        // Option visibility
        const repOpt = n.repeat_option_visible || false, timerOpt = n.timer_option_visible || false;
        const forceOpt = n.force_trigger_visible || false, waitOpt = n.wait_complete_visible || false;

        $el.find('.timer-toggle-label').css('display', repOpt ? 'flex' : 'none');
        $el.find('.timer-interval-wrapper').css('display', timerOpt ? 'flex' : 'none');
        $el.find('.timer-row').css('display', (repOpt || timerOpt) ? 'flex' : 'none');
        $el.find('.force-trigger-label').css('display', forceOpt ? 'flex' : 'none');
        $el.find('.wait-complete-label').css('display', waitOpt ? 'flex' : 'none');
        $el.find('.extra-options-row').css('display', (forceOpt || waitOpt) ? 'flex' : 'none');
        $el.find('.node-timer-wrapper').css('display', (repOpt || timerOpt || forceOpt || waitOpt) ? 'block' : 'none');

        // SVG updates
        if (n.title === 'Plot') {
            const cr = _chartRenderers.get(n.id.toString());
            if (cr) {
                const buf = n.buffer || [];
                let series;
                if (buf.length > 0 && Array.isArray(buf[0])) {
                    series = buf.map((arr, i) => ({ data: arr, color: COLORS[i % COLORS.length] }));
                } else {
                    series = [{ data: buf, color: '#6366f1', fill: true }];
                }
                cr.setData(series);
            }
        } else if (n.title === 'Advanced Plot' || n.title === 'Orderbook Plot') {
            const ctr = $el.find('.custom-svg-container');
            if (ctr.length) ctr.html(n.svg_content || '<div style="color:var(--text-muted);font-size:0.65rem;">No data plotted yet</div>');
        }
    });
}

