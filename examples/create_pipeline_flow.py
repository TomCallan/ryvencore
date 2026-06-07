"""
Data Pipeline — a clean data processing pipeline.
  Random number generator → Stats (mean/std/median) → Normalize (z-score) → Chart

Shows: data generation, descriptive statistics, normalization, and visualization.
"""
import os, sys, json
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir); sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from basic_nodes import RandomNode, LogNode
from analysis_nodes import StatsNode, NormalizeNode, ChartNode

def main():
    session = rc.Session()
    session.register_node_types([RandomNode, StatsNode, NormalizeNode, ChartNode, LogNode])
    flow = session.create_flow('pipeline_flow')

    rnd = flow.create_node(RandomNode); rnd.x, rnd.y = 50, 200
    stats = flow.create_node(StatsNode); stats.x, stats.y = 300, 200
    norm = flow.create_node(NormalizeNode); norm.x, norm.y = 550, 200
    chart = flow.create_node(ChartNode); chart.x, chart.y = 800, 200
    log_s = flow.create_node(LogNode); log_s.x, log_s.y = 300, 420
    log_ch = flow.create_node(LogNode); log_ch.x, log_ch.y = 800, 420

    rnd.inputs[0].default = rc.Data(0.0)
    rnd.inputs[1].default = rc.Data(50.0)
    norm.inputs[1].default = rc.Data('zscore')
    chart.inputs[4].default = rc.Data('Pipeline Data')
    chart.inputs[5].default = rc.Data('bar')

    # Data flow: Random → Stats → (log)   Random → Normalize → Chart
    flow.connect_nodes(rnd.outputs[0], stats.inputs[0])
    flow.connect_nodes(stats.outputs[1], log_s.inputs[0])  # mean → log
    flow.connect_nodes(rnd.outputs[0], norm.inputs[0])
    flow.connect_nodes(norm.outputs[0], chart.inputs[0])
    flow.connect_nodes(chart.outputs[0], log_ch.inputs[0])  # svg → log

    rnd.loop_enabled = True; rnd.loop_interval = 1.0; rnd.wait_until_complete = True

    saved = os.path.join(current_dir, 'saved_flows', 'pipeline_flow.json')
    with open(saved, 'w') as f: json.dump(session.serialize(), f, indent=4)
    print(f"Generated pipeline flow: {saved}")

if __name__ == '__main__': main()
