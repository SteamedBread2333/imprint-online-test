#!/usr/bin/env python3
"""Build HTML report: grep+Read (control) vs grep+find(paths)+Read (experiment)."""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, REPORT_DIR
from report_style import ARG_POP_JS, CSS, legend, grouped_bar_chart, fmt_time, esc_pre, report_nav
from measure_retrieval import QUERIES


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


summ = load("retrieval_summary.json")
sh = load("retrieval_shelves.json")["rows"]
sf = load("retrieval_self.json")["rows"]
final_k2 = summ.get("final_k2") or {}
_nk2 = os.path.join(DATA, "retrieval_narrow_k2.json")
_sk2 = os.path.join(DATA, "retrieval_self_k2.json")
if os.path.isfile(_nk2) and os.path.isfile(_sk2):
    sh_k2 = load("retrieval_narrow_k2.json")["rows"]
    sf_k2 = load("retrieval_self_k2.json")["rows"]
else:
    sh_k2 = sf_k2 = None
prec = load("retrieval_precision.json")
cp = prec["canonical_precision"]
fuzz = prec["fuzz"]
P1 = cp["precision_at_1"]
TOT = cp["total"]
RK = cp["recall_at_k"]

meta = summ["meta"]
final = summ["final"]
summary = summ["summary"]

qids = [r["qid"] for r in summary]
nq = len(qids)

self_hit = sum(r["grep_hits_tokens"] for r in sf)
self_read = sum(r.get("read_files_tokens", r.get("read_section_tokens", 0)) for r in sf)
sh_req = sum(r.get("find_req_tokens", 0) for r in sh)
sh_docs = sum(r.get("find_docs_tokens", r.get("snippets_tokens", 0)) for r in sh)
sh_read = sum(r.get("read_files_tokens", 0) for r in sh)

OPEN_OK = final.get("control_opened_target")
NARROW_OPEN = final.get("narrow_opened_target") or final.get("find_hit_target")
FIND_OK = final.get("find_hit_target")
HEAD_OK = final.get("find_hit_heading")
PROTO = meta.get("protocol") or "grep+Read vs grep+find(paths)+Read"
N_Q = final.get("n_queries") or nq
TOKENIZER = meta["tokenizer"]
DOCS_N = meta["docs"]
DOCS_BYTES = meta["docs_bytes"]
SNIP_CAP = meta.get("snippet_runes_cap", 80)
FIND_K = meta.get("find_top_k") or 2
CONTROL_K = meta.get("control_max_open") or FIND_K
CONTROL_K2 = meta.get("control_k2_max_open") or 2
CONTROL = meta.get("control_search") or "rg -i"
CTRL_BAR = "#a3a3a3"
EXP_BAR = "#dcdcdc"
FIND_K2 = final_k2.get("doc_budget") or CONTROL_K2


def _chips(values):
    out = []
    for v in values:
        if v is None or v == "":
            continue
        out.append(f"<code>{html.escape(str(v))}</code>")
    return "".join(out) if out else "<span class='meta'>—</span>"


def _pop_card(kicker, rows, foot=None):
    bits = ["<div class='pop-src'><div class='pop-card'>",
            f"<p class='pop-kicker'>{html.escape(kicker)}</p>",
            "<dl class='pop-dl'>"]
    for label, values in rows:
        if isinstance(values, str):
            values = [values]
        bits.append(
            f"<div><dt>{html.escape(label)}</dt><dd>{_chips(values)}</dd></div>"
        )
    bits.append("</dl>")
    if foot:
        bits.append(f"<p class='pop-foot'>{html.escape(foot)}</p>")
    bits.append("</div></div>")
    return "".join(bits)


def _arg_cell(short, pop_html, as_code=True):
    inner = f"<code>{html.escape(short)}</code>" if as_code else html.escape(short)
    return (
        f"<td class='clip arg' tabindex='0'>"
        f"<span class='short'>{inner}</span>"
        f"{pop_html}</td>"
    )


def _text_by_qid(qid):
    for q in QUERIES:
        if q["qid"] == qid:
            return q.get("text") or ""
    return ""


