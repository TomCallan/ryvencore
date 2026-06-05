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

import importlib

# Ensure nodes folder is in sys.path
nodes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodes')
if nodes_dir not in sys.path:
    sys.path.append(nodes_dir)

import nodes.base as nb
from nodes.base import WebNode

NODE_CLASSES = []

def load_nodes_from_folder():
    global NODE_CLASSES
    NODE_CLASSES = []
    for filename in os.listdir(nodes_dir):
        if filename.endswith('.py') and filename not in ('__init__.py', 'base.py'):
            module_name = filename[:-3]
            try:
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    module = importlib.import_module(module_name)
                    
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, rc.Node) and attr not in (rc.Node, WebNode):
                        if attr not in NODE_CLASSES:
                            NODE_CLASSES.append(attr)
            except Exception as e:
                print(f"Error loading module {module_name}: {e}")

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


# Instantiate Session
session = rc.Session()

# Load node classes dynamically
load_nodes_from_folder()
session.register_node_types(NODE_CLASSES)

# Import classes for default flow setup
from basic_nodes import NumberNode, AddNode, LogNode

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
            'code': getattr(n, 'code', None),
            'script_path': getattr(n, 'script_path', None),
            'buffer': getattr(n, 'buffer', None),
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
        'execution_paused': nb.global_execution_paused,
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
            load_nodes_from_folder()
            session.register_node_types(NODE_CLASSES)
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
            self.send_json_response(nb.log_messages)
        elif path == '/api/list_flows':
            flows_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_flows')
            os.makedirs(flows_dir, exist_ok=True)
            files = []
            for filename in os.listdir(flows_dir):
                if filename.endswith('.json'):
                    files.append(filename[:-5])
            
            default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flow_project.json')
            if os.path.exists(default_path) and 'flow_project' not in files:
                files.append('flow_project')
            
            self.send_json_response({'status': 'success', 'flows': sorted(files)})
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
                    # Disconnect all inputs
                    for inp in list(n.inputs):
                        out = flow.connected_output(inp)
                        if out is not None:
                            flow.disconnect_nodes(out, inp)
                    # Disconnect all outputs
                    for out in list(n.outputs):
                        for inp in list(flow.connected_inputs(out)):
                            flow.disconnect_nodes(out, inp)
                            
                    if hasattr(n, 'stop_loop'):
                        n.stop_loop()
                        
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

            elif path == '/api/update_node_property':
                node_id = int(req.get('node_id'))
                name = req.get('name')
                val = req.get('val')
                
                n = next((node for node in flow.nodes if node.global_id == node_id), None)
                if n:
                    # Safely coerce boolean and numeric types
                    if val == 'true' or val is True:
                        val = True
                    elif val == 'false' or val is False:
                        val = False
                    elif val is None or val == '':
                        val = None
                    else:
                        try:
                            if '.' in str(val):
                                val = float(val)
                            else:
                                val = int(val)
                        except ValueError:
                            pass
                    
                    setattr(n, name, val)
                    
                    # Handle thread loop state if loop_enabled is modified
                    if name == 'loop_enabled':
                        if val:
                            n.start_loop()
                        else:
                            n.stop_loop()
                            
                    n.update()
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Node not found')

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
                nb.global_execution_paused = paused
                self.send_json_response({'status': 'success', 'flow': get_flow_state()})

            elif path == '/api/clear':
                # Re-create empty flow
                title = flow.title
                for n in list(flow.nodes):
                    if hasattr(n, 'stop_loop'):
                        n.stop_loop()
                session.delete_flow(flow)
                flow = session.create_flow(title)
                nb.global_execution_paused = False
                self.send_json_response({'status': 'success', 'flow': get_flow_state()})

            elif path == '/api/save':
                name = req.get('name', 'flow_project')
                if not name.strip():
                    name = 'flow_project'
                name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
                if not name:
                    name = 'flow_project'
                
                flows_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_flows')
                os.makedirs(flows_dir, exist_ok=True)
                
                filepath = os.path.join(flows_dir, f"{name}.json")
                data = session.serialize()
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=4)
                
                # Also save default flow_project.json in root if it's the default name
                if name == 'flow_project':
                    default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flow_project.json')
                    with open(default_path, 'w') as f:
                        json.dump(data, f, indent=4)

                self.send_json_response({'status': 'success', 'filepath': filepath, 'name': name})

            elif path == '/api/load':
                name = req.get('name', 'flow_project')
                name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
                if not name:
                    name = 'flow_project'
                
                flows_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_flows')
                filepath = os.path.join(flows_dir, f"{name}.json")
                
                if not os.path.exists(filepath) and name == 'flow_project':
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
                    flows = session.load(data)
                    if flows:
                        flow = flows[0]
                    nb.global_execution_paused = False
                    self.send_json_response({'status': 'success', 'flow': get_flow_state(), 'name': name})
                else:
                    self.send_error_response(f'Saved flow file not found: {name}')

            elif path == '/api/add_log':
                msg = req.get('msg')
                if msg:
                    nb.add_server_log(msg)
                self.send_json_response({'status': 'success'})

            elif path == '/api/clear_logs':
                nb.log_messages.clear()
                self.send_json_response({'status': 'success'})

            elif path == '/api/add_port':
                node_id = int(req.get('node_id'))
                direction = req.get('direction')
                n = next((node for node in flow.nodes if node.global_id == node_id), None)
                if n:
                    if direction == 'input':
                        label = f"in{len(n.inputs) + 1}"
                        n.create_input(label=label, default=rc.Data(0.0))
                    elif direction == 'output':
                        label = f"out{len(n.outputs) + 1}"
                        n.create_output(label=label)
                    n.update()
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Node not found')

            elif path == '/api/delete_port':
                node_id = int(req.get('node_id'))
                direction = req.get('direction')
                index = int(req.get('index'))
                n = next((node for node in flow.nodes if node.global_id == node_id), None)
                if n:
                    if direction == 'input':
                        n.delete_input(index)
                    elif direction == 'output':
                        n.delete_output(index)
                    n.update()
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Node not found')

            elif path == '/api/rename_port':
                node_id = int(req.get('node_id'))
                direction = req.get('direction')
                index = int(req.get('index'))
                label = req.get('label')
                n = next((node for node in flow.nodes if node.global_id == node_id), None)
                if n:
                    if direction == 'input':
                        n.rename_input(index, label)
                    elif direction == 'output':
                        n.rename_output(index, label)
                    n.update()
                    self.send_json_response({'status': 'success', 'flow': get_flow_state()})
                else:
                    self.send_error_response('Node not found')

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
