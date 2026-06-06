"""
Comprehensive benchmark runner for ryvencore.

Demonstrates:
  1. NN training/inference with timing across all algorithm modes
  2. Large DB (parquet) processing with compilation speedup
  3. Core compilation pipeline end-to-end validation
  4. Metrics collection and comparison summaries

Usage:
    python run_benchmarks.py                  # Run all benchmarks
    python run_benchmarks.py --quick          # Fast mode (fewer iterations)
    python run_benchmarks.py --nn-only        # Only NN benchmarks
    python run_benchmarks.py --db-only        # Only DB benchmarks
    python run_benchmarks.py --quiet          # Suppress verbose log output
"""
import os
import sys
import json
import time
import random
import math
import argparse
import io

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from ryvencore.Metrics import Metrics, global_metrics

# Load node definitions
from basic_nodes import (
    TriggerNode, CounterNode, LogNode, ExecutionTimerNode,
    AddNode, MultiplyNode, NumberNode, PythonScriptNode, PythonReplNode,
    DuckDBQueryNode, ParquetReaderNode
)
from nn_nodes import (
    NNTrainerNode, NNInferenceNode, LinearLayerNode, ReLUNode,
    MSELossNode, NNDataGeneratorNode
)


# =============================================================
# Utility
# =============================================================

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_subheader(title):
    print(f"\n  --- {title} ---")


def benchmark_standalone_compiled(flow, compiled_path, iterations, trigger_flow_fn):
    """
    Import a compiled flow module once and benchmark standalone execution.
    Returns (avg_ms, times_list, results_dict).
    """
    import importlib.util

    module_name = f"bench_{flow.title}_{int(time.time())}"
    spec = importlib.util.spec_from_file_location(module_name, compiled_path)
    compiled_module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = compiled_module
    spec.loader.exec_module(compiled_module)

    compiled_nodes = compiled_module.setup_flow()
    compiled_triggers = [n for n in compiled_nodes.values() if n.__class__.__name__ == 'TriggerNode']

    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        for t in compiled_triggers:
            t.update()
        times.append((time.perf_counter() - t0) * 1000.0)

    avg = sum(times) / len(times)
    return avg, times


def benchmark_with_standalone(flow, iterations, quick=False):
    """
    Benchmark a flow across data/optimized/standalone-compiled modes.
    Compiles the flow and measures standalone compiled speed via direct import.
    Returns (results dict, compiled_path).
    """
    # Compile first
    compiled_dir = os.path.join(current_dir, 'compiled')
    os.makedirs(compiled_dir, exist_ok=True)

    flow_title_safe = "".join(c for c in flow.title if c.isalnum() or c == '_')
    compiled_path = os.path.join(compiled_dir, f"{flow_title_safe}_compiled.py")

    compiled_code = rc.FlowCompiler.compile_with_metrics(flow)
    with open(compiled_path, 'w', encoding='utf-8') as f:
        f.write(compiled_code)

    # Data naive
    flow.set_algorithm_mode('data')
    times_data = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        for n in flow.nodes:
            if type(n).__name__ == 'TriggerNode':
                n.update()
        times_data.append((time.perf_counter() - t0) * 1000.0)
    avg_data = sum(times_data) / len(times_data)

    # Data optimized
    flow.set_algorithm_mode('data opt')
    times_opt = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        for n in flow.nodes:
            if type(n).__name__ == 'TriggerNode':
                n.update()
        times_opt.append((time.perf_counter() - t0) * 1000.0)
    avg_opt = sum(times_opt) / len(times_opt)

    # Standalone compiled
    avg_compiled, times_compiled = benchmark_standalone_compiled(
        flow, compiled_path, iterations, None
    )

    return {
        'data': {'avg_ms': avg_data, 'min_ms': min(times_data)},
        'data opt': {'avg_ms': avg_opt, 'min_ms': min(times_opt)},
        'compiled': {'avg_ms': avg_compiled, 'min_ms': min(times_compiled)},
        'speedups': {
            'data': 1.0,
            'data opt': avg_data / avg_opt if avg_opt > 0 else 0,
            'compiled': avg_data / avg_compiled if avg_compiled > 0 else 0,
        }
    }, compiled_path


