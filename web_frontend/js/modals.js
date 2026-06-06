/**
 * Modals — Save, Load, Info, Radial Menus, Radial Search.
 */
import { state } from './state.js';
import { getNodeCategory } from './nodes.js';
import * as API from './api.js';

// --- Modal helpers ---
function showModal(id) { $(`#${id}`).css('display', 'flex').hide().fadeIn(200); }
function hideModals() { $('.modal-overlay').fadeOut(200); }

// --- Save Modal ---
export function openSaveModal() {
    $('#save-flow-name').val(state.currentFlowName);
    showModal('save-flow-modal');
    $('#save-flow-name').focus().select();
}
$('#btn-confirm-save').on('click', function () {
    const name = $('#save-flow-name').val().trim();
    if (!name) return;
    API.saveFlow(name).then(res => {
        state.currentFlowName = res.name;
        hideModals();
        import('./logs.js').then(m => m.addLog(`Project saved successfully as "${res.name}"`));
    }).catch(err => alert('Failed to save: ' + (err.responseJSON?.message || 'Unknown')));
});
$('#save-flow-name').on('keypress', e => { if (e.which === 13) $('#btn-confirm-save').click(); });

// --- Load Modal ---
export function openLoadModal() {
    API.listFlows().then(res => {
        const flows = res.flows || [];
        const list = $('#load-flow-list').empty();
        if (!flows.length) {
            list.html('<div style="color:var(--text-muted);font-size:0.85rem;text-align:center;padding:20px;">No saved flows found.</div>');
        } else {
            flows.forEach(f => {
                const isCur = (f === state.currentFlowName);
                const item = $(`
                    <div class="flow-list-item" data-name="${f}">
                        <div class="flow-item-info">
                            <span class="material-icons-round flow-item-icon">${isCur ? 'stars' : 'article'}</span>
                            <span class="flow-item-name">${f} ${isCur ? '<span style="color:var(--primary);font-size:0.75rem;font-weight:600;margin-left:4px;">(active)</span>' : ''}</span>
                        </div>
                        <button class="flow-item-action">Load</button>
                    </div>
                `);
                item.on('click', () => {
                    API.loadFlow(f).then(loadRes => {
                        state.currentFlowName = loadRes.name;
                        if (typeof loadFlow === 'function') loadFlow();
                        hideModals();
                        import('./logs.js').then(m => m.addLog(`Loaded saved project flow: ${loadRes.name}`));
                    }).catch(err => alert('Failed to load: ' + (err.responseJSON?.message || 'Unknown')));
                });
                list.append(item);
            });
        }
        showModal('load-flow-modal');
    });
}

// --- Info Modal ---
export function openInfoModal() { showModal('mode-info-modal'); }

// Modal close handlers
$('.modal-cancel').on('click', hideModals);
$(document).on('click', '.modal-overlay', function (e) {
    if (e.target === this || $(e.target).closest('.modal-close').length) hideModals();
});

// --- Radial Menu ---
export function showRadialMenu(pageX, pageY) {
    $('#radial-search-popup').hide();
    const menu = $('#radial-menu');
    menu.css({ left: pageX + 'px', top: pageY + 'px', display: 'block' });
    setTimeout(() => menu.addClass('active'), 10);
}
function hideRadialMenu() {
    const m = $('#radial-menu');
    m.removeClass('active');
    setTimeout(() => { if (!m.hasClass('active')) m.hide(); }, 300);
}

// --- Node Radial Menu ---
export function showNodeRadial(pageX, pageY, nodeId) {
    state.activeNodeRadialId = nodeId;
    hideRadialMenu();
    $('#radial-search-popup').hide();
    const $el = $(`.node-card[data-id="${nodeId}"]`);
    const hasRep = $el.find('.timer-toggle-label').css('display') !== 'none';
    const hasTim = $el.find('.timer-interval-wrapper').css('display') !== 'none';
    const hasFrc = $el.find('.force-trigger-label').css('display') !== 'none';
    const hasWai = $el.find('.wait-complete-label').css('display') !== 'none';

    $('#node-radial-repeat-label').text(hasRep ? 'Remove Repeat' : 'Add Repeat');
    $('#node-radial-timer-label').text(hasTim ? 'Remove Timer' : 'Add Timer');
    $('#node-radial-force-label').text(hasFrc ? 'Remove Force' : 'Add Force');
    $('#node-radial-wait-label').text(hasWai ? 'Remove Wait' : 'Add Wait Complete');

    const menu = $('#node-radial-menu');
    menu.css({ left: pageX + 'px', top: pageY + 'px', display: 'block' });
    setTimeout(() => menu.addClass('active'), 10);
}
function hideNodeRadial() {
    const m = $('#node-radial-menu');
    m.removeClass('active');
    setTimeout(() => { if (!m.hasClass('active')) m.css('display', 'none'); }, 200);
}

