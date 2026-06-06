import threading
import time
import ryvencore as rc

class SlowNode(rc.Node):
    title = 'slow node'
    init_inputs = [rc.NodeInputType(type_='data', default=rc.Data(0))]
    init_outputs = [rc.NodeOutputType(type_='data')]

    def update_event(self, inp=-1):
        val = self.input(0).payload if self.input(0) else 0
        # simulate some lightweight processing
        time.sleep(0.05)
        self.set_output_val(0, rc.Data(val * 2))

class CollectorNode(rc.Node):
    title = 'collector'
    init_inputs = [
        rc.NodeInputType(type_='data', default=rc.Data(0)),
        rc.NodeInputType(type_='data', default=rc.Data(0))
    ]
    init_outputs = [rc.NodeOutputType(type_='data')]

    def update_event(self, inp=-1):
        a = self.input(0).payload if self.input(0) else 0
        b = self.input(1).payload if self.input(1) else 0
        self.set_output_val(0, rc.Data(a + b))

def test_concurrent_execution():
    session = rc.Session()
    session.register_node_types([SlowNode, CollectorNode])
    flow = session.create_flow('concurrent_flow')
    flow.set_algorithm_mode('data opt')

    # We will build two independent graph paths (Path A and Path B)
    # sharing the SAME flow (and therefore the SAME FlowExecutor instance)

    # Path A
    n_root_a = flow.create_node(SlowNode)
    n_left_a = flow.create_node(SlowNode)
    n_right_a = flow.create_node(SlowNode)
    n_collector_a = flow.create_node(CollectorNode)

    flow.connect_nodes(n_root_a.outputs[0], n_left_a.inputs[0])
    flow.connect_nodes(n_root_a.outputs[0], n_right_a.inputs[0])
    flow.connect_nodes(n_left_a.outputs[0], n_collector_a.inputs[0])
    flow.connect_nodes(n_right_a.outputs[0], n_collector_a.inputs[1])

    # Path B
    n_root_b = flow.create_node(SlowNode)
    n_left_b = flow.create_node(SlowNode)
    n_right_b = flow.create_node(SlowNode)
    n_collector_b = flow.create_node(CollectorNode)

    flow.connect_nodes(n_root_b.outputs[0], n_left_b.inputs[0])
    flow.connect_nodes(n_root_b.outputs[0], n_right_b.inputs[0])
    flow.connect_nodes(n_left_b.outputs[0], n_collector_b.inputs[0])
    flow.connect_nodes(n_right_b.outputs[0], n_collector_b.inputs[1])

    errors = []

    def worker_a():
        try:
            n_root_a.inputs[0].default = rc.Data(5)
            n_root_a.update()
            expected = 5 * 8
            actual = n_collector_a.outputs[0].val.payload
            assert actual == expected, f"Path A expected {expected}, got {actual}"
        except Exception as e:
            errors.append(e)

    def worker_b():
        try:
            n_root_b.inputs[0].default = rc.Data(7)
            n_root_b.update()
            expected = 7 * 8
            actual = n_collector_b.outputs[0].val.payload
            assert actual == expected, f"Path B expected {expected}, got {actual}"
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=worker_a)
    t2 = threading.Thread(target=worker_b)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    assert not errors, f"Concurrent execution errors encountered: {errors}"
    print("SUCCESS: Concurrent execution with same executor but independent paths passed!")

if __name__ == '__main__':
    test_concurrent_execution()
