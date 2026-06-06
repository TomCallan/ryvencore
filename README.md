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
├── ryvencore/               # Core graph execution engine
│   ├── __init__.py          # Public API surface
│   ├── Base.py              # Base class (ID counter, events, serialization)
│   ├── Compiler.py          # Flow-to-standalone-script compiler
│   ├── Data.py              # Inter-node data wrapper
│   ├── Flow.py              # Graph manager (nodes, edges, executors, benchmarks)
│   ├── FlowExecutor.py      # 4 execution algorithms + compiled executor
│   ├── Metrics.py           # Timing/benchmarking infrastructure
│   ├── Node.py              # Node base class
│   ├── NodePort.py          # Runtime port objects
│   ├── NodePortType.py      # Port blueprint types
│   ├── RC.py                # Enums (FlowAlg, PortObjPos)
│   ├── Session.py           # Top-level project manager
│   ├── utils.py             # Serialization, deserialization, imports
│   ├── py.typed             # PEP 561 marker
│   └── addons/              # Built-in add-ons (Logging, Variables)
├── nodes/                   # Custom node definitions
│   ├── base.py              # WebNode base class + flow execution hooks
│   ├── basic_nodes.py       # ~24 node classes (math, logic, exec, I/O, DB, plotting)
│   └── nn_nodes.py          # 8 neural network nodes (trainer, inference, layers, loss)
├── plotting/                # SVG plotting engine
├── compiled/                # Generated standalone compiled scripts
├── saved_flows/             # Persistent JSON flow project files
├── example_scripts/         # External Python scripts for PythonScriptNode
├── tests/                   # pytest test suite
├── web_frontend/            # Browser-based UI (HTML/CSS/JS)
├── run_web_server.py        # HTTP API server + static file server
├── run_cli.py               # CLI flow runner + benchmark mode
├── run_benchmarks.py        # Comprehensive 7-benchmark performance suite
├── compile_workflow.py      # Standalone flow compilation script
├── create_nn_flow.py        # NN training + inference flow generator
├── create_parquet_db_flow.py # 100MB parquet DB flow generator
├── create_*.py              # Additional flow generators
└── flow_project.json        # Default example workflow
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

---

## High-Efficiency & High-Compute Nodes (Phase 2)

ryvencore Studio supports processing massive datasets and high-compute tasks natively on the backend, without choking data transmission or blocking the web browser:

1.  **Wait Complete Flag:** Each node card features a **Wait Complete** checkbox. When checked, the node blocks overlapping concurrent/re-entrant triggers (e.g., if a loop interval is 0.1s but a deep learning model forward pass takes 0.5s), executing safely and linearly.
2.  **Execution Timer Node (`ExecutionTimerNode`):** Profiles execution times directly within the flow. When triggered, it executes downstream nodes, measures the total time elapsed (in milliseconds), and outputs the duration.
3.  **Lazy File Reader Node (`LazyFileReaderNode`):** Lazily streams large text/CSV files line-by-line or chunk-by-chunk in-memory, keeping file handles and pointer offsets in the Python backend. Passing memory chunks locally avoids JSON serialization overhead to the client.
4.  **CSV Parser Node (`CsvParserNode`):** Parses loaded raw string chunks on the fly using standard library modules and forwards nested structured arrays downstream.

### Blazing Fast Python Script & REPL Execution Caching
Both the **Python Script** node and **Python REPL** node compile their AST tree once and cache the resulting bytecode. Instead of parsing the code, copying, and compiling the AST tree on every single node execution:
* The AST is modified once to direct input lookups to a dynamic `_IN_` namespace key.
* For subsequent executions, input values are populated into the namespace at runtime, and `exec()` is run directly on the cached bytecode.
* For `PythonScriptNode`, file modification times (`mtime`) are checked so recompilation only occurs when files actually change.
* Result: Pipeline updates execute in microseconds, bypassing all I/O and compilation overhead!

### Example Workflows

ryvencore Studio includes several pre-configured workflows showcasing different features and optimizations:

1. **Pipeline Script Workflow (`pipeline_flow`)**
   * **Use Case:** AST-caching compiled Python script runner pipeline.
   * **Behavior:** Coordinates three step scripts (`step1_generate.py`, `step2_analyze.py`, `step3_format.py`) checking constraints and formatting logs, running at microsecond speed with cache hits.
   * **Run:**
     ```bash
     python run_cli.py pipeline_flow
     ```

