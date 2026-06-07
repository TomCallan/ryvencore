/**
 * ChartRenderer — Client-side SVG charting for real-time node plots.
 * Supports multi-line, bar, area, and indicator overlays.
 * Auto-scales to container via ResizeObserver.
 */

const NS = 'http://www.w3.org/2000/svg';

const COLORS = ['#6366f1', '#22c55e', '#ef4444', '#f59e0b', '#06b6d4', '#a855f7', '#3b82f6', '#10b981'];

export class ChartRenderer {
    /**
     * @param {jQuery|HTMLElement} container  DOM element to hold the chart
     * @param {object} opts  { bg, title, margin }
     */
    constructor(container, opts = {}) {
        this.$el = $(container);
        this.opts = Object.assign({ bg: 'rgba(0,0,0,0.3)', title: '', margin: { l: 42, r: 14, t: 24, b: 20 } }, opts);
        this.$el.empty().css({ position: 'relative', overflow: 'hidden' });
        this._svg = null;
        this._data = [];
        this._indicators = [];

        // Auto-resize
        this._ro = new ResizeObserver(() => this._resize());
        this._ro.observe(this.$el[0]);
        this._needsRender = true;
        // Throttled render via animation frame
        this._rafId = null;
    }

    destroy() {
        this._ro.disconnect();
        if (this._rafId) cancelAnimationFrame(this._rafId);
    }

    /** Set data series: array of { data:number[], color, label, style, fill } */
    setData(series) {
        this._data = series.map(s => Object.assign({
            data: [], color: COLORS[Math.floor(Math.random() * COLORS.length)],
            label: '', style: 'line', fill: false,
        }, s));
        this._scheduleRender();
    }

    /** Set overlay indicators: array of { kind, y?, x?, color, label } */
    setIndicators(indicators) {
        this._indicators = indicators;
        this._scheduleRender();
    }

    _scheduleRender() {
        this._needsRender = true;
        if (!this._rafId) {
            this._rafId = requestAnimationFrame(() => {
                this._rafId = null;
                if (this._needsRender) this._render();
            });
        }
    }

    _resize() {
        this._scheduleRender();
    }

