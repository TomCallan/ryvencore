import ryvencore as rc
import time
import datetime

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
        while self._loop_running:
            if global_execution_paused:
                time.sleep(0.5)
                continue
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
