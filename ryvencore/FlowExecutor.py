"""
The flow executors are responsible for executing the flow. They have access to
the flow as well as the nodes' internals and are able to perform optimizations.
"""
# prevent cyclic imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .Flow import Flow
    from .Node import Node

from typing import Optional

from .Data import Data
from .NodePort import NodeOutput, NodeInput
from .RC import FlowAlg


"""
graph_adjacency = {
    node_output: [node_input],    
    node_input:  node_output | None
}
"""


class FlowExecutor:
    """
    Base class for special flow execution algorithms.
    """

    def __init__(self, flow: Flow):
        self.flow = flow
        self.flow_changed = True
        self.graph = self.flow.graph_adj
        self.graph_rev = self.flow.graph_adj_rev
        self.force_propagation = False

    # Node.update() =>
    def update_node(self, node: Node, inp: int):
        pass

    # Node.input() =>
    def input(self, node: Node, index: int) -> Optional[Data]:
        pass

    # Node.set_output_val() =>
    def set_output_val(self, node: Node, index: int, val) -> None:
        pass

    # Node.exec_output() =>
    def exec_output(self, node: Node, index: int) -> None:
        pass

    def conn_added(self, out: NodeOutput, inp: NodeInput, silent=False) -> None:
        pass

    def conn_removed(self, out: NodeOutput, inp: NodeInput, silent=False) -> None:
        pass


class DataFlowNaive(FlowExecutor):
    """
    The naive implementation of data-flow execution. Naive meaning setting a node output
    leads to an immediate update in all successors consecutively. No runtime optimization
    if performed, and some types of graphs can run really slow here, especially if they
    include "diamonds".

    Assumptions for the graph:
    - no non-terminating feedback loops
    """

    # Node.update() =>
    def update_node(self, node: Node, inp: int):
        try:
            node.update_event(inp)
        except Exception as e:
            node.update_err(e)

    # Node.input() =>
    def input(self, node: Node, index: int):
        inp = node.inputs[index]
        conn_out = self.graph_rev[inp]

        if conn_out:
            return conn_out.val
        else:
            return inp.default

    # Node.set_output_val() =>
    def set_output_val(self, node: Node, index: int, data):
        out = node.outputs[index]
        if not out.type_ == 'data':
            return
        out.val = data

        if getattr(node, 'force_trigger', False) and not getattr(self, 'force_propagation', False):
            return

        for inp in self.graph[out]:
            inp.node.update(inp=inp.node.inputs.index(inp))

    # Node.exec_output() =>
    def exec_output(self, node: Node, index: int):
        out = node.outputs[index]
        if not out.type_ == 'exec':
            return

        if getattr(node, 'force_trigger', False) and not getattr(self, 'force_propagation', False):
            return

        for inp in self.graph[out]:
            inp.node.update(inp=inp.node.inputs.index(inp))

    def conn_added(self, out: NodeOutput, inp: NodeInput, silent=False):
        if not silent:
            # update input
            inp.node.update(inp=inp.node.inputs.index(inp))

    def conn_removed(self, out, inp, silent=False):
        if not silent:
            # update input
            inp.node.update(inp=inp.node.inputs.index(inp))


import threading

