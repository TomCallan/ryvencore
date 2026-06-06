# Structure Hash: 753674256e488e029762c1e9cfd677a4b66c2fa50a731ee0b87f4becf1b8cd59
"""
Compiled ryvencore flow: compiled_flow
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


class PythonReplNode(WebNode):
    title = 'Python REPL'
    init_inputs = [
        rc.NodeInputType(label='in1', default=rc.Data(0.0)),
        rc.NodeInputType(label='in2', default=rc.Data(0.0))
    ]
    init_outputs = [
        rc.NodeOutputType(label='out1'),
        rc.NodeOutputType(label='out2')
    ]

    def __init__(self, params):
        super().__init__(params)
        self._code = ""
        self._cached_code = None
        self._compiled_code = None
        self._has_inputs_class = False
        self._has_outputs_class = False
        self.code = "out1 = in1 + in2\nout2 = in1 * in2"

    @property
    def code(self):
        return getattr(self, '_code', '')

    @code.setter
    def code(self, value):
        self._code = value
        self.update_ports_from_code()

    def additional_data(self):
        d = super().additional_data()
        d['code'] = self.code
        return d

    def load_additional_data(self, data):
        super().load_additional_data(data)
        self.code = data.get('code', "out1 = in1 + in2\nout2 = in1 * in2")

    def get_literal_value(self, node):
        import ast
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            val = self.get_literal_value(node.operand)
            if val is not None:
                return -val
        elif hasattr(ast, 'Num') and isinstance(node, ast.Num):
            return node.n
        elif hasattr(ast, 'Str') and isinstance(node, ast.Str):
            return node.s
        elif hasattr(ast, 'NameConstant') and isinstance(node, ast.NameConstant):
            return node.value
        return None

    def _compile_and_cache(self, code_str):
        if self._cached_code == code_str and self._compiled_code is not None:
            return

        import ast
        self._cached_code = code_str
        self._compiled_code = None
        self._has_inputs_class = False
        self._has_outputs_class = False

        if not code_str:
            return

        try:
            tree = ast.parse(code_str)
        except Exception as e:
            print(f"Error parsing code: {e}")
            return

        # Scan for Inputs and Outputs classes
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if node.name == 'Inputs':
                    self._has_inputs_class = True
                elif node.name == 'Outputs':
                    self._has_outputs_class = True

        if self._has_inputs_class or self._has_outputs_class:
            # Rewrite Inputs class to read from _IN_
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == 'Inputs':
                    new_body = []
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            if item.targets and isinstance(item.targets[0], ast.Name):
                                name = item.targets[0].id
                                subscript_node = ast.Subscript(
                                    value=ast.Name(id='_IN_', ctx=ast.Load()),
                                    slice=ast.Constant(value=name),
                                    ctx=ast.Load()
                                )
                                ast.copy_location(subscript_node, item.value)
                                item.value = subscript_node
                            new_body.append(item)
                        elif isinstance(item, ast.AnnAssign):
                            if isinstance(item.target, ast.Name):
                                name = item.target.id
                                subscript_node = ast.Subscript(
                                    value=ast.Name(id='_IN_', ctx=ast.Load()),
                                    slice=ast.Constant(value=name),
                                    ctx=ast.Load()
                                )
                                orig_node = item.value if item.value else item.target
                                ast.copy_location(subscript_node, orig_node)
                                item.value = subscript_node
                            new_body.append(item)
                        else:
                            new_body.append(item)
                    node.body = new_body

            try:
                ast.fix_missing_locations(tree)
                self._compiled_code = compile(tree, filename="<repl>", mode="exec")
            except Exception as e:
                print(f"Error compiling AST: {e}")
        else:
            # Fallback simple mode - just compile the raw code string
            try:
                self._compiled_code = compile(code_str, filename="<repl>", mode="exec")
            except Exception as e:
                print(f"Error compiling simple code: {e}")

    def update_ports_from_code(self):
        code_str = getattr(self, '_code', '')
        self._compile_and_cache(code_str)

        if not self._has_inputs_class and not self._has_outputs_class:
            # Keep standard fallback ports or don't modify if we don't have them
            return

        import ast
        desired_inputs = []
        desired_outputs = []
        try:
            tree = ast.parse(code_str)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    if node.name == 'Inputs':
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        val = self.get_literal_value(item.value)
                                        desired_inputs.append((target.id, val))
                            elif isinstance(item, ast.AnnAssign):
                                if isinstance(item.target, ast.Name):
                                    val = self.get_literal_value(item.value) if item.value else None
                                    desired_inputs.append((item.target.id, val))
                    elif node.name == 'Outputs':
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        val = self.get_literal_value(item.value)
                                        desired_outputs.append((target.id, val))
                            elif isinstance(item, ast.AnnAssign):
                                if isinstance(item.target, ast.Name):
                                    val = self.get_literal_value(item.value) if item.value else None
                                    desired_outputs.append((item.target.id, val))
        except Exception:
            pass

        # Update inputs
        desired_input_names = [name for name, _ in desired_inputs]
        inputs_to_delete = []
        for idx, inp in enumerate(self.inputs):
            if inp.label_str not in desired_input_names:
                inputs_to_delete.append(idx)
        for idx in sorted(inputs_to_delete, reverse=True):
            self.delete_input(idx)

        for name, val in desired_inputs:
            existing_inp = next((inp for inp in self.inputs if inp.label_str == name), None)
            if existing_inp is None:
                self.create_input(label=name, default=rc.Data(val) if val is not None else rc.Data(''))
            else:
                is_connected = False
                try:
                    is_connected = bool(self.flow.connected_output(existing_inp))
                except Exception:
                    pass
                if val is not None and not is_connected:
                    existing_inp.default = rc.Data(val)

        # Update outputs
        desired_output_names = [name for name, _ in desired_outputs]
        outputs_to_delete = []
        for idx, out in enumerate(self.outputs):
            if out.label_str not in desired_output_names:
                outputs_to_delete.append(idx)
        for idx in sorted(outputs_to_delete, reverse=True):
            self.delete_output(idx)

        for name, val in desired_outputs:
            existing_out = next((out for out in self.outputs if out.label_str == name), None)
            if existing_out is None:
                self.create_output(label=name)

    def update_event(self, inp=-1):
        code_str = getattr(self, '_code', '')
        if not code_str:
            return

        self._compile_and_cache(code_str)

        if self._compiled_code is None:
            print("REPL execution error: Code is not compiled")
            return

        if self._has_inputs_class or self._has_outputs_class:
            try:
                # 1. Get input port values
                port_values = {}
                for idx, inp_port in enumerate(self.inputs):
                    val_obj = self.input(idx)
                    port_values[inp_port.label_str] = val_obj.payload if val_obj else None
                
                # 2. Run compiled code
                namespace = {'_IN_': port_values}
                exec(self._compiled_code, namespace)
                
                # 3. Read output values
                if 'Outputs' in namespace:
                    outputs_class = namespace['Outputs']
                    for idx, out_port in enumerate(self.outputs):
                        label = out_port.label_str
                        val = getattr(outputs_class, label, None)
                        self.set_output_val(idx, rc.Data(val))
            except Exception as e:
                err_msg = f"Error: {e}"
                print(f"REPL execution error: {err_msg}")
                for idx in range(len(self.outputs)):
                    self.set_output_val(idx, rc.Data(err_msg))
        else:
            # Fallback simple mode using compiled code
            local_vars = {}
            for idx, inp_port in enumerate(self.inputs):
                val_obj = self.input(idx)
                local_vars[inp_port.label_str] = val_obj.payload if val_obj else None
            
            for out_port in self.outputs:
                local_vars[out_port.label_str] = None
                
            try:
                exec(self._compiled_code, local_vars)
            except Exception as e:
                err_msg = f"Error: {e}"
                print(f"REPL execution error: {err_msg}")
                for idx in range(len(self.outputs)):
                    self.set_output_val(idx, rc.Data(err_msg))
                return
                
            for idx, out_port in enumerate(self.outputs):
                val = local_vars.get(out_port.label_str)
                self.set_output_val(idx, rc.Data(val))


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


class PythonScriptNode(WebNode):
    title = 'Python Script'
    init_inputs = []
    init_outputs = []

    def __init__(self, params):
        super().__init__(params)
        self._cached_script_path = None
        self._cached_mtime = None
        self._compiled_code = None
        self._has_inputs_class = False
        self._has_outputs_class = False
        self.script_path = ""

    @property
    def script_path(self):
        return getattr(self, '_script_path', '')

    @property
    def code(self):
        return ""

    @script_path.setter
    def script_path(self, value):
        self._script_path = value
        self.update_ports_from_script()

    def additional_data(self):
        d = super().additional_data()
        d['script_path'] = self.script_path
        return d

    def load_additional_data(self, data):
        super().load_additional_data(data)
        self.script_path = data.get('script_path', '')

    def get_absolute_path(self):
        import os
        path = self.script_path
        if not path:
            return ""
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
        return path

    def get_literal_value(self, node):
        import ast
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            val = self.get_literal_value(node.operand)
            if val is not None:
                return -val
        elif hasattr(ast, 'Num') and isinstance(node, ast.Num):
            return node.n
        elif hasattr(ast, 'Str') and isinstance(node, ast.Str):
            return node.s
        elif hasattr(ast, 'NameConstant') and isinstance(node, ast.NameConstant):
            return node.value
        return None

    def _compile_and_cache_script(self):
        import os
        abs_path = self.get_absolute_path()
        if not abs_path or not os.path.exists(abs_path) or not os.path.isfile(abs_path):
            self._compiled_code = None
            self._cached_script_path = None
            self._cached_mtime = None
            return

        try:
            mtime = os.path.getmtime(abs_path)
        except Exception:
            mtime = None

        if (self._cached_script_path == abs_path and 
            self._cached_mtime is not None and 
            self._cached_mtime == mtime and 
            self._compiled_code is not None):
            return

        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                code_str = f.read()
        except Exception as e:
            print(f"Error reading script file: {e}")
            return

        self._cached_script_path = abs_path
        self._cached_mtime = mtime
        self._compiled_code = None
        self._has_inputs_class = False
        self._has_outputs_class = False

        import ast
        try:
            tree = ast.parse(code_str)
        except Exception as e:
            print(f"Error parsing script syntax: {e}")
            return

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if node.name == 'Inputs':
                    self._has_inputs_class = True
                elif node.name == 'Outputs':
                    self._has_outputs_class = True

        if self._has_inputs_class or self._has_outputs_class:
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == 'Inputs':
                    new_body = []
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            if item.targets and isinstance(item.targets[0], ast.Name):
                                name = item.targets[0].id
                                subscript_node = ast.Subscript(
                                    value=ast.Name(id='_IN_', ctx=ast.Load()),
                                    slice=ast.Constant(value=name),
                                    ctx=ast.Load()
                                )
                                ast.copy_location(subscript_node, item.value)
                                item.value = subscript_node
                            new_body.append(item)
                        elif isinstance(item, ast.AnnAssign):
                            if isinstance(item.target, ast.Name):
                                name = item.target.id
                                subscript_node = ast.Subscript(
                                    value=ast.Name(id='_IN_', ctx=ast.Load()),
                                    slice=ast.Constant(value=name),
                                    ctx=ast.Load()
                                )
                                orig_node = item.value if item.value else item.target
                                ast.copy_location(subscript_node, orig_node)
                                item.value = subscript_node
                            new_body.append(item)
                        else:
                            new_body.append(item)
                    node.body = new_body

            try:
                ast.fix_missing_locations(tree)
                self._compiled_code = compile(tree, filename=os.path.basename(abs_path), mode="exec")
            except Exception as e:
                print(f"Error compiling script AST: {e}")
        else:
            try:
                self._compiled_code = compile(code_str, filename=os.path.basename(abs_path), mode="exec")
            except Exception as e:
                print(f"Error compiling script: {e}")

    def update_ports_from_script(self):
        import os
        self._compile_and_cache_script()

        if not self._has_inputs_class and not self._has_outputs_class:
            if not self.script_path:
                self.delete_all_ports()
            return

        abs_path = self.get_absolute_path()
        desired_inputs = []
        desired_outputs = []
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                code_str = f.read()
            import ast
            tree = ast.parse(code_str)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    if node.name == 'Inputs':
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        val = self.get_literal_value(item.value)
                                        desired_inputs.append((target.id, val))
                            elif isinstance(item, ast.AnnAssign):
                                if isinstance(item.target, ast.Name):
                                    val = self.get_literal_value(item.value) if item.value else None
                                    desired_inputs.append((item.target.id, val))
                    elif node.name == 'Outputs':
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        val = self.get_literal_value(item.value)
                                        desired_outputs.append((target.id, val))
                            elif isinstance(item, ast.AnnAssign):
                                if isinstance(item.target, ast.Name):
                                    val = self.get_literal_value(item.value) if item.value else None
                                    desired_outputs.append((item.target.id, val))
        except Exception:
            pass

        # Update inputs
        desired_input_names = [name for name, _ in desired_inputs]
        inputs_to_delete = []
        for idx, inp in enumerate(self.inputs):
            if inp.label_str not in desired_input_names:
                inputs_to_delete.append(idx)
        for idx in sorted(inputs_to_delete, reverse=True):
            self.delete_input(idx)

        for name, val in desired_inputs:
            existing_inp = next((inp for inp in self.inputs if inp.label_str == name), None)
            if existing_inp is None:
                self.create_input(label=name, default=rc.Data(val) if val is not None else rc.Data(''))
            else:
                is_connected = False
                try:
                    is_connected = bool(self.flow.connected_output(existing_inp))
                except Exception:
                    pass
                if val is not None and not is_connected:
                    existing_inp.default = rc.Data(val)

        # Update outputs
        desired_output_names = [name for name, _ in desired_outputs]
        outputs_to_delete = []
        for idx, out in enumerate(self.outputs):
            if out.label_str not in desired_output_names:
                outputs_to_delete.append(idx)
        for idx in sorted(outputs_to_delete, reverse=True):
            self.delete_output(idx)

        for name, val in desired_outputs:
            existing_out = next((out for out in self.outputs if out.label_str == name), None)
            if existing_out is None:
                self.create_output(label=name)

    def delete_all_ports(self):
        for idx in sorted(range(len(self.inputs)), reverse=True):
            self.delete_input(idx)
        for idx in sorted(range(len(self.outputs)), reverse=True):
            self.delete_output(idx)

    def update_event(self, inp=-1):
        import os
        self._compile_and_cache_script()

        if self._compiled_code is None:
            print(f"Script file execution error: File not found or invalid: {self.script_path}")
            return

        if self._has_inputs_class or self._has_outputs_class:
            try:
                # 1. Get input port values
                port_values = {}
                for idx, inp_port in enumerate(self.inputs):
                    val_obj = self.input(idx)
                    port_values[inp_port.label_str] = val_obj.payload if val_obj else None
                
                # 2. Run compiled code
                namespace = {'_IN_': port_values}
                exec(self._compiled_code, namespace)
                
                # 3. Read output values
                if 'Outputs' in namespace:
                    outputs_class = namespace['Outputs']
                    for idx, out_port in enumerate(self.outputs):
                        label = out_port.label_str
                        val = getattr(outputs_class, label, None)
                        self.set_output_val(idx, rc.Data(val))
            except Exception as e:
                err_msg = f"Error: {e}"
                print(f"Script execution error: {err_msg}")
                for idx in range(len(self.outputs)):
                    self.set_output_val(idx, rc.Data(err_msg))
        else:
            try:
                exec(self._compiled_code, {})
            except Exception as e:
                print(f"Script execution error: {e}")


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
    n_0.loop_enabled = True
    n_0.loop_interval = 1.0
    n_0.wait_until_complete = True
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

    # Node: Counter (ID: 2)
    n_2 = CounterNode(params=None)
    n_2.node_id = 2
    n_2.global_id = 2
    n_2.flow_alg = flow_alg
    if actual_nodes and 2 in actual_nodes:
        n_2.actual_node = actual_nodes[2]
    n_2.create_input('inc', 'exec', default=rc.Data(None))
    n_2.create_input('reset', 'exec', default=rc.Data(None))
    n_2.create_output('out', 'exec')
    n_2.create_output('count', 'data')
    n_2.loop_enabled = False
    n_2.loop_interval = 1.0
    n_2.wait_until_complete = False
    n_2.auto_exec_downstream = False
    nodes[2] = n_2

    # Node: Python Script (ID: 3)
    n_3 = PythonScriptNode(params=None)
    n_3.node_id = 3
    n_3.global_id = 3
    n_3.flow_alg = flow_alg
    if actual_nodes and 3 in actual_nodes:
        n_3.actual_node = actual_nodes[3]
    n_3.create_input('command', 'data', default=rc.Data('echo Hello from ryvencore compiled workflow!'))
    n_3.create_input('trigger_val', 'data', default=rc.Data(0))
    n_3.create_output('output', 'data')
    n_3.script_path = 'example_scripts/run_cli_cmd.py'
    n_3.loop_enabled = False
    n_3.loop_interval = 1.0
    n_3.wait_until_complete = False
    n_3.auto_exec_downstream = False
    nodes[3] = n_3

    # Node: Python REPL (ID: 4)
    n_4 = PythonReplNode(params=None)
    n_4.node_id = 4
    n_4.global_id = 4
    n_4.flow_alg = flow_alg
    if actual_nodes and 4 in actual_nodes:
        n_4.actual_node = actual_nodes[4]
    n_4.create_input('in1', 'data', default=rc.Data(0.0))
    n_4.create_input('in2', 'data', default=rc.Data(0.0))
    n_4.create_output('out1', 'data')
    n_4.create_output('out2', 'data')
    n_4.loop_enabled = False
    n_4.loop_interval = 1.0
    n_4.wait_until_complete = False
    n_4.code = "out1 = f'REPL PROCESSED: {in1}'\nout2 = len(in1)"
    n_4.auto_exec_downstream = False
    nodes[4] = n_4

    # Node: Python Script (ID: 5)
    n_5 = PythonScriptNode(params=None)
    n_5.node_id = 5
    n_5.global_id = 5
    n_5.flow_alg = flow_alg
    if actual_nodes and 5 in actual_nodes:
        n_5.actual_node = actual_nodes[5]
    n_5.create_input('text', 'data', default=rc.Data(''))
    n_5.create_input('length', 'data', default=rc.Data(0))
    n_5.create_output('final_message', 'data')
    n_5.script_path = 'example_scripts/analyze_output.py'
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

    # Node: Log (ID: 7)
    n_7 = LogNode(params=None)
    n_7.node_id = 7
    n_7.global_id = 7
    n_7.flow_alg = flow_alg
    if actual_nodes and 7 in actual_nodes:
        n_7.actual_node = actual_nodes[7]
    n_7.create_input('msg', 'data', default=rc.Data(''))
    n_7.create_output('out', 'data')
    n_7.loop_enabled = False
    n_7.loop_interval = 1.0
    n_7.wait_until_complete = False
    n_7.auto_exec_downstream = False
    nodes[7] = n_7

    # Connections
    nodes[0].connections[0] = [(nodes[1], 0)]
    nodes[1].connections[0] = [(nodes[2], 0)]
    nodes[1].connections[1] = [(nodes[7], 0)]
    nodes[2].connections[1] = [(nodes[3], 1)]
    nodes[3].connections[0] = [(nodes[4], 0)]
    nodes[4].connections[0] = [(nodes[5], 0)]
    nodes[4].connections[1] = [(nodes[5], 1)]
    nodes[5].connections[0] = [(nodes[6], 0)]

    # Run initial placement events
    nodes[0].after_placement()
    nodes[1].after_placement()
    nodes[2].after_placement()
    nodes[3].after_placement()
    nodes[4].after_placement()
    nodes[5].after_placement()
    nodes[6].after_placement()
    nodes[7].after_placement()

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
