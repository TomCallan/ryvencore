# Structure Hash: cac7da9682c80f459d5bed21d452b5eaabad62896728a5a5517978358131a124
"""
Compiled ryvencore flow: math_pipeline_bench
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
class NumberNode(WebNode):
    title = 'Number'
    init_inputs = [rc.NodeInputType(label='val', default=rc.Data(0.0))]
    init_outputs = [rc.NodeOutputType(label='val')]

    def update_event(self, inp=-1):
        self.set_output_val(0, self.input(0))


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


class TriggerNode(WebNode):
    title = 'Trigger'
    init_inputs = []
    init_outputs = [rc.NodeOutputType(type_='exec', label='out')]

    def update_event(self, inp=-1):
        self.exec_output(0)


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


class MultiplyNode(WebNode):
    title = 'Multiply'
    init_inputs = [
        rc.NodeInputType(label='A', default=rc.Data(0.0)),
        rc.NodeInputType(label='B', default=rc.Data(0.0))
    ]
    init_outputs = [rc.NodeOutputType(label='prod')]

    def update_event(self, inp=-1):
        a = self.input(0).payload if self.input(0) else 0.0
        b = self.input(1).payload if self.input(1) else 0.0
        try: a = float(a)
        except: pass
        try: b = float(b)
        except: pass
        self.set_output_val(0, rc.Data(a * b))


class AddNode(WebNode):
    title = 'Add'
    init_inputs = [
        rc.NodeInputType(label='A', default=rc.Data(0.0)),
        rc.NodeInputType(label='B', default=rc.Data(0.0))
    ]
    init_outputs = [rc.NodeOutputType(label='sum')]

    def update_event(self, inp=-1):
        a = self.input(0).payload if self.input(0) else 0.0
        b = self.input(1).payload if self.input(1) else 0.0
        try: a = float(a)
        except: pass
        try: b = float(b)
        except: pass
        self.set_output_val(0, rc.Data(a + b))


# --- Flow Execution Instantiation ---
def setup_flow(actual_nodes=None):
    nodes = {}
    flow_alg = 'data'

    # Node: Trigger (ID: 31)
    n_31 = TriggerNode(params=None)
    n_31.node_id = 31
    n_31.global_id = 31
    n_31.flow_alg = flow_alg
    if actual_nodes and 31 in actual_nodes:
        n_31.actual_node = actual_nodes[31]
    n_31.create_output('out', 'exec')
    n_31.loop_enabled = False
    n_31.loop_interval = 1.0
    n_31.wait_until_complete = False
    n_31.auto_exec_downstream = False
    nodes[31] = n_31

    # Node: Execution Timer (ID: 32)
    n_32 = ExecutionTimerNode(params=None)
    n_32.node_id = 32
    n_32.global_id = 32
    n_32.flow_alg = flow_alg
    if actual_nodes and 32 in actual_nodes:
        n_32.actual_node = actual_nodes[32]
    n_32.create_input('trigger', 'exec', default=rc.Data(None))
    n_32.create_output('out', 'exec')
    n_32.create_output('time_ms', 'data')
    n_32.loop_enabled = False
    n_32.loop_interval = 1.0
    n_32.wait_until_complete = False
    n_32.auto_exec_downstream = False
    nodes[32] = n_32

    # Node: Number (ID: 33)
    n_33 = NumberNode(params=None)
    n_33.node_id = 33
    n_33.global_id = 33
    n_33.flow_alg = flow_alg
    if actual_nodes and 33 in actual_nodes:
        n_33.actual_node = actual_nodes[33]
    n_33.create_input('val', 'data', default=rc.Data(10.0))
    n_33.create_output('val', 'data')
    n_33.loop_enabled = False
    n_33.loop_interval = 1.0
    n_33.wait_until_complete = False
    n_33.auto_exec_downstream = False
    nodes[33] = n_33

    # Node: Number (ID: 34)
    n_34 = NumberNode(params=None)
    n_34.node_id = 34
    n_34.global_id = 34
    n_34.flow_alg = flow_alg
    if actual_nodes and 34 in actual_nodes:
        n_34.actual_node = actual_nodes[34]
    n_34.create_input('val', 'data', default=rc.Data(5.0))
    n_34.create_output('val', 'data')
    n_34.loop_enabled = False
    n_34.loop_interval = 1.0
    n_34.wait_until_complete = False
    n_34.auto_exec_downstream = False
    nodes[34] = n_34

    # Node: Multiply (ID: 35)
    n_35 = MultiplyNode(params=None)
    n_35.node_id = 35
    n_35.global_id = 35
    n_35.flow_alg = flow_alg
    if actual_nodes and 35 in actual_nodes:
        n_35.actual_node = actual_nodes[35]
    n_35.create_input('A', 'data', default=rc.Data(0.0))
    n_35.create_input('B', 'data', default=rc.Data(0.0))
    n_35.create_output('prod', 'data')
    n_35.loop_enabled = False
    n_35.loop_interval = 1.0
    n_35.wait_until_complete = False
    n_35.auto_exec_downstream = False
    nodes[35] = n_35

    # Node: Add (ID: 36)
    n_36 = AddNode(params=None)
    n_36.node_id = 36
    n_36.global_id = 36
    n_36.flow_alg = flow_alg
    if actual_nodes and 36 in actual_nodes:
        n_36.actual_node = actual_nodes[36]
    n_36.create_input('A', 'data', default=rc.Data(0.0))
    n_36.create_input('B', 'data', default=rc.Data(0.0))
    n_36.create_output('sum', 'data')
    n_36.loop_enabled = False
    n_36.loop_interval = 1.0
    n_36.wait_until_complete = False
    n_36.auto_exec_downstream = False
    nodes[36] = n_36

    # Node: Log (ID: 30)
    n_30 = LogNode(params=None)
    n_30.node_id = 30
    n_30.global_id = 30
    n_30.flow_alg = flow_alg
    if actual_nodes and 30 in actual_nodes:
        n_30.actual_node = actual_nodes[30]
    n_30.create_input('msg', 'data', default=rc.Data(''))
    n_30.create_output('out', 'data')
    n_30.loop_enabled = False
    n_30.loop_interval = 1.0
    n_30.wait_until_complete = False
    n_30.auto_exec_downstream = False
    nodes[30] = n_30

    # Connections
    nodes[31].connections[0] = [(nodes[32], 0)]
    nodes[33].connections[0] = [(nodes[36], 0)]
    nodes[34].connections[0] = [(nodes[35], 0)]
    nodes[35].connections[0] = [(nodes[36], 1)]
    nodes[36].connections[0] = [(nodes[30], 0)]

    # Run initial placement events
    nodes[31].after_placement()
    nodes[32].after_placement()
    nodes[33].after_placement()
    nodes[34].after_placement()
    nodes[35].after_placement()
    nodes[36].after_placement()
    nodes[30].after_placement()

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
