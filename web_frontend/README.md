# ryvencore Studio — Frontend

The frontend is a single-page application built with vanilla JavaScript (ES modules), jQuery, and pure CSS. No build tools, no bundlers — the Python web server serves all files directly.

---

## Architecture

```
web_frontend/
├── index.html              # Entry point (modals, radial menus)
├── index.css               # Master stylesheet (imports all CSS modules)
├── css/
│   ├── variables.css       # Design tokens, reset, buttons
│   ├── layout.css          # Header, sidebar, canvas, HUD
│   ├── nodes.css           # Node cards, ports, handles, timers
│   ├── wires.css           # SVG connection curves
│   ├── modals.css          # Modal overlays, radial menus, search
│   └── logs.css            # Execution log footer panel
└── js/
    ├── app.js              # Entry point, flow orchestration, polling
    ├── state.js            # Global state (zoom, pan, selection)
    ├── api.js              # All backend API calls
    ├── canvas.js           # Pan, zoom, drag-and-drop
    ├── nodes.js            # Node rendering, dragging, resizing, ports
    ├── wires.js            # SVG wire drawing, connection management
    ├── sidebar.js          # Node library, search, categories
    ├── modals.js           # Save/load/info modals, radial menus
    ├── events.js           # Event handlers (buttons, inputs, toggles)
    ├── logs.js             # Log panel, polling
    └── plotting.js         # Client-side ChartRenderer (real-time plots)
```

## Module Responsibilities

### `js/state.js`
Single source of truth for all global UI state:
- `zoom`, `panX`, `panY` — canvas transform
- `selectedNodeId` — currently selected node
- `viewPaused` — whether canvas value updates are suspended
- `userInteracting` — flag to pause polling during drag/resize

### `js/api.js`
All HTTP calls to the Python backend. Every function returns a Promise (jQuery AJAX):

```javascript
import * as API from './api.js';
API.loadFlowState().then(data => renderNodes(data.nodes));
API.createNode('AddNode', 200, 150).then(loadFlow);
API.connectNodes(1, 0, 2, 0).then(loadFlow);
```

Key endpoints:
| Function | HTTP | Purpose |
|----------|------|---------|
| `loadFlowState()` | GET /api/flow | Full flow data (nodes, connections, mode) |
| `loadNodeTemplates()` | GET /api/nodes | Available node types |
| `createNode(id, x, y)` | POST /api/create_node | Add node to flow |
| `deleteNode(id)` | POST /api/delete_node | Remove node |
| `connectNodes(p, o, c, i)` | POST /api/connect | Add wire |
| `disconnectNodes(p, o, c, i)` | POST /api/disconnect | Remove wire |
| `updateInput(nid, idx, val)` | POST /api/update_input | Change input value |
| `triggerNode(nid)` | POST /api/trigger_node | Execute a node |
| `compileFlow()` | POST /api/compile | Run FlowCompiler |
| `saveFlow(name)` | POST /api/save | Save to saved_flows/ |
| `loadFlow(name)` | POST /api/load | Load saved project |

### `js/app.js`
Entry point. Exports two key functions:

| Function | API calls | DOM work | When used |
|----------|-----------|----------|-----------|
| `loadFlow()` | /api/flow | Full node + wire re-render | Structural changes (add/delete node, connect, mode, load, compile) |
| `refreshFlow()` | /api/flow | Value update + wire refresh only | Routine changes (input edit, toggle, trigger) |

Polling runs every 100ms when loops are active, 1000ms otherwise.

### `js/nodes.js`
Renders node cards, ports, dragging, and resizing. The `renderNodes()` function creates or updates `<div class="node-card">` elements from flow data. `updateFlowValues()` is a lightweight path that only updates displayed values.

**Custom node content** is handled per title:
- `Python REPL` — textarea for code input
- `Execute Button` — trigger button  
- `Plot` — uses ChartRenderer for real-time client-side chart
- `Advanced Plot` / `Orderbook Plot` — server-generated SVG

### `js/plotting.js`
Client-side chart renderer using native SVG. Supports:

