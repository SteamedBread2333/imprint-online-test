"""Static desk-style SVG graphs for record.html (works offline, file://)."""
from __future__ import annotations

import html
import math
from record_graph_data import CASE_GRAPHS

W, H = 560, 280
CX, CY = W / 2, H / 2

EDGE_STYLE = {
    "supersedes": ('stroke="#e07060" stroke-width="2" marker-end="url(#arrow-super)"'),
    "related": ('stroke="#d4b483" stroke-width="1.35" stroke-dasharray="5 4" opacity="0.75"'),
    "conflicts_with": ('stroke="#e0a04a" stroke-width="2.2" opacity="0.9"'),
    "sources": ('stroke="#6ec4c0" stroke-width="1.8" opacity="0.85"'),
}

PALETTE = ["#e8c99a", "#7cb8e8", "#a8d4a0", "#d4a0c8", "#c8b890", "#90c8d4", "#d4c090"]
STATUS_STROKE = {"active": "#e8c99a", "dormant": "#7a736c", "superseded": "#7aa0c8"}


def _scope_color(scope):
    if not scope:
        return "#e8c99a"
    s = scope[0]
    h = 2166136261
    for c in s:
        h = (h ^ ord(c)) * 16777619 & 0xFFFFFFFF
    return PALETTE[h % len(PALETTE)]


def _layout(nodes, edges):
    n = len(nodes)
    if n == 0:
        return {}
    by_id = {nd["id"]: nd for nd in nodes}
    adj = {nd["id"]: set() for nd in nodes}
    for e in edges:
        if e["source"] in adj and e["target"] in adj:
            adj[e["source"]].add(e["target"])
            adj[e["target"]].add(e["source"])
    start = nodes[0]["id"]
    depth = {start: 0}
    q = [start]
    while q:
        u = q.pop(0)
        for v in adj[u]:
            if v not in depth:
                depth[v] = depth[u] + 1
                q.append(v)
    for nd in nodes:
        depth.setdefault(nd["id"], 1)
    layers: dict[int, list] = {}
    for nd in nodes:
        layers.setdefault(depth[nd["id"]], []).append(nd["id"])
    pos = {}
    max_d = max(layers)
    for d, ids in layers.items():
        ring_r = 55 + d * 52
        k = len(ids)
        for i, nid in enumerate(ids):
            ang = (2 * math.pi * i / k) - math.pi / 2
            pos[nid] = (CX + ring_r * math.cos(ang), CY + ring_r * math.sin(ang))
    return pos


def _spring_refine(pos, edges, steps=80):
    p = {k: [v[0], v[1]] for k, v in pos.items()}
    ids = list(p)
    for _ in range(steps):
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                dx, dy = p[a][0] - p[b][0], p[a][1] - p[b][1]
                dist = math.hypot(dx, dy) or 1
                if dist < 70:
                    push = (70 - dist) * 0.08
                    p[a][0] += (dx / dist) * push
                    p[b][0] -= (dx / dist) * push
                    p[a][1] += (dy / dist) * push
                    p[b][1] -= (dy / dist) * push
        for e in edges:
            a, b = e["source"], e["target"]
            if a not in p or b not in p:
                continue
            dx, dy = p[b][0] - p[a][0], p[b][1] - p[a][1]
            dist = math.hypot(dx, dy) or 1
            pull = (dist - 90) * 0.04
            p[a][0] += (dx / dist) * pull
            p[a][1] += (dy / dist) * pull
            p[b][0] -= (dx / dist) * pull
            p[b][1] -= (dy / dist) * pull
    return {k: (v[0], v[1]) for k, v in p.items()}


def _fit_viewbox(pos: dict[str, tuple[float, float]], pad: float = 40) -> dict[str, tuple[float, float]]:
    if not pos:
        return pos
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    spanx = max(maxx - minx, 1.0)
    spany = max(maxy - miny, 1.0)
    scale = min((W - 2 * pad) / spanx, (H - 2 * pad) / spany, 1.8)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    return {
        k: ((v[0] - cx) * scale + CX, (v[1] - cy) * scale + CY)
        for k, v in pos.items()
    }


def render_case(case_id: str) -> str:
    spec = CASE_GRAPHS[case_id]
    nodes = spec["nodes"]
    edges = spec["edges"]
    pos = _fit_viewbox(_spring_refine(_layout(nodes, edges), edges))
    by_id = {n["id"]: n for n in nodes}

    lines = []
    for e in edges:
        if e["source"] not in pos or e["target"] not in pos:
            continue
        x1, y1 = pos[e["source"]]
        x2, y2 = pos[e["target"]]
        st = EDGE_STYLE.get(e["kind"], 'stroke="#888"')
        lines.append(
            f'<line class="d3-link {html.escape(e["kind"])}" x1="{x1:.1f}" y1="{y1:.1f}" '
            f'x2="{x2:.1f}" y2="{y2:.1f}" fill="none" {st}/>'
        )

    circles = []
    for n in nodes:
        x, y = pos.get(n["id"], (CX, CY))
        label = html.escape((n.get("label") or n["id"])[:16])
        if n.get("kind") == "document":
            fill, stroke = "#141a19", "#6ec4c0"
            r = 11
            dash = ' stroke-dasharray="3 2"'
        else:
            fill = _scope_color(n.get("scope"))
            stroke = STATUS_STROKE.get(n.get("status"), "#9a9084")
            r = 10 if n.get("status") == "superseded" else 14
            dash = ""
        circles.append(
            f'<g class="d3-node{" doc-node" if n.get("kind") == "document" else ""}">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="2"{dash}/>'
            f'<text class="d3-label" x="{x:.1f}" y="{y + r + 11:.1f}" '
            f'text-anchor="middle">{label}</text></g>'
        )

    inner = "\n".join(lines + circles)
    return f"""<svg class="desk-graph-svg" viewBox="0 0 {W} {H}" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="关联图 {html.escape(case_id)}">
  <defs>
    <marker id="arrow-super" viewBox="0 -4 8 8" refX="14" refY="0" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,-4L8,0L0,4" fill="#e07060"/>
    </marker>
  </defs>
  {inner}
</svg>"""