def _text_pop(text):
    text = text or "—"
    return (
        "<div class='pop-src'><div class='pop-card'>"
        "<p class='pop-kicker'>用户原话</p>"
        f"<p class='pop-text'>{html.escape(text)}</p>"
        "</div></div>"
    )


def _rg_short(e):
    pats = e.get("search_patterns") or []
    if pats:
        return " · ".join(pats)
    return e.get("query") or "—"


def _rg_pop(e):
    pats = e.get("search_patterns") or []
    cmd = e.get("rg_command") or ""
    rows = [
        ("工具", ["rg" if cmd.startswith("rg") else "grep"]),
        ("标志", ["-i", "-l", "--glob *.md"]),
        ("-e", pats or ["—"]),
        ("路径", ["docs"]),
    ]
    return _pop_card("对照 rg / grep · 一次检索", rows, cmd or None)


def _find_short(s):
    if not s.get("used_find_paths"):
        return "（未调 find）"
    args = s.get("find_args") or {}
    qloc = args.get("query_local") or s.get("query_local")
    q = args.get("query") or s.get("query")
    if qloc and qloc != q:
        return qloc
    return q or "—"


def _find_pop(s, budget_k):
    args = dict(s.get("find_args") or {})
    if not args:
        args = {
            "scope": s.get("scope") or "aurora",
            "query": s.get("query") or "",
        }
        if s.get("query_local"):
            args["query_local"] = s["query_local"]
    rows = [
        ("scope", [args.get("scope") or "—"]),
        ("query", [args.get("query") or "—"]),
        ("query_local", [args.get("query_local") or "（未传）"]),
    ]
    paths = args.get("paths")
    if paths:
        rows.append(("paths", [f"{len(paths)} 篇 indexed grep"]))
    n = s.get("n_docs")
    foot = f"k={budget_k} 触发 find · find 返回 {n} 篇" if n is not None else f"k={budget_k}"
    if not s.get("used_find_paths"):
        foot = f"k={budget_k} · indexed≤k，无 paths find"
    return _pop_card("实验 find · MCP", rows, foot)


def _tail(p):
    p = p or ""
    return p.split("/", 1)[1] if "/" in p else p


def _find_inject(s):
    n_open = s.get("n_files_opened", 0)
    opened_ok = s.get("opened_target")
    if n_open == 0:
        return "0篇·未读"
    if opened_ok and n_open == 1:
        return "1篇·目标"
    if opened_ok:
        return f"{n_open}篇·含目标"
    return f"{n_open}篇·未中"


def _find_docs(s):
    paths = s.get("opened_files") or []
    bits = [f"<code>{html.escape(_tail(p))}</code>" for p in paths]
    return " · ".join(bits) if bits else "—"


def _rg_open(e):
    n_match = e.get("n_files_matched", e.get("n_files_opened", 0))
    n_open = e.get("n_files_opened", 0)
    opened_ok = e.get("opened_target")
    if n_match == 0:
        return "空集"
    if opened_ok and n_open == 1:
        return "1篇·目标"
    if n_match == n_open:
        return f"{n_open}篇·含目标" if opened_ok else f"{n_open}篇·未中"
    hit = "含目标" if opened_ok else "未中"
    return f"{n_match}→{n_open}·{hit}"


def _delta_cell(ctrl, expn, s, saved, pct):
    find_extra = s.get("find_req_tokens", 0) + s.get("find_docs_tokens", s.get("snippets_tokens", 0))
    if saved == 0 and not s.get("used_find_paths"):
        return f"{ctrl:,} − {expn:,} = 0（未调 find）"
    if saved == 0:
        return f"{ctrl:,} − {expn:,} = 0（0.0%）"
    if saved > 0:
        return f"{ctrl:,} − {expn:,} = {saved:,}（{pct:.1f}%）"
    return f"{ctrl:,} − {expn:,} = {saved:,}（实验 +{abs(saved):,}，find {find_extra}）"


