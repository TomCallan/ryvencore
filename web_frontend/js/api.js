/**
 * API layer — all AJAX calls to the backend server.
 */

export function getJSON(url) {
    return $.getJSON(url);
}

export function postJSON(url, data) {
    return $.ajax({
        url, method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
    });
}

/** Load node type templates */
export function loadNodeTemplates() {
    return getJSON('/api/nodes');
}

/** Load current flow state */
export function loadFlowState() {
    return getJSON('/api/flow');
}

/** Create a new node */
export function createNode(identifier, x, y) {
    return postJSON('/api/create_node', { identifier, x, y });
}

/** Delete a node */
export function deleteNode(nodeId) {
    return postJSON('/api/delete_node', { node_id: nodeId });
}

/** Connect two ports */
export function connectNodes(parentId, outIdx, destId, inpIdx) {
    return postJSON('/api/connect', {
        parent_node_id: parentId, output_index: outIdx,
        connected_node_id: destId, input_index: inpIdx,
    });
}

/** Disconnect two ports */
export function disconnectNodes(parentId, outIdx, destId, inpIdx) {
    return postJSON('/api/disconnect', {
        parent_node_id: parentId, output_index: outIdx,
        connected_node_id: destId, input_index: inpIdx,
    });
}

/** Update an input value */
export function updateInput(nodeId, index, val) {
    return postJSON('/api/update_input', { node_id: nodeId, input_index: index, val });
}

/** Update a node property (loop, force_trigger, etc.) */
export function updateNodeProp(nodeId, name, val) {
    return postJSON('/api/update_node_property', { node_id: nodeId, name, val });
}

/** Move/resize a node */
export function moveNode(nodeId, x, y, width, height) {
    return postJSON('/api/move_node', { node_id: nodeId, x, y, width, height });
}

/** Trigger a node */
export function triggerNode(nodeId) {
    return postJSON('/api/trigger_node', { node_id: nodeId });
}

/** Set algorithm mode */
export function setAlgMode(mode) {
    return postJSON('/api/set_alg_mode', { mode });
}

/** Set paused state */
export function setPaused(paused) {
    return postJSON('/api/set_paused', { paused });
}

/** Compile flow */
export function compileFlow() {
    return postJSON('/api/compile', {});
}

/** Set compiled file */
export function setCompiledFile(filename) {
    return postJSON('/api/set_compiled_file', { filename });
}

/** Save flow */
export function saveFlow(name) {
    return postJSON('/api/save', { name });
}

/** Load a saved flow */
export function loadFlow(name) {
    return postJSON('/api/load', { name });
}

/** List saved flows */
export function listFlows() {
    return getJSON('/api/list_flows');
}

/** Clear flow */
export function clearFlow() {
    return $.post('/api/clear');
}

/** Get logs */
export function getLogs() {
    return getJSON('/api/logs');
}

/** Add a server-side log */
export function addServerLog(msg) {
    return postJSON('/api/add_log', { msg });
}

/** Clear logs */
export function clearLogs() {
    return postJSON('/api/clear_logs', {});
}

/** Add/delete/rename port */
export function addPort(nodeId, direction) {
    return postJSON('/api/add_port', { node_id: nodeId, direction });
}
export function deletePort(nodeId, direction, index) {
    return postJSON('/api/delete_port', { node_id: nodeId, direction, index });
}
export function renamePort(nodeId, direction, index, label) {
    return postJSON('/api/rename_port', { node_id: nodeId, direction, index, label });
}
