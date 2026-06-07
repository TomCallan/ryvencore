class Inputs:
    trigger_val = 0.0

class Outputs:
    raw_data = 0.0

# Generate a raw data point based on trigger count
Outputs.raw_data = float(Inputs.trigger_val) * 10.0 + 5.5
