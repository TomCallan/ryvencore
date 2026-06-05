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

---

## Dynamic Inputs / Outputs via Python Class Declarations

Both the **Python REPL** node and custom script/node definitions support dynamic input/output port generation using nested `Inputs` and `Outputs` class declarations.

### Example:
If you write the following structure:
```python
class Inputs:
    multiplier = 2.0
    value = 5.0

class Outputs:
    result = 0.0

Outputs.result = Inputs.multiplier * Inputs.value
```
The node will automatically build with the corresponding `multiplier` and `value` input ports, and the `result` output port. If attributes are added or removed, ports will be updated on the fly while preserving connections on unmodified ports.

---

## The Inline Python REPL Node

The **Python REPL** node (`PythonReplNode`) lets you execute arbitrary inline python code.
*   **Properties:** A custom multi-line text input field embedded inside the node card.
*   **Fallback:** If no `class Inputs:` or `class Outputs:` are declared in the code, it falls back to 2 default inputs (`in1`, `in2`) and 2 default outputs (`out1`, `out2`) for compatibility.

---

## The Python Script Node

The **Python Script** node (`PythonScriptNode`) executes a full external Python script file (e.g. `example_script.py`) rather than requiring inline text entry.
*   **Properties:** A text input field to enter the script file path (relative to the project root).
*   **How it works:** Whenever the path is edited, the backend loads the script, parses the `Inputs` and `Outputs` class declarations to construct ports on the fly, and runs the script using AST-rewriting to inject input values on execution.

---

## Right-Click Radial Context Menu & Search Spotlight

Right-click anywhere on the canvas background to summon a circular **Radial Context Menu**.
*   **Actions:** Quick access to Add Node, Save Flow, Load Flow, Clear Flow, and Pause/Resume.
*   **Search Spotlight:** Choosing **Add Node** opens an Unreal Engine / Spotlight-style floating search input at the mouse pointer.
    *   Type to filter all registered nodes dynamically.
    *   Use **Up/Down Arrow keys** to navigate list items.
    *   Press **Enter** to place the node exactly at the right-click coordinate.

---

## Saving & Loading Multiple Flows

You are no longer limited to a single hardcoded project file.
*   **Saving:** Click **Save** (or use the Radial Menu) to name the flow. It is saved as a JSON project in the `saved_flows/` directory.
*   **Loading:** Click **Load** (or use the Radial Menu) to retrieve a list of all saved flows. Type the name of the flow to deserialize and open it.

---

## Data Nodes with Buffers

Two new nodes are provided to demonstrate and process data buffers:
1.  **Plot Node (`PlotNode`):** Listens to a stream of numeric values, appends them to a sliding buffer (configurable limit), and visualizes the curve in real-time as an SVG line chart directly inside the node card. Updates smoothly even while you drag cards around.
2.  **Array Calculator Node (`ArrayCalculatorNode`):** Parses arrays (e.g. `[1, 2, 3]`) or raw comma-separated values, executing aggregate functions: `sum`, `mean`, `min`, `max`, `std` (standard deviation), or scalar element multiplication (`multiply`).

---

## Flow: Creating a New Node & Rendering It

Here is the step-by-step procedure to add a new node and render it in ryvencore Studio:

### Step 1: Write the Python Logic
Create a new file in the `nodes/` folder (e.g., `nodes/custom_nodes.py`) or add it to `nodes/basic_nodes.py`. Define a class inheriting from `WebNode` using nested `Inputs` and `Outputs` class declarations:

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
        try:
            # Attributes are automatically populated from/written to ports
            self.Outputs.result = float(self.Inputs.base) ** float(self.Inputs.exponent)
        except Exception as e:
            self.Outputs.result = f"Error: {e}"
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

---

## Running Graphs in CLI (Bypassing Web UI)

You can run your saved node graphs completely from the command line, bypassing the web UI overhead. The backend execution is fully managed by ryvencore's core logic.

### How to Run:
Run `run_cli.py` with the path to your JSON flow project file:
```bash
python run_cli.py flow_project.json
```
or load a flow by name from the `saved_flows/` directory:
```bash
python run_cli.py my_custom_flow
```

### Implementation Details:
The CLI runner `run_cli.py`:
1. Scans and dynamically imports all node classes in `nodes/`.
2. Registers them into a `ryvencore.Session`.
3. Loads/deserializes the JSON project file.
4. Automatically spins up looping/timer nodes in background daemon threads and handles graph updates using the ryvencore engine.
5. Captures and prints execution outputs (e.g. from `LogNode`) directly to stdout.
6. Gracefully terminates all active loops upon receiving `Ctrl+C`.
