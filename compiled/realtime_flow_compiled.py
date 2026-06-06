# Structure Hash: 444752e478616359352b444911b65ebc5fce2d3198eccd4237f93a259d2e5f5d
"""
Compiled ryvencore flow: realtime_flow
Generated automatically by FlowCompiler.
"""
import sys
import time
import os

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
class CompareNode(WebNode):
    title = 'Compare'
    init_inputs = [
        rc.NodeInputType(label='A', default=rc.Data(0.0)),
        rc.NodeInputType(label='op (==, >, <)', default=rc.Data('==')),
        rc.NodeInputType(label='B', default=rc.Data(0.0))
    ]
    init_outputs = [rc.NodeOutputType(label='res')]

    def update_event(self, inp=-1):
        a = self.input(0).payload if self.input(0) else 0.0
        op = str(self.input(1).payload if self.input(1) else '==').strip()
        b = self.input(2).payload if self.input(2) else 0.0
        try:
            a = float(a)
            b = float(b)
        except:
            pass
        
        if op == '==': res = (a == b)
        elif op == '>': res = (a > b)
        elif op == '<': res = (a < b)
        elif op == '>=': res = (a >= b)
        elif op == '<=': res = (a <= b)
        elif op == '!=': res = (a != b)
        else: res = False
        self.set_output_val(0, rc.Data(res))


class RandomNode(WebNode):
    title = 'Random'
    init_inputs = [
        rc.NodeInputType(label='min', default=rc.Data(0.0)),
        rc.NodeInputType(label='max', default=rc.Data(1.0))
    ]
    init_outputs = [rc.NodeOutputType(label='val')]

    def update_event(self, inp=-1):
        import random
        min_v = float(self.input(0).payload if self.input(0) else 0.0)
        max_v = float(self.input(1).payload if self.input(1) else 1.0)
        self.set_output_val(0, rc.Data(random.uniform(min_v, max_v)))


class IfElseNode(WebNode):
    title = 'If/Else'
    init_inputs = [
        rc.NodeInputType(label='cond', default=rc.Data(False)),
        rc.NodeInputType(label='true_val', default=rc.Data('True')),
        rc.NodeInputType(label='false_val', default=rc.Data('False'))
    ]
    init_outputs = [rc.NodeOutputType(label='out')]

    def update_event(self, inp=-1):
        cond = bool(self.input(0).payload if self.input(0) else False)
        t_val = self.input(1).payload if self.input(1) else None
        f_val = self.input(2).payload if self.input(2) else None
        self.set_output_val(0, rc.Data(t_val if cond else f_val))


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


# --- Flow Execution Instantiation ---
def setup_flow(actual_nodes=None):
    nodes = {}
    flow_alg = 'data'

    # Node: Random (ID: 5)
    n_5 = RandomNode(params=None)
    n_5.node_id = 5
    n_5.global_id = 5
    n_5.flow_alg = flow_alg
    if actual_nodes and 5 in actual_nodes:
        n_5.actual_node = actual_nodes[5]
    n_5.create_input('min', 'data', default=rc.Data(10.0))
    n_5.create_input('max', 'data', default=rc.Data(100.0))
    n_5.create_output('val', 'data')
    n_5.loop_enabled = True
    n_5.loop_interval = 0.05
    n_5.wait_until_complete = True
    nodes[5] = n_5

    # Node: Compare (ID: 6)
    n_6 = CompareNode(params=None)
    n_6.node_id = 6
    n_6.global_id = 6
    n_6.flow_alg = flow_alg
    if actual_nodes and 6 in actual_nodes:
        n_6.actual_node = actual_nodes[6]
    n_6.create_input('A', 'data', default=rc.Data(0.0))
    n_6.create_input('op (==, >, <)', 'data', default=rc.Data('>'))
    n_6.create_input('B', 'data', default=rc.Data(80.0))
    n_6.create_output('res', 'data')
    n_6.loop_enabled = False
    n_6.loop_interval = 1.0
    n_6.wait_until_complete = False
    nodes[6] = n_6

    # Node: If/Else (ID: 7)
    n_7 = IfElseNode(params=None)
    n_7.node_id = 7
    n_7.global_id = 7
    n_7.flow_alg = flow_alg
    if actual_nodes and 7 in actual_nodes:
        n_7.actual_node = actual_nodes[7]
    n_7.create_input('cond', 'data', default=rc.Data(False))
    n_7.create_input('true_val', 'data', default=rc.Data('SELL SIGNAL (Price > 80)'))
    n_7.create_input('false_val', 'data', default=rc.Data('HOLD'))
    n_7.create_output('out', 'data')
    n_7.loop_enabled = False
    n_7.loop_interval = 1.0
    n_7.wait_until_complete = False
    nodes[7] = n_7

    # Node: Log (ID: 8)
    n_8 = LogNode(params=None)
    n_8.node_id = 8
    n_8.global_id = 8
    n_8.flow_alg = flow_alg
    if actual_nodes and 8 in actual_nodes:
        n_8.actual_node = actual_nodes[8]
    n_8.create_input('msg', 'data', default=rc.Data(''))
    n_8.create_output('out', 'data')
    n_8.loop_enabled = False
    n_8.loop_interval = 1.0
    n_8.wait_until_complete = False
    nodes[8] = n_8

    # Connections
    nodes[5].connections[0] = [(nodes[6], 0), (nodes[7], 1)]
    nodes[6].connections[0] = [(nodes[7], 0)]
    nodes[7].connections[0] = [(nodes[8], 0)]

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