# =============================================================
# Benchmark 0: Large diamond graph (demonstrates optimization + compilation)
# =============================================================

def benchmark_diamond_graph(depth=20, width=5, iterations=50, quick=False):
    """
    Create a diamond-shaped graph of depth*width nodes.
    Every node is connected to all nodes in the next layer.
    This creates O(width^2 * depth) edges, demonstrating how
    the optimized executor avoids exponential blowup and
    compiled standalone execution eliminates framework overhead.
    """
    print_header("Benchmark 0: Diamond Graph (Optimization Stress Test)")

    import random as _rnd
    rng = _rnd.Random(42)

    if quick:
        depth = min(depth, 8)
        width = min(width, 3)
        iterations = min(iterations, 20)

    session = rc.Session()
    session.register_node_types([
        TriggerNode, NumberNode, AddNode, MultiplyNode, LogNode, ExecutionTimerNode
    ])

    flow = session.create_flow('diamond_graph_bench')

    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)

    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0])

    # Create layers of nodes
    layers = []
    prev_outputs = []

    # Input layer: 2 number nodes as sources
    for i in range(width):
        n = flow.create_node(NumberNode)
        n.inputs[0].default = rc.Data(float(i + 1))
        n.title = f"Input_{i}"
        n.update()
        prev_outputs.append(n.outputs[0])

    # Diamond layers
    for d in range(depth):
        layer_nodes = []
        for w in range(width):
            if (d + w) % 2 == 0:
                n = flow.create_node(AddNode)
            else:
                n = flow.create_node(MultiplyNode)
            n.title = f"L{d}_N{w}"

            # Connect to ALL previous outputs (creates diamond pattern)
            for pi, prev_out in enumerate(prev_outputs):
                inp_idx = pi % len(n.inputs)
                flow.connect_nodes(prev_out, n.inputs[inp_idx])

            layer_nodes.append(n)

        prev_outputs = []
        for n in layer_nodes:
            for inp in n.inputs:
                if flow.connected_output(inp) is None:
                    inp.default = rc.Data(1.0)
            n.update()
            prev_outputs.append(n.outputs[0])

        layers.append(layer_nodes)

    # Final log node
    n_log = flow.create_node(LogNode)
    flow.connect_nodes(prev_outputs[0], n_log.inputs[0])
    flow.connect_nodes(n_timer.outputs[1], n_log.inputs[0])

    node_count = len(flow.nodes)
    edge_count = sum(len(inputs) for inputs in flow.graph_adj.values())

    print(f"  Graph: {node_count} nodes, {edge_count} edges, depth={depth}, width={width}")

    # Compile
    print_subheader("Compiling")
    compiled_code = rc.FlowCompiler.compile_with_metrics(flow)
    compiled_dir = os.path.join(current_dir, 'compiled')
    os.makedirs(compiled_dir, exist_ok=True)
    compiled_path = os.path.join(compiled_dir, 'diamond_graph_bench_compiled.py')
    with open(compiled_path, 'w', encoding='utf-8') as f:
        f.write(compiled_code)
    print(f"  Compiled to: {compiled_path}")

    # ---- Benchmark: data flow naive ----
    flow.set_algorithm_mode('data')
    times_data = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        n_trigger.update()
        times_data.append((time.perf_counter() - t0) * 1000.0)
    avg_data = sum(times_data) / len(times_data)
    global_metrics().stop_execution(flow.title, 'data', iterations=iterations)

    # ---- Benchmark: data flow optimized ----
    flow.set_algorithm_mode('data opt')
    times_opt = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        n_trigger.update()
        times_opt.append((time.perf_counter() - t0) * 1000.0)
    avg_opt = sum(times_opt) / len(times_opt)
    global_metrics().stop_execution(flow.title, 'data opt', iterations=iterations)

    # ---- Benchmark: standalone compiled (import once) ----
    import importlib.util
    import importlib

    module_name = f"bench_diamond_{int(time.time())}"
    spec = importlib.util.spec_from_file_location(module_name, compiled_path)
    compiled_module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = compiled_module
    spec.loader.exec_module(compiled_module)

    # Setup once
    compiled_nodes = compiled_module.setup_flow()
    compiled_triggers = [n for n in compiled_nodes.values() if n.__class__.__name__ == 'TriggerNode']

    times_compiled = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        for t in compiled_triggers:
            t.update()
        times_compiled.append((time.perf_counter() - t0) * 1000.0)
    avg_compiled = sum(times_compiled) / len(times_compiled)
    global_metrics().stop_execution(flow.title, 'compiled', iterations=iterations)

    # Record per-mode data
    for mode, avg, times in [('data', avg_data, times_data),
                              ('data opt', avg_opt, times_opt),
                              ('compiled', avg_compiled, times_compiled)]:
        for t in times:
            global_metrics()._executions[flow.title][mode].append({
                'elapsed_s': t / 1000.0,
                'bytes_processed': 0,
                'rows_processed': 0,
                'iterations': 1,
                'timestamp': time.time(),
            })

    speedup_opt = avg_data / avg_opt if avg_opt > 0 else 0
    speedup_compiled = avg_data / avg_compiled if avg_compiled > 0 else 0

    print_subheader("Results")
    print(f"  {'Mode':<16s} {'Avg (ms)':<14s} {'Min (ms)':<14s} {'Speedup':<10s}")
    print(f"  {'-'*54}")
    print(f"  {'data':<16s} {avg_data:<14.3f} {min(times_data):<14.3f} {'1.00x':<10s}")
    print(f"  {'data opt':<16s} {avg_opt:<14.3f} {min(times_opt):<14.3f} {f'{speedup_opt:.2f}x':<10s}")
    print(f"  {'compiled (standalone)':<16s} {avg_compiled:<14.3f} {min(times_compiled):<14.3f} {f'{speedup_compiled:.2f}x':<10s}")

    print(global_metrics().summary('diamond_graph_bench'))
    return {
        'data': {'avg_ms': avg_data, 'min_ms': min(times_data)},
        'data opt': {'avg_ms': avg_opt, 'min_ms': min(times_opt)},
        'compiled': {'avg_ms': avg_compiled, 'min_ms': min(times_compiled)},
        'speedups': {'data opt': speedup_opt, 'compiled': speedup_compiled},
    }


