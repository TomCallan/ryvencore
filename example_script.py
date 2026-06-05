# Example Script for ryvencore Studio Python Script node
class Inputs:
    multiplier = 2.0
    value = 5.0

class Outputs:
    result = 0.0

# Compute output easily
Outputs.result = Inputs.value * Inputs.multiplier