class DataFlowOptimized(DataFlowNaive):
    """
    *(see also documentation in Flow)*

    A special flow executor which implements some node functions to optimise flow execution.
    Whenever a new execution is invoked somewhere (some node or output is updated), it
    analyses the graph's connected component (of successors) where the execution was invoked
    and creates a few data structures to reverse engineer how many input
    updates every node possibly receives in this execution. A node's outputs are
    propagated once no input can still receive new data from a predecessor node.
    Therefore, while a node gets updated every time an input receives some data,
    every OUTPUT is only updated ONCE.
    This implies that every connection is activated at most once in an execution.
    This can result in asymptotic speedup in large data flows compared to normal data flow
    execution where any two executed branches which merge again in the future result in two
    complete executions of everything that comes after the merge, which quickly produces
    exponential performance issues.
    """

    def __init__(self, flow):
        super().__init__(flow)
        self._local = threading.local()
        self._cache_lock = threading.Lock()
        self._waiting_count_cache = {}
        self.flow_changed = True
        self.last_execution_root = None

    @property
    def output_updated(self):
        if not hasattr(self._local, 'output_updated'):
            self._local.output_updated = {}
        return self._local.output_updated

    @output_updated.setter
    def output_updated(self, val):
        self._local.output_updated = val

    @property
    def waiting_count(self):
        if not hasattr(self._local, 'waiting_count'):
            self._local.waiting_count = {}
        return self._local.waiting_count

    @waiting_count.setter
    def waiting_count(self, val):
        self._local.waiting_count = val

    @property
    def node_waiting(self):
        if not hasattr(self._local, 'node_waiting'):
            self._local.node_waiting = {}
        return self._local.node_waiting

    @node_waiting.setter
    def node_waiting(self, val):
        self._local.node_waiting = val

    @property
    def execution_root(self):
        return getattr(self._local, 'execution_root', None)

    @execution_root.setter
    def execution_root(self, val):
        self._local.execution_root = val

    @property
    def execution_root_node(self):
        return getattr(self._local, 'execution_root_node', None)

    @execution_root_node.setter
    def execution_root_node(self, val):
        self._local.execution_root_node = val

    # NODE FUNCTIONS

    # Node.update() =>
    def update_node(self, node, inp=-1):
        if self.execution_root_node is None:  # execution starter!
            self.start_execution(root_node=node)
            self.invoke_node_update_event(node, inp)
            self.propagate_outputs(node)
            self.stop_execution()
        else:
            self.invoke_node_update_event(node, inp)

    # Node.input() =>
    #   DataFlowNaive.input(node, index)

    # Node.set_output_val() =>
    def set_output_val(self, node, index, data):
        out = node.outputs[index]

        if self.execution_root_node is None:  # execution starter!
            self.start_execution(root_output=out)

            out.val = data
            self.output_updated[out] = True
            self.propagate_output(out)

            self.stop_execution()

        else:
            if not self.node_waiting.get(out.node, False):
                # the output's node might not be part of the analyzed graph!
                super().set_output_val(node, index, data)

            else:
                out.val = data
                self.output_updated[out] = True

    # Node.exec_output() =>
    def exec_output(self, node, index):
        out = node.outputs[index]

        if self.execution_root_node is None:  # execution starter!
            self.start_execution(root_output=out)

            self.output_updated[out] = True
            self.propagate_output(out)

            self.stop_execution()

        else:
            self.output_updated[out] = True

    """
    
    Helper methods
    
    """

    def start_execution(self, root_node=None, root_output=None):
        # reset cached output values (empty dict, default False)
        self.output_updated = {}

        if root_node is not None:
            self.execution_root = root_node
            self.execution_root_node = root_node
            self.waiting_count = self.generate_waiting_count(root_node=root_node)

        elif root_output is not None:
            self.execution_root = root_output
            self.execution_root_node = root_output.node
            self.waiting_count = self.generate_waiting_count(root_output=root_output)

    def stop_execution(self):
        self.execution_root_node = None
        self.last_execution_root = self.execution_root
        self.execution_root = None

    def generate_waiting_count(self, root_node=None, root_output=None):
        with self._cache_lock:
            if self.flow_changed:
                self._waiting_count_cache = {}
                self.flow_changed = False

            cache_key = (root_node, root_output)
            if cache_key in self._waiting_count_cache:
                num_conns, node_waiting = self._waiting_count_cache[cache_key]
                self.node_waiting = node_waiting
                return num_conns.copy()

        nodes = self.flow.nodes
        node_successors = self.flow.node_successors

        # DP TABLE
        num_conns_from_predecessors = {
            n: 0
            for n in nodes
        }

        successors = set()
        visited = {
            n: False
            for n in nodes
        }

        # BC
        if root_node is not None:
            successors.add(root_node)

        elif root_output is not None:
            for inp in self.graph[root_output]:
                connected_node = inp.node
                num_conns_from_predecessors[connected_node] += 1
                successors.add(connected_node)

        # ITERATION
        while len(successors) > 0:
            n = successors.pop()
            if visited[n]:
                continue

            for s in node_successors[n]:
                num_conns_from_predecessors[s] += 1
                successors.add(s)
            visited[n] = True

        self.node_waiting = visited

        with self._cache_lock:
            self._waiting_count_cache[cache_key] = (num_conns_from_predecessors, visited)

        return num_conns_from_predecessors.copy()

    def invoke_node_update_event(self, node, inp):
        super().update_node(node, inp)

    def decrease_wait(self, node):
        """decreases the wait count of the node;
        if the count reaches zero, which means there is no other input waiting for data,
        the output values get propagated"""

        self.waiting_count[node] -= 1
        if self.waiting_count[node] == 0:
            self.propagate_outputs(node)

    def propagate_outputs(self, node):
        """propagates all outputs of node"""

        for out in node.outputs:
            self.propagate_output(out)

    def propagate_output(self, out):
        """pushes an output's value to successors if it has been changed in the execution"""

        if self.output_updated.get(out, False) and not (getattr(out.node, 'force_trigger', False) and not getattr(self, 'force_propagation', False)):
            # same procedure for data and exec connections
            for inp in self.graph[out]:
                inp.node.update(inp=inp.node.inputs.index(inp))

        # decrease wait count of successors
        for inp in self.graph[out]:
            self.decrease_wait(inp.node)


class ExecFlowNaive(FlowExecutor):
    """
    ...
    """

    def __init__(self, flow):
        super().__init__(flow)

        # all the nodes currently updating because of an output data request
        # used to prevent redundant predecessor updates during the update
        # of a single successor
        self.updated_nodes = None

    # Node.update() = >
    def update_node(self, node, inp):
        if inp != -1 and node.inputs[inp].type_ == 'data':
            return

        execution_starter = self.updated_nodes is None

        if execution_starter:
            self.updated_nodes = {node}
        else:
            self.updated_nodes.add(node)

        try:
            node.update_event(inp)
        except Exception as e:
            node.update_err(e)

        if execution_starter:
            self.updated_nodes = None

    # Node.input() =>
    def input(self, node, index):
        inp = node.inputs[index]
        out = self.graph_rev[inp]
        if out:
            n = out.node
            if n not in self.updated_nodes:
                n.update(-1)

            return out.val
        else:
            return None

    # Node.set_output_val() =>
    def set_output_val(self, node, index, data):
        out = node.outputs[index]
        out.val = data

    # Node.exec_output() =>
    def exec_output(self, node, index):
        for inp in self.graph[node.outputs[index]]:
            inp.node.update(inp.node.inputs.index(inp))