# =============================================================
# Benchmark 1: Simple math pipeline (basic compilation validation)
# =============================================================

def benchmark_simple_pipeline(iterations=500, quick=False):
    """Simple A+B*C pipeline. Tests basic compilation correctness and speedup."""
    print_header("Benchmark 1: Simple Math Pipeline")

    session = rc.Session()
    session.register_node_types([
        TriggerNode, NumberNode, AddNode, MultiplyNode, LogNode, ExecutionTimerNode
    ])

    flow = session.create_flow('math_pipeline_bench')

    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)
    n_num_a = flow.create_node(NumberNode)
    n_num_b = flow.create_node(NumberNode)
    n_mult = flow.create_node(MultiplyNode)
    n_add = flow.create_node(AddNode)
    n_log = flow.create_node(LogNode)

    n_num_a.inputs[0].default = rc.Data(10.0)
    n_num_b.inputs[0].default = rc.Data(5.0)
    n_num_a.update()
    n_num_b.update()

    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0])
    flow.connect_nodes(n_num_a.outputs[0], n_add.inputs[0])
    flow.connect_nodes(n_num_b.outputs[0], n_mult.inputs[0])
    flow.connect_nodes(n_mult.outputs[0], n_add.inputs[1])
    flow.connect_nodes(n_add.outputs[0], n_log.inputs[0])

    iterations = iterations if not quick else 100

    results, _ = benchmark_with_standalone(flow, iterations, quick)

    print_subheader("Results")
    for mode in ('data', 'data opt', 'compiled'):
        r = results.get(mode, {})
        if r:
            sp = results.get('speedups', {}).get(mode, 0)
            print(f"  {mode:12s}: {r['avg_ms']:10.3f} ms avg  (speedup: {sp:.2f}x)")

    print(global_metrics().summary('math_pipeline_bench'))
    return results


# =============================================================
# Benchmark 2: Neural Network Training
# =============================================================

