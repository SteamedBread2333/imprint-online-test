#!/usr/bin/env python3
"""Build record.html — vault ↔ shelves linking scenarios."""
import html
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, LINK_VAULT, PROJECT, REPORT_DIR
from report_style import CSS, report_nav, fmt_time, esc_pre
from record_graph_data import CASE_GRAPHS
from record_graph_svg import render_case
from record_vault_map import bench_key, load_id_map, resolve, rule_key

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

DESK_LEGEND = """
<div class="desk-graph-legend">
  <span class="node-hint">实点=规则 · 虚线圆=文档 · 颜色=scope</span>
  <span class="edge-key"><span class="swatch line super"></span>supersedes</span>
  <span class="edge-key"><span class="swatch line related"></span>related</span>
  <span class="edge-key"><span class="swatch line conflict"></span>conflicts_with</span>
  <span class="edge-key"><span class="swatch line sources"></span>sources</span>
</div>"""


def desk_graph(case_id: str, caption: str, id_map: dict[str, str]) -> str:
    svg = render_case(case_id, id_map)
    return f"""
<div class="desk-graph-block">
  <p class="graph-caption">{html.escape(caption)}</p>
  <div class="desk-graph-stage">{svg}</div>
  {DESK_LEGEND}
</div>"""


def _R(id_map: dict[str, str], case: str, node: str) -> str:
    return resolve(id_map, rule_key(case, node), f"{case}:{node}")


def id_map_section(id_map: dict[str, str]) -> str:
    if not id_map:
        return (
            f"<p class=\"meta\">未找到 <code>{html.escape(LINK_VAULT)}/state/record-vault-seed.json</code>。"
            "运行 <code>python3 experiment/scripts/measure_linking.py</code>（或 seed）后重建本页；"
            "节点标签与 desk 使用同一 vault id。</p>"
        )
    rows = []
    for case_id in sorted(CASE_GRAPHS.keys()):
        for n in CASE_GRAPHS[case_id]["nodes"]:
            if n.get("kind") == "document":
                continue
            key = rule_key(case_id, n["id"])
            vid = id_map.get(key)
            if not vid:
                continue
            alias = html.escape(n.get("label") or n["id"])
            rows.append(
                f"<tr><td>{html.escape(case_id)}</td><td>{alias}</td>"
                f"<td><code>{html.escape(vid)}</code></td></tr>"
            )
    if not rows:
        return ""
    return f"""
<p class="meta">节点标签与 hover 中的 <code>id</code> 为 <code>{html.escape(LINK_VAULT)}</code> 内真实规则 id（与 desk / §3–§4 一致）；别名为叙事用名。</p>
<table class="data comp-table">
<thead><tr><th>案例</th><th>别名</th><th>vault id（desk）</th></tr></thead>
<tbody>
{"".join(rows)}
</tbody>
</table>"""


