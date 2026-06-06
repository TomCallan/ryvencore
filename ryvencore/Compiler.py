import inspect
import json
import hashlib
from typing import List, Set, Type
from .Flow import Flow
from .Node import Node

class FlowCompiler:
    """
    Compiles a ryvencore Flow into a single, self-contained Python script.
    This eliminates the overhead of the execution framework for high-throughput
    backtesting and live trading.
    """

    @staticmethod
    def get_structure_hash(flow: Flow) -> str:
        nodes = []
        for n in flow.nodes:
            inputs = [inp.label_str for inp in n.inputs]
            outputs = [out.label_str for out in n.outputs]
            nodes.append((n.global_id, type(n).__name__, inputs, outputs))
        nodes.sort(key=lambda x: x[0])
        
        connections = []
        for n in flow.nodes:
            for j, out in enumerate(n.outputs):
                if out in flow.graph_adj:
                    for inp in flow.graph_adj[out]:
                        try:
                            inp_idx = inp.node.inputs.index(inp)
                        except ValueError:
                            inp_idx = -1
                        connections.append((out.node.global_id, j, inp.node.global_id, inp_idx))
        connections.sort()
        
        structure = {
            'nodes': nodes,
            'connections': connections
        }
        struct_bytes = json.dumps(structure, sort_keys=True).encode('utf-8')
        return hashlib.sha256(struct_bytes).hexdigest()

    @staticmethod
    def compile(flow: Flow) -> str:
        # Get structure hash
        struct_hash = FlowCompiler.get_structure_hash(flow)

        # 1. Discover all node instances and classes used in the flow
        nodes = flow.nodes
        unique_classes: Set[Type[Node]] = {type(n) for n in nodes}

        # 2. Collect the source code of all custom node classes
        class_sources = []
        for cls in unique_classes:
            try:
                source = inspect.getsource(cls)
                class_sources.append(source)
            except Exception as e:
                # Fallback if source is not inspectable
                class_sources.append(f"class {cls.__name__}(WebNode):\n    pass\n")

        # 3. Generate self-contained compiled python code
        script = []
        script.append(f"# Structure Hash: {struct_hash}")
        script.append('"""')
        script.append(f"Compiled ryvencore flow: {flow.title}")
        script.append("Generated automatically by FlowCompiler.")
        script.append('"""')
        script.append("import sys")
        script.append("import time")
        script.append("import os")
        script.append("")

        # Add basic mocks of ryvencore classes
        script.append("""# --- Compiled ryvencore Runtime Mock ---
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

""")

        # Add node classes source code
        script.append("# --- Node Classes Definitions ---")
        for src in class_sources:
            script.append(src)
            script.append('')

        # Add flow execution setup
        script.append("# --- Flow Execution Instantiation ---")
        script.append("def setup_flow(actual_nodes=None):")
        script.append("    nodes = {}")
        script.append(f"    flow_alg = '{flow.algorithm_mode()}'")
        script.append("")

        # 5. Instantiate all nodes
        for n in nodes:
            class_name = type(n).__name__
            script.append(f"    # Node: {n.title} (ID: {n.global_id})")
            script.append(f"    n_{n.global_id} = {class_name}(params=None)")
            script.append(f"    n_{n.global_id}.node_id = {n.global_id}")
            script.append(f"    n_{n.global_id}.global_id = {n.global_id}")
            script.append(f"    n_{n.global_id}.flow_alg = flow_alg")
            script.append(f"    if actual_nodes and {n.global_id} in actual_nodes:")
            script.append(f"        n_{n.global_id}.actual_node = actual_nodes[{n.global_id}]")
            
            # Setup inputs
            for idx, inp in enumerate(n.inputs):
                def_val = f"rc.Data({repr(inp.default.payload)})" if inp.default else "rc.Data(None)"
                script.append(f"    n_{n.global_id}.create_input('{inp.label_str}', '{inp.type_}', default={def_val})")
            
            # Setup outputs
            for out in n.outputs:
                script.append(f"    n_{n.global_id}.create_output('{out.label_str}', '{out.type_}')")
            
            # Additional attributes if present (like file path, auto_exec_downstream)
            for attr in ['script_path', 'loop_enabled', 'loop_interval', 'wait_until_complete', 'code', 'buffer', 'target_node_id', 'auto_exec_downstream']:
                if hasattr(n, attr):
                    prop = getattr(type(n), attr, None)
                    if isinstance(prop, property) and prop.fset is None:
                        continue
                    val = getattr(n, attr)
                    if isinstance(val, str):
                        script.append(f"    n_{n.global_id}.{attr} = {repr(val)}")
                    else:
                        script.append(f"    n_{n.global_id}.{attr} = {val}")

            script.append(f"    nodes[{n.global_id}] = n_{n.global_id}")
            script.append("")

        # 6. Establish connections between nodes
        script.append("    # Connections")
        for out, inputs in flow.graph_adj.items():
            out_node_id = out.node.global_id
            out_port_idx = out.node.outputs.index(out)
            
            targets = []
            for inp in inputs:
                inp_node_id = inp.node.global_id
                inp_port_idx = inp.node.inputs.index(inp)
                targets.append(f"(nodes[{inp_node_id}], {inp_port_idx})")
            
            if targets:
                script.append(f"    nodes[{out_node_id}].connections[{out_port_idx}] = [{', '.join(targets)}]")

        script.append("")
        script.append("    # Run initial placement events")
        for n in nodes:
            script.append(f"    nodes[{n.global_id}].after_placement()")

        script.append("")
        script.append("    return nodes")
        script.append("")

        # Add execution main entrypoint
        script.append("""
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
""")

        return "\n".join(script)
