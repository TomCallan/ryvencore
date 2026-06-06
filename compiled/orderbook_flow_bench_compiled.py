# Structure Hash: b39db8d697168873d60e3dab9f518f72591f66cd8ca716217ca724c42fc45d3a
"""
Compiled ryvencore flow: orderbook_flow
Generated automatically by FlowCompiler.
"""
import sys
import time
import os
try:
    import numpy as np
except ImportError:
    pass
try:
    import pandas as pd
except ImportError:
    pass

# --- Compiled ryvencore Runtime Mock ---
class CompiledData:
    def __init__(self, value=None, load_from=None):
        self.payload = value

    def __str__(self):
        return f"<Data payload: {self.payload}>"

class CompiledNode:
    def __init__(self, node_id, flow_alg='data', actual_node=None):
        self.node_id = node_id
        self.global_id = node_id
        self.flow_alg = flow_alg
        self.actual_node = actual_node
        self.inputs = []
        self.outputs = []
        self.connections = {}  # output_idx -> [(target_node, input_idx)]

    def input(self, index):
        if index < len(self.inputs):
            return self.inputs[index].default
        return None

    def set_output_val(self, index, val):
        if not isinstance(val, CompiledData):
            val = CompiledData(val)
        
        # Update output port value
        if index < len(self.outputs):
            self.outputs[index].val = val

        # Update actual node's output val in ryvencore flow
        if self.actual_node and index < len(self.actual_node.outputs):
            self.actual_node.outputs[index].val = val

        # Propagate to connected nodes
        if index in self.connections:
            for target_node, target_input in self.connections[index]:
                if target_input < len(target_node.inputs):
                    target_node.inputs[target_input].default = val
                    if self.flow_alg in ('data', 'data opt', 'compiled'):
                        target_node.update(target_input)

    def exec_output(self, index):
        if index in self.connections:
            for target_node, target_input in self.connections[index]:
                target_node.update(target_input)

    def update(self, inp=-1):
        if getattr(self, 'wait_until_complete', False) and getattr(self, '_is_executing', False):
            return
        self._is_executing = True
        try:
            # Map Inputs/Outputs if class declarations exist (similar to WebNode logic)
            if hasattr(self.__class__, 'Inputs') and isinstance(self.__class__.Inputs, type):
                inputs_instance = self.__class__.Inputs()
                for idx, inp_port in enumerate(self.inputs):
                    label = inp_port.label_str
                    val_obj = self.input(idx)
                    setattr(inputs_instance, label, val_obj.payload if val_obj else None)
                self.Inputs = inputs_instance
                
            if hasattr(self.__class__, 'Outputs') and isinstance(self.__class__.Outputs, type):
                self.Outputs = self.__class__.Outputs()

            # Execute main node update
            self.update_event(inp)

            # Map Outputs class attributes back to ports
            if hasattr(self, 'Outputs') and not isinstance(self.Outputs, type):
                for idx, out_port in enumerate(self.outputs):
                    label = out_port.label_str
                    val = getattr(self.Outputs, label, None)
                    self.set_output_val(idx, val)
        finally:
            self._is_executing = False

    def update_event(self, inp=-1):
        pass

    def rebuilt(self):
        pass

    def after_placement(self):
        pass

    def prepare_removal(self):
        pass

class CompiledPort:
    def __init__(self, label_str='', type_='data', default=None):
        self.label_str = label_str
        self.type_ = type_
        self.default = default
        self.val = default

class CompiledNodeInput(CompiledPort):
    pass

class CompiledNodeOutput(CompiledPort):
    pass

class MockRyvencore:
    Node = CompiledNode
    Data = CompiledData
    
    @staticmethod
    def NodeInputType(label='', type_='data', default=None):
        return CompiledNodeInput(label, type_, default)

    @staticmethod
    def NodeOutputType(label='', type_='data'):
        return CompiledNodeOutput(label, type_)

# Register mock in sys.modules so imports of ryvencore inside node classes resolve to mock
sys.modules['ryvencore'] = MockRyvencore
import ryvencore as rc

# Mock WebNode parent class used in basic_nodes
class WebNode(CompiledNode):
    def __init__(self, params=None):
        super().__init__(node_id=-1)
        self.loop_enabled = False
        self.loop_interval = 1.0
        self._is_executing = False

    def create_input(self, label='', type_='data', default=None, load_from=None):
        port = CompiledNodeInput(label, type_, default)
        self.inputs.append(port)
        return port

    def create_output(self, label='', type_='data', load_from=None):
        port = CompiledNodeOutput(label, type_)
        self.outputs.append(port)
        return port

def add_server_log(msg):
    print(f"[Server Log] {msg}")


