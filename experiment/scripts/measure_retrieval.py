#!/usr/bin/env python3
"""Benchmark document recall token cost: grep+Read vs grep+find(paths)+Read.

  self (control) — host-agent default: rg -i -l then Read every matched file (full).
  narrow (experiment) — same rg; when indexed hits > k, one find(paths); if grep∩find
      non-empty Read all intersected paths in full; else same as control (Read all grep hits).

  k = find_top_k: caps find document hits and triggers paths find only; does not cap Read.
"""
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tokenizer
import agent_search
from mcp_client import MCPClient
from paths import DATA, PROJECT, RETRIEVAL_VAULT, imprint_mcp, public_bin, find_top_k

QUERIES = [
    {"qid": 1, "scope": "aurora", "query": "snake_case PascalCase naming",
     "query_local": "命名 snake_case PascalCase 函数 变量",
     "text": "函数变量用 snake_case、类名用 PascalCase，命名到底怎么定？",
     "target_file": "docs/01-python-style.md", "target_heading": "命名约定"},
    {"qid": 2, "scope": "aurora", "query": "Repository domain data access",
     "query_local": "仓储 Repository 数据访问 抽象",
     "text": "别直接打库，仓储这一层数据访问怎么抽象？",
     "target_file": "docs/02-architecture.md", "target_heading": "仓储模式"},
    {"qid": 3, "scope": "aurora", "query": "AuroraError exception base class",
     "query_local": "异常 AuroraError 基类 错误码",
     "text": "异常是不是都要走 AuroraError 基类和错误码？",
     "target_file": "docs/03-error-handling.md", "target_heading": "异常基类"},
    {"qid": 4, "scope": "aurora", "query": "ISO8601 UTC timestamp storage",
     "query_local": "时间戳 UTC ISO8601 存储",
     "text": "时间戳入库是不是必须 UTC、ISO8601？",
     "target_file": "docs/04-database.md", "target_heading": "时间戳存储"},
    {"qid": 5, "scope": "aurora", "query": "REST api prefix version",
     "query_local": "REST 接口 前缀 /api/v1 版本",
     "text": "REST 接口路径前缀和版本号怎么写？",
     "target_file": "docs/05-api-design.md", "target_heading": "路径前缀"},
    {"qid": 6, "scope": "aurora", "query": "trace_id structured logging",
     "query_local": "trace_id 结构化 日志 链路",
     "text": "日志要不要带 trace_id，结构化怎么打？",
     "target_file": "docs/06-logging.md", "target_heading": "trace_id"},
    {"qid": 7, "scope": "aurora", "query": "pytest test framework coverage",
     "query_local": "测试 pytest 覆盖率 框架",
     "text": "测试框架是 pytest 吗，覆盖率要多少？",
     "target_file": "docs/07-testing.md", "target_heading": "测试框架"},
    {"qid": 8, "scope": "aurora", "query": "readiness liveness health probe",
     "query_local": "健康检查 readiness liveness 探针",
     "text": "readiness 和 liveness 健康检查探针怎么配？",
     "target_file": "docs/08-deployment.md", "target_heading": "健康检查"},
    {"qid": 9, "scope": "aurora", "query": "CSRF security token",
     "query_local": "CSRF 安全 令牌 防护",
     "text": "写接口 CSRF 令牌防护怎么做？",
     "target_file": "docs/09-security.md", "target_heading": "CSRF 防护"},
    {"qid": 10, "scope": "aurora", "query": "rate limit degradation cache",
     "query_local": "限流 降级 缓存 性能",
     "text": "限流了之后怎么降级，能不能走缓存？",
     "target_file": "docs/10-performance.md", "target_heading": "限流降级"},
    {"qid": 11, "scope": "aurora", "query": "SLO error budget freeze release",
     "query_local": "SLO 错误预算 冻结发布",
     "text": "SLO 错误预算烧完了要不要冻结发布？",
     "target_file": "docs/11-observability.md", "target_heading": "SLO 定义"},
    {"qid": 12, "scope": "aurora", "query": "RED rate errors duration metrics",
     "query_local": "RED 方法 错误率 耗时",
     "text": "RED 方法里错误率和耗时指标怎么采？",
     "target_file": "docs/11-observability.md", "target_heading": "RED 方法"},
    {"qid": 13, "scope": "aurora", "query": "dead letter queue retry three",
     "query_local": "死信队列 重试 三次",
     "text": "失败重试三次还不行，是不是进死信队列？",
     "target_file": "docs/12-concurrency.md", "target_heading": "死信队列"},
    {"qid": 14, "scope": "aurora", "query": "idempotent consumer message_id",
     "query_local": "幂等消费 message_id",
     "text": "消费者怎么按 message_id 做幂等？",
     "target_file": "docs/12-concurrency.md", "target_heading": "幂等消费"},
    {"qid": 15, "scope": "aurora", "query": "parameterized SQL injection ORM",
     "query_local": "SQL 注入 参数化 ORM",
     "text": "防 SQL 注入是不是必须参数化，能不能拼字符串？",
     "target_file": "docs/09-security.md", "target_heading": "SQL 注入"},
    {"qid": 16, "scope": "aurora", "query": "soft delete archive physical",
     "query_local": "软删除 归档 物理删除",
     "text": "删数据是软删除、归档，还是物理删？",
     "target_file": "docs/04-database.md", "target_heading": "软删除"},
    {"qid": 17, "scope": "aurora", "query": "public function type annotations",
     "query_local": "类型注解 公开函数 签名",
     "text": "公开函数签名要不要写类型注解？",
     "target_file": "docs/01-python-style.md", "target_heading": "类型注解"},
    {"qid": 18, "scope": "aurora", "query": "list pagination page_size total",
     "query_local": "分页 page page_size total",
     "text": "列表分页 page、page_size、total 怎么约定？",
     "target_file": "docs/05-api-design.md", "target_heading": "分页约定"},
    {"qid": 19, "scope": "aurora", "query": "database connection pool timeout",
     "query_local": "连接池 超时 数据库连接",
     "text": "数据库连接池超时怎么设？",
     "target_file": "docs/04-database.md", "target_heading": "连接管理"},
    {"qid": 20, "scope": "aurora", "query": "two reviewers public API contract",
     "query_local": "公开接口 两名评审 接口负责人",
     "text": "公开接口是不是要两名评审，还要接口负责人？",
     "target_file": "docs/13-review.md", "target_heading": "公开接口"},
    {"qid": 21, "scope": "aurora", "query": "feature flag default off expiry",
     "query_local": "功能开关 默认关闭 过期",
     "text": "功能开关默认关着，过期了怎么办？",
     "target_file": "docs/14-config.md", "target_heading": "功能开关"},
    {"qid": 22, "scope": "aurora", "query": "i18n message catalog hardcoded string",
     "query_local": "文案目录 国际化 硬编码",
     "text": "文案能不能硬编码，国际化目录放哪？",
     "target_file": "docs/15-i18n.md", "target_heading": "文案目录"},
    {"qid": 23, "scope": "aurora", "query": "outbound HTTP connect read timeout",
     "query_local": "出站 连接超时 读取超时",
     "text": "出站 HTTP 连接超时和读取超时分别设多少？",
     "target_file": "docs/16-http-client.md", "target_heading": "超时设置"},
    {"qid": 24, "scope": "aurora", "query": "OpenAPI document drift sync",
     "query_local": "OpenAPI 文档 同步 漂移",
     "text": "OpenAPI 文档和实现漂移了怎么同步？",
     "target_file": "docs/05-api-design.md", "target_heading": "文档同步"},
    {"qid": 25, "scope": "aurora", "query": "performance cache",
     "query_local": "性能 缓存",
     "text": "性能这边缓存策略怎么定？",
     "target_file": "docs/10-performance.md", "target_heading": "缓存策略"},
    {"qid": 26, "scope": "aurora", "query": "connection pool timeout",
     "query_local": "连接池 超时",
     "text": "连接池超时怎么配？",
     "target_file": "docs/04-database.md", "target_heading": "连接管理"},
    {"qid": 27, "scope": "aurora", "query": "canary rollback",
     "query_local": "灰度发布 回滚",
     "text": "灰度发布失败了怎么回滚？",
     "target_file": "docs/08-deployment.md", "target_heading": "灰度发布"},
    {"qid": 28, "scope": "aurora", "query": "secret plaintext",
     "query_local": "密钥 明文",
     "text": "密钥能不能明文进仓库？",
     "target_file": "docs/09-security.md", "target_heading": "密钥存储"},
    {"qid": 29, "scope": "aurora", "query": "idempotent retry",
     "query_local": "幂等 重试",
     "text": "这个操作幂等吗，失败了能不能重试？",
     "target_file": "docs/03-error-handling.md", "target_heading": "重试策略"},
    {"qid": 30, "scope": "aurora", "query": "cache expiry",
     "query_local": "缓存 过期",
     "text": "缓存过期时间怎么定？",
     "target_file": "docs/10-performance.md", "target_heading": "缓存策略"},
    {"qid": 31, "scope": "aurora", "query": "sampling trace",
     "query_local": "采样 追踪",
     "text": "链路追踪采样率怎么设？",
     "target_file": "docs/11-observability.md", "target_heading": "链路采样"},
    {"qid": 32, "scope": "aurora", "query": "SQL concatenation",
     "query_local": "SQL 拼接",
     "text": "SQL 能不能字符串拼接？",
     "target_file": "docs/09-security.md", "target_heading": "SQL 注入"},
    {"qid": 33, "scope": "aurora", "query": "image layer cache",
     "query_local": "镜像 缓存",
     "text": "镜像构建缓存怎么用？",
     "target_file": "docs/08-deployment.md", "target_heading": "构建缓存"},
    {"qid": 34, "scope": "aurora", "query": "batch loop query",
     "query_local": "批量 循环",
     "text": "循环里逐条查库行不行，要不要批量？",
     "target_file": "docs/10-performance.md", "target_heading": "批量查询"},
    {"qid": 35, "scope": "aurora", "query": "trace_id logging",
     "query_local": "trace_id 日志",
     "text": "日志里要不要打 trace_id？",
     "target_file": "docs/06-logging.md", "target_heading": "trace_id"},
    {"qid": 36, "scope": "aurora", "query": "ISO8601 storage",
     "query_local": "ISO8601 存储",
     "text": "时间字段存储要用 ISO8601 吗？",
     "target_file": "docs/04-database.md", "target_heading": "时间戳存储"},
]


