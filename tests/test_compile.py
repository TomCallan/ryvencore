import sys
import os
import subprocess
import tempfile

# Ensure project root is on path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ryvencore as rc
import scripts.run_web_server as ws

def test_flow_compilation():
    # Load basic nodes classes
    ws.load_nodes_from_folder()

    session = rc.Session()
    session.register_node_types(ws.NODE_CLASSES)
    flow = session.create_flow('compile_test_flow')
    
    # Trigger -> Counter -> Log
    TriggerNode = next(n for n in ws.NODE_CLASSES if n.__name__ == 'TriggerNode')
    CounterNode = next(n for n in ws.NODE_CLASSES if n.__name__ == 'CounterNode')
    LogNode = next(n for n in ws.NODE_CLASSES if n.__name__ == 'LogNode')
    
    n_trig = flow.create_node(TriggerNode)
    n_counter = flow.create_node(CounterNode)
    n_log = flow.create_node(LogNode)
    
    flow.connect_nodes(n_trig.outputs[0], n_counter.inputs[0])
    flow.connect_nodes(n_counter.outputs[1], n_log.inputs[0])
    
    # Compile the flow
    compiled_code = rc.FlowCompiler.compile(flow)
    
    assert compiled_code, "Compiled code is empty"
    assert "class TriggerNode" in compiled_code, "Compiled code missing TriggerNode class definition"
    assert "class CounterNode" in compiled_code, "Compiled code missing CounterNode class definition"
    assert "class LogNode" in compiled_code, "Compiled code missing LogNode class definition"
    
    # Save compilation result to a temp file and execute it to make sure it runs correctly
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(compiled_code)
        temp_filename = f.name
        
    try:
        # Run the compiled script as a standalone process
        # We set PYTHONPATH to include the current directory so imports in basic_nodes work
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        result = subprocess.run(
            [sys.executable, temp_filename],
            capture_output=True,
            text=True,
            env=env,
            timeout=5
        )
        
        print("Compiled run stdout:", result.stdout)
        print("Compiled run stderr:", result.stderr)
        
        assert result.returncode == 0, f"Compiled script failed with code {result.returncode}. Stderr: {result.stderr}"
        assert "Counter" in result.stdout or "Log" in result.stdout, "Expected output missing from execution stdout"
        print("SUCCESS: Standalone flow compilation and execution test passed!")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

def test_structure_hash_and_dirty_tracking():
    ws.load_nodes_from_folder()
    session = rc.Session()
    session.register_node_types(ws.NODE_CLASSES)
    flow = session.create_flow('hash_test_flow')
    
    TriggerNode = next(n for n in ws.NODE_CLASSES if n.__name__ == 'TriggerNode')
    CounterNode = next(n for n in ws.NODE_CLASSES if n.__name__ == 'CounterNode')
    
    hash1 = rc.FlowCompiler.get_structure_hash(flow)
    
    n_trig = flow.create_node(TriggerNode)
    hash2 = rc.FlowCompiler.get_structure_hash(flow)
    assert hash1 != hash2, "Adding a node did not change structure hash"
    
    n_counter = flow.create_node(CounterNode)
    hash3 = rc.FlowCompiler.get_structure_hash(flow)
    assert hash2 != hash3, "Adding another node did not change structure hash"
    
    flow.connect_nodes(n_trig.outputs[0], n_counter.inputs[0])
    hash4 = rc.FlowCompiler.get_structure_hash(flow)
    assert hash3 != hash4, "Connecting nodes did not change structure hash"
    
    # Save compilation to establish a clean compiled state
    status_before = ws.check_compiled_status(flow)
    
    # Run server-side compilation via ws (which writes file)
    compiled_code = rc.FlowCompiler.compile(flow)
    compiled_dir = os.path.abspath('compiled')
    os.makedirs(compiled_dir, exist_ok=True)
    filename = f"hash_test_flow_compiled.py"
    filepath = os.path.join(compiled_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(compiled_code)
        
    status_after = ws.check_compiled_status(flow)
    assert status_after['compiled_exists'] is True
    assert status_after['compiled_dirty'] is False
    
    # Modify flow (disconnect nodes) -> should become dirty
    flow.disconnect_nodes(n_trig.outputs[0], n_counter.inputs[0])
    status_after_mod = ws.check_compiled_status(flow)
    assert status_after_mod['compiled_exists'] is True
    assert status_after_mod['compiled_dirty'] is True
    
    # Cleanup compiled file
    if os.path.exists(filepath):
        os.remove(filepath)

def test_new_nodes_and_plotting():
    # Test plotting engine
    from plotting.engine import SVGPlotter
    line_svg = SVGPlotter.plot_line([10, 20, 15, 30], title="Line Test")
    assert "<svg" in line_svg and "</svg>" in line_svg
    assert "Line Test" in line_svg

    ob_svg = SVGPlotter.plot_orderbook([[99.0, 1.0]], [[101.0, 2.0]], title="OB Test")
    assert "<svg" in ob_svg and "</svg>" in ob_svg
    assert "OB Test" in ob_svg

    # Test nodes instantiation
    ws.load_nodes_from_folder()
    session = rc.Session()
    session.register_node_types(ws.NODE_CLASSES)
    flow = session.create_flow('new_nodes_test')

    ParquetReaderNode = next(n for n in ws.NODE_CLASSES if n.__name__ == 'ParquetReaderNode')
    DuckDBQueryNode = next(n for n in ws.NODE_CLASSES if n.__name__ == 'DuckDBQueryNode')
    AdvancedPlotNode = next(n for n in ws.NODE_CLASSES if n.__name__ == 'AdvancedPlotNode')
    OrderbookPlotNode = next(n for n in ws.NODE_CLASSES if n.__name__ == 'OrderbookPlotNode')

    n_pq = flow.create_node(ParquetReaderNode)
    n_db = flow.create_node(DuckDBQueryNode)
    n_ap = flow.create_node(AdvancedPlotNode)
    n_op = flow.create_node(OrderbookPlotNode)

    assert n_pq.title == 'Parquet Reader'
    assert n_db.title == 'DuckDB Query'
    assert n_ap.title == 'Advanced Plot'
    assert n_op.title == 'Orderbook Plot'

if __name__ == '__main__':
    test_flow_compilation()
    test_structure_hash_and_dirty_tracking()
    test_new_nodes_and_plotting()