```javascript
import { ChartRenderer } from './plotting.js';

const chart = new ChartRenderer(containerElement, { title: 'My Chart' });

// Single line series
chart.setData([{ data: [1, 2, 3, 4, 5], color: '#6366f1', fill: true }]);

// Multiple series
chart.setData([
    { data: [100, 200, 150], color: '#22c55e', label: 'Revenue' },
    { data: [80, 160, 120], color: '#ef4444', label: 'Costs' },
]);

// Bar chart
chart.setData([{ data: [30, 45, 20, 60], color: '#f59e0b', style: 'bar' }]);

// Indicators (overlay lines/flags)
chart.setIndicators([
    { kind: 'hline', y: 150, color: '#f59e0b', label: 'Target' },
    { kind: 'vline', x: 2, color: '#06b6d4', label: 'Event' },
    { kind: 'flag', x: 3, y: 180, color: '#a855f7', label: 'Peak' },
]);
```

The ChartRenderer auto-scales to its container via `ResizeObserver` and renders via `requestAnimationFrame` for smooth updates.

### `js/wires.js`
SVG Bezier curves between ports. Supports:
- Data wires (cyan, `--port-data`)
- Exec wires (purple, `--port-exec`)
- Virtual trigger wires (dashed, from Execute Buttons to targets)
- Mouse-drag wire drawing with real-time curve preview

### `js/modals.js`
Modal dialogs:
- **Save**: enter flow name, POST to /api/save
- **Load**: list saved flows from /api/list_flows, click to load
- **Info**: execution mode comparison help
- **Radial menus**: right-click canvas for quick actions (Add Node, Save, Load, Clear, Pause)
- **Node radial**: right-click node for option toggles (Repeat, Force, Wait)
- **Radial search**: type to filter and place nodes

---

## Responsive Layout

The header has three breakpoints:

| Width | Header Height | Button Labels | Logo Subtitle | Controls |
|-------|---------------|---------------|---------------|----------|
| >1100px | 56px | Visible | Visible | Full |
| 800-1100px | 56px | Hidden (icon only) | Visible | Compact |
| <800px | 48px | Hidden | Hidden | Minimal |

On overflow, the controls area scrolls horizontally with a hidden scrollbar.

---

## Adding a New Node

### 1. Python backend

Create a file in `nodes/`:

```python
import ryvencore as rc
from nodes.base import WebNode

class PowerNode(WebNode):
    title = 'Power'
    class Inputs:
        base = 2.0
        exponent = 3.0
    class Outputs:
        result = 0.0

    def update_event(self, inp=-1):
        self.Outputs.result = float(self.Inputs.base) ** float(self.Inputs.exponent)
```

The server auto-discovers nodes by scanning `nodes/*.py` on startup.

### 2. Categorization

Add the node title to `getNodeCategory()` in `js/nodes.js`:

```javascript
if (['Add', 'Subtract', 'Multiply', 'Divide', 'Array Calculator', 'Power'].includes(title)) return 'Math';
```

Add category colors in `css/nodes.css`:

```css
.node-card[data-category="Math"] { --cat-color: var(--cat-math); }
```

### 3. Custom UI (optional)

Add custom rendering in `renderCustomContent()` in `js/nodes.js`:

```javascript
} else if (n.title === 'Power') {
    if (!$el.find('.node-custom-content').length) {
        $el.find('.node-ports').after(`
            <div class="node-custom-content" style="padding:10px;text-align:center;">
                <small style="color:var(--text-muted);">Computes base^exponent</small>
            </div>
        `);
    }
}
```

---

## Adding a New Plot Type

### Backend (Python)

Add a static method to `SVGPlotter` in `plotting/engine.py`:

```python
@classmethod
def plot_heatmap(cls, data, ...):
    """SVG heatmap using rect elements."""
    ...
    return ''.join(svg)
```

### Frontend (JavaScript)

Use `ChartRenderer` in `js/plotting.js` for real-time plots, or display server-generated SVG in `.custom-svg-container`.

---

## CSS Theme

Overriding variables in `css/variables.css`:

```css
:root {
    --bg-darker: #0d0d12;
    --primary: #6366f1;
    --cat-math: #f59e0b;
    --port-data: #00bcd4;
    --port-exec: #e040fb;
}
```

Category colors get their own CSS variable per category:

```
Math → var(--cat-math)  #f59e0b  (amber)
String → var(--cat-string)  #06b6d4  (cyan)
Logic → var(--cat-logic)  #10b981  (green)
Utility → var(--cat-utility)  #3b82f6  (blue)
Exec → var(--cat-exec)  #a855f7  (purple)
Plotting → var(--cat-math)  (amber)
Database → var(--cat-string)  (cyan)
Neural Net → var(--cat-exec)  (purple)
```
