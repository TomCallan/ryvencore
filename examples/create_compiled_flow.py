import os
import sys
import json

# Add paths to import ryvencore
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from basic_nodes import TriggerNode, CounterNode, PythonScriptNode, PythonReplNode, LogNode, ExecutionTimerNode

def main():
    session = rc.Session()
    session.register_node_types([
        TriggerNode,
        ExecutionTimerNode,
        CounterNode,
        PythonScriptNode,
        PythonReplNode,
        LogNode
    ])

    flow = session.create_flow('compiled_flow')

    # Create nodes
    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)
    n_counter = flow.create_node(CounterNode)
    
    n_script1 = flow.create_node(PythonScriptNode)
    n_script1.script_path = 'example_scripts/run_cli_cmd.py'
    n_script1.update_ports_from_script()

    n_repl = flow.create_node(PythonReplNode)
    n_repl.code = "out1 = f'REPL PROCESSED: {in1}'\nout2 = len(in1)"

    n_script2 = flow.create_node(PythonScriptNode)
    n_script2.script_path = 'example_scripts/analyze_output.py'
    n_script2.update_ports_from_script()

    n_log_msg = flow.create_node(LogNode)
    n_log_time = flow.create_node(LogNode)

    # Position nodes on canvas
    n_trigger.x, n_trigger.y = 100, 200
    n_timer.x, n_timer.y = 300, 200
    n_counter.x, n_counter.y = 550, 200
    n_script1.x, n_script1.y = 800, 200
    n_repl.x, n_repl.y = 1100, 200
    n_script2.x, n_script2.y = 1400, 200
    n_log_msg.x, n_log_msg.y = 1700, 200
    n_log_time.x, n_log_time.y = 1700, 350

    # Connect execution flow
    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0]) # trigger -> timer
    flow.connect_nodes(n_timer.outputs[0], n_counter.inputs[0]) # timer out -> counter inc

    # Connect data flow
    # n_counter outputs: 0 = out (exec), 1 = count (data)
    # n_script1 inputs: 0 = command (data), 1 = trigger_val (data)
    flow.connect_nodes(n_counter.outputs[1], n_script1.inputs[1]) # count -> trigger_val
    
    # n_script1 outputs: 0 = output (data)
    # n_repl inputs: 0 = in1 (data), 1 = in2 (data)
    flow.connect_nodes(n_script1.outputs[0], n_repl.inputs[0]) # output -> in1

    # n_repl outputs: 0 = out1 (data), 1 = out2 (data)
    # n_script2 inputs: 0 = length (data), 1 = text (data)
    # Wait, let's verify inputs order of script2 (analyze_output.py):
    # Inputs:
    #   text = ""
    #   length = 0
    # Let's inspect the order: text is index 0, length is index 1.
    flow.connect_nodes(n_repl.outputs[0], n_script2.inputs[0]) # out1 -> text
    flow.connect_nodes(n_repl.outputs[1], n_script2.inputs[1]) # out2 -> length

    # n_script2 outputs: 0 = final_message (data)
    flow.connect_nodes(n_script2.outputs[0], n_log_msg.inputs[0]) # final_message -> log msg
    flow.connect_nodes(n_timer.outputs[1], n_log_time.inputs[0]) # time_ms -> log time

    # Set loop properties
    n_trigger.loop_enabled = True
    n_trigger.loop_interval = 1.0
    n_trigger.wait_until_complete = True

    # Set flow execution mode to compiled
    flow.set_algorithm_mode('compiled')

    # Serialize and save flow
    flows_dir = os.path.join(current_dir, 'saved_flows')
    os.makedirs(flows_dir, exist_ok=True)
    
    data = session.serialize()
    
    # Save to multiple targets to override the default loading project
    targets = [
        os.path.join(flows_dir, 'compiled_flow.json'),
        os.path.join(flows_dir, 'flow_project.json'),
        os.path.join(current_dir, 'saved_flows', 'flow_project.json')
    ]
    for filepath in targets:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Generated compiled flow successfully at: {filepath}")

if __name__ == '__main__':
    main()
