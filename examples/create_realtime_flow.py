import os
import sys
import json

# Add paths to import ryvencore
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from basic_nodes import RandomNode, CompareNode, IfElseNode, LogNode

def main():
    session = rc.Session()
    session.register_node_types([
        RandomNode,
        CompareNode,
        IfElseNode,
        LogNode
    ])

    flow = session.create_flow('realtime_flow')

    # Create nodes
    n_random = flow.create_node(RandomNode)
    n_compare = flow.create_node(CompareNode)
    n_ifelse = flow.create_node(IfElseNode)
    n_log = flow.create_node(LogNode)

    # Position nodes on canvas
    n_random.x, n_random.y = 100, 200
    n_compare.x, n_compare.y = 350, 200
    n_ifelse.x, n_ifelse.y = 600, 200
    n_log.x, n_log.y = 850, 200

    # Configure parameters
    n_random.inputs[0].default = rc.Data(10.0) # min price
    n_random.inputs[1].default = rc.Data(100.0) # max price
    
    n_compare.inputs[1].default = rc.Data('>') # operator
    n_compare.inputs[2].default = rc.Data(80.0) # threshold
    
    n_ifelse.inputs[1].default = rc.Data('SELL SIGNAL (Price > 80)') # true val
    n_ifelse.inputs[2].default = rc.Data('HOLD') # false val

    # Connections
    flow.connect_nodes(n_random.outputs[0], n_compare.inputs[0]) # price -> compare A
    flow.connect_nodes(n_compare.outputs[0], n_ifelse.inputs[0]) # compare res -> ifelse cond
    flow.connect_nodes(n_random.outputs[0], n_ifelse.inputs[1]) # also pass price to true_val or log it
    flow.connect_nodes(n_ifelse.outputs[0], n_log.inputs[0]) # decision -> log

    # Configure random node internal trigger loop for high frequency (20Hz / 0.05s)
    n_random.loop_enabled = True
    n_random.loop_interval = 0.05
    n_random.wait_until_complete = True

    # Serialize and save flow
    flows_dir = os.path.join(current_dir, 'saved_flows')
    os.makedirs(flows_dir, exist_ok=True)
    
    filepath = os.path.join(flows_dir, 'realtime_flow.json')
    data = session.serialize()
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
        
    print(f"Generated realtime workflow at: {filepath}")

if __name__ == '__main__':
    main()