def build_complex_cases(id_map: dict[str, str]) -> str:
    A = lambda node: _R(id_map, "case_a", node)
    B = lambda node: _R(id_map, "case_b", node)
    C = lambda node: _R(id_map, "case_c", node)
    D = lambda node: _R(id_map, "case_d", node)
    E = lambda node: _R(id_map, "case_e", node)
    cap = "节点圆上文字 = vault 规则 id（与 imprint desk 相同）· 文档仍为 path 文件名"
    return f"""
<article class="scenario">
  <h3>案例 A · 事故后改灰度政策（supersedes + sources + 宽 grep）</h3>
  {desk_graph("case_a", cap + " · 仅 deployment 有 sources", id_map)}
  <p><strong>背景</strong> 线上一次灰度回滚拖了 40 分钟。事后口头约定变了，但 <code>docs/08-deployment.md</code>、<code>docs/03-error-handling.md</code>、<code>docs/13-review.md</code> 里仍都能搜到「灰度」「回滚」。</p>
  <p><strong>写入</strong> 对旧规则 <code>{html.escape(A("r-old"))}</code> 做 <code>supersede</code> → 现行 <code>{html.escape(A("r-new"))}</code>；<code>sources</code> 只钉 <code>08-deployment.md#灰度发布</code>。</p>
  <p><strong>编码前</strong> 用户：「灰度失败现在到底怎么回滚？」→ grep 3 篇 → indexed &gt; k → <code>find(paths, …)</code>。</p>
  <p><strong>imprint 行为</strong> find 召回现行规则；<code>get {html.escape(A("r-new"))}</code> 看 <code>resolved_sources</code>。</p>
</article>

<article class="scenario">
  <h3>案例 B · 下单链路：HTTP 重试 vs POST 幂等 vs 队列死信</h3>
  {desk_graph("case_b", cap, id_map)}
  <ul>
    <li><code>{html.escape(B("r-retry"))}</code>：HTTP 重试 ×3 · sources → 16-http-client</li>
    <li><code>{html.escape(B("r-post"))}</code>：禁止 POST 重试 · <code>conflicts_with</code> → {html.escape(B("r-retry"))}</li>
    <li><code>{html.escape(B("r-dlq"))}</code>：DLQ · <code>related</code> → {html.escape(B("r-post"))}</li>
  </ul>
</article>

<article class="scenario">
  <h3>案例 C · 用户纠错 + supersede 继承</h3>
  {desk_graph("case_c", cap, id_map)}
  <p><strong>写入</strong> <code>supersede {html.escape(C("r-old"))}</code> → <code>{html.escape(C("r-new"))}</code>；双 <code>sources</code>（database + api）。</p>
</article>

<article class="scenario">
  <h3>案例 D · 组合检索噪声 + 规则定锚</h3>
  {desk_graph("case_d", cap, id_map)}
  <p><strong>vault</strong> <code>{html.escape(D("r-cache"))}</code> sources → performance；<code>{html.escape(D("r-flag"))}</code> related → cache。</p>
</article>

<article class="scenario">
  <h3>案例 E · 发版门禁（related + 多 sources）</h3>
  {desk_graph("case_e", cap, id_map)}
  <p><strong>图</strong> <code>{html.escape(E("r-ruff"))}</code> related <code>{html.escape(E("r-log"))}</code>；<code>{html.escape(E("r-cap"))}</code> related <code>{html.escape(E("r-lim"))}</code>。</p>
</article>"""


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def _rule_id_cell(_id_map: dict[str, str], _scenario_id: str, snapshot_id: str) -> str:
    """§3–§4 ids come from the same run as link-bench vault (measure_linking.py)."""
    return f"<code>{html.escape(snapshot_id or '—')}</code>"


def vault_row_html(r, id_map: dict[str, str]):
    c, l = r["control"], r["linked"]
    check = "通过" if r.get("checks_passed") else "未通过"
    extra = ""
    if r["id"] == "v1_supersede":
        old_d = resolve(id_map, "bench:v1_supersede:old", l.get("dormant_rule_id") or "")
        new_d = resolve(id_map, "bench:v1_supersede:new", l.get("active_rule_id") or "")
        extra = (
            f"desk 旧 <code>{html.escape(old_d)}</code> · 新 <code>{html.escape(new_d)}</code> · "
            f"旧进 find：{'是' if l.get('old_recalled') else '否'} · "
            f"新进 find：{'是' if l.get('new_recalled') else '否'}"
        )
    elif r["id"] == "v2_conflicts":
        ids = l.get("rule_ids") or []
        a = ids[0] if len(ids) > 0 else resolve(id_map, "bench:v2_conflicts:a", "")
        b = ids[1] if len(ids) > 1 else resolve(id_map, "bench:v2_conflicts:b", "")
        extra = (
            f"<code>{html.escape(a)}</code> ↔ <code>{html.escape(b)}</code> · "
            f"conflict_set {len(l.get('conflict_set') or [])} 条"
        )
    elif r["id"] == "v3_related":
        rel = resolve(id_map, rule_key("case_e", "r-ruff"), l.get("rule_id") or "")
        extra = f"desk related · <code>{html.escape(rel)}</code>"
    sample = json.dumps(
        {"find_args": r.get("find_args"), "linked": l},
        ensure_ascii=False,
        indent=2,
    )
    return f"""
<section class="scenario">
  <h3>{html.escape(r['title'])}</h3>
  <p class="meta">{html.escape(r['advantage'])}</p>
  <p><strong>用户</strong> {html.escape(r['user_message'])}</p>
  <table class="data">
  <tr><td>对照</td><td>{html.escape(c.get('description', ''))}</td>
      <td class="num">{c.get('tokens', 0):,} tok</td></tr>
  <tr><td>实验</td><td>{html.escape(l.get('description', ''))}</td>
      <td class="num">{l.get('tokens', 0):,} tok</td></tr>
  </table>
  <p class="meta">断言 {check} · {extra}</p>
  <details class="sample"><summary>JSON</summary>{esc_pre(sample)}</details>
</section>"""


