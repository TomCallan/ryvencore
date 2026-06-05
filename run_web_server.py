import os
import sys
import json
import traceback
import urllib.parse
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# Add current directory to path to import ryvencore
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import ryvencore as rc

# Log messages captured from PrintNode
log_messages = []
global_execution_paused = False

def add_server_log(msg):
    t_str = datetime.datetime.now().strftime("%H:%M:%S")
    log_messages.append({'time': t_str, 'msg': msg})
    if len(log_messages) > 200:
        log_messages.pop(0)

def get_downstream_nodes(start_node):
    downstream = set()
    to_visit = [start_node]
    while to_visit:
        current = to_visit.pop()
        for out in current.outputs:
            if out in current.flow.graph_adj:
                for inp_port in current.flow.graph_adj[out]:
                    neighbor = inp_port.node
                    if neighbor not in downstream:
                        downstream.add(neighbor)
                        to_visit.append(neighbor)
    return downstream

def topological_sort(nodes, flow):
    visited = set()
    order = []
    
    def visit(node):
        if node in visited:
            return
        visited.add(node)
        for out in node.outputs:
            if out in flow.graph_adj:
                for inp_port in flow.graph_adj[out]:
                    neighbor = inp_port.node
                    if neighbor in nodes:
                        visit(neighbor)
        order.append(node)

    for node in nodes:
        visit(node)
    
    return order[::-1]

def get_trigger_input_index(node, flow, downstream_set, start_node):
    for idx, inp in enumerate(node.inputs):
        out = flow.graph_adj_rev.get(inp)
        if out:
            if out.node == start_node or out.node in downstream_set:
                if inp.type_ == 'exec':
                    return idx
    return -1

# Define custom node classes that inherit from ryvencore.Node
class WebNode(rc.Node):
    """Base Web Node with default coordinate state handling, timestep trigger, and downstream exec propagation support"""
    def __init__(self, params):
        super().__init__(params)
        self.x = 100
        self.y = 100
        self.width = 200
        self.height = 120
        self.loop_enabled = False
        self.loop_interval = 1.0
        self.auto_exec_downstream = False
        self.force_trigger = False
        self._loop_thread = None
        self._loop_running = False

    def additional_data(self):
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'loop_enabled': self.loop_enabled,
            'loop_interval': self.loop_interval,
            'auto_exec_downstream': self.auto_exec_downstream,
            'force_trigger': self.force_trigger
        }

    def load_additional_data(self, data):
        self.x = data.get('x', 100)
        self.y = data.get('y', 100)
        self.width = data.get('width', 200)
        self.height = data.get('height', 120)
        self.loop_enabled = data.get('loop_enabled', False)
        self.loop_interval = data.get('loop_interval', 1.0)
        self.auto_exec_downstream = data.get('auto_exec_downstream', False)
        self.force_trigger = data.get('force_trigger', False)
        if self.loop_enabled:
            self.start_loop()

    def place_event(self):
        if self.loop_enabled:
            self.start_loop()

    def remove_event(self):
        self.stop_loop()

    def start_loop(self):
        self.stop_loop()
        self._loop_running = True
        import threading
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._loop_thread.start()

    def stop_loop(self):
        self._loop_running = False
        self._loop_thread = None

    def _run_loop(self):
        import time
        while self._loop_running:
            try:
                self.update()
            except Exception as e:
                print(f"Error in loop update for node {self.global_id}: {e}")
            time.sleep(max(0.1, self.loop_interval))

    def update(self, inp=-1):
        if global_execution_paused:
            return
        # Downstream execution propagation hook for exec mode
        if self.flow.algorithm_mode() == 'exec' and getattr(self, 'auto_exec_downstream', False):
            executor = self.flow.executor
            if executor.updated_nodes is None:
                downstream = get_downstream_nodes(self)
                all_nodes = set(self.flow.nodes)
                # Block updates on all non-downstream nodes (upstream and unrelated)
                non_downstream = all_nodes - downstream
                executor.updated_nodes = non_downstream
                try:
                    # Update ourselves first while blocking upstream updates
                    super().update(inp)
                    # Update downstream nodes one by one in topological order
                    if downstream:
                        sorted_downstream = topological_sort(downstream, self.flow)
                        for node in sorted_downstream:
                            if node in executor.updated_nodes:
                                continue
                            try:
                                trigger_idx = get_trigger_input_index(node, self.flow, downstream, self)
                                node.update(trigger_idx)
                            except Exception as e:
                                print(f"Error propagating exec to downstream node {node.global_id}: {e}")
                finally:
                    executor.updated_nodes = None
                return

        # Default behavior
        super().update(inp)


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
        # Coerce to float/int if possible
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
        rc.NodeInputType(label='A', default=rc.Data(1.0)),
        rc.NodeInputType(label='B', default=rc.Data(1.0))
    ]
    init_outputs = [rc.NodeOutputType(label='prod')]

    def update_event(self, inp=-1):
        a = self.input(0).payload if self.input(0) else 1.0
        b = self.input(1).payload if self.input(1) else 1.0
        try: a = float(a)
        except: pass
        try: b = float(b)
        except: pass
        self.set_output_val(0, rc.Data(a * b))


