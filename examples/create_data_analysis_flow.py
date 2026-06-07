"""
Data Analysis — full analysis pipeline on a synthetic dataset.
  Stats on X → Stats on Y → Correlation (X vs Y) → Normalize (minmax) → Filter (outliers) → Chart

Shows: descriptive statistics, correlation analysis, normalization, outlier filtering, visualization.
"""
import os, sys, json
import random
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir); sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from basic_nodes import LogNode
from analysis_nodes import StatsNode, CorrelationNode, NormalizeNode, FilterNode, ChartNode

def main():
    session = rc.Session()
    session.register_node_types([StatsNode, CorrelationNode, NormalizeNode, FilterNode, ChartNode, LogNode])
    flow = session.create_flow('data_analysis_flow')

    rng = random.Random(99)
    x = [round(rng.gauss(50, 15), 2) for _ in range(50)]
    y = [round(2 * x[i] + rng.gauss(0, 10), 2) for i in range(50)]
    z = [round(-0.5 * x[i] + rng.gauss(0, 8), 2) for i in range(50)]

    stats_x = flow.create_node(StatsNode); stats_x.x, stats_x.y = 50, 80
    stats_x.title = 'Stats (X)'; stats_x.inputs[0].default = rc.Data(x)

    stats_y = flow.create_node(StatsNode); stats_y.x, stats_y.y = 50, 300
    stats_y.title = 'Stats (Y)'; stats_y.inputs[0].default = rc.Data(y)

    corr = flow.create_node(CorrelationNode); corr.x, corr.y = 300, 200
    corr.inputs[0].default = rc.Data(x); corr.inputs[1].default = rc.Data(y)

    norm = flow.create_node(NormalizeNode); norm.x, norm.y = 550, 80
    norm.inputs[0].default = rc.Data(x); norm.inputs[1].default = rc.Data('minmax')

    filt = flow.create_node(FilterNode); filt.x, filt.y = 550, 350
    filt.inputs[0].default = rc.Data(x)
    filt.inputs[1].default = rc.Data('outlier')
    filt.inputs[2].default = rc.Data(1.5)

    chart = flow.create_node(ChartNode); chart.x, chart.y = 850, 200
    chart.inputs[0].default = rc.Data(x); chart.inputs[1].default = rc.Data(y)
    chart.inputs[2].default = rc.Data(z)
    chart.inputs[4].default = rc.Data('Data Analysis')
    chart.inputs[5].default = rc.Data('line')

    log_sx = flow.create_node(LogNode); log_sx.x, log_sx.y = 50, 500
    log_sy = flow.create_node(LogNode); log_sy.x, log_sy.y = 50, 580
    log_c = flow.create_node(LogNode); log_c.x, log_c.y = 300, 500
    log_f = flow.create_node(LogNode); log_f.x, log_f.y = 550, 500
    log_ch = flow.create_node(LogNode); log_ch.x, log_ch.y = 850, 500

    flow.connect_nodes(stats_x.outputs[1], log_sx.inputs[0])  # mean of X
    flow.connect_nodes(stats_y.outputs[1], log_sy.inputs[0])  # mean of Y
    flow.connect_nodes(corr.outputs[0], log_c.inputs[0])      # correlation r
    flow.connect_nodes(filt.outputs[2], log_f.inputs[0])      # filter info
    flow.connect_nodes(chart.outputs[0], log_ch.inputs[0])    # SVG chart

    saved = os.path.join(current_dir, 'saved_flows', 'data_analysis_flow.json')
    with open(saved, 'w') as f: json.dump(session.serialize(), f, indent=4)
    print(f"Generated data analysis flow: {saved}")

if __name__ == '__main__': main()
