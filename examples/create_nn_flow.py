"""
Creates neural network training and inference workflows.
Demonstrates compilation speedups for NN operations.
"""
import os
import sys
import json
import time

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from ryvencore.Metrics import global_metrics
from basic_nodes import TriggerNode, CounterNode, LogNode, ExecutionTimerNode, PythonScriptNode
from nn_nodes import (
    NNTrainerNode, NNInferenceNode, LinearLayerNode, ReLUNode,
    MSELossNode, NNDataGeneratorNode
)


def create_nn_training_flow():
    """Create a flow that trains a simple neural network."""
    session = rc.Session()
    session.register_node_types([
        TriggerNode,
        ExecutionTimerNode,
        CounterNode,
        NNTrainerNode,
        LogNode,
    ])

    flow = session.create_flow('nn_training_flow')

    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)
    n_counter = flow.create_node(CounterNode)
    n_trainer = flow.create_node(NNTrainerNode)
    n_log_loss = flow.create_node(LogNode)
    n_log_time = flow.create_node(LogNode)

    # Position
    n_trigger.x, n_trigger.y = 100, 200
    n_timer.x, n_timer.y = 300, 200
    n_counter.x, n_counter.y = 550, 200
    n_trainer.x, n_trainer.y = 800, 200
    n_log_loss.x, n_log_loss.y = 1100, 200
    n_log_time.x, n_log_time.y = 1100, 350

    # Connections
    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0])
    flow.connect_nodes(n_timer.outputs[0], n_counter.inputs[0])
    flow.connect_nodes(n_counter.outputs[1], n_trainer.inputs[0])  # count as input_data (will be overridden)

    # Connect trainer loss -> log
    flow.connect_nodes(n_trainer.outputs[1], n_log_loss.inputs[0])
    flow.connect_nodes(n_timer.outputs[1], n_log_time.inputs[0])

    # Save
    flows_dir = os.path.join(current_dir, 'saved_flows')
    os.makedirs(flows_dir, exist_ok=True)

    data = session.serialize()
    save_path = os.path.join(flows_dir, 'nn_training_flow.json')
    with open(save_path, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Created NN training flow: {save_path}")
    return flow, save_path


def create_nn_inference_flow():
    """Create a flow that runs NN inference (forward pass only)."""
    session = rc.Session()
    session.register_node_types([
        TriggerNode,
        ExecutionTimerNode,
        NNInferenceNode,
        LogNode,
    ])

    flow = session.create_flow('nn_inference_flow')

    n_trigger = flow.create_node(TriggerNode)
    n_timer = flow.create_node(ExecutionTimerNode)
    n_inference = flow.create_node(NNInferenceNode)
    n_log = flow.create_node(LogNode)
    n_log_time = flow.create_node(LogNode)

    # Position
    n_trigger.x, n_trigger.y = 100, 200
    n_timer.x, n_timer.y = 300, 200
    n_inference.x, n_inference.y = 550, 200
    n_log.x, n_log.y = 850, 200
    n_log_time.x, n_log_time.y = 850, 350

    # Connections
    flow.connect_nodes(n_trigger.outputs[0], n_timer.inputs[0])
    flow.connect_nodes(n_timer.outputs[0], n_inference.inputs[0])  # exec out -> inference
    flow.connect_nodes(n_inference.outputs[0], n_log.inputs[0])    # prediction -> log
    flow.connect_nodes(n_timer.outputs[1], n_log_time.inputs[0])   # time_ms -> log

    # Save
    flows_dir = os.path.join(current_dir, 'saved_flows')
    os.makedirs(flows_dir, exist_ok=True)

    data = session.serialize()
    save_path = os.path.join(flows_dir, 'nn_inference_flow.json')
    with open(save_path, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Created NN inference flow: {save_path}")
    return flow, save_path


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--compile', action='store_true', help='Also compile flows')
    args = parser.parse_args()

    # 1. Training flow
    training_flow, _ = create_nn_training_flow()

    # 2. Inference flow
    inference_flow, _ = create_nn_inference_flow()

    if args.compile:
        compiled_dir = os.path.join(current_dir, 'compiled')
        os.makedirs(compiled_dir, exist_ok=True)

        print("\nCompiling NN training flow...")
        code = rc.FlowCompiler.compile_with_metrics(training_flow)
        path = os.path.join(compiled_dir, 'nn_training_flow_compiled.py')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"  -> {path}")

        print("\nCompiling NN inference flow...")
        code = rc.FlowCompiler.compile_with_metrics(inference_flow)
        path = os.path.join(compiled_dir, 'nn_inference_flow_compiled.py')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"  -> {path}")

        print(global_metrics().summary())


if __name__ == '__main__':
    main()
