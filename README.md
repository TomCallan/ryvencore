# ryvencore Studio

<p align="center">
  <img src="./docs/img/logo.png" alt="ryvencore Studio" width="70%"/>
</p>

A visual scripting platform built on [ryvencore](https://github.com/leon-thomm/ryvencore) — the Python graph execution engine. Build node-based data pipelines, train neural networks, query massive parquet datasets, and compile everything to standalone Python with zero framework overhead.

---

## Quick Start

```bash
pip install -e .                       # install core
python run_web_server.py 8000          # launch web UI
python run_benchmarks.py --quick       # validate performance
python run_cli.py flow_project.json    # run a flow headless
python compile_workflow.py flow_project.json compiled/  # compile to standalone
```

---

## Core API (`ryvencore`)

The `ryvencore` package is the graph execution engine. It manages flows (directed graphs of nodes), executes them in multiple algorithm modes, and can compile them to standalone Python scripts.

### Session — top-level project manager

```python
import ryvencore as rc

session = rc.Session()
session.register_node_types([AddNode, MultiplyNode, LogNode])
flow = session.create_flow('my_pipeline')
```

| Method | Purpose |
|--------|---------|
| `register_node_type(cls)` | Register a single node class |
| `register_node_types(list)` | Register multiple node classes |
| `create_flow(title)` → Flow | Create a new flow |
| `delete_flow(flow)` | Remove a flow |
| `serialize()` → dict | Export project for saving |
| `load(data)` | Restore project from dict |

### Flow — the graph container

```python
flow = session.create_flow('demo')
n_a = flow.create_node(AddNode)
n_b = flow.create_node(NumberNode)
flow.connect_nodes(n_b.outputs[0], n_a.inputs[0])
```

| Mode | Enum | Description |
|------|------|-------------|
| Data Flow (naive) | `FlowAlg.DATA` | Immediate forward propagation. Simple but can be exponential for diamond graphs. |
| Data Flow (optimized) | `FlowAlg.DATA_OPT` | O(V+E) DP ensures each edge fires at most once per execution. Thread-safe. |
| Execution Flow | `FlowAlg.EXEC` | Pull-based: data is computed on demand like Unreal blueprints. |
| Compiled | `FlowAlg.COMPILED` | Dynamically loads a standalone compiled script at native speed. |

```python
flow.set_algorithm_mode('compiled')
print(flow.algorithm_mode())  # 'compiled'
```

| Method | Purpose |
|--------|---------|
| `create_node(node_class)` → Node | Instantiate and add a node |
| `remove_node(node)` | Remove from graph |
| `connect_nodes(out_port, in_port)` | Add edge |
| `disconnect_nodes(out_port, in_port)` | Remove edge |
| `set_algorithm_mode(mode)` | Switch executor (data / data opt / exec / compiled) |
| `benchmark_execution(trigger_fn, mode, iters)` | Time N executions |
| `compare_algorithms(trigger_fn, modes, iters)` | Cross-mode speedup comparison |

### Node — creating custom nodes

Nodes subclass `rc.Node` and override `update_event(inp)`:

```python
class PowerNode(rc.Node):
    title = 'Power'
    init_inputs = [
        rc.NodeInputType(label='base', default=rc.Data(2.0)),
        rc.NodeInputType(label='exponent', default=rc.Data(3.0)),
    ]
    init_outputs = [rc.NodeOutputType(label='result')]

    def update_event(self, inp=-1):
        base = self.input(0).payload
        exp = self.input(1).payload
        self.set_output_val(0, rc.Data(base ** exp))
```

Or use the `WebNode` base class from `nodes/base.py` which adds:
- Canvas position (x, y, width, height)
- Loop/timer support
- Force trigger / wait complete flags
- Dynamic `Inputs`/`Outputs` class-declaration ports

```python
from nodes.base import WebNode

class MyNode(WebNode):
    title = 'My Custom'
    class Inputs:
        value = 0.0
    class Outputs:
        result = 0.0

    def update_event(self, inp=-1):
        self.Outputs.result = self.Inputs.value * 2
```

### Data — inter-node values

```python
data = rc.Data(42.0)
print(data.payload)      # 42.0
data.payload = [1, 2, 3]

# In nodes:
val = self.input(0).payload    # get incoming data
self.set_output_val(0, rc.Data(result))
```

### FlowCompiler — standalone compilation

Eliminates all framework overhead by generating a self-contained Python script.

```python
source = rc.FlowCompiler.compile(flow)
# Or with timing:
source = rc.FlowCompiler.compile_with_metrics(flow)
```

The compiled script:
- Contains mock runtime (CompiledNode, CompiledData, CompiledPort)
- Embeds the actual node class source code via `inspect.getsource()`
- Creates nodes and connections in `setup_flow()`
- Runs via `main()`

```bash
python compile_workflow.py flow_project.json compiled/
# → compiled/flow_20260521_143022.py
```

```python
# Run compiled standalone:
exec(open('compiled/flow_compiled.py').read())
```

### Metrics — performance benchmarking

```python
from ryvencore.Metrics import Metrics, global_metrics

global_metrics().start_compile('my_flow')
rc.FlowCompiler.compile(flow)
global_metrics().stop_compile('my_flow', nodes=10, edges=25)

global_metrics().start_execution('my_flow', 'data')
trigger_nodes()
global_metrics().stop_execution('my_flow', 'data')

print(global_metrics().summary('my_flow'))
```

Or use Flow's built-in:

```python
results = flow.compare_algorithms(trigger, modes=('data', 'data opt', 'compiled'), iterations=100)
# results['speedups'] -> {'data opt': 3.03, 'compiled': 16.12}
```

### Full API Surface

```
rc.Session            — project manager (flows, nodes, add-ons)
rc.Flow               — graph container (nodes, edges, executors)
rc.Node               — base class for all nodes
rc.Data               — value wrapper between nodes
rc.NodeInputType      — input port blueprint
rc.NodeOutputType     — output port blueprint
rc.FlowCompiler       — compile flows to standalone Python
rc.Metrics            — timing/benchmarking
rc.global_metrics()   — global metrics singleton
rc.FlowAlg            — enum: DATA, DATA_OPT, EXEC, COMPILED
rc.AddOn              — add-on base class
rc.serialize()        — pickle+base64 encode
rc.deserialize()      — pickle+base64 decode
rc.InfoMsgs           — toggle debug logging
```

---

## Nodes Reference

### Math
| Node | Inputs | Outputs | Description |
|------|--------|---------|-------------|
| Add | A, B | sum | a + b |
| Subtract | A, B | diff | a - b |
| Multiply | A, B | prod | a * b |
| Divide | A, B | quot | a / b (div-by-zero safe) |
| Array Calculator | array, operation, operand | result | sum / mean / min / max / std / multiply |

### String
| Node | Inputs | Outputs | Description |
|------|--------|---------|-------------|
| Number | val | val | Pass-through float |
| String | val | val | Pass-through string |
| Concat | A, B | out | String concatenation |
| Uppercase | text | out | `str.upper()` |

### Logic / Control
| Node | Inputs | Outputs | Description |
|------|--------|---------|-------------|
| Compare | A, op, B | res | == > < >= <= != |
| If/Else | cond, true_val, false_val | out | Ternary selector |
| Python REPL | dynamic | dynamic | Inline Python with Inputs/Outputs class declarations |
| Python Script | dynamic | dynamic | Execute external `.py` file with port mapping |
| Branch | in(exec), cond | true, false(exec) | Exec flow branch |
| Counter | inc(exec), reset(exec) | out(exec), count | Incrementing counter |

### Exec / Flow
| Node | Inputs | Outputs | Description |
|------|--------|---------|-------------|
| Trigger | — | out(exec) | Fires execution output on update |
| Execute Button | — | trigger(exec) | Manually trigger target node |
| Execution Timer | trigger(exec) | out(exec), time_ms | Profile downstream execution time |

### Utility
| Node | Description |
|------|-------------|
| Random | `random.uniform(min, max)` |
| Log | Print + server-side logging |
| Lazy File Reader | Stream large files chunk-by-chunk |
| CSV Parser | Parse raw CSV chunks into rows |

### Database
| Node | Inputs | Outputs | Description |
|------|--------|---------|-------------|
| Parquet Reader | file_path, n_rows | df_info, data | Read parquet via Polars |
| DuckDB Query | database, query | info, data | Execute SQL, returns rows as dicts |

### Plotting
| Node | Inputs | Outputs | Description |
|------|--------|---------|-------------|
| Plot | val, limit | buffer | Real-time line chart in node card |
| Advanced Plot | val, limit, title, color | buffer | Server-side SVG with gradient/glow |
| Orderbook Plot | bids, asks, title | rendered | Cumulative depth chart |

The plotting engine (`plotting/engine.py`) generates TradingView-quality SVGs:
- **Line/Area charts**: multiple series, gradient fill, glow effects, grid lines
- **Bar charts**: individual value bars
- **OHLCV candlesticks**: full candlestick with volume bars
- **Indicators**: horizontal/vertical reference lines, flags, labels
- **Orderbook depth**: cumulative bid/ask curves, volume bars, mid-price, spread, B/A ratio
- All charts use `viewBox` and `width="100%"` to scale to any container

### Neural Network
| Node | Inputs | Outputs | Description |
|------|--------|---------|-------------|
| NN Trainer | input_data, target, lr, activation | prediction, loss, weights | 2-layer NN, one SGD step per update |
| NN Inference | input_data, weights, bias, activation | prediction, hidden | Forward pass only |
| Linear Layer | weights, bias, input_vec | output, grad | y = x @ W^T + b |
| ReLU | input_vec | output, mask | Element-wise max(0, x) |
| Sigmoid | input_vec | output | 1 / (1 + exp(-x)) |
| MSE Loss | predicted, target | loss, grad | Mean squared error |
| SGD Optimizer | params, grad, lr, mask | updated | param -= lr * grad |
| NN Data Generator | seed, noise, batch_size | x_batch, y_batch | y = 2*x0 + 3*x1 + noise |

---

## Benchmark Suite

```bash
python run_benchmarks.py              # all 7 benchmarks
python run_benchmarks.py --quick      # fewer iterations
python run_benchmarks.py --nn-only    # neural network benchmarks
python run_benchmarks.py --db-only    # parquet database benchmark
python run_benchmarks.py --quiet      # suppress verbose output
```

### Benchmarks

| # | Benchmark | Graph Size | What it Tests |
|---|-----------|-----------|---------------|
| 0 | Diamond Graph | 30 nodes, 75 edges | Optimization stress test (O(V+E) DP vs naive) |
| 1 | Math Pipeline | 7 nodes, 5 edges | Basic compilation correctness |
| 2 | NN Training | 5 nodes, 3 edges | Backprop through compiled vs interpreted |
| 3 | NN Inference | 5 nodes, 3 edges | Forward pass latency |
| 4 | Parquet DB | 5 nodes, 3 edges | 100MB file read + DuckDB aggregation |
| 5 | Compilation Overhead | 24 nodes, 19 edges | Raw compiler timing |
| 6 | PythonScript AST | 5 nodes, 3 edges | Cached AST execution speed |

### Typical Speedups (standalone compiled vs naive data flow)

| Workload | Optimized | Compiled |
|----------|-----------|----------|
| Diamond graph (30 nodes) | 0.7x | **4.1x** |
| Simple math | 0.6x | **4.7x** |
| NN training | 0.7x | **4.4x** |
| NN inference | 0.5x | **4.3x** |
| Parquet DB query | 0.8x | **3.0x** |
| PythonScript AST | 1.1x | **6.8x** |
| Real compiled flow (CLI) | 3.0x | **16.1x** |

> The optimized mode (data opt) adds DP overhead for small graphs but avoids exponential blowup on large diamonds. Compiled mode removes all framework dispatch, running node code at native Python speed.

---

## CLI Reference

```bash
# Run a flow interactively
python run_cli.py flow_project.json                # data mode (default)
python run_cli.py my_flow                          # auto-resolve from saved_flows/
python run_cli.py flow_project.json --mode compiled
python run_cli.py flow_project.json --compiled-file my_flow_compiled.py

# Compile only
python run_cli.py flow_project.json --compile

# Benchmark all modes
python run_cli.py flow_project.json --benchmark --benchmark-iters 100

# Show metrics after run
python run_cli.py flow_project.json --show-metrics
```

---

## Workflow Generators

```bash
# Generate and compile NN training + inference flows
python create_nn_flow.py --compile

# Generate 100MB parquet database processing flow
python create_parquet_db_flow.py

# Existing example flows
python run_cli.py pipeline_flow
python run_cli.py realtime_flow
python run_cli.py compiled_flow
```

---

## Project Structure

```
rycore/
├── ryvencore/               # Core graph execution engine
│   ├── __init__.py          # Public API
│   ├── Compiler.py          # Flow-to-Python compiler
│   ├── Flow.py              # Graph manager + benchmarking
│   ├── FlowExecutor.py      # 4 execution algorithms
│   ├── Metrics.py           # Performance tracking
│   ├── Node.py / NodePort.py / NodePortType.py
│   ├── Session.py           # Top-level project
│   └── addons/              # Logging, Variables
├── nodes/                   # Custom node definitions
│   ├── base.py              # WebNode with loop/timer support
│   ├── basic_nodes.py       # 30+ nodes (math, logic, DB, plotting)
│   └── nn_nodes.py          # 8 neural network nodes
├── plotting/                # SVG plotting engine
│   └── engine.py            # Line/bar/OHLCV/orderbook charts
├── web_frontend/            # Browser UI (see frontend README)
├── compiled/                # Generated standalone scripts
├── saved_flows/             # Persistent flow projects
├── tests/                   # pytest suite
├── run_cli.py               # Headless CLI runner
├── run_web_server.py        # Web API server
├── run_benchmarks.py        # Performance benchmark suite
├── compile_workflow.py      # Standalone compilation
└── setup.cfg                # Package configuration
```
