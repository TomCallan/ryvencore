import os
import sys
import json
import time
import importlib

# Add current directory and nodes directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from ryvencore.Metrics import global_metrics
from nodes.base import WebNode

NODE_CLASSES = []

def load_nodes_from_folder():
    global NODE_CLASSES
    nodes_dir = os.path.join(current_dir, 'nodes')
    for filename in os.listdir(nodes_dir):
        if filename.endswith('.py') and filename not in ('__init__.py', 'base.py'):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, rc.Node) and attr not in (rc.Node, WebNode):
                        if attr not in NODE_CLASSES:
                            NODE_CLASSES.append(attr)
            except Exception as e:
                print(f"Error loading module {module_name}: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ryvencore CLI Flow Runner")
    parser.add_argument('project_file', nargs='?', default='flow_project.json', help='Path to flow project file')
    parser.add_argument('--compile', action='store_true', help='Compile the flow and exit')
    parser.add_argument('--compiled-file', type=str, default=None, help='Active compiled file to use in compiled execution mode')
    parser.add_argument('--benchmark', action='store_true', help='Run benchmark comparing all algorithm modes')
    parser.add_argument('--benchmark-iters', type=int, default=100, help='Benchmark iterations per mode')
    parser.add_argument('--mode', type=str, default=None, choices=['data', 'data opt', 'exec', 'compiled'], help='Set execution mode override')
    parser.add_argument('--show-metrics', action='store_true', help='Show full metrics after run')

    args = parser.parse_args()
    filepath = args.project_file

    if not os.path.exists(filepath):
        # check if it exists in saved_flows
        saved_path = os.path.join(current_dir, 'saved_flows', filepath)
        if os.path.exists(saved_path):
            filepath = saved_path
        elif not filepath.endswith('.json'):
            saved_path_json = os.path.join(current_dir, 'saved_flows', f"{filepath}.json")
            if os.path.exists(saved_path_json):
                filepath = saved_path_json

    if not os.path.exists(filepath):
        print(f"Error: Project file not found: {filepath}")
        sys.exit(1)

    if args.compile:
        print(f"Compiling project flow: {filepath}...")
        script_path = os.path.join(current_dir, 'compile_workflow.py')
        compiled_dir = os.path.join(current_dir, 'compiled')
        import subprocess
        res = subprocess.run([sys.executable, script_path, filepath, compiled_dir], capture_output=True, text=True)
        if res.returncode == 0 and "SUCCESS:" in res.stdout:
            filename = ""
            for line in res.stdout.splitlines():
                if line.startswith("SUCCESS:"):
                    filename = line.split("SUCCESS:")[1].strip()
                    break
            print(f"Flow compiled successfully. Saved to compiled/{filename}")
            sys.exit(0)
        else:
            print(f"Compilation failed:\n{res.stderr or res.stdout}")
            sys.exit(1)

    print(f"Loading nodes from folder...")
    load_nodes_from_folder()

    print(f"Initializing ryvencore Session...")
    session = rc.Session()
    session.register_node_types(NODE_CLASSES)

    print(f"Loading project file: {filepath}...")
    with open(filepath, 'r') as f:
        data = json.load(f)

    flows = session.load(data)
    if not flows:
        print("Error: No flows loaded from project.")
        sys.exit(1)

    flow = flows[0]
    print(f"\nFlow '{flow.title}' loaded successfully!")
    print(f" - Nodes count: {len(flow.nodes)}")

    # --- Benchmark Mode ---
    if args.benchmark:
        print(f"\n{'='*50}")
        print(f"  BENCHMARK: {flow.title}")
        print(f"{'='*50}")

        # Find trigger nodes
        triggers = [n for n in flow.nodes if type(n).__name__ == 'TriggerNode']

        def trigger_fn():
            for t in triggers:
                t.update()

        results = flow.compare_algorithms(
            trigger_fn,
            modes=('data', 'data opt', 'compiled'),
            iterations=args.benchmark_iters,
            bytes_per_iter=0
        )

        print(f"\n  Results ({args.benchmark_iters} iterations each):")
        print(f"  {'Mode':<12s} {'Avg (ms)':<14s} {'Min (ms)':<14s} {'Max (ms)':<14s} {'Speedup':<10s}")
        print(f"  {'-'*60}")
        for mode in ('data', 'data opt', 'compiled'):
            r = results.get(mode, {})
            if r:
                sp = results.get('speedups', {}).get(mode, 1.0)
                print(f"  {mode:<12s} {r['avg_ms']:<14.3f} {r['min_ms']:<14.3f} {r['max_ms']:<14.3f} {sp:<10.2f}x")

        # Compilation benchmark
        print(f"\n  Compilation benchmark:")
        comp_bench = rc.FlowCompiler.benchmark_compile(flow, iterations=10)
        print(f"    {comp_bench['avg_ms']:.3f} ms avg (n={comp_bench['iterations']})")

        print(global_metrics().summary(flow.title))

        # Save metrics
        metrics_path = os.path.join(current_dir, 'cli_benchmark_results.json')
        with open(metrics_path, 'w') as f:
            json.dump(global_metrics().to_dict(), f, indent=2)
        print(f"\n  Metrics saved to: {metrics_path}")
        sys.exit(0)

    # --- Normal execution mode ---
    def cli_on_output_changed(port):
        try:
            port_index = port.node.outputs.index(port)
        except ValueError:
            port_index = -1
        val = port.val.payload if hasattr(port.val, 'payload') else port.val
        print(f"[CLI Realtime Update] Node {port.node.title} (ID: {port.node.global_id}) output[{port_index}] -> {val}")

    flow.output_changed.sub(cli_on_output_changed)

    if args.mode:
        flow.set_algorithm_mode(args.mode)
        print(f" - Algorithm mode override: {args.mode}")

    if args.compiled_file:
        flow.active_compiled_file = args.compiled_file
        flow.set_algorithm_mode('compiled')

    print(f" - Execution mode: {flow.algorithm_mode()}")
    if flow.algorithm_mode() == 'compiled':
        # Trigger compiled executor initialization/validation
        flow.executor.compile_and_load()
        print(f" - Active compiled file: {flow.active_compiled_file}")

    # Count loops
    loops_count = sum(1 for n in flow.nodes if getattr(n, 'loop_enabled', False))
    print(f" - Active loops count: {loops_count}")
    print("\nRunning flow... Press Ctrl+C to stop.\n")

    try:
        # If in compiled mode, we trigger the trigger nodes once to kick off execution if loops aren't auto-triggered
        if flow.algorithm_mode() == 'compiled':
            triggers = [n for n in flow.nodes if type(n).__name__ == 'TriggerNode']
            for t in triggers:
                flow.executor.update_node(t, -1)

        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping all loops...")
        for n in flow.nodes:
            if hasattr(n, 'stop_loop'):
                n.stop_loop()
        print("Flow execution stopped.")

    if args.show_metrics:
        print(global_metrics().summary(flow.title))

if __name__ == '__main__':
    main()
