import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ryvencore as rc
import scripts.run_web_server as ws

def test_force_trigger_data_flow():
    session = rc.Session()
    session.register_node_types(ws.NODE_CLASSES)
    flow = session.create_flow('test_flow')
    flow.set_algorithm_mode('data')

    # Setup: NumberNode -> AddNode -> LogNode
    n_num = flow.create_node(ws.NumberNode)
    n_add = flow.create_node(ws.AddNode)
    n_log = flow.create_node(ws.LogNode)

    # Enable force_trigger on AddNode
    n_add.force_trigger = True

    flow.connect_nodes(n_num.outputs[0], n_add.inputs[0])
    flow.connect_nodes(n_add.outputs[0], n_log.inputs[0])

    # Monitor updates
    log_updated = False
    orig_log_update = n_log.update_event
    def mock_log_update(inp=-1):
        nonlocal log_updated
        log_updated = True
        orig_log_update(inp)
    n_log.update_event = mock_log_update

    # Set input default (mimics user editing the input box)
    n_num.inputs[0].default = rc.Data(12.5)

    # Trigger update on input index 0 (data input)
    n_num.update(0)

    # Since n_add has force_trigger = True, it should not propagate its output to n_log
    assert n_num.outputs[0].val.payload == 12.5, "NumberNode output was not updated!"
    assert n_add.outputs[0].val.payload == 12.5, "AddNode output was not updated!"
    assert not log_updated, "LogNode should NOT be updated because of Force Trigger!"

    # Now, trigger manually (force propagation)
    flow.executor.force_propagation = True
    try:
        n_add.update()
    finally:
        flow.executor.force_propagation = False

    # Now it should have propagated!
    assert log_updated, "LogNode should have updated after force trigger manual propagation!"
    print("SUCCESS: Force trigger mode works correctly in Data Flow mode!")

if __name__ == '__main__':
    test_force_trigger_data_flow()
