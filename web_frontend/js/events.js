/**
 * Event handlers — wiring up all user interactions.
 * Uses loadFlow (full re-render) for structural changes,
 * refreshFlow (light value update) for routine changes.
 */
import { state } from './state.js';
import * as API from './api.js';
import * as Logs from './logs.js';

let loadFlowFn = null;
let refreshFlowFn = null;
export function setLoadFlow(fn) { loadFlowFn = fn; }
export function setRefreshFlow(fn) { refreshFlowFn = fn; }
export function loadFlow() { if (loadFlowFn) loadFlowFn(); }
export function refreshFlow() { if (refreshFlowFn) refreshFlowFn(); }

// --- Structural: delete node ---
$(document).on('click', '.delete-btn', function () {
    const id = $(this).closest('.node-card').attr('data-id');
    if (id) API.deleteNode(id).then(() => { $(this).closest('.node-card').remove(); loadFlow(); });
});

// --- Value: inline input change ---
$(document).on('change', '.port-inline-input', function () {
    API.updateInput($(this).attr('data-node'), $(this).attr('data-index'), $(this).val()).then(refreshFlow);
});

// --- Value: loop toggle ---
$(document).on('change', '.loop-toggle', function () {
    const nid = $(this).attr('data-node');
    if (!nid) return;
    const enabled = $(this).is(':checked');
    API.updateNodeProp(nid, 'loop_enabled', enabled).then(() => {
        refreshFlow();
        Logs.addLog(`Toggled repeat loop for Node ${nid}: ${enabled ? 'Enabled' : 'Disabled'}`);
    });
});

// --- Value: loop interval ---
$(document).on('change', '.loop-interval', function () {
    const nid = $(this).attr('data-node');
    if (nid) API.updateNodeProp(nid, 'loop_interval', parseFloat($(this).val()) || 1.0).then(refreshFlow);
});

// --- Value: force trigger toggle ---
$(document).on('change', '.force-trigger-toggle', function () {
    const nid = $(this).attr('data-node');
    if (!nid) return;
    API.updateNodeProp(nid, 'force_trigger', $(this).is(':checked')).then(() => {
        refreshFlow();
        Logs.addLog(`Toggled force-trigger for Node ${nid}`);
    });
});

// --- Value: wait complete toggle ---
$(document).on('change', '.wait-complete-toggle', function () {
    const nid = $(this).attr('data-node');
    if (!nid) return;
    API.updateNodeProp(nid, 'wait_until_complete', $(this).is(':checked')).then(() => {
        refreshFlow();
        Logs.addLog(`Toggled wait-complete for Node ${nid}`);
    });
});

// --- Value: trigger action button ---
$(document).on('click', '.btn-trigger-action', function (e) {
    e.stopPropagation();
    const nid = $(this).attr('data-node');
    if (!nid) return;
    API.triggerNode(nid).then(refreshFlow);
});

// --- Value: double-click exec nodes ---
$(document).on('dblclick', '.node-card[data-category="Exec"]', function () {
    const nid = $(this).attr('data-id');
    if (!nid) return;
    API.triggerNode(nid).then(refreshFlow);
});

// --- Structural: wire delete ---
$(document).on('contextmenu', '.wire-path', function (e) {
    e.preventDefault();
    const $w = $(this);
    if ($w.hasClass('virtual-trigger')) {
        if (!confirm('Delete this virtual trigger link?')) return;
        API.updateNodeProp($w.attr('data-parent-node'), 'target_node_id', null).then(() => { $w.remove(); loadFlow(); });
        return;
    }
    if (!confirm('Delete this connection?')) return;
    API.disconnectNodes(
        $w.attr('data-parent-node'), $w.attr('data-parent-port'),
        $w.attr('data-dest-node'), $w.attr('data-dest-port')
    ).then(() => { $w.remove(); loadFlow(); });
});

// --- Value: port label rename ---
$(document).on('change', '.port-label-input', function () {
    API.renamePort($(this).attr('data-node'), $(this).attr('data-direction'), $(this).attr('data-index'), $(this).val()).then(refreshFlow);
});

// --- Structural: delete port ---
$(document).on('click', '.delete-port-btn', function (e) {
    e.stopPropagation();
    API.deletePort($(this).attr('data-node'), $(this).attr('data-direction'), $(this).attr('data-index')).then(loadFlow);
});

// --- Structural: add port ---
$(document).on('click', '.btn-add-port', function (e) {
    e.stopPropagation();
    API.addPort($(this).attr('data-node'), $(this).attr('data-direction')).then(loadFlow);
});

// --- Prevent drag on inputs ---
$(document).on('mousedown selectstart', '.port-label-input, .delete-port-btn, .btn-add-port', e => e.stopPropagation());