def rows_html(sh_rows, sf_rows, budget_k):
    out = []
    for s, e in zip(sh_rows, sf_rows):
        ctrl, expn = e["total_input_tokens"], s["total_input_tokens"]
        saved = ctrl - expn
        pct = saved / ctrl * 100 if ctrl else 0
        read = e.get("read_files_tokens", e.get("read_section_tokens", 0))
        nread = s.get("read_files_tokens", 0)
        find_docs_t = s.get("find_docs_tokens", s.get("snippets_tokens", 0))
        target = _tail(s.get("target_file") or e.get("target_file") or "")
        uttered = s.get("text") or e.get("text") or _text_by_qid(s["qid"])
        cls = "pos" if saved > 0 else ("neg" if saved < 0 else "")
        delta_cell = _delta_cell(ctrl, expn, s, saved, pct)
        out.append(
            f"<tr><td class='num'>q{s['qid']}</td>"
            f"<td class='clip' title='{html.escape(target, quote=True)}'><code>{target}</code></td>"
            f"{_arg_cell(uttered, _text_pop(uttered), as_code=False)}"
            f"{_arg_cell(_rg_short(e), _rg_pop(e))}"
            f"{_arg_cell(_find_short(s), _find_pop(s, budget_k))}"
            f"<td class='num'>{e['search_req_tokens']}</td>"
            f"<td class='num'>{e['grep_hits_tokens']}</td>"
            f"<td class='num'>{read}</td>"
            f"<td class='clip'>{_rg_open(e)}</td>"
            f"<td class='num'>{ctrl}</td>"
            f"<td class='num sep'>{s.get('find_req_tokens', 0)}</td>"
            f"<td class='num'>{find_docs_t}</td>"
            f"<td class='num'>{nread}</td>"
            f"<td class='clip'>{_find_inject(s)}</td>"
            f"<td class='clip'>{_find_docs(s)}</td>"
            f"<td class='num'>{expn}</td>"
            f"<td class='num {cls} sep'>{delta_cell}</td></tr>"
        )
    return "".join(out)


def _table_head(budget_k):
    return f"""
<thead>
<tr>
  <th rowspan="2" class="num">查询</th>
  <th rowspan="2">期望目标</th>
  <th rowspan="2">用户原话</th>
  <th rowspan="2">rg / grep 参数</th>
  <th rowspan="2">find 参数</th>
  <th colspan="5" class="grp">对照 rg / grep · k={budget_k}</th>
  <th colspan="6" class="grp sep">实验 grep+find+Read · k={budget_k}</th>
  <th rowspan="2" class="num sep">差额</th>
</tr>
<tr>
  <th class="num">检索式</th>
  <th class="num">命中行</th>
  <th class="num">Read</th>
  <th>打开</th>
  <th class="num">小计</th>
  <th class="num sep">find</th>
  <th class="num">documents</th>
  <th class="num">Read</th>
  <th>Read</th>
  <th>文件</th>
  <th class="num">小计</th>
</tr>
</thead>"""


