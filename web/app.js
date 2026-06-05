(() => {
  const NODE_WIDTH = 280;
  const HEADER_HEIGHT = 58;
  const ROW_HEIGHT = 28;
  const NODE_PADDING_ROWS = 1;
  const MIN_BEND_DISTANCE = 60;
  const BEND_FACTOR = 0.45;
  const MIN_ZOOM_SCALE = 0.35;
  const MAX_ZOOM_SCALE = 2.2;
  const RUN_STEP_DELAY_MS = 220;
  const RUN_FINAL_DELAY_MS = 400;

  const state = {
    project: null,
    flows: [],
    selectedFlowIndex: 0,
    nodes: [],
    connections: [],
    selectedNodeIndex: null,
    connectMode: false,
    pendingConnectionSource: null,
    view: { x: 60, y: 40, scale: 1 },
    rafQueued: false,
    pan: null,
    drag: null,
  };

  const $surface = $('#graph-surface');
  const $viewport = $('#graph-viewport');
  const $nodesLayer = $('#nodes-layer');
  const $connectionsLayer = $('#connections-layer');
  const $flowSelect = $('#flow-select');
  const $status = $('#status');
  const $runOutput = $('#run-output');
  const $connectModeBtn = $('#connect-mode');

  function setStatus(msg) {
    $status.text(msg);
  }

  function writeRunOutput(lines) {
    $runOutput.text(lines.join('\n'));
  }

  function normalizeFlows(data) {
    if (!data || typeof data !== 'object') return [];
    if (data.scripts && typeof data.scripts === 'object') {
      return Object.entries(data.scripts).map(([name, value]) => ({ title: name, flow: value.flow || {} }));
    }
    if (Array.isArray(data.flows)) {
      return data.flows.map((flow, i) => ({ title: `Flow ${i + 1}`, flow }));
    }
    if (data.flows && typeof data.flows === 'object') {
      return Object.entries(data.flows).map(([title, flow]) => ({ title, flow }));
    }
    return [];
  }

  function parseCoord(value) {
    const num = Number(value);
    return Number.isFinite(num) ? num : null;
  }

  function positionFromUnknown(raw) {
    if (!raw) return null;
    if (Array.isArray(raw) && raw.length >= 2) {
      const x = parseCoord(raw[0]);
      const y = parseCoord(raw[1]);
      if (x !== null && y !== null) return { x, y };
    }
    if (typeof raw === 'object') {
      const x = parseCoord(raw.x ?? raw[0]);
      const y = parseCoord(raw.y ?? raw[1]);
      if (x !== null && y !== null) return { x, y };
    }
    if (typeof raw === 'string') {
      const parts = raw.split(/[\s,;]+/).map(Number).filter(Number.isFinite);
      if (parts.length >= 2) return { x: parts[0], y: parts[1] };
    }
    return null;
  }

  function extractNodePosition(node, index) {
    const fallback = { x: 80 + (index % 4) * 350, y: 80 + Math.floor(index / 4) * 220 };
    const addData = node['additional data'] || {};
    const candidates = [
      node.position,
      node.pos,
      [node.x, node.y],
      addData.position,
      addData.pos,
      [addData.x, addData.y],
      [addData['pos x'], addData['pos y']],
      addData['main widget pos'],
      addData['display pos'],
    ];
    for (const candidate of candidates) {
      const found = positionFromUnknown(candidate);
      if (found) return found;
    }
    return fallback;
  }

  function normalizePortLabel(port, idx, fallbackPrefix) {
    if (!port) return `${fallbackPrefix} ${idx}`;
    const label = String(port.label || port.label_str || '').trim();
    return label || `${fallbackPrefix} ${idx}`;
  }

  function buildGraph(flow) {
    const nodes = (flow.nodes || []).map((node, i) => {
      const inputs = Array.isArray(node.inputs) ? node.inputs : [];
      const outputs = Array.isArray(node.outputs) ? node.outputs : [];
      const position = extractNodePosition(node, i);
      return {
        index: i,
        raw: node,
        title: node.title || node.identifier || `Node ${i + 1}`,
        subtitle: node.identifier || '',
        inputs,
        outputs,
        x: position.x,
        y: position.y,
      };
    });

    const connections = (flow.connections || []).map((c) => ({
      fromNode: Number(c['parent node index']),
      fromPort: Number(c['output port index']),
      toNode: Number(c['connected node']),
      toPort: Number(c['connected input port index']),
    })).filter((c) =>
      Number.isInteger(c.fromNode) && Number.isInteger(c.fromPort) &&
      Number.isInteger(c.toNode) && Number.isInteger(c.toPort)
    );

    return { nodes, connections };
  }

  function nodeHeight(node) {
    return HEADER_HEIGHT + (Math.max(node.inputs.length, node.outputs.length) + NODE_PADDING_ROWS) * ROW_HEIGHT;
  }

  function edgeColor(outPortType) {
    return outPortType === 'exec' ? 'var(--edge-exec)' : 'var(--edge-data)';
  }

  function updateHeaderStats() {
    $('#node-count').text(`Nodes: ${state.nodes.length}`);
    $('#connection-count').text(`Connections: ${state.connections.length}`);
  }

  function portTypeForNode(node, isOutput, portIndex) {
    const list = isOutput ? node.outputs : node.inputs;
    return list[portIndex]?.type_ || 'data';
  }

  function renderNodes() {
    $nodesLayer.empty();

    for (const node of state.nodes) {
      const rows = Math.max(node.inputs.length, node.outputs.length, 1);
      const $article = $('<article class="node"></article>')
        .attr('data-node-index', node.index)
        .css({ transform: `translate(${node.x}px, ${node.y}px)`, height: `${nodeHeight(node)}px` });

      if (node.index === state.selectedNodeIndex) $article.addClass('selected');

      const $header = $('<div class="node-header"></div>');
      $('<div></div>').text(node.title).appendTo($header);
      $('<div class="node-subtitle"></div>').text(node.subtitle).appendTo($header);
      $article.append($header);

      const $ports = $('<div class="ports"></div>');
      const $inputs = $('<div class="port-col inputs"></div>');
      const $outputs = $('<div class="port-col outputs"></div>');

      for (let i = 0; i < rows; i += 1) {
        const inp = node.inputs[i];
        const out = node.outputs[i];

        const $inRow = $('<div class="port-row"></div>').attr({ 'data-node': node.index, 'data-input': i });
        if (state.connectMode && inp) $inRow.addClass('selectable');
        if (inp) {
          $('<span class="port-dot"></span>').addClass(inp.type_ === 'exec' ? 'exec' : 'data').appendTo($inRow);
          $('<span class="port-name"></span>').text(normalizePortLabel(inp, i, 'In')).appendTo($inRow);
        }
        $inputs.append($inRow);

        const $outRow = $('<div class="port-row"></div>').attr({ 'data-node': node.index, 'data-output': i });
        if (state.connectMode && out) $outRow.addClass('selectable');
        if (state.pendingConnectionSource && state.pendingConnectionSource.nodeIndex === node.index && state.pendingConnectionSource.portIndex === i) {
          $outRow.addClass('pending');
        }
        if (out) {
          $('<span class="port-name"></span>').text(normalizePortLabel(out, i, 'Out')).appendTo($outRow);
          $('<span class="port-dot"></span>').addClass(out.type_ === 'exec' ? 'exec' : 'data').appendTo($outRow);
        }
        $outputs.append($outRow);
      }

      $ports.append($inputs, $outputs);
      $article.append($ports);
      $nodesLayer.append($article);
    }

    updateHeaderStats();
  }

  function scheduleConnectionRender() {
    if (state.rafQueued) return;
    state.rafQueued = true;
    requestAnimationFrame(() => {
      state.rafQueued = false;
      renderConnections();
    });
  }

  function renderConnections() {
    const svgEl = $connectionsLayer[0];
    while (svgEl.firstChild) svgEl.removeChild(svgEl.firstChild);

    for (const c of state.connections) {
      const fromNode = state.nodes[c.fromNode];
      const toNode = state.nodes[c.toNode];
      if (!fromNode || !toNode) continue;
      if (!fromNode.outputs[c.fromPort] || !toNode.inputs[c.toPort]) continue;

      const outPort = fromNode.outputs[c.fromPort];
      const y1 = fromNode.y + HEADER_HEIGHT + ROW_HEIGHT * (c.fromPort + 0.5);
      const x1 = fromNode.x + NODE_WIDTH;
      const y2 = toNode.y + HEADER_HEIGHT + ROW_HEIGHT * (c.toPort + 0.5);
      const x2 = toNode.x;
      const bend = Math.max(MIN_BEND_DISTANCE, Math.abs(x2 - x1) * BEND_FACTOR);
      const d = `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`;

      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', d);
      path.style.stroke = edgeColor(outPort.type_);
      svgEl.appendChild(path);
    }

    updateHeaderStats();
  }

  function applyViewTransform() {
    const { x, y, scale } = state.view;
    $viewport.css('transform', `translate(${x}px, ${y}px) scale(${scale})`);
  }

  function reindexNodes() {
    state.nodes.forEach((n, i) => { n.index = i; });
  }

  function commitCurrentFlowData() {
    const flow = state.flows[state.selectedFlowIndex]?.flow;
    if (!flow) return;

    flow.nodes = state.nodes.map((node) => {
      const additionalData = { ...(node.raw['additional data'] || {}) };
      additionalData.position = [node.x, node.y];

      return {
        ...node.raw,
        title: node.title,
        identifier: node.subtitle || node.raw.identifier || node.title,
        inputs: node.inputs,
        outputs: node.outputs,
        'additional data': additionalData,
      };
    });

    flow.connections = state.connections.map((c) => ({
      'parent node index': c.fromNode,
      'output port index': c.fromPort,
      'connected node': c.toNode,
      'connected input port index': c.toPort,
    }));
  }

  function renderFlow(index) {
    commitCurrentFlowData();

    const selected = state.flows[index];
    if (!selected) {
      state.nodes = [];
      state.connections = [];
      state.selectedNodeIndex = null;
      renderNodes();
      renderConnections();
      setStatus('No flow available in project data.');
      return;
    }

    const graph = buildGraph(selected.flow);
    state.selectedFlowIndex = index;
    state.nodes = graph.nodes;
    state.connections = graph.connections;
    state.selectedNodeIndex = null;
    state.pendingConnectionSource = null;

    renderNodes();
    renderConnections();
    setStatus(`Loaded flow "${selected.title}".`);
  }

  function populateFlowSelector() {
    $flowSelect.empty();

    state.flows.forEach((f, i) => {
      const $option = $('<option></option>').attr('value', i).text(f.title);
      $flowSelect.append($option);
    });

    if (state.flows.length === 0) $flowSelect.append('<option value="0">No flows</option>');
    $flowSelect.val(String(state.selectedFlowIndex));
  }

  function loadProjectFromObject(obj) {
    state.project = obj;
    state.flows = normalizeFlows(obj);
    state.selectedFlowIndex = 0;
    populateFlowSelector();
    renderFlow(0);
  }

  function handleProjectFile(file) {
    if (!file) return;
    const reader = new FileReader();

    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result);
        loadProjectFromObject(parsed);
      } catch (error) {
        setStatus(`Failed to parse JSON: ${error.message}`);
      }
    };

    reader.onerror = () => {
      setStatus('Failed to read selected file.');
    };

    reader.readAsText(file);
  }

  function setConnectMode(enabled) {
    state.connectMode = enabled;
    state.pendingConnectionSource = null;
    $connectModeBtn.toggleClass('active', enabled);
    renderNodes();
  }

  function addNode() {
    const title = prompt('Node title:', `Node ${state.nodes.length + 1}`);
    if (title === null) return;
    const inCount = Math.max(0, Math.floor(Number(prompt('Number of inputs:', '1') || '1')));
    const outCount = Math.max(0, Math.floor(Number(prompt('Number of outputs:', '1') || '1')));

    const node = {
      index: state.nodes.length,
      raw: {
        identifier: title.replace(/\s+/g, '_'),
        title,
        inputs: [],
        outputs: [],
        'additional data': {},
      },
      title,
      subtitle: title.replace(/\s+/g, '_'),
      inputs: Array.from({ length: inCount }).map((_, i) => ({ label: `In ${i}`, type_: 'data' })),
      outputs: Array.from({ length: outCount }).map((_, i) => ({ label: `Out ${i}`, type_: 'data' })),
      x: 120 + (state.nodes.length % 4) * 320,
      y: 120 + Math.floor(state.nodes.length / 4) * 220,
    };

    state.nodes.push(node);
    state.selectedNodeIndex = node.index;
    commitCurrentFlowData();
    renderNodes();
    scheduleConnectionRender();
    setStatus(`Added node "${title}".`);
  }

  function deleteSelectedNode() {
    const idx = state.selectedNodeIndex;
    if (idx === null || !state.nodes[idx]) {
      setStatus('Select a node first to delete it.');
      return;
    }

    const removed = state.nodes[idx];
    state.nodes.splice(idx, 1);
    state.connections = state.connections
      .filter((c) => c.fromNode !== idx && c.toNode !== idx)
      .map((c) => ({
        ...c,
        fromNode: c.fromNode > idx ? c.fromNode - 1 : c.fromNode,
        toNode: c.toNode > idx ? c.toNode - 1 : c.toNode,
      }));

    reindexNodes();
    state.selectedNodeIndex = null;
    commitCurrentFlowData();
    renderNodes();
    scheduleConnectionRender();
    setStatus(`Deleted node "${removed.title}".`);
  }

  function connectionExists(candidate) {
    return state.connections.some((c) =>
      c.fromNode === candidate.fromNode && c.fromPort === candidate.fromPort &&
      c.toNode === candidate.toNode && c.toPort === candidate.toPort
    );
  }

  function tryCreateConnection(targetNodeIndex, targetPortIndex) {
    if (!state.pendingConnectionSource) return;
    const src = state.pendingConnectionSource;
    const sourceNode = state.nodes[src.nodeIndex];
    const targetNode = state.nodes[targetNodeIndex];
    if (!sourceNode || !targetNode) return;
    if (src.nodeIndex === targetNodeIndex) return;

    const fromType = portTypeForNode(sourceNode, true, src.portIndex);
    const toType = portTypeForNode(targetNode, false, targetPortIndex);
    if (fromType !== toType) {
      setStatus(`Port type mismatch: ${fromType} -> ${toType}.`);
      state.pendingConnectionSource = null;
      renderNodes();
      return;
    }

    const conn = { fromNode: src.nodeIndex, fromPort: src.portIndex, toNode: targetNodeIndex, toPort: targetPortIndex };
    if (!connectionExists(conn)) {
      state.connections.push(conn);
      commitCurrentFlowData();
      scheduleConnectionRender();
      setStatus(`Connected ${sourceNode.title} -> ${targetNode.title}.`);
    }

    state.pendingConnectionSource = null;
    renderNodes();
  }

  function exportProject() {
    if (!state.project) {
      setStatus('No project loaded.');
      return;
    }

    commitCurrentFlowData();
    const blob = new Blob([JSON.stringify(state.project, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ryvencore-project-edited.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setStatus('Exported edited project JSON.');
  }

  function animateRun(order) {
    const $nodes = $('.node');
    $nodes.removeClass('running');

    order.forEach((idx, i) => {
      setTimeout(() => {
        $nodes.removeClass('running');
        $(`.node[data-node-index="${idx}"]`).addClass('running');
      }, i * RUN_STEP_DELAY_MS);
    });

    setTimeout(() => {
      $nodes.removeClass('running');
    }, order.length * RUN_STEP_DELAY_MS + RUN_FINAL_DELAY_MS);
  }

  function runFlowSimulation() {
    if (state.nodes.length === 0) {
      setStatus('Load or create nodes before running.');
      return;
    }

    const indegree = Array(state.nodes.length).fill(0);
    const next = Array.from({ length: state.nodes.length }, () => []);

    for (const c of state.connections) {
      if (!state.nodes[c.fromNode] || !state.nodes[c.toNode]) continue;
      indegree[c.toNode] += 1;
      next[c.fromNode].push(c.toNode);
    }

    const queue = [];
    indegree.forEach((d, i) => { if (d === 0) queue.push(i); });

    const order = [];
    while (queue.length) {
      const nodeIndex = queue.shift();
      order.push(nodeIndex);
      for (const succ of next[nodeIndex]) {
        indegree[succ] -= 1;
        if (indegree[succ] === 0) queue.push(succ);
      }
    }

    const hasCycle = order.length !== state.nodes.length;
    const trace = [];
    trace.push(`Flow: ${state.flows[state.selectedFlowIndex]?.title || 'Untitled'}`);
    trace.push(`Nodes: ${state.nodes.length}, Connections: ${state.connections.length}`);
    trace.push(`Mode: browser simulation`);

    if (hasCycle) {
      trace.push('Cycle detected: fallback execution order applied for remaining nodes.');
      for (let i = 0; i < state.nodes.length; i += 1) {
        if (!order.includes(i)) order.push(i);
      }
    }

    for (let step = 0; step < order.length; step += 1) {
      const nodeIndex = order[step];
      const node = state.nodes[nodeIndex];
      const outCount = state.connections.filter((c) => c.fromNode === nodeIndex).length;
      trace.push(`${step + 1}. ${node.title} (${node.subtitle}) -> ${outCount} outgoing`);
    }

    writeRunOutput(trace);
    animateRun(order);
    setStatus(`Run complete (${order.length} nodes simulated${hasCycle ? ', cycle detected' : ''}).`);
  }

  function bindPanAndZoom() {
    $surface.on('wheel', (event) => {
      event.preventDefault();
      const e = event.originalEvent;
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      const next = Math.min(MAX_ZOOM_SCALE, Math.max(MIN_ZOOM_SCALE, state.view.scale + delta));
      if (next === state.view.scale) return;

      const rect = $surface[0].getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      const wx = (cx - state.view.x) / state.view.scale;
      const wy = (cy - state.view.y) / state.view.scale;

      state.view.scale = next;
      state.view.x = cx - wx * next;
      state.view.y = cy - wy * next;
      applyViewTransform();
    });

    $surface.on('mousedown', (event) => {
      if ($(event.target).closest('.node').length) return;
      state.pan = {
        x: event.clientX,
        y: event.clientY,
        startX: state.view.x,
        startY: state.view.y,
      };
    });

    $(document).on('mousemove', (event) => {
      if (state.pan) {
        const dx = event.clientX - state.pan.x;
        const dy = event.clientY - state.pan.y;
        state.view.x = state.pan.startX + dx;
        state.view.y = state.pan.startY + dy;
        applyViewTransform();
      }

      if (state.drag) {
        const scaledDx = (event.clientX - state.drag.startX) / state.view.scale;
        const scaledDy = (event.clientY - state.drag.startY) / state.view.scale;
        const node = state.nodes[state.drag.nodeIndex];
        if (!node) return;

        node.x = state.drag.nodeStartX + scaledDx;
        node.y = state.drag.nodeStartY + scaledDy;
        state.drag.$node.css('transform', `translate(${node.x}px, ${node.y}px)`);
        commitCurrentFlowData();
        scheduleConnectionRender();
      }
    });

    $(document).on('mouseup', () => {
      state.pan = null;
      state.drag = null;
    });

    $nodesLayer.on('mousedown', '.node-header', function onNodeMouseDown(event) {
      const $node = $(this).closest('.node');
      const nodeIndex = Number($node.attr('data-node-index'));
      const node = state.nodes[nodeIndex];
      if (!node) return;

      event.stopPropagation();
      state.drag = {
        nodeIndex,
        $node,
        startX: event.clientX,
        startY: event.clientY,
        nodeStartX: node.x,
        nodeStartY: node.y,
      };
    });
  }

  function bindUi() {
    $('#project-file').on('change', (event) => {
      const [file] = event.target.files;
      handleProjectFile(file);
    });

    $flowSelect.on('change', () => {
      const idx = Number($flowSelect.val() || 0);
      renderFlow(idx);
    });

    $('#add-node').on('click', addNode);
    $('#delete-node').on('click', deleteSelectedNode);
    $('#connect-mode').on('click', () => setConnectMode(!state.connectMode));
    $('#export-json').on('click', exportProject);
    $('#run-flow').on('click', runFlowSimulation);

    $nodesLayer.on('click', '.node', function onNodeClick(event) {
      if ($(event.target).closest('.port-row').length) return;
      const nodeIndex = Number($(this).attr('data-node-index'));
      state.selectedNodeIndex = Number.isInteger(nodeIndex) ? nodeIndex : null;
      renderNodes();
    });

    $nodesLayer.on('click', '.port-col.outputs .port-row.selectable', function onOutputPortClick() {
      const nodeIndex = Number($(this).attr('data-node'));
      const portIndex = Number($(this).attr('data-output'));
      if (!Number.isInteger(nodeIndex) || !Number.isInteger(portIndex)) return;

      if (!state.nodes[nodeIndex]?.outputs[portIndex]) return;
      state.pendingConnectionSource = { nodeIndex, portIndex };
      renderNodes();
      setStatus('Select a target input port to complete the connection.');
    });

    $nodesLayer.on('click', '.port-col.inputs .port-row.selectable', function onInputPortClick() {
      const nodeIndex = Number($(this).attr('data-node'));
      const portIndex = Number($(this).attr('data-input'));
      if (!Number.isInteger(nodeIndex) || !Number.isInteger(portIndex)) return;
      if (!state.nodes[nodeIndex]?.inputs[portIndex]) return;
      tryCreateConnection(nodeIndex, portIndex);
    });
  }

  function init() {
    bindUi();
    bindPanAndZoom();
    applyViewTransform();
  }

  init();
})();