    _render() {
        this._needsRender = false;
        const cw = this.$el.width();
        const ch = this.$el.height();
        if (cw < 10 || ch < 10) return;

        this.$el.empty();
        this._svg = $(document.createElementNS(NS, 'svg'))
            .attr({ width: '100%', height: '100%', viewBox: `0 0 ${cw} ${ch}` })
            .css({ display: 'block' });
        this.$el.append(this._svg);

        const m = this.opts.margin;
        const pw = cw - m.l - m.r;
        const ph = ch - m.t - m.b;
        if (pw < 10 || ph < 10) return;

        const g = $(document.createElementNS(NS, 'g'));
        this._svg.append(g);

        // Background
        g.append(`<rect width="${cw}" height="${ch}" fill="${this.opts.bg}" rx="4"/>`);

        if (this.opts.title) {
            g.append(`<text x="${m.l}" y="${m.t - 6}" fill="rgba(255,255,255,0.6)" font-size="10" font-family="Outfit,sans-serif" font-weight="600">${this.opts.title}</text>`);
        }

        // Gather all values
        let allVals = [];
        this._data.forEach(s => {
            if (s.data) s.data.forEach(v => { if (v != null) allVals.push(Number(v)); });
        });
        if (!allVals.length) allVals = [0, 1];
        let mn = Math.min(...allVals), mx = Math.max(...allVals);
        const pad = (mx - mn) * 0.08 || 0.1;
        mn -= pad; mx += pad;

        const maxN = Math.max(1, ...this._data.map(s => s.data ? s.data.length : 0));
        const n = Math.max(maxN, 2);

        const xPos = i => m.l + (i / (n - 1)) * pw;
        const yPos = v => m.t + ph * (1 - (v - mn) / (mx - mn));

        // Grid
        for (let i = 0; i < 4; i++) {
            const ratio = i / 3;
            const yc = m.t + ph * (1 - ratio);
            const val = mn + (mx - mn) * ratio;
            g.append(`<line x1="${m.l}" y1="${yc}" x2="${m.l + pw}" y2="${yc}" stroke="rgba(255,255,255,0.06)" stroke-width="1" stroke-dasharray="3,3"/>`);
            g.append(`<text x="${m.l - 6}" y="${yc + 3}" fill="rgba(255,255,255,0.3)" font-size="8" font-family="Outfit,sans-serif" text-anchor="end">${val.toFixed(2)}</text>`);
        }

        // Indicators
        this._indicators.forEach(ind => {
            if (ind.kind === 'hline' && ind.y != null) {
                const yy = yPos(ind.y);
                g.append(`<line x1="${m.l}" y1="${yy}" x2="${m.l + pw}" y2="${yy}" stroke="${ind.color || '#f59e0b'}" stroke-width="1" stroke-dasharray="4,4" opacity="0.6"/>`);
                if (ind.label) g.append(`<text x="${m.l + 4}" y="${yy - 3}" fill="${ind.color || '#f59e0b'}" font-size="8" font-family="JetBrains Mono,monospace">${ind.label}</text>`);
            } else if (ind.kind === 'vline' && ind.x != null) {
                const xx = xPos(ind.x);
                g.append(`<line x1="${xx}" y1="${m.t}" x2="${xx}" y2="${m.t + ph}" stroke="${ind.color || '#f59e0b'}" stroke-width="1" stroke-dasharray="4,4" opacity="0.6"/>`);
                if (ind.label) g.append(`<text x="${xx}" y="${m.t - 4}" fill="${ind.color || '#f59e0b'}" font-size="8" font-family="JetBrains Mono,monospace" text-anchor="middle">${ind.label}</text>`);
            } else if (ind.kind === 'flag' && ind.x != null && ind.y != null) {
                const fx = xPos(ind.x), fy = yPos(ind.y);
                g.append(`<polygon points="${fx},${fy - 8} ${fx + 18},${fy - 4} ${fx},${fy}" fill="${ind.color || '#f59e0b'}" opacity="0.9"/>`);
                if (ind.label) g.append(`<text x="${fx + 20}" y="${fy - 2}" fill="${ind.color || '#f59e0b'}" font-size="8" font-family="JetBrains Mono,monospace" font-weight="600">${ind.label}</text>`);
            }
        });

        // Series
        this._data.forEach((s, si) => {
            const pts = [];
            if (s.data) s.data.forEach((v, i) => { if (v != null) pts.push({ x: xPos(i), y: yPos(Number(v)) }); });
            if (pts.length < 2) return;

            if (s.style === 'bar') {
                const bw = Math.min(Math.max(2, pw / n * 0.5), 12);
                const zy = yPos(0);
                pts.forEach((p, i) => {
                    if (s.data[i] == null) return;
                    const top = Math.min(p.y, zy);
                    const hh = Math.max(Math.abs(p.y - zy), 1);
                    const bar = $(document.createElementNS(NS, 'rect'))
                        .attr({ x: p.x - bw / 2, y: top, width: bw, height: hh, rx: 1, fill: s.color, opacity: 0.85 });
                    g.append(bar);
                });
            } else {
                const d = 'M' + pts.map(p => `${p.x},${p.y}`).join('L');
                if (s.fill) {
                    const fd = `M${pts[0].x},${m.t + ph}L${pts.map(p => `${p.x},${p.y}`).join('L')}L${pts[pts.length - 1].x},${m.t + ph}Z`;
                    g.append(`<path d="${fd}" fill="${s.color}" opacity="0.15"/>`);
                }
                g.append(`<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.width || 2}" stroke-linecap="round" stroke-linejoin="round"/>`);
                // end dot
                const last = pts[pts.length - 1];
                g.append(`<circle cx="${last.x}" cy="${last.y}" r="2.5" fill="${s.color}" stroke="white" stroke-width="1"/>`);
                if (s.label) g.append(`<text x="${last.x + 5}" y="${last.y + 3}" fill="${s.color}" font-size="8" font-family="Outfit,sans-serif">${s.label}</text>`);
            }

            // Legend
            if (s.label && this._data.length > 1) {
                const lx2 = m.l + 4, ly2 = m.t + 10 + si * 13;
                g.append(`<line x1="${lx2}" y1="${ly2 + 3}" x2="${lx2 + 12}" y2="${ly2 + 3}" stroke="${s.color}" stroke-width="2"/>`);
                g.append(`<text x="${lx2 + 16}" y="${ly2 + 6}" fill="rgba(255,255,255,0.5)" font-size="7" font-family="Outfit,sans-serif">${s.label}</text>`);
            }
        });
    }
}
