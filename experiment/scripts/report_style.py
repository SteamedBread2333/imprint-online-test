"""Shared layout for experiment HTML: document style, print-friendly."""

CSS = """
:root {
  --ink: #111111;
  --muted: #555555;
  --line: #d0d0d0;
  --fill: #f6f6f6;
}
* { box-sizing: border-box; }
html { font-size: 15px; }
body {
  margin: 0;
  color: var(--ink);
  background: #fff;
  font-family: "Helvetica Neue", Helvetica, Arial, "PingFang SC", "Hiragino Sans GB",
    "Noto Sans SC", sans-serif;
  line-height: 1.6;
}
.wrap { max-width: 1200px; margin: 0 auto; padding: 56px 40px 80px; }
.mast {
  border-bottom: 1px solid var(--ink);
  padding-bottom: 16px;
  margin-bottom: 28px;
}
.mast .meta-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  font-size: 12px;
  color: var(--muted);
  margin: 0 0 10px;
}
h1 { font-size: 22px; font-weight: 600; margin: 0 0 8px; line-height: 1.35; }
.lede { color: var(--muted); font-size: 15px; margin: 0; max-width: 42em; }
h2 {
  font-size: 15px;
  font-weight: 600;
  margin: 36px 0 12px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
h3 { font-size: 14px; font-weight: 600; margin: 24px 0 8px; }
p { margin: 0 0 14px; }
.meta { color: var(--muted); font-size: 13px; }
.report-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 20px;
  margin: 0 0 20px;
  font-size: 13px;
  font-weight: 600;
}
.report-tabs a {
  color: var(--muted);
  text-decoration: none;
  padding-bottom: 4px;
  border-bottom: 2px solid transparent;
}
.report-tabs a.on {
  color: var(--ink);
  border-bottom-color: var(--ink);
}
.graph-wrap {
  margin: 14px 0 18px;
  padding: 12px 14px;
  background: var(--fill);
  border: 1px solid var(--line);
  overflow-x: auto;
}
.graph-wrap .graph-caption {
  font-size: 12px;
  color: var(--muted);
  margin: 0 0 8px;
}
.graph-wrap .mermaid {
  font-size: 13px;
}
/* imprint desk–style mini graph (record.html §5) */
.desk-graph-block { margin: 14px 0 18px; }
.desk-graph-block .graph-caption { font-size: 12px; color: var(--muted); margin: 0 0 8px; }
.desk-graph-stage {
  position: relative; height: 280px; border: 1px solid #2a241c;
  border-radius: 10px; overflow: hidden;
  background: radial-gradient(900px 500px at 50% 40%, #1b1712 0%, #100e0c 70%);
}
.desk-graph-stage::before {
  content: ""; position: absolute; inset: 0; pointer-events: none; opacity: 0.35;
  background-image:
    linear-gradient(rgba(196,165,116,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(196,165,116,0.05) 1px, transparent 1px);
  background-size: 48px 48px;
}
.desk-graph-stage .desk-graph-svg {
  position: absolute; inset: 0; z-index: 1;
  width: 100%; height: 100%; display: block;
}
.desk-graph-legend {
  display: flex; flex-wrap: wrap; gap: 10px 18px; margin-top: 8px;
  font-size: 11px; color: var(--muted);
}
.desk-graph-legend .edge-key { display: flex; align-items: center; gap: 6px; }
.desk-graph-legend .swatch.line {
  width: 22px; height: 0; border-top: 2px solid; flex: none;
}
.desk-graph-legend .swatch.line.super { border-color: #e07060; }
.desk-graph-legend .swatch.line.related { border-color: #d4b483; border-top-style: dashed; }
.desk-graph-legend .swatch.line.conflict { border-color: #e0a04a; border-top-width: 2.2px; }
.desk-graph-legend .swatch.line.sources { border-color: #6ec4c0; }
.desk-graph-legend .node-hint { color: var(--muted); }
.desk-graph-block .d3-link { fill: none; }
.desk-graph-block .d3-link.related { stroke: #d4b483; stroke-width: 1.35; stroke-dasharray: 5 4; opacity: 0.75; }
.desk-graph-block .d3-link.supersedes { stroke: #e07060; stroke-width: 2; opacity: 0.9; }
.desk-graph-block .d3-link.conflicts_with { stroke: #e0a04a; stroke-width: 2.2; opacity: 0.9; }
.desk-graph-block .d3-link.sources { stroke: #6ec4c0; stroke-width: 1.8; opacity: 0.85; }
.desk-graph-block .d3-node.doc-node circle { stroke-dasharray: 3 2; fill: #141a19; }
.desk-graph-block .d3-label {
  font: 10px "Helvetica Neue", Helvetica, Arial, sans-serif; fill: #f0e7d8;
  text-anchor: middle; paint-order: stroke; stroke: #100e0c; stroke-width: 3px;
  pointer-events: none;
}
.table-scroll {
  display: block;
  overflow-x: auto;
  max-width: 100%;
  margin: 12px 0 16px;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-x: contain;
}
table.kpi {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin: 12px 0 16px;
}
table.data {
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
  margin: 0;
}
table.kpi th, table.kpi td,
table.data th, table.data td {
  text-align: left;
  padding: 8px 14px 8px 0;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}
table.kpi th, table.data th {
  font-weight: 600;
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
}
table.kpi td { font-size: 15px; font-weight: 600; }
table.kpi .sub {
  display: block;
  font-size: 12px;
  font-weight: 400;
  color: var(--muted);
  margin-top: 2px;
}
table.data td.num, table.data th.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
  padding-left: 16px;
  white-space: nowrap;
}
table.data td.clip {
  white-space: nowrap;
}
table.data td.clip code {
  white-space: nowrap;
}
td.arg {
  cursor: default;
}
td.arg .short {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-bottom: 1px dotted var(--ink);
  padding-bottom: 1px;
}
td.arg:hover .short,
td.arg:focus-within .short {
  border-bottom-style: solid;
}
.pop-src { display: none; }
.arg-float {
  position: fixed;
  z-index: 80;
  display: none;
  pointer-events: auto;
}
.arg-float.on { display: block; }
.pop-card {
  width: 360px;
  background: #fff;
  color: var(--ink);
  border: 1px solid var(--ink);
  padding: 14px 16px 12px;
}
.pop-kicker {
  margin: 0 0 10px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.pop-dl {
  margin: 0;
}
.pop-dl > div {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 4px 12px;
  padding: 7px 0;
  border-top: 1px solid var(--line);
  align-items: start;
}
.pop-dl dt {
  margin: 0;
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
  padding-top: 2px;
}
.pop-dl dd {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.pop-dl dd code {
  background: var(--fill);
  padding: 2px 6px;
  font-size: 12px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
}
.pop-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
}
  margin: 10px 0 0;
  padding-top: 8px;
  border-top: 1px solid var(--line);
  font-size: 11px;
  color: var(--muted);
  line-height: 1.45;
}
.pop-foot code {
  background: none;
  padding: 0;
  color: var(--ink);
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-word;
}
table.data thead th.grp {
  text-align: center;
  color: var(--ink);
  border-bottom: 1px solid var(--ink);
  padding: 8px 14px 6px 0;
}
table.data .sep {
  border-left: 1px solid var(--ink);
  padding-left: 16px;
}
table.data.pin thead tr:first-child th:nth-child(1),
table.data.pin tbody td:nth-child(1) {
  position: sticky;
  left: 0;
  z-index: 3;
  background: #fff;
  width: 52px;
  min-width: 52px;
  max-width: 52px;
  padding: 8px 8px 8px 0;
  box-sizing: border-box;
}
table.data.pin thead tr:first-child th:nth-child(2),
table.data.pin tbody td:nth-child(2) {
  position: sticky;
  left: 52px;
  z-index: 3;
  background: #fff;
  width: 160px;
  min-width: 160px;
  max-width: 160px;
  padding: 8px 12px 8px 8px;
  box-sizing: border-box;
  overflow: hidden;
  text-overflow: ellipsis;
  border-right: 1px solid var(--ink);
}
table.data.pin thead tr:first-child th:nth-child(3),
table.data.pin tbody td:nth-child(3) {
  padding-left: 16px;
  min-width: 220px;
  max-width: 280px;
}
table.data.pin tbody td:nth-child(2) code {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
}
code {
  font-family: "SF Mono", Menlo, Consolas, monospace;
  font-size: 12px;
  background: var(--fill);
  padding: 0 3px;
}
.chart { margin: 8px 0 16px; }
.legend { font-size: 12px; color: var(--muted); margin: 0 0 6px; }
.legend span { margin-right: 16px; white-space: nowrap; }
.sw { display: inline-block; width: 16px; height: 2px; vertical-align: middle; margin-right: 6px; }
.sw-bar { width: 10px; height: 10px; }
.note, .limits {
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  padding: 12px 0;
  margin: 12px 0 16px;
  font-size: 13px;
}
ul { margin: 6px 0; padding-left: 18px; }
li { margin: 4px 0; }
.formula {
  font-family: "SF Mono", Menlo, Consolas, monospace;
  font-size: 12px;
  background: var(--fill);
  padding: 12px 14px;
  white-space: pre-wrap;
  margin: 8px 0 16px;
}
.sample-pre {
  font-family: "SF Mono", Menlo, Consolas, monospace;
  font-size: 11px;
  background: var(--fill);
  padding: 10px 12px;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 6px 0 12px;
  max-height: 320px;
  overflow: auto;
}
details.sample {
  margin: 10px 0 14px;
  font-size: 13px;
}
details.sample > summary {
  cursor: pointer;
  font-weight: 600;
  margin-bottom: 6px;
}
.comp-table td:first-child { font-weight: 600; width: 22%; }
.footer {
  margin-top: 40px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 12px;
}
.pos, .neg { font-variant-numeric: tabular-nums; }
a { color: var(--ink); }
@media print {
  .wrap { padding: 0; max-width: none; overflow-x: visible; }
  .table-scroll { overflow: visible; }
}
"""


