# Structure Hash: 920687b60f020b0ed6211c2b8588b41c2e7eb2e4117903b9cdd22e118f9704d6
"""
Compiled ryvencore flow: nn_inference_bench
Generated automatically by FlowCompiler.
"""
import sys
import time
import os

# --- Compiled ryvencore Runtime Mock ---
import random
import math
import json
import csv
import os.path
class CompiledData:
    def __init__(self, value=None, load_from=None):
        self.payload = value

    def __str__(self):
        return f"<Data payload: {self.payload}>"

class CompiledNode:
    def __init__(self, node_id, flow_alg='data', actual_node=None):
        self.node_id = node_id
        self.global_id = node_id
        self.flow_alg = flow_alg
        self.actual_node = actual_node
        self.inputs = []
        self.outputs = []
        self.connections = {}  # output_idx -> [(target_node, input_idx)]

    def input(self, index):
        if index < len(self.inputs):
            return self.inputs[index].default
        return None

    def set_output_val(self, index, val):
        if not isinstance(val, CompiledData):
            val = CompiledData(val)
        
        # Update output port value
        if index < len(self.outputs):
            self.outputs[index].val = val

        # Update actual node's output val in ryvencore flow
        if self.actual_node and index < len(self.actual_node.outputs):
            self.actual_node.outputs[index].val = val

        # Propagate to connected nodes
        if index in self.connections:
            for target_node, target_input in self.connections[index]:
                if target_input < len(target_node.inputs):
                    target_node.inputs[target_input].default = val
                    if self.flow_alg in ('data', 'data opt', 'compiled'):
                        target_node.update(target_input)

    def exec_output(self, index):
        if index in self.connections:
            for target_node, target_input in self.connections[index]:
                target_node.update(target_input)

    def update(self, inp=-1):
        if getattr(self, 'wait_until_complete', False) and getattr(self, '_is_executing', False):
            return
        self._is_executing = True
        try:
            # Map Inputs/Outputs if class declarations exist (similar to WebNode logic)
            if hasattr(self.__class__, 'Inputs') and isinstance(self.__class__.Inputs, type):
                inputs_instance = self.__class__.Inputs()
                for idx, inp_port in enumerate(self.inputs):
                    label = inp_port.label_str
                    val_obj = self.input(idx)
                    setattr(inputs_instance, label, val_obj.payload if val_obj else None)
                self.Inputs = inputs_instance
                
            if hasattr(self.__class__, 'Outputs') and isinstance(self.__class__.Outputs, type):
                self.Outputs = self.__class__.Outputs()

            # Execute main node update
            self.update_event(inp)

            # Map Outputs class attributes back to ports
            if hasattr(self, 'Outputs') and not isinstance(self.Outputs, type):
                for idx, out_port in enumerate(self.outputs):
                    label = out_port.label_str
                    val = getattr(self.Outputs, label, None)
                    self.set_output_val(idx, val)
        finally:
            self._is_executing = False

    def update_event(self, inp=-1):
        pass

    def rebuilt(self):
        pass

    def after_placement(self):
        pass

    def prepare_removal(self):
        pass

class CompiledPort:
    def __init__(self, label_str='', type_='data', default=None):
        self.label_str = label_str
        self.type_ = type_
        self.default = default
        self.val = default

class CompiledNodeInput(CompiledPort):
    pass

class CompiledNodeOutput(CompiledPort):
    pass

class MockRyvencore:
    Node = CompiledNode
    Data = CompiledData
    
    @staticmethod
    def NodeInputType(label='', type_='data', default=None):
        return CompiledNodeInput(label, type_, default)

    @staticmethod
    def NodeOutputType(label='', type_='data'):
        return CompiledNodeOutput(label, type_)

# Register mock in sys.modules so imports of ryvencore inside node classes resolve to mock
sys.modules['ryvencore'] = MockRyvencore
import ryvencore as rc

# Mock WebNode parent class used in basic_nodes
class WebNode(CompiledNode):
    def __init__(self, params=None):
        super().__init__(node_id=-1)
        self.loop_enabled = False
        self.loop_interval = 1.0
        self._is_executing = False

    def create_input(self, label='', type_='data', default=None, load_from=None):
        port = CompiledNodeInput(label, type_, default)
        self.inputs.append(port)
        return port

    def create_output(self, label='', type_='data', load_from=None):
        port = CompiledNodeOutput(label, type_)
        self.outputs.append(port)
        return port

def add_server_log(msg):
    print(f"[Server Log] {msg}")

