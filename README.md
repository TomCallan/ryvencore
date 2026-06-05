
<p align="center">
  <img src="./docs/img/logo.png" alt="drawing" width="70%"/>
</p>

An experimental Python library for graph-based processing, designed for flow-based/node-based visual scripting editors. It is the backbone of the [Ryven](https://github.com/leon-thomm/Ryven) project, but it can very much be used in other contexts as well.

While ryvencore is written purely in Python, it is very lightweight and highly compatible. It can be compiled with Cython, see the `setup_cython.py` file. The performance seems comparable so far, but the code hasn't been optimized for Cython yet, so there might be a lot of potential. Please consider contributing. ryvencore also seems compatible with most Python ports to WebAssembly, even the Cython compiled ryvencore.

### Installation

```
pip install ryvencore
```

or from sources:
```
git clone https://github.com/leon-thomm/ryvencore
cd ryvencore
pip install .
```

### Usage

As an experimental library, the API is not fully stable and small breaking changes over time should be expected. Generally, the API is defined by what is included in the [docs](https://leon-thomm.github.io/ryvencore/).

### Web frontend (HTML5 + jQuery + Python backend)

A lightweight browser-based frontend is available in `web/`.

Features:
- dynamic rendering and editing of serialized ryvencore nodes and connections
- support for multiple flows in one project
- pan, zoom, and node dragging
- add node, delete node, create connections, and export edited JSON
- backend-powered flow execution using real Python ryvencore nodes
- material-inspired UI styling with pure HTML/CSS/JS and jQuery

Run it locally:
1. `cd ryvencore`
2. `python web/backend.py`
3. Open `http://localhost:8000/` in your browser and load a project JSON file

The backend currently ships with a few example Python node types:
- `NumberNode` (constant numeric value)
- `AddNode` (sum of two inputs)
- `MultiplyNode` (multiply two inputs)
- `PrintNode` (prints incoming value and records it in run output)

### Creating more backend node types

1. Subclass `ryvencore.Node` and define `init_inputs` / `init_outputs`.
2. Implement `update_event()` with your Python logic.
3. If the node has persistent config/state, implement `get_state()` and `set_state()`.
4. Register the node class in `EXAMPLE_NODE_TYPES` in `ryvencore/web_backend.py`.
5. Restart `python web/backend.py`; the web editor will load the new node type from `/api/node-types`.

### Examples

**loading a project** e.g. exported from Ryven

```python
import ryvencore as rc
import json
import sys

if __name__ == '__main__':
    # project file path
    fpath = sys.args[1]

    # read project file
    with open(fpath, 'r') as f:
        project: dict = json.loads(f.read())

    # run ryvencore
    session = rc.Session()
    session.load(project)

    # access the first flow
    f = session.flows[0]
    
    # and the last node that was created
    my_node = f.nodes[-1]

    # and execute it
    my_node.update()
```

### Features

The main features include

- **load & save** from and into JSON
- **a simple and powerful nodes system** which lets you do anything, simple and unrestricted
- **data *and* exec flow support** - unlike lots of other solutions out there, ryvencore supports exec flows
- **variables system** with subscribe and update mechanism to build nodes that automatically adapt to change of data
- **built-in logging** based on python's `logging` module
- **actions system for nodes** (WIP)

### Licensing

ryvencore is licensed under the [LGPL License](github.com/leon-thomm/ryvencore/blob/master/LICENSE).
