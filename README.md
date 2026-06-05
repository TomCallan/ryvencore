# ryvencore Studio

<p align="center">
  <img src="./docs/img/logo.png" alt="ryvencore Studio" width="70%"/>
</p>

**ryvencore Studio** is an interactive, web-based visual scripting editor and flow-based execution environment built upon [ryvencore](https://github.com/leon-thomm/ryvencore). It allows users to build, run, save, and load node graphs in real-time through a premium dark-themed web interface, supporting both standard Data Flow and optimized propagation algorithms.

---

## Getting Started

### 1. Installation
Ensure you have the required dependencies. Since ryvencore is bundled, you can run the server directly.

### 2. Running the Web Server
Launch the server from the project root:
```bash
python run_web_server.py 8000
```
This initializes the backend API, loads all node definitions dynamically, and starts hosting the web frontend on [http://localhost:8000](http://localhost:8000).

---

## Project Structure & Node Directory

To make extending the platform simple and clean, all node definitions have been moved into a dedicated directory:

```
rycore/
├── nodes/                  # Dedicated Python Node Logic
│   ├── base.py             # WebNode base class and flow execution hooks
│   └── basic_nodes.py      # Python node definitions (Math, Logic, Utility, REPL)
├── web_frontend/           # Frontend Web App (HTML/CSS/JS)
│   ├── index.html          # Main HTML markup
│   ├── index.css           # Premium styles
│   └── index.js            # Node rendering, canvas zoom/pan, socket/AJAX logic
├── run_web_server.py       # HTTP API Server and session coordinator
└── flow_project.json       # Pre-saved example workflow
```

---

## Example Workflow

An example flow is pre-saved as `flow_project.json` in the root of the workspace. It contains a standard math flow consisting of:
*   Two `Number` nodes (initialized to `15.0` and `27.0`)
*   An `Add` node computing their sum
*   A `Log` node displaying the result downstream

### How to use:
1. Open the UI at [http://localhost:8000](http://localhost:8000).
2. Click **Load** in the header control bar to deserialize and load the `flow_project.json` workflow.
3. Modify node values or draw connections.
4. Click **Save** to serialize the current canvas back into `flow_project.json`.

---

## Dynamic Node Discovery

When the frontend mounts, it queries the `/api/nodes` endpoint. The server dynamically scans the `nodes/` folder and registers any Python classes that inherit from `WebNode` (excluding the base classes). 

This means **any new nodes you add to the `nodes/` directory are immediately discovered and rendered in the sidebar library without manual registry updates.**

---

## The Inline Python REPL Node

The **Python REPL** node (`PythonReplNode`) lets you execute arbitrary python code inside the flow using exactly 2 inputs and 2 outputs.

*   **Inputs:** `in1` (data), `in2` (data)
*   **Outputs:** `out1` (data), `out2` (data)
*   **Properties:** A custom multi-line text input field embedded directly inside the node card.

### How it works:
When the Python REPL node is updated, the backend executes the custom code block via python's `exec()` command inside a scoped environment containing the input payloads (`in1`, `in2`) and variables for outputs (`out1`, `out2`). The outputs are then updated with the resulting values.

---

## Flow: Creating a New Node & Rendering It

Here is the step-by-step procedure to add a new node and render it in ryvencore Studio:

### Step 1: Write the Python Logic
Create a new file in the `nodes/` folder (e.g., `nodes/custom_nodes.py`) or add it to `nodes/basic_nodes.py`. Define a class inheriting from `WebNode`:

```python
import ryvencore as rc
from nodes.base import WebNode

class PowerNode(WebNode):
    title = 'Power'
    init_inputs = [
        rc.NodeInputType(label='base', default=rc.Data(2.0)),
        rc.NodeInputType(label='exponent', default=rc.Data(3.0))
    ]
    init_outputs = [rc.NodeOutputType(label='result')]

    def update_event(self, inp=-1):
        # Read inputs safely
        base = self.input(0).payload if self.input(0) else 2.0
        exponent = self.input(1).payload if self.input(1) else 3.0
        
        try:
            res = float(base) ** float(exponent)
        except Exception as e:
            res = f"Error: {e}"

        # Write output
        self.set_output_val(0, rc.Data(res))
```

### Step 2: Categorization (Frontend)
Open `web_frontend/index.js` and map your new node's title to a sidebar category inside the `getNodeCategory` function:

```javascript
function getNodeCategory(title) {
    if (['Add', 'Subtract', 'Multiply', 'Divide', 'Power'].includes(title)) return 'Math';
    // ... other categorizations ...
    return 'Utility'; // Default category
}
```

### Step 3: Implement Custom UI Elements (Optional)
If your node needs special input widgets or buttons (like the `Python REPL` or `Execute Button`), insert the custom markup inside `renderNodes(nodes)` in `web_frontend/index.js`:

```javascript
if (n.title === 'Power') {
    if (nodeEl.find('.node-custom-content').length === 0) {
        nodeEl.find('.node-ports').after(`
            <div class="node-custom-content" style="padding: 10px; text-align: center;">
                 <small style="color: var(--text-muted);">Computes base^exponent</small>
            </div>
        `);
    }
}
```

### Step 4: Interact & Save
Refresh your browser. Drag the new node onto the canvas, hook up its inputs/outputs, and verify its downstream effects. Use the **Save** button to store the custom setup.