def row_html(r, id_map: dict[str, str]):
    c, l = r["control"], r["linked"]
    audit = r.get("audit") or {}
    audit_bits = []
    if audit.get("get_rule"):
        rs = audit["get_rule"].get("resolved_sources") or []
        audit_bits.append(f"get 规则 · resolved_sources {len(rs)} 条")
    if audit.get("get_chunk"):
        rr = audit["get_chunk"].get("referenced_rules") or []
        audit_bits.append(f"get chunk · referenced_rules {len(rr)} 条")
    audit_line = " · ".join(audit_bits) if audit_bits else "—"

    read_ctrl = ", ".join(html.escape(p.split("/")[-1]) for p in c["paths"])
    read_link = ", ".join(html.escape(p.split("/")[-1]) for p in l["read_paths"]) if l["read_paths"] else "（仅 find，无 Read）"
    kinds = ", ".join(f"<code>{html.escape(k)}</code>" for k in l.get("link_kinds") or []) or "—"

    sample = compact_sample(r)
    return f"""
<section class="scenario">
  <h3>{html.escape(r['title'])}</h3>
  <p class="meta">{html.escape(r['advantage'])}</p>
  <p><strong>用户</strong> {html.escape(r['user_message'])}</p>
  <table class="data">
  <thead><tr>
    <th></th><th class="num">输入 tok</th><th>Read</th><th>关联信号</th>
  </tr></thead>
  <tbody>
  <tr>
    <td>对照（无关联）</td>
    <td class="num">{c['tokens']:,}</td>
    <td>{read_ctrl}</td>
    <td>—</td>
  </tr>
  <tr>
    <td>实验（vault+find）</td>
    <td class="num">{l['tokens']:,}</td>
    <td>{read_link}</td>
    <td>规则 {_rule_id_cell(id_map, r['id'], r.get('rule_id') or '')} · links {l['find_links_count']}（{kinds}）· 召回 {'是' if r['rule_recalled'] else '否'}</td>
  </tr>
  </tbody>
  </table>
  <p class="meta">节约 {r['saved_tokens']:,} tok（{r['saving_pct']:.1f}%）· 审计 {audit_line}</p>
  {sample}
</section>"""


def compact_sample(r):
    l = r["linked"]
    blob = json.dumps(
        {
            "find_args": r["find_args"],
            "rules": l.get("rules_sample"),
            "documents": l.get("documents_sample"),
            "links": l.get("links_sample"),
            "audit": r.get("audit"),
        },
        ensure_ascii=False,
        indent=2,
    )
    return f"<details class='sample'><summary>find / get 样本 JSON</summary>{esc_pre(blob)}</details>"


try:
    data = load("linking_summary.json")
except FileNotFoundError:
    data = None

id_map = load_id_map()

if not data:
    body = vault_body = "<p class='meta'>缺少 linking_summary.json — 请运行 measure_linking.py</p>"
    fin = {}
    comp = {}
    created = "—"
else:
    fin = data["final"]
    comp = data.get("comparison") or {}
    created = fmt_time(data["meta"]["created_at"])
    body = "".join(row_html(r, id_map) for r in data["rows"])
    vault_body = "".join(vault_row_html(r, id_map) for r in data.get("vault_rows") or [])
    if not vault_body:
        vault_body = "<p class='meta'>无 vault↔vault 场景 — 请重新运行 measure_linking.py</p>"