2. **Efficiency Benchmark Workflow (`efficiency_flow`)**
   * **Use Case:** Lazy file parsing and execution profiling.
   * **Behavior:** Automatically streams lines from a CSV dataset, parses them, calculates aggregates, and logs durations using `ExecutionTimerNode`.
   * **Run:**
     ```bash
     python run_cli.py efficiency_flow
     ```

3. **High-Frequency Real-Time Workflow (`realtime_flow`)**
   * **Use Case:** Simulated real-time tick streaming and instant decision logic.
   * **Behavior:** Uses a high-speed trigger loop (20Hz) running in a background thread to generate random price ticks, feed a comparator node, run an if/else selector, and log output signals. Demonstrates thread-safe execution and O(1) propagation.
   * **Run:**
     ```bash
     python run_cli.py realtime_flow
     ```

4. **Batch Backtesting Workflow (`backtesting_flow`)**
   * **Use Case:** Simulating historical backtesting with large files.
   * **Behavior:** Streams raw data blocks, computes the sliding average price using `ArrayCalculatorNode`, compares against a threshold, determines buy/sell signals, and profiles end-to-end throughput.
   * **Run:**
     ```bash
     python run_cli.py backtesting_flow
     ```

5. **Showcase Compiled Workflow (`compiled_flow`)**
   * **Use Case:** Executing complex hybrid flows combining CLI commands, Python REPL, and Python scripts at native speed.
   * **Behavior:** Runs a Trigger -> Timer -> Counter -> CLI script (executing shell command via `subprocess`) -> Python REPL (inline code processing) -> Formatting script -> Log outputs. Configured to run in the third execution mode (`compiled`).
   * **Run:**
     ```bash
     python run_cli.py compiled_flow
     ```

---

## High-Performance Core & Flow Compilation (Phase 3)

The ryvencore core has been optimized for high-throughput processing (e.g. streaming 100M+ rows of OHLCV/orderbook data, real-time feeds, and fast backtesting) with comprehensive benchmarking and metrics infrastructure.

### 0. Metrics & Benchmarking Infrastructure (`ryvencore/Metrics.py`)

A centralized metrics system tracks and compares execution performance across all algorithm modes:

```python
import ryvencore as rc
from ryvencore.Metrics import Metrics, global_metrics

# Track compilation
global_metrics().start_compile('my_flow')
rc.FlowCompiler.compile(flow)
elapsed = global_metrics().stop_compile('my_flow', node_count=10, edge_count=25)

# Track execution per mode
global_metrics().start_execution('my_flow', 'data')
# ... trigger flow execution ...
global_metrics().stop_execution('my_flow', 'data', bytes_processed=1_000_000)

# Get speedup comparisons
speedup = global_metrics().speedup_over_naive('my_flow', 'compiled')
print(global_metrics().summary())
```

**API Surface** (`rc.Metrics` and `rc.global_metrics`):
- `start_compile(name)` / `stop_compile(name, nodes, edges)` — track compilation timing
- `start_execution(name, mode)` / `stop_execution(name, mode, bytes, rows, iters)` — track execution timing
- `avg_execution_time(name, mode)` — average execution time for a flow/mode
- `speedup_over_naive(name, mode)` — speedup ratio vs naive data flow
- `compilation_speedup_over_naive(name)` — compiled vs naive comparison
- `throughput_mb_s(name, mode)` — data throughput in MB/s
- `summary(flow_name)` — human-readable metrics report
- `to_dict()` / `reset()` — serialization and reset

**Flow-level benchmarking methods** (on `rc.Flow`):
- `benchmark_execution(trigger_fn, mode, iterations, bytes_processed)` — per-mode benchmark
- `compare_algorithms(trigger_fn, modes, iterations, bytes_per_iter)` — cross-mode comparison with speedup ratios


### 1. Core Optimizations

### 1. Core Optimizations
*   **Lazy ID Generation:** Transient `Data` instances skip global ID generation overhead.
*   **O(1) Output Propagation:** Output update status stored in dynamic dictionary keys.
*   **DP Waiting Cache:** Topological wait count generation caches successor counts per root node.
*   **Thread-Local Execution Isolation:** Transparent properties map executor states to `threading.local()` storage.
*   **Memory Leak Fix:** Loaded ID mapping references cleared at session load completion.

### 2. Standalone Flow Compiler & "Run Compiled" Execution Mode
You can compile any visual node graph into a single, self-contained Python script. This completely eliminates the overhead of the execution framework (executors, events, sessions) and allows running backtesting/trading at native python speed.

