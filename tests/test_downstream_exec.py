import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ryvencore as rc
import scripts.run_web_server as ws

def test_downstream_exec():
    # Instantiate session & flow
    session = rc.Session()
    session.register_node_types(ws.NODE_CLASSES)
    flow = session.create_flow('test_flow')
    flow.set_algorithm_mode('exec')
    
    # Setup node structure:
    # UpstreamNode (Number) -> MiddleNode (Add) -> DownstreamNode (Log)
    # Plus a secondary input to MiddleNode (Number)
    
    n_up = flow.create_node(ws.NumberNode)
    n_up.inputs[0].default = rc.Data(10.0)
    
    n_side = flow.create_node(ws.NumberNode)
    n_side.inputs[0].default = rc.Data(5.0)
    
    n_mid = flow.create_node(ws.AddNode)
    n_down = flow.create_node(ws.LogNode)
    
    # Connections
    flow.connect_nodes(n_up.outputs[0], n_mid.inputs[0])
    flow.connect_nodes(n_side.outputs[0], n_mid.inputs[1])
    flow.connect_nodes(n_mid.outputs[0], n_down.inputs[0])
    
    # Initialize values
    n_up.update()
    n_side.update()
    
    # Let's count updates
    up_update_count = 0
    side_update_count = 0
    mid_update_count = 0
    down_update_count = 0
    
    # Mock update_event to count updates
    orig_up_update_event = n_up.update_event
    def mock_up_update(inp=-1):
        nonlocal up_update_count
        up_update_count += 1
        orig_up_update_event(inp)
    n_up.update_event = mock_up_update
    
    orig_side_update_event = n_side.update_event
    def mock_side_update(inp=-1):
        nonlocal side_update_count
        side_update_count += 1
        orig_side_update_event(inp)
    n_side.update_event = mock_side_update

    orig_mid_update_event = n_mid.update_event
    def mock_mid_update(inp=-1):
        nonlocal mid_update_count
        mid_update_count += 1
        orig_mid_update_event(inp)
    n_mid.update_event = mock_mid_update

    orig_down_update_event = n_down.update_event
    def mock_down_update(inp=-1):
        nonlocal down_update_count
        down_update_count += 1
        orig_down_update_event(inp)
    n_down.update_event = mock_down_update

    print("--- Initial update test ---")
    # Now set auto_exec_downstream on n_mid
    n_mid.auto_exec_downstream = True
    
    # Trigger an update on n_mid
    print("Updating middle node...")
    n_mid.update()
    
    # Assertions:
    # 1. Downstream node (n_down) should be updated
    # 2. Upstream nodes (n_up, n_side) should NOT be updated
    print(f"n_up updates: {up_update_count}")
    print(f"n_side updates: {side_update_count}")
    print(f"n_mid updates: {mid_update_count}")
    print(f"n_down updates: {down_update_count}")
    
    assert up_update_count == 0, "Upstream node was updated!"
    assert side_update_count == 0, "Side upstream node was updated!"
    assert mid_update_count == 1, "Middle node was not updated!"
    assert down_update_count == 1, "Downstream node was not updated!"
    print("SUCCESS: Downstream executed, upstream not executed!")

if __name__ == '__main__':
    test_downstream_exec()
