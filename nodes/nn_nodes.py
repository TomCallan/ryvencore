import ryvencore as rc
from nodes.base import WebNode, add_server_log
import math
import random


class LinearLayerNode(WebNode):
    """
    Linear (fully-connected) layer: y = x @ W^T + b.

    Inputs:
        weights  : list[list[float]] of shape (out_features x in_features)
        bias     : list[float] of shape (out_features,)
        input_vec: list[float] of shape (in_features,)

    Outputs:
        output: list[float] of shape (out_features,)
        grad_weights: placeholder for backprop gradient
        grad_bias: placeholder for backprop gradient
        cached_input: input cached for backward pass
    """
    title = 'Linear Layer'
    init_inputs = [
        rc.NodeInputType(label='weights', default=rc.Data([[0.5, -0.2], [0.3, 0.8]])),
        rc.NodeInputType(label='bias', default=rc.Data([0.0, 0.0])),
        rc.NodeInputType(label='input_vec', default=rc.Data([1.0, 2.0])),
    ]
    init_outputs = [
        rc.NodeOutputType(label='output'),
        rc.NodeOutputType(label='grad_weights'),
        rc.NodeOutputType(label='grad_bias'),
        rc.NodeOutputType(label='cached_input'),
    ]

    def __init__(self, params):
        super().__init__(params)
        self._cached_input = None

    def update_event(self, inp=-1):
        weights = self.input(0).payload if self.input(0) else [[0.5]]
        bias = self.input(1).payload if self.input(1) else [0.0]
        x = self.input(2).payload if self.input(2) else [0.0]

        if not isinstance(x, list):
            x = [float(x)]
        if not isinstance(bias, list):
            bias = [float(bias)]

        in_features = len(x)
        out_features = len(bias)

        # Ensure weights is (out_features x in_features)
        result = [0.0] * out_features
        for i in range(out_features):
            w_row = weights[i] if i < len(weights) else [0.0] * in_features
            s = bias[i] if i < len(bias) else 0.0
            for j in range(min(len(w_row), in_features)):
                s += w_row[j] * (x[j] if j < len(x) else 0.0)
            result[i] = s

        self._cached_input = x
        self.set_output_val(0, rc.Data(result))
        self.set_output_val(1, rc.Data([]))
        self.set_output_val(2, rc.Data([]))
        self.set_output_val(3, rc.Data(x))


class ReLUNode(WebNode):
    """Element-wise ReLU activation."""
    title = 'ReLU'
    init_inputs = [rc.NodeInputType(label='input_vec', default=rc.Data([0.0]))]
    init_outputs = [
        rc.NodeOutputType(label='output'),
        rc.NodeOutputType(label='mask'),
    ]

    def update_event(self, inp=-1):
        x = self.input(0).payload if self.input(0) else [0.0]
        if not isinstance(x, list):
            x = [float(x)]

        out = [max(0.0, v) for v in x]
        mask = [1.0 if v > 0 else 0.0 for v in x]
        self.set_output_val(0, rc.Data(out))
        self.set_output_val(1, rc.Data(mask))


class SigmoidNode(WebNode):
    """Element-wise sigmoid activation."""
    title = 'Sigmoid'
    init_inputs = [rc.NodeInputType(label='input_vec', default=rc.Data([0.0]))]
    init_outputs = [rc.NodeOutputType(label='output')]

    def update_event(self, inp=-1):
        x = self.input(0).payload if self.input(0) else [0.0]
        if not isinstance(x, list):
            x = [float(x)]

        out = [1.0 / (1.0 + math.exp(-v)) for v in x]
        self.set_output_val(0, rc.Data(out))


class MSELossNode(WebNode):
    """
    Mean Squared Error loss.
    Inputs: predicted, target (both list[float])
    Outputs: loss (float), grad (list[float])
    """
    title = 'MSE Loss'
    init_inputs = [
        rc.NodeInputType(label='predicted', default=rc.Data([0.0])),
        rc.NodeInputType(label='target', default=rc.Data([0.0])),
    ]
    init_outputs = [
        rc.NodeOutputType(label='loss'),
        rc.NodeOutputType(label='grad'),
    ]

    def update_event(self, inp=-1):
        pred = self.input(0).payload if self.input(0) else [0.0]
        target = self.input(1).payload if self.input(1) else [0.0]

        if not isinstance(pred, list):
            pred = [float(pred)]
        if not isinstance(target, list):
            target = [float(target)]

        n = max(len(pred), len(target))
        if n == 0:
            n = 1

        loss = 0.0
        grad = [0.0] * n
        for i in range(n):
            p = pred[i] if i < len(pred) else 0.0
            t = target[i] if i < len(target) else 0.0
            diff = p - t
            loss += diff * diff
            grad[i] = 2.0 * diff / n

        loss /= n
        self.set_output_val(0, rc.Data(loss))
        self.set_output_val(1, rc.Data(grad))


