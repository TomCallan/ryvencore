/**
 * Event handlers — wiring up inline input changes, checkboxes,
 * port add/delete/rename, wire deletion, trigger buttons, execution mode.
 */
import * as API from './api.js';

let loadFlowFn = null;
export function setLoadFlow(fn) { loadFlowFn = fn; }
export function loadFlow() { if (loadFlowFn) loadFlowFn(); }

// --- Delete node ---
$(document).on('click', '.delete-btn', function () {
    const card = $(this).closest('.node-card');
    const id = card.attr('data-id');
    API.deleteNode(id).then(() => { card.remove(); loadFlow(); });
});

// --- Inline input change ---
$(document).on('change', '.port-inline-input', function () {
    API.updateInput($(this).attr('data-node'), $(this).attr('data-index'), $(this).val()).then(loadFlow);
});

// --- Loop toggle ---
$(document).on('change', '.loop-toggle', function () {
    const nid = $(this).attr('data-node');
    const enabled = $(this).is(':checked');
    API.updateNodeProp(nid, 'loop_enabled', enabled).then(() => {
        loadFlow();
        import('./logs.js').then(m => m.addLog(`Toggled repeat loop for Node ${nid}: ${enabled ? 'Enabled' : 'Disabled'}`));
    });
});

// --- Loop interval ---
$(document).on('change', '.loop-interval', function () {
    API.updateNodeProp($(this).attr('data-node'), 'loop_interval', parseFloat($(this).val()) || 1.0).then(loadFlow);
});

// --- Force trigger toggle ---
$(document).on('change', '.force-trigger-toggle', function () {
    const nid = $(this).attr('data-node');
    API.updateNodeProp(nid, 'force_trigger', $(this).is(':checked')).then(() => {
        loadFlow();
        import('./logs.js').then(m => m.addLog(`Toggled force-trigger for Node ${nid}`));
    });
});

// --- Wait complete toggle ---
$(document).on('change', '.wait-complete-toggle', function () {
    const nid = $(this).attr('data-node');
    API.updateNodeProp(nid, 'wait_until_complete', $(this).is(':checked')).then(() => {
        loadFlow();
        import('./logs.js').then(m => m.addLog(`Toggled wait-complete for Node ${nid}`));
    });
});

// --- Trigger action button (Execute Button) ---
$(document).on('click', '.btn-trigger-action', function (e) {
    e.stopPropagation();
    const nid = $(this).attr('data-node');
    API.triggerNode(nid).then(() => {
        loadFlow();
        import('./logs.js').then(m => m.addLog(`Triggered Execute Button node ${nid}`));
    });
});

// --- Double-click Exec nodes ---
$(document).on('dblclick', '.node-card[data-category="Exec"]', function () {
    const nid = $(this).attr('data-id');
    API.triggerNode(nid).then(() => {
        loadFlow();
        import('./logs.js').then(m => m.addLog(`Double-clicked Exec node ${nid} to trigger execution path`));
    });
});

// --- Wire right-click delete ---
$(document).on('contextmenu', '.wire-path', function (e) {
    e.preventDefault();
    const $w = $(this);

    if ($w.hasClass('virtual-trigger')) {
        if (!confirm('Delete this virtual trigger link?')) return;
        API.updateNodeProp($w.attr('data-parent-node'), 'target_node_id', null).then(() => { $w.remove(); loadFlow(); });
        return;
    }

    if (!confirm('Delete this connection?')) return;
    API.disconnectNodes($w.attr('data-parent-node'), $w.attr('data-parent-port'), $w.attr('data-dest-node'), $w.attr('data-dest-port'))
        .then(() => { $w.remove(); loadFlow(); });
});

// --- Port label rename ---
$(document).on('change', '.port-label-input', function () {
    API.renamePort($(this).attr('data-node'), $(this).attr('data-direction'), $(this).attr('data-index'), $(this).val()).then(loadFlow);
});

// --- Delete port ---
$(document).on('click', '.delete-port-btn', function (e) {
    e.stopPropagation();
    API.deletePort($(this).attr('data-node'), $(this).attr('data-direction'), $(this).attr('data-index')).then(loadFlow);
});

// --- Add port ---
$(document).on('click', '.btn-add-port', function (e) {
    e.stopPropagation();
    API.addPort($(this).attr('data-node'), $(this).attr('data-direction')).then(loadFlow);
});

// --- Prevent drag on label inputs ---
$(document).on('mousedown selectstart', '.port-label-input, .delete-port-btn, .btn-add-port', e => e.stopPropagation());