// Hide on outside click
$(document).on('mousedown', function (e) {
    if (!$(e.target).closest('#radial-menu, #radial-search-popup, #node-radial-menu').length) {
        hideRadialMenu();
        $('#radial-search-popup').hide();
        hideNodeRadial();
    }
});

// Radial menu item clicks
$(document).on('click', '.radial-menu-item', async function (e) {
    e.stopPropagation();
    const action = $(this).attr('data-action');
    if (action && action.startsWith('toggle-')) return; // node radial
    hideRadialMenu();

    if (action === 'add-node') {
        const m = $('#radial-menu');
        const search = $('#radial-search-popup');
        search.css({ left: m.css('left'), top: m.css('top'), display: 'flex' });
        const input = $('#radial-search-input').val('').focus();
        renderRadialSearch('');
    } else if (action === 'save') { $('#btn-save').click(); }
    else if (action === 'load') { $('#btn-load').click(); }
    else if (action === 'clear') { $('#btn-clear').click(); }
    else if (action === 'pause') { $('#btn-pause').click(); }
});

// Node radial menu clicks
$(document).on('click', '#node-radial-menu .radial-menu-item', function (e) {
    e.stopPropagation();
    const action = $(this).attr('data-action');
    hideNodeRadial();
    if (!state.activeNodeRadialId) return;

    const nid = state.activeNodeRadialId;
    const $el = $(`.node-card[data-id="${nid}"]`);

    const toggle = (name, visName, logName) => {
        const has = $el.find(`.${visName}`).css('display') !== 'none';
        const next = !has;
        if (!next) API.updateNodeProp(nid, name, false);
        API.updateNodeProp(nid, visName + '_visible', next).then(() => {
            if (typeof loadFlow === 'function') loadFlow();
            import('./logs.js').then(m => m.addLog(`${logName} option ${next ? 'added to' : 'removed from'} Node ${nid}`));
        });
    };

    if (action === 'toggle-repeat') toggle('loop_enabled', 'timer-toggle-label', 'Repeat');
    else if (action === 'toggle-timer') toggle(null, 'timer-interval-wrapper', 'Timer');
    else if (action === 'toggle-force') toggle('force_trigger', 'force-trigger-label', 'Force Trigger');
    else if (action === 'toggle-wait') toggle('wait_until_complete', 'wait-complete-label', 'Wait Complete');
});

// --- Radial Search ---
function renderRadialSearch(query) {
    const container = $('#radial-search-results').empty();
    const filtered = [];
    const q = query.toLowerCase().trim();

    Object.keys(state.nodeTemplates).forEach(id => {
        const tpl = state.nodeTemplates[id];
        if (!q || tpl.title.toLowerCase().includes(q)) filtered.push(tpl);
    });

    filtered.forEach((tpl, idx) => {
        const cat = getNodeCategory(tpl.title);
        container.append($(`
            <div class="radial-search-item ${idx === 0 ? 'selected' : ''}" data-identifier="${tpl.identifier}">
                <span class="item-title">${tpl.title}</span>
                <span class="item-category">${cat}</span>
            </div>
        `));
    });

    if (!filtered.length) {
        container.append('<div style="font-size:0.7rem;color:var(--text-muted);text-align:center;padding:8px;">No nodes found</div>');
    }
}

$('#radial-search-input').on('input', function () { renderRadialSearch($(this).val()); });

$(document).on('click', '.radial-search-item', function (e) {
    e.stopPropagation();
    const id = $(this).attr('data-identifier');
    API.createNode(id, state.radialX, state.radialY).then(() => {
        if (typeof loadFlow === 'function') loadFlow();
    });
    $('#radial-search-popup').hide();
});

$(document).on('keydown', '#radial-search-input', function (e) {
    if (e.key === 'Enter') {
        const sel = $('#radial-search-results .radial-search-item.selected');
        if (sel.length) {
            API.createNode(sel.attr('data-identifier'), state.radialX, state.radialY).then(() => {
                if (typeof loadFlow === 'function') loadFlow();
            });
            $('#radial-search-popup').hide();
        }
    } else if (e.key === 'Escape') {
        $('#radial-search-popup').hide();
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        const items = $('#radial-search-results .radial-search-item');
        if (!items.length) return;
        const cur = items.filter('.selected');
        let idx = 0;
        if (cur.length) { idx = items.index(cur); cur.removeClass('selected'); }
        const next = e.key === 'ArrowDown' ? (idx + 1) % items.length : (idx - 1 + items.length) % items.length;
        items.eq(next).addClass('selected')[0].scrollIntoView({ block: 'nearest' });
        e.preventDefault();
    }
});

$(document).on('mousedown keydown keyup', '#radial-search-input', e => e.stopPropagation());