complex_cases = build_complex_cases(id_map)
id_table = id_map_section(id_map)
desk_vault = os.path.join(PROJECT, LINK_VAULT)

html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>规则关联对照实验</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header class="mast">
  <p class="meta-row"><span>imprint 对照实验 · 规则关联</span><span>{created}</span></p>
  {report_nav("record")}
  <h1>Vault 关联：文档与规则图</h1>
  <p class="lede">§3 规则↔文档（sources）；§4 规则↔规则（supersedes / conflicts_with / related）。与纯 BM25 检索、无 graph 的 prompt 堆叠对照。</p>
</header>

<table class="kpi">
<tr>
  <th>规则↔文档 · 累计节约</th>
  <th>节约率</th>
  <th>规则↔规则 · 断言</th>
</tr>
<tr>
  <td>{fin.get('saved_tokens', 0):,}<span class="sub">对照 {fin.get('control_total', 0):,} → 实验 {fin.get('linked_total', 0):,}</span></td>
  <td>{fin.get('saving_pct', 0)}%</td>
  <td>{fin.get('vault_checks_passed', 0)}/{fin.get('vault_checks_total', 0)} 通过</td>
</tr>
</table>

<h2>1. 两类持久关联</h2>
<h3>规则 ↔ 文档（shelves）</h3>
<ul>
<li><code>sources</code>：规则 → 文档；<code>get r-…</code> → <code>resolved_sources</code>。</li>
<li><code>find.links</code>（当次）：<code>sources</code> / <code>co_search</code>；chunk <code>get</code> → <code>referenced_rules</code>。</li>
</ul>
<h3>规则 ↔ 规则（vault graph）</h3>
<ul>
<li><code>supersedes</code>：新政策 → 旧政策（旧 dormant，find 默认不召回）。</li>
<li><code>conflicts_with</code>：相反政策共存；<code>find</code> 返回 <code>conflict_set</code>，并对较弱一侧降权。</li>
<li><code>related</code>：相关但不替代；<code>get</code> / desk <code>/</code>、<code>/unified</code> 看图。</li>
<li><code>referenced_by</code>：谁指向我（<code>get r-…</code> 自动）。</li>
</ul>

<h2>2. 对照定义（规则↔文档）</h2>
<table class="data comp-table">
<tbody>
<tr><td>对照</td><td>{html.escape(comp.get('baseline_arm', ''))}</td></tr>
<tr><td>实验</td><td>{html.escape(comp.get('experiment_arm', ''))}</td></tr>
<tr><td>文档链</td><td>{html.escape(comp.get('link_types_doc') or comp.get('link_types', ''))}</td></tr>
<tr><td>规则图</td><td>{html.escape(comp.get('link_types_vault', ''))}</td></tr>
</tbody>
</table>

<h2>3. 场景 · 规则 ↔ 文档</h2>
{body}

<h2>4. 场景 · 规则 ↔ 规则</h2>
{vault_body}

<h2>5. 复杂实际案例（叙事 + desk 关系图）</h2>
{id_table}
{complex_cases}

<h2>6. 与另两项实验的关系</h2>
<p class="meta"><a href="report.html">规范记忆</a> 测 vault 规则复用 token；<a href="retrieval.html">文档检索</a> 测 grep+find 收窄 Read。本页 §3–§5 与 desk 共用 <code>{html.escape(LINK_VAULT)}</code>（<code>imprint.yaml</code> 的 <code>vault:</code> · 跑 <code>measure_linking.py</code>）。</p>

<p class="footer">由 experiment/scripts/build_record_report.py 生成 · 图 layout rev {html.escape(str(__import__("record_graph_svg").GRAPH_LAYOUT_REV))} · {html.escape(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))}</p>
</div>
<div id="graph-node-tip" hidden aria-live="polite"></div>
"""

with open(os.path.join(SCRIPTS_DIR, "record_graph_tooltip.js"), encoding="utf-8") as _tf:
    _tip_js = _tf.read()
html_doc += f"""
<script>{_tip_js}</script>
</body>
</html>
"""

os.makedirs(REPORT_DIR, exist_ok=True)
out = os.path.join(REPORT_DIR, "record.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html_doc)
print("wrote", out)