# --- Node Classes Definitions ---
class OrderbookGeneratorNode(WebNode):
    title = 'Orderbook Generator'
    init_inputs = [
        rc.NodeInputType(label='file_path', default=rc.Data('orderbook.parquet')),
        rc.NodeInputType(label='generate', type_='exec')
    ]
    init_outputs = [
        rc.NodeOutputType(label='file_path'),
        rc.NodeOutputType(label='finished', type_='exec')
    ]

    def update_event(self, inp=-1):
        if inp == 1: # generate trigger
            file_path = self.input(0).payload if self.input(0) else 'orderbook.parquet'
            if not os.path.exists(file_path):
                generate_orderbook_parquet(file_path)
            self.set_output_val(0, rc.Data(file_path))
            self.exec_output(1)


class TradingAlgoNode(WebNode):
    title = 'Trading Algo'
    init_inputs = [
        rc.NodeInputType(label='mid_prices'),
        rc.NodeInputType(label='spreads'),
        rc.NodeInputType(label='start_balance', default=rc.Data(10000.0)),
        rc.NodeInputType(label='run', type_='exec')
    ]
    init_outputs = [
        rc.NodeOutputType(label='final_balance'),
        rc.NodeOutputType(label='finished', type_='exec')
    ]

    def update_event(self, inp=-1):
        if inp == 3: # run trigger
            mids_data = self.input(0)
            spreads_data = self.input(1)
            start_bal_data = self.input(2)
            
            if mids_data and mids_data.payload is not None and spreads_data and spreads_data.payload is not None:
                mids = mids_data.payload
                spreads = spreads_data.payload
                balance = start_bal_data.payload if start_bal_data else 10000.0
                
                # Simple momentum strategy using numpy:
                # Buy when price increases, sell when price decreases
                diffs = np.diff(mids)
                signals = np.zeros_like(mids)
                signals[1:][diffs > 0.01] = 1   # Buy signal
                signals[1:][diffs < -0.01] = -1 # Sell signal
                
                position = 0.0
                entry_price = 0.0
                
                for i in range(len(mids)):
                    sig = signals[i]
                    price = mids[i]
                    spread = spreads[i]
                    
                    if sig == 1 and position == 0.0: # Buy
                        # pay spread
                        buy_price = price + spread / 2
                        position = balance / buy_price
                        balance = 0.0
                        entry_price = buy_price
                    elif sig == -1 and position > 0.0: # Sell
                        # pay spread
                        sell_price = price - spread / 2
                        balance = position * sell_price
                        position = 0.0
                        
                # Close remaining position at the end
                if position > 0.0:
                    balance = position * (mids[-1] - spreads[-1] / 2)
                    
                self.set_output_val(0, rc.Data(float(balance)))
                self.exec_output(1)


class BalanceLogNode(WebNode):
    title = 'Balance Log'
    init_inputs = [
        rc.NodeInputType(label='balance'),
        rc.NodeInputType(label='trigger', type_='exec')
    ]
    init_outputs = [
        rc.NodeOutputType(label='logged_balance')
    ]

    def update_event(self, inp=-1):
        if inp == 1:
            bal = self.input(0).payload if self.input(0) else 0.0
            print(f"[Balance Log] Account Balance: ${bal:.2f}")
            self.set_output_val(0, rc.Data(bal))


class OrderbookSnapshotNode(WebNode):
    title = 'Orderbook Snapshot'
    init_inputs = [
        rc.NodeInputType(label='data'),
        rc.NodeInputType(label='process', type_='exec')
    ]
    init_outputs = [
        rc.NodeOutputType(label='mid_prices'),
        rc.NodeOutputType(label='spreads'),
        rc.NodeOutputType(label='finished', type_='exec')
    ]

    def update_event(self, inp=-1):
        if inp == 1:
            df_data = self.input(0)
            if df_data and df_data.payload is not None:
                df = df_data.payload
                mid_prices = (df['bid_price'].values + df['ask_price'].values) / 2.0
                spreads = df['ask_price'].values - df['bid_price'].values
                self.set_output_val(0, rc.Data(mid_prices))
                self.set_output_val(1, rc.Data(spreads))
                self.exec_output(2)


class ParquetReaderNode(WebNode):
    title = 'Parquet Reader'
    init_inputs = [
        rc.NodeInputType(label='file_path', default=rc.Data('orderbook.parquet')),
        rc.NodeInputType(label='read', type_='exec')
    ]
    init_outputs = [
        rc.NodeOutputType(label='data'),
        rc.NodeOutputType(label='finished', type_='exec')
    ]

    def update_event(self, inp=-1):
        if inp == 1: # read trigger
            file_path = self.input(0).payload if self.input(0) else 'orderbook.parquet'
            if os.path.exists(file_path):
                df = pd.read_parquet(file_path)
                self.set_output_val(0, rc.Data(df))
                self.exec_output(1)


