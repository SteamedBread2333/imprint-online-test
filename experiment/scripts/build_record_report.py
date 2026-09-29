#!/usr/bin/env python3
"""Build record.html — vault ↔ shelves linking scenarios."""
import html
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, REPORT_DIR
from report_style import CSS, report_nav, fmt_time, esc_pre
from record_graph_data import CASE_GRAPHS
from record_graph_svg import render_case

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

DESK_LEGEND = """
<div class="desk-graph-legend">
  <span class="node-hint">实点=规则 · 虚线圆=文档 · 颜色=scope</span>
  <span class="edge-key"><span class="swatch line super"></span>supersedes</span>
  <span class="edge-key"><span class="swatch line related"></span>related</span>
  <span class="edge-key"><span class="swatch line conflict"></span>conflicts_with</span>
  <span class="edge-key"><span class="swatch line sources"></span>sources</span>
</div>"""


def desk_graph(case_id: str, caption: str) -> str:
    svg = render_case(case_id)
    return f"""
<div class="desk-graph-block">
  <p class="graph-caption">{html.escape(caption)}</p>
  <div class="desk-graph-stage">{svg}</div>
  {DESK_LEGEND}
</div>"""


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


# Narrative only — desk-style unified graph per case (§5).
COMPLEX_CASES_HTML = f"""
<article class="scenario">
  <h3>案例 A · 事故后改灰度政策（supersedes + sources + 宽 grep）</h3>
  {desk_graph("case_a", "imprint desk 统一视图风格 · 仅 deployment 有 sources；error/review 为 grep 宽命中、图中无 vault 边")}
  <p><strong>背景</strong> 线上一次灰度回滚拖了 40 分钟。事后口头约定变了，但 <code>docs/08-deployment.md</code>、<code>docs/03-error-handling.md</code>、<code>docs/13-review.md</code> 里仍都能搜到「灰度」「回滚」。</p>
  <p><strong>写入</strong> 对旧规则 <code>r-…-canary-v1</code> 做 <code>supersede</code>，新 claim 写清「自动回滚触发条件与审批」；<code>sources</code> 只钉 <code>08-deployment.md#灰度发布</code>（不是 review 里的 checklist）。</p>
  <p><strong>编码前</strong> 用户：「灰度失败现在到底怎么回滚？」→ grep 3 篇 → indexed &gt; k → <code>find(paths, query=canary rollback, query_local=灰度发布 回滚)</code>。</p>
  <p><strong>imprint 行为</strong> find 召回<strong>现行</strong>规则（旧 v1 已 dormant 不进 top）；<code>links.sources</code> 指向 deployment chunk；Read 交集往往只需 deployment 一篇。agent 按 claim 写流水线，细节以 <code>get r-…</code> 的 <code>resolved_sources</code> 核对，不必三篇全文进 context。</p>
  <p><strong>若无关联</strong> 要么三篇全 Read，要么 BM25 把 review 放第一导致 checklist 当权威 — 和真实「部署节唯一来源」不一致。</p>
</article>

<article class="scenario">
  <h3>案例 B · 下单链路：HTTP 重试 vs POST 幂等 vs 队列死信（conflicts + related + 多 sources）</h3>
  {desk_graph("case_b", "desk /unified：conflicts_with 橙实线 · related 金虚线 · 各规则 sources 到 doc")}
  <p><strong>背景</strong> 三条政策同时有效、互相牵制：</p>
  <ul>
    <li><code>r-http-retry</code>：出站 HTTP 默认最多重试 3 次（出处 <code>16-http-client.md</code>）</li>
    <li><code>r-no-post-retry</code>：非幂等 POST 禁止自动重试（出处 <code>05-api-design.md</code>），<code>conflicts_with → r-http-retry</code></li>
    <li><code>r-dlq</code>：异步消费失败进 DLQ、可见性超时 &gt; 最坏处理时间（出处 <code>12-concurrency.md</code>），<code>related → r-no-post-retry</code>（「同步 HTTP 不重试、异步走队列」）</li>
  </ul>
  <p><strong>用户</strong> 「支付回调 POST 超时了，客户端要自动重试吗？后台 Job 又怎么兜？」</p>
  <p><strong>一次 find</strong> <code>scope=aurora,http</code>（或更宽）+ query → 召回 2～3 条 active 规则 + <strong><code>conflict_set</code></strong>（retry  vs no-post-retry）。agent 必须先向用户确认场景：<strong>同步 POST</strong> 走 B，<strong>已进队列</strong> 走 C；不能只看 BM25 第一条。</p>
  <p><strong>文档</strong> 每条规则自带 <code>sources</code>；需要原文时 Read 1～2 篇金标节，而不是 grep「重试」命中的 5 篇（config / observability / http / api / concurrency）全读。</p>
  <p><strong>desk</strong> 发版前在 <code>/unified</code> 看三角边 + 文档 cross-edge，评审是否漏链。</p>
</article>

<article class="scenario">
  <h3>案例 C · 用户纠错 + 继承（supersede 继承 sources/query_local + 审计链）</h3>
  {desk_graph("case_c", "supersedes 箭头 · 新规则双 sources（database + api）")}
  <p><strong>背景</strong> 早期规则「时间戳存 UTC ISO8601 字符串」(<code>r-ts-iso</code>)，<code>sources</code> 指向 <code>04-database.md</code> 与 <code>05-api-design.md</code> 两处。用户纠正：「对外 JSON 仍 ISO8601，但<strong>库内改为 timestamptz + ORM 自动转</strong>，别再用字符串字段了。」</p>
  <p><strong>写入</strong> <code>supersede r-ts-iso</code>，<code>confidence 0.85</code>；未改 <code>sources</code> 时继承旧指针，再<strong>追加</strong> <code>04-database.md#时间存储</code>；<code>query_local</code> 合并 CJK 检索词（如 timestamptz、时区）。</p>
  <p><strong>召回</strong> 之后 find「订单 created_at 存什么」→ 只应命中<strong>新</strong>规则；<code>get r-new</code> 可见 <code>supersedes: [r-ts-iso]</code> + 合并后的 <code>resolved_sources</code>。旧规则 dormant，避免 agent 仍按字符串方案建表。</p>
  <p><strong>复杂点</strong> 同一主题跨 interface + database 两篇 doc — sources 是多指针，不是「find 排名第一 doc 即真理」；supersede 解决「政策版本」，sources 解决「出处分散」。</p>
</article>

<article class="scenario">
  <h3>案例 D · 组合检索噪声 + 规则定锚（co_search 仅辅助）</h3>
  {desk_graph("case_d", "sources 锚定 performance · related 连 config 规则 · deployment 仅 grep 噪声（无边）")}
  <p><strong>背景</strong> 用户口语：「性能那边缓存和过期怎么配？」grep「性能+缓存+过期」命中 performance、deployment、config 等多篇（实验里类似「性能 缓存」「缓存 过期」组合词 fuzz）。</p>
  <p><strong>vault</strong> 已有规则「热点缓存策略以 performance 文档缓存策略节为准」，<code>sources</code> → <code>10-performance.md#缓存策略</code>；另有一条「功能开关过期日」在 config，<code>related</code> 到性能规则但不 supersede。</p>
  <p><strong>find</strong> 同轮返回 documents（多 chunk）+ <code>links.sources</code>（规则已指向 performance chunk）+ 可能 <code>co_search</code>（规则与 config chunk 同屏出现）。协议要求：<strong>行为以 rule claim + sources 为准</strong>，co_search 不 write-back、不单独当政策。</p>
  <p><strong>Read</strong> grep∩find 非空 → Read 交集中 performance（+ 若 claim 明确涉及开关再 Read config 一节），而不是 fuzz 表里的 3～5 篇全读。</p>
</article>

<article class="scenario">
  <h3>案例 E · 发版门禁：规则图 + 文档交叉（related + 多 scope AND）</h3>
  {desk_graph("case_e", "发版 related 子图 + 每条规则 sources 到对应 doc")}
  <p><strong>背景</strong> 发版前 checklist：命名 / 静态检查 / 可观测性水位 / 安全脱敏 — 分属 python、quality、observability、logging 多个 scope。</p>
  <p><strong>图</strong> <code>r-ruff-mypy</code> <code>related</code> <code>r-log-redact</code>；<code>r-capacity-70</code>（CPU/连接池水位）<code>related</code> 性能限流规则；无 conflicts，但 find 时 <code>scope=aurora,quality,ops</code> AND 收窄。</p>
  <p><strong>用户</strong> 「这轮要上生产，帮我对一下规范清单。」→ 一次 find 拉回相关 claim 子集；需要条文细节时对每条 <code>get r-…</code> 的 sources 按需 Read，而不是把 16 篇 docs 或 16 条 user text 全文灌进 prompt（对照 <a href="report.html">规范记忆</a> 实验的 baseline 臂）。</p>
  <p><strong>价值</strong> vault↔vault 表达「一起审」；vault↔doc 表达「每条出处」；与纯 shelves 检索互补。</p>
</article>
"""