// --- Header controls ---
$('#btn-save').on('click', () => import('./modals.js').then(m => m.openSaveModal()));
$('#btn-load').on('click', () => import('./modals.js').then(m => m.openLoadModal()));
$('#btn-mode-info').on('click', () => import('./modals.js').then(m => m.openInfoModal()));

$('#btn-clear').on('click', () => {
    if (confirm('Clear entire flow?')) {
        API.clearFlow().then(() => { loadFlow(); import('./logs.js').then(m => m.addLog('Cleared workspace flow')); });
    }
});

$('#btn-pause').on('click', function () {
    const paused = $(this).hasClass('btn-warning');
    const next = !paused;
    API.setPaused(next).then(() => {
        loadFlow();
        import('./logs.js').then(m => m.addLog(next ? 'Paused all execution loops' : 'Resumed all execution loops'));
    });
});

$('#btn-pause-view').on('click', async function () {
    const { state } = await import('./state.js');
    state.viewPaused = !state.viewPaused;
    const btn = $(this);
    if (state.viewPaused) {
        btn.removeClass('btn-secondary').addClass('btn-warning')
            .html('<span class="material-icons-round">visibility_off</span> Resume View')
            .attr('title', 'Resume canvas node updates');
        (await import('./logs.js')).addLog('[Studio UI]: Canvas node view updates paused');
    } else {
        btn.removeClass('btn-warning').addClass('btn-secondary')
            .html('<span class="material-icons-round">visibility</span> Pause View')
            .attr('title', 'Pause canvas node updates (background execution continues)');
        (await import('./logs.js')).addLog('[Studio UI]: Canvas node view updates resumed');
        const { pollFlowUpdates } = await import('./app.js');
        pollFlowUpdates();
    }
});

$('#btn-run').on('click', function () {
    const mode = $('#alg-mode-select').val();
    const recompile = $('#recompile-badge').is(':visible');

    const triggerExec = () => {
        $('.node-card').each(function () {
            const card = $(this);
            const title = card.find('.node-title').text();
            const cat = card.attr('data-category');
            if (title === 'Trigger' || ['String', 'Math'].includes(cat)) {
                API.triggerNode(card.attr('data-id'));
            }
        });
        setTimeout(loadFlow, 250);
        import('./logs.js').then(m => m.addLog('Manually triggered flow execution'));
    };

    if (mode === 'compiled' && recompile) {
        import('./logs.js').then(m => m.addLog('[Warning]: Flow has modified nodes. Auto-recompiling...'));
        API.compileFlow().then(res => {
            if (res.status === 'success') {
                import('./logs.js').then(m => m.addLog('[Studio UI]: Auto-recompilation successful.'));
                triggerExec();
            } else {
                alert('Auto-recompilation failed: ' + res.message);
            }
        });
    } else {
        triggerExec();
    }
});

$('#btn-compile').on('click', () => {
    import('./logs.js').then(m => m.addLog('[Studio UI]: Compiling flow into a standalone Python file...'));
    API.compileFlow().then(res => {
        if (res.status === 'success') {
            loadFlow();
            import('./logs.js').then(m => m.addLog('[Studio UI]: Flow successfully compiled: ' + res.filename));
        } else {
            alert('Compilation failed: ' + res.message);
        }
    }).catch(err => alert('Compilation request failed: ' + (err.responseJSON?.message || 'Unknown')));
});

// --- Algorithm mode select ---
$('#alg-mode-select').on('change', function () {
    const mode = $(this).val();
    API.setAlgMode(mode).then(() => {
        loadFlow();
        import('./logs.js').then(m => m.addLog(`Switched execution mode to: ${mode}`));
    }).catch(err => {
        alert(err.responseJSON?.message || 'Failed to set algorithm mode');
        loadFlow();
    });
});

// --- Compiled file select ---
$('#compiled-file-select').on('change', function () {
    const fname = $(this).val();
    API.setCompiledFile(fname).then(() => {
        loadFlow();
        import('./logs.js').then(m => m.addLog(`Switched active compiled file to: ${fname}`));
    });
});

// --- Log panel header ---
$('#logs-header').on('click', function (e) {
    if ($(e.target).closest('.footer-btn').length) return;
    import('./logs.js').then(m => m.togglePanel());
});
$('#btn-toggle-logs').on('click', () => import('./logs.js').then(m => m.togglePanel()));
$('#btn-clear-logs').on('click', () => {
    API.clearLogs().then(() => { $('#log-list').empty(); $('#log-count').text('0'); });
});

// --- Pause button state sync ---
export function updatePauseButton(paused) {
    const btn = $('#btn-pause');
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
