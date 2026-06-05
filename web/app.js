(() => {
  const NODE_WIDTH = 280;
  const HEADER_HEIGHT = 58;
  const ROW_HEIGHT = 28;
  const NODE_PADDING_ROWS = 1;
  const MIN_BEND_DISTANCE = 60;
  const BEND_FACTOR = 0.45;
  const MIN_ZOOM_SCALE = 0.35;
  const MAX_ZOOM_SCALE = 2.2;

  const state = {
    project: null,
    flows: [],
    selectedFlowIndex: 0,
    nodes: [],
    connections: [],
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

  function setStatus(msg) {
    $status.text(msg);
  }

  function normalizeFlows(data) {
    if (!data || typeof data !== 'object') return [];
    if (data.scripts && typeof data.scripts === 'object') {
      return Object.entries(data.scripts).map(([name, value]) => ({
        title: name,
        flow: value.flow || {},
      }));
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
    const fallback = {
      x: 80 + (index % 4) * 350,
      y: 80 + Math.floor(index / 4) * 220,
    };

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

  function renderNodes() {
    $nodesLayer.empty();

    for (const node of state.nodes) {
      const rows = Math.max(node.inputs.length, node.outputs.length, 1);
      const inRows = [];
      const outRows = [];

      for (let i = 0; i < rows; i += 1) {
        const inp = node.inputs[i];
        const out = node.outputs[i];

        inRows.push(`
          <div class="port-row" data-node="${node.index}" data-input="${i}">
            ${inp ? `<span class="port-dot ${inp.type_ === 'exec' ? 'exec' : 'data'}"></span><span class="port-name">${normalizePortLabel(inp, i, 'In')}</span>` : ''}
          </div>`);

        outRows.push(`
          <div class="port-row" data-node="${node.index}" data-output="${i}">
            ${out ? `<span class="port-name">${normalizePortLabel(out, i, 'Out')}</span><span class="port-dot ${out.type_ === 'exec' ? 'exec' : 'data'}"></span>` : ''}
          </div>`);
      }

      const $node = $(
        `<article class="node" data-node-index="${node.index}" style="transform: translate(${node.x}px, ${node.y}px); height: ${nodeHeight(node)}px;">
          <div class="node-header">
            <div>${node.title}</div>
            <div class="node-subtitle">${node.subtitle}</div>
          </div>
          <div class="ports">
            <div class="port-col inputs">${inRows.join('')}</div>
            <div class="port-col outputs">${outRows.join('')}</div>
          </div>
        </article>`
      );

      $nodesLayer.append($node);
    }

    $('#node-count').text(`Nodes: ${state.nodes.length}`);
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
    while (svgEl.firstChild) {
      svgEl.removeChild(svgEl.firstChild);
    }

    for (const c of state.connections) {
      const fromNode = state.nodes[c.fromNode];
      const toNode = state.nodes[c.toNode];
      if (!fromNode || !toNode) continue;

      const outPort = fromNode.outputs[c.fromPort];
      const y1 = fromNode.y + HEADER_HEIGHT + ROW_HEIGHT * (c.fromPort + 0.5);
      const x1 = fromNode.x + NODE_WIDTH;
      const y2 = toNode.y + HEADER_HEIGHT + ROW_HEIGHT * (c.toPort + 0.5);
      const x2 = toNode.x;
      const bend = Math.max(MIN_BEND_DISTANCE, Math.abs(x2 - x1) * BEND_FACTOR);
      const d = `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`;

      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', d);
      path.style.stroke = edgeColor(outPort?.type_);
      svgEl.appendChild(path);
    }
    $('#connection-count').text(`Connections: ${state.connections.length}`);
  }

  function applyViewTransform() {
    const { x, y, scale } = state.view;
    $viewport.css('transform', `translate(${x}px, ${y}px) scale(${scale})`);
  }

  function renderFlow(index) {
    const selected = state.flows[index];
    if (!selected) {
      state.nodes = [];
      state.connections = [];
      renderNodes();
      renderConnections();
      setStatus('No flow available in project data.');
      return;
    }

    const graph = buildGraph(selected.flow);
    state.selectedFlowIndex = index;
    state.nodes = graph.nodes;
    state.connections = graph.connections;

    renderNodes();
    renderConnections();
    setStatus(`Loaded flow "${selected.title}".`);
  }

  function populateFlowSelector() {
    $flowSelect.empty();

    state.flows.forEach((f, i) => {
      const $option = $(`<option value="${i}"></option>`).text(f.title);
      $flowSelect.append($option);
    });

    if (state.flows.length === 0) {
      $flowSelect.append('<option value="0">No flows</option>');
    }

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
  }

  function init() {
    bindUi();
    bindPanAndZoom();
    applyViewTransform();
  }

  init();
})();
