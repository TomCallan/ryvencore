/**
 * app.js — Main entry point for ryvencore Studio.
 * Boots the application, orchestrates modules, and manages the polling loop.
 */
import { state, applyTransform } from './state.js';
import * as API from './api.js';
import * as Canvas from './canvas.js';
import * as Nodes from './nodes.js';
import * as Wires from './wires.js';
import * as Sidebar from './sidebar.js';
import * as Logs from './logs.js';
import * as Events from './events.js';
import { setLoadFlow } from './events.js';

// ---- Flow Loading (the central data refresh) ----
export async function loadFlow() {
    try {
        const flowData = await API.loadFlowState();

        // Sync algorithm mode selector
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

        // Recompile badge
        if (flowData.compiled_exists && flowData.compiled_dirty) {
            $('#recompile-badge').fadeIn(200);
            if (flowData.algorithm_mode === 'compiled') {
                Logs.addLog('[Warning]: Flow modified since compilation. Recompilation is required to run.');
            }
        } else {
            $('#recompile-badge').fadeOut(200);
        }

        // Compiled UI customization
        if (flowData.algorithm_mode === 'compiled') {
            $('#compiled-badge').fadeIn(200);
            $('#btn-run').html('<span class="material-icons-round">play_arrow</span> Run Compiled')
                .css({ background: 'linear-gradient(135deg, #ab47bc, #7b1fa2)', border: 'none', 'box-shadow': '0 0 10px rgba(171,71,188,0.4)' })
                .attr('title', 'Execute compiled in-process flow logic');

            const sel = $('#compiled-file-select').empty();
            if (flowData.compiled_files?.length) {
                flowData.compiled_files.forEach(f => sel.append($('<option>').val(f).text(f)));
                if (flowData.active_compiled_file) sel.val(flowData.active_compiled_file);
            }
            $('#compiled-file-group').fadeIn(200);
        } else {
            $('#compiled-badge').fadeOut(200);
            $('#btn-run').html('<span class="material-icons-round">play_arrow</span> Run Flow')
                .css({ background: '', border: '', 'box-shadow': '' })
                .attr('title', 'Trigger execution update');
            $('#compiled-file-group').fadeOut(200);
        }

        // Sync pause button
        Events.updatePauseButton(flowData.execution_paused);

        // Render
        Nodes.renderNodes(flowData.nodes);
        Nodes.updateFlowValues(flowData);
        Wires.renderConnections(flowData.connections);

    } catch (err) {
        console.error('loadFlow failed:', err);
    }
}

// ---- Polling ----
export function pollFlowUpdates() {
    if (state.viewPaused) {
        schedulePoll(1000);
        return;
    }
    if ($('.port-inline-input:focus').length || $('.port-label-input:focus').length) {
        schedulePoll(1000);
        return;
    }

    API.loadFlowState().then(flowData => {
        Nodes.updateFlowValues(flowData);
        Events.updatePauseButton(flowData.execution_paused);
        const activeLoops = flowData.nodes.filter(n => n.loop_enabled).length;
        schedulePoll(activeLoops > 0 ? 100 : 1000);
    }).catch(() => {
        schedulePoll(2000);
    });
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

// ---- Right-click menus ----
$('#canvas-viewport').on('contextmenu', function (e) {
    if ($(e.target).closest('.node-card, .port-handle, .wire-path').length) return;
    e.preventDefault();

    const offset = $(this).offset();
    const cx = (e.clientX - offset.left - state.panX) / state.zoom;
    const cy = (e.clientY - offset.top - state.panY) / state.zoom;
    state.radialX = cx; state.radialY = cy;

    import('./modals.js').then(m => m.showRadialMenu(e.pageX, e.pageY));
});

$(document).on('contextmenu', '.node-card', function (e) {
    e.preventDefault(); e.stopPropagation();
    import('./modals.js').then(m => m.showNodeRadial(e.pageX, e.pageY, $(this).attr('data-id')));
});

// ---- Init ----
function init() {
    applyTransform();
    setLoadFlow(loadFlow);

    Canvas.init();
    Sidebar.loadLibrary();
    Logs.startLogPolling();

    // Initial load then start polling
    loadFlow().then(() => schedulePoll(1000));
}

$(init);
