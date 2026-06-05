import unittest

import ryvencore as rc
from ryvencore.web_backend import AddNode, NumberNode, PrintNode, example_node_schemas, run_project


class WebBackend(unittest.TestCase):
    def test_example_node_schemas(self):
        schemas = example_node_schemas()
        identifiers = {schema['identifier'] for schema in schemas}

        self.assertIn(NumberNode.identifier, identifiers)
        self.assertIn(AddNode.identifier, identifiers)
        self.assertIn(PrintNode.identifier, identifiers)

    def test_run_project_uses_python_nodes(self):
        session = rc.Session()
        session.register_node_types([NumberNode, AddNode, PrintNode])
        flow = session.create_flow('main')

        number_a = flow.create_node(NumberNode)
        number_a.value = 2
        number_b = flow.create_node(NumberNode)
        number_b.value = 3
        add = flow.create_node(AddNode)
        printer = flow.create_node(PrintNode)

        flow.connect_nodes(number_a.outputs[0], add.inputs[0])
        flow.connect_nodes(number_b.outputs[0], add.inputs[1])
        flow.connect_nodes(add.outputs[0], printer.inputs[0])

        result = run_project(session.serialize())

        add_result = next(node for node in result['node_runs'] if node['identifier'] == AddNode.identifier)
        print_result = next(node for node in result['node_runs'] if node['identifier'] == PrintNode.identifier)

        self.assertEqual(add_result['outputs'][0]['value'], 5.0)
        self.assertEqual(print_result['last_value'], '5.0')


if __name__ == '__main__':
    unittest.main()