def esc_pre(text, limit=4000):
    import html as _html
    t = text if text is not None else ""
    if len(t) > limit:
        t = t[:limit] + "\n…（截断；完整见 experiment/data/*.json）"
    return f'<pre class="sample-pre">{_html.escape(t)}</pre>'


def line_chart(xs, series, y_min, y_max, width=1120, height=280, y_unit="", x_prefix=""):
    pad_l, pad_r, pad_t, pad_b = 64, 12, 12, 36
    pw = width - pad_l - pad_r
    ph = height - pad_t - pad_b
    xmin, xmax = min(xs), max(xs)
    span = y_max - y_min or 1
    n = len(xs)
    step = 1 if n <= 12 else (2 if n <= 20 else 3)

    def X(v):
        return pad_l + (v - xmin) / (xmax - xmin) * pw

    def Y(v):
        return pad_t + (1 - (v - y_min) / span) * ph

    parts = []
    for i in range(5):
        gy = y_min + span * i / 4
        yy = Y(gy)
        parts.append(
            f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{width-pad_r}" y2="{yy:.1f}" '
            f'stroke="#ececec" stroke-width="1"/>'
        )
        label = f"{gy:,.0f}{y_unit}"
        parts.append(
            f'<text x="{pad_l-8}" y="{yy+4:.1f}" text-anchor="end" '
            f'font-size="11" fill="#555">{label}</text>'
        )
    if y_min < 0 < y_max:
        yy = Y(0)
        parts.append(
            f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{width-pad_r}" y2="{yy:.1f}" '
            f'stroke="#111" stroke-width="1"/>'
        )
    for i, x in enumerate(xs):
        if i % step and i != n - 1:
            continue
        parts.append(
            f'<text x="{X(x):.1f}" y="{height-pad_b+16:.1f}" text-anchor="middle" '
            f'font-size="11" fill="#555">{x_prefix}{x}</text>'
        )
    for _label, ys, color in series:
        pts = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in zip(xs, ys))
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" '
            f'stroke-width="1.5" stroke-linejoin="round"/>'
        )
    return "\n".join(parts)