class DivideNode(WebNode):
    title = 'Divide'
    init_inputs = [
        rc.NodeInputType(label='A', default=rc.Data(1.0)),
        rc.NodeInputType(label='B', default=rc.Data(1.0))
    ]
    init_outputs = [rc.NodeOutputType(label='div')]

    def update_event(self, inp=-1):
        a = self.input(0).payload if self.input(0) else 1.0
        b = self.input(1).payload if self.input(1) else 1.0
        try: a = float(a)
        except: pass
        try: b = float(b)
        except: pass
        res = a / b if b != 0 else 0
        self.set_output_val(0, rc.Data(res))


# String Nodes
class NumberNode(WebNode):
    title = 'Number'
    init_inputs = [rc.NodeInputType(label='val', default=rc.Data(0.0))]
    init_outputs = [rc.NodeOutputType(label='out')]

    def update_event(self, inp=-1):
        v = self.input(0).payload if self.input(0) else 0.0
        try: v = float(v)
        except: pass
        self.set_output_val(0, rc.Data(v))


class StringNode(WebNode):
    title = 'String'
    init_inputs = [rc.NodeInputType(label='val', default=rc.Data('Hello'))]
    init_outputs = [rc.NodeOutputType(label='out')]

    def update_event(self, inp=-1):
        v = self.input(0).payload if self.input(0) else ''
        self.set_output_val(0, rc.Data(str(v)))


class ConcatNode(WebNode):
    title = 'Concat'
    init_inputs = [
        rc.NodeInputType(label='str1', default=rc.Data('')),
        rc.NodeInputType(label='str2', default=rc.Data(''))
    ]
    init_outputs = [rc.NodeOutputType(label='out')]

    def update_event(self, inp=-1):
        s1 = str(self.input(0).payload if self.input(0) else '')
        s2 = str(self.input(1).payload if self.input(1) else '')
        self.set_output_val(0, rc.Data(s1 + s2))


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


# List of node templates
NODE_CLASSES = [
    NumberNode, StringNode, AddNode, SubtractNode, MultiplyNode, DivideNode,
    ConcatNode, UppercaseNode, CompareNode, IfElseNode, RandomNode, LogNode,
    TriggerNode, BranchNode, CounterNode, ExecuteButtonNode
]

# Instantiate Session & Flow
session = rc.Session()
session.register_node_types(NODE_CLASSES)
flow = session.create_flow('main')

# Setup default nodes for representation
n_num1 = flow.create_node(NumberNode)
n_num1.x, n_num1.y = 100, 150
n_num1.inputs[0].default = rc.Data(15.0)

n_num2 = flow.create_node(NumberNode)
n_num2.x, n_num2.y = 100, 320
n_num2.inputs[0].default = rc.Data(27.0)

n_add = flow.create_node(AddNode)
n_add.x, n_add.y = 350, 220

n_log = flow.create_node(LogNode)
n_log.x, n_log.y = 600, 240

flow.connect_nodes(n_num1.outputs[0], n_add.inputs[0])
flow.connect_nodes(n_num2.outputs[0], n_add.inputs[1])
flow.connect_nodes(n_add.outputs[0], n_log.inputs[0])

# Trigger first execution
n_num1.update()
n_num2.update()

def serialize_payload(val):
    if val is None:
        return None
    if hasattr(val, 'payload'):
        return val.payload
    return val

def get_input_val(node, index):
    inp = node.inputs[index]
    conn_out = flow.graph_adj_rev.get(inp)
    if conn_out:
        return conn_out.val
    else:
        return inp.default

