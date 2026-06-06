import ryvencore as rc
from nodes.base import WebNode, add_server_log

# Math Nodes
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


class SubtractNode(WebNode):
    title = 'Subtract'
    init_inputs = [
        rc.NodeInputType(label='A', default=rc.Data(0.0)),
        rc.NodeInputType(label='B', default=rc.Data(0.0))
    ]
    init_outputs = [rc.NodeOutputType(label='diff')]

    def update_event(self, inp=-1):
        a = self.input(0).payload if self.input(0) else 0.0
        b = self.input(1).payload if self.input(1) else 0.0
        try: a = float(a)
        except: pass
        try: b = float(b)
        except: pass
        self.set_output_val(0, rc.Data(a - b))


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


class DivideNode(WebNode):
    title = 'Divide'
    init_inputs = [
        rc.NodeInputType(label='A', default=rc.Data(0.0)),
        rc.NodeInputType(label='B', default=rc.Data(1.0))
    ]
    init_outputs = [rc.NodeOutputType(label='quot')]

    def update_event(self, inp=-1):
        a = self.input(0).payload if self.input(0) else 0.0
        b = self.input(1).payload if self.input(1) else 1.0
        try: a = float(a)
        except: pass
        try: b = float(b)
        except: pass
        if b == 0:
            self.set_output_val(0, rc.Data('Error: Division by 0'))
        else:
            self.set_output_val(0, rc.Data(a / b))


# String Nodes
class NumberNode(WebNode):
    title = 'Number'
    init_inputs = [rc.NodeInputType(label='val', default=rc.Data(0.0))]
    init_outputs = [rc.NodeOutputType(label='val')]

    def update_event(self, inp=-1):
        self.set_output_val(0, self.input(0))


class StringNode(WebNode):
    title = 'String'
    init_inputs = [rc.NodeInputType(label='val', default=rc.Data(''))]
    init_outputs = [rc.NodeOutputType(label='val')]

    def update_event(self, inp=-1):
        self.set_output_val(0, self.input(0))


class ConcatNode(WebNode):
    title = 'Concat'
    init_inputs = [
        rc.NodeInputType(label='A', default=rc.Data('')),
        rc.NodeInputType(label='B', default=rc.Data(''))
    ]
    init_outputs = [rc.NodeOutputType(label='out')]

    def update_event(self, inp=-1):
        a = str(self.input(0).payload if self.input(0) else '')
        b = str(self.input(1).payload if self.input(1) else '')
        self.set_output_val(0, rc.Data(a + b))


class UppercaseNode(WebNode):
    title = 'Uppercase'
    init_inputs = [rc.NodeInputType(label='text', default=rc.Data(''))]
    init_outputs = [rc.NodeOutputType(label='out')]

    def update_event(self, inp=-1):
        t = str(self.input(0).payload if self.input(0) else '')
        self.set_output_val(0, rc.Data(t.upper()))


# Logic/Utility Nodes
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


# Execution Nodes
class TriggerNode(WebNode):
    title = 'Trigger'
    init_inputs = []
    init_outputs = [rc.NodeOutputType(type_='exec', label='out')]

    def update_event(self, inp=-1):
        self.exec_output(0)


class BranchNode(WebNode):
    title = 'Branch'
    init_inputs = [
        rc.NodeInputType(type_='exec', label='in'),
        rc.NodeInputType(type_='data', label='cond', default=rc.Data(False))
    ]
    init_outputs = [
        rc.NodeOutputType(type_='exec', label='true'),
        rc.NodeOutputType(type_='exec', label='false')
    ]

    def update_event(self, inp=-1):
        if inp == 0:  # exec input triggered
            cond = bool(self.input(1).payload if self.input(1) else False)
            if cond:
                self.exec_output(0)
            else:
                self.exec_output(1)


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


