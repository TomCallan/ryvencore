import os
import sys
import json
import csv
import random

# Add paths for importing basic_nodes and ryvencore
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'nodes'))

# 1. Generate example CSV dataset on the fly
csv_path = os.path.join(current_dir, 'large_dataset.csv')
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['val1', 'val2', 'val3'])
    for i in range(100):
        writer.writerow([round(random.uniform(10.0, 50.0), 2), round(random.uniform(50.0, 100.0), 2), round(random.uniform(100.0, 200.0), 2)])

print(f"Generated dataset at: {csv_path}")

import ryvencore as rc
from basic_nodes import TriggerNode, ExecutionTimerNode, LazyFileReaderNode, CsvParserNode, ArrayCalculatorNode, LogNode

def main():
    # 2. Setup ryvencore session
    session = rc.Session()
    session.register_node_types([
        TriggerNode,
        ExecutionTimerNode,
        LazyFileReaderNode,
        CsvParserNode,
        ArrayCalculatorNode,
        LogNode
    ])

    flow = session.create_flow('efficiency_flow')

    # 3. Create nodes
    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)
    n_reader = flow.create_node(LazyFileReaderNode)
    n_parser = flow.create_node(CsvParserNode)
    n_calculator = flow.create_node(ArrayCalculatorNode)
    n_log = flow.create_node(LogNode)
    n_log_time = flow.create_node(LogNode)

    # 4. Set inputs & properties
    n_reader.inputs[0].default = rc.Data('large_dataset.csv')
    n_reader.inputs[1].default = rc.Data(10)
    n_calculator.inputs[1].default = rc.Data('mean')

    # 5. Position nodes on canvas
    n_trigger.x, n_trigger.y = 100, 200
    n_timer.x, n_timer.y = 300, 200
    n_reader.x, n_reader.y = 550, 200
    n_parser.x, n_parser.y = 800, 200
    n_calculator.x, n_calculator.y = 1050, 200
    n_log.x, n_log.y = 1300, 200
    n_log_time.x, n_log_time.y = 1300, 350

    # 6. Connect ports
    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0])
    flow.connect_nodes(n_timer.outputs[0], n_reader.inputs[2]) # Timer out -> Reader next
    flow.connect_nodes(n_reader.outputs[0], n_parser.inputs[0]) # Reader chunk -> Parser chunk
    flow.connect_nodes(n_parser.outputs[0], n_calculator.inputs[0]) # Parser parsed -> Calculator array
    flow.connect_nodes(n_calculator.outputs[0], n_log.inputs[0]) # Calculator result -> Log msg
    flow.connect_nodes(n_timer.outputs[1], n_log_time.inputs[0]) # Timer duration -> Log time msg

    # Enable repeat/loop on trigger for automatic polling, with wait_until_complete guard enabled
    n_trigger.loop_enabled = True
    n_trigger.loop_interval = 1.0
    n_trigger.wait_until_complete = True

    # 7. Serialize and save flow
    flows_dir = os.path.join(current_dir, 'saved_flows')
    os.makedirs(flows_dir, exist_ok=True)
    
    filepath = os.path.join(flows_dir, 'efficiency_flow.json')
    data = session.serialize()
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Generated example workflow at: {filepath}")

if __name__ == '__main__':
    main()