def get_flow_state():
    nodes_data = []
    for n in flow.nodes:
        inputs_data = []
        for i, inp in enumerate(n.inputs):
            inputs_data.append({
                'label': inp.label_str,
                'type': inp.type_,
                'val': serialize_payload(get_input_val(n, i)) if inp.type_ == 'data' else None
            })
        outputs_data = []
        for out in n.outputs:
            outputs_data.append({
                'label': out.label_str,
                'type': out.type_,
                'val': serialize_payload(out.val)
            })
        nodes_data.append({
            'id': n.global_id,
            'identifier': n.identifier,
            'title': n.title,
            'x': getattr(n, 'x', 100),
            'y': getattr(n, 'y', 100),
            'width': getattr(n, 'width', 200),
            'height': getattr(n, 'height', 120),
            'loop_enabled': getattr(n, 'loop_enabled', False),
            'loop_interval': getattr(n, 'loop_interval', 1.0),
            'auto_exec_downstream': getattr(n, 'auto_exec_downstream', False),
            'force_trigger': getattr(n, 'force_trigger', False),
            'target_node_id': getattr(n, 'target_node_id', None),
            'inputs': inputs_data,
            'outputs': outputs_data
        })
    
    connections_data = []
    for n in flow.nodes:
        for j, out in enumerate(n.outputs):
            for inp in flow.graph_adj[out]:
                connections_data.append({
                    'parent_node_id': out.node.global_id,
                    'output_index': j,
                    'connected_node_id': inp.node.global_id,
                    'input_index': inp.node.inputs.index(inp)
                })

    return {
        'algorithm_mode': flow.algorithm_mode(),
        'execution_paused': global_execution_paused,
        'nodes': nodes_data,
        'connections': connections_data
    }

class APIRequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/api/nodes':
            nodes_templates = []
            for nc in NODE_CLASSES:
                # build identifier for template details
                nc._build_identifier()
                nodes_templates.append({
                    'identifier': nc.identifier,
                    'title': nc.title,
                    'inputs': [{'label': i.label, 'type': i.type_} for i in nc.init_inputs],
                    'outputs': [{'label': o.label, 'type': o.type_} for o in nc.init_outputs]
                })
            self.send_json_response(nodes_templates)
        elif path == '/api/flow':
            self.send_json_response(get_flow_state())
        elif path == '/api/logs':
            self.send_json_response(log_messages)
        else:
            # Serve static files from web_frontend folder
            filename = path.lstrip('/')
            if filename == '':
                filename = 'index.html'
            
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_frontend', filename)
            if os.path.exists(filepath) and os.path.isfile(filepath):
                self.send_response(200)
                if filepath.endswith('.html'):
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                elif filepath.endswith('.css'):
                    self.send_header('Content-Type', 'text/css; charset=utf-8')
                elif filepath.endswith('.js'):
                    self.send_header('Content-Type', 'application/javascript; charset=utf-8')
                self.end_headers()
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, 'File Not Found')

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            req = json.loads(post_data) if post_data else {}
        except Exception:
            req = {}

        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        global flow, session, global_execution_paused
        try:
            if path == '/api/create_node':
                identifier = req.get('identifier')
                x = float(req.get('x', 100))
                y = float(req.get('y', 100))
                
                node_class = next((nc for nc in NODE_CLASSES if nc.identifier == identifier), None)
                if node_class:
                    n = flow.create_node(node_class)
                    n.x = x
                    n.y = y
                    n.update()
                    self.send_json_response({'status': 'success', 'node': {'id': n.global_id}})
                else:
                    self.send_error_response('Node class not found')

            elif path == '/api/delete_node':
                node_id = int(req.get('node_id'))
                n = next((node for node in flow.nodes if node.global_id == node_id), None)
                if n:
                    flow.remove_node(n)
                    self.send_json_response({'status': 'success'})
                else:
                    self.send_error_response('Node not found')

            elif path == '/api/move_node':
                node_id = int(req.get('node_id'))
                x = float(req.get('x'))
                y = float(req.get('y'))
                width = req.get('width')
                height = req.get('height')
                n = next((node for node in flow.nodes if node.global_id == node_id), None)
                if n:
                    n.x = x
                    n.y = y
                    if width is not None:
                        n.width = float(width)
                    if height is not None:
                        n.height = float(height)
                    self.send_json_response({'status': 'success'})
                else:
                    self.send_error_response('Node not found')

            elif path == '/api/connect':
                p_id = int(req.get('parent_node_id'))
                o_idx = int(req.get('output_index'))
                c_id = int(req.get('connected_node_id'))
                i_idx = int(req.get('input_index'))

                parent_node = next((node for node in flow.nodes if node.global_id == p_id), None)
                connected_node = next((node for node in flow.nodes if node.global_id == c_id), None)

                if parent_node and connected_node:
                    out = parent_node.outputs[o_idx]
                    inp = connected_node.inputs[i_idx]
                    res = flow.connect_nodes(out, inp)
                    if res:
                        # Trigger updates
                        parent_node.update()
                        self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                    else:
                        self.send_error_response('Connection invalid')
                else:
                    self.send_error_response('Nodes not found')

            elif path == '/api/disconnect':
                p_id = int(req.get('parent_node_id'))
                o_idx = int(req.get('output_index'))
                c_id = int(req.get('connected_node_id'))
                i_idx = int(req.get('input_index'))

                parent_node = next((node for node in flow.nodes if node.global_id == p_id), None)
                connected_node = next((node for node in flow.nodes if node.global_id == c_id), None)

                if parent_node and connected_node:
                    out = parent_node.outputs[o_idx]
                    inp = connected_node.inputs[i_idx]
                    flow.disconnect_nodes(out, inp)
                    # Trigger updates
                    parent_node.update()
                    connected_node.update()
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Nodes not found')

            elif path == '/api/update_input':
                node_id = int(req.get('node_id'))
                i_idx = int(req.get('input_index'))
                val = req.get('val')
                
                n = next((node for node in flow.nodes if node.global_id == node_id), None)
                if n:
                    inp = n.inputs[i_idx]
                    # Coerce values safely
                    try:
                        if '.' in str(val):
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        pass # keep as string or whatever type was entered
                    
                    inp.default = rc.Data(val)
                    n.update(i_idx)
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Node not found')

            elif path == '/api/update_loop':
                node_id = int(req.get('node_id'))
                enabled = bool(req.get('enabled'))
                interval = float(req.get('interval', 1.0))
                
                n = next((node for node in flow.nodes if node.global_id == node_id), None)
                if n:
                    n.loop_enabled = enabled
                    n.loop_interval = interval
                    if enabled:
                        n.start_loop()
                    else:
                        n.stop_loop()
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Node not found')

            elif path == '/api/update_auto_exec':
                node_id = int(req.get('node_id'))
                enabled = bool(req.get('enabled'))
                
                n = next((node for node in flow.nodes if node.global_id == node_id), None)
                if n:
                    n.auto_exec_downstream = enabled
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Node not found')

            elif path == '/api/update_force_trigger':
                node_id = int(req.get('node_id'))
                enabled = bool(req.get('enabled'))
                
                n = next((node for node in flow.nodes if node.global_id == node_id), None)
                if n:
                    n.force_trigger = enabled
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Node not found')

            elif path == '/api/set_button_target':
                b_id = int(req.get('button_node_id'))
                t_id = req.get('target_node_id')
                if t_id is not None:
                    t_id = int(t_id)

                button_node = next((node for node in flow.nodes if node.global_id == b_id), None)
                if button_node:
                    button_node.target_node_id = t_id
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Button node not found')

            elif path == '/api/trigger_node':
                node_id = int(req.get('node_id'))
                n = next((node for node in flow.nodes if node.global_id == node_id), None)
                if n:
                    flow.executor.force_propagation = True
                    try:
                        n.update()
                    finally:
                        flow.executor.force_propagation = False
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Node not found')

            elif path == '/api/set_alg_mode':
                mode = req.get('mode')
                if flow.set_algorithm_mode(mode):
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Invalid algorithm mode')

            elif path == '/api/set_paused':
                paused = bool(req.get('paused'))
                global_execution_paused = paused
                self.send_json_response({'status': 'success', 'flow': get_flow_state()})

            elif path == '/api/clear':
                # Re-create empty flow
                title = flow.title
                for n in list(flow.nodes):
                    if hasattr(n, 'stop_loop'):
                        n.stop_loop()
                session.delete_flow(flow)
                flow = session.create_flow(title)
                global_execution_paused = False
                self.send_json_response({'status': 'success', 'flow': get_flow_state()})

            elif path == '/api/save':
                filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flow_project.json')
                data = session.serialize()
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=4)
                self.send_json_response({'status': 'success', 'filepath': filepath})

            elif path == '/api/load':
                filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flow_project.json')
                if os.path.exists(filepath):
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    # Stop current loops first
                    for n in list(flow.nodes):
                        if hasattr(n, 'stop_loop'):
                            n.stop_loop()
                    
                    # Recreate session & flow
                    session = rc.Session()
                    session.register_node_types(NODE_CLASSES)
                    # Load will rebuild
                    flows = session.load(data)
                    if flows:
                        flow = flows[0]
                    global_execution_paused = False
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('No saved project file found')

            elif path == '/api/add_log':
                msg = req.get('msg')
                if msg:
                    add_server_log(msg)
                self.send_json_response({'status': 'success'})

            elif path == '/api/clear_logs':
                log_messages.clear()
                self.send_json_response({'status': 'success'})

            else:
                self.send_error(404, 'Endpoint Not Found')
        except Exception as e:
            traceback.print_exc()
            self.send_error_response(str(e))

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_response(self, message):
        self.send_response(400)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'error', 'message': message}).encode('utf-8'))


def run(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, APIRequestHandler)
    print(f'Starting web server on port {port}...')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    print('Stopping web server.')

if __name__ == '__main__':
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run(port)