// --- Header: save / load / info ---
$('#btn-save').on('click', () => import('./modals.js').then(m => m.openSaveModal()));
$('#btn-load').on('click', () => import('./modals.js').then(m => m.openLoadModal()));
$('#btn-mode-info').on('click', () => import('./modals.js').then(m => m.openInfoModal()));

// --- Structural: clear ---
$('#btn-clear').on('click', () => {
    if (confirm('Clear entire flow?')) {
        API.clearFlow().then(() => { loadFlow(); Logs.addLog('Cleared workspace flow'); });
    }
});

// --- Value: pause ---
$('#btn-pause').on('click', function () {
    const next = !$(this).hasClass('btn-warning');
    API.setPaused(next).then(() => {
        refreshFlow();
        Logs.addLog(next ? 'Paused all execution loops' : 'Resumed all execution loops');
    });
});

// --- Value: pause view ---
$('#btn-pause-view').on('click', async function () {
    state.viewPaused = !state.viewPaused;
    const btn = $(this);
    if (state.viewPaused) {
        btn.removeClass('btn-secondary').addClass('btn-warning')
            .html('<span class="material-icons-round">visibility_off</span><span class="btn-label"> Resume View</span>')
            .attr('title', 'Resume canvas node updates');
        Logs.addLog('[Studio UI]: Canvas node view updates paused');
    } else {
        btn.removeClass('btn-warning').addClass('btn-secondary')
            .html('<span class="material-icons-round">visibility</span><span class="btn-label"> Pause View</span>')
            .attr('title', 'Pause canvas node updates (background execution continues)');
        Logs.addLog('[Studio UI]: Canvas node view updates resumed');
        refreshFlow();
    }
});

// --- Value: run flow trigger ---
$('#btn-run').on('click', function () {
    const mode = $('#alg-mode-select').val();
    const recompileBadge = $('#recompile-badge').is(':visible');

    const triggerExec = () => {
        $('.node-card').each(function () {
            const title = $(this).find('.node-title').text();
            if (title === 'Trigger' || ['String', 'Math'].includes($(this).attr('data-category'))) {
                API.triggerNode($(this).attr('data-id'));
            }
        });
        setTimeout(refreshFlow, 250);
        Logs.addLog('Manually triggered flow execution');
    };

    if (mode === 'compiled' && recompileBadge) {
        Logs.addLog('[Warning]: Flow modified. Auto-recompiling...');
        API.compileFlow().then(res => {
            if (res.status === 'success') {
                Logs.addLog('[Studio UI]: Auto-recompilation successful.');
                loadFlow(); // structural change: new compiled file
            } else alert('Auto-recompilation failed: ' + res.message);
        });
    } else triggerExec();
});

// --- Structural: compile ---
$('#btn-compile').on('click', () => {
    Logs.addLog('[Studio UI]: Compiling flow...');
    API.compileFlow().then(res => {
        if (res.status === 'success') { loadFlow(); Logs.addLog('[Studio UI]: Flow compiled: ' + res.filename); }
        else alert('Compilation failed: ' + res.message);
    }).catch(err => alert('Compilation request failed: ' + (err.responseJSON?.message || 'Unknown')));
});

// --- Structural: algorithm mode change ---
$('#alg-mode-select').on('change', function () {
    const mode = $(this).val();
    API.setAlgMode(mode).then(() => {
        loadFlow();
        Logs.addLog(`Switched execution mode to: ${mode}`);
    }).catch(err => {
        alert(err.responseJSON?.message || 'Failed to set algorithm mode');
        loadFlow();
    });
});

// --- Structural: compiled file select ---
$('#compiled-file-select').on('change', function () {
    const fname = $(this).val();
    API.setCompiledFile(fname).then(() => {
        loadFlow();
        Logs.addLog(`Switched active compiled file to: ${fname}`);
    });
});

// --- Log panel ---
$('#logs-header').on('click', function (e) {
    if ($(e.target).closest('.footer-btn').length) return;
    Logs.togglePanel();
});
$('#btn-toggle-logs').on('click', () => Logs.togglePanel());
$('#btn-clear-logs').on('click', () => {
    API.clearLogs().then(() => { $('#log-list').empty(); $('#log-count').text('0'); });
});

// --- Pause button sync ---
export function updatePauseButton(paused) {
    const btn = $('#btn-pause');
    if (paused) {
        btn.removeClass('btn-secondary').addClass('btn-warning')
            .html('<span class="material-icons-round">play_arrow</span><span class="btn-label"> Resume</span>')
            .attr('title', 'Resume all execution');
    } else {
        btn.removeClass('btn-warning').addClass('btn-secondary')
            .html('<span class="material-icons-round">pause</span><span class="btn-label"> Pause</span>')
            .attr('title', 'Pause all execution');
    }
}
