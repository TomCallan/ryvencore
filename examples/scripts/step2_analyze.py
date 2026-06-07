class Inputs:
    input_data = 0.0
    factor = 1.5

class Outputs:
    scaled_data = 0.0
    is_high = False

# Multiply data by factor and check if it exceeds a threshold
val = float(Inputs.input_data) * float(Inputs.factor)
Outputs.scaled_data = val
Outputs.is_high = val > 50.0