class ExecuteButtonNode(WebNode):
    title = 'Execute Button'
    init_inputs = []
    init_outputs = [rc.NodeOutputType(type_='exec', label='trigger')]

    def __init__(self, params):
        super().__init__(params)
        self.target_node_id = None

    def additional_data(self):
        d = super().additional_data()
        d['target_node_id'] = self.target_node_id
        return d

    def load_additional_data(self, data):
        super().load_additional_data(data)
        self.target_node_id = data.get('target_node_id')

    def update_event(self, inp=-1):
        if self.target_node_id is not None:
            target = next((node for node in self.flow.nodes if node.global_id == self.target_node_id), None)
            if target:
                print(f"[ExecuteButton] Triggering target node {target.global_id}")
                try:
                    exec_idx = -1
                    for idx, inp_port in enumerate(target.inputs):
                        if inp_port.type_ == 'exec':
                            exec_idx = idx
                            break
                    self.flow.executor.force_propagation = True
                    try:
                        target.update(exec_idx)
                    finally:
                        self.flow.executor.force_propagation = False
                except Exception as e:
                    print(f"Error triggering target node from execute button: {e}")
        self.exec_output(0)


# Inline Python REPL Node
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


class PlotNode(WebNode):
    title = 'Plot'
    init_inputs = [
        rc.NodeInputType(label='val', default=rc.Data(0.0)),
        rc.NodeInputType(label='limit', default=rc.Data(50))
    ]
    init_outputs = [
        rc.NodeOutputType(label='buffer')
    ]

    def __init__(self, params):
        super().__init__(params)
        self.buffer = []

    def update_event(self, inp=-1):
        try:
            val_data = self.input(0)
            val = float(val_data.payload) if val_data and val_data.payload is not None else 0.0
        except (ValueError, TypeError):
            val = 0.0

        try:
            limit_data = self.input(1)
            limit = int(limit_data.payload) if limit_data and limit_data.payload is not None else 50
        except (ValueError, TypeError):
            limit = 50

        self.buffer.append(val)
        if len(self.buffer) > limit:
            self.buffer = self.buffer[-limit:]

        self.set_output_val(0, rc.Data(self.buffer))

    def additional_data(self):
        d = super().additional_data()
        d['buffer'] = self.buffer
        return d

    def load_additional_data(self, data):
        super().load_additional_data(data)
        self.buffer = data.get('buffer', [])


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


class ParquetReaderNode(WebNode):
    title = 'Parquet Reader'
    init_inputs = [
        rc.NodeInputType(label='file_path', default=rc.Data('')),
        rc.NodeInputType(label='n_rows', default=rc.Data(-1))
    ]
    init_outputs = [
        rc.NodeOutputType(label='df_info'),
        rc.NodeOutputType(label='data')
    ]

    def update_event(self, inp=-1):
        file_path = self.input(0).payload if self.input(0) else ''
        n_rows = self.input(1).payload if self.input(1) else -1
        try:
            n_rows = int(n_rows)
        except:
            n_rows = -1

        if not file_path:
            self.set_output_val(0, rc.Data('No file path provided'))
            self.set_output_val(1, rc.Data([]))
            return

        import os
        if not os.path.exists(file_path):
            self.set_output_val(0, rc.Data(f"File not found: {file_path}"))
            self.set_output_val(1, rc.Data([]))
            return

        try:
            import polars as pl
        except ImportError:
            self.set_output_val(0, rc.Data("polars is not installed. Please install it to read Parquet."))
            self.set_output_val(1, rc.Data([]))
            return

        try:
            # Read/scan parquet using polars
            if n_rows > 0:
                df = pl.read_parquet(file_path, n_rows=n_rows)
            else:
                df = pl.read_parquet(file_path)
            
            summary = f"Polars DataFrame: Shape {df.shape}, Schema: {dict(df.schema)}"
            # Convert to list of dicts for serialization
            dict_data = df.to_dicts()
            self.set_output_val(0, rc.Data(summary))
            self.set_output_val(1, rc.Data(dict_data))
        except Exception as e:
            self.set_output_val(0, rc.Data(f"Error: {str(e)}"))
            self.set_output_val(1, rc.Data([]))


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