def grouped_bar_chart(xs, series, y_max, width=1120, height=280, y_unit="", x_prefix=""):
    """Side-by-side bars per category. Categories are discrete (queries), not a series."""
    pad_l, pad_r, pad_t, pad_b = 64, 12, 12, 36
    pw = width - pad_l - pad_r
    ph = height - pad_t - pad_b
    n = len(xs)
    nser = max(len(series), 1)
    span = y_max or 1
    slot = pw / n
    inner = slot * 0.72
    bar_w = inner / nser
    step = 1 if n <= 12 else (2 if n <= 20 else 3)

    def Y(v):
        return pad_t + (1 - v / span) * ph

    parts = []
    for i in range(5):
        gy = span * i / 4
        yy = Y(gy)
        parts.append(
            f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{width-pad_r}" y2="{yy:.1f}" '
            f'stroke="#ececec" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{pad_l-8}" y="{yy+4:.1f}" text-anchor="end" '
            f'font-size="11" fill="#555">{gy:,.0f}{y_unit}</text>'
        )
    axis_y = pad_t + ph
    parts.append(
        f'<line x1="{pad_l}" y1="{axis_y:.1f}" x2="{width-pad_r}" y2="{axis_y:.1f}" '
        f'stroke="#111" stroke-width="1"/>'
    )
    for i, x in enumerate(xs):
        gx = pad_l + i * slot + (slot - inner) / 2
        for j, (_label, ys, color) in enumerate(series):
            v = ys[i] if i < len(ys) else 0
            h = (v / span) * ph
            bx = gx + j * bar_w
            by = axis_y - h
            parts.append(
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{max(bar_w - 1.2, 1):.1f}" '
                f'height="{h:.1f}" fill="{color}" stroke="#c8c8c8" stroke-width="0.6"/>'
            )
        if i % step == 0 or i == n - 1:
            cx = pad_l + i * slot + slot / 2
            parts.append(
                f'<text x="{cx:.1f}" y="{height-pad_b+16:.1f}" text-anchor="middle" '
                f'font-size="11" fill="#555">{x_prefix}{x}</text>'
            )
    return "\n".join(parts)


