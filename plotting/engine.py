"""
Pure Python SVG plotting engine — TradingView-quality visualizations.

Features:
  - Multiple series (line, bar, area) in one chart
  - Horizontal / vertical indicator lines and flags
  - Auto-scaled to container via viewBox
  - Dark theme with gradients and glow
"""
import math
from typing import List, Optional, Tuple, Union


# ---- Data model ----

class LineSeries:
    """A single data series: line, bar, or area."""
    def __init__(self, data: List[float], color: str = '#6366f1', label: str = '',
                 width: float = 2, style: str = 'line', fill: bool = False):
        """
        style: 'line', 'bar', 'area'
        """
        self.data = [self._to_float(v) for v in data]
        self.color = color
        self.label = label
        self.width = width
        self.style = style
        self.fill = fill

    @staticmethod
    def _to_float(v):
        try: return float(v)
        except: return 0.0


class Indicator:
    """An overlay indicator: horizontal line, vertical line, or flag."""
    def __init__(self, kind: str = 'hline', y: Optional[float] = None,
                 x: Optional[float] = None, color: str = '#f59e0b',
                 label: str = '', dash: str = '4,4'):
        self.kind = kind          # 'hline', 'vline', 'flag'
        self.y = y
        self.x = x
        self.color = color
        self.label = label
        self.dash = dash


class OHLCVBar:
    """Single OHLCV bar for candlestick charts."""
    def __init__(self, time: float, open: float, high: float, low: float, close: float,
                 volume: float = 0, color_up: str = '#22c55e', color_down: str = '#ef4444'):
        self.time = time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.color_up = color_up
        self.color_down = color_down


# ---- Plotter ----

