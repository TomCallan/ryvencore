import math

class SVGPlotter:
    """
    Pure Python SVG plotting engine for premium, responsive visualizations.
    Generates modern, dark-themed SVGs with glowing lines, gradients, and grids.
    """

    @staticmethod
    def _create_gradient(svg_id, color_start, color_end, opacity_start=0.4, opacity_end=0.0):
        return f"""
        <linearGradient id="{svg_id}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="{color_start}" stop-opacity="{opacity_start}"/>
            <stop offset="100%" stop-color="{color_end}" stop-opacity="{opacity_end}"/>
        </linearGradient>
        """

    @staticmethod
    def _create_glow_filter(filter_id, glow_color):
        return f"""
        <filter id="{filter_id}" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="{glow_color}" flood-opacity="0.5"/>
        </filter>
        """

    @classmethod
    def plot_line(cls, data, title="Data Plot", width=320, height=160, color="#6366f1", fill_color="#4f46e5"):
        """
        Generates a beautiful SVG line plot with gridlines, gradient area fill, and a glow effect.
        """
        if not data:
            # Fallback if empty
            data = [0, 0]

        # Safety coerce
        data_clean = []
        for x in data:
            try:
                data_clean.append(float(x))
            except (ValueError, TypeError):
                data_clean.append(0.0)
        data = data_clean

        n = len(data)
        min_y = min(data)
        max_y = max(data)
        y_range = max_y - min_y
        if y_range == 0:
            y_range = 1.0

        # Margins
        margin_left = 40
        margin_right = 15
        margin_top = 25
        margin_bottom = 20

        plot_w = width - margin_left - margin_right
        plot_h = height - margin_top - margin_bottom

        # Grid lines
        grid_html = []
        y_ticks = 4
        for i in range(y_ticks):
            ratio = i / (y_ticks - 1)
            y_coord = margin_top + plot_h * (1 - ratio)
            val = min_y + y_range * ratio
            grid_html.append(f'<line x1="{margin_left}" y1="{y_coord}" x2="{width - margin_right}" y2="{y_coord}" stroke="rgba(255,255,255,0.07)" stroke-width="1" stroke-dasharray="3,3"/>')
            grid_html.append(f'<text x="{margin_left - 8}" y="{y_coord + 4}" fill="rgba(255,255,255,0.4)" font-size="9" font-family="Outfit, sans-serif" text-anchor="end">{val:.2f}</text>')

        # Construct path points
        points = []
        for i, val in enumerate(data):
            x_ratio = i / (n - 1) if n > 1 else 0.5
            x = margin_left + x_ratio * plot_w
            y_ratio = (val - min_y) / y_range
            y = margin_top + plot_h * (1 - y_ratio)
            points.append((x, y))

        line_path = "L".join(f"{x},{y}" for x, y in points)
        if points:
            line_path = "M" + line_path[1:]

        # Fill path (area under curve)
        fill_path = ""
        if points:
            first_x, first_y = points[0]
            last_x, last_y = points[-1]
            fill_path = f"M{first_x},{margin_top + plot_h} L" + "L".join(f"{x},{y}" for x, y in points) + f" L{last_x},{margin_top + plot_h} Z"

        grad_id = f"grad_line_{id(data)}"
        filter_id = f"glow_line_{id(data)}"

        svg = []
        svg.append(f'<svg width="100%" height="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">')
        svg.append("<defs>")
        svg.append(cls._create_gradient(grad_id, color, color, 0.25, 0.0))
        svg.append(cls._create_glow_filter(filter_id, color))
        svg.append("</defs>")

        # Background card style
        svg.append(f'<rect width="{width}" height="{height}" rx="6" fill="rgba(24, 24, 37, 0.7)" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>')
        
        # Title
        svg.append(f'<text x="12" y="16" fill="rgba(255,255,255,0.7)" font-size="10" font-family="Outfit, sans-serif" font-weight="600">{title}</text>')

        # Grid and axes
        svg.extend(grid_html)

        if points:
            # Draw area fill
            svg.append(f'<path d="{fill_path}" fill="url(#{grad_id})"/>')
            # Draw line path with glow filter
            svg.append(f'<path d="{line_path}" fill="none" stroke="{color}" stroke-width="2" filter="url(#{filter_id})"/>')
            # Draw main line path crisp
            svg.append(f'<path d="{line_path}" fill="none" stroke="{color}" stroke-width="1.5"/>')
            
            # Highlight last point
            last_x, last_y = points[-1]
            svg.append(f'<circle cx="{last_x}" cy="{last_y}" r="3.5" fill="{color}" stroke="white" stroke-width="1"/>')

        svg.append("</svg>")
        return "".join(svg)

    @classmethod
    def plot_orderbook(cls, bids, asks, title="Orderbook Depth", width=320, height=160):
        """
        Generates a cumulative orderbook depth chart.
        bids: list of [price, size]
        asks: list of [price, size]
        """
        # Sort and cumulative calculations
        # Bids: sorted descending by price
        bids = sorted([[float(p), float(s)] for p, s in bids], key=lambda x: x[0], reverse=True)
        # Asks: sorted ascending by price
        asks = sorted([[float(p), float(s)] for p, s in asks], key=lambda x: x[0])

        # Cumulate sizes
        cum_bids = []
        running_bid_vol = 0.0
        for p, s in bids:
            running_bid_vol += s
            cum_bids.append((p, running_bid_vol))

        cum_asks = []
        running_ask_vol = 0.0
        for p, s in asks:
            running_ask_vol += s
            cum_asks.append((p, running_ask_vol))

        # We want to display bids on left side, asks on right side
        # X axis ranges from min bid price to max ask price
        all_prices = [p for p, _ in cum_bids] + [p for p, _ in cum_asks]
        if not all_prices:
            # Fallback
            all_prices = [99.0, 100.0, 101.0]
            cum_bids = [(99.0, 1.0), (99.5, 2.0)]
            cum_asks = [(100.5, 2.0), (101.0, 1.0)]

        min_price = min(all_prices)
        max_price = max(all_prices)
        price_range = max_price - min_price
        if price_range == 0:
            price_range = 1.0

        all_vols = [v for _, v in cum_bids] + [v for _, v in cum_asks]
        max_vol = max(all_vols) if all_vols else 1.0

        # Margins
        margin_left = 15
        margin_right = 15
        margin_top = 25
        margin_bottom = 20

        plot_w = width - margin_left - margin_right
        plot_h = height - margin_top - margin_bottom

        # Mid price calculation
        best_bid = bids[0][0] if bids else min_price
        best_ask = asks[0][0] if asks else max_price
        mid_price = (best_bid + best_ask) / 2.0

        # Map function: price to X coordinate, vol to Y coordinate
        def get_x(price):
            ratio = (price - min_price) / price_range
            return margin_left + ratio * plot_w

        def get_y(vol):
            ratio = vol / max_vol
            return margin_top + plot_h * (1 - ratio)

        # Build bid path: Bids go from left (min price) to best bid (highest bid price)
        # Note: Bids cumulative volume increases as price decreases (going left)
        # So we sort bids ascending for drawing from left to right
        draw_bids = sorted(cum_bids, key=lambda x: x[0])
        bid_points = []
        for p, v in draw_bids:
            bid_points.append((get_x(p), get_y(v)))

        # Build ask path: Asks go from best ask (lowest ask price) to right (max price)
        draw_asks = sorted(cum_asks, key=lambda x: x[0])
        ask_points = []
        for p, v in draw_asks:
            ask_points.append((get_x(p), get_y(v)))

        # Create SVG Paths
        bid_fill_path = ""
        bid_line_path = ""
        if bid_points:
            # We want to fill down to the bottom of the plot
            first_x = bid_points[0][0]
            last_x = bid_points[-1][0]
            bid_line_path = "M" + "L".join(f"{x},{y}" for x, y in bid_points)
            bid_fill_path = f"M{first_x},{margin_top + plot_h} " + "L".join(f"{x},{y}" for x, y in bid_points) + f" L{last_x},{margin_top + plot_h} Z"

        ask_fill_path = ""
        ask_line_path = ""
        if ask_points:
            first_x = ask_points[0][0]
            last_x = ask_points[-1][0]
            ask_line_path = "M" + "L".join(f"{x},{y}" for x, y in ask_points)
            ask_fill_path = f"M{first_x},{margin_top + plot_h} " + "L".join(f"{x},{y}" for x, y in ask_points) + f" L{last_x},{margin_top + plot_h} Z"

        # Unique IDs
        bid_grad = f"bid_grad_{id(bids)}"
        ask_grad = f"ask_grad_{id(asks)}"
        bid_glow = f"bid_glow_{id(bids)}"
        ask_glow = f"ask_glow_{id(asks)}"

        svg = []
        svg.append(f'<svg width="100%" height="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">')
        svg.append("<defs>")
        svg.append(cls._create_gradient(bid_grad, "#10b981", "#10b981", 0.25, 0.0))
        svg.append(cls._create_gradient(ask_grad, "#ef4444", "#ef4444", 0.25, 0.0))
        svg.append(cls._create_glow_filter(bid_glow, "#10b981"))
        svg.append(cls._create_glow_filter(ask_glow, "#ef4444"))
        svg.append("</defs>")

        # Background card style
        svg.append(f'<rect width="{width}" height="{height}" rx="6" fill="rgba(24, 24, 37, 0.7)" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>')
        
        # Title
        svg.append(f'<text x="12" y="16" fill="rgba(255,255,255,0.7)" font-size="10" font-family="Outfit, sans-serif" font-weight="600">{title}</text>')

        # Center mid-price label
        mid_x = get_x(mid_price)
        svg.append(f'<line x1="{mid_x}" y1="{margin_top}" x2="{mid_x}" y2="{margin_top + plot_h}" stroke="rgba(255,255,255,0.15)" stroke-width="1" stroke-dasharray="2,2"/>')
        svg.append(f'<text x="{mid_x}" y="{margin_top - 5}" fill="#60a5fa" font-size="8" font-family="JetBrains Mono, monospace" font-weight="600" text-anchor="middle">MID: {mid_price:.2f}</text>')

        # Grid lines (horizontal)
        for val_ratio in [0.25, 0.5, 0.75]:
            y_coord = margin_top + plot_h * (1 - val_ratio)
            svg.append(f'<line x1="{margin_left}" y1="{y_coord}" x2="{width - margin_right}" y2="{y_coord}" stroke="rgba(255,255,255,0.05)" stroke-width="0.75" stroke-dasharray="4,4"/>')

        # Draw Bid Depth (Green)
        if bid_fill_path:
            svg.append(f'<path d="{bid_fill_path}" fill="url(#{bid_grad})"/>')
            svg.append(f'<path d="{bid_line_path}" fill="none" stroke="#10b981" stroke-width="1.5" filter="url(#{bid_glow})"/>')
            svg.append(f'<path d="{bid_line_path}" fill="none" stroke="#10b981" stroke-width="1"/>')

        # Draw Ask Depth (Red)
        if ask_fill_path:
            svg.append(f'<path d="{ask_fill_path}" fill="url(#{ask_grad})"/>')
            svg.append(f'<path d="{ask_line_path}" fill="none" stroke="#ef4444" stroke-width="1.5" filter="url(#{ask_glow})"/>')
            svg.append(f'<path d="{ask_line_path}" fill="none" stroke="#ef4444" stroke-width="1"/>')

        # Axes labels (min price, mid price, max price)
        svg.append(f'<text x="{margin_left}" y="{height - 6}" fill="rgba(255,255,255,0.4)" font-size="8" font-family="Outfit, sans-serif" text-anchor="start">{min_price:.2f}</text>')
        svg.append(f'<text x="{width - margin_right}" y="{height - 6}" fill="rgba(255,255,255,0.4)" font-size="8" font-family="Outfit, sans-serif" text-anchor="end">{max_price:.2f}</text>')

        svg.append("</svg>")
        return "".join(svg)
