"""
Chart Gallery — demonstrates multiple chart types with the Chart node.
  Three synthetic data series → Chart node rendering line, bar, area overlays.

Shows: multi-series charts, switching chart types, data visualization.
"""
import os, sys, json
import random
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir); sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from basic_nodes import TriggerNode, LogNode
from analysis_nodes import ChartNode, StatsNode

def main():
    session = rc.Session()
    session.register_node_types([TriggerNode, ChartNode, StatsNode, LogNode])
    flow = session.create_flow('chart_flow')

    chart = flow.create_node(ChartNode); chart.x, chart.y = 100, 200
    stats = flow.create_node(StatsNode); stats.x, stats.y = 100, 420
    log_ch = flow.create_node(LogNode); log_ch.x, log_ch.y = 500, 200

    rng = random.Random(42)
    sine = [round(10 + 8 * (i / 20 * 3.14159), 2) for i in range(30)]
    trend = [round(10 + i * 0.5 + rng.uniform(-1, 1), 2) for i in range(30)]
    noise = [round(20 + rng.gauss(0, 3), 2) for _ in range(30)]

    chart.inputs[0].default = rc.Data(sine)
    chart.inputs[1].default = rc.Data(trend)
    chart.inputs[2].default = rc.Data(noise)
    chart.inputs[4].default = rc.Data('Chart Gallery')
    chart.inputs[5].default = rc.Data('line')

    stats.inputs[0].default = rc.Data(noise)

    flow.connect_nodes(chart.outputs[0], log_ch.inputs[0])

    saved = os.path.join(current_dir, 'saved_flows', 'chart_flow.json')
    with open(saved, 'w') as f: json.dump(session.serialize(), f, indent=4)
    print(f"Generated chart gallery flow: {saved}")

if __name__ == '__main__': main()
