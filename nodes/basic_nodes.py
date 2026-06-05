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

    def update_ports_from_code(self):
        desired_inputs = []
        desired_outputs = []
        has_inputs_class = False
        has_outputs_class = False

        code_str = getattr(self, '_code', '')
        if code_str:
            try:
                import ast
                tree = ast.parse(code_str)
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        if node.name == 'Inputs':
                            has_inputs_class = True
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
                            has_outputs_class = True
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
            except Exception as e:
                # If code is invalid syntax, keep current ports
                print(f"Error parsing REPL code syntax: {e}")
                return

        # If class wasn't declared in code, do not reset ports (keeps UI port configuration!)
        if not has_inputs_class and not has_outputs_class:
            return

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
                if val is not None and not self.flow.connected_output(existing_inp):
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
        
        has_inputs_class = False
        has_outputs_class = False
        try:
            import ast
            tree = ast.parse(code_str)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    if node.name == 'Inputs':
                        has_inputs_class = True
                    elif node.name == 'Outputs':
                        has_outputs_class = True
        except Exception:
            pass

        if has_inputs_class or has_outputs_class:
            try:
                import ast
                # 1. Get input port values
                port_values = {}
                for idx, inp_port in enumerate(self.inputs):
                    val_obj = self.input(idx)
                    port_values[inp_port.label_str] = val_obj.payload if val_obj else None
                
                # 2. Parse and rewrite AST
                tree = ast.parse(code_str)
                for node in tree.body:
                    if isinstance(node, ast.ClassDef) and node.name == 'Inputs':
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name) and target.id in port_values:
                                        new_val = ast.Constant(value=port_values[target.id])
                                        ast.copy_location(new_val, item.value)
                                        item.value = new_val
                            elif isinstance(item, ast.AnnAssign):
                                if isinstance(item.target, ast.Name) and item.target.id in port_values:
                                    new_val = ast.Constant(value=port_values[item.target.id])
                                    orig_node = item.value if item.value else item.target
                                    ast.copy_location(new_val, orig_node)
                                    item.value = new_val
                
                ast.fix_missing_locations(tree)
                compiled_code = compile(tree, filename="<repl>", mode="exec")
                
                namespace = {}
                exec(compiled_code, {}, namespace)
                
                # 3. Read output values from the namespace
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
            # Dynamic port-variable injection execution (n8n variable style!)
            local_vars = {}
            for idx, inp_port in enumerate(self.inputs):
                val_obj = self.input(idx)
                local_vars[inp_port.label_str] = val_obj.payload if val_obj else None
            
            # Pre-populate outputs with None in the namespace so they exist
            for out_port in self.outputs:
                local_vars[out_port.label_str] = None
                
            try:
                exec(code_str, {}, local_vars)
            except Exception as e:
                err_msg = f"Error: {e}"
                print(f"REPL execution error: {err_msg}")
                for idx in range(len(self.outputs)):
                    self.set_output_val(idx, rc.Data(err_msg))
                return
                
            # Write outputs back to ports
            for idx, out_port in enumerate(self.outputs):
                val = local_vars.get(out_port.label_str)
                self.set_output_val(idx, rc.Data(val))


# Node executing an external python script file
class PythonScriptNode(WebNode):
    title = 'Python Script'
    init_inputs = []
    init_outputs = []

    def __init__(self, params):
        super().__init__(params)
        self.script_path = ""

    @property
    def script_path(self):
        return getattr(self, '_script_path', '')

    @property
    def code(self):
        # Fallback helper for internal REPL styling if needed
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
            # Resolve relative to the project root directory
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

    def update_ports_from_script(self):
        import os
        desired_inputs = []
        desired_outputs = []
        has_inputs_class = False
        has_outputs_class = False

        abs_path = self.get_absolute_path()
        if abs_path and os.path.exists(abs_path) and os.path.isfile(abs_path):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    code_str = f.read()
                
                import ast
                tree = ast.parse(code_str)
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        if node.name == 'Inputs':
                            has_inputs_class = True
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
                            has_outputs_class = True
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
            except Exception as e:
                print(f"Error parsing script file ports: {e}")
                return

        # If no script is loaded or classes aren't declared, we have no dynamic ports
        # (or keep current ports). Let's keep ports if no file, or clear them if file is empty
        if not has_inputs_class and not has_outputs_class and not abs_path:
            desired_inputs = []
            desired_outputs = []

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
                if val is not None and not self.flow.connected_output(existing_inp):
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
        import os
        abs_path = self.get_absolute_path()
        if not abs_path or not os.path.exists(abs_path) or not os.path.isfile(abs_path):
            print(f"Script file not found: {self.script_path}")
            return

        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                code_str = f.read()
            
            import ast
            has_inputs_class = False
            tree = ast.parse(code_str)
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == 'Inputs':
                    has_inputs_class = True
                    break

            # 1. Get input port values
            port_values = {}
            for idx, inp_port in enumerate(self.inputs):
                val_obj = self.input(idx)
                port_values[inp_port.label_str] = val_obj.payload if val_obj else None
            
            # 2. Parse and rewrite AST if Inputs class is present
            tree = ast.parse(code_str)
            if has_inputs_class:
                for node in tree.body:
                    if isinstance(node, ast.ClassDef) and node.name == 'Inputs':
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name) and target.id in port_values:
                                        new_val = ast.Constant(value=port_values[target.id])
                                        ast.copy_location(new_val, item.value)
                                        item.value = new_val
                            elif isinstance(item, ast.AnnAssign):
                                if isinstance(item.target, ast.Name) and item.target.id in port_values:
                                    new_val = ast.Constant(value=port_values[item.target.id])
                                    orig_node = item.value if item.value else item.target
                                    ast.copy_location(new_val, orig_node)
                                    item.value = new_val
            
            ast.fix_missing_locations(tree)
            compiled_code = compile(tree, filename=os.path.basename(abs_path), mode="exec")
            
            namespace = {}
            exec(compiled_code, {}, namespace)
            
            # 3. Read output values from the namespace
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

        # Convert elements to float
        numeric_arr = []
        for x in arr:
            try:
                numeric_arr.append(float(x))
            except (ValueError, TypeError):
                pass

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

