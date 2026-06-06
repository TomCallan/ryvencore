import subprocess

class Inputs:
    command = "echo Hello from ryvencore compiled workflow!"
    trigger_val = 0

class Outputs:
    output = ""

try:
    res = subprocess.check_output(Inputs.command, shell=True).decode().strip()
    Outputs.output = f"{res} (Tick: {Inputs.trigger_val})"
except Exception as e:
    Outputs.output = f"Error: {e}"
