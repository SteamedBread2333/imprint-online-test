#!/usr/bin/env python3
"""Build semantic.html from experiment/data/semantic_gate_summary.json."""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, REPORT_DIR
from report_style import CSS, fmt_time, report_nav

OUTCOME_ZH = {
    "blocked_duplicate": "已拒写（同政策重复）",
    "missed_duplicate": "漏写（应拒未拒）",
    "advisory_similar": "已写入，并提醒可能冲突",
    "added_ok": "已写入（无冲突提醒）",
    "false_duplicate_block": "误拒（不该当重复）",
    "unexpected": "异常",
    "seed_failed": "首条 seed 失败",
}


def load_summary():
    path = os.path.join(DATA, "semantic_gate_summary.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def outcome_label(outcome: str) -> str:
    return OUTCOME_ZH.get(outcome, outcome)


def extra_cell(mode: str, r: dict) -> str:
    """Human-facing extra column: candidates for duplicate, similar for conflict/unrelated."""
    if mode == "duplicate":
        if r.get("outcome") == "blocked_duplicate":
            n = r.get("candidate_count")
            if n is None:
                return "—"
            return str(n)
        if r.get("outcome") == "missed_duplicate":
            return "—"
        return "—"
    # conflict / unrelated: advisory only when write succeeded with similar list
    n = r.get("similar_count") or 0
    if n > 0:
        return str(n)
    return "—"


def group_table(title: str, rows: list[dict], note: str, *, mode: str) -> str:
    if mode == "duplicate":
        extra_header = "拒写命中"
        extra_hint = "（candidates，最多 3 条已有规则）"
    else:
        extra_header = "冲突提醒"
        extra_hint = "（advisory · similar 条数，仅写入成功时）"

    trs = []
    for r in rows:
        ok = r.get("ok")
        mark = "✓" if ok else "✗"
        extra = extra_cell(mode, r)
        trs.append(
            "<tr>"
            f"<td class=\"num\">{r['index']}</td>"
            f"<td>{html.escape(r['claim_a'][:80])}{'…' if len(r['claim_a']) > 80 else ''}</td>"
            f"<td>{html.escape(r['claim_b'][:80])}{'…' if len(r['claim_b']) > 80 else ''}</td>"
            f"<td>{html.escape(outcome_label(r.get('outcome', '')))}</td>"
            f"<td class=\"num\">{html.escape(extra)}</td>"
            f"<td class=\"num\">{mark}</td>"
            "</tr>"
        )
    return f"""
<h3>{html.escape(title)}</h3>
<p class="meta">{html.escape(note)}</p>
<table>
<thead><tr>
  <th>#</th><th>首条 claim</th><th>第二条 claim</th><th>结果</th>
  <th class="num">{html.escape(extra_header)}</th><th class="num">OK</th>
</tr></thead>
<tbody>
{"".join(trs)}
</tbody>
</table>
<p class="meta">「{html.escape(extra_header)}」{html.escape(extra_hint)}。拒写走 <code>candidates</code>，不会填 <code>similar</code>。</p>"""


def main():
    data = load_summary()
    meta = data["meta"]
    fin = data["final"]
    created = fmt_time(meta["created_at"])
    thr = meta.get("thresholds") or {}
    thr_line = (
        f"duplicate_threshold={thr.get('duplicate_threshold')} · "
        f"relate C/E={thr.get('relate_contradiction_min')}/{thr.get('relate_entailment_min')} · "
        f"high_cos_block={thr.get('duplicate_high_cosine_block')}"
    )

    head_stats = f"""
<table>
<thead><tr><th>组别</th><th class="num">通过</th><th class="num">说明</th></tr></thead>
<tbody>
<tr>
  <td>duplicate（同政策改述）</td>
  <td class="num">{fin['duplicate_blocked']}/{fin['duplicate_total']}</td>
  <td>第二笔应拒写；命中条数见下方 candidates 列</td>
</tr>
<tr>
  <td>conflict（对立政策）</td>
  <td class="num">{fin['conflict_passed']}/{fin['conflict_total']}</td>
  <td>不得误拒 · 误拒 {fin['conflict_false_block']} · 有冲突提醒 {fin['conflict_advisory']}</td>
</tr>
<tr>
  <td>unrelated（无关主题）</td>
  <td class="num">{fin['unrelated_passed']}/{fin['unrelated_total']}</td>
  <td>不得误拒 · 误拒 {fin['unrelated_false_block']}</td>
</tr>
</tbody>
</table>
"""

    groups = data.get("groups") or {}
    sections = [
        group_table(
            "Duplicate · 20 对",
            groups.get("duplicate") or [],
            "词面 Jaccard 常低于 0.82；依赖 embed 余弦 + relate entail 拒写重复规则。",
            mode="duplicate",
        ),
        group_table(
            "Conflict · 20 对（极性 / 对立）",
            groups.get("conflict") or [],
            "第二笔应写入；语义近但 NLI 对立时，成功 JSON 的 similar 列表提醒 agent 后续 link --conflicts。",
            mode="conflict",
        ),
        group_table(
            "Unrelated · 20 对",
            groups.get("unrelated") or [],
            "不同主题；第二笔应正常 add。通常无 similar 提醒（表中为 —）。",
            mode="unrelated",
        ),
    ]

    status = "通过" if fin.get("passed") else "未通过"
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>语义写闸 · imprint 对照实验</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="mast">
    <p class="meta-row"><span>imprint 对照实验</span><span>{html.escape(created)}</span></p>
    <h1>语义写闸（embed + relate）</h1>
    <p class="lede">隔离 vault 上对 calibration 样本跑真实 <code>imprint add</code>；sidecar 样本见 imprint-embed-sidecar <code>samples.py</code>。总体：{html.escape(status)}。</p>
  </header>
  {report_nav("semantic")}
  <h2>§1 汇总</h2>
  <p class="meta">二进制 {html.escape(meta.get('imprint_bin', 'imprint'))} · {html.escape(meta.get('embed_url', ''))} · {html.escape(thr_line)}</p>
  {head_stats}
  <h2>§2 怎么读结果</h2>
  <ul>
    <li><strong>duplicate</strong>：第二次 <code>add</code> 失败 →「已拒写」；像哪条规则在错误 JSON 的 <code>candidates</code> 里（表里「拒写命中」条数，非 similar）。</li>
    <li><strong>conflict</strong>：第二次成功写入；若「冲突提醒」为 1–3，表示 <code>similar</code> advisory，需 agent/用户决定是否 <code>link --conflicts</code>。</li>
    <li><strong>unrelated</strong>：第二次正常入库；「—」表示无 advisory。</li>
  </ul>
  <h2>§3 逐对明细</h2>
  {"".join(sections)}
  <p class="meta">复现：sidecar <code>ready</code> 后 <code>python3 experiment/scripts/run_all.py</code>。</p>
</div>
</body>
</html>
"""
    os.makedirs(REPORT_DIR, exist_ok=True)
    out_path = os.path.join(REPORT_DIR, "semantic.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
