/**
 * app.js — Main entry point for ryvencore Studio.
 */
import { state, applyTransform } from './state.js';
import * as API from './api.js';
import * as Canvas from './canvas.js';
import * as Nodes from './nodes.js';
import * as Wires from './wires.js';
import * as Sidebar from './sidebar.js';
import * as Logs from './logs.js';
import * as Events from './events.js';
import * as Modals from './modals.js';
import { setLoadFlow } from './events.js';

// ---- Loading overlay ----
function showLoading(visible) {
    $('#app-loading').toggle(visible);
}

// ---- Flow Loading ----
export async function loadFlow() {
    try {
        showLoading(true);
        const flowData = await API.loadFlowState();

        // Algorithm mode selector
        $('#alg-mode-select').val(flowData.algorithm_mode);

        // Compiled mode handling
        const optCompiled = $('#alg-mode-select option[value="compiled"]');
        if (flowData.compiled_exists) {
            optCompiled.prop('disabled', false).show();
        } else {
            optCompiled.prop('disabled', true).hide();
            if (flowData.algorithm_mode === 'compiled') {
                await API.setAlgMode('data');
                Logs.addLog('[Warning]: Compiled file not found. Reverted to Data Flow mode.');
                return loadFlow();
            }
        }

        // Recompile badge — stop any running animation first
        const badge = $('#recompile-badge');
        if (flowData.compiled_exists && flowData.compiled_dirty) {
            badge.stop(true, true).fadeIn(200);
            if (flowData.algorithm_mode === 'compiled') {
                Logs.addLog('[Warning]: Flow modified since compilation. Recompilation required.');
            }
        } else {
            badge.stop(true, true).fadeOut(200);
        }

        // Compiled UI customization
        const runBtn = $('#btn-run');
        const compiledBadge = $('#compiled-badge');
        const compiledFileGroup = $('#compiled-file-group');
        if (flowData.algorithm_mode === 'compiled') {
            compiledBadge.stop(true).fadeIn(200);
            runBtn.html('<span class="material-icons-round">play_arrow</span> Run Compiled')
                .css({ background: 'linear-gradient(135deg,#ab47bc,#7b1fa2)', border: 'none', 'box-shadow': '0 0 10px rgba(171,71,188,0.4)' })
                .attr('title', 'Execute compiled in-process flow logic');

            const sel = $('#compiled-file-select').empty();
            if (flowData.compiled_files?.length) {
                flowData.compiled_files.forEach(f => sel.append($('<option>').val(f).text(f)));
                if (flowData.active_compiled_file) sel.val(flowData.active_compiled_file);
            }
            compiledFileGroup.stop(true).fadeIn(200);
        } else {
            compiledBadge.stop(true).fadeOut(200);
            runBtn.html('<span class="material-icons-round">play_arrow</span> Run Flow')
                .css({ background: '', border: '', 'box-shadow': '' })
                .attr('title', 'Trigger execution update');
            compiledFileGroup.stop(true).fadeOut(200);
        }

        Events.updatePauseButton(flowData.execution_paused);

        // Render
        Nodes.renderNodes(flowData.nodes);
        Nodes.updateFlowValues(flowData);
        Wires.renderConnections(flowData.connections);
    } catch (err) {
        console.error('loadFlow failed:', err);
    } finally {
        showLoading(false);
    }
}

// ---- Right-click menus (static imports) ----
$('#canvas-viewport').on('contextmenu', function (e) {
    if ($(e.target).closest('.node-card, .port-handle, .wire-path').length) return;
    e.preventDefault();
    const offset = $(this).offset();
    const cx = (e.clientX - offset.left - state.panX) / state.zoom;
    const cy = (e.clientY - offset.top - state.panY) / state.zoom;
    state.radialX = cx; state.radialY = cy;
    Modals.showRadialMenu(e.pageX, e.pageY);
});

$(document).on('contextmenu', '.node-card', function (e) {
    e.preventDefault(); e.stopPropagation();
    Modals.showNodeRadial(e.pageX, e.pageY, $(this).attr('data-id'));
});

// ---- Polling ----
export function pollFlowUpdates() {
    if (state.viewPaused) { schedulePoll(1000); return; }
    if ($('.port-inline-input:focus').length || $('.port-label-input:focus').length) {
        schedulePoll(1000); return;
    }

    API.loadFlowState().then(flowData => {
        Nodes.updateFlowValues(flowData);
        Events.updatePauseButton(flowData.execution_paused);
        const activeLoops = flowData.nodes.filter(n => n.loop_enabled).length;
        schedulePoll(activeLoops > 0 ? 100 : 1000);
    }).catch(() => schedulePoll(2000));
}

function schedulePoll(delay) {
    clearTimeout(state.pollTimeout);
    state.pollTimeout = setTimeout(pollFlowUpdates, delay);
}

// ---- Wire drawing ----
$(document).on('mousedown', '.port-handle', function (e) {
    e.stopPropagation();
    Wires.startWireDraw($(this));
    $(document).on('mouseup.wire', function (ev) {
        Wires.endWireDraw(ev);
    });
});

// ---- Init ----
function init() {
    applyTransform();
    setLoadFlow(loadFlow);
    Canvas.init();
    Sidebar.loadLibrary();
    Logs.startLogPolling();
    loadFlow().then(() => schedulePoll(1000));
}

$(init);
