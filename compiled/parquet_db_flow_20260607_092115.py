# Structure Hash: 0daa629b723c6ec139a3126bc2d007948dfc5388dbbfc8da09f1fd4742e7fad4
"""
Compiled ryvencore flow: parquet_db_flow
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


class DuckDBQueryNode(WebNode):
    title = 'DuckDB Query'
    init_inputs = [
        rc.NodeInputType(label='database', default=rc.Data(':memory:')),
        rc.NodeInputType(label='query', default=rc.Data('SELECT 1 as val'))
    ]
    init_outputs = [
        rc.NodeOutputType(label='info'),
        rc.NodeOutputType(label='data')
    ]

    def update_event(self, inp=-1):
        db_path = self.input(0).payload if self.input(0) else ':memory:'
        query = self.input(1).payload if self.input(1) else ''

        if not query:
            self.set_output_val(0, rc.Data('No query provided'))
            self.set_output_val(1, rc.Data([]))
            return

        try:
            import duckdb
        except ImportError:
            self.set_output_val(0, rc.Data("duckdb is not installed. Please install it."))
            self.set_output_val(1, rc.Data([]))
            return

        try:
            conn = duckdb.connect(database=db_path)
            res = conn.execute(query)
            cols = [desc[0] for desc in res.description]
            rows = res.fetchall()
            
            summary = f"DuckDB query success. Columns: {cols}. Rows: {len(rows)}"
            dict_data = [dict(zip(cols, row)) for row in rows]
            
            self.set_output_val(0, rc.Data(summary))
            self.set_output_val(1, rc.Data(dict_data))
            conn.close()
        except Exception as e:
            self.set_output_val(0, rc.Data(f"Error: {str(e)}"))
            self.set_output_val(1, rc.Data([]))


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


# --- Flow Execution Instantiation ---
def setup_flow(actual_nodes=None):
    nodes = {}
    flow_alg = 'compiled'

    # Node: Trigger (ID: 0)
    n_0 = TriggerNode(params=None)
    n_0.node_id = 0
    n_0.global_id = 0
    n_0.flow_alg = flow_alg
    if actual_nodes and 0 in actual_nodes:
        n_0.actual_node = actual_nodes[0]
    n_0.create_output('out', 'exec')
    n_0.loop_enabled = False
    n_0.loop_interval = 1.0
    n_0.wait_until_complete = False
    n_0.auto_exec_downstream = False
    nodes[0] = n_0

    # Node: Execution Timer (ID: 1)
    n_1 = ExecutionTimerNode(params=None)
    n_1.node_id = 1
    n_1.global_id = 1
    n_1.flow_alg = flow_alg
    if actual_nodes and 1 in actual_nodes:
        n_1.actual_node = actual_nodes[1]
    n_1.create_input('trigger', 'exec', default=rc.Data(None))
    n_1.create_output('out', 'exec')
    n_1.create_output('time_ms', 'data')
    n_1.loop_enabled = False
    n_1.loop_interval = 1.0
    n_1.wait_until_complete = False
    n_1.auto_exec_downstream = False
    nodes[1] = n_1

    # Node: DuckDB Query (ID: 2)
    n_2 = DuckDBQueryNode(params=None)
    n_2.node_id = 2
    n_2.global_id = 2
    n_2.flow_alg = flow_alg
    if actual_nodes and 2 in actual_nodes:
        n_2.actual_node = actual_nodes[2]
    n_2.create_input('database', 'data', default=rc.Data(':memory:'))
    n_2.create_input('query', 'data', default=rc.Data('SELECT 1 as val'))
    n_2.create_output('info', 'data')
    n_2.create_output('data', 'data')
    n_2.loop_enabled = False
    n_2.loop_interval = 1.0
    n_2.wait_until_complete = False
    n_2.auto_exec_downstream = False
    nodes[2] = n_2

    # Node: DuckDB Query (ID: 3)
    n_3 = DuckDBQueryNode(params=None)
    n_3.node_id = 3
    n_3.global_id = 3
    n_3.flow_alg = flow_alg
    if actual_nodes and 3 in actual_nodes:
        n_3.actual_node = actual_nodes[3]
    n_3.create_input('database', 'data', default=rc.Data(':memory:'))
    n_3.create_input('query', 'data', default=rc.Data('SELECT 1 as val'))
    n_3.create_output('info', 'data')
    n_3.create_output('data', 'data')
    n_3.loop_enabled = False
    n_3.loop_interval = 1.0
    n_3.wait_until_complete = False
    n_3.auto_exec_downstream = False
    nodes[3] = n_3

    # Node: DuckDB Query (ID: 4)
    n_4 = DuckDBQueryNode(params=None)
    n_4.node_id = 4
    n_4.global_id = 4
    n_4.flow_alg = flow_alg
    if actual_nodes and 4 in actual_nodes:
        n_4.actual_node = actual_nodes[4]
    n_4.create_input('database', 'data', default=rc.Data(':memory:'))
    n_4.create_input('query', 'data', default=rc.Data('SELECT 1 as val'))
    n_4.create_output('info', 'data')
    n_4.create_output('data', 'data')
    n_4.loop_enabled = False
    n_4.loop_interval = 1.0
    n_4.wait_until_complete = False
    n_4.auto_exec_downstream = False
    nodes[4] = n_4

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
    nodes[0].connections[0] = [(nodes[1], 0)]
    nodes[1].connections[1] = [(nodes[6], 0)]
    nodes[2].connections[0] = [(nodes[5], 0)]

    # Run initial placement events
    nodes[0].after_placement()
    nodes[1].after_placement()
    nodes[2].after_placement()
    nodes[3].after_placement()
    nodes[4].after_placement()
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