class SGDOptimizerNode(WebNode):
    """
    Performs one SGD step: param = param - lr * grad.
    Updates weights and bias in-place (stores new values as outputs).

    Inputs:
        params    : list[list[float]] weights or list[float] bias
        grad      : list[list[float]] or list[float] gradient
        lr        : learning rate

    Outputs:
        updated_params: updated parameter tensor
    """
    title = 'SGD Optimizer'
    init_inputs = [
        rc.NodeInputType(label='params', default=rc.Data([[0.0]])),
        rc.NodeInputType(label='grad', default=rc.Data([[0.0]])),
        rc.NodeInputType(label='lr', default=rc.Data(0.01)),
        rc.NodeInputType(label='mask', default=rc.Data(None)),
    ]
    init_outputs = [rc.NodeOutputType(label='updated')]

    def update_event(self, inp=-1):
        params = self.input(0).payload if self.input(0) else [[0.0]]
        grad = self.input(1).payload if self.input(1) else [[0.0]]
        try:
            lr = float(self.input(2).payload) if self.input(2) else 0.01
        except (ValueError, TypeError):
            lr = 0.01
        mask = self.input(3).payload if self.input(3) else None

        if isinstance(params, list) and params and isinstance(params[0], list):
            # Matrix update
            updated = []
            for i in range(len(params)):
                row = []
                for j in range(len(params[i])):
                    g = 0.0
                    if isinstance(grad, list) and i < len(grad) and isinstance(grad[i], list) and j < len(grad[i]):
                        g = grad[i][j]
                    row.append(params[i][j] - lr * g)
                updated.append(row)
        elif isinstance(params, list):
            # Vector update (with optional mask)
            updated = []
            for i in range(len(params)):
                g = grad[i] if isinstance(grad, list) and i < len(grad) else 0.0
                m = mask[i] if isinstance(mask, list) and i < len(mask) else 1.0
                updated.append(params[i] - lr * g * m)
        else:
            updated = params - lr * grad

        self.set_output_val(0, rc.Data(updated))


class NNInferenceNode(WebNode):
    """
    Run a complete NN inference (forward pass).
    Takes input data and a pretrained weights blob, runs through
    a configurable network and outputs predictions.

    Inputs:
        input_data  : list[float] input features
        weights_1   : list[list[float]] W1
        bias_1      : list[float] b1
        weights_2   : list[list[float]] W2
        bias_2      : list[float] b2
        activation  : str 'relu' or 'sigmoid'

    Outputs:
        prediction  : list[float] output
        hidden      : list[float] hidden layer activations
    """
    title = 'NN Inference'
    init_inputs = [
        rc.NodeInputType(label='input_data', default=rc.Data([0.0, 0.0])),
        rc.NodeInputType(label='weights_1', default=rc.Data([[0.5, -0.2], [0.3, 0.8], [0.1, -0.5]])),
        rc.NodeInputType(label='bias_1', default=rc.Data([0.0, 0.0, 0.0])),
        rc.NodeInputType(label='weights_2', default=rc.Data([[0.4, -0.3, 0.2]])),
        rc.NodeInputType(label='bias_2', default=rc.Data([0.0])),
        rc.NodeInputType(label='activation', default=rc.Data('relu')),
    ]
    init_outputs = [
        rc.NodeOutputType(label='prediction'),
        rc.NodeOutputType(label='hidden'),
    ]

    def update_event(self, inp=-1):
        x = self.input(0).payload if self.input(0) else [0.0]
        w1 = self.input(1).payload if self.input(1) else [[0.5]]
        b1 = self.input(2).payload if self.input(2) else [0.0]
        w2 = self.input(3).payload if self.input(3) else [[0.5]]
        b2 = self.input(4).payload if self.input(4) else [0.0]
        act = str(self.input(5).payload).lower() if self.input(5) else 'relu'

        if not isinstance(x, list):
            x = [float(x)]

        # Layer 1: hidden = act(x @ W1^T + b1)
        hidden = []
        for i in range(len(b1)):
            s = b1[i] if i < len(b1) else 0.0
            w_row = w1[i] if i < len(w1) else [0.0] * len(x)
            for j in range(min(len(w_row), len(x))):
                s += w_row[j] * x[j]
            hidden.append(s)

        if act == 'relu':
            hidden = [max(0.0, v) for v in hidden]
        elif act == 'sigmoid':
            hidden = [1.0 / (1.0 + math.exp(-v)) for v in hidden]

        # Layer 2: output = hidden @ W2^T + b2
        output = []
        for i in range(len(b2)):
            s = b2[i] if i < len(b2) else 0.0
            w_row = w2[i] if i < len(w2) else [0.0] * len(hidden)
            for j in range(min(len(w_row), len(hidden))):
                s += w_row[j] * hidden[j]
            output.append(s)

        self.set_output_val(0, rc.Data(output))
        self.set_output_val(1, rc.Data(hidden))