def legend(entries, mark="line"):
    cls = "sw sw-bar" if mark == "bar" else "sw"
    bits = []
    for title, color in entries:
        bits.append(
            f'<span><i class="{cls}" style="background:{color}"></i>{title}</span>'
        )
    return '<p class="legend">' + "".join(bits) + "</p>"


def fmt_time(s):
    return (s or "").replace("T", " ")[:16]


ARG_POP_JS = r"""
(function () {
  var layer = document.createElement("div");
  layer.className = "arg-float";
  layer.setAttribute("role", "tooltip");
  document.body.appendChild(layer);
  var hideT = 0, showT = 0, current = null;

  function clearTimers() {
    if (hideT) { clearTimeout(hideT); hideT = 0; }
    if (showT) { clearTimeout(showT); showT = 0; }
  }
  function hide() {
    clearTimers();
    layer.classList.remove("on");
    layer.innerHTML = "";
    current = null;
  }
  function place(td) {
    var src = td.querySelector(".pop-src .pop-card");
    if (!src) return;
    layer.innerHTML = "";
    layer.appendChild(src.cloneNode(true));
    layer.classList.add("on");
    var r = td.getBoundingClientRect();
    var w = layer.offsetWidth;
    var h = layer.offsetHeight;
    var left = Math.min(Math.max(12, r.left), Math.max(12, window.innerWidth - w - 12));
    var top = r.bottom + 10;
    if (top + h > window.innerHeight - 12) {
      top = Math.max(12, r.top - h - 10);
    }
    layer.style.left = left + "px";
    layer.style.top = top + "px";
  }
  function scheduleShow(td) {
    clearTimers();
    current = td;
    showT = setTimeout(function () { place(td); }, 80);
  }
  function scheduleHide() {
    clearTimers();
    hideT = setTimeout(hide, 140);
  }
  document.addEventListener("mouseover", function (e) {
    var td = e.target.closest && e.target.closest("td.arg");
    if (td) scheduleShow(td);
    else if (!e.target.closest(".arg-float")) scheduleHide();
  });
  document.addEventListener("focusin", function (e) {
    var td = e.target.closest && e.target.closest("td.arg");
    if (td) { clearTimers(); place(td); }
  });
  layer.addEventListener("mouseenter", clearTimers);
  layer.addEventListener("mouseleave", scheduleHide);
  window.addEventListener("scroll", function () {
    if (current && layer.classList.contains("on")) place(current);
  }, true);
  window.addEventListener("resize", hide);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") hide();
  });
})();
"""

REPORT_TABS = (
    ("report.html", "规范记忆", "memory"),
    ("retrieval.html", "文档检索", "retrieval"),
    ("record.html", "规则关联", "record"),
)


def report_nav(active: str) -> str:
    """Horizontal nav between experiment report tabs. `active` is memory|retrieval|record."""
    parts = []
    for href, label, key in REPORT_TABS:
        cls = ' class="on"' if key == active else ""
        parts.append(f'<a href="{href}"{cls}>{label}</a>')
    return (
        '<nav class="report-tabs" aria-label="实验报告">'
        + "".join(parts)
        + "</nav>"
    )
