from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Type

from .Data import Data
from .Node import Node
from .NodePortType import NodeInputType, NodeOutputType
from .Session import Session


class NumberNode(Node):
    title = 'Number'
    init_inputs: List[NodeInputType] = []
    init_outputs = [NodeOutputType('value')]

    def __init__(self, params):
        super().__init__(params)
        self.value: float = 0.0

    def update_event(self, inp=-1):
        self.set_output_val(0, Data(self.value))

    def get_state(self) -> Dict[str, Any]:
        return {'value': self.value}

    def set_state(self, data: Dict[str, Any], version):
        if isinstance(data, dict) and isinstance(data.get('value'), (int, float)):
            self.value = float(data['value'])


class AddNode(Node):
    title = 'Add'
    init_inputs = [
        NodeInputType('a', default=Data(0)),
        NodeInputType('b', default=Data(0)),
    ]
    init_outputs = [NodeOutputType('sum')]

    def update_event(self, inp=-1):
        a = self.input(0)
        b = self.input(1)
        a_val = a.payload if a is not None else 0
        b_val = b.payload if b is not None else 0
        self.set_output_val(0, Data(a_val + b_val))


class MultiplyNode(Node):
    title = 'Multiply'
    init_inputs = [
        NodeInputType('a', default=Data(1)),
        NodeInputType('b', default=Data(1)),
    ]
    init_outputs = [NodeOutputType('product')]

    def update_event(self, inp=-1):
        a = self.input(0)
        b = self.input(1)
        a_val = a.payload if a is not None else 1
        b_val = b.payload if b is not None else 1
        self.set_output_val(0, Data(a_val * b_val))


class PrintNode(Node):
    title = 'Print'
    init_inputs = [NodeInputType('value')]
    init_outputs: List[NodeOutputType] = []

    def __init__(self, params):
        super().__init__(params)
        self.last_value: Optional[str] = None

    def update_event(self, inp=-1):
        value = self.input(0)
        payload = value.payload if value is not None else None
        self.last_value = str(payload)
        print(self.last_value)


EXAMPLE_NODE_TYPES: Sequence[Type[Node]] = (
    NumberNode,
    AddNode,
    MultiplyNode,
    PrintNode,
)


def example_node_schemas() -> List[Dict[str, Any]]:
    schemas: List[Dict[str, Any]] = []
    for node_type in EXAMPLE_NODE_TYPES:
        node_type._build_identifier()
        schemas.append(
            {
                'identifier': node_type.identifier,
                'title': node_type.title or node_type.__name__,
                'inputs': [
                    {'label': p.label or f'In {i}', 'type_': p.type_}
                    for i, p in enumerate(node_type.init_inputs)
                ],
                'outputs': [
                    {'label': p.label or f'Out {i}', 'type_': p.type_}
                    for i, p in enumerate(node_type.init_outputs)
                ],
            }
        )
    return schemas


def _connected_predecessor_count(flow, node: Node) -> int:
    return sum(1 for inp in node.inputs if flow.connected_output(inp) is not None)


def run_project(project: Dict[str, Any], flow_index: int = 0) -> Dict[str, Any]:
    session = Session()
    session.register_node_types(list(EXAMPLE_NODE_TYPES))
    session.load(project)

    if not session.flows:
        return {'trace': ['No flows found in project.'], 'node_runs': []}

    if flow_index < 0 or flow_index >= len(session.flows):
        flow_index = 0

    flow = session.flows[flow_index]
    root_nodes = [node for node in flow.nodes if _connected_predecessor_count(flow, node) == 0]
    if not root_nodes:
        root_nodes = list(flow.nodes)

    for node in root_nodes:
        node.update()

    trace = [f'Flow: {flow.title}', f'Executed {len(root_nodes)} root node(s).']
    node_runs: List[Dict[str, Any]] = []

    for index, node in enumerate(flow.nodes):
        outputs = []
        for output in node.outputs:
            output_val = output.val.payload if output.val is not None else None
            outputs.append(
                {
                    'label': output.label_str,
                    'type_': output.type_,
                    'value': output_val,
                }
            )

        run_info: Dict[str, Any] = {
            'index': index,
            'title': node.title,
            'identifier': node.identifier,
            'outputs': outputs,
        }
        if isinstance(node, PrintNode):
            run_info['last_value'] = node.last_value

        node_runs.append(run_info)
        trace.append(f'{index + 1}. {node.title} ({node.identifier}) outputs: {outputs}')

    printed = [r['last_value'] for r in node_runs if r.get('last_value') is not None]
    if printed:
        trace.append(f'Printed values: {printed}')

    return {'trace': trace, 'node_runs': node_runs}
