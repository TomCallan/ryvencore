/**
 * Canvas viewport — pan, zoom, transform, and HUD controls.
 */
import { state, applyTransform, setZoom } from './state.js';

export function init() {
    const viewport = $('#canvas-viewport');

    // Panning
    viewport.on('mousedown', function (e) {
        if ($(e.target).closest('.node-card, .port-handle').length > 0) return;
        state.isPanning = true;
        state.panStartX = e.clientX - state.panX;
        state.panStartY = e.clientY - state.panY;
        viewport.css('cursor', 'grabbing');

        $(document).on('mousemove.pan', ev => {
            if (!state.isPanning) return;
            state.panX = ev.clientX - state.panStartX;
            state.panY = ev.clientY - state.panStartY;
            applyTransform();
        }).on('mouseup.pan', () => {
            state.isPanning = false;
            viewport.css('cursor', 'grab');
            $(document).off('.pan');
        });
    });

    // Zoom via mousewheel
    viewport.on('wheel', function (e) {
        e.preventDefault();
        const delta = e.originalEvent.deltaY;
        const factor = delta < 0 ? 1.1 : 0.9;

        const offset = viewport.offset();
        const mx = e.clientX - offset.left;
        const my = e.clientY - offset.top;
        const cx = (mx - state.panX) / state.zoom;
        const cy = (my - state.panY) / state.zoom;

        const newZoom = Math.max(state.minZoom, Math.min(state.maxZoom, state.zoom * factor));
        state.panX = mx - cx * newZoom;
        state.panY = my - cy * newZoom;
        state.zoom = newZoom;
        applyTransform();
    });

    // Deselect on canvas click
    viewport.on('click', function (e) {
        if ($(e.target).closest('.node-card').length === 0) {
            $('.node-card').removeClass('selected');
            state.selectedNodeId = null;
        }
    });

    // Drag-and-drop from sidebar
    viewport.on('dragover', e => { e.preventDefault(); e.originalEvent.dataTransfer.dropEffect = 'copy'; });
    viewport.on('drop', async function (e) {
        e.preventDefault();
        const identifier = e.originalEvent.dataTransfer.getData('text/plain');
        if (!identifier) return;
        const offset = viewport.offset();
        const x = (e.originalEvent.clientX - offset.left - state.panX) / state.zoom;
        const y = (e.originalEvent.clientY - offset.top - state.panY) / state.zoom;
        const { createNode } = await import('./api.js');
        createNode(identifier, x, y);
        const { addLog } = await import('./logs.js');
        addLog(`Dropped new node: ${identifier}`);
    });

    // HUD buttons
    $('#btn-zoom-in').on('click', () => setZoom(state.zoom + 0.1));
    $('#btn-zoom-out').on('click', () => setZoom(state.zoom - 0.1));
    $('#btn-zoom-reset').on('click', () => {
        state.zoom = 1.0; state.panX = 100; state.panY = 100;
        applyTransform();
    });
}

export function canvasCoords(clientX, clientY) {
    const offset = $('#canvas-viewport').offset();
    return {
        x: (clientX - offset.left - state.panX) / state.zoom,
        y: (clientY - offset.top - state.panY) / state.zoom,
    };
}

export function pageCoordsFromCanvas(canvasX, canvasY) {
    const offset = $('#canvas-viewport').offset();
    return {
        x: canvasX * state.zoom + state.panX + offset.left,
        y: canvasY * state.zoom + state.panY + offset.top,
    };
}