class CompiledFlowExecutor(FlowExecutor):
    """
    A compiled flow executor that translates the graph into a single Python script
    and runs updates through it at native speed in the same process.
    """

    def __init__(self, flow):
        super().__init__(flow)
        self.compiled_module = None
        self.compiled_nodes = {}
        self.flow_changed = True

    def update_node(self, node, inp):
        if self.flow_changed or not self.compiled_nodes:
            self.compile_and_load()

        comp_node = self.compiled_nodes.get(node.global_id)
        if comp_node:
            # Sync inputs from actual node to compiled node
            for idx, inp_port in enumerate(node.inputs):
                if idx < len(comp_node.inputs):
                    comp_node.inputs[idx].default = inp_port.default

            # Run compiled update
            comp_node.update(inp)

    def set_output_val(self, node, index, data):
        if self.flow_changed or not self.compiled_nodes:
            self.compile_and_load()

        comp_node = self.compiled_nodes.get(node.global_id)
        if comp_node:
            comp_node.set_output_val(index, data)

    def exec_output(self, node, index):
        if self.flow_changed or not self.compiled_nodes:
            self.compile_and_load()

        comp_node = self.compiled_nodes.get(node.global_id)
        if comp_node:
            comp_node.exec_output(index)

    def run_external_compile(self):
        import os
        import sys
        import json
        import subprocess
        import tempfile
        
        # Serialize current session state to a temp file
        temp_dir = os.path.abspath('compiled')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Serialize the session containing this flow
        data = self.flow.session.serialize()
        
        with tempfile.NamedTemporaryFile(suffix='.json', dir=temp_dir, delete=False, mode='w', encoding='utf-8') as temp_f:
            json.dump(data, temp_f, indent=4)
            temp_path = temp_f.name
            
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'compile_workflow.py')
        
        result = subprocess.run(
            [sys.executable, script_path, temp_path, temp_dir],
            capture_output=True,
            text=True,
            check=False
        )
        
        # Clean up
        try:
            os.remove(temp_path)
        except:
            pass
            
        if result.returncode == 0 and "SUCCESS:" in result.stdout:
            filename = ""
            for line in result.stdout.splitlines():
                if line.startswith("SUCCESS:"):
                    filename = line.split("SUCCESS:")[1].strip()
                    break
            self.flow.active_compiled_file = filename
            return filename
        else:
            raise RuntimeError(f"Compilation script failed: {result.stderr or result.stdout}")

    def compile_and_load(self):
        import os
        import importlib.util
        import sys
        
        compiled_dir = os.path.abspath('compiled')
        
        # Determine which file to load
        filename = getattr(self.flow, 'active_compiled_file', None)
        
        # If active_compiled_file is not set or doesn't exist, try to find the latest matching file
        flow_title_safe = "".join(c for c in self.flow.title if c.isalnum() or c == '_')
        if not flow_title_safe:
            flow_title_safe = "flow"
            
        if not filename or not os.path.exists(os.path.join(compiled_dir, filename)):
            # Scan compiled directory for matching files
            candidates = []
            if os.path.exists(compiled_dir):
                for f in os.listdir(compiled_dir):
                    if f.endswith('.py') and (f == f"{flow_title_safe}_compiled.py" or (f.startswith(flow_title_safe + "_") and len(f) > len(flow_title_safe) + 4)):
                        candidates.append(f)
            if candidates:
                # Sort by modification time, latest first
                candidates.sort(key=lambda x: os.path.getmtime(os.path.join(compiled_dir, x)), reverse=True)
                filename = candidates[0]
                self.flow.active_compiled_file = filename
                
        # If still no file exists, we force compile!
        if not filename or not os.path.exists(os.path.join(compiled_dir, filename)):
            filename = self.run_external_compile()
            
        filepath = os.path.join(compiled_dir, filename)
        
        # Load the module dynamically
        module_name = f"compiled_{filename[:-3]}"
        
        if module_name in sys.modules:
            del sys.modules[module_name]
            
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        self.compiled_module = module
        actual_nodes = {n.global_id: n for n in self.flow.nodes}
        self.compiled_nodes = module.setup_flow(actual_nodes)
        self.flow_changed = False


def executor_from_flow_alg(algorithm: FlowAlg):
    if algorithm == FlowAlg.DATA:
        return DataFlowNaive
    if algorithm == FlowAlg.DATA_OPT:
        return DataFlowOptimized
    if algorithm == FlowAlg.EXEC:
        return ExecFlowNaive
    if algorithm == FlowAlg.COMPILED:
        return CompiledFlowExecutor