class NNTrainerNode(WebNode):
    """
    Simple 2-layer neural network trainer with configurable architecture.
    Runs a single training iteration (forward + backward + update).

    Internally stores weights/biases as state. Each update_event runs one
    training step on the current input/target pair.

    Inputs:
        input_data  : list[float]
        target      : list[float]
        lr          : float learning rate
        activation  : 'relu' or 'sigmoid'

    Outputs:
        prediction  : current prediction
        loss        : current loss value
        weights_1   : updated W1
        weights_2   : updated W2
        bias_1      : updated b1
        bias_2      : updated b2
    """
    title = 'NN Trainer'
    init_inputs = [
        rc.NodeInputType(label='input_data', default=rc.Data([0.0, 0.0])),
        rc.NodeInputType(label='target', default=rc.Data([0.0])),
        rc.NodeInputType(label='lr', default=rc.Data(0.01)),
        rc.NodeInputType(label='activation', default=rc.Data('relu')),
    ]
    init_outputs = [
        rc.NodeOutputType(label='prediction'),
        rc.NodeOutputType(label='loss'),
        rc.NodeOutputType(label='weights_1'),
        rc.NodeOutputType(label='weights_2'),
        rc.NodeOutputType(label='bias_1'),
        rc.NodeOutputType(label='bias_2'),
    ]

    def __init__(self, params):
        super().__init__(params)
        self.hidden_size = 8
        self.input_size = 2
        self.output_size = 1
        self._init_weights()

    def _init_weights(self):
        r = random.Random(42)
        self._w1 = [[r.uniform(-0.5, 0.5) for _ in range(self.input_size)]
                    for _ in range(self.hidden_size)]
        self._b1 = [0.0] * self.hidden_size
        self._w2 = [[r.uniform(-0.5, 0.5) for _ in range(self.hidden_size)]
                    for _ in range(self.output_size)]
        self._b2 = [0.0] * self.output_size

    def additional_data(self):
        d = super().additional_data()
        d['hidden_size'] = self.hidden_size
        d['input_size'] = self.input_size
        d['output_size'] = self.output_size
        d['w1'] = self._w1
        d['b1'] = self._b1
        d['w2'] = self._w2
        d['b2'] = self._b2
        return d

    def load_additional_data(self, data):
        super().load_additional_data(data)
        self.hidden_size = data.get('hidden_size', 8)
        self.input_size = data.get('input_size', 2)
        self.output_size = data.get('output_size', 1)
        self._w1 = data.get('w1')
        self._b1 = data.get('b1')
        self._w2 = data.get('w2')
        self._b2 = data.get('b2')
        if self._w1 is None:
            self._init_weights()

    def update_event(self, inp=-1):
        x = self.input(0).payload if self.input(0) else [0.0, 0.0]
        target = self.input(1).payload if self.input(1) else [0.0]
        try:
            lr = float(self.input(2).payload) if self.input(2) else 0.01
        except (ValueError, TypeError):
            lr = 0.01
        act = str(self.input(3).payload).lower() if self.input(3) else 'relu'

        if not isinstance(x, list):
            x = [float(x)]
        if not isinstance(target, list):
            target = [float(target)]

        # ---- Forward pass ----
        # Layer 1: z1 = x @ W1^T + b1,  a1 = act(z1)
        z1 = []
        for i in range(self.hidden_size):
            s = self._b1[i]
            w_row = self._w1[i]
            for j in range(min(len(w_row), len(x))):
                s += w_row[j] * x[j]
            z1.append(s)

        if act == 'relu':
            a1 = [max(0.0, v) for v in z1]
            d_act = [1.0 if v > 0 else 0.0 for v in z1]
        else:
            a1 = [1.0 / (1.0 + math.exp(-v)) for v in z1]
            d_act = [a1[i] * (1.0 - a1[i]) for i in range(len(a1))]

        # Layer 2: z2 = a1 @ W2^T + b2,  pred = z2 (identity output)
        z2 = []
        for i in range(self.output_size):
            s = self._b2[i]
            w_row = self._w2[i]
            for j in range(min(len(w_row), len(a1))):
                s += w_row[j] * a1[j]
            z2.append(s)
        pred = z2

        # ---- Loss ----
        n_out = max(len(pred), len(target))
        loss = 0.0
        d_loss = [0.0] * n_out
        for i in range(n_out):
            p = pred[i] if i < len(pred) else 0.0
            t = target[i] if i < len(target) else 0.0
            diff = p - t
            loss += diff * diff
            d_loss[i] = 2.0 * diff / n_out
        loss /= n_out

        # ---- Backward pass (simple SGD) ----
        # dL/dW2 = outer(d_loss, a1)
        # dL/db2 = d_loss
        # dL/da1 = d_loss @ W2   (element-wise * d_act)
        # dL/dW1 = outer(dL/da1, x)
        # dL/db1 = dL/da1

        # W2 gradient
        for i in range(self.output_size):
            for j in range(self.hidden_size):
                if i < len(d_loss):
                    self._w2[i][j] -= lr * d_loss[i] * a1[j]

        # b2 gradient
        for i in range(min(self.output_size, len(d_loss))):
            self._b2[i] -= lr * d_loss[i]

        # Backprop to hidden
        d_a1 = [0.0] * self.hidden_size
        for j in range(self.hidden_size):
            for i in range(min(self.output_size, len(d_loss))):
                d_a1[j] += d_loss[i] * self._w2[i][j]
            d_a1[j] *= d_act[j]

        # W1 gradient
        for i in range(self.hidden_size):
            for j in range(min(len(self._w1[i]), len(x))):
                self._w1[i][j] -= lr * d_a1[i] * x[j]

        # b1 gradient
        for i in range(self.hidden_size):
            self._b1[i] -= lr * d_a1[i]

        # ---- Output ----
        self.set_output_val(0, rc.Data(pred))
        self.set_output_val(1, rc.Data(loss))
        self.set_output_val(2, rc.Data(self._w1))
        self.set_output_val(3, rc.Data(self._w2))
        self.set_output_val(4, rc.Data(self._b1))
        self.set_output_val(5, rc.Data(self._b2))