def vault_row_html(r):
    c, l = r["control"], r["linked"]
    check = "通过" if r.get("checks_passed") else "未通过"
    extra = ""
    if r["id"] == "v1_supersede":
        extra = (
            f"旧规则进 find：{'是' if l.get('old_recalled') else '否'} · "
            f"新规则进 find：{'是' if l.get('new_recalled') else '否'} · "
            f"get.supersedes → {html.escape(str(l.get('get_supersedes') or []))}"
        )
    elif r["id"] == "v2_conflicts":
        extra = (
            f"conflict_set 条数 {len(l.get('conflict_set') or [])} · "
            f"A.conflicts_with {html.escape(str(l.get('get_a_conflicts') or []))}"
        )
    elif r["id"] == "v3_related":
        extra = f"get.related → {html.escape(str(l.get('get_related') or []))}"
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


def row_html(r):
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
    <td>规则 {html.escape(r.get('rule_id') or '—')} · links {l['find_links_count']}（{kinds}）· 召回 {'是' if r['rule_recalled'] else '否'}</td>
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

if not data:
    body = vault_body = "<p class='meta'>缺少 linking_summary.json — 请运行 measure_linking.py</p>"
    fin = {}
    comp = {}
    created = "—"
else:
    fin = data["final"]
    comp = data.get("comparison") or {}
    created = fmt_time(data["meta"]["created_at"])
    body = "".join(row_html(r) for r in data["rows"])
    vault_body = "".join(vault_row_html(r) for r in data.get("vault_rows") or [])
    if not vault_body:
        vault_body = "<p class='meta'>无 vault↔vault 场景 — 请重新运行 measure_linking.py</p>"

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
<p class="meta">静态 SVG，边样式与 <code>imprint desk open → 统一</code> 一致（离线 / 直接打开 html 即可）。示意节点，非 live vault。自动化断言见 §3–§4。</p>
{COMPLEX_CASES_HTML}

<h2>6. 与另两项实验的关系</h2>
<p class="meta"><a href="report.html">规范记忆</a> 测 vault 规则复用 token；<a href="retrieval.html">文档检索</a> 测 grep+find 收窄 Read（RETRIEVAL_VAULT 为空）。本页专用 <code>{html.escape(data['meta']['vault'] if data else '.imprint-link-bench')}</code>，在 add 时写入 sources，体现<strong>规则—文档双向可追溯</strong>，而非只比 BM25 排序。</p>

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
