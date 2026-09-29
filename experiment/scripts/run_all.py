#!/usr/bin/env python3
"""Run the full imprint token + retrieval experiment and rebuild HTML reports."""
import json
import os
import subprocess
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SCRIPTS))
DATA = os.path.join(os.path.dirname(SCRIPTS), "data")
REPORT = os.path.join(os.path.dirname(SCRIPTS), "report")
PY = sys.executable


def run(name):
    print("==>", name, flush=True)
    subprocess.check_call([PY, os.path.join(SCRIPTS, name)])


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


sys.path.insert(0, SCRIPTS)
from report_style import fmt_time


def write_index():
    token = load("summary.json")
    retr = load("retrieval_summary.json")
    link_path = os.path.join(DATA, "linking_summary.json")
    link = load("linking_summary.json") if os.path.isfile(link_path) else {}
    lf = link.get("final") or {}
    link_saved = f"{lf['saved_tokens']:,}" if lf else "—"
    link_pct = f"{lf.get('saving_pct', 0):.1f}%" if lf else "—"
    link_hit = f"{lf.get('rules_recalled', '—')}/3 场景规则召回" if lf else "—"
    prec = load("retrieval_precision.json")["canonical_precision"]
    acc = token.get("accuracy") or {}
    tf = token["final"]
    rf = retr["final"]
    rf2 = retr.get("final_k2") or {}
    created = fmt_time(token["meta"]["created_at"])
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>imprint 对照实验报告</title>
<style>
body {{
  font-family: "Helvetica Neue", Helvetica, Arial, "PingFang SC", "Hiragino Sans GB", sans-serif;
  max-width: 720px; margin: 0 auto; padding: 56px 32px 80px;
  color: #111; line-height: 1.6;
}}
.meta-row {{
  display: flex; justify-content: space-between; gap: 16px;
  font-size: 12px; color: #555; margin: 0 0 10px;
  border-bottom: 1px solid #111; padding-bottom: 12px;
}}
h1 {{ font-size: 22px; font-weight: 600; margin: 16px 0 8px; }}
p {{ color: #333; margin: 0 0 12px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; margin: 20px 0 28px; }}
th, td {{ text-align: left; padding: 8px 10px 8px 0; border-bottom: 1px solid #d0d0d0; vertical-align: top; }}
th {{ font-size: 12px; font-weight: 600; color: #555; }}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
a {{ color: #111; }}
.muted {{ color: #555; font-size: 13px; }}
</style>
</head>
<body>
<p class="meta-row"><span>imprint 对照实验</span><span>{created}</span></p>
<h1>实验报告</h1>
<p class="muted">Grok-2 分词 · 相对比较 · 对照定义与样本见各报告 §2</p>
<table>
<thead><tr><th>实验</th><th class="num">累计节约</th><th class="num">节约率</th><th>命中</th></tr></thead>
<tbody>
<tr>
  <td><a href="report.html">规范记忆</a></td>
  <td class="num">{tf['saved_tokens']:,}</td>
  <td class="num">{tf['saving_pct']:.1f}%</td>
  <td class="num">复用期 {acc.get('perfect_comply', 0)}/{acc.get('comply_rounds', 0)} 轮完全命中</td>
</tr>
<tr>
  <td><a href="retrieval.html">文档检索</a><div class="muted">k={rf.get('doc_budget', 3)}：{rf['saving_pct']:.1f}% · k=2：{rf2.get('saving_pct', '—')}%</div></td>
  <td class="num">{rf['saved_tokens']:,}</td>
  <td class="num">{rf['saving_pct']:.1f}%</td>
  <td class="num">k3 {rf.get('narrow_opened_target', '—')}/{rf.get('n_queries', 36)} · k2 {rf2.get('narrow_opened_target', '—')}/{rf.get('n_queries', 36)} Read 金标</td>
</tr>
<tr>
  <td><a href="record.html">规则关联</a><div class="muted">vault sources · find links · get 双向</div></td>
  <td class="num">{link_saved}</td>
  <td class="num">{link_pct}</td>
  <td class="num">{link_hit}{f" · 图 {lf.get('vault_checks_passed', '')}/{lf.get('vault_checks_total', '')}" if lf and lf.get('vault_checks_total') else ""}</td>
</tr>
</tbody>
</table>
<p class="muted">原始数据：experiment/data/。复现：python3 experiment/scripts/run_all.py</p>
</body>
</html>
"""
    os.makedirs(REPORT, exist_ok=True)
    path = os.path.join(REPORT, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", path)


def main():
    os.chdir(ROOT)
    run("gen_dialogues.py")
    run("docgen.py")
    run("measure.py")
    run("measure_retrieval.py")
    run("check_precision.py")
    run("measure_linking.py")
    run("build_report.py")
    run("build_retrieval_report.py")
    run("build_record_report.py")
    write_index()


if __name__ == "__main__":
    main()
