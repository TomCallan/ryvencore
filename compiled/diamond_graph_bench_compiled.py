# Structure Hash: d57e9e42c7838748314aedd61ff3f41cf6bd60f3a2362e9f4843aa2c05d464c2
"""
Compiled ryvencore flow: diamond_graph_bench
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

    # Node: Trigger (ID: 1)
    n_1 = TriggerNode(params=None)
    n_1.node_id = 1
    n_1.global_id = 1
    n_1.flow_alg = flow_alg
    if actual_nodes and 1 in actual_nodes:
        n_1.actual_node = actual_nodes[1]
    n_1.create_output('out', 'exec')
    n_1.loop_enabled = False
    n_1.loop_interval = 1.0
    n_1.wait_until_complete = False
    n_1.auto_exec_downstream = False
    nodes[1] = n_1

    # Node: Execution Timer (ID: 2)
    n_2 = ExecutionTimerNode(params=None)
    n_2.node_id = 2
    n_2.global_id = 2
    n_2.flow_alg = flow_alg
    if actual_nodes and 2 in actual_nodes:
        n_2.actual_node = actual_nodes[2]
    n_2.create_input('trigger', 'exec', default=rc.Data(None))
    n_2.create_output('out', 'exec')
    n_2.create_output('time_ms', 'data')
    n_2.loop_enabled = False
    n_2.loop_interval = 1.0
    n_2.wait_until_complete = False
    n_2.auto_exec_downstream = False
    nodes[2] = n_2

    # Node: Input_0 (ID: 3)
    n_3 = NumberNode(params=None)
    n_3.node_id = 3
    n_3.global_id = 3
    n_3.flow_alg = flow_alg
    if actual_nodes and 3 in actual_nodes:
        n_3.actual_node = actual_nodes[3]
    n_3.create_input('val', 'data', default=rc.Data(1.0))
    n_3.create_output('val', 'data')
    n_3.loop_enabled = False
    n_3.loop_interval = 1.0
    n_3.wait_until_complete = False
    n_3.auto_exec_downstream = False
    nodes[3] = n_3

    # Node: Input_1 (ID: 4)
    n_4 = NumberNode(params=None)
    n_4.node_id = 4
    n_4.global_id = 4
    n_4.flow_alg = flow_alg
    if actual_nodes and 4 in actual_nodes:
        n_4.actual_node = actual_nodes[4]
    n_4.create_input('val', 'data', default=rc.Data(2.0))
    n_4.create_output('val', 'data')
    n_4.loop_enabled = False
    n_4.loop_interval = 1.0
    n_4.wait_until_complete = False
    n_4.auto_exec_downstream = False
    nodes[4] = n_4

    # Node: Input_2 (ID: 5)
    n_5 = NumberNode(params=None)
    n_5.node_id = 5
    n_5.global_id = 5
    n_5.flow_alg = flow_alg
    if actual_nodes and 5 in actual_nodes:
        n_5.actual_node = actual_nodes[5]
    n_5.create_input('val', 'data', default=rc.Data(3.0))
    n_5.create_output('val', 'data')
    n_5.loop_enabled = False
    n_5.loop_interval = 1.0
    n_5.wait_until_complete = False
    n_5.auto_exec_downstream = False
    nodes[5] = n_5

    # Node: L0_N0 (ID: 6)
    n_6 = AddNode(params=None)
    n_6.node_id = 6
    n_6.global_id = 6
    n_6.flow_alg = flow_alg
    if actual_nodes and 6 in actual_nodes:
        n_6.actual_node = actual_nodes[6]
    n_6.create_input('A', 'data', default=rc.Data(0.0))
    n_6.create_input('B', 'data', default=rc.Data(0.0))
    n_6.create_output('sum', 'data')
    n_6.loop_enabled = False
    n_6.loop_interval = 1.0
    n_6.wait_until_complete = False
    n_6.auto_exec_downstream = False
    nodes[6] = n_6

    # Node: L0_N1 (ID: 7)
    n_7 = MultiplyNode(params=None)
    n_7.node_id = 7
    n_7.global_id = 7
    n_7.flow_alg = flow_alg
    if actual_nodes and 7 in actual_nodes:
        n_7.actual_node = actual_nodes[7]
    n_7.create_input('A', 'data', default=rc.Data(0.0))
    n_7.create_input('B', 'data', default=rc.Data(0.0))
    n_7.create_output('prod', 'data')
    n_7.loop_enabled = False
    n_7.loop_interval = 1.0
    n_7.wait_until_complete = False
    n_7.auto_exec_downstream = False
    nodes[7] = n_7

    # Node: L0_N2 (ID: 8)
    n_8 = AddNode(params=None)
    n_8.node_id = 8
    n_8.global_id = 8
    n_8.flow_alg = flow_alg
    if actual_nodes and 8 in actual_nodes:
        n_8.actual_node = actual_nodes[8]
    n_8.create_input('A', 'data', default=rc.Data(0.0))
    n_8.create_input('B', 'data', default=rc.Data(0.0))
    n_8.create_output('sum', 'data')
    n_8.loop_enabled = False
    n_8.loop_interval = 1.0
    n_8.wait_until_complete = False
    n_8.auto_exec_downstream = False
    nodes[8] = n_8

    # Node: L1_N0 (ID: 9)
    n_9 = MultiplyNode(params=None)
    n_9.node_id = 9
    n_9.global_id = 9
    n_9.flow_alg = flow_alg
    if actual_nodes and 9 in actual_nodes:
        n_9.actual_node = actual_nodes[9]
    n_9.create_input('A', 'data', default=rc.Data(0.0))
    n_9.create_input('B', 'data', default=rc.Data(0.0))
    n_9.create_output('prod', 'data')
    n_9.loop_enabled = False
    n_9.loop_interval = 1.0
    n_9.wait_until_complete = False
    n_9.auto_exec_downstream = False
    nodes[9] = n_9

    # Node: L1_N1 (ID: 10)
    n_10 = AddNode(params=None)
    n_10.node_id = 10
    n_10.global_id = 10
    n_10.flow_alg = flow_alg
    if actual_nodes and 10 in actual_nodes:
        n_10.actual_node = actual_nodes[10]
    n_10.create_input('A', 'data', default=rc.Data(0.0))
    n_10.create_input('B', 'data', default=rc.Data(0.0))
    n_10.create_output('sum', 'data')
    n_10.loop_enabled = False
    n_10.loop_interval = 1.0
    n_10.wait_until_complete = False
    n_10.auto_exec_downstream = False
    nodes[10] = n_10

    # Node: L1_N2 (ID: 11)
    n_11 = MultiplyNode(params=None)
    n_11.node_id = 11
    n_11.global_id = 11
    n_11.flow_alg = flow_alg
    if actual_nodes and 11 in actual_nodes:
        n_11.actual_node = actual_nodes[11]
    n_11.create_input('A', 'data', default=rc.Data(0.0))
    n_11.create_input('B', 'data', default=rc.Data(0.0))
    n_11.create_output('prod', 'data')
    n_11.loop_enabled = False
    n_11.loop_interval = 1.0
    n_11.wait_until_complete = False
    n_11.auto_exec_downstream = False
    nodes[11] = n_11

    # Node: L2_N0 (ID: 12)
    n_12 = AddNode(params=None)
    n_12.node_id = 12
    n_12.global_id = 12
    n_12.flow_alg = flow_alg
    if actual_nodes and 12 in actual_nodes:
        n_12.actual_node = actual_nodes[12]
    n_12.create_input('A', 'data', default=rc.Data(0.0))
    n_12.create_input('B', 'data', default=rc.Data(0.0))
    n_12.create_output('sum', 'data')
    n_12.loop_enabled = False
    n_12.loop_interval = 1.0
    n_12.wait_until_complete = False
    n_12.auto_exec_downstream = False
    nodes[12] = n_12

    # Node: L2_N1 (ID: 13)
    n_13 = MultiplyNode(params=None)
    n_13.node_id = 13
    n_13.global_id = 13
    n_13.flow_alg = flow_alg
    if actual_nodes and 13 in actual_nodes:
        n_13.actual_node = actual_nodes[13]
    n_13.create_input('A', 'data', default=rc.Data(0.0))
    n_13.create_input('B', 'data', default=rc.Data(0.0))
    n_13.create_output('prod', 'data')
    n_13.loop_enabled = False
    n_13.loop_interval = 1.0
    n_13.wait_until_complete = False
    n_13.auto_exec_downstream = False
    nodes[13] = n_13

    # Node: L2_N2 (ID: 14)
    n_14 = AddNode(params=None)
    n_14.node_id = 14
    n_14.global_id = 14
    n_14.flow_alg = flow_alg
    if actual_nodes and 14 in actual_nodes:
        n_14.actual_node = actual_nodes[14]
    n_14.create_input('A', 'data', default=rc.Data(0.0))
    n_14.create_input('B', 'data', default=rc.Data(0.0))
    n_14.create_output('sum', 'data')
    n_14.loop_enabled = False
    n_14.loop_interval = 1.0
    n_14.wait_until_complete = False
    n_14.auto_exec_downstream = False
    nodes[14] = n_14

    # Node: L3_N0 (ID: 15)
    n_15 = MultiplyNode(params=None)
    n_15.node_id = 15
    n_15.global_id = 15
    n_15.flow_alg = flow_alg
    if actual_nodes and 15 in actual_nodes:
        n_15.actual_node = actual_nodes[15]
    n_15.create_input('A', 'data', default=rc.Data(0.0))
    n_15.create_input('B', 'data', default=rc.Data(0.0))
    n_15.create_output('prod', 'data')
    n_15.loop_enabled = False
    n_15.loop_interval = 1.0
    n_15.wait_until_complete = False
    n_15.auto_exec_downstream = False
    nodes[15] = n_15

    # Node: L3_N1 (ID: 16)
    n_16 = AddNode(params=None)
    n_16.node_id = 16
    n_16.global_id = 16
    n_16.flow_alg = flow_alg
    if actual_nodes and 16 in actual_nodes:
        n_16.actual_node = actual_nodes[16]
    n_16.create_input('A', 'data', default=rc.Data(0.0))
    n_16.create_input('B', 'data', default=rc.Data(0.0))
    n_16.create_output('sum', 'data')
    n_16.loop_enabled = False
    n_16.loop_interval = 1.0
    n_16.wait_until_complete = False
    n_16.auto_exec_downstream = False
    nodes[16] = n_16

    # Node: L3_N2 (ID: 17)
    n_17 = MultiplyNode(params=None)
    n_17.node_id = 17
    n_17.global_id = 17
    n_17.flow_alg = flow_alg
    if actual_nodes and 17 in actual_nodes:
        n_17.actual_node = actual_nodes[17]
    n_17.create_input('A', 'data', default=rc.Data(0.0))
    n_17.create_input('B', 'data', default=rc.Data(0.0))
    n_17.create_output('prod', 'data')
    n_17.loop_enabled = False
    n_17.loop_interval = 1.0
    n_17.wait_until_complete = False
    n_17.auto_exec_downstream = False
    nodes[17] = n_17

    # Node: L4_N0 (ID: 18)
    n_18 = AddNode(params=None)
    n_18.node_id = 18
    n_18.global_id = 18
    n_18.flow_alg = flow_alg
    if actual_nodes and 18 in actual_nodes:
        n_18.actual_node = actual_nodes[18]
    n_18.create_input('A', 'data', default=rc.Data(0.0))
    n_18.create_input('B', 'data', default=rc.Data(0.0))
    n_18.create_output('sum', 'data')
    n_18.loop_enabled = False
    n_18.loop_interval = 1.0
    n_18.wait_until_complete = False
    n_18.auto_exec_downstream = False
    nodes[18] = n_18

    # Node: L4_N1 (ID: 19)
    n_19 = MultiplyNode(params=None)
    n_19.node_id = 19
    n_19.global_id = 19
    n_19.flow_alg = flow_alg
    if actual_nodes and 19 in actual_nodes:
        n_19.actual_node = actual_nodes[19]
    n_19.create_input('A', 'data', default=rc.Data(0.0))
    n_19.create_input('B', 'data', default=rc.Data(0.0))
    n_19.create_output('prod', 'data')
    n_19.loop_enabled = False
    n_19.loop_interval = 1.0
    n_19.wait_until_complete = False
    n_19.auto_exec_downstream = False
    nodes[19] = n_19

    # Node: L4_N2 (ID: 20)
    n_20 = AddNode(params=None)
    n_20.node_id = 20
    n_20.global_id = 20
    n_20.flow_alg = flow_alg
    if actual_nodes and 20 in actual_nodes:
        n_20.actual_node = actual_nodes[20]
    n_20.create_input('A', 'data', default=rc.Data(0.0))
    n_20.create_input('B', 'data', default=rc.Data(0.0))
    n_20.create_output('sum', 'data')
    n_20.loop_enabled = False
    n_20.loop_interval = 1.0
    n_20.wait_until_complete = False
    n_20.auto_exec_downstream = False
    nodes[20] = n_20

    # Node: L5_N0 (ID: 21)
    n_21 = MultiplyNode(params=None)
    n_21.node_id = 21
    n_21.global_id = 21
    n_21.flow_alg = flow_alg
    if actual_nodes and 21 in actual_nodes:
        n_21.actual_node = actual_nodes[21]
    n_21.create_input('A', 'data', default=rc.Data(0.0))
    n_21.create_input('B', 'data', default=rc.Data(0.0))
    n_21.create_output('prod', 'data')
    n_21.loop_enabled = False
    n_21.loop_interval = 1.0
    n_21.wait_until_complete = False
    n_21.auto_exec_downstream = False
    nodes[21] = n_21

    # Node: L5_N1 (ID: 22)
    n_22 = AddNode(params=None)
    n_22.node_id = 22
    n_22.global_id = 22
    n_22.flow_alg = flow_alg
    if actual_nodes and 22 in actual_nodes:
        n_22.actual_node = actual_nodes[22]
    n_22.create_input('A', 'data', default=rc.Data(0.0))
    n_22.create_input('B', 'data', default=rc.Data(0.0))
    n_22.create_output('sum', 'data')
    n_22.loop_enabled = False
    n_22.loop_interval = 1.0
    n_22.wait_until_complete = False
    n_22.auto_exec_downstream = False
    nodes[22] = n_22

    # Node: L5_N2 (ID: 23)
    n_23 = MultiplyNode(params=None)
    n_23.node_id = 23
    n_23.global_id = 23
    n_23.flow_alg = flow_alg
    if actual_nodes and 23 in actual_nodes:
        n_23.actual_node = actual_nodes[23]
    n_23.create_input('A', 'data', default=rc.Data(0.0))
    n_23.create_input('B', 'data', default=rc.Data(0.0))
    n_23.create_output('prod', 'data')
    n_23.loop_enabled = False
    n_23.loop_interval = 1.0
    n_23.wait_until_complete = False
    n_23.auto_exec_downstream = False
    nodes[23] = n_23

    # Node: L6_N0 (ID: 24)
    n_24 = AddNode(params=None)
    n_24.node_id = 24
    n_24.global_id = 24
    n_24.flow_alg = flow_alg
    if actual_nodes and 24 in actual_nodes:
        n_24.actual_node = actual_nodes[24]
    n_24.create_input('A', 'data', default=rc.Data(0.0))
    n_24.create_input('B', 'data', default=rc.Data(0.0))
    n_24.create_output('sum', 'data')
    n_24.loop_enabled = False
    n_24.loop_interval = 1.0
    n_24.wait_until_complete = False
    n_24.auto_exec_downstream = False
    nodes[24] = n_24

    # Node: L6_N1 (ID: 25)
    n_25 = MultiplyNode(params=None)
    n_25.node_id = 25
    n_25.global_id = 25
    n_25.flow_alg = flow_alg
    if actual_nodes and 25 in actual_nodes:
        n_25.actual_node = actual_nodes[25]
    n_25.create_input('A', 'data', default=rc.Data(0.0))
    n_25.create_input('B', 'data', default=rc.Data(0.0))
    n_25.create_output('prod', 'data')
    n_25.loop_enabled = False
    n_25.loop_interval = 1.0
    n_25.wait_until_complete = False
    n_25.auto_exec_downstream = False
    nodes[25] = n_25

    # Node: L6_N2 (ID: 26)
    n_26 = AddNode(params=None)
    n_26.node_id = 26
    n_26.global_id = 26
    n_26.flow_alg = flow_alg
    if actual_nodes and 26 in actual_nodes:
        n_26.actual_node = actual_nodes[26]
    n_26.create_input('A', 'data', default=rc.Data(0.0))
    n_26.create_input('B', 'data', default=rc.Data(0.0))
    n_26.create_output('sum', 'data')
    n_26.loop_enabled = False
    n_26.loop_interval = 1.0
    n_26.wait_until_complete = False
    n_26.auto_exec_downstream = False
    nodes[26] = n_26

    # Node: L7_N0 (ID: 27)
    n_27 = MultiplyNode(params=None)
    n_27.node_id = 27
    n_27.global_id = 27
    n_27.flow_alg = flow_alg
    if actual_nodes and 27 in actual_nodes:
        n_27.actual_node = actual_nodes[27]
    n_27.create_input('A', 'data', default=rc.Data(0.0))
    n_27.create_input('B', 'data', default=rc.Data(0.0))
    n_27.create_output('prod', 'data')
    n_27.loop_enabled = False
    n_27.loop_interval = 1.0
    n_27.wait_until_complete = False
    n_27.auto_exec_downstream = False
    nodes[27] = n_27

    # Node: L7_N1 (ID: 28)
    n_28 = AddNode(params=None)
    n_28.node_id = 28
    n_28.global_id = 28
    n_28.flow_alg = flow_alg
    if actual_nodes and 28 in actual_nodes:
        n_28.actual_node = actual_nodes[28]
    n_28.create_input('A', 'data', default=rc.Data(0.0))
    n_28.create_input('B', 'data', default=rc.Data(0.0))
    n_28.create_output('sum', 'data')
    n_28.loop_enabled = False
    n_28.loop_interval = 1.0
    n_28.wait_until_complete = False
    n_28.auto_exec_downstream = False
    nodes[28] = n_28

    # Node: L7_N2 (ID: 29)
    n_29 = MultiplyNode(params=None)
    n_29.node_id = 29
    n_29.global_id = 29
    n_29.flow_alg = flow_alg
    if actual_nodes and 29 in actual_nodes:
        n_29.actual_node = actual_nodes[29]
    n_29.create_input('A', 'data', default=rc.Data(0.0))
    n_29.create_input('B', 'data', default=rc.Data(0.0))
    n_29.create_output('prod', 'data')
    n_29.loop_enabled = False
    n_29.loop_interval = 1.0
    n_29.wait_until_complete = False
    n_29.auto_exec_downstream = False
    nodes[29] = n_29

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

    # Connections
    nodes[1].connections[0] = [(nodes[2], 0)]
    nodes[2].connections[1] = [(nodes[0], 0)]
    nodes[3].connections[0] = [(nodes[6], 0), (nodes[7], 0), (nodes[8], 0)]
    nodes[4].connections[0] = [(nodes[6], 1), (nodes[7], 1), (nodes[8], 1)]
    nodes[5].connections[0] = [(nodes[6], 0), (nodes[7], 0), (nodes[8], 0)]
    nodes[6].connections[0] = [(nodes[9], 0), (nodes[10], 0), (nodes[11], 0)]
    nodes[7].connections[0] = [(nodes[9], 1), (nodes[10], 1), (nodes[11], 1)]
    nodes[8].connections[0] = [(nodes[9], 0), (nodes[10], 0), (nodes[11], 0)]
    nodes[9].connections[0] = [(nodes[12], 0), (nodes[13], 0), (nodes[14], 0)]
    nodes[10].connections[0] = [(nodes[12], 1), (nodes[13], 1), (nodes[14], 1)]
    nodes[11].connections[0] = [(nodes[12], 0), (nodes[13], 0), (nodes[14], 0)]
    nodes[12].connections[0] = [(nodes[15], 0), (nodes[16], 0), (nodes[17], 0)]
    nodes[13].connections[0] = [(nodes[15], 1), (nodes[16], 1), (nodes[17], 1)]
    nodes[14].connections[0] = [(nodes[15], 0), (nodes[16], 0), (nodes[17], 0)]
    nodes[15].connections[0] = [(nodes[18], 0), (nodes[19], 0), (nodes[20], 0)]
    nodes[16].connections[0] = [(nodes[18], 1), (nodes[19], 1), (nodes[20], 1)]
    nodes[17].connections[0] = [(nodes[18], 0), (nodes[19], 0), (nodes[20], 0)]
    nodes[18].connections[0] = [(nodes[21], 0), (nodes[22], 0), (nodes[23], 0)]
    nodes[19].connections[0] = [(nodes[21], 1), (nodes[22], 1), (nodes[23], 1)]
    nodes[20].connections[0] = [(nodes[21], 0), (nodes[22], 0), (nodes[23], 0)]
    nodes[21].connections[0] = [(nodes[24], 0), (nodes[25], 0), (nodes[26], 0)]
    nodes[22].connections[0] = [(nodes[24], 1), (nodes[25], 1), (nodes[26], 1)]
    nodes[23].connections[0] = [(nodes[24], 0), (nodes[25], 0), (nodes[26], 0)]
    nodes[24].connections[0] = [(nodes[27], 0), (nodes[28], 0), (nodes[29], 0)]
    nodes[25].connections[0] = [(nodes[27], 1), (nodes[28], 1), (nodes[29], 1)]
    nodes[26].connections[0] = [(nodes[27], 0), (nodes[28], 0), (nodes[29], 0)]
    nodes[27].connections[0] = [(nodes[0], 0)]

    # Run initial placement events
    nodes[1].after_placement()
    nodes[2].after_placement()
    nodes[3].after_placement()
    nodes[4].after_placement()
    nodes[5].after_placement()
    nodes[6].after_placement()
    nodes[7].after_placement()
    nodes[8].after_placement()
    nodes[9].after_placement()
    nodes[10].after_placement()
    nodes[11].after_placement()
    nodes[12].after_placement()
    nodes[13].after_placement()
    nodes[14].after_placement()
    nodes[15].after_placement()
    nodes[16].after_placement()
    nodes[17].after_placement()
    nodes[18].after_placement()
    nodes[19].after_placement()
    nodes[20].after_placement()
    nodes[21].after_placement()
    nodes[22].after_placement()
    nodes[23].after_placement()
    nodes[24].after_placement()
    nodes[25].after_placement()
    nodes[26].after_placement()
    nodes[27].after_placement()
    nodes[28].after_placement()
    nodes[29].after_placement()
    nodes[0].after_placement()

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
