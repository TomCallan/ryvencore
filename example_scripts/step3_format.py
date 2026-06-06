class Inputs:
    data_val = 0.0
    flag = False

class Outputs:
    formatted_msg = ""

# Format a nice output message
status = "HIGH" if Inputs.flag else "NORMAL"
Outputs.formatted_msg = f"Status: {status} | Processed Value: {Inputs.data_val:.2f}"
