import os
import sys
import json

# Add paths to import ryvencore
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from basic_nodes import TriggerNode, ExecutionTimerNode, LazyFileReaderNode, CsvParserNode, ArrayCalculatorNode, CompareNode, IfElseNode, LogNode

def main():
    session = rc.Session()
    session.register_node_types([
        TriggerNode,
        ExecutionTimerNode,
        LazyFileReaderNode,
        CsvParserNode,
        ArrayCalculatorNode,
        CompareNode,
        IfElseNode,
        LogNode
    ])

    flow = session.create_flow('backtesting_flow')

    # Create nodes
    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)
    n_reader = flow.create_node(LazyFileReaderNode)
    n_parser = flow.create_node(CsvParserNode)
    n_calculator = flow.create_node(ArrayCalculatorNode)
    n_compare = flow.create_node(CompareNode)
    n_ifelse = flow.create_node(IfElseNode)
    n_log = flow.create_node(LogNode)
    n_log_time = flow.create_node(LogNode)

    # Position nodes on canvas
    n_trigger.x, n_trigger.y = 100, 200
    n_timer.x, n_timer.y = 300, 200
    n_reader.x, n_reader.y = 550, 200
    n_parser.x, n_parser.y = 800, 200
    n_calculator.x, n_calculator.y = 1050, 200
    n_compare.x, n_compare.y = 1300, 200
    n_ifelse.x, n_ifelse.y = 1550, 200
    n_log.x, n_log.y = 1800, 200
    n_log_time.x, n_log_time.y = 1800, 350

    # Configure parameters
    n_reader.inputs[0].default = rc.Data('large_dataset.csv')
    n_reader.inputs[1].default = rc.Data(10) # chunk size 10 rows
    n_calculator.inputs[1].default = rc.Data('mean') # calculate average of the chunk
    n_compare.inputs[1].default = rc.Data('>') # operator
    n_compare.inputs[2].default = rc.Data(100.0) # threshold average price
    n_ifelse.inputs[1].default = rc.Data('CRITICAL: High average price detected!')
    n_ifelse.inputs[2].default = rc.Data('Normal average price')

    # Connections
    # Exec flow connections
    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0]) # trigger -> timer
    flow.connect_nodes(n_timer.outputs[0], n_reader.inputs[2]) # timer out -> reader next
    
    # Data flow connections
    flow.connect_nodes(n_reader.outputs[0], n_parser.inputs[0]) # reader chunk -> parser chunk
    flow.connect_nodes(n_parser.outputs[0], n_calculator.inputs[0]) # parser parsed -> calculator array
    flow.connect_nodes(n_calculator.outputs[0], n_compare.inputs[0]) # calculator result -> compare A
    flow.connect_nodes(n_compare.outputs[0], n_ifelse.inputs[0]) # compare res -> ifelse cond
    flow.connect_nodes(n_ifelse.outputs[0], n_log.inputs[0]) # decision -> log
    flow.connect_nodes(n_timer.outputs[1], n_log_time.inputs[0]) # duration -> log time

    # Configure trigger loop (10Hz / 0.1s)
    n_trigger.loop_enabled = True
    n_trigger.loop_interval = 0.1
    n_trigger.wait_until_complete = True

    # Serialize and save flow
    flows_dir = os.path.join(current_dir, 'saved_flows')
    os.makedirs(flows_dir, exist_ok=True)
    
    filepath = os.path.join(flows_dir, 'backtesting_flow.json')
    data = session.serialize()
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
        
    print(f"Generated backtesting workflow at: {filepath}")

if __name__ == '__main__':
    main()