def benchmark_nn_training(iterations=200, quick=False):
    """Train a simple 2-layer NN on synthetic data. Compares modes."""
    print_header("Benchmark 2: Neural Network Training")

    session = rc.Session()
    session.register_node_types([
        TriggerNode, NNTrainerNode, LogNode, ExecutionTimerNode, CounterNode
    ])

    flow = session.create_flow('nn_training_bench')

    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)
    n_trainer = flow.create_node(NNTrainerNode)
    n_log_loss = flow.create_node(LogNode)
    n_log_time = flow.create_node(LogNode)

    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0])
    flow.connect_nodes(n_trainer.outputs[1], n_log_loss.inputs[0])
    flow.connect_nodes(n_timer.outputs[1], n_log_time.inputs[0])

    rng = random.Random(42)
    x0, x1 = rng.uniform(-1, 1), rng.uniform(-1, 1)
    target = 2.0 * x0 + 3.0 * x1 + rng.gauss(0, 0.1)

    n_trainer.inputs[0].default = rc.Data([x0, x1])
    n_trainer.inputs[1].default = rc.Data([target])
    n_trainer.inputs[2].default = rc.Data(0.01)
    n_trainer.inputs[3].default = rc.Data('relu')

    iterations = iterations if not quick else 50

    results, _ = benchmark_with_standalone(flow, iterations, quick)

    print_subheader("Results")
    for mode in ('data', 'data opt', 'compiled'):
        r = results.get(mode, {})
        if r:
            sp = results.get('speedups', {}).get(mode, 0)
            print(f"  {mode:12s}: {r['avg_ms']:10.3f} ms avg  (speedup: {sp:.2f}x)")

    loss_val = n_trainer.outputs[1].val
    if loss_val:
        print(f"\n  Final training loss: {loss_val.payload}")

    print(global_metrics().summary('nn_training_bench'))
    return results


# =============================================================
# Benchmark 3: NN Inference
# =============================================================

def benchmark_nn_inference(iterations=500, quick=False):
    """Run NN inference (forward pass only) many times."""
    print_header("Benchmark 3: Neural Network Inference")

    session = rc.Session()
    session.register_node_types([
        TriggerNode, NNInferenceNode, LogNode, ExecutionTimerNode
    ])

    flow = session.create_flow('nn_inference_bench')

    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)
    n_infer = flow.create_node(NNInferenceNode)
    n_log = flow.create_node(LogNode)
    n_log_time = flow.create_node(LogNode)

    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0])
    flow.connect_nodes(n_infer.outputs[0], n_log.inputs[0])
    flow.connect_nodes(n_timer.outputs[1], n_log_time.inputs[0])

    iterations = iterations if not quick else 100

    results, _ = benchmark_with_standalone(flow, iterations, quick)

    print_subheader("Results")
    for mode in ('data', 'data opt', 'compiled'):
        r = results.get(mode, {})
        if r:
            sp = results.get('speedups', {}).get(mode, 0)
            print(f"  {mode:12s}: {r['avg_ms']:10.3f} ms avg  (speedup: {sp:.2f}x)")

    print(global_metrics().summary('nn_inference_bench'))
    return results


# =============================================================
# Benchmark 4: Parquet DB Processing
# =============================================================

def ensure_parquet_exists(target_mb=100):
    """Ensure a large parquet file exists."""
    parquet_path = os.path.join(current_dir, 'large_dataset.parquet')
    if os.path.exists(parquet_path):
        size_mb = os.path.getsize(parquet_path) / (1024 * 1024)
        if size_mb >= target_mb * 0.9:
            print(f"  Using existing parquet: {parquet_path} ({size_mb:.1f}MB)")
            return parquet_path

    print(f"  Generating ~{target_mb}MB parquet file...")
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        n_rows = (target_mb * 1024 * 1024) // (10 * 4)
        import numpy as np
        rng = np.random.RandomState(42)
        data = {}
        for i in range(3):
            data[f"id_{i}"] = np.arange(n_rows, dtype=np.int32)
        for i in range(3):
            data[f"price_{i}"] = (rng.randn(n_rows).astype(np.float32) * 100 + 50)
        for i in range(3):
            data[f"volume_{i}"] = rng.randint(1, 10000, n_rows, dtype=np.int32)
        data["category"] = rng.choice(["A", "B", "C", "D", "E"], n_rows)

        table = pa.table(data)
        pq.write_table(table, parquet_path, compression='snappy')
    except ImportError:
        print("  pyarrow not available, trying polars...")
        try:
            import polars as pl
            n_rows = (target_mb * 1024 * 1024) // (10 * 8)
            rng = random.Random(42)
            columns = {}
            for i in range(3):
                columns[f"id_{i}"] = list(range(n_rows))
            for i in range(3):
                columns[f"price_{i}"] = [rng.gauss(50, 100) for _ in range(n_rows)]
            for i in range(3):
                columns[f"volume_{i}"] = [rng.randint(1, 10000) for _ in range(n_rows)]
            columns["category"] = [rng.choice(["A", "B", "C", "D", "E"]) for _ in range(n_rows)]
            df = pl.DataFrame(columns)
            df.write_parquet(parquet_path)
        except ImportError:
            print("  ERROR: Neither pyarrow nor polars available. Skipping parquet benchmark.")
            return None

    size_mb = os.path.getsize(parquet_path) / (1024 * 1024)
    print(f"  Generated: {parquet_path} ({size_mb:.1f}MB, {n_rows} rows)")
    return parquet_path


