/**
 * Global application state — single source of truth.
 * Replaces scattered jQuery variables and DOM state queries.
 */

/** @type {{ zoom: number, panX: number, panY: number, selectedNodeId: string|null, isPanning: boolean, drawingConnection: object|null, viewPaused: boolean, currentFlowName: string, userInteracting: boolean }} */
export const state = {
    zoom: 1.0,
    minZoom: 0.25,
    maxZoom: 2.5,
    panX: 100,
    panY: 100,
    isPanning: false,
    panStartX: 0,
    panStartY: 0,

    drawingConnection: null,
    selectedNodeId: null,
    activeNodeRadialId: null,
    radialX: 0,
    radialY: 0,

    userInteracting: false,
    viewPaused: false,
    currentFlowName: 'flow_project',
    lastLogHash: '',

    nodeTemplates: {},
    pollTimeout: null,
};

export function setPan(x, y) {
    state.panX = x;
    state.panY = y;
    $('#canvas-content').css({ transform: `translate(${x}px, ${y}px) scale(${state.zoom})` });
    $('#zoom-level').text(`${Math.round(state.zoom * 100)}%`);
}

export function applyTransform() {
    $('#canvas-content').css({ transform: `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom})` });
    $('#zoom-level').text(`${Math.round(state.zoom * 100)}%`);
}

export function setZoom(z) {
    state.zoom = Math.max(state.minZoom, Math.min(state.maxZoom, z));
    applyTransform();
}
