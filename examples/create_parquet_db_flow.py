"""
Generates a 100MB+ parquet file and creates a flow that processes it
with query/aggregation operations, demonstrating compilation speedups
for large-scale data workloads.
"""
import os
import sys
import json
import time
import random

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from ryvencore.Metrics import global_metrics
from basic_nodes import TriggerNode, DuckDBQueryNode, LogNode, ExecutionTimerNode, CounterNode, PythonScriptNode


def generate_large_parquet(filepath, target_mb=100):
    """Generate a parquet file of approximately target_mb megabytes."""
    print(f"Generating ~{target_mb}MB parquet file: {filepath} ...")

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        import numpy as np
    except ImportError:
        print("pyarrow/numpy not installed. Trying polars fallback...")
        return _generate_parquet_polars(filepath, target_mb)

    # Approximate: each float32 is 4 bytes, we want ~26M rows for 100MB
    # with 10 columns: 10 cols * 4 bytes * N rows = target_MB * 1024*1024
    n_rows = (target_mb * 1024 * 1024) // (10 * 4)

    rng = np.random.RandomState(42)
    data = {}
    for i in range(10):
        if i < 3:
            data[f"id_{i}"] = np.arange(n_rows, dtype=np.int32)
        elif i < 6:
            data[f"price_{i}"] = rng.randn(n_rows).astype(np.float32) * 100 + 50
        elif i < 9:
            data[f"volume_{i}"] = rng.randint(1, 10000, n_rows, dtype=np.int32)
        else:
            data["category"] = rng.choice(["A", "B", "C", "D", "E"], n_rows)

    table = pa.table(data)
    pq.write_table(table, filepath, compression='snappy')

    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"  Generated {n_rows} rows, {size_mb:.1f}MB")

    return filepath


def _generate_parquet_polars(filepath, target_mb):
    """Fallback using polars."""
    try:
        import polars as pl
    except ImportError:
        print("ERROR: Neither pyarrow nor polars is installed. Cannot generate parquet.")
        return None

    n_rows = (target_mb * 1024 * 1024) // (10 * 8)  # float64 = 8 bytes

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
    df.write_parquet(filepath)

    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"  Generated {n_rows} rows, {size_mb:.1f}MB")

    return filepath


def create_parquet_process_flow(parquet_path):
    """Create a flow that reads and processes the large parquet file."""
    session = rc.Session()
    session.register_node_types([
        TriggerNode,
        ExecutionTimerNode,
        DuckDBQueryNode,
        LogNode,
    ])

    flow = session.create_flow('parquet_db_flow')

    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)

    # Query 1: Count and basic stats
    n_query1 = flow.create_node(DuckDBQueryNode)
    n_query1.title = "Count & Stats"

    # Query 2: Group by aggregation
    n_query2 = flow.create_node(DuckDBQueryNode)
    n_query2.title = "Group By Agg"

    # Query 3: Filtered sum
    n_query3 = flow.create_node(DuckDBQueryNode)
    n_query3.title = "Filtered Sum"

    n_log1 = flow.create_node(LogNode)
    n_log1.title = "Log Stats"
    n_log_time = flow.create_node(LogNode)
    n_log_time.title = "Log Timer"

    # Position
    n_trigger.x, n_trigger.y = 100, 200
    n_timer.x, n_timer.y = 300, 200
    n_query1.x, n_query1.y = 550, 50
    n_query2.x, n_query2.y = 550, 250
    n_query3.x, n_query3.y = 550, 450
    n_log1.x, n_log1.y = 850, 250
    n_log_time.x, n_log_time.y = 850, 450

    # Connections: trigger -> timer -> queries
    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0])
    flow.connect_nodes(n_timer.outputs[0], n_query1.inputs[0])  # exec out -> query1

    # Data connections: timer time_ms -> log
    flow.connect_nodes(n_timer.outputs[1], n_log_time.inputs[0])

    # Connect query1 info output -> log
    flow.connect_nodes(n_query1.outputs[0], n_log1.inputs[0])

    # Set parquet path into query DB paths
    # Use DuckDB with the parquet file
    parquet_abs = os.path.abspath(parquet_path).replace('\\', '/')
    n_query1.code = f"SELECT count(*) as total_rows, avg(price_0) as avg_price, sum(volume_0) as total_vol FROM read_parquet('{parquet_abs}')"

    # Save flow
    flows_dir = os.path.join(current_dir, 'saved_flows')
    os.makedirs(flows_dir, exist_ok=True)

    data = session.serialize()
    save_path = os.path.join(flows_dir, 'parquet_db_flow.json')
    with open(save_path, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Created parquet DB flow: {save_path}")
    return flow, save_path


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--size-mb', type=int, default=100, help='Target parquet size in MB')
    parser.add_argument('--no-generate', action='store_true', help='Skip parquet generation')
    args = parser.parse_args()

    parquet_path = os.path.join(current_dir, 'large_dataset.parquet')

    if not args.no_generate:
        if os.path.exists(parquet_path):
            print(f"Parquet file already exists: {parquet_path}")
            size_mb = os.path.getsize(parquet_path) / (1024 * 1024)
            print(f"  Size: {size_mb:.1f}MB")
        else:
            generate_large_parquet(parquet_path, args.size_mb)

    flow, flow_path = create_parquet_process_flow(parquet_path)

    # Compile the flow
    print("\nCompiling flow...")
    compiled_code = rc.FlowCompiler.compile_with_metrics(flow)

    compiled_dir = os.path.join(current_dir, 'compiled')
    os.makedirs(compiled_dir, exist_ok=True)
    compiled_path = os.path.join(compiled_dir, 'parquet_db_flow_compiled.py')
    with open(compiled_path, 'w', encoding='utf-8') as f:
        f.write(compiled_code)
    print(f"Compiled output: {compiled_path}")

    print(global_metrics().summary())


if __name__ == '__main__':
    main()
