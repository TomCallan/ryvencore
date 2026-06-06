/**
 * Wire / connection rendering — SVG Bezier curves between node ports.
 * Handles virtual trigger wires from Execute Buttons.
 */
import { state } from './state.js';
import * as API from './api.js';

const resizeObserver = new ResizeObserver(() => refreshAll());

export function initObserver(nodeEl) {
    resizeObserver.observe(nodeEl[0]);
}

export function unobserve(nodeEl) {
    resizeObserver.unobserve(nodeEl[0]);
}

/** Compute local offset of a port handle within its node card */
function computePortLocal(handle) {
    const nodeCard = handle.closest('.node-card');
    if (!nodeCard.length) return { x: 0, y: 0 };
    const cardRect = nodeCard[0].getBoundingClientRect();
    const hRect = handle[0].getBoundingClientRect();
    if (!cardRect.width || !cardRect.height) return { x: 0, y: 0 };
    return {
        x: (hRect.left + hRect.width / 2 - cardRect.left) / state.zoom,
        y: (hRect.top + hRect.height / 2 - cardRect.top) / state.zoom,
    };
}

/** Cache port local coordinates on DOM attributes */
export function cachePortOffsets(nodeCard) {
    nodeCard.find('.port-handle').each(function () {
        const c = computePortLocal($(this));
        if (c.x > 0 || c.y > 0) {
            this.setAttribute('data-local-x', c.x);
            this.setAttribute('data-local-y', c.y);
        }
    });
}

function getPortLocal(handle) {
    let lx = parseFloat(handle.attr('data-local-x'));
    let ly = parseFloat(handle.attr('data-local-y'));
    if (isNaN(lx) || lx === 0 || isNaN(ly) || ly === 0) {
        const c = computePortLocal(handle);
        if (c.x > 0 || c.y > 0) handle.attr({ 'data-local-x': c.x, 'data-local-y': c.y });
        return c;
    }
    return { x: lx, y: ly };
}

function calcCurve(fromNodeId, outIdx, toNodeId, inIdx) {
    const outH = $(`.port-handle.output[data-node="${fromNodeId}"][data-index="${outIdx}"]`);
    const inH = $(`.port-handle.input[data-node="${toNodeId}"][data-index="${inIdx}"]`);
    if (!outH.length || !inH.length) return null;

    const pCard = $(`.node-card[data-id="${fromNodeId}"]`);
    const cCard = $(`.node-card[data-id="${toNodeId}"]`);
    const px = parseFloat(pCard.attr('data-x')) || 0;
    const py = parseFloat(pCard.attr('data-y')) || 0;
    const cx = parseFloat(cCard.attr('data-x')) || 0;
    const cy = parseFloat(cCard.attr('data-y')) || 0;

    const c1 = getPortLocal(outH);
    const c2 = getPortLocal(inH);
    const x1 = px + c1.x, y1 = py + c1.y;
    const x2 = cx + c2.x, y2 = cy + c2.y;
    const dx = Math.abs(x2 - x1) * 0.5;

    return {
        d: `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`,
        type: outH.attr('data-type'),
    };
}

function calcVirtualCurve(srcCard, tgtCard) {
    const sx = parseFloat(srcCard.attr('data-x')) || 0;
    const sy = parseFloat(srcCard.attr('data-y')) || 0;
    const sw = parseFloat(srcCard.attr('data-width')) || 200;
    const tx = parseFloat(tgtCard.attr('data-x')) || 0;
    const ty = parseFloat(tgtCard.attr('data-y')) || 0;
    const tw = parseFloat(tgtCard.attr('data-width')) || 200;

    const outH = srcCard.find('.port-handle.output[data-index="0"]');
    let x1, y1;
    if (outH.length) {
        const c = getPortLocal(outH);
        x1 = sx + c.x; y1 = sy + c.y;
    } else {
        x1 = sx + sw; y1 = sy + 30;
    }
    const x2 = tx + tw / 2;
    const y2 = ty + 15;
    const dx1 = Math.min(100, Math.max(30, Math.abs(x2 - x1) * 0.3));
    const dy2 = Math.min(100, Math.max(40, Math.abs(y2 - y1) * 0.3));
    return { d: `M ${x1} ${y1} C ${x1 + dx1} ${y1}, ${x2} ${y2 - dy2}, ${x2} ${y2}` };
}

export function renderConnections(connections) {
    const group = $('#wires-group').empty();

    connections.forEach(conn => {
        const path = calcCurve(conn.parent_node_id, conn.output_index, conn.connected_node_id, conn.input_index);
        if (!path) return;
        const wire = $(document.createElementNS('http://www.w3.org/2000/svg', 'path'))
            .attr('d', path.d)
            .attr('class', `wire-path ${path.type === 'exec' ? 'exec' : ''}`)
            .attr({ 'data-parent-node': conn.parent_node_id, 'data-parent-port': conn.output_index, 'data-dest-node': conn.connected_node_id, 'data-dest-port': conn.input_index })
            .attr('title', 'Right-click wire to delete');
        group.append(wire);
    });

    // Virtual trigger wires
    $('.node-card').each(function () {
        const src = $(this);
        const targetId = src.attr('data-target-node-id');
        if (!targetId) return;
        const tgt = $(`.node-card[data-id="${targetId}"]`);
        if (!tgt.length) return;
        const path = calcVirtualCurve(src, tgt);
        if (!path) return;
        const wire = $(document.createElementNS('http://www.w3.org/2000/svg', 'path'))
            .attr('d', path.d)
            .attr('class', 'wire-path virtual-trigger')
            .attr({ 'data-parent-node': src.attr('data-id'), 'data-dest-node': targetId })
            .attr('title', 'Right-click virtual wire to delete link');
        group.append(wire);
    });

    updateInputVisibility();
}