class AdvancedPlotNode(WebNode):
    title = 'Advanced Plot'
    init_inputs = [
        rc.NodeInputType(label='val', default=rc.Data(0.0)),
        rc.NodeInputType(label='limit', default=rc.Data(50)),
        rc.NodeInputType(label='title', default=rc.Data('Advanced Line Plot')),
        rc.NodeInputType(label='color', default=rc.Data('#818cf8'))
    ]
    init_outputs = [
        rc.NodeOutputType(label='buffer')
    ]

    def __init__(self, params):
        super().__init__(params)
        self.buffer = []
        self.svg_content = ""

    def update_event(self, inp=-1):
        try:
            val_data = self.input(0)
            val = float(val_data.payload) if val_data and val_data.payload is not None else 0.0
        except (ValueError, TypeError):
            val = 0.0

        try:
            limit_data = self.input(1)
            limit = int(limit_data.payload) if limit_data and limit_data.payload is not None else 50
        except (ValueError, TypeError):
            limit = 50

        plot_title = str(self.input(2).payload) if self.input(2) else "Advanced Line Plot"
        color = str(self.input(3).payload) if self.input(3) else "#818cf8"

        self.buffer.append(val)
        if len(self.buffer) > limit:
            self.buffer = self.buffer[-limit:]

        # Render to SVG using our plotting engine!
        from plotting.engine import SVGPlotter
        self.svg_content = SVGPlotter.plot_line(self.buffer, title=plot_title, color=color)

        self.set_output_val(0, rc.Data(self.buffer))

       # We increase default node size for display
        self.width = 240
        self.height = 220

    def additional_data(self):
        d = super().additional_data()
        d['buffer'] = self.buffer
        d['svg_content'] = self.svg_content
        return d

    def load_additional_data(self, data):
        super().load_additional_data(data)
        self.buffer = data.get('buffer', [])
        self.svg_content = data.get('svg_content', '')


class OrderbookPlotNode(WebNode):
    title = 'Orderbook Plot'
    init_inputs = [
        rc.NodeInputType(label='bids', default=rc.Data([[99.5, 1.2], [99.0, 2.5], [98.5, 4.0]])),
        rc.NodeInputType(label='asks', default=rc.Data([[100.5, 1.8], [101.0, 3.1], [101.5, 5.0]])),
        rc.NodeInputType(label='title', default=rc.Data('BTC/USDT Orderbook'))
    ]
    init_outputs = [
        rc.NodeOutputType(label='rendered')
    ]

    def __init__(self, params):
        super().__init__(params)
        self.svg_content = ""
        # Increase default node size for display
        self.width = 240
        self.height = 220

    def update_event(self, inp=-1):
        # Parse bids/asks
        bids_data = self.input(0).payload if self.input(0) else []
        asks_data = self.input(1).payload if self.input(1) else []
        title = str(self.input(2).payload) if self.input(2) else "Orderbook Depth"

        # Coerce to lists of lists/tuples
        try:
            if isinstance(bids_data, str):
                import json
                bids_data = json.loads(bids_data)
        except:
            bids_data = []

        try:
            if isinstance(asks_data, str):
                import json
                asks_data = json.loads(asks_data)
        except:
            asks_data = []

        # Ensure they are valid lists
        if not isinstance(bids_data, list): bids_data = []
        if not isinstance(asks_data, list): asks_data = []

        from plotting.engine import SVGPlotter
        self.svg_content = SVGPlotter.plot_orderbook(bids_data, asks_data, title=title)
        self.set_output_val(0, rc.Data(self.svg_content))

    def additional_data(self):
        d = super().additional_data()
        d['svg_content'] = self.svg_content
        return d

    def load_additional_data(self, data):
        super().load_additional_data(data)
        self.svg_content = data.get('svg_content', '')