log_messages = []
global_execution_paused = False


# --- Node Classes Definitions ---
class ExecutionTimerNode(WebNode):
    title = 'Execution Timer'
    init_inputs = [
        rc.NodeInputType(type_='exec', label='trigger')
    ]
    init_outputs = [
        rc.NodeOutputType(type_='exec', label='out'),
        rc.NodeOutputType(type_='data', label='time_ms')
    ]

    def update_event(self, inp=-1):
        if inp == 0:
            import time
            start = time.perf_counter()
            self.exec_output(0)
            end = time.perf_counter()
            dur = (end - start) * 1000.0
            self.set_output_val(1, rc.Data(dur))


class LogNode(WebNode):
    title = 'Log'
    init_inputs = [rc.NodeInputType(label='msg', default=rc.Data(''))]
    init_outputs = [rc.NodeOutputType(label='out')]

    def update_event(self, inp=-1):
        msg = self.input(0).payload if self.input(0) else ''
        log_str = f"Log Node {self.global_id}: {msg}"
        print(log_str)
        add_server_log(log_str)
        self.set_output_val(0, rc.Data(msg))


class TriggerNode(WebNode):
    title = 'Trigger'
    init_inputs = []
    init_outputs = [rc.NodeOutputType(type_='exec', label='out')]

    def update_event(self, inp=-1):
        self.exec_output(0)


class NNInferenceNode(WebNode):
    """
    Run a complete NN inference (forward pass).
    Takes input data and a pretrained weights blob, runs through
    a configurable network and outputs predictions.

    Inputs:
        input_data  : list[float] input features
        weights_1   : list[list[float]] W1
        bias_1      : list[float] b1
        weights_2   : list[list[float]] W2
        bias_2      : list[float] b2
        activation  : str 'relu' or 'sigmoid'

    Outputs:
        prediction  : list[float] output
        hidden      : list[float] hidden layer activations
    """
    title = 'NN Inference'
    init_inputs = [
        rc.NodeInputType(label='input_data', default=rc.Data([0.0, 0.0])),
        rc.NodeInputType(label='weights_1', default=rc.Data([[0.5, -0.2], [0.3, 0.8], [0.1, -0.5]])),
        rc.NodeInputType(label='bias_1', default=rc.Data([0.0, 0.0, 0.0])),
        rc.NodeInputType(label='weights_2', default=rc.Data([[0.4, -0.3, 0.2]])),
        rc.NodeInputType(label='bias_2', default=rc.Data([0.0])),
        rc.NodeInputType(label='activation', default=rc.Data('relu')),
    ]
    init_outputs = [
        rc.NodeOutputType(label='prediction'),
        rc.NodeOutputType(label='hidden'),
    ]

    def update_event(self, inp=-1):
        x = self.input(0).payload if self.input(0) else [0.0]
        w1 = self.input(1).payload if self.input(1) else [[0.5]]
        b1 = self.input(2).payload if self.input(2) else [0.0]
        w2 = self.input(3).payload if self.input(3) else [[0.5]]
        b2 = self.input(4).payload if self.input(4) else [0.0]
        act = str(self.input(5).payload).lower() if self.input(5) else 'relu'

        if not isinstance(x, list):
            x = [float(x)]

        # Layer 1: hidden = act(x @ W1^T + b1)
        hidden = []
        for i in range(len(b1)):
            s = b1[i] if i < len(b1) else 0.0
            w_row = w1[i] if i < len(w1) else [0.0] * len(x)
            for j in range(min(len(w_row), len(x))):
                s += w_row[j] * x[j]
            hidden.append(s)

        if act == 'relu':
            hidden = [max(0.0, v) for v in hidden]
        elif act == 'sigmoid':
            hidden = [1.0 / (1.0 + math.exp(-v)) for v in hidden]

        # Layer 2: output = hidden @ W2^T + b2
        output = []
        for i in range(len(b2)):
            s = b2[i] if i < len(b2) else 0.0
            w_row = w2[i] if i < len(w2) else [0.0] * len(hidden)
            for j in range(min(len(w_row), len(hidden))):
                s += w_row[j] * hidden[j]
            output.append(s)

        self.set_output_val(0, rc.Data(output))
        self.set_output_val(1, rc.Data(hidden))