# --- Flow Execution Instantiation ---
def setup_flow(actual_nodes=None):
    nodes = {}
    flow_alg = 'data'

    # Node: Orderbook Generator (ID: 0)
    n_0 = OrderbookGeneratorNode(params=None)
    n_0.node_id = 0
    n_0.global_id = 0
    n_0.flow_alg = flow_alg
    if actual_nodes and 0 in actual_nodes:
        n_0.actual_node = actual_nodes[0]
    n_0.create_input('file_path', 'data', default=rc.Data('orderbook.parquet'))
    n_0.create_input('generate', 'exec', default=rc.Data(None))
    n_0.create_output('file_path', 'data')
    n_0.create_output('finished', 'exec')
    n_0.loop_enabled = False
    n_0.loop_interval = 1.0
    n_0.wait_until_complete = False
    n_0.auto_exec_downstream = False
    nodes[0] = n_0

    # Node: Parquet Reader (ID: 1)
    n_1 = ParquetReaderNode(params=None)
    n_1.node_id = 1
    n_1.global_id = 1
    n_1.flow_alg = flow_alg
    if actual_nodes and 1 in actual_nodes:
        n_1.actual_node = actual_nodes[1]
    n_1.create_input('file_path', 'data', default=rc.Data('orderbook.parquet'))
    n_1.create_input('read', 'exec', default=rc.Data(None))
    n_1.create_output('data', 'data')
    n_1.create_output('finished', 'exec')
    n_1.loop_enabled = False
    n_1.loop_interval = 1.0
    n_1.wait_until_complete = False
    n_1.auto_exec_downstream = False
    nodes[1] = n_1

    # Node: Orderbook Snapshot (ID: 2)
    n_2 = OrderbookSnapshotNode(params=None)
    n_2.node_id = 2
    n_2.global_id = 2
    n_2.flow_alg = flow_alg
    if actual_nodes and 2 in actual_nodes:
        n_2.actual_node = actual_nodes[2]
    n_2.create_input('data', 'data', default=rc.Data(None))
    n_2.create_input('process', 'exec', default=rc.Data(None))
    n_2.create_output('mid_prices', 'data')
    n_2.create_output('spreads', 'data')
    n_2.create_output('finished', 'exec')
    n_2.loop_enabled = False
    n_2.loop_interval = 1.0
    n_2.wait_until_complete = False
    n_2.auto_exec_downstream = False
    nodes[2] = n_2

    # Node: Trading Algo (ID: 3)
    n_3 = TradingAlgoNode(params=None)
    n_3.node_id = 3
    n_3.global_id = 3
    n_3.flow_alg = flow_alg
    if actual_nodes and 3 in actual_nodes:
        n_3.actual_node = actual_nodes[3]
    n_3.create_input('mid_prices', 'data', default=rc.Data(None))
    n_3.create_input('spreads', 'data', default=rc.Data(None))
    n_3.create_input('start_balance', 'data', default=rc.Data(10000.0))
    n_3.create_input('run', 'exec', default=rc.Data(None))
    n_3.create_output('final_balance', 'data')
    n_3.create_output('finished', 'exec')
    n_3.loop_enabled = False
    n_3.loop_interval = 1.0
    n_3.wait_until_complete = False
    n_3.auto_exec_downstream = False
    nodes[3] = n_3

    # Node: Balance Log (ID: 4)
    n_4 = BalanceLogNode(params=None)
    n_4.node_id = 4
    n_4.global_id = 4
    n_4.flow_alg = flow_alg
    if actual_nodes and 4 in actual_nodes:
        n_4.actual_node = actual_nodes[4]
    n_4.create_input('balance', 'data', default=rc.Data(None))
    n_4.create_input('trigger', 'exec', default=rc.Data(None))
    n_4.create_output('logged_balance', 'data')
    n_4.loop_enabled = False
    n_4.loop_interval = 1.0
    n_4.wait_until_complete = False
    n_4.auto_exec_downstream = False
    nodes[4] = n_4

    # Connections
    nodes[0].connections[0] = [(nodes[1], 0)]
    nodes[0].connections[1] = [(nodes[1], 1)]
    nodes[1].connections[0] = [(nodes[2], 0)]
    nodes[1].connections[1] = [(nodes[2], 1)]
    nodes[2].connections[0] = [(nodes[3], 0)]
    nodes[2].connections[1] = [(nodes[3], 1)]
    nodes[2].connections[2] = [(nodes[3], 3)]
    nodes[3].connections[0] = [(nodes[4], 0)]
    nodes[3].connections[1] = [(nodes[4], 1)]

    # Run initial placement events
    nodes[0].after_placement()
    nodes[1].after_placement()
    nodes[2].after_placement()
    nodes[3].after_placement()
    nodes[4].after_placement()

    return nodes


def main():
    print("Setting up compiled flow...")
    nodes = setup_flow()
    
    # Identify trigger nodes
    triggers = [n for n in nodes.values() if n.__class__.__name__ == 'TriggerNode']
    if not triggers:
        # Fallback: trigger first topological node
        print("No TriggerNode found. Running all nodes in topological order...")
        for n in sorted(nodes.values(), key=lambda x: x.node_id):
            n.update()
    else:
        print(f"Found {len(triggers)} TriggerNodes. Initiating flow execution...")
        for t in triggers:
            t.update()

if __name__ == '__main__':
    main()
