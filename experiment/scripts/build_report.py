#!/usr/bin/env python3
"""Build a plain typographic HTML report from experiment/data/*.json."""
import hashlib
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import BASE, DATA, REPORT_DIR, imprint_mcp, public_bin
from report_style import CSS, legend, line_chart, fmt_time, esc_pre, report_nav


def load(name):
    path = name if os.path.isabs(name) else os.path.join(DATA, name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


summary_json = load("summary.json")
base_json = load("baseline.json")
mem_json = load("with_memory.json")
dialogues = load(os.path.join(BASE, "dialogues.json"))

summary = summary_json["summary"]
final = summary_json["final"]
acc = summary_json.get("accuracy") or {}
rounds = [r["round"] for r in summary]
base_cum = [r["baseline_cum"] for r in summary]
mem_core = [r["memory_core_cum"] for r in summary]
mem_shelf = [r["memory_with_shelves_cum"] for r in summary]
saving_pct = [r["saving_pct"] for r in summary]

meta_d = dialogues["meta"]
rounds_build = meta_d["build_rounds"]
rounds_comply = meta_d["compliance_rounds"]
rules_total = meta_d["rules_total"]
n_rounds = meta_d["rounds"]

breakeven = next((r for r in summary if r["saving_pct"] > 0), None)
breakeven_round = breakeven["round"] if breakeven else "—"
build_pct_end = summary[rounds_build - 1]["saving_pct"]
build_pct_min = min(r["saving_pct"] for r in summary[:rounds_build])

shelf_overhead = final["memory_with_shelves_total"] - final["baseline_total"]
shelf_overhead_pct = shelf_overhead / final["baseline_total"] * 100 if final["baseline_total"] else 0
if shelf_overhead <= 0:
    shelf_cost_zh = (
        f"相对对照组仍节约 {-shelf_overhead:,} token"
        f"（{-shelf_overhead_pct:.1f}%）"
    )
else:
    shelf_cost_zh = (
        f"相对对照组增加 {shelf_overhead:,} token"
        f"（{shelf_overhead_pct:.1f}%）"
    )

TOKENIZER = summary_json["meta"]["tokenizer"]
MCP_NAME = public_bin(summary_json["meta"].get("imprint_mcp"))
try:
    SHA256 = sha256_file(imprint_mcp())
except Exception:
    SHA256 = "unavailable"

evidence = []
for rd in dialogues["rounds"]:
    for nr in rd["new_rules"]:
        evidence.append((nr["claim"], nr["scope"], nr["text"]))
ids = []
for m in mem_json["rows"]:
    ids.extend(m.get("add_rule_ids") or [])
evidence = [(rid, c, s, t) for (rid, (c, s, t)) in zip(ids, evidence)]

THEME_ZH = {
    "python": "命名与分层",
    "quality": "质量",
    "interface": "接口",
    "security": "安全",
    "testing": "测试",
    "ops": "运维",
    "review": "评审",
    "config": "配置",
}
themes_zh = "、".join(THEME_ZH.get(t, t) for t in meta_d.get("themes", [])) or "—"

y1_max = ((max(base_cum + mem_core + mem_shelf) // 500) + 1) * 500
chart1 = line_chart(rounds, [
    ("baseline", base_cum, "#1a1a1a"),
    ("imprint core", mem_core, "#5a5a5a"),
    ("imprint + shelves", mem_shelf, "#9a9a9a"),
], 0, y1_max, y_unit="")
pct_lo = min(-20, (min(saving_pct) // 20) * 20 - 20)
pct_hi = (max(saving_pct) // 20) * 20 + 20
chart2 = line_chart(rounds, [("saving %", saving_pct, "#1a1a1a")],
                    pct_lo, pct_hi, y_unit="%")

detail_rows = []
for i, r in enumerate(summary):
    m = mem_json["rows"][i]
    b = base_json["rows"][i]
    phase = "写入期" if m.get("phase") == "build" else "复用期"
    cls = "pos" if r["saving_pct"] >= 0 else "neg"
    detail_rows.append(
        f"<tr><td class='num'>{r['round']}</td><td>{phase}</td>"
        f"<td class='num'>{b['rules_in_context']}</td>"
        f"<td class='num'>{m['rules_recalled']}</td>"
        f"<td class='num'>{m.get('hit_count', '—')}/{m.get('expected_count', '—')}</td>"
        f"<td class='num'>{b['total_input_tokens']}</td>"
        f"<td class='num'>{m['core_input_tokens']}</td>"
        f"<td class='num'>{m['find_req_tokens']+m['find_rules_tokens']}</td>"
        f"<td class='num'>{m['add_req_tokens']+m['add_resp_tokens']}</td>"
        f"<td class='num {cls}'>{r['saving_pct']:+.1f}%</td></tr>"
    )

evidence_rows = "".join(
    f"<tr><td><code>{rid or '—'}</code></td><td>{claim}</td>"
    f"<td><code>{scope}</code></td><td>{text}</td></tr>"
    for rid, claim, scope, text in evidence
)

p_all = acc.get("all_rounds_mean_precision")
r_all = acc.get("all_rounds_mean_recall")
p_c = acc.get("comply_mean_precision")
r_c = acc.get("comply_mean_recall")
perfect = acc.get("perfect_comply")
comply_n = acc.get("comply_rounds")

created = fmt_time(summary_json["meta"]["created_at"])
comp = summary_json.get("meta", {}).get("comparison") or {}
samples = summary_json.get("samples") or {}
if not comp:
    comp = {
        "baseline_arm": "无 vault：每轮重复注入 dialogues 中迄今全部规范 user text 全文（【项目规范】块）。",
        "experiment_arm": "imprint vault：find 紧凑 rules + 写入期 add；不重复注入 vault 全文。",
        "excluded_from_both_arms": [
            "Cursor alwaysApply（如 imprint-memory.mdc）",
            "AGENTS.md / body.md",
        ],
        "shared_in_both_arms": "SYSTEM + 用户消息 + 任务",
        "corpus": "experiment/dialogues.json",
        "rules_source_field": "new_rules[].text",
    }
def _sample_block(key, title):
    s = samples.get(key)
    if not s:
        return ""
    b, m = s.get("baseline") or {}, s.get("memory_core") or {}
    bt, mt = b.get("tokens") or {}, m.get("tokens") or {}
    return f"""
<details class="sample" open>
  <summary>{html.escape(title)} · 第 {s.get('round')} 轮 · 对照 {bt.get('total', '—')} tok · 实验 {mt.get('core_total', '—')} tok</summary>
  <p class="meta">对照 prompt（含【项目规范】全文块）</p>
  {esc_pre((b.get('shared_prompt') or '') + (b.get('rules_injection') or ''))}
  <p class="meta">实验 find 请求</p>
  {esc_pre(m.get('find_request_json') or '')}
  <p class="meta">实验 find rules</p>
  {esc_pre(m.get('find_rules_json') or '')}
</details>"""


transparency_section = f"""
<h2>2. 对照与样本</h2>
<table class="data comp-table">
<thead><tr><th>臂</th><th>计入 prompt 的规范</th></tr></thead>
<tbody>
<tr><td>对照</td><td>{html.escape(comp.get('baseline_arm', ''))}</td></tr>
<tr><td>实验</td><td>{html.escape(comp.get('experiment_arm', ''))}</td></tr>
<tr><td>共用</td><td>{html.escape(comp.get('shared_in_both_arms', ''))}</td></tr>
<tr><td>语料</td><td><code>{html.escape(comp.get('corpus', ''))}</code> · <code>{html.escape(comp.get('rules_source_field', 'new_rules[].text'))}</code></td></tr>
<tr><td>不含</td><td>{html.escape('；'.join(comp.get('excluded_from_both_arms') or []))}</td></tr>
</tbody>
</table>
{_sample_block('last_build_round', '写入期结束')}
{_sample_block('first_comply_round', '复用期首轮')}
"""

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>规范记忆对照实验</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header class="mast">
  <p class="meta-row"><span>imprint 对照实验 · 规范记忆</span><span>{created}</span></p>
  {report_nav("memory")}
  <h1>规范记忆的输入成本与召回准确率</h1>
  <p class="lede">aurora · {n_rounds} 轮 · {rules_total} 条规范。对照/实验差异见 §2。</p>
</header>

<table class="kpi">
<tr>
  <th>累计节约<span class="sub">{n_rounds} 轮</span></th>
  <th>节约率</th>
  <th>盈亏平衡</th>
  <th>复用期完全命中</th>
</tr>
<tr>
  <td>{final['saved_tokens']:,}<span class="sub">对照 {final['baseline_total']:,} → 实验 {final['memory_core_total']:,}</span></td>
  <td>{final['saving_pct']:.1f}%</td>
  <td>第 {breakeven_round} 轮</td>
  <td>{perfect}/{comply_n}<span class="sub">精确率 {p_c:.0%} · 召回率 {r_c:.0%}</span></td>
</tr>
</table>

<h2>1. 结论</h2>
<p>第 {breakeven_round} 轮起实验累计低于对照；终局 {final['saved_tokens']:,} token（{final['saving_pct']:.1f}%）。复用期 {perfect}/{comply_n} 轮 P/R 100%（scope AND）。含 shelves 时 {shelf_cost_zh}（第三条曲线）。</p>

{transparency_section}

<h2>3. 环境与计量</h2>
<table class="data">
<thead><tr><th>项</th><th>值</th></tr></thead>
<tbody>
<tr><td>MCP</td><td><code>{MCP_NAME}</code> · <code>{SHA256[:16]}…</code></td></tr>
<tr><td>分词</td><td>{TOKENIZER}</td></tr>
<tr><td>vault</td><td><code>{summary_json['meta'].get('vault','')}</code>（跑前清空）</td></tr>
<tr><td>设计</td><td>写入 {rounds_build} 轮×2 条（{themes_zh}）→ 复用 {rounds_comply} 轮 find</td></tr>
</tbody>
</table>
<div class="formula">对照 = 共用 + 迄今规范全文
实验 core = 共用 + find(req+rules) + [写入期] add(req+resp)
含文档 = core + find.documents</div>

<h2>4. 输入成本</h2>
<h3>累计输入 token</h3>
{legend([('对照：每轮注入全文', '#1a1a1a'), ('实验：imprint', '#5a5a5a'), ('实验：含文档摘录', '#9a9a9a')])}
<div class="chart"><svg viewBox="0 0 1120 300" width="100%" xmlns="http://www.w3.org/2000/svg">{chart1}</svg></div>
<h3>累计节约率</h3>
{legend([('相对对照的节约率', '#1a1a1a')])}
<div class="chart"><svg viewBox="0 0 1120 300" width="100%" xmlns="http://www.w3.org/2000/svg">{chart2}</svg></div>
<h3>分轮明细</h3>
<div class="table-scroll">
<table class="data">
<thead><tr>
<th class="num">轮次</th><th>阶段</th><th class="num">对照携带条数</th>
<th class="num">返回条数</th><th class="num">命中 / 应召回</th>
<th class="num">对照</th><th class="num">实验</th>
<th class="num">检索</th><th class="num">写入</th><th class="num">累计节约</th>
</tr></thead>
<tbody>{''.join(detail_rows)}</tbody>
</table>
</div>

<h2>5. 召回</h2>
<table class="data">
<thead><tr><th>范围</th><th class="num">精确率</th><th class="num">召回率</th></tr></thead>
<tbody>
<tr><td>全部轮次</td><td class="num">{p_all:.1%}</td><td class="num">{r_all:.1%}</td></tr>
<tr><td>复用期</td><td class="num">{p_c:.1%}</td><td class="num">{r_c:.1%}</td></tr>
</tbody>
</table>

<h2>6. 写入语料</h2>
<div class="table-scroll">
<table class="data">
<thead><tr><th>编号</th><th>摘要</th><th>主题标签</th><th>用户原话</th></tr></thead>
<tbody>{evidence_rows}</tbody>
</table>
</div>

<h2>7. 局限</h2>
<ul class="limits">
<li>分词：Grok-2 公开编码器，仅相对比较。</li>
<li>写入期最大落后对照 {abs(build_pct_min):.1f}%，第 {rounds_build} 轮 {build_pct_end:+.1f}%。</li>
<li>应召回按 scope 标签，非人工同义表；docs/ 为合成语料。</li>
</ul>

<h2>8. 复现</h2>
<div class="formula">cd imprint-online-test
python3 -m pip install -r requirements.txt
python3 experiment/scripts/run_all.py</div>
<p class="footer">由 experiment/scripts/build_report.py 根据 experiment/data/*.json 生成。实验时间 {created}。</p>
</div>
</body>
</html>
"""

os.makedirs(REPORT_DIR, exist_ok=True)
out = os.path.join(REPORT_DIR, "report.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", out)
print("final:", final, "accuracy:", acc)
