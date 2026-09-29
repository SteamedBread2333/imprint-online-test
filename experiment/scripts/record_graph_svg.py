"""Static desk-style SVG graphs for record.html (works offline, file://)."""
from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from record_graph_data import CASE_GRAPHS

W = 560
GRAPH_LAYOUT_REV = 5
PALETTE = ["#e8c99a", "#7cb8e8", "#a8d4a0", "#d4a0c8", "#c8b890", "#90c8d4", "#d4c090"]
STATUS_STROKE = {"active": "#e8c99a", "dormant": "#7a736c", "superseded": "#7aa0c8"}
NODE_STROKE_W = 2.0

EDGE_STYLE = {
    "supersedes": ('stroke="#e07060" stroke-width="2" marker-end="url(#{marker})"'),
    "related": ('stroke="#d4b483" stroke-width="1.35" stroke-dasharray="5 4" opacity="0.75"'),
    "conflicts_with": ('stroke="#e0a04a" stroke-width="2.2" opacity="0.9"'),
    "sources": ('stroke="#6ec4c0" stroke-width="1.8" opacity="0.85"'),
}


def _canvas_h(n_nodes: int) -> int:
    return 320 if n_nodes > 5 else 280


def _scope_color(scope):
    if not scope:
        return "#e8c99a"
    s = scope[0]
    h = 2166136261
    for c in s:
        h = (h ^ ord(c)) * 16777619 & 0xFFFFFFFF
    return PALETTE[h % len(PALETTE)]


def _node_r(n: dict) -> float:
    if n.get("kind") == "document":
        return 11.0
    return 14.0


def _attach_r(n: dict) -> float:
    return _node_r(n) + NODE_STROKE_W * 0.5


def _row_x(count: int, i: int, margin: float = 64) -> float:
    if count <= 1:
        return W / 2
    return margin + (W - 2 * margin) * (i / (count - 1))


def _layout_layered(nodes, h: int):
    """Rules on top band, documents on bottom — keeps sources edges from crossing the rule chain."""
    rules = sorted(
        [n for n in nodes if n.get("kind") != "document"],
        key=lambda n: n["id"],
    )
    docs = sorted(
        [n for n in nodes if n.get("kind") == "document"],
        key=lambda n: n["id"],
    )
    pos: dict[str, tuple[float, float]] = {}
    top_y = h * 0.28
    bot_y = h * 0.74
    for i, nd in enumerate(rules):
        pos[nd["id"]] = (_row_x(len(rules), i), top_y)
    for i, nd in enumerate(docs):
        pos[nd["id"]] = (_row_x(len(docs), i, margin=56), bot_y)
    return pos


def _spring_refine(pos, edges, nodes, h: int, steps=90):
    by_id = {n["id"]: n for n in nodes}
    p = {k: [v[0], v[1]] for k, v in pos.items()}
    ids = list(p)
    rule_y, doc_y = h * 0.28, h * 0.74
    min_dist = 58
    for _ in range(steps):
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                dx, dy = p[a][0] - p[b][0], p[a][1] - p[b][1]
                dist = math.hypot(dx, dy) or 1
                if dist < min_dist:
                    push = (min_dist - dist) * 0.14
                    p[a][0] += (dx / dist) * push
                    p[a][1] += (dy / dist) * push
                    p[b][0] -= (dx / dist) * push
                    p[b][1] -= (dy / dist) * push
        for e in edges:
            a, b = e["source"], e["target"]
            if a not in p or b not in p:
                continue
            dx, dy = p[b][0] - p[a][0], p[b][1] - p[a][1]
            dist = math.hypot(dx, dy) or 1
            if e["kind"] == "sources":
                want = doc_y - rule_y
            elif e["kind"] in ("supersedes", "conflicts_with", "related"):
                want = 72 if by_id[a].get("kind") != "document" else 100
            else:
                want = 96
            pull = (dist - want) * 0.028
            p[a][0] += (dx / dist) * pull
            p[a][1] += (dy / dist) * pull
            p[b][0] -= (dx / dist) * pull
            p[b][1] -= (dy / dist) * pull
        for nid in ids:
            band_y = doc_y if by_id[nid].get("kind") == "document" else rule_y
            p[nid][1] += (band_y - p[nid][1]) * 0.18
    return {k: (v[0], v[1]) for k, v in p.items()}


def _fit_viewbox(pos: dict[str, tuple[float, float]], h: int, pad: float = 44):
    if not pos:
        return pos
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    spanx = max(maxx - minx, 120.0)
    spany = max(maxy - miny, 100.0)
    scale = min((W - 2 * pad) / spanx, (h - 2 * pad - 22) / spany, 1.35)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    return {
        k: ((v[0] - cx) * scale + W / 2, (v[1] - cy) * scale + h / 2)
        for k, v in pos.items()
    }


def _trim_segment(x1, y1, x2, y2, inset_start: float, inset_end: float):
    dx, dy = x2 - x1, y2 - y1
    dist = math.hypot(dx, dy) or 1
    if dist <= inset_start + inset_end:
        return x1, y1, x2, y2
    ux, uy = dx / dist, dy / dist
    return (
        x1 + ux * inset_start,
        y1 + uy * inset_start,
        x2 - ux * inset_end,
        y2 - uy * inset_end,
    )


def _line_endpoints(e, pos, by_id):
    x1, y1 = pos[e["source"]]
    x2, y2 = pos[e["target"]]
    r1 = _attach_r(by_id[e["source"]])
    r2 = _attach_r(by_id[e["target"]])
    if e["kind"] == "supersedes":
        r2 += 6
    return _trim_segment(x1, y1, x2, y2, r1, r2)


