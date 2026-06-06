# Structure Hash: 0d13adfdc2ec976cf5dc6f9a4817088eb69ad675a2706a7645a9a309c9d76dec
"""
Compiled ryvencore flow: nn_flow
Generated automatically by FlowCompiler.
"""
import sys
import time
import os
try:
    import numpy as np
except ImportError:
    pass
try:
    import pandas as pd
except ImportError:
    pass

# --- Compiled ryvencore Runtime Mock ---
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


# --- Node Classes Definitions ---
class NNPredictNode(WebNode):
    title = 'NN Predict'
    init_inputs = [
        rc.NodeInputType(label='X'),
        rc.NodeInputType(label='w1'),
        rc.NodeInputType(label='b1'),
        rc.NodeInputType(label='w2'),
        rc.NodeInputType(label='b2'),
        rc.NodeInputType(label='predict', type_='exec')
    ]
    init_outputs = [
        rc.NodeOutputType(label='predictions'),
        rc.NodeOutputType(label='finished', type_='exec')
    ]

    def update_event(self, inp=-1):
        if inp == 5: # predict trigger
            def sigmoid(x):
                return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

            X = self.input(0).payload if self.input(0) else None
            w1 = self.input(1).payload if self.input(1) else None
            b1 = self.input(2).payload if self.input(2) else None
            w2 = self.input(3).payload if self.input(3) else None
            b2 = self.input(4).payload if self.input(4) else None
            
            if X is not None and w1 is not None and b1 is not None and w2 is not None and b2 is not None:
                h = sigmoid(X @ w1 + b1)
                predictions = sigmoid(h @ w2 + b2)
                self.set_output_val(0, rc.Data(predictions))
                self.exec_output(1)


class NNDatasetNode(WebNode):
    title = 'NN Dataset'
    init_inputs = [
        rc.NodeInputType(label='num_samples', default=rc.Data(200)),
        rc.NodeInputType(label='generate', type_='exec')
    ]
    init_outputs = [
        rc.NodeOutputType(label='X'),
        rc.NodeOutputType(label='y'),
        rc.NodeOutputType(label='finished', type_='exec')
    ]

    def update_event(self, inp=-1):
        if inp == 1:
            num = self.input(0).payload if self.input(0) else 200
            np.random.seed(42)
            # Create a simple non-linear dataset (XOR shape)
            X = np.random.uniform(-1, 1, size=(num, 2)).astype(np.float32)
            # y is 1 if XOR-like regions are positive, else 0
            y = ((X[:, 0] > 0) ^ (X[:, 1] > 0)).astype(np.float32).reshape(-1, 1)
            
            self.set_output_val(0, rc.Data(X))
            self.set_output_val(1, rc.Data(y))
            self.exec_output(2)


class NNAccuracyNode(WebNode):
    title = 'NN Accuracy'
    init_inputs = [
        rc.NodeInputType(label='predictions'),
        rc.NodeInputType(label='y'),
        rc.NodeInputType(label='calculate', type_='exec')
    ]
    init_outputs = [
        rc.NodeOutputType(label='accuracy')
    ]

    def update_event(self, inp=-1):
        if inp == 2: # calculate trigger
            preds_data = self.input(0)
            y_data = self.input(1)
            
            if preds_data and preds_data.payload is not None and y_data and y_data.payload is not None:
                preds = preds_data.payload
                y = y_data.payload
                binary_preds = (preds >= 0.5).astype(np.float32)
                accuracy = np.mean(binary_preds == y)
                print(f"[NN Evaluation] Training Accuracy: {accuracy * 100.0:.2f}%")
                self.set_output_val(0, rc.Data(float(accuracy)))


class NNTrainNode(WebNode):
    title = 'NN Train'
    init_inputs = [
        rc.NodeInputType(label='X'),
        rc.NodeInputType(label='y'),
        rc.NodeInputType(label='learning_rate', default=rc.Data(0.1)),
        rc.NodeInputType(label='epochs', default=rc.Data(1000)),
        rc.NodeInputType(label='train', type_='exec')
    ]
    init_outputs = [
        rc.NodeOutputType(label='w1'),
        rc.NodeOutputType(label='b1'),
        rc.NodeOutputType(label='w2'),
        rc.NodeOutputType(label='b2'),
        rc.NodeOutputType(label='finished', type_='exec')
    ]

    def update_event(self, inp=-1):
        if inp == 4: # train trigger
            def sigmoid(x):
                return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

            def sigmoid_derivative(x):
                return x * (1.0 - x)

            X_val = self.input(0)
            y_val = self.input(1)
            lr_val = self.input(2)
            epochs_val = self.input(3)
            
            if X_val and X_val.payload is not None and y_val and y_val.payload is not None:
                X = X_val.payload
                y = y_val.payload
                lr = lr_val.payload if lr_val else 0.1
                epochs = epochs_val.payload if epochs_val else 1000
                
                # Network dimensions
                input_dim = X.shape[1]
                hidden_dim = 8
                output_dim = 1
                
                # Weight initialization
                np.random.seed(42)
                w1 = np.random.normal(0, 0.5, size=(input_dim, hidden_dim)).astype(np.float32)
                b1 = np.zeros((1, hidden_dim), dtype=np.float32)
                w2 = np.random.normal(0, 0.5, size=(hidden_dim, output_dim)).astype(np.float32)
                b2 = np.zeros((1, output_dim), dtype=np.float32)
                
                # Train loops using numpy backpropagation
                for _ in range(epochs):
                    # Forward pass
                    z1 = X @ w1 + b1
                    h1 = sigmoid(z1)
                    z2 = h1 @ w2 + b2
                    o = sigmoid(z2)
                    
                    # Loss (MSE)
                    # loss = np.mean((y - o) ** 2)
                    
                    # Backward pass
                    error = o - y
                    d_z2 = error * sigmoid_derivative(o)
                    d_w2 = h1.T @ d_z2
                    d_b2 = np.sum(d_z2, axis=0, keepdims=True)
                    
                    d_h1 = d_z2 @ w2.T
                    d_z1 = d_h1 * sigmoid_derivative(h1)
                    d_w1 = X.T @ d_z1
                    d_b1 = np.sum(d_z1, axis=0, keepdims=True)
                    
                    # Update weights
                    w1 -= lr * d_w1
                    b1 -= lr * d_b1
                    w2 -= lr * d_w2
                    b2 -= lr * d_b2
                    
                self.set_output_val(0, rc.Data(w1))
                self.set_output_val(1, rc.Data(b1))
                self.set_output_val(2, rc.Data(w2))
                self.set_output_val(3, rc.Data(b2))
                self.exec_output(4)


