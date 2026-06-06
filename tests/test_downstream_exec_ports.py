import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ryvencore as rc
import run_web_server as ws
from basic_nodes import TriggerNode, BranchNode, CounterNode

def test_downstream_exec_ports():
    session = rc.Session()
    session.register_node_types(ws.NODE_CLASSES)
    flow = session.create_flow('test_flow')
    flow.set_algorithm_mode('exec')
    
    # TriggerNode -> BranchNode -> CounterNode
    n_trig = flow.create_node(TriggerNode)
    n_branch = flow.create_node(BranchNode)
    n_counter = flow.create_node(CounterNode)
    
    # Connections
    flow.connect_nodes(n_trig.outputs[0], n_branch.inputs[0]) # exec line
    flow.connect_nodes(n_branch.outputs[0], n_counter.inputs[0]) # exec line
    
    # Set condition to True so branch propagates
    n_branch.inputs[1].default = rc.Data(True)
    
    # Turn on auto_exec_downstream on n_trig
    n_trig.auto_exec_downstream = True
    
    # Monitor updates
    branch_updated = False
    counter_updated = False
    
    orig_branch_update = n_branch.update_event
    def mock_branch_update(inp=-1):
        nonlocal branch_updated
        branch_updated = True
        orig_branch_update(inp)
    n_branch.update_event = mock_branch_update
    
    orig_counter_update = n_counter.update_event
    def mock_counter_update(inp=-1):
        nonlocal counter_updated
        counter_updated = True
        orig_counter_update(inp)
    n_counter.update_event = mock_counter_update
    
    # Trigger TriggerNode
    n_trig.update()
    
    # Assertions
    assert branch_updated, "BranchNode was not updated!"
    assert counter_updated, "CounterNode was not updated!"
    assert n_counter.count == 1, f"Counter count is {n_counter.count}, expected 1"
    print("SUCCESS: Downstream execution ports test passed!")

if __name__ == '__main__':
    test_downstream_exec_ports()
