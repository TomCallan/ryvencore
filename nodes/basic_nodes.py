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

    def additional_data(self):
        d = super().additional_data()
        d['code'] = self.code
        return d

    def load_additional_data(self, data):
        super().load_additional_data(data)
        self.code = data.get('code', "out1 = in1 + in2\nout2 = in1 * in2")

    def update_event(self, inp=-1):
        in1_val = self.input(0).payload if self.input(0) else 0.0
        in2_val = self.input(1).payload if self.input(1) else 0.0
        
        local_vars = {
            'in1': in1_val,
            'in2': in2_val,
            'out1': 0.0,
            'out2': 0.0
        }
        try:
            exec(self.code, {}, local_vars)
        except Exception as e:
            err_msg = f"Error: {e}"
            print(f"REPL execution error: {err_msg}")
            self.set_output_val(0, rc.Data(err_msg))
            self.set_output_val(1, rc.Data(err_msg))
            return
            
        self.set_output_val(0, rc.Data(local_vars.get('out1', 0.0)))
        self.set_output_val(1, rc.Data(local_vars.get('out2', 0.0)))