def tok(s):
    return tokenizer.count(s)


def compact(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def extract_documents(fr):
    r = fr.get("result", {})
    sc = r.get("structuredContent")
    if isinstance(sc, dict):
        return sc.get("documents", [])
    content = r.get("content", [])
    if content:
        try:
            return json.loads(content[0].get("text", "")).get("documents", [])
        except Exception:
            pass
    return []


def read_hit_files(paths):
    """Concatenate unique hit files as a Read tool would inject them."""
    parts, seen = [], []
    for p in paths:
        rel = p.replace("\\", "/")
        if rel in seen:
            continue
        seen.append(rel)
        fp = os.path.join(PROJECT, rel)
        if os.path.isfile(fp):
            with open(fp, encoding="utf-8") as f:
                parts.append(f.read())
    return "\n".join(parts), seen


def _norm_path(p):
    return (p or "").replace("\\", "/").lstrip("./")


def _same_path(a, b):
    a, b = _norm_path(a), _norm_path(b)
    if not a or not b:
        return False
    return a == b or a.endswith("/" + b) or b.endswith("/" + a)


def _target_rank(paths, target):
    for i, p in enumerate(paths, 1):
        if _same_path(p, target):
            return i
    return None


def indexed_grep_paths(files):
    """Paths from rg that shelves indexes (this corpus: docs/*.md)."""
    out = []
    for f in files:
        p = _norm_path(f)
        if p.startswith("docs/") and p.endswith(".md"):
            out.append(p)
    return out


def intersect_grep_find(grep_files, find_doc_paths):
    """Read order: find document rank; every grep hit that appears in find docs."""
    opened = []
    for dp in find_doc_paths:
        for gf in grep_files:
            if _same_path(gf, dp) and gf not in opened:
                opened.append(gf)
                break
    return opened


def host_default_read_files(indexed, all_files):
    """Host default search→read: full text for each grep-matched file (indexed first)."""
    if not all_files:
        return []
    if indexed:
        return list(indexed)
    return list(all_files)


def grep_hits_tokens(patterns, files, too_broad):
    """Shared grep channel: rg -l file list + (when wide) capped rg -n lines."""
    list_t = tok("\n".join(files))
    shown_lines = []
    hits = []
    line_t = 0
    if too_broad and files:
        hits = agent_search.search_lines(PROJECT, patterns)
        shown_lines = hits[: agent_search.MAX_HIT_LINES]
        line_t = tok("\n".join(shown_lines))
    return list_t + line_t, hits, shown_lines


def run_narrow(client, doc_budget):
    k = doc_budget
    rows = []
    for q in QUERIES:
        patterns = agent_search.distill_patterns(q["query"], q.get("query_local"))
        files = agent_search.search_files(PROJECT, patterns)
        rg_cmd = agent_search.rg_command(patterns)
        indexed = indexed_grep_paths(files)
        too_broad = len(indexed) > k
        qloc = q.get("query_local")
        hits_t, hits, shown_lines = grep_hits_tokens(patterns, files, too_broad)
        grep_sample = "\n".join(files) + (
            ("\n---\n" + "\n".join(shown_lines)) if shown_lines else ""
        )

        find_args = None
        find_req_t = 0
        find_docs_t = 0
        docs = []
        doc_paths = []
        headings = []

        if too_broad:
            find_args = {
                "scope": q["scope"],
                "query": q["query"],
                "query_local": q["query_local"],
                "paths": indexed,
            }
            fr = client.call_tool("find", find_args)
            docs = extract_documents(fr)
            doc_paths = [_norm_path(d.get("path")) for d in docs]
            headings = [d.get("heading") or "" for d in docs]
            find_req_t = tok(compact(find_args))
            find_docs_t = tok(compact(docs))
            opened = intersect_grep_find(indexed, doc_paths)
            if not opened:
                opened = host_default_read_files(indexed, files)
        else:
            opened = host_default_read_files(indexed, files)

        body, opened = read_hit_files(opened)
        search_req = tok(rg_cmd)
        read_t = tok(body)

        target = q["target_file"]
        rank = _target_rank(doc_paths, target) if doc_paths else None
        gold_h = q.get("target_heading") or ""

        rows.append({
            "qid": q["qid"],
            "query": q["query"],
            "query_local": qloc,
            "text": q.get("text") or "",
            "search_patterns": patterns,
            "rg_command": rg_cmd,
            "search_req_tokens": search_req,
            "grep_hits_tokens": hits_t,
            "grep_hits_sample": grep_sample,
            "find_args": find_args,
            "find_documents": docs,
            "find_req_tokens": find_req_t,
            "find_docs_tokens": find_docs_t,
            "read_files_tokens": read_t,
            "n_hits": len(files),
            "n_files_matched": len(files),
            "n_files_opened": len(opened),
            "opened_files": opened,
            "used_find_paths": too_broad,
            "used_find": too_broad,
            "n_docs": len(docs),
            "doc_paths": doc_paths,
            "doc_headings": headings,
            "target_file": target,
            "target_heading": gold_h,
            "target_rank": rank,
            "hit_target": rank is not None,
            "hit_heading": bool(gold_h) and gold_h in headings,
            "opened_target": any(_same_path(f, target) for f in opened),
            "too_broad": too_broad,
            "doc_budget": k,
            "total_input_tokens": search_req + hits_t + find_req_t + find_docs_t + read_t,
        })
    return rows


def run_self(doc_budget=None):
    k = doc_budget if doc_budget is not None else find_top_k(PROJECT)
    rows = []
    for q in QUERIES:
        patterns = agent_search.distill_patterns(q["query"], q.get("query_local"))
        files = agent_search.search_files(PROJECT, patterns)
        rg_cmd = agent_search.rg_command(patterns)
        search_req = tok(rg_cmd)
        indexed = indexed_grep_paths(files)
        too_broad = len(indexed) > k
        qloc = q.get("query_local")
        hits_t, hits, shown_lines = grep_hits_tokens(patterns, files, too_broad)
        grep_sample = "\n".join(files) + (
            ("\n---\n" + "\n".join(shown_lines)) if shown_lines else ""
        )
        opened = host_default_read_files(indexed, files) if files else []
        body, opened = read_hit_files(opened)
        read_t = tok(body)
        rows.append({
            "qid": q["qid"], "query": q["query"],
            "query_local": qloc,
            "text": q.get("text") or "",
            "search_patterns": patterns,
            "rg_command": rg_cmd,
            "search_req_tokens": search_req,
            "grep_hits_tokens": hits_t,
            "grep_hits_sample": grep_sample,
            "read_files_tokens": read_t,
            "n_hits": len(hits) if too_broad else len(files),
            "n_files_matched": len(files),
            "n_files_opened": len(opened),
            "opened_files": opened,
            "target_file": q["target_file"],
            "target_heading": q.get("target_heading") or "",
            "hit_target": any(_same_path(f, q["target_file"]) for f in files),
            "opened_target": any(_same_path(f, q["target_file"]) for f in opened),
            "too_broad": too_broad,
            "doc_budget": k,
            "total_input_tokens": search_req + hits_t + read_t,
        })
    return rows


def summarize(narrow_rows, self_rows):
    sd = se = 0
    out = []
    for n, e in zip(narrow_rows, self_rows):
        se += e["total_input_tokens"]
        sd += n["total_input_tokens"]
        out.append({
            "qid": n["qid"],
            "narrow_cum": sd,
            "self_cum": se,
            "saved_cum": se - sd,
            "saving_pct": round((se - sd) / se * 100, 2) if se else 0.0,
        })
    return out


def run_final_stats(narrow_rows, self_rows, summ):
    return {
        "doc_budget": narrow_rows[0]["doc_budget"] if narrow_rows else 0,
        "self_total": summ[-1]["self_cum"],
        "narrow_total": summ[-1]["narrow_cum"],
        "saved_tokens": summ[-1]["saved_cum"],
        "saving_pct": summ[-1]["saving_pct"],
        "control_opened_target": sum(1 for r in self_rows if r.get("opened_target")),
        "narrow_opened_target": sum(1 for r in narrow_rows if r.get("opened_target")),
        "find_hit_target": sum(
            1 for r in narrow_rows if r.get("used_find_paths") and r.get("hit_target")
        ),
        "find_hit_heading": sum(
            1 for r in narrow_rows if r.get("used_find_paths") and r.get("hit_heading")
        ),
        "queries_with_find_paths": sum(1 for r in narrow_rows if r.get("used_find_paths")),
        "n_queries": len(narrow_rows),
    }


def main():
    k = find_top_k(PROJECT)
    agent_search.MAX_OPEN = k
    vault_dir = os.path.join(PROJECT, RETRIEVAL_VAULT)
    if os.path.isdir(vault_dir):
        shutil.rmtree(vault_dir)
    client = MCPClient(
        imprint_mcp(),
        ["--project", PROJECT, "--vault", RETRIEVAL_VAULT],
        cwd=PROJECT,
    )
    client.initialize()
    try:
        narrow_rows = run_narrow(client, k)
        narrow_rows_k2 = run_narrow(client, 2)
    finally:
        client.close()
    self_rows = run_self(k)
    self_rows_k2 = run_self(2)
    summ = summarize(narrow_rows, self_rows)
    summ_k2 = summarize(narrow_rows_k2, self_rows_k2)
    final_k = run_final_stats(narrow_rows, self_rows, summ)
    final_k2 = run_final_stats(narrow_rows_k2, self_rows_k2, summ_k2)
    used_find = final_k["queries_with_find_paths"]
    used_find_k2 = final_k2["queries_with_find_paths"]

    def _retrieval_comparison(k_val):
        return {
            "question": "文档检索实验在比什么？",
            "baseline_arm": (
                f"对照 grep+Read（宿主默认）：rg -i -l 得完整名单；命中 > k 时另计 capped rg -n 行样本；"
                f"Read grep 命中的全部文件全文。无 vault、无 find。"
            ),
            "experiment_arm": (
                f"实验 grep+find(paths)+Read：同一 rg 与 grep token 口径；indexed > k 时计 "
                f"find(paths)+documents JSON；grep∩find 非空则 Read 交集全部篇全文，否则 Read 全部 grep 命中。"
                f" k={k_val} 仅触发 find/限制 find 文档条数，不 cap Read 篇数。"
            ),
            "excluded_from_both_arms": [
                "规范记忆 vault 中的 rules（本实验 RETRIEVAL_VAULT 为空，只测 shelves 文档）",
                "Cursor alwaysApply 规则与 AGENTS.md",
                "find 返回的 rules 段（语料无写入规则）",
            ],
            "shared_in_both_arms": "rg 命令字符串 + grep 名单（+ 宽查询时的行样本）",
            "corpus": "experiment 项目 docs/*.md + measure_retrieval.QUERIES",
        }

    def _retrieval_samples(self_rows, narrow_rows):
        wide = next((r for r in narrow_rows if r.get("used_find_paths")), None)
        narrow = next((r for r in narrow_rows if not r.get("used_find_paths")), None)
        out = {}
        if wide:
            qid = wide["qid"]
            ctrl = next(r for r in self_rows if r["qid"] == qid)
            out["wide_grep_query"] = {
                "qid": qid,
                "user_text": wide.get("text"),
                "rg_command": wide["rg_command"],
                "control": {
                    "grep_hits_sample": ctrl.get("grep_hits_sample") or "",
                    "opened_files": ctrl.get("opened_files") or [],
                    "tokens": {
                        "rg_cmd": ctrl["search_req_tokens"],
                        "grep_hits": ctrl["grep_hits_tokens"],
                        "read": ctrl["read_files_tokens"],
                        "total": ctrl["total_input_tokens"],
                    },
                },
                "experiment": {
                    "grep_hits_sample": wide.get("grep_hits_sample") or "",
                    "find_request_json": compact(wide.get("find_args") or {}),
                    "find_documents_json": compact(wide.get("find_documents") or []),
                    "opened_files": wide.get("opened_files") or [],
                    "tokens": {
                        "rg_cmd": wide["search_req_tokens"],
                        "grep_hits": wide["grep_hits_tokens"],
                        "find_req": wide["find_req_tokens"],
                        "find_docs": wide["find_docs_tokens"],
                        "read": wide["read_files_tokens"],
                        "total": wide["total_input_tokens"],
                    },
                },
            }
        if narrow:
            qid = narrow["qid"]
            ctrl = next(r for r in self_rows if r["qid"] == qid)
            out["narrow_no_find"] = {
                "qid": qid,
                "user_text": narrow.get("text"),
                "note": f"indexed ≤ k，实验不调 find；与对照同为 grep+Read",
                "rg_command": narrow["rg_command"],
                "grep_hits_sample": narrow.get("grep_hits_sample") or "",
                "opened_files": narrow.get("opened_files") or [],
                "tokens_control": ctrl["total_input_tokens"],
                "tokens_experiment": narrow["total_input_tokens"],
            }
        return out

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "retrieval_narrow.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "grep_find_read", "doc_budget": k, "rows": narrow_rows}, f,
                  ensure_ascii=False, indent=2)
    with open(os.path.join(DATA, "retrieval_narrow_k2.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "grep_find_read", "doc_budget": 2, "rows": narrow_rows_k2}, f,
                  ensure_ascii=False, indent=2)
    # Legacy filename for scripts not yet updated
    with open(os.path.join(DATA, "retrieval_shelves.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "grep_find_read", "doc_budget": k, "rows": narrow_rows}, f,
                  ensure_ascii=False, indent=2)
    with open(os.path.join(DATA, "retrieval_self.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "grep_read", "doc_budget": k, "rows": self_rows}, f,
                  ensure_ascii=False, indent=2)
    with open(os.path.join(DATA, "retrieval_self_k2.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "grep_read", "doc_budget": 2, "rows": self_rows_k2}, f,
                  ensure_ascii=False, indent=2)
    result = {
        "meta": {
            "imprint_mcp": public_bin(),
            "tokenizer": tokenizer.label(),
            "protocol": "control=grep+Read; experiment=grep+find(paths)+Read",
            "grep_tokens": "rg -l list; when indexed hits > k both arms add capped rg -n sample",
            "experiment_extra": "find request + documents JSON on top of aligned grep",
            "docs": len([fn for fn in os.listdir(os.path.join(PROJECT, "docs"))
                         if fn.endswith(".md")]),
            "docs_bytes": sum(
                os.path.getsize(os.path.join(PROJECT, "docs", fn))
                for fn in os.listdir(os.path.join(PROJECT, "docs"))
                if fn.endswith(".md")),
            "queries": len(QUERIES),
            "find_top_k": k,
            "snippet_runes_cap": 80,
            "control_max_open": k,
            "control_k2_max_open": 2,
            "control_search": agent_search.tool_label(),
            "queries_with_find_paths": used_find,
            "queries_with_find_paths_k2": used_find_k2,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "comparison": _retrieval_comparison(k),
            "comparison_k2": _retrieval_comparison(2),
        },
        "samples": _retrieval_samples(self_rows, narrow_rows),
        "samples_k2": _retrieval_samples(self_rows_k2, narrow_rows_k2),
        "summary": summ,
        "summary_k2": summ_k2,
        "final": {
            **final_k,
            "shelves_total": final_k["narrow_total"],
        },
        "final_k2": final_k2,
    }
    with open(os.path.join(DATA, "retrieval_summary.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({"k3": result["final"], "k2": result["final_k2"]},
                     ensure_ascii=False, indent=2))
    for label, sm in [("k3", summ), ("k2", summ_k2)]:
        print(f"--- per-query {label} ---")
        for r in sm:
            print(f"  q{r['qid']}: self={r['self_cum']:4d} narrow={r['narrow_cum']:4d} "
                  f"saved={r['saved_cum']:4d} ({r['saving_pct']:+.2f}%)")


if __name__ == "__main__":
    main()