# --- Flow Execution Instantiation ---
def setup_flow(actual_nodes=None):
    nodes = {}
    flow_alg = 'data'

    # Node: NN Dataset (ID: 5)
    n_5 = NNDatasetNode(params=None)
    n_5.node_id = 5
    n_5.global_id = 5
    n_5.flow_alg = flow_alg
    if actual_nodes and 5 in actual_nodes:
        n_5.actual_node = actual_nodes[5]
    n_5.create_input('num_samples', 'data', default=rc.Data(200))
    n_5.create_input('generate', 'exec', default=rc.Data(None))
    n_5.create_output('X', 'data')
    n_5.create_output('y', 'data')
    n_5.create_output('finished', 'exec')
    n_5.loop_enabled = False
    n_5.loop_interval = 1.0
    n_5.wait_until_complete = False
    n_5.auto_exec_downstream = False
    nodes[5] = n_5

    # Node: NN Train (ID: 6)
    n_6 = NNTrainNode(params=None)
    n_6.node_id = 6
    n_6.global_id = 6
    n_6.flow_alg = flow_alg
    if actual_nodes and 6 in actual_nodes:
        n_6.actual_node = actual_nodes[6]
    n_6.create_input('X', 'data', default=rc.Data(None))
    n_6.create_input('y', 'data', default=rc.Data(None))
    n_6.create_input('learning_rate', 'data', default=rc.Data(0.1))
    n_6.create_input('epochs', 'data', default=rc.Data(1500))
    n_6.create_input('train', 'exec', default=rc.Data(None))
    n_6.create_output('w1', 'data')
    n_6.create_output('b1', 'data')
    n_6.create_output('w2', 'data')
    n_6.create_output('b2', 'data')
    n_6.create_output('finished', 'exec')
    n_6.loop_enabled = False
    n_6.loop_interval = 1.0
    n_6.wait_until_complete = False
    n_6.auto_exec_downstream = False
    nodes[6] = n_6

    # Node: NN Predict (ID: 7)
    n_7 = NNPredictNode(params=None)
    n_7.node_id = 7
    n_7.global_id = 7
    n_7.flow_alg = flow_alg
    if actual_nodes and 7 in actual_nodes:
        n_7.actual_node = actual_nodes[7]
    n_7.create_input('X', 'data', default=rc.Data(None))
    n_7.create_input('w1', 'data', default=rc.Data(None))
    n_7.create_input('b1', 'data', default=rc.Data(None))
    n_7.create_input('w2', 'data', default=rc.Data(None))
    n_7.create_input('b2', 'data', default=rc.Data(None))
    n_7.create_input('predict', 'exec', default=rc.Data(None))
    n_7.create_output('predictions', 'data')
    n_7.create_output('finished', 'exec')
    n_7.loop_enabled = False
    n_7.loop_interval = 1.0
    n_7.wait_until_complete = False
    n_7.auto_exec_downstream = False
    nodes[7] = n_7

    # Node: NN Accuracy (ID: 8)
    n_8 = NNAccuracyNode(params=None)
    n_8.node_id = 8
    n_8.global_id = 8
    n_8.flow_alg = flow_alg
    if actual_nodes and 8 in actual_nodes:
        n_8.actual_node = actual_nodes[8]
    n_8.create_input('predictions', 'data', default=rc.Data(None))
    n_8.create_input('y', 'data', default=rc.Data(None))
    n_8.create_input('calculate', 'exec', default=rc.Data(None))
    n_8.create_output('accuracy', 'data')
    n_8.loop_enabled = False
    n_8.loop_interval = 1.0
    n_8.wait_until_complete = False
    n_8.auto_exec_downstream = False
    nodes[8] = n_8

    # Connections
    nodes[5].connections[0] = [(nodes[6], 0), (nodes[7], 0)]
    nodes[5].connections[1] = [(nodes[6], 1), (nodes[8], 1)]
    nodes[5].connections[2] = [(nodes[6], 4)]
    nodes[6].connections[0] = [(nodes[7], 1)]
    nodes[6].connections[1] = [(nodes[7], 2)]
    nodes[6].connections[2] = [(nodes[7], 3)]
    nodes[6].connections[3] = [(nodes[7], 4)]
    nodes[6].connections[4] = [(nodes[7], 5)]
    nodes[7].connections[0] = [(nodes[8], 0)]
    nodes[7].connections[1] = [(nodes[8], 2)]

    # Run initial placement events
    nodes[5].after_placement()
    nodes[6].after_placement()
    nodes[7].after_placement()
    nodes[8].after_placement()

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