class SVGPlotter:
    """
    TradingView-style SVG chart engine.
    All plots use viewBox so they scale to any container.
    """

    # ─── helpers ────────────────────────────────────────────

    @staticmethod
    def _gradient(svg_id: str, c: str, o1: float = 0.3, o2: float = 0.0):
        return f'<linearGradient id="{svg_id}" x1="0" y1="0" x2="0" y2="1">' \
               f'<stop offset="0%" stop-color="{c}" stop-opacity="{o1}"/>' \
               f'<stop offset="100%" stop-color="{c}" stop-opacity="{o2}"/>' \
               f'</linearGradient>'

    @staticmethod
    def _glow(fid: str, c: str):
        return f'<filter id="{fid}" x="-20%" y="-20%" width="140%" height="140%">' \
               f'<feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="{c}" flood-opacity="0.5"/>' \
               f'</filter>'

    # ─── layout ────────────────────────────────────────────

    @classmethod
    def _layout(cls, width: int, height: int, title: str, margin: dict = None):
        m = margin or {'l': 42, 'r': 14, 't': 26, 'b': 22}
        pw = width - m['l'] - m['r']
        ph = height - m['t'] - m['b']
        out = []
        out.append(f'<svg width="100%" height="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">')
        out.append(f'<rect width="{width}" height="{height}" rx="6" fill="rgba(24,24,37,0.7)" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>')
        if title:
            out.append(f'<text x="12" y="16" fill="rgba(255,255,255,0.7)" font-size="10" font-family="Outfit,sans-serif" font-weight="600">{title}</text>')
        return out, m, pw, ph

    @classmethod
    def _grid(cls, pw: float, ph: float, ml: float, mt: float, mr: float,
              min_v: float, max_v: float, y_ticks: int = 4):
        out = []
        rng = max_v - min_v
        if rng == 0: rng = 1.0
        for i in range(y_ticks):
            ratio = i / (y_ticks - 1)
            yc = mt + ph * (1 - ratio)
            val = min_v + rng * ratio
            out.append(f'<line x1="{ml}" y1="{yc}" x2="{ml + pw}" y2="{yc}" stroke="rgba(255,255,255,0.07)" stroke-width="1" stroke-dasharray="3,3"/>')
            out.append(f'<text x="{ml - 8}" y="{yc + 4}" fill="rgba(255,255,255,0.4)" font-size="9" font-family="Outfit,sans-serif" text-anchor="end">{val:.2f}</text>')
        return out

    # ─── plot_lines — multi-series chart ─────────────────────

    @classmethod
    def plot_lines(cls, series_list: List[Union[LineSeries, List[float]]],
                   title: str = 'Chart', indicators: Optional[List[Indicator]] = None,
                   width: int = 320, height: int = 160,
                   colors: Optional[List[str]] = None,
                   labels: Optional[List[str]] = None) -> str:
        """
        Render multiple series on one chart.
        Each entry in series_list can be a LineSeries or a plain list[float].
        """
        # Normalise inputs
        parsed: List[LineSeries] = []
        palette = colors or ['#6366f1', '#22c55e', '#ef4444', '#f59e0b', '#06b6d4', '#a855f7', '#3b82f6', '#10b981']
        default_labels = labels or []
        for i, s in enumerate(series_list):
            if isinstance(s, LineSeries):
                parsed.append(s)
            else:
                parsed.append(LineSeries(s, color=palette[i % len(palette)],
                               label=default_labels[i] if i < len(default_labels) else ''))
        if not parsed:
            return cls.plot_lines([LineSeries([0, 0])], title=title, width=width, height=height)

        # Global min/max across all series
        all_vals = [v for s in parsed for v in s.data if v is not None]
        if not all_vals: all_vals = [0, 1]
        mn, mx = min(all_vals), max(all_vals)
        padding = (mx - mn) * 0.05 or 0.1
        mn -= padding; mx += padding

        n_points = max(len(s.data) for s in parsed)
        if n_points < 2: n_points = 2

        indicators = indicators or []

        out, m, pw, ph = cls._layout(width, height, title)
        out.append('<defs>')
        for i, s in enumerate(parsed):
            out.append(cls._gradient(f'g_{i}', s.color, 0.2, 0.0))
            out.append(cls._glow(f'gl_{i}', s.color))
        out.append('</defs>')

        # Grid
        out.extend(cls._grid(pw, ph, m['l'], m['t'], m['r'], mn, mx))

        # Mapping
        def x_pos(idx):
            return m['l'] + (idx / (n_points - 1)) * pw

        def y_pos(val):
            return m['t'] + ph * (1 - (val - mn) / (mx - mn))

        # Indicators
        for ind in indicators:
            if ind.kind == 'hline' and ind.y is not None:
                yy = y_pos(ind.y)
                out.append(f'<line x1="{m["l"]}" y1="{yy}" x2="{m["l"] + pw}" y2="{yy}" stroke="{ind.color}" stroke-width="1" stroke-dasharray="{ind.dash}" opacity="0.7"/>')
                if ind.label:
                    out.append(f'<text x="{m["l"] + 4}" y="{yy - 3}" fill="{ind.color}" font-size="8" font-family="JetBrains Mono,monospace">{ind.label}</text>')
            elif ind.kind == 'vline' and ind.x is not None:
                xx = x_pos(ind.x)
                out.append(f'<line x1="{xx}" y1="{m["t"]}" x2="{xx}" y2="{m["t"] + ph}" stroke="{ind.color}" stroke-width="1" stroke-dasharray="{ind.dash}" opacity="0.7"/>')
                if ind.label:
                    out.append(f'<text x="{xx}" y="{m["t"] - 4}" fill="{ind.color}" font-size="8" font-family="JetBrains Mono,monospace" text-anchor="middle">{ind.label}</text>')
            elif ind.kind == 'flag' and ind.x is not None and ind.y is not None:
                fx, fy = x_pos(ind.x), y_pos(ind.y)
                out.append(f'<polygon points="{fx},{fy - 8} {fx + 20},{fy - 4} {fx},{fy}" fill="{ind.color}" opacity="0.9"/>')
                if ind.label:
                    out.append(f'<text x="{fx + 22}" y="{fy - 2}" fill="{ind.color}" font-size="8" font-family="JetBrains Mono,monospace" font-weight="600">{ind.label}</text>')

        # Series
        for si, s in enumerate(parsed):
            pts = []
            for i, v in enumerate(s.data):
                if v is not None:
                    pts.append((x_pos(i), y_pos(v)))

            if len(pts) < 2:
                continue

            if s.style == 'bar':
                bar_w = max(2, pw / n_points * 0.6)
                zero_y = y_pos(0)
                for i, (px, py) in enumerate(pts):
                    if s.data[i] is not None:
                        bw = bar_w if bar_w < 30 else 12
                        bottom = max(py, zero_y)
                        top = min(py, zero_y)
                        hh = max(abs(py - zero_y), 1)
                        out.append(f'<rect x="{px - bw / 2}" y="{top}" width="{bw}" height="{hh}" rx="1" fill="{s.color}" opacity="0.85"/>')

            elif s.style == 'area':
                path = 'M' + 'L'.join(f'{x},{y}' for x, y in pts)
                fill_p = f'M{pts[0][0]},{m["t"] + ph} L' + 'L'.join(f'{x},{y}' for x, y in pts) + f' L{pts[-1][0]},{m["t"] + ph} Z'
                out.append(f'<path d="{fill_p}" fill="url(#g_{si})"/>')
                out.append(f'<path d="{path}" fill="none" stroke="{s.color}" stroke-width="{s.width}" filter="url(#gl_{si})"/>')
                out.append(f'<path d="{path}" fill="none" stroke="{s.color}" stroke-width="{s.width - 0.5}"/>')
            else:
                path = 'M' + 'L'.join(f'{x},{y}' for x, y in pts)
                if s.fill:
                    fill_p = f'M{pts[0][0]},{m["t"] + ph} L' + 'L'.join(f'{x},{y}' for x, y in pts) + f' L{pts[-1][0]},{m["t"] + ph} Z'
                    out.append(f'<path d="{fill_p}" fill="url(#g_{si})"/>')
                out.append(f'<path d="{path}" fill="none" stroke="{s.color}" stroke-width="{s.width}" filter="url(#gl_{si})"/>')
                out.append(f'<path d="{path}" fill="none" stroke="{s.color}" stroke-width="{s.width - 0.5}"/>')

            # End dot + label
            lx, ly = pts[-1]
            out.append(f'<circle cx="{lx}" cy="{ly}" r="3" fill="{s.color}" stroke="white" stroke-width="1"/>')
            if s.label:
                out.append(f'<text x="{lx + 6}" y="{ly + 3}" fill="{s.color}" font-size="8" font-family="Outfit,sans-serif">{s.label}</text>')

            # Legend
            if s.label and len(parsed) > 1:
                lx_leg = m['l'] + 4
                ly_leg = m['t'] + 12 + si * 14
                out.append(f'<line x1="{lx_leg}" y1="{ly_leg + 3}" x2="{lx_leg + 14}" y2="{ly_leg + 3}" stroke="{s.color}" stroke-width="2"/>')
                out.append(f'<text x="{lx_leg + 18}" y="{ly_leg + 6}" fill="rgba(255,255,255,0.6)" font-size="7" font-family="Outfit,sans-serif">{s.label}</text>')

        out.append('</svg>')
        return ''.join(out)

    # ─── convenience single-line ────────────────────────────

    @classmethod
    def plot_line(cls, data: List[float], title: str = 'Data Plot',
                  width: int = 320, height: int = 160, color: str = '#6366f1',
                  fill_color: str = '#4f46e5'):
        """Single line series (backward-compatible)."""
        return cls.plot_lines([LineSeries(data, color=color, fill=True)],
                              title=title, width=width, height=height)

    # ─── orderbook depth ────────────────────────────────────

    @classmethod
    def plot_orderbook(cls, bids, asks, title: str = 'Orderbook Depth',
                       width: int = 320, height: int = 160,
                       show_volume_bars: bool = True):
        """
        Enhanced orderbook depth chart with volume bars and spread indicator.
        bids: list of [price, size]
        asks: list of [price, size]
        """
        bids = sorted([[float(p), float(s)] for p, s in bids], key=lambda x: x[0], reverse=True)
        asks = sorted([[float(p), float(s)] for p, s in asks], key=lambda x: x[0])

        cum_b, cum_a = [], []
        rv = 0.0
        for p, s in bids: rv += s; cum_b.append((p, rv))
        rv = 0.0
        for p, s in asks: rv += s; cum_a.append((p, rv))

        all_p = [p for p, _ in cum_b] + [p for p, _ in cum_a]
        if not all_p: all_p = [99, 100, 101]
        mn_p, mx_p = min(all_p), max(all_p)
        pr = mx_p - mn_p or 1.0

        all_v = [v for _, v in cum_b] + [v for _, v in cum_a]
        mx_v = max(all_v) or 1.0

        m = {'l': 14, 'r': 14, 't': 26, 'b': 22}
        pw, ph = width - m['l'] - m['r'], height - m['t'] - m['b']

        def gx(p): return m['l'] + (p - mn_p) / pr * pw
        def gy(v): return m['t'] + ph * (1 - v / mx_v)

        best_bid = bids[0][0] if bids else mn_p
        best_ask = asks[0][0] if asks else mx_p
        mid = (best_bid + best_ask) / 2

        db = sorted(cum_b, key=lambda x: x[0])
        da = sorted(cum_a, key=lambda x: x[0])
        bp = [(gx(p), gy(v)) for p, v in db]
        ap = [(gx(p), gy(v)) for p, v in da]

        bf, bl, af, al = '', '', '', ''
        if bp:
            bf = f'M{bp[0][0]},{m["t"] + ph} L' + 'L'.join(f'{x},{y}' for x, y in bp) + f' L{bp[-1][0]},{m["t"] + ph} Z'
            bl = 'M' + 'L'.join(f'{x},{y}' for x, y in bp)
        if ap:
            af = f'M{ap[0][0]},{m["t"] + ph} L' + 'L'.join(f'{x},{y}' for x, y in ap) + f' L{ap[-1][0]},{m["t"] + ph} Z'
            al = 'M' + 'L'.join(f'{x},{y}' for x, y in ap)

        bid_g = f'bg_{id(bids)}'; ask_g = f'ag_{id(asks)}'
        bg2 = f'bg2_{id(bids)}'; ag2 = f'ag2_{id(asks)}'

        out, _, _, _ = cls._layout(width, height, title, m)
        out.append('<defs>')
        out.append(cls._gradient(bid_g, '#10b981', 0.25, 0.0))
        out.append(cls._gradient(ask_g, '#ef4444', 0.25, 0.0))
        out.append(cls._gradient(bg2, '#10b981', 0.08, 0.0))
        out.append(cls._gradient(ag2, '#ef4444', 0.08, 0.0))
        out.append(cls._glow(f'bg_{id(bids)}', '#10b981'))
        out.append(cls._glow(f'ag_{id(asks)}', '#ef4444'))
        out.append('</defs>')

        # Grid
        for vr in [0.25, 0.5, 0.75]:
            yc = m['t'] + ph * (1 - vr)
            out.append(f'<line x1="{m["l"]}" y1="{yc}" x2="{width - m["r"]}" y2="{yc}" stroke="rgba(255,255,255,0.05)" stroke-width="0.75" stroke-dasharray="4,4"/>')

        # Depth fills / lines
        if bf: out.append(f'<path d="{bf}" fill="url(#{bid_g})"/>')
        if bl: out.append(f'<path d="{bl}" fill="none" stroke="#10b981" stroke-width="1.5" filter="url(#bg_{id(bids)})"/><path d="{bl}" fill="none" stroke="#10b981" stroke-width="1"/>')
        if af: out.append(f'<path d="{af}" fill="url(#{ask_g})"/>')
        if al: out.append(f'<path d="{al}" fill="none" stroke="#ef4444" stroke-width="1.5" filter="url(#ag_{id(asks)})"/><path d="{al}" fill="none" stroke="#ef4444" stroke-width="1"/>')

        # Volume bars (individual order sizes)
        if show_volume_bars:
            max_bid_size = max([s for _, s in bids] + [1])
            max_ask_size = max([s for _, s in asks] + [1])
            max_vol_bar = max(max_bid_size, max_ask_size) or 1.0
            vh = 30
            for p, s in cum_b:
                bw = max(2, pw / len(all_p) * 0.3) if len(all_p) > 1 else 4
                hh = (s / max_vol_bar) * vh
                out.append(f'<rect x="{gx(p) - bw / 2}" y="{m["t"] + ph - hh}" width="{bw}" height="{hh}" fill="#10b981" opacity="0.2" rx="1"/>')
            for p, s in cum_a:
                bw = max(2, pw / len(all_p) * 0.3) if len(all_p) > 1 else 4
                hh = (s / max_vol_bar) * vh
                out.append(f'<rect x="{gx(p) - bw / 2}" y="{m["t"] + ph - hh}" width="{bw}" height="{hh}" fill="#ef4444" opacity="0.2" rx="1"/>')

        # Mid-price line
        mx_x = gx(mid)
        out.append(f'<line x1="{mx_x}" y1="{m["t"]}" x2="{mx_x}" y2="{m["t"] + ph}" stroke="rgba(255,255,255,0.15)" stroke-width="1" stroke-dasharray="2,2"/>')
        out.append(f'<text x="{mx_x}" y="{m["t"] - 5}" fill="#60a5fa" font-size="8" font-family="JetBrains Mono,monospace" font-weight="600" text-anchor="middle">MID {mid:.2f}</text>')

        # Spread label
        spread = best_ask - best_bid
        out.append(f'<text x="{m["l"] + pw}" y="{m["t"] - 5}" fill="rgba(255,255,255,0.5)" font-size="7" font-family="JetBrains Mono,monospace" text-anchor="end">SPREAD {spread:.4f}</text>')

        # Bid/Ask ratio
        bid_vol = cum_b[-1][1] if cum_b else 1
        ask_vol = cum_a[-1][1] if cum_a else 1
        ratio = bid_vol / ask_vol if ask_vol > 0 else 1
        ratio_color = '#22c55e' if ratio > 1 else '#ef4444'
        out.append(f'<text x="{m["l"] + 4}" y="{m["t"] + ph + 14}" fill="{ratio_color}" font-size="8" font-family="JetBrains Mono,monospace" font-weight="600">B/A {ratio:.2f}</text>')

        # Price labels
        out.append(f'<text x="{m["l"]}" y="{height - 6}" fill="rgba(255,255,255,0.4)" font-size="8" font-family="Outfit,sans-serif" text-anchor="start">{mn_p:.2f}</text>')
        out.append(f'<text x="{width - m["r"]}" y="{height - 6}" fill="rgba(255,255,255,0.4)" font-size="8" font-family="Outfit,sans-serif" text-anchor="end">{mx_p:.2f}</text>')

        out.append('</svg>')
        return ''.join(out)

    # ─── candlestick ────────────────────────────────────────

    @classmethod
    def plot_candlesticks(cls, bars: List[OHLCVBar], title: str = 'Candlesticks',
                          width: int = 320, height: int = 160,
                          show_volume: bool = True) -> str:
        """OHLCV candlestick chart."""
        if not bars: return cls.plot_lines([LineSeries([0])], title=title, width=width, height=height)

        hi = max(b.high for b in bars)
        lo = min(b.low for b in bars)
        pad = (hi - lo) * 0.05 or 0.1
        hi += pad; lo -= pad
        rng = hi - lo or 1.0

        out, m, pw, ph = cls._layout(width, height, title)
        out.append('</defs>')  # no defs needed

        # Grid
        for vr in [0.25, 0.5, 0.75]:
            yc = m['t'] + ph * (1 - vr)
            out.append(f'<line x1="{m["l"]}" y1="{yc}" x2="{m["l"] + pw}" y2="{yc}" stroke="rgba(255,255,255,0.07)" stroke-width="1" stroke-dasharray="3,3"/>')
            out.append(f'<text x="{m["l"] - 8}" y="{yc + 4}" fill="rgba(255,255,255,0.4)" font-size="9" font-family="Outfit,sans-serif" text-anchor="end">{lo + rng * (1 - vr):.2f}</text>')

        n = len(bars)
        if n < 2: n = 2

        for i, b in enumerate(bars):
            cx = m['l'] + (i / (n - 1)) * pw
            cw = max(2, pw / n * 0.6)
            if cw > 20: cw = 12

            is_up = b.close >= b.open
            clr = b.color_up if is_up else b.color_down

            oy = m['t'] + ph * (1 - (b.open - lo) / rng)
            cy = m['t'] + ph * (1 - (b.close - lo) / rng)
            hy = m['t'] + ph * (1 - (b.high - lo) / rng)
            ly2 = m['t'] + ph * (1 - (b.low - lo) / rng)

            # Wick
            out.append(f'<line x1="{cx}" y1="{hy}" x2="{cx}" y2="{ly2}" stroke="{clr}" stroke-width="1.5"/>')
            # Body
            body_top = min(oy, cy)
            body_h = max(abs(cy - oy), 1)
            out.append(f'<rect x="{cx - cw / 2}" y="{body_top}" width="{cw}" height="{body_h}" rx="1" fill="{clr}"/>')

            # Volume bar at bottom
            if show_volume and b.volume > 0:
                vh = (b.volume / (max(bar.volume for bar in bars) or 1)) * 15
                out.append(f'<rect x="{cx - cw / 4}" y="{m["t"] + ph - vh}" width="{cw / 2}" height="{vh}" fill="{clr}" opacity="0.25" rx="1"/>')

        out.append('</svg>')
        return ''.join(out)