function updateInputVisibility() {
    $('.port-inline-input').show();
    $('.wire-path').each(function () {
        const destNode = $(this).attr('data-dest-node');
        const destPort = $(this).attr('data-dest-port');
        $(`.port-inline-input[data-node="${destNode}"][data-index="${destPort}"]`).hide();
    });
}

export function refreshAll() {
    $('.wire-path:not(.drawing)').each(function () {
        const $w = $(this);
        if ($w.hasClass('virtual-trigger')) {
            const src = $(`.node-card[data-id="${$w.attr('data-parent-node')}"]`);
            const tgt = $(`.node-card[data-id="${$w.attr('data-dest-node')}"]`);
            if (src.length && tgt.length) {
                const p = calcVirtualCurve(src, tgt);
                if (p) $w.attr('d', p.d);
            }
        } else {
            const p = calcCurve(
                $w.attr('data-parent-node'), $w.attr('data-parent-port'),
                $w.attr('data-dest-node'), $w.attr('data-dest-port'),
            );
            if (p) $w.attr('d', p.d);
        }
    });
}

// --- Connection drawing (drag from port) ---
export function startWireDraw(handle) {
    state.userInteracting = true;
    state.drawingConnection = {
        nodeId: handle.attr('data-node'),
        portIndex: handle.attr('data-index'),
        direction: handle.attr('data-direction'),
        type: handle.attr('data-type'),
        x: 0, y: 0,
    };

    const canvasOffset = $('#canvas-content').offset();
    const hOff = handle.offset();
    state.drawingConnection.x = (hOff.left - canvasOffset.left) / state.zoom + handle.outerWidth() / 2;
    state.drawingConnection.y = (hOff.top - canvasOffset.top) / state.zoom + handle.outerHeight() / 2;

    const wire = $('#active-wire');
    wire.attr('class', `wire-path drawing ${state.drawingConnection.type === 'exec' ? 'exec' : ''}`);
    wire.show();

    $(document).on('mousemove.wire', ev => {
        const curX = (ev.clientX - canvasOffset.left) / state.zoom;
        const curY = (ev.clientY - canvasOffset.top) / state.zoom;
        const { x, y, direction } = state.drawingConnection;

        let d;
        if (direction === 'output') {
            const dx = Math.abs(curX - x) * 0.5;
            d = `M ${x} ${y} C ${x + dx} ${y}, ${curX - dx} ${curY}, ${curX} ${curY}`;
        } else {
            const dx = Math.abs(x - curX) * 0.5;
            d = `M ${curX} ${curY} C ${curX + dx} ${curY}, ${x - dx} ${y}, ${x} ${y}`;
        }
        wire.attr('d', d);
    });
}

export function endWireDraw(ev) {
    $(document).off('.wire');
    $('#active-wire').hide();
    state.userInteracting = false;

    if (!state.drawingConnection) return;
    const dc = state.drawingConnection;
    state.drawingConnection = null;

    const target = $(document.elementFromPoint(ev.clientX, ev.clientY));
    const destHandle = target.closest('.port-handle');

    if (destHandle.length > 0) {
        const dId = destHandle.attr('data-node');
        const dIdx = destHandle.attr('data-index');
        const dDir = destHandle.attr('data-direction');
        const dType = destHandle.attr('data-type');

        if (dc.direction !== dDir && dc.nodeId !== dId && dc.type === dType) {
            const parentId = dc.direction === 'output' ? dc.nodeId : dId;
            const outIdx = dc.direction === 'output' ? dc.portIndex : dIdx;
            const destId = dc.direction === 'input' ? dc.nodeId : dId;
            const inpIdx = dc.direction === 'input' ? dc.portIndex : dIdx;

            API.connectNodes(parentId, outIdx, destId, inpIdx)
                .then(() => { if (typeof loadFlow === 'function') loadFlow(); })
                .catch(err => alert('Invalid Connection: ' + (err.responseJSON?.message || 'Unknown')));
        }
    } else if (dc.direction === 'output') {
        // Check for Execute Button → target node
        const srcCard = $(`.node-card[data-id="${dc.nodeId}"]`);
        if (srcCard.find('.node-title').text() === 'Execute Button') {
            const tgtCard = target.closest('.node-card');
            if (tgtCard.length && tgtCard.attr('data-id') !== dc.nodeId) {
                API.updateNodeProp(dc.nodeId, 'target_node_id', tgtCard.attr('data-id'))
                    .then(() => {
                        import('./logs.js').then(m => m.addLog(`Linked Execute Button ${dc.nodeId} to Node ${tgtCard.attr('data-id')}`));
                        if (typeof loadFlow === 'function') loadFlow();
                    });
            }
        }
    }
}