# --- Flow Execution Instantiation ---
def setup_flow(actual_nodes=None):
    nodes = {}
    flow_alg = 'data'

    # Node: Trigger (ID: 7)
    n_7 = TriggerNode(params=None)
    n_7.node_id = 7
    n_7.global_id = 7
    n_7.flow_alg = flow_alg
    if actual_nodes and 7 in actual_nodes:
        n_7.actual_node = actual_nodes[7]
    n_7.create_output('out', 'exec')
    n_7.loop_enabled = False
    n_7.loop_interval = 1.0
    n_7.wait_until_complete = False
    n_7.auto_exec_downstream = False
    nodes[7] = n_7

    # Node: Execution Timer (ID: 8)
    n_8 = ExecutionTimerNode(params=None)
    n_8.node_id = 8
    n_8.global_id = 8
    n_8.flow_alg = flow_alg
    if actual_nodes and 8 in actual_nodes:
        n_8.actual_node = actual_nodes[8]
    n_8.create_input('trigger', 'exec', default=rc.Data(None))
    n_8.create_output('out', 'exec')
    n_8.create_output('time_ms', 'data')
    n_8.loop_enabled = False
    n_8.loop_interval = 1.0
    n_8.wait_until_complete = False
    n_8.auto_exec_downstream = False
    nodes[8] = n_8

    # Node: NN Inference (ID: 9)
    n_9 = NNInferenceNode(params=None)
    n_9.node_id = 9
    n_9.global_id = 9
    n_9.flow_alg = flow_alg
    if actual_nodes and 9 in actual_nodes:
        n_9.actual_node = actual_nodes[9]
    n_9.create_input('input_data', 'data', default=rc.Data([0.0, 0.0]))
    n_9.create_input('weights_1', 'data', default=rc.Data([[0.5, -0.2], [0.3, 0.8], [0.1, -0.5]]))
    n_9.create_input('bias_1', 'data', default=rc.Data([0.0, 0.0, 0.0]))
    n_9.create_input('weights_2', 'data', default=rc.Data([[0.4, -0.3, 0.2]]))
    n_9.create_input('bias_2', 'data', default=rc.Data([0.0]))
    n_9.create_input('activation', 'data', default=rc.Data('relu'))
    n_9.create_output('prediction', 'data')
    n_9.create_output('hidden', 'data')
    n_9.loop_enabled = False
    n_9.loop_interval = 1.0
    n_9.wait_until_complete = False
    n_9.auto_exec_downstream = False
    nodes[9] = n_9

    # Node: Log (ID: 5)
    n_5 = LogNode(params=None)
    n_5.node_id = 5
    n_5.global_id = 5
    n_5.flow_alg = flow_alg
    if actual_nodes and 5 in actual_nodes:
        n_5.actual_node = actual_nodes[5]
    n_5.create_input('msg', 'data', default=rc.Data(''))
    n_5.create_output('out', 'data')
    n_5.loop_enabled = False
    n_5.loop_interval = 1.0
    n_5.wait_until_complete = False
    n_5.auto_exec_downstream = False
    nodes[5] = n_5

    # Node: Log (ID: 6)
    n_6 = LogNode(params=None)
    n_6.node_id = 6
    n_6.global_id = 6
    n_6.flow_alg = flow_alg
    if actual_nodes and 6 in actual_nodes:
        n_6.actual_node = actual_nodes[6]
    n_6.create_input('msg', 'data', default=rc.Data(''))
    n_6.create_output('out', 'data')
    n_6.loop_enabled = False
    n_6.loop_interval = 1.0
    n_6.wait_until_complete = False
    n_6.auto_exec_downstream = False
    nodes[6] = n_6

    # Connections
    nodes[7].connections[0] = [(nodes[8], 0)]
    nodes[8].connections[1] = [(nodes[6], 0)]
    nodes[9].connections[0] = [(nodes[5], 0)]

    # Run initial placement events
    nodes[7].after_placement()
    nodes[8].after_placement()
    nodes[9].after_placement()
    nodes[5].after_placement()
    nodes[6].after_placement()

    return nodes


def main():
    print("Setting up compiled flow...")
    nodes = setup_flow()
    
    # Identify trigger nodes
    triggers = [n for n in nodes.values() if n.__class__.__name__ == 'TriggerNode']
    if not triggers:
        # Fallback: trigger first topological node
        print("No TriggerNode found. Running all nodes in topological order...")
        for n in sorted(nodes.values(), key=lambda x: x.node_id):
            n.update()
    else:
        print(f"Found {len(triggers)} TriggerNodes. Initiating flow execution...")
        for t in triggers:
            t.update()

if __name__ == '__main__':
    main()