*   **How it works:** FlowCompiler discovers all node instances and classes, collects their exact source code using `inspect.getsource()`, mock-binds ports and connections, and outputs a single standalone python script containing the topologically sorted graph logic.
*   **Run Compiled Mode (In-Process):** Select **Run Compiled** in the Execution Mode dropdown. This mode is only accessible if the current workflow has already been compiled. In compiled mode, automatic node execution and value propagation during canvas edits are disabled. Logic only triggers when you click **Run Compiled** or via repeating loops.
*   **How to compile (Web UI):** Click the purple **Compile** button in the header toolbar to run the backend compilation script. This saves a standalone Python script to `compiled/<workflow>_<timestamp>.py` on the server without downloading anything.
*   **Version Selection Dropdown:** When in compiled mode, a version selector appears in the top header to select which compiled file to execute. Entering compiled mode is blocked if no compiled file exists for the current workflow.
*   **Structure Tracking & Force Recompile:** Any structural changes to the graph (adding nodes, links, or modifying ports) are tracked via a structure hash. If the graph differs from the active compiled file, a **Recompile Required** badge is shown. Running the compiled flow while dirty automatically triggers an automatic background recompilation before execution.
*   **CLI Compilation & Execution:**
    *   **Compile:** Run `python run_cli.py [flow_project.json] --compile` to compile the flow.
    *   **Execute Compiled:** Run `python run_cli.py [flow_project.json] --compiled-file [compiled_file_name]` to run in compiled mode using the specified file. If not specified, the latest compiled file is loaded automatically.