def benchmark_parquet_db(iterations=30, quick=False):
    """Benchmark reading + querying a large parquet file."""
    print_header("Benchmark 4: Parquet DB Processing")

    parquet_path = ensure_parquet_exists(target_mb=100 if not quick else 10)
    if not parquet_path:
        print("  Skipping: cannot generate parquet file.")
        return None

    parquet_abs = parquet_path.replace('\\', '/')

    session = rc.Session()
    session.register_node_types([
        TriggerNode, DuckDBQueryNode, LogNode, ExecutionTimerNode
    ])

    flow = session.create_flow('parquet_db_bench')

    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)
    n_query = flow.create_node(DuckDBQueryNode)
    n_log = flow.create_node(LogNode)
    n_log_time = flow.create_node(LogNode)

    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0])
    flow.connect_nodes(n_query.outputs[0], n_log.inputs[0])
    flow.connect_nodes(n_timer.outputs[1], n_log_time.inputs[0])

    n_query.inputs[0].default = rc.Data(':memory:')

    iterations = iterations if not quick else 5

    file_size_bytes = os.path.getsize(parquet_path)

    # Compile
    compiled_dir = os.path.join(current_dir, 'compiled')
    os.makedirs(compiled_dir, exist_ok=True)
    compiled_path = os.path.join(compiled_dir, 'parquet_db_bench_compiled.py')

    compiled_code = rc.FlowCompiler.compile_with_metrics(flow)
    with open(compiled_path, 'w', encoding='utf-8') as f:
        f.write(compiled_code)

    queries = [
        f"SELECT count(*) as cnt FROM read_parquet('{parquet_abs}')",
        f"SELECT category, count(*) as cnt, avg(price_0) as avg_price FROM read_parquet('{parquet_abs}') GROUP BY category",
        f"SELECT sum(volume_0) as total_vol FROM read_parquet('{parquet_abs}') WHERE price_0 > 0",
    ]

    # Data naive
    flow.set_algorithm_mode('data')
    times_data = []
    for i in range(iterations):
        q = queries[i % len(queries)]
        n_query.inputs[1].default = rc.Data(q)
        t0 = time.perf_counter()
        n_trigger.update()
        times_data.append((time.perf_counter() - t0) * 1000.0)
    avg_data = sum(times_data) / len(times_data)

    # Data optimized
    flow.set_algorithm_mode('data opt')
    times_opt = []
    for i in range(iterations):
        q = queries[i % len(queries)]
        n_query.inputs[1].default = rc.Data(q)
        t0 = time.perf_counter()
        n_trigger.update()
        times_opt.append((time.perf_counter() - t0) * 1000.0)
    avg_opt = sum(times_opt) / len(times_opt)

    # Standalone compiled - but the compiled script doesn't know the parquet path at compile time
    # So we need to set the query in the compiled nodes after setup
    import importlib.util

    module_name = f"bench_parquet_{int(time.time())}"
    spec = importlib.util.spec_from_file_location(module_name, compiled_path)
    compiled_module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = compiled_module
    spec.loader.exec_module(compiled_module)

    compiled_nodes = compiled_module.setup_flow()
    compiled_triggers = [n for n in compiled_nodes.values() if n.__class__.__name__ == 'TriggerNode']
    compiled_queries = [n for n in compiled_nodes.values() if n.__class__.__name__ == 'DuckDBQueryNode']

    times_compiled = []
    for i in range(iterations):
        q = queries[i % len(queries)]
        for cq in compiled_queries:
            if len(cq.inputs) > 1:
                cq.inputs[1].default = q
        t0 = time.perf_counter()
        for t in compiled_triggers:
            t.update()
        times_compiled.append((time.perf_counter() - t0) * 1000.0)
    avg_compiled = sum(times_compiled) / len(times_compiled)

    speedup_opt = avg_data / avg_opt if avg_opt > 0 else 0
    speedup_compiled = avg_data / avg_compiled if avg_compiled > 0 else 0

    results = {
        'data': {'avg_ms': avg_data, 'min_ms': min(times_data)},
        'data opt': {'avg_ms': avg_opt, 'min_ms': min(times_opt)},
        'compiled': {'avg_ms': avg_compiled, 'min_ms': min(times_compiled)},
        'speedups': {'data': 1.0, 'data opt': speedup_opt, 'compiled': speedup_compiled},
    }

    print_subheader("Results")
    for mode in ('data', 'data opt', 'compiled'):
        r = results.get(mode, {})
        if r:
            sp = results.get('speedups', {}).get(mode, 0)
            print(f"  {mode:12s}: {r['avg_ms']:10.3f} ms avg  (speedup: {sp:.2f}x)")

    print(global_metrics().summary('parquet_db_bench'))
    return results