def _cost_block(budget_k, sh_rows, sf_rows, fin):
    if not sh_rows or not sf_rows or not fin:
        return "<p class='meta'>缺少数据：请运行 measure_retrieval.py</p>"
    qids_local = [r["qid"] for r in sh_rows]
    self_each = [r["total_input_tokens"] for r in sf_rows]
    exp_each = [r["total_input_tokens"] for r in sh_rows]
    y_max = ((max(self_each + exp_each) // 500) + 1) * 500
    chart = grouped_bar_chart(qids_local, [
        (f"对照 grep+Read k={budget_k}", self_each, CTRL_BAR),
        (f"实验 grep+find k={budget_k}", exp_each, EXP_BAR),
    ], y_max, x_prefix="q")
    saved = fin.get("saved_tokens", 0)
    pct = fin.get("saving_pct", 0)
    nq = fin.get("n_queries", len(qids_local))
    used = fin.get("queries_with_find_paths", "—")
    return f"""
<p class="meta">累计 {saved:,} tok（{pct:.1f}%）· 对照 {fin.get('self_total', 0):,} → 实验 {fin.get('narrow_total', 0):,}
· Read 金标 {fin.get('control_opened_target', '—')}/{nq} / {fin.get('narrow_opened_target', '—')}/{nq}
· 调 find {used}/{nq} · find 列表含目标 {fin.get('find_hit_target', '—')}/{nq}</p>
{legend([('对照 grep+Read', CTRL_BAR), ('实验 grep+find+Read', EXP_BAR)], mark="bar")}
<div class="chart"><svg viewBox="0 0 1120 300" width="100%" xmlns="http://www.w3.org/2000/svg">{chart}</svg></div>
<div class="table-scroll">
<table class="data pin">
{_table_head(budget_k)}
<tbody>{rows_html(sh_rows, sf_rows, budget_k)}</tbody>
</table>
</div>"""


section_k3 = _cost_block(CONTROL_K, sh, sf, final)
section_k2 = _cost_block(FIND_K2, sh_k2, sf_k2, final_k2) if sh_k2 and sf_k2 else ""


def _nset(c):
    return len(c.get("grep_files") or [])


def _shrinks(c):
    n_rg = _nset(c)
    n_read = len(c.get("read_paths") or c.get("shelves_paths") or [])
    return n_rg > 1 and n_read and n_read < n_rg and c.get("find_rank", c.get("shelves_rank"))


fuzz_combo = [c for c in fuzz if c.get("kind") == "combo"]
fuzz_ident = [c for c in fuzz if c.get("kind") == "ident"]
if not fuzz_combo and not fuzz_ident:
    fuzz_combo = list(fuzz)
combo_wide = [c for c in fuzz_combo if _nset(c) > 1]
combo_shrink = [c for c in combo_wide if _shrinks(c)]
combo_one = [c for c in combo_shrink if len(c.get("read_paths") or c.get("shelves_paths") or []) == 1]
fuzz_single = [c for c in fuzz_ident if c.get("grep_hit_target") and _nset(c) == 1]
fuzz_miss = [c for c in fuzz if not c.get("grep_hit_target") and c.get("kind") != "combo"]
off_rank = [c for c in prec.get("canonical") or [] if c.get("rank") not in (1, None)]
N_COMBO = len(fuzz_combo)
N_WIDE = len(combo_wide)
N_SHRINK = len(combo_shrink)
N_ONE = len(combo_one)


def grep_cell(c):
    fs = c["grep_files"]
    pats = c.get("search_patterns") or []
    extra = ""
    if pats:
        shown = ", ".join(f"<code>{p}</code>" for p in pats[:3])
        extra = f"<div class='meta'>检索式：{shown}</div>"
    if not fs:
        return extra + "空集" if extra else "空集"
    names = ", ".join(_tail(f) for f in fs)
    n = len(fs)
    if c["grep_hit_target"]:
        return f"{extra}{n} 篇（含目标：{names}）"
    return f"{extra}{n} 篇，不含目标（{names}）"


def find_cell(c):
    read_paths = c.get("read_paths") or []
    n = len(read_paths)
    n_rg = _nset(c)
    rank = c.get("find_rank", c.get("shelves_rank"))
    if not c.get("used_find_paths"):
        return f"grep ≤ {FIND_K}，直接 Read {n} 篇"
    if n == 0:
        return "find 后未 Read（回退空）"
    if rank is None:
        return f"Read {n} 篇，不含目标（grep {n_rg} 篇）"
    if n == 1:
        return "Read 1 篇，即目标"
    if n < n_rg:
        return f"Read {n} 篇，含目标（grep 命中 {n_rg} 篇）"
    return f"Read {n} 篇，含目标"


def fuzz_html(rows):
    out = []
    for c in rows:
        qloc = c.get("query_local")
        extra = f"<div class='meta'>中文检索词：{qloc}</div>" if qloc else ""
        out.append(
            f"<tr><td><code>{c['guess']}</code>{extra}</td><td>{c['note']}</td>"
            f"<td>{grep_cell(c)}</td>"
            f"<td class='sep'>{find_cell(c)}</td></tr>"
        )
    return "".join(out)


single_examples = "、".join(f"<code>{c['guess']}</code>" for c in fuzz_single[:6])
if len(fuzz_single) > 6:
    single_examples += " 等"
ident_line = (
    f"{len(fuzz_ident)} 组标识符变体中，{len(fuzz_single)} 组 grep 只命中目标一篇"
    + (f"（如 {single_examples}）" if single_examples else "")
    + "。两边 Read 同一篇，成本接近。"
) if fuzz_ident else ""
off_rank_html = ""
if off_rank:
    bits = []
    for c in off_rank:
        top = (c.get("top") or [{}])[0].get("path", "")
        bits.append(
            f"q{c['qid']}（<code>{c['query']}</code>）首选为 {_tail(top)}，"
            f"目标文档列第 {c['rank']}"
        )
    off_rank_html = "未列首选的查询：" + "；".join(bits) + "。"

comp = summ.get("meta", {}).get("comparison") or {}
rsamples = summ.get("samples") or {}
if not comp:
    comp = {
        "baseline_arm": f"grep+Read：rg 名单 +（宽时）行样本 + Read ≤{FIND_K} 篇全文",
        "experiment_arm": f"grep+find(paths)+Read：同一 grep 段 + 宽时 find + Read 交集",
        "excluded_from_both_arms": ["Cursor .mdc", "vault rules（本实验 vault 为空）"],
        "shared_in_both_arms": "rg 命令 + grep 名单/行样本",
        "corpus": "docs/*.md + QUERIES",
    }
def _ret_sample_wide():
    w = rsamples.get("wide_grep_query")
    if not w:
        return ""
    c, e = w.get("control") or {}, w.get("experiment") or {}
    ct, et = c.get("tokens") or {}, e.get("tokens") or {}
    find_blob = (e.get("find_request_json") or "") + "\n\n" + (e.get("find_documents_json") or "")
    read_list = html.escape(", ".join(e.get("opened_files") or []))
    return f"""
<details class="sample" open>
  <summary>宽 grep q{w.get('qid')} · 对照 {ct.get('total')} tok · 实验 {et.get('total')} tok</summary>
  <p class="meta">{html.escape(w.get('user_text') or '')}</p>
  {esc_pre(w.get('rg_command') or '')}
  <p class="meta">grep 段</p>
  {esc_pre(c.get('grep_hits_sample') or '')}
  <p class="meta">find 请求 · documents（Read：{read_list}）</p>
  {esc_pre(find_blob)}
</details>"""


def _ret_sample_narrow():
    n = rsamples.get("narrow_no_find")
    if not n:
        return ""
    rg_blob = (n.get("rg_command") or "") + "\n\n" + (n.get("grep_hits_sample") or "")
    return f"""
<details class="sample">
  <summary>窄 grep q{n.get('qid')} · 未调 find · {n.get('tokens_control')} tok</summary>
  <p class="meta">{html.escape(n.get('user_text') or '')}</p>
  {esc_pre(rg_blob)}
  <p class="meta">Read：{html.escape(', '.join(n.get('opened_files') or []))}</p>
</details>"""


retrieval_transparency = f"""
<h2>2. 对照与样本</h2>
<table class="data comp-table">
<thead><tr><th>臂</th><th>计入 prompt 的文档证据</th></tr></thead>
<tbody>
<tr><td>对照</td><td>{html.escape(comp.get('baseline_arm', ''))}</td></tr>
<tr><td>实验</td><td>{html.escape(comp.get('experiment_arm', ''))}</td></tr>
<tr><td>共用</td><td>{html.escape(comp.get('shared_in_both_arms', ''))}</td></tr>
<tr><td>语料</td><td><code>{html.escape(comp.get('corpus', ''))}</code></td></tr>
<tr><td>不含</td><td>{html.escape('；'.join(comp.get('excluded_from_both_arms') or []))}</td></tr>
</tbody>
</table>
<div class="formula">两套独立实验：k 仅用于 indexed&gt;k 触发 find 与 find 文档条数；对照/实验 Read 均为 grep 全命中或 find 交集全篇（不 cap Read）
§3 k={CONTROL_K} · §4 k=2</div>
{_ret_sample_wide()}
{_ret_sample_narrow()}
"""

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>文档检索对照实验</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header class="mast">
  <p class="meta-row"><span>imprint 对照实验 · 文档检索</span><span>{fmt_time(meta['created_at'])}</span></p>
  {report_nav("retrieval")}
  <h1>文档检索：grep+Read 与 grep+find 收窄+Read</h1>
  <p class="lede">{DOCS_N} 篇 docs · {nq} 查询。§3 k={CONTROL_K} 与 §4 k=2 各一套对照/实验（表格独立）。</p>
</header>

<table class="kpi">
<tr>
  <th>k</th>
  <th>累计差额</th>
  <th>节约率</th>
  <th>对照 Read 金标</th>
  <th>实验 Read 金标</th>
  <th>调 find</th>
</tr>
<tr>
  <td>{CONTROL_K}</td>
  <td class="num">{final['saved_tokens']:,}</td>
  <td class="num">{final['saving_pct']:.1f}%</td>
  <td class="num">{OPEN_OK}/{N_Q}</td>
  <td class="num">{NARROW_OPEN}/{N_Q}</td>
  <td class="num">{meta.get('queries_with_find_paths', '—')}/{N_Q}</td>
</tr>
<tr>
  <td>2</td>
  <td class="num">{final_k2.get('saved_tokens', '—')}</td>
  <td class="num">{final_k2.get('saving_pct', '—')}{'%' if final_k2.get('saving_pct') is not None else ''}</td>
  <td class="num">{final_k2.get('control_opened_target', '—')}/{N_Q}</td>
  <td class="num">{final_k2.get('narrow_opened_target', '—')}/{N_Q}</td>
  <td class="num">{meta.get('queries_with_find_paths_k2', '—')}/{N_Q}</td>
</tr>
</table>

<h2>1. 结论</h2>
<p>k={CONTROL_K}：{final['saved_tokens']:,} tok（{final['saving_pct']:.1f}%）。k=2：{final_k2.get('saved_tokens', '—')} tok（{final_k2.get('saving_pct', '—')}%）。k 越小 indexed&gt;k 越早触发 find；两表互不可加总对比。</p>
<p>k={CONTROL_K} 组合查询：宽 grep {N_WIDE} 组，实验收窄 Read {N_SHRINK}、单篇 {N_ONE}（仅 k={CONTROL_K} 实验臂）。</p>

{retrieval_transparency}

<h2>3. 输入成本 · k={CONTROL_K}</h2>
{section_k3}

<h2>4. 输入成本 · k=2</h2>
{section_k2}

<h2>5. 组合查询（k={CONTROL_K} 实验臂）</h2>
<div class="table-scroll">
<table class="data">
<thead>
<tr>
  <th rowspan="2">组合查询</th>
  <th rowspan="2">词的分布</th>
  <th class="grp">对照 rg / grep</th>
  <th class="grp sep">实验 find</th>
</tr>
<tr>
  <th>命中集合</th>
  <th class="sep">find+Read</th>
</tr>
</thead>
<tbody>{fuzz_html(fuzz_combo)}</tbody>
</table>
</div>
{f'<p>{ident_line}</p>' if ident_line else ''}
{f'''<p>{len(fuzz_miss)} 组未命中目标文档。</p>
<div class="table-scroll">
<table class="data">
<thead>
<tr>
  <th rowspan="2">查询</th>
  <th rowspan="2">说明</th>
  <th class="grp">对照 rg / grep</th>
  <th class="grp sep">实验 find</th>
</tr>
<tr>
  <th>命中集合</th>
  <th class="sep">find+Read</th>
</tr>
</thead>
<tbody>{fuzz_html(fuzz_miss)}</tbody>
</table>
</div>
''' if fuzz_miss else ''}
<p>问法正确的 {TOT} 组上，find 首选即目标 {P1}/{TOT}，列表覆盖 {RK}/{TOT}。{off_rank_html}</p>

<h2>6. 局限</h2>
<ul class="limits">
<li>grep 对齐；宽时实验另计 find+documents（snippet ~{SNIP_CAP} 字），Read 计全文。</li>
<li>grep&gt;k 选篇启发式不同；交集空则回退 grep。</li>
<li>分词 Grok-2 公开编码器；未测未索引 path。</li>
</ul>

<p class="footer">由 experiment/scripts/build_retrieval_report.py 生成。实验时间 {fmt_time(meta['created_at'])}。文档合计 {DOCS_BYTES:,} 字节。</p>
</div>
<script>{ARG_POP_JS}</script>
</body>
</html>
"""

os.makedirs(REPORT_DIR, exist_ok=True)
out = os.path.join(REPORT_DIR, "retrieval.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", out)
print("final:", final)
