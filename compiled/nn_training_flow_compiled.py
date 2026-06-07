# Structure Hash: 51cfab37776aa43cd6bb755add0a2e4f440bd21996b26d4bdacd60a8c07a175e
"""
Compiled ryvencore flow: nn_training_flow
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


class CounterNode(WebNode):
    title = 'Counter'
    init_inputs = [
        rc.NodeInputType(type_='exec', label='inc'),
        rc.NodeInputType(type_='exec', label='reset')
    ]
    init_outputs = [
        rc.NodeOutputType(type_='exec', label='out'),
        rc.NodeOutputType(type_='data', label='count')
    ]

    def __init__(self, params):
        super().__init__(params)
        self.count = 0

    def update_event(self, inp=-1):
        if inp == 0:
            self.count += 1
            self.set_output_val(1, rc.Data(self.count))
            self.exec_output(0)
        elif inp == 1:
            self.count = 0
            self.set_output_val(1, rc.Data(self.count))
            self.exec_output(0)


class TriggerNode(WebNode):
    title = 'Trigger'
    init_inputs = []
    init_outputs = [rc.NodeOutputType(type_='exec', label='out')]

    def update_event(self, inp=-1):
        self.exec_output(0)


class NNTrainerNode(WebNode):
    """
    Simple 2-layer neural network trainer with configurable architecture.
    Runs a single training iteration (forward + backward + update).

    Internally stores weights/biases as state. Each update_event runs one
    training step on the current input/target pair.

    Inputs:
        input_data  : list[float]
        target      : list[float]
        lr          : float learning rate
        activation  : 'relu' or 'sigmoid'

    Outputs:
        prediction  : current prediction
        loss        : current loss value
        weights_1   : updated W1
        weights_2   : updated W2
        bias_1      : updated b1
        bias_2      : updated b2
    """
    title = 'NN Trainer'
    init_inputs = [
        rc.NodeInputType(label='input_data', default=rc.Data([0.0, 0.0])),
        rc.NodeInputType(label='target', default=rc.Data([0.0])),
        rc.NodeInputType(label='lr', default=rc.Data(0.01)),
        rc.NodeInputType(label='activation', default=rc.Data('relu')),
    ]
    init_outputs = [
        rc.NodeOutputType(label='prediction'),
        rc.NodeOutputType(label='loss'),
        rc.NodeOutputType(label='weights_1'),
        rc.NodeOutputType(label='weights_2'),
        rc.NodeOutputType(label='bias_1'),
        rc.NodeOutputType(label='bias_2'),
    ]

    def __init__(self, params):
        super().__init__(params)
        self.hidden_size = 8
        self.input_size = 2
        self.output_size = 1
        self._init_weights()

    def _init_weights(self):
        r = random.Random(42)
        self._w1 = [[r.uniform(-0.5, 0.5) for _ in range(self.input_size)]
                    for _ in range(self.hidden_size)]
        self._b1 = [0.0] * self.hidden_size
        self._w2 = [[r.uniform(-0.5, 0.5) for _ in range(self.hidden_size)]
                    for _ in range(self.output_size)]
        self._b2 = [0.0] * self.output_size

    def additional_data(self):
        d = super().additional_data()
        d['hidden_size'] = self.hidden_size
        d['input_size'] = self.input_size
        d['output_size'] = self.output_size
        d['w1'] = self._w1
        d['b1'] = self._b1
        d['w2'] = self._w2
        d['b2'] = self._b2
        return d

    def load_additional_data(self, data):
        super().load_additional_data(data)
        self.hidden_size = data.get('hidden_size', 8)
        self.input_size = data.get('input_size', 2)
        self.output_size = data.get('output_size', 1)
        self._w1 = data.get('w1')
        self._b1 = data.get('b1')
        self._w2 = data.get('w2')
        self._b2 = data.get('b2')
        if self._w1 is None:
            self._init_weights()

    def update_event(self, inp=-1):
        x = self.input(0).payload if self.input(0) else [0.0, 0.0]
        target = self.input(1).payload if self.input(1) else [0.0]
        try:
            lr = float(self.input(2).payload) if self.input(2) else 0.01
        except (ValueError, TypeError):
            lr = 0.01
        act = str(self.input(3).payload).lower() if self.input(3) else 'relu'

        if not isinstance(x, list):
            x = [float(x)]
        if not isinstance(target, list):
            target = [float(target)]

        # ---- Forward pass ----
        # Layer 1: z1 = x @ W1^T + b1,  a1 = act(z1)
        z1 = []
        for i in range(self.hidden_size):
            s = self._b1[i]
            w_row = self._w1[i]
            for j in range(min(len(w_row), len(x))):
                s += w_row[j] * x[j]
            z1.append(s)

        if act == 'relu':
            a1 = [max(0.0, v) for v in z1]
            d_act = [1.0 if v > 0 else 0.0 for v in z1]
        else:
            a1 = [1.0 / (1.0 + math.exp(-v)) for v in z1]
            d_act = [a1[i] * (1.0 - a1[i]) for i in range(len(a1))]

        # Layer 2: z2 = a1 @ W2^T + b2,  pred = z2 (identity output)
        z2 = []
        for i in range(self.output_size):
            s = self._b2[i]
            w_row = self._w2[i]
            for j in range(min(len(w_row), len(a1))):
                s += w_row[j] * a1[j]
            z2.append(s)
        pred = z2

        # ---- Loss ----
        n_out = max(len(pred), len(target))
        loss = 0.0
        d_loss = [0.0] * n_out
        for i in range(n_out):
            p = pred[i] if i < len(pred) else 0.0
            t = target[i] if i < len(target) else 0.0
            diff = p - t
            loss += diff * diff
            d_loss[i] = 2.0 * diff / n_out
        loss /= n_out

        # ---- Backward pass (simple SGD) ----
        # dL/dW2 = outer(d_loss, a1)
        # dL/db2 = d_loss
        # dL/da1 = d_loss @ W2   (element-wise * d_act)
        # dL/dW1 = outer(dL/da1, x)
        # dL/db1 = dL/da1

        # W2 gradient
        for i in range(self.output_size):
            for j in range(self.hidden_size):
                if i < len(d_loss):
                    self._w2[i][j] -= lr * d_loss[i] * a1[j]

        # b2 gradient
        for i in range(min(self.output_size, len(d_loss))):
            self._b2[i] -= lr * d_loss[i]

        # Backprop to hidden
        d_a1 = [0.0] * self.hidden_size
        for j in range(self.hidden_size):
            for i in range(min(self.output_size, len(d_loss))):
                d_a1[j] += d_loss[i] * self._w2[i][j]
            d_a1[j] *= d_act[j]

        # W1 gradient
        for i in range(self.hidden_size):
            for j in range(min(len(self._w1[i]), len(x))):
                self._w1[i][j] -= lr * d_a1[i] * x[j]

        # b1 gradient
        for i in range(self.hidden_size):
            self._b1[i] -= lr * d_a1[i]

        # ---- Output ----
        self.set_output_val(0, rc.Data(pred))
        self.set_output_val(1, rc.Data(loss))
        self.set_output_val(2, rc.Data(self._w1))
        self.set_output_val(3, rc.Data(self._w2))
        self.set_output_val(4, rc.Data(self._b1))
        self.set_output_val(5, rc.Data(self._b2))


# --- Flow Execution Instantiation ---
def setup_flow(actual_nodes=None):
    nodes = {}
    flow_alg = 'data'

    # Node: Trigger (ID: 4)
    n_4 = TriggerNode(params=None)
    n_4.node_id = 4
    n_4.global_id = 4
    n_4.flow_alg = flow_alg
    if actual_nodes and 4 in actual_nodes:
        n_4.actual_node = actual_nodes[4]
    n_4.create_output('out', 'exec')
    n_4.loop_enabled = False
    n_4.loop_interval = 1.0
    n_4.wait_until_complete = False
    n_4.auto_exec_downstream = False
    nodes[4] = n_4

    # Node: Execution Timer (ID: 6)
    n_6 = ExecutionTimerNode(params=None)
    n_6.node_id = 6
    n_6.global_id = 6
    n_6.flow_alg = flow_alg
    if actual_nodes and 6 in actual_nodes:
        n_6.actual_node = actual_nodes[6]
    n_6.create_input('trigger', 'exec', default=rc.Data(None))
    n_6.create_output('out', 'exec')
    n_6.create_output('time_ms', 'data')
    n_6.loop_enabled = False
    n_6.loop_interval = 1.0
    n_6.wait_until_complete = False
    n_6.auto_exec_downstream = False
    nodes[6] = n_6

    # Node: Counter (ID: 10)
    n_10 = CounterNode(params=None)
    n_10.node_id = 10
    n_10.global_id = 10
    n_10.flow_alg = flow_alg
    if actual_nodes and 10 in actual_nodes:
        n_10.actual_node = actual_nodes[10]
    n_10.create_input('inc', 'exec', default=rc.Data(None))
    n_10.create_input('reset', 'exec', default=rc.Data(None))
    n_10.create_output('out', 'exec')
    n_10.create_output('count', 'data')
    n_10.loop_enabled = False
    n_10.loop_interval = 1.0
    n_10.wait_until_complete = False
    n_10.auto_exec_downstream = False
    nodes[10] = n_10

    # Node: NN Trainer (ID: 15)
    n_15 = NNTrainerNode(params=None)
    n_15.node_id = 15
    n_15.global_id = 15
    n_15.flow_alg = flow_alg
    if actual_nodes and 15 in actual_nodes:
        n_15.actual_node = actual_nodes[15]
    n_15.create_input('input_data', 'data', default=rc.Data([0.0, 0.0]))
    n_15.create_input('target', 'data', default=rc.Data([0.0]))
    n_15.create_input('lr', 'data', default=rc.Data(0.01))
    n_15.create_input('activation', 'data', default=rc.Data('relu'))
    n_15.create_output('prediction', 'data')
    n_15.create_output('loss', 'data')
    n_15.create_output('weights_1', 'data')
    n_15.create_output('weights_2', 'data')
    n_15.create_output('bias_1', 'data')
    n_15.create_output('bias_2', 'data')
    n_15.loop_enabled = False
    n_15.loop_interval = 1.0
    n_15.wait_until_complete = False
    n_15.auto_exec_downstream = False
    nodes[15] = n_15

    # Node: Log (ID: 0)
    n_0 = LogNode(params=None)
    n_0.node_id = 0
    n_0.global_id = 0
    n_0.flow_alg = flow_alg
    if actual_nodes and 0 in actual_nodes:
        n_0.actual_node = actual_nodes[0]
    n_0.create_input('msg', 'data', default=rc.Data(''))
    n_0.create_output('out', 'data')
    n_0.loop_enabled = False
    n_0.loop_interval = 1.0
    n_0.wait_until_complete = False
    n_0.auto_exec_downstream = False
    nodes[0] = n_0

    # Node: Log (ID: 1)
    n_1 = LogNode(params=None)
    n_1.node_id = 1
    n_1.global_id = 1
    n_1.flow_alg = flow_alg
    if actual_nodes and 1 in actual_nodes:
        n_1.actual_node = actual_nodes[1]
    n_1.create_input('msg', 'data', default=rc.Data(''))
    n_1.create_output('out', 'data')
    n_1.loop_enabled = False
    n_1.loop_interval = 1.0
    n_1.wait_until_complete = False
    n_1.auto_exec_downstream = False
    nodes[1] = n_1

    # Connections
    nodes[4].connections[0] = [(nodes[6], 0)]
    nodes[6].connections[0] = [(nodes[10], 0)]
    nodes[6].connections[1] = [(nodes[1], 0)]
    nodes[10].connections[1] = [(nodes[15], 0)]
    nodes[15].connections[1] = [(nodes[0], 0)]

    # Run initial placement events
    nodes[4].after_placement()
    nodes[6].after_placement()
    nodes[10].after_placement()
    nodes[15].after_placement()
    nodes[0].after_placement()
    nodes[1].after_placement()

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
