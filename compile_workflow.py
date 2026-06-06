import os
import sys
import json
import time

# Add current directory and nodes directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from run_cli import load_nodes_from_folder, NODE_CLASSES

def main():
    if len(sys.argv) < 3:
        print("Usage: python compile_workflow.py <flow_json_path> <output_dir>")
        sys.exit(1)
        
    flow_json_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    load_nodes_from_folder()
    session = rc.Session()
    session.register_node_types(NODE_CLASSES)
    
    with open(flow_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    flows = session.load(data)
    if not flows:
        print("Error: No flows found in json")
        sys.exit(1)
        
    flow = flows[0]
    compiled_code = rc.FlowCompiler.compile(flow)
    
    os.makedirs(output_dir, exist_ok=True)
    flow_title_safe = "".join(c for c in flow.title if c.isalnum() or c == '_')
    if not flow_title_safe:
        flow_title_safe = "flow"
        
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{flow_title_safe}_{timestamp}.py"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(compiled_code)
        
    print(f"SUCCESS:{filename}")

if __name__ == '__main__':
    main()