def _edge_bend(e, slot: int, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1
    base = min(48, length * 0.28)
    if e["kind"] == "sources":
        sign = 1 if slot % 2 == 0 else -1
        return sign * base
    if e["kind"] == "related":
        return (1 if slot % 2 else -1) * base * 0.35
    if e["kind"] == "conflicts_with":
        return base * 0.15
    return base * 0.2


def _curved_path(x1, y1, x2, y2, bend: float) -> str:
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1
    px, py = -dy / length, dx / length
    cx, cy = mx + px * bend, my + py * bend
    return f"M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}"


def _bend_slots(edges):
    """Per-edge index among same kind for alternating curve direction."""
    counts: dict[str, int] = {}
    slots = []
    for e in edges:
        k = e["kind"]
        slots.append(counts.get(k, 0))
        counts[k] = counts.get(k, 0) + 1
    return slots


def _vault_rule_id(case_id: str, n: dict, id_map: dict[str, str] | None) -> str | None:
    if not id_map or n.get("kind") == "document":
        return None
    from record_vault_map import rule_key

    return id_map.get(rule_key(case_id, n["id"]))


def _node_tip_attr(n: dict, vault_id: str | None = None) -> str:
    payload = {
        "id": vault_id or n.get("id"),
        "kind": n.get("kind", "rule"),
        "label": n.get("label"),
        "claim": n.get("claim"),
        "text": n.get("text"),
        "status": n.get("status"),
        "scope": n.get("scope"),
        "path": n.get("path"),
        "heading": n.get("heading"),
    }
    if vault_id and n.get("label"):
        payload["alias"] = n.get("label")
    cleaned = {k: v for k, v in payload.items() if v}
    return html.escape(json.dumps(cleaned, ensure_ascii=False), quote=True)


def render_case(case_id: str, id_map: dict[str, str] | None = None) -> str:
    spec = CASE_GRAPHS[case_id]
    nodes = spec["nodes"]
    edges = spec["edges"]
    h = _canvas_h(len(nodes))
    pos = _fit_viewbox(_spring_refine(_layout_layered(nodes, h), edges, nodes, h), h)
    by_id = {n["id"]: n for n in nodes}
    marker_id = f"arrow-super-{case_id.replace('_', '-')}"
    bend_slots = _bend_slots(edges)

    circles = []
    for n in nodes:
        x, y = pos.get(n["id"], (W / 2, h / 2))
        vault_id = _vault_rule_id(case_id, n, id_map)
        if vault_id:
            label = html.escape(vault_id)
        else:
            label = html.escape((n.get("label") or n["id"])[:16])
        r = _node_r(n)
        superseded = n.get("status") == "superseded"
        if n.get("kind") == "document":
            fill, stroke = "#141a19", "#6ec4c0"
            dash = ' stroke-dasharray="3 2"'
            fill_op = ""
        else:
            fill = _scope_color(n.get("scope"))
            stroke = STATUS_STROKE.get(n.get("status"), "#9a9084")
            dash = ""
            fill_op = ' fill-opacity="0.55"' if superseded else ""
        tip = _node_tip_attr(n, vault_id)
        hit = r + 8
        label_y = y + r + 12
        extra_cls = ""
        if n.get("kind") == "document":
            extra_cls = " doc-node"
        elif superseded:
            extra_cls = " superseded"
        aria = html.escape(n.get("label") or n["id"])
        circles.append(
            f'<g class="d3-node{extra_cls}" data-node-tip="{tip}">'
            f'<circle class="d3-hit" cx="{x:.1f}" cy="{y:.1f}" r="{hit}" fill="transparent" '
            f'tabindex="0" role="button" aria-label="{aria}"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{NODE_STROKE_W:g}"{dash}{fill_op} pointer-events="none"/>'
            f'<text class="d3-label" x="{x:.1f}" y="{label_y:.1f}" '
            f'text-anchor="middle" pointer-events="none">{label}</text></g>'
        )

    # Rule↔rule edges first, sources last (drawn on top within edge layer).
    draw_order = {"conflicts_with": 0, "supersedes": 1, "related": 2, "sources": 3}
    indexed = sorted(enumerate(edges), key=lambda t: draw_order.get(t[1]["kind"], 9))
    lines = []
    for orig_idx, e in indexed:
        if e["source"] not in pos or e["target"] not in pos:
            continue
        x1, y1, x2, y2 = _line_endpoints(e, pos, by_id)
        bend = _edge_bend(e, bend_slots[orig_idx], x1, y1, x2, y2)
        d = _curved_path(x1, y1, x2, y2, bend)
        st_tpl = EDGE_STYLE.get(e["kind"], 'stroke="#888"')
        st = st_tpl.format(marker=marker_id)
        lines.append(
            f'<path class="d3-link {html.escape(e["kind"])}" d="{d}" fill="none" '
            f'stroke-linecap="round" {st}/>'
        )

    inner = "\n".join(circles + lines)
    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    return f"""<svg class="desk-graph-svg" viewBox="0 0 {W} {h}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="关联图 {html.escape(case_id)}" data-graph-h="{h}" data-graph-rev="{GRAPH_LAYOUT_REV}" data-graph-built="{built}">
  <defs>
    <marker id="{marker_id}" viewBox="0 -4 8 8" refX="8" refY="0" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,-4L8,0L0,4" fill="#e07060"/>
    </marker>
  </defs>
  {inner}
</svg>"""
