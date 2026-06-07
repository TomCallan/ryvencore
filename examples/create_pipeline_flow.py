import os
import sys
import json

# Add paths for importing basic_nodes and ryvencore
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from basic_nodes import TriggerNode, CounterNode, PythonScriptNode, LogNode, ExecutionTimerNode

def main():
    session = rc.Session()
    session.register_node_types([
        TriggerNode,
        CounterNode,
        PythonScriptNode,
        LogNode,
        ExecutionTimerNode
    ])

    flow = session.create_flow('pipeline_flow')

    # Create nodes
    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)
    n_counter = flow.create_node(CounterNode)
    
    n_step1 = flow.create_node(PythonScriptNode)
    n_step1.script_path = 'example_scripts/step1_generate.py'

    n_step2 = flow.create_node(PythonScriptNode)
    n_step2.script_path = 'example_scripts/step2_analyze.py'

    n_step3 = flow.create_node(PythonScriptNode)
    n_step3.script_path = 'example_scripts/step3_format.py'

    n_log_msg = flow.create_node(LogNode)
    n_log_time = flow.create_node(LogNode)

    # Position nodes on canvas
    n_trigger.x, n_trigger.y = 100, 200
    n_timer.x, n_timer.y = 300, 200
    n_counter.x, n_counter.y = 550, 200
    n_step1.x, n_step1.y = 800, 200
    n_step2.x, n_step2.y = 1100, 200
    n_step3.x, n_step3.y = 1400, 200
    n_log_msg.x, n_log_msg.y = 1700, 200
    n_log_time.x, n_log_time.y = 1700, 350

    # Connect execution flow
    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0])
    flow.connect_nodes(n_timer.outputs[0], n_counter.inputs[0])

    # Connect data flow
    flow.connect_nodes(n_counter.outputs[1], n_step1.inputs[0]) # trigger_val
    flow.connect_nodes(n_step1.outputs[0], n_step2.inputs[0]) # raw_data -> input_data
    flow.connect_nodes(n_step2.outputs[0], n_step3.inputs[0]) # scaled_data -> data_val
    flow.connect_nodes(n_step2.outputs[1], n_step3.inputs[1]) # is_high -> flag
    flow.connect_nodes(n_step3.outputs[0], n_log_msg.inputs[0]) # formatted_msg -> msg
    flow.connect_nodes(n_timer.outputs[1], n_log_time.inputs[0]) # time_ms -> msg

    # Set loop properties
    n_trigger.loop_enabled = True
    n_trigger.loop_interval = 1.0
    n_trigger.wait_until_complete = True

    # Serialize and save flow
    flows_dir = os.path.join(current_dir, 'saved_flows')
    os.makedirs(flows_dir, exist_ok=True)
    
    data = session.serialize()
    
    # Save to multiple targets to override the default loading project
    targets = [
        os.path.join(flows_dir, 'pipeline_flow.json'),
        os.path.join(flows_dir, 'flow_project.json'),
        os.path.join(current_dir, 'saved_flows', 'flow_project.json')
    ]
    for filepath in targets:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Generated pipeline flow successfully at: {filepath}")

if __name__ == '__main__':
    main()
