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
    filepath = 'flow_project.json'
    if len(sys.argv) > 1:
        filepath = sys.argv[1]

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
    
    # Count loops
    loops_count = sum(1 for n in flow.nodes if getattr(n, 'loop_enabled', False))
    print(f" - Active loops count: {loops_count}")
    print("\nRunning flow... Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping all loops...")
        for n in flow.nodes:
            if hasattr(n, 'stop_loop'):
                n.stop_loop()
        print("Flow execution stopped.")

if __name__ == '__main__':
    main()
