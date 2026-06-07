"""
Real-Time Monitor — simulated sensor data with moving average and threshold alerting.
  Random sensor → Moving Average (SMA-10) → Compare threshold → Chart (raw + smoothed)

Shows: streaming data, smoothing filters, conditional alerting, live charting.
"""
import os, sys, json
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir); sys.path.append(os.path.join(current_dir, 'nodes'))

import ryvencore as rc
from basic_nodes import RandomNode, CompareNode, IfElseNode, LogNode
from analysis_nodes import MovingAverageNode, ChartNode

def main():
    session = rc.Session()
    session.register_node_types([RandomNode, MovingAverageNode, CompareNode, IfElseNode, ChartNode, LogNode])
    flow = session.create_flow('realtime_flow')

    sensor = flow.create_node(RandomNode); sensor.x, sensor.y = 50, 200
    sensor.inputs[0].default = rc.Data(20.0)
    sensor.inputs[1].default = rc.Data(80.0)

    ma = flow.create_node(MovingAverageNode); ma.x, ma.y = 250, 200
    ma.inputs[1].default = rc.Data(10)

    cmp = flow.create_node(CompareNode); cmp.x, cmp.y = 500, 200
    cmp.inputs[1].default = rc.Data('>')
    cmp.inputs[2].default = rc.Data(60.0)

    alarm = flow.create_node(IfElseNode); alarm.x, alarm.y = 700, 60
    alarm.inputs[1].default = rc.Data('ALERT: Above threshold!')
    alarm.inputs[2].default = rc.Data('Normal')

    chart = flow.create_node(ChartNode); chart.x, chart.y = 500, 420
    chart.inputs[4].default = rc.Data('Sensor Monitor')
    chart.inputs[5].default = rc.Data('line')

    log_a = flow.create_node(LogNode); log_a.x, log_a.y = 950, 60
    log_ch = flow.create_node(LogNode); log_ch.x, log_ch.y = 800, 420

    # Raw -> Moving Average
    flow.connect_nodes(sensor.outputs[0], ma.inputs[0])
    # MA -> Compare (for alert)
    flow.connect_nodes(ma.outputs[0], cmp.inputs[0])
    # Compare -> If/Else alarm
    flow.connect_nodes(cmp.outputs[0], alarm.inputs[0])
    # Alarm -> Log
    flow.connect_nodes(alarm.outputs[0], log_a.inputs[0])
    # Raw + smoothed -> Chart
    flow.connect_nodes(sensor.outputs[0], chart.inputs[0])
    flow.connect_nodes(ma.outputs[0], chart.inputs[1])

    sensor.loop_enabled = True; sensor.loop_interval = 0.3; sensor.wait_until_complete = True

    saved = os.path.join(current_dir, 'saved_flows', 'realtime_flow.json')
    with open(saved, 'w') as f: json.dump(session.serialize(), f, indent=4)
    print(f"Generated realtime monitor flow: {saved}")

if __name__ == '__main__': main()