# =============================================================
# Benchmark 5: Compilation overhead test
# =============================================================

def benchmark_compilation_overhead():
    """Measure how fast the compiler itself runs."""
    print_header("Benchmark 5: Compilation Overhead")

    session = rc.Session()
    session.register_node_types([
        TriggerNode, AddNode, MultiplyNode, NumberNode, LogNode,
        PythonScriptNode, NNTrainerNode, NNInferenceNode,
        DuckDBQueryNode, ReLUNode
    ])

    flow = session.create_flow('compilation_overhead_bench')

    # Create a flow with many nodes to stress the compiler
    nodes = []
    n_trigger = flow.create_node(TriggerNode)
    nodes.append(n_trigger)

    # Add 20 math nodes
    for i in range(10):
        n_mul = flow.create_node(MultiplyNode)
        n_mul.title = f"Mul_{i}"
        nodes.append(n_mul)
        n_add = flow.create_node(AddNode)
        n_add.title = f"Add_{i}"
        nodes.append(n_add)

    # Add Python script nodes
    for i in range(3):
        n_ps = flow.create_node(PythonScriptNode)
        n_ps.title = f"Script_{i}"
        nodes.append(n_ps)

    # Connect in a chain
    prev_out = n_trigger.outputs[0]
    for n in nodes[1:]:
        if n.inputs:
            flow.connect_nodes(prev_out, n.inputs[0])
        if n.outputs:
            prev_out = n.outputs[0]

    print_subheader("Compilation Benchmark")
    bench = rc.FlowCompiler.benchmark_compile(flow, iterations=10)
    print(f"  Iterations: {bench['iterations']}")
    print(f"  Min:  {bench['min_ms']:.3f} ms")
    print(f"  Avg:  {bench['avg_ms']:.3f} ms")
    print(f"  Max:  {bench['max_ms']:.3f} ms")

    # Also compile with metrics
    compiled = rc.FlowCompiler.compile_with_metrics(flow)
    print(global_metrics().summary('compilation_overhead_bench'))
    return bench


# =============================================================
# Benchmark 6: PythonScript AST compilation speed
# =============================================================