class NNDataGeneratorNode(WebNode):
    """
    Generates synthetic training data for a simple regression problem.
    y = 2*x0 + 3*x1 + noise

    Inputs:
        seed   : random seed
        noise  : noise scale

    Outputs:
        x_batch: list of [x0, x1] pairs
        y_batch: list of target values
    """
    title = 'NN Data Generator'
    init_inputs = [
        rc.NodeInputType(label='seed', default=rc.Data(42)),
        rc.NodeInputType(label='noise', default=rc.Data(0.1)),
        rc.NodeInputType(label='batch_size', default=rc.Data(100)),
    ]
    init_outputs = [
        rc.NodeOutputType(label='x_batch'),
        rc.NodeOutputType(label='y_batch'),
    ]

    def __init__(self, params):
        super().__init__(params)
        self._rng = random.Random(42)

    def update_event(self, inp=-1):
        try:
            seed = int(self.input(0).payload) if self.input(0) else 42
        except (ValueError, TypeError):
            seed = 42
        try:
            noise = float(self.input(1).payload) if self.input(1) else 0.1
        except (ValueError, TypeError):
            noise = 0.1
        try:
            batch_size = int(self.input(2).payload) if self.input(2) else 100
        except (ValueError, TypeError):
            batch_size = 100

        self._rng = random.Random(seed)
        xs = []
        ys = []
        for _ in range(batch_size):
            x0 = self._rng.uniform(-1, 1)
            x1 = self._rng.uniform(-1, 1)
            y = 2.0 * x0 + 3.0 * x1 + self._rng.gauss(0, noise)
            xs.append([x0, x1])
            ys.append([y])

        self.set_output_val(0, rc.Data(xs))
        self.set_output_val(1, rc.Data(ys))
