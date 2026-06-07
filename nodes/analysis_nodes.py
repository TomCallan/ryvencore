import ryvencore as rc
from nodes.base import WebNode, add_server_log


class StatsNode(WebNode):
    """
    Compute descriptive statistics on a list of numbers.
    Outputs: count, mean, min, max, range, std, variance, median, q1, q3, sum
    """
    title = 'Stats'
    init_inputs = [
        rc.NodeInputType(label='data', default=rc.Data([1.0, 2.0, 3.0, 4.0, 5.0])),
    ]
    init_outputs = [
        rc.NodeOutputType(label='count'),
        rc.NodeOutputType(label='mean'),
        rc.NodeOutputType(label='min'),
        rc.NodeOutputType(label='max'),
        rc.NodeOutputType(label='range'),
        rc.NodeOutputType(label='std'),
        rc.NodeOutputType(label='variance'),
        rc.NodeOutputType(label='median'),
        rc.NodeOutputType(label='q1'),
        rc.NodeOutputType(label='q3'),
        rc.NodeOutputType(label='sum'),
    ]

    def update_event(self, inp=-1):
        raw = self.input(0).payload if self.input(0) else []
        if not isinstance(raw, list):
            raw = [raw]
        vals = [self._to_float(v) for v in raw if v is not None]
        n = len(vals)
        if n == 0:
            for i in range(len(self.outputs)):
                self.set_output_val(i, rc.Data(0.0))
            return

        s = sum(vals)
        mn = min(vals)
        mx = max(vals)
        mean = s / n
        variance = sum((x - mean) ** 2 for x in vals) / n
        std = variance ** 0.5
        sorted_v = sorted(vals)
        median = sorted_v[n // 2] if n % 2 else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2
        q1 = sorted_v[n // 4]
        q3 = sorted_v[3 * n // 4]

        self.set_output_val(0, rc.Data(n))
        self.set_output_val(1, rc.Data(mean))
        self.set_output_val(2, rc.Data(mn))
        self.set_output_val(3, rc.Data(mx))
        self.set_output_val(4, rc.Data(mx - mn))
        self.set_output_val(5, rc.Data(std))
        self.set_output_val(6, rc.Data(variance))
        self.set_output_val(7, rc.Data(median))
        self.set_output_val(8, rc.Data(q1))
        self.set_output_val(9, rc.Data(q3))
        self.set_output_val(10, rc.Data(s))

    @staticmethod
    def _to_float(v):
        try: return float(v)
        except: return 0.0


class MovingAverageNode(WebNode):
    """
    Simple Moving Average (SMA) over a sliding window.
    Input: data stream of numbers.
    Output: smoothed series.
    """
    title = 'Moving Average'
    init_inputs = [
        rc.NodeInputType(label='val', default=rc.Data(0.0)),
        rc.NodeInputType(label='window', default=rc.Data(5)),
    ]
    init_outputs = [rc.NodeOutputType(label='avg'), rc.NodeOutputType(label='buffer')]

    def __init__(self, params):
        super().__init__(params)
        self._buffer = []

    def additional_data(self):
        d = super().additional_data()
        d['buffer'] = self._buffer
        return d

    def load_additional_data(self, data):
        super().load_additional_data(data)
        self._buffer = data.get('buffer', [])

    def update_event(self, inp=-1):
        try:
            val = float(self.input(0).payload) if self.input(0) else 0.0
        except (ValueError, TypeError):
            val = 0.0
        try:
            window = int(self.input(1).payload) if self.input(1) else 5
        except (ValueError, TypeError):
            window = 5
        if window < 1:
            window = 1

        self._buffer.append(val)
        if len(self._buffer) > window * 2:
            self._buffer = self._buffer[-window:]

        recent = self._buffer[-window:]
        avg = sum(recent) / len(recent)
        self.set_output_val(0, rc.Data(avg))
        self.set_output_val(1, rc.Data(self._buffer))


class NormalizeNode(WebNode):
    """
    Normalize a list of numbers.
    Methods: 'minmax' (scale to [0,1]), 'zscore' (standardize), 'max' (divide by max).
    """
    title = 'Normalize'
    init_inputs = [
        rc.NodeInputType(label='data', default=rc.Data([1.0, 2.0, 3.0, 4.0, 5.0])),
        rc.NodeInputType(label='method', default=rc.Data('minmax')),
    ]
    init_outputs = [rc.NodeOutputType(label='normalized'), rc.NodeOutputType(label='params')]

    def update_event(self, inp=-1):
        raw = self.input(0).payload if self.input(0) else []
        method = str(self.input(1).payload or 'minmax').lower().strip()
        if not isinstance(raw, list):
            raw = [raw]
        vals = [self._to_float(v) for v in raw if v is not None]
        if not vals:
            self.set_output_val(0, rc.Data([]))
            self.set_output_val(1, rc.Data({}))
            return

        mn, mx = min(vals), max(vals)
        if method == 'zscore':
            mean = sum(vals) / len(vals)
            var = sum((x - mean) ** 2 for x in vals) / len(vals)
            std = var ** 0.5 or 1.0
            result = [(x - mean) / std for x in vals]
            params = {'mean': mean, 'std': std}
        elif method == 'max':
            m = mx or 1.0
            result = [x / m for x in vals]
            params = {'max': m}
        else:
            r = mx - mn or 1.0
            result = [(x - mn) / r for x in vals]
            params = {'min': mn, 'range': r}

        self.set_output_val(0, rc.Data(result))
        self.set_output_val(1, rc.Data(params))

    @staticmethod
    def _to_float(v):
        try: return float(v)
        except: return 0.0


class CorrelationNode(WebNode):
    """
    Compute Pearson correlation between two data series.
    """
    title = 'Correlation'
    init_inputs = [
        rc.NodeInputType(label='a', default=rc.Data([1.0, 2.0, 3.0, 4.0, 5.0])),
        rc.NodeInputType(label='b', default=rc.Data([2.0, 4.0, 6.0, 8.0, 10.0])),
    ]
    init_outputs = [
        rc.NodeOutputType(label='r'),
        rc.NodeOutputType(label='r_squared'),
        rc.NodeOutputType(label='covariance'),
    ]

    def update_event(self, inp=-1):
        ra = self.input(0).payload if self.input(0) else []
        rb = self.input(1).payload if self.input(1) else []
        if not isinstance(ra, list): ra = [ra]
        if not isinstance(rb, list): rb = [rb]
        a = [self._to_float(v) for v in ra if v is not None]
        b = [self._to_float(v) for v in rb if v is not None]
        n = min(len(a), len(b))
        if n < 2:
            self.set_output_val(0, rc.Data(0.0))
            self.set_output_val(1, rc.Data(0.0))
            self.set_output_val(2, rc.Data(0.0))
            return
        a, b = a[:n], b[:n]
        ma, mb = sum(a) / n, sum(b) / n
        cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / n
        sa = (sum((x - ma) ** 2 for x in a) / n) ** 0.5
        sb = (sum((x - mb) ** 2 for x in b) / n) ** 0.5
        r = cov / (sa * sb) if sa * sb > 0 else 0.0
        self.set_output_val(0, rc.Data(r))
        self.set_output_val(1, rc.Data(r * r))
        self.set_output_val(2, rc.Data(cov))

    @staticmethod
    def _to_float(v):
        try: return float(v)
        except: return 0.0


class FilterNode(WebNode):
    """
    Filter data by threshold or remove outliers.
    Methods: 'threshold' (keep > threshold), 'outlier' (keep within N std of mean),
             'top_k', 'bottom_k'.
    """
    title = 'Filter'
    init_inputs = [
        rc.NodeInputType(label='data', default=rc.Data([1.0, 2.0, 99.0, 4.0, 5.0])),
        rc.NodeInputType(label='method', default=rc.Data('outlier')),
        rc.NodeInputType(label='param', default=rc.Data(2.0)),
    ]
    init_outputs = [
        rc.NodeOutputType(label='filtered'),
        rc.NodeOutputType(label='removed'),
        rc.NodeOutputType(label='info'),
    ]

    def update_event(self, inp=-1):
        raw = self.input(0).payload if self.input(0) else []
        method = str(self.input(1).payload or 'outlier').lower().strip()
        try:
            param = float(self.input(2).payload) if self.input(2) else 2.0
        except (ValueError, TypeError):
            param = 2.0
        if not isinstance(raw, list):
            raw = [raw]
        vals = [self._to_float(v) for v in raw if v is not None]
        if not vals:
            self.set_output_val(0, rc.Data([]))
            self.set_output_val(1, rc.Data([]))
            self.set_output_val(2, rc.Data('No data'))
            return

        n = len(vals)
        if method == 'outlier':
            mean = sum(vals) / n
            var = sum((x - mean) ** 2 for x in vals) / n
            std = var ** 0.5 or 1.0
            keep, drop = [], []
            for v in vals:
                if abs(v - mean) <= param * std:
                    keep.append(v)
                else:
                    drop.append(v)
            info = f'kept {len(keep)}/{n} | threshold {param} std'
        elif method == 'threshold':
            keep = [v for v in vals if v > param]
            drop = [v for v in vals if v <= param]
            info = f'kept {len(keep)}/{n} | > {param}'
        elif method == 'top_k':
            k = max(1, int(param))
            keep = sorted(vals, reverse=True)[:k]
            drop = sorted(vals, reverse=True)[k:]
            info = f'top {len(keep)}/{n}'
        elif method == 'bottom_k':
            k = max(1, int(param))
            keep = sorted(vals)[:k]
            drop = sorted(vals)[k:]
            info = f'bottom {len(keep)}/{n}'
        else:
            keep, drop = vals, []
            info = f'no filter applied ({n} points)'

        self.set_output_val(0, rc.Data(keep))
        self.set_output_val(1, rc.Data(drop))
        self.set_output_val(2, rc.Data(info))

    @staticmethod
    def _to_float(v):
        try: return float(v)
        except: return 0.0


class ChartNode(WebNode):
    """
    Lightweight multi-series chart node.
    Accepts up to 4 data series and renders a combined chart.
    Configurable: title, chart type (line/bar/area), colors, labels.
    The output SVG is a standalone viewBox chart that scales to any container.
    """
    title = 'Chart'
    init_inputs = [
        rc.NodeInputType(label='series_0', default=rc.Data([1.0, 2.0, 3.0, 4.0, 5.0])),
        rc.NodeInputType(label='series_1', default=rc.Data([])),
        rc.NodeInputType(label='series_2', default=rc.Data([])),
        rc.NodeInputType(label='series_3', default=rc.Data([])),
        rc.NodeInputType(label='title', default=rc.Data('Chart')),
        rc.NodeInputType(label='chart_type', default=rc.Data('line')),
    ]
    init_outputs = [
        rc.NodeOutputType(label='svg'),
        rc.NodeOutputType(label='all_series'),
    ]

    def update_event(self, inp=-1):
        from plotting.engine import SVGPlotter, LineSeries
        title = str(self.input(4).payload) if self.input(4) else 'Chart'
        chart_type = str(self.input(5).payload or 'line').lower().strip()
        colors = ['#6366f1', '#22c55e', '#ef4444', '#f59e0b']
        labels = ['Series A', 'Series B', 'Series C', 'Series D']
        series = []
        all_vals = []
        for i in range(4):
            raw = self.input(i).payload if self.input(i) else []
            if not isinstance(raw, list):
                raw = [raw]
            vals = [self._to_float(v) for v in raw if v is not None]
            if vals:
                all_vals.extend(vals)
                series.append(LineSeries(
                    vals, color=colors[i], label=labels[i] if len([s for s in [self.input(j).payload for j in range(4)] if s]) > 1 else '',
                    style=chart_type if chart_type in ('line', 'bar', 'area') else 'line',
                    fill=(chart_type == 'area'),
                ))
        if not series:
            series = [LineSeries([0], color='#6366f1')]

        # Auto-detect height based on series count
        h = 160 + max(0, len(series) - 1) * 16
        svg = SVGPlotter.plot_lines(series, title=title, width=400, height=h)
        self.set_output_val(0, rc.Data(svg))
        self.set_output_val(1, rc.Data(all_vals))

    @staticmethod
    def _to_float(v):
        try: return float(v)
        except: return 0.0


class DataFrameNode(WebNode):
    """
    Simple in-memory data table using Polars.
    Accepts a list of dicts or a list of rows and column schema.
    Operations: head, tail, describe, select columns, sort, filter rows.
    """
    title = 'DataFrame'
    init_inputs = [
        rc.NodeInputType(label='data', default=rc.Data([{'x': 1, 'y': 10}, {'x': 2, 'y': 20}])),
        rc.NodeInputType(label='operation', default=rc.Data('describe')),
        rc.NodeInputType(label='param', default=rc.Data('')),
    ]
    init_outputs = [
        rc.NodeOutputType(label='result'),
        rc.NodeOutputType(label='info'),
    ]

    def update_event(self, inp=-1):
        import polars as pl
        raw = self.input(0).payload
        op = str(self.input(1).payload or 'describe').lower().strip()
        param = str(self.input(2).payload or '')

        if not raw:
            self.set_output_val(0, rc.Data([]))
            self.set_output_val(1, rc.Data('No data'))
            return

        try:
            if isinstance(raw, list) and raw and isinstance(raw[0], dict):
                df = pl.DataFrame(raw)
            elif isinstance(raw, list) and raw and isinstance(raw[0], list):
                # Try automatic schema detection
                cols = [f"col_{i}" for i in range(len(raw[0]))]
                df = pl.DataFrame({cols[i]: [row[i] for row in raw] for i in range(len(cols))})
            else:
                df = pl.DataFrame({'value': raw} if isinstance(raw, list) else {'value': [raw]})
        except Exception as e:
            self.set_output_val(0, rc.Data([]))
            self.set_output_val(1, rc.Data(f'Error: {e}'))
            return

        try:
            if op == 'describe':
                desc = df.describe()
                result = desc.to_dicts()
                info = f'Shape: {df.shape} | {len(df.columns)} cols, {df.height} rows'
            elif op == 'head':
                n = 5
                try: n = int(param)
                except: pass
                result = df.head(n).to_dicts()
                info = f'First {n} rows'
            elif op == 'tail':
                n = 5
                try: n = int(param)
                except: pass
                result = df.tail(n).to_dicts()
                info = f'Last {n} rows'
            elif op == 'columns':
                cols = param.split(',') if param else df.columns
                cols = [c.strip() for c in cols if c.strip() in df.columns]
                if cols:
                    result = df.select(cols).to_dicts()
                else:
                    result = df.to_dicts()
                info = f'Selected {len(cols)} columns'
            elif op == 'sort':
                col = param or df.columns[0]
                result = df.sort(col).to_dicts()
                info = f'Sorted by {col}'
            else:
                result = df.to_dicts()
                info = f'Shape: {df.shape}'
        except Exception as e:
            result = df.to_dicts()
            info = f'Shape: {df.shape} | Op error: {e}'

        self.set_output_val(0, rc.Data(result))
        self.set_output_val(1, rc.Data(info))