def benchmark_python_script_execution(iterations=300, quick=False):
    """Benchmark PythonScriptNode execution speed."""
    print_header("Benchmark 6: PythonScript AST Execution")

    session = rc.Session()
    session.register_node_types([
        TriggerNode, PythonScriptNode, PythonReplNode, LogNode, ExecutionTimerNode
    ])

    flow = session.create_flow('pyscript_bench')

    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)
    n_script = flow.create_node(PythonReplNode)
    n_log = flow.create_node(LogNode)
    n_log_time = flow.create_node(LogNode)

    n_script.code = """
class Inputs:
    in1 = 0.0
    in2 = 0.0
class Outputs:
    sum = 0.0
    prod = 0.0
    diff = 0.0
    ratio = 0.0
sum = in1 + in2
prod = in1 * in2
diff = in1 - in2
ratio = in1 / (in2 + 0.001)
    """

    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0])
    flow.connect_nodes(n_timer.outputs[0], n_script.inputs[0])
    flow.connect_nodes(n_script.outputs[0], n_log.inputs[0])
    flow.connect_nodes(n_timer.outputs[1], n_log_time.inputs[0])

    iterations = iterations if not quick else 100

    results, _ = benchmark_with_standalone(flow, iterations, quick)

    print_subheader("Results")
    for mode in ('data', 'data opt', 'compiled'):
        r = results.get(mode, {})
        if r:
            sp = results.get('speedups', {}).get(mode, 0)
            print(f"  {mode:12s}: {r['avg_ms']:10.3f} ms avg  (speedup: {sp:.2f}x)")

    print(global_metrics().summary('pyscript_bench'))
    return results


# =============================================================
# Main
# =============================================================

def main():
    parser = argparse.ArgumentParser(description="ryvencore Comprehensive Benchmark Suite")
    parser.add_argument('--quick', action='store_true', help='Run with fewer iterations (faster)')
    parser.add_argument('--nn-only', action='store_true', help='Only NN benchmarks')
    parser.add_argument('--db-only', action='store_true', help='Only DB benchmarks')
    parser.add_argument('--compile-only', action='store_true', help='Only compilation overhead test')
    parser.add_argument('--quiet', action='store_true', help='Suppress LogNode output during benchmarks')
    args = parser.parse_args()

    # Suppress output if --quiet
    if args.quiet:
        _orig_stdout = sys.stdout
        sys.stdout = io.StringIO()

    t_start = time.perf_counter()

    print("=" * 60)
    print("  ryvencore Benchmark Suite")
    print(f"  Mode: {'quick' if args.quick else 'full'}")
    print("=" * 60)

    results = {}

    if args.nn_only:
        results['nn_training'] = benchmark_nn_training(quick=args.quick)
        results['nn_inference'] = benchmark_nn_inference(quick=args.quick)
    elif args.db_only:
        results['parquet_db'] = benchmark_parquet_db(quick=args.quick)
    elif args.compile_only:
        results['compilation'] = benchmark_compilation_overhead()
    else:
        # Run all benchmarks
        results['diamond_graph'] = benchmark_diamond_graph(quick=args.quick)
        results['simple_pipeline'] = benchmark_simple_pipeline(quick=args.quick)
        results['nn_training'] = benchmark_nn_training(quick=args.quick)
        results['nn_inference'] = benchmark_nn_inference(quick=args.quick)
        results['parquet_db'] = benchmark_parquet_db(quick=args.quick)
        results['compilation'] = benchmark_compilation_overhead()
        results['pyscript'] = benchmark_python_script_execution(quick=args.quick)

    # =============================================================
    # Final Summary
    # =============================================================
    t_total = time.perf_counter() - t_start

    # Restore stdout if --quiet was used
    if args.quiet:
        sys.stdout = _orig_stdout

    print("\n" + "=" * 60)
    print("  BENCHMARK SUITE SUMMARY")
    print("=" * 60)
    print(f"  Total time: {t_total:.2f}s")
    print()

    # Collect all speedup data
    for bench_name, result in results.items():
        if isinstance(result, dict) and 'speedups' in result:
            sp = result['speedups']
            print(f"  {bench_name}:")
            for mode in ('data opt', 'compiled'):
                if mode in sp:
                    print(f"    {mode:12s} speedup: {sp[mode]:.2f}x")

    # Full metrics summary
    print(global_metrics().summary())

    # Save metrics as JSON for external analysis
    metrics_json_path = os.path.join(current_dir, 'benchmark_results.json')
    with open(metrics_json_path, 'w') as f:
        json.dump(global_metrics().to_dict(), f, indent=2)
    print(f"\nMetrics saved to: {metrics_json_path}")


if __name__ == '__main__':
    main()
