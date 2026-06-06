"""
Compiled ryvencore flow: efficiency_flow
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
class CsvParserNode(WebNode):
    title = 'CSV Parser'
    init_inputs = [
        rc.NodeInputType(type_='data', label='chunk')
    ]
    init_outputs = [
        rc.NodeOutputType(type_='data', label='parsed')
    ]

    def update_event(self, inp=-1):
        import csv
        chunk_data = self.input(0)
        chunk = chunk_data.payload if chunk_data else None

        if chunk is None:
            self.set_output_val(0, rc.Data([]))
            return

        lines = []
        if isinstance(chunk, list):
            lines = chunk
        elif isinstance(chunk, str):
            lines = chunk.splitlines()
        else:
            lines = [str(chunk)]

        parsed_rows = []
        reader = csv.reader(lines)
        for row in reader:
            parsed_rows.append(row)

        self.set_output_val(0, rc.Data(parsed_rows))


class LazyFileReaderNode(WebNode):
    title = 'Lazy File Reader'
    init_inputs = [
        rc.NodeInputType(type_='data', label='file_path', default=rc.Data('')),
        rc.NodeInputType(type_='data', label='chunk_size', default=rc.Data(10)),
        rc.NodeInputType(type_='exec', label='next'),
        rc.NodeInputType(type_='exec', label='reset')
    ]
    init_outputs = [
        rc.NodeOutputType(type_='data', label='chunk'),
        rc.NodeOutputType(type_='exec', label='out'),
        rc.NodeOutputType(type_='exec', label='eof')
    ]

    def __init__(self, params):
        super().__init__(params)
        self._file_handle = None
        self._current_path = ""

    def additional_data(self):
        d = super().additional_data()
        d['current_path'] = self._current_path
        return d

    def load_additional_data(self, data):
        super().load_additional_data(data)
        self._current_path = data.get('current_path', '')

    def update_event(self, inp=-1):
        import os
        if inp == 3:
            self.reset_file()
            return

        if inp == 2:
            file_path_data = self.input(0)
            file_path = str(file_path_data.payload).strip() if file_path_data else ""
            
            try:
                chunk_size_data = self.input(1)
                chunk_size = int(chunk_size_data.payload) if chunk_size_data else 10
            except (ValueError, TypeError):
                chunk_size = 10

            if not file_path:
                self.set_output_val(0, rc.Data("Error: Empty file path"))
                return

            if self._file_handle is None or self._current_path != file_path:
                self.reset_file()
                if not os.path.exists(file_path):
                    self.set_output_val(0, rc.Data(f"Error: File not found: {file_path}"))
                    return
                try:
                    self._file_handle = open(file_path, 'r', encoding='utf-8')
                    self._current_path = file_path
                except Exception as e:
                    self.set_output_val(0, rc.Data(f"Error opening file: {e}"))
                    return

            lines = []
            for _ in range(chunk_size):
                line = self._file_handle.readline()
                if not line:
                    break
                lines.append(line.rstrip('\r\n'))

            if not lines:
                self.reset_file()
                self.set_output_val(0, rc.Data([]))
                self.exec_output(2)
            else:
                self.set_output_val(0, rc.Data(lines))
                self.exec_output(1)

    def reset_file(self):
        if self._file_handle is not None:
            try:
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None

    def remove_event(self):
        super().remove_event()
        self.reset_file()


class ArrayCalculatorNode(WebNode):
    title = 'Array Calculator'
    init_inputs = [
        rc.NodeInputType(label='array', default=rc.Data('[1, 2, 3, 4]')),
        rc.NodeInputType(label='operation', default=rc.Data('sum')),
        rc.NodeInputType(label='operand', default=rc.Data(1.0))
    ]
    init_outputs = [
        rc.NodeOutputType(label='result')
    ]

    def __init__(self, params):
        super().__init__(params)

    def update_event(self, inp=-1):
        import json
        import ast
        arr_input = self.input(0)
        op_input = self.input(1)
        operand_input = self.input(2)

        arr_raw = arr_input.payload if arr_input else None
        op = op_input.payload if op_input else 'sum'
        try:
            operand = float(operand_input.payload) if operand_input and operand_input.payload is not None else 1.0
        except (ValueError, TypeError):
            operand = 1.0

        # Parse array
        arr = []
        if isinstance(arr_raw, list):
            arr = arr_raw
        elif isinstance(arr_raw, str):
            try:
                arr = json.loads(arr_raw)
            except Exception:
                try:
                    arr = ast.literal_eval(arr_raw)
                except Exception:
                    # Try splitting by commas
                    try:
                        arr = [float(x.strip()) for x in arr_raw.replace('[','').replace(']','').split(',') if x.strip()]
                    except Exception:
                        arr = []
        
        if not isinstance(arr, list):
            arr = []

        # Convert elements to float recursively to handle nested lists
        numeric_arr = []
        def extract_floats(item):
            if isinstance(item, list):
                for subitem in item:
                    extract_floats(subitem)
            elif isinstance(item, (int, float)):
                numeric_arr.append(float(item))
            elif isinstance(item, str):
                try:
                    numeric_arr.append(float(item))
                except ValueError:
                    pass

        extract_floats(arr)

        if not numeric_arr:
            self.set_output_val(0, rc.Data(0.0))
            return

        op = str(op).lower().strip()
        if op == 'sum':
            res = sum(numeric_arr)
        elif op == 'mean':
            res = sum(numeric_arr) / len(numeric_arr)
        elif op == 'min':
            res = min(numeric_arr)
        elif op == 'max':
            res = max(numeric_arr)
        elif op == 'std':
            import math
            mean = sum(numeric_arr) / len(numeric_arr)
            variance = sum((x - mean) ** 2 for x in numeric_arr) / len(numeric_arr)
            res = math.sqrt(variance)
        elif op == 'multiply':
            res = [x * operand for x in numeric_arr]
        else:
            res = sum(numeric_arr)

        self.set_output_val(0, rc.Data(res))


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


# --- Flow Execution Instantiation ---
def setup_flow(actual_nodes=None):
    nodes = {}
    flow_alg = 'compiled'

    # Node: Trigger (ID: 12)
    n_12 = TriggerNode(params=None)
    n_12.node_id = 12
    n_12.global_id = 12
    n_12.flow_alg = flow_alg
    if actual_nodes and 12 in actual_nodes:
        n_12.actual_node = actual_nodes[12]
    n_12.create_output('out', 'exec')
    n_12.loop_enabled = True
    n_12.loop_interval = 1.0
    n_12.wait_until_complete = True
    nodes[12] = n_12

    # Node: Execution Timer (ID: 13)
    n_13 = ExecutionTimerNode(params=None)
    n_13.node_id = 13
    n_13.global_id = 13
    n_13.flow_alg = flow_alg
    if actual_nodes and 13 in actual_nodes:
        n_13.actual_node = actual_nodes[13]
    n_13.create_input('trigger', 'exec', default=rc.Data(None))
    n_13.create_output('out', 'exec')
    n_13.create_output('time_ms', 'data')
    n_13.loop_enabled = False
    n_13.loop_interval = 1.0
    n_13.wait_until_complete = False
    nodes[13] = n_13

    # Node: Lazy File Reader (ID: 14)
    n_14 = LazyFileReaderNode(params=None)
    n_14.node_id = 14
    n_14.global_id = 14
    n_14.flow_alg = flow_alg
    if actual_nodes and 14 in actual_nodes:
        n_14.actual_node = actual_nodes[14]
    n_14.create_input('file_path', 'data', default=rc.Data('large_dataset.csv'))
    n_14.create_input('chunk_size', 'data', default=rc.Data(10))
    n_14.create_input('next', 'exec', default=rc.Data(None))
    n_14.create_input('reset', 'exec', default=rc.Data(None))
    n_14.create_output('chunk', 'data')
    n_14.create_output('out', 'exec')
    n_14.create_output('eof', 'exec')
    n_14.loop_enabled = False
    n_14.loop_interval = 1.0
    n_14.wait_until_complete = False
    nodes[14] = n_14

    # Node: CSV Parser (ID: 15)
    n_15 = CsvParserNode(params=None)
    n_15.node_id = 15
    n_15.global_id = 15
    n_15.flow_alg = flow_alg
    if actual_nodes and 15 in actual_nodes:
        n_15.actual_node = actual_nodes[15]
    n_15.create_input('chunk', 'data', default=rc.Data(None))
    n_15.create_output('parsed', 'data')
    n_15.loop_enabled = False
    n_15.loop_interval = 1.0
    n_15.wait_until_complete = False
    nodes[15] = n_15

    # Node: Array Calculator (ID: 16)
    n_16 = ArrayCalculatorNode(params=None)
    n_16.node_id = 16
    n_16.global_id = 16
    n_16.flow_alg = flow_alg
    if actual_nodes and 16 in actual_nodes:
        n_16.actual_node = actual_nodes[16]
    n_16.create_input('array', 'data', default=rc.Data('[1, 2, 3, 4]'))
    n_16.create_input('operation', 'data', default=rc.Data('mean'))
    n_16.create_input('operand', 'data', default=rc.Data(1.0))
    n_16.create_output('result', 'data')
    n_16.loop_enabled = False
    n_16.loop_interval = 1.0
    n_16.wait_until_complete = False
    nodes[16] = n_16

    # Node: Log (ID: 17)
    n_17 = LogNode(params=None)
    n_17.node_id = 17
    n_17.global_id = 17
    n_17.flow_alg = flow_alg
    if actual_nodes and 17 in actual_nodes:
        n_17.actual_node = actual_nodes[17]
    n_17.create_input('msg', 'data', default=rc.Data(''))
    n_17.create_output('out', 'data')
    n_17.loop_enabled = False
    n_17.loop_interval = 1.0
    n_17.wait_until_complete = False
    nodes[17] = n_17

    # Node: Log (ID: 18)
    n_18 = LogNode(params=None)
    n_18.node_id = 18
    n_18.global_id = 18
    n_18.flow_alg = flow_alg
    if actual_nodes and 18 in actual_nodes:
        n_18.actual_node = actual_nodes[18]
    n_18.create_input('msg', 'data', default=rc.Data(''))
    n_18.create_output('out', 'data')
    n_18.loop_enabled = False
    n_18.loop_interval = 1.0
    n_18.wait_until_complete = False
    nodes[18] = n_18

    # Connections
    nodes[12].connections[0] = [(nodes[13], 0)]
    nodes[13].connections[0] = [(nodes[14], 2)]
    nodes[13].connections[1] = [(nodes[18], 0)]
    nodes[14].connections[0] = [(nodes[15], 0)]
    nodes[15].connections[0] = [(nodes[16], 0)]
    nodes[16].connections[0] = [(nodes[17], 0)]

    # Run initial placement events
    nodes[12].after_placement()
    nodes[13].after_placement()
    nodes[14].after_placement()
    nodes[15].after_placement()
    nodes[16].after_placement()
    nodes[17].after_placement()
    nodes[18].after_placement()

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