### 3. Native Python Plotting Engine & Advanced Data Nodes
A custom modular plotting engine is implemented in the [plotting](file:///C:/Users/SXDM2/Desktop/agytests/rycore/plotting) package, enabling nodes to generate beautiful dark-mode SVG visualizations in Python and render them directly in the browser.

*   **Plotting Engine (`plotting/engine.py`):**
    *   **SVG Line Plotter:** Renders line charts with gridlines, glowing gradient area fills, and tick markers.
    *   **SVG Orderbook Depth Plotter:** Renders standard bids (green) vs asks (red) depth curves, displaying the spread and mid-price.
*   **New Advanced Nodes:**
    *   `Parquet Reader`: Lazy loads datasets using Polars and scans custom row limits.
    *   `DuckDB Query`: Connects to databases (including in-memory) and executes SQL queries.
    *   `Advanced Plot`: Injects SVG line charts dynamically into the node card on each execution tick.
    *   `Orderbook Plot`: Renders BTC/USDT or custom orderbook depth charts inside the node card.
*   **Premium Save & Load Modals:**
    *   The web browser dialogs have been upgraded to styled, dark-mode overlay modals.
    *   The Load modal fetches and renders saved project flows as dynamic cards with status indicators.
*   **Layout & Alignment Engine:**
    *   Integrated a global `ResizeObserver` on node card bounds to automatically update coordinate offsets and redraw connections in real-time when inputs shrink or nodes are resized.


## Neural Network Training & Inference (Phase 4)

The `nodes/nn_nodes.py` module provides production-ready neural network nodes for training and inference directly within flows:

### Node Types

| Node | Title | Description |
|------|-------|-------------|
| `NNTrainerNode` | NN Trainer | 2-layer NN with configurable hidden size, full forward/backward pass + SGD optimization. Each `update_event` runs one training step. Outputs prediction, loss, and updated weights/biases. |
| `NNInferenceNode` | NN Inference | Forward pass only through a 2-layer network. Takes pretrained weights and input data, outputs prediction and hidden layer activations. |
| `LinearLayerNode` | Linear Layer | Generic y = x @ W^T + b transform with gradient caching for backprop. |
| `ReLUNode` | ReLU | Element-wise ReLU activation with mask output. |
| `SigmoidNode` | Sigmoid | Element-wise sigmoid activation. |
| `MSELossNode` | MSE Loss | Mean Squared Error with gradient output. |
| `SGDOptimizerNode` | SGD Optimizer | Parameter update step: param = param - lr * grad. |
| `NNDataGeneratorNode` | NN Data Generator | Generates synthetic training data (y = 2*x0 + 3*x1 + noise). |

### Usage Example

```python
import ryvencore as rc
from nn_nodes import NNTrainerNode, NNInferenceNode

session = rc.Session()
session.register_node_types([NNTrainerNode])
flow = session.create_flow('nn_demo')
trainer = flow.create_node(NNTrainerNode)
trainer.inputs[0].default = rc.Data([0.5, 0.8])   # input features
trainer.inputs[1].default = rc.Data([2.6])        # target
trainer.inputs[2].default = rc.Data(0.01)         # learning rate
trainer.update()
print(f"Loss: {trainer.outputs[1].val.payload}")
```

### Workflow Generation

```bash
python create_nn_flow.py            # Generate training + inference flows
python create_nn_flow.py --compile  # Also compile both flows
```


## Large-Scale Database Workflows (Phase 4)

Support for generating and querying massive datasets (100MB+ parquet) with DuckDB:

### Nodes

| Node | Title | Description |
|------|-------|-------------|
| `ParquetReaderNode` | Parquet Reader | Reads parquet files via Polars with configurable row limits. Outputs schema info and data as dicts. |
| `DuckDBQueryNode` | DuckDB Query | Executes SQL queries against DuckDB databases (file or `:memory:`). Outputs query info and results. |

### 100MB Parquet Generator

```bash
python create_parquet_db_flow.py                    # Generate 100MB parquet + processing flow
python create_parquet_db_flow.py --size-mb 200      # Custom size
python create_parquet_db_flow.py --no-generate      # Skip parquet generation, just create flow
```

### Parquet Query Benchmarks

The DuckDB query node runs SQL directly against parquet files:

```python
n_query.inputs[1].default = rc.Data(
    "SELECT category, count(*), avg(price_0) "
    "FROM read_parquet('large_dataset.parquet') "
    "GROUP BY category"
)
```

Compiled standalone execution achieves **3-4x speedup** over naive data flow for parquet queries by eliminating framework dispatch overhead.


## Comprehensive Benchmark Suite

`run_benchmarks.py` provides a complete performance validation suite comparing all algorithm modes:

```bash
python run_benchmarks.py              # Run all 7 benchmarks
python run_benchmarks.py --quick      # Fast mode (fewer iterations)
python run_benchmarks.py --nn-only    # Only NN benchmarks
python run_benchmarks.py --db-only    # Only DB benchmarks
python run_benchmarks.py --quiet      # Suppress verbose log output
```

### Benchmarks

| # | Benchmark | What it Tests |
|---|-----------|---------------|
| 0 | Diamond Graph | n-node wide graph, O(width^2 * depth) edges — validates DP optimization + compilation |
| 1 | Simple Math | Basic A+B*C pipeline correctness |
| 2 | NN Training | 2-layer backprop through compiled vs interpreted |
| 3 | NN Inference | Forward pass latency across modes |
| 4 | Parquet DB | 100MB file read + SQL group-by aggregation |
| 5 | Compilation Overhead | Raw `FlowCompiler.compile()` timing |
| 6 | PythonScript AST | Cached AST execution speed comparison |

### Typical Results (quick mode)

| Benchmark | Data Opt | Compiled |
|-----------|---------|----------|
| Diamond graph (30 nodes) | 0.7x | **4.1x** |
| Simple math pipeline | 0.6x | **4.7x** |
| NN training | 0.7x | **4.4x** |
| NN inference | 0.5x | **4.3x** |
| Parquet DB query | 0.8x | **3.0x** |
| PythonScript AST | 1.1x | **6.8x** |

Compilation overhead: ~2-7ms for flows up to 24 nodes.
Metrics saved to `benchmark_results.json` for external analysis.


## CLI Benchmark Mode

The CLI runner now supports direct benchmarking of any saved flow:

```bash
# Benchmark all modes
python run_cli.py my_flow --benchmark --benchmark-iters 100

# Run in specific mode
python run_cli.py my_flow --mode compiled --compiled-file my_flow_compiled.py

# Show metrics after run
python run_cli.py my_flow --show-metrics
```

Example output:
```
  Mode         Avg (ms)       Speedup
  ------------------------------------
  data         57.52          1.00x
  data opt     18.99          3.03x
  compiled      3.57         16.12x

  Compilation benchmark: 10.15 ms avg (n=10)
  Metrics saved to: cli_benchmark_results.json
```


## ryvencore Public API (Full Surface)

```
rc.Session          — top-level project manager
rc.Flow             — graph container (nodes, edges, executors)
rc.Node             — base class for all node blueprints
rc.Data             — inter-node data wrapper
rc.NodeInputType    — input port blueprint
rc.NodeOutputType   — output port blueprint
rc.FlowCompiler     — flow-to-standalone-script compiler
rc.Metrics          — timing/benchmarking metrics collector
rc.global_metrics() — global metrics singleton
rc.FlowAlg          — algorithm modes (DATA, DATA_OPT, EXEC, COMPILED)
rc.AddOn            — add-on base class
rc.serialize()      — pickle+base64 encoder
rc.deserialize()    — pickle+base64 decoder
rc.InfoMsgs         — debug logging toggle
```
