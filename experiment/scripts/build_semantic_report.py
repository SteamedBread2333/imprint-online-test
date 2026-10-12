#!/usr/bin/env python3
"""Build semantic.html from experiment/data/semantic_gate_summary.json."""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, REPORT_DIR
from report_style import CSS, esc_pre, fmt_time, report_nav


def load_summary():
    path = os.path.join(DATA, "semantic_gate_summary.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def group_table(title: str, rows: list[dict], note: str) -> str:
    trs = []
    for r in rows:
        outcome = r.get("outcome", "")
        ok = r.get("ok")
        mark = "✓" if ok else "✗"
        trs.append(
            "<tr>"
            f"<td class=\"num\">{r['index']}</td>"
            f"<td>{html.escape(r['claim_a'][:80])}{'…' if len(r['claim_a']) > 80 else ''}</td>"
            f"<td>{html.escape(r['claim_b'][:80])}{'…' if len(r['claim_b']) > 80 else ''}</td>"
            f"<td><code>{html.escape(outcome)}</code></td>"
            f"<td class=\"num\">{r.get('similar_count', '—')}</td>"
            f"<td class=\"num\">{mark}</td>"
            "</tr>"
        )
    return f"""
<h3>{html.escape(title)}</h3>
<p class="meta">{html.escape(note)}</p>
<table>
<thead><tr>
  <th>#</th><th>首条 claim</th><th>第二条 claim</th><th>结果</th><th class="num">similar</th><th class="num">OK</th>
</tr></thead>
<tbody>
{"".join(trs)}
</tbody>
</table>"""


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
  <td>第二笔 <code>add</code> 应 <code>code: duplicate</code> · recall {fin['duplicate_recall_pct']:.1f}%</td>
</tr>
<tr>
  <td>conflict（对立政策）</td>
  <td class="num">{fin['conflict_passed']}/{fin['conflict_total']}</td>
  <td>不得误拦 duplicate · 误拦 {fin['conflict_false_block']} · advisory(similar) {fin['conflict_advisory']}</td>
</tr>
<tr>
  <td>unrelated（无关主题）</td>
  <td class="num">{fin['unrelated_passed']}/{fin['unrelated_total']}</td>
  <td>不得误拦 duplicate · 误拦 {fin['unrelated_false_block']}</td>
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
        ),
        group_table(
            "Conflict · 20 对（极性 / 对立）",
            groups.get("conflict") or [],
            "第二笔应写入成功；高 contradiction 时出现在 similar 列表（advisory），供 agent 后续 link --conflicts。",
        ),
        group_table(
            "Unrelated · 20 对",
            groups.get("unrelated") or [],
            "不同主题；第二笔应正常 add，且不得 duplicate 误拦。",
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
  <h2>§2 样本与期望</h2>
  <ul>
    <li><strong>duplicate</strong>：同政策不同措辞 → 写闸拒写（duplicate）。</li>
    <li><strong>conflict</strong>：互斥政策 → 不得当 duplicate；常带 <code>similar</code> advisory。</li>
    <li><strong>unrelated</strong>：无关句对 → 两次均可入库。</li>
  </ul>
  <p class="meta">复现：sidecar <code>ready</code> 后 <code>python3 experiment/scripts/run_all.py</code>（或单独 <code>measure_semantic_gate.py</code>）。</p>
  <h2>§3 逐对明细</h2>
  {"".join(sections)}
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
