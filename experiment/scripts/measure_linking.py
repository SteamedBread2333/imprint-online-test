#!/usr/bin/env python3
"""Vault linking benchmark: rule↔doc and rule↔rule scenarios.

Doc rows: grep+Read full files vs find with persisted sources.
Vault rows: supersede / conflicts_with / related — graph in get & find conflict_set.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tokenizer
from mcp_client import MCPClient
from paths import DATA, PROJECT, LINK_VAULT, imprint_mcp, public_bin
from measure_retrieval import read_hit_files, _norm_path
from measure import extract_rules, extract_shelves, compact, extract_add_out
import agent_search

SCENARIOS = [
    {
        "id": "s1_rule_first",
        "title": "编码前：规则 claim 替代整篇风格文档",
        "advantage": "一次 find 返回紧凑 claim，足够落地命名；vault sources 指向出处，不必先 Read 全文。",
        "user_message": "新增订单 API 模块，类和函数怎么命名？",
        "scope": "aurora,python",
        "query": "PascalCase snake_case naming",
        "query_local": "命名 PascalCase snake_case 类 函数",
        "seed": {
            "claim": "Use snake_case for functions/variables and PascalCase for classes",
            "scope": "aurora,python",
            "text": "函数和变量统一 snake_case，类名 PascalCase；review 时一眼能分清标识符种类。",
            "query_local": "命名 snake_case PascalCase 函数 变量 类名",
            "sources": [{"path": "docs/01-python-style.md", "heading": "命名约定"}],
        },
        "control_read": ["docs/01-python-style.md"],
        "linked_read": [],
    },
    {
        "id": "s2_wide_grep",
        "title": "宽 grep：规则 + sources 钉住权威文档",
        "advantage": "grep 命中多篇时，规则 claim 说明「缓存策略」权威节；sources 链到 chunk，Read 只需金标一篇。",
        "user_message": "性能这边缓存策略怎么定？",
        "scope": "aurora",
        "query": "performance cache",
        "query_local": "性能 缓存",
        "grep_patterns_from": ("performance cache", "性能 缓存"),
        "seed": {
            "claim": "Define hot-data cache TTL and anti-stampede policy per performance doc cache section",
            "scope": "aurora,performance",
            "text": "热点数据走缓存并设合理过期，避免击穿与雪崩；以性能规范「缓存策略」节为唯一权威。",
            "query_local": "缓存策略 热点 过期 击穿 雪崩 性能",
            "sources": [{"path": "docs/10-performance.md", "heading": "缓存策略"}],
        },
        "control_read_from_grep": True,
        "linked_read": ["docs/10-performance.md"],
    },
    {
        "id": "s3_provenance",
        "title": "审计：get 规则 ↔ get chunk 双向关联",
        "advantage": "写入期 sources 持久化；find 带 links；get 规则看 resolved_sources，get chunk 看 referenced_rules。",
        "user_message": "异常必须怎么抛？我要核对原文依据。",
        "scope": "aurora,quality",
        "query": "AuroraError exception raise",
        "query_local": "异常 AuroraError 裸 raise",
        "seed": {
            "claim": "Throw AuroraError subclasses for all errors; never bare raise",
            "scope": "aurora,quality",
            "text": "统一抛 AuroraError 子类，禁止裸 raise Exception，便于映射错误码与日志。",
            "query_local": "异常 auroraerror 子类 裸 raise",
            "sources": [{"path": "docs/03-error-handling.md", "heading": "异常基类"}],
        },
        "control_read": ["docs/03-error-handling.md"],
        "linked_read": ["docs/03-error-handling.md"],
        "audit_get": True,
    },
]


def extract_find_obj(resp):
    return tool_json(resp)


def run_vault_graph(client):
    """Rule ↔ rule edges (persistent vault); separate fresh vault."""
    rows = []

    # --- v1 supersede: only active successor in find; lineage on get ---
    old_add = {
        "claim": "Use camelCase for Python function names in aurora",
        "scope": "aurora,python",
        "text": "历史约定：函数名用 camelCase（已废弃，仅作对照）。",
        "query_local": "camelCase 函数名 命名",
    }
    ar = client.call_tool("add", old_add)
    old_id = extract_add_out(ar).get("id")
    sup_args = {
        "old_id": old_id,
        "claim": "Use snake_case for functions/variables and PascalCase for classes",
        "scope": "aurora,python",
        "reason": "团队对齐 PEP8，camelCase 废止",
        "text": "函数和变量统一 snake_case，类名 PascalCase。",
        "query_local": "snake_case PascalCase 命名",
    }
    sr = client.call_tool("supersede", sup_args)
    new_id = tool_json(sr).get("id") or extract_add_out(sr).get("id")
    find_args = {"scope": "aurora,python", "query": "function naming snake_case",
                 "query_local": "函数 命名 snake_case"}
    fr = client.call_tool("find", find_args)
    fobj = extract_find_obj(fr)
    rules = fobj.get("rules") or extract_rules(fr)
    recalled_ids = {r.get("id") for r in rules}
    gr = client.call_tool("get", {"id": new_id})
    gobj = tool_json(gr)
    control_text = old_add["text"] + "\n" + sup_args["text"]
    control_t = tok("用户：函数怎么命名？") + tok(control_text)
    linked_t = tok("用户：函数怎么命名？") + tok(compact(find_args)) + tok(compact(rules))
    rows.append({
        "id": "v1_supersede",
        "kind": "vault_vault",
        "title": "政策演进：supersedes（新 → 旧）",
        "advantage": "旧政策 dormant，find 只召回现行 claim；get 可见 supersedes 链，desk /graph 可审 lineage。",
        "user_message": "函数和变量怎么命名？",
        "find_args": find_args,
        "control": {
            "description": "未 supersede：旧+新两条 user text 同时进 prompt",
            "tokens": control_t,
        },
        "linked": {
            "description": "supersede 后单次 find",
            "tokens": linked_t,
            "active_rule_id": new_id,
            "dormant_rule_id": old_id,
            "old_recalled": old_id in recalled_ids,
            "new_recalled": new_id in recalled_ids,
            "get_supersedes": gobj.get("supersedes") or [],
            "rules_sample": rules[:4],
        },
        "checks_passed": new_id in recalled_ids and old_id not in recalled_ids
            and old_id in (gobj.get("supersedes") or []),
        "saved_tokens": control_t - linked_t,
        "saving_pct": round((control_t - linked_t) / control_t * 100, 2) if control_t else 0,
    })

    # --- v2 conflicts_with: find conflict_set surfaces opposition ---
    a_add = {
        "claim": "Retry failed outbound HTTP calls up to three times",
        "scope": "aurora,http",
        "text": "出站 HTTP 失败默认重试最多 3 次，带指数退避。",
        "query_local": "HTTP 重试 三次 退避",
    }
    ar_a = client.call_tool("add", a_add)
    a_id = extract_add_out(ar_a).get("id")
    b_add = {
        "claim": "Never retry non-idempotent POST requests",
        "scope": "aurora,http",
        "text": "非幂等 POST 禁止自动重试，避免重复下单。",
        "query_local": "POST 幂等 禁止 重试",
        "conflicts": a_id,
    }
    ar_b = client.call_tool("add", b_add)
    b_id = extract_add_out(ar_b).get("id")
    find_args2 = {"scope": "aurora,http", "query": "HTTP retry POST",
                  "query_local": "HTTP 重试 POST"}
    fr2 = client.call_tool("find", find_args2)
    fobj2 = extract_find_obj(fr2)
    rules2 = fobj2.get("rules") or extract_rules(fr2)
    conflict_set = fobj2.get("conflict_set") or []
    ga = tool_json(client.call_tool("get", {"id": a_id}))
    gb = tool_json(client.call_tool("get", {"id": b_id}))
    both_recalled = a_id in {r.get("id") for r in rules2} and b_id in {r.get("id") for r in rules2}
    rows.append({
        "id": "v2_conflicts",
        "kind": "vault_vault",
        "title": "对立共存：conflicts_with + find conflict_set",
        "advantage": "两条相反政策都 active 时，vault 边 + find 的 conflict_set 提醒 agent 不可盲从一端；find 会对较弱一侧降权。",
        "user_message": "出站 POST 失败时要不要重试？",
        "find_args": find_args2,
        "control": {
            "description": "无边：两条 claim 同时召回且无 conflict_set（模拟未 link）",
            "tokens": tok("用户：POST 失败重试？") + tok(compact(a_add)) + tok(compact(b_add)),
        },
        "linked": {
            "description": "add(conflicts) 后 find",
            "tokens": tok("用户：POST 失败重试？") + tok(compact(find_args2))
                + tok(compact({"rules": rules2, "conflict_set": conflict_set})),
            "rule_ids": [a_id, b_id],
            "conflict_set": conflict_set,
            "get_a_conflicts": ga.get("conflicts_with") or [],
            "get_b_conflicts": gb.get("conflicts_with") or [],
            "rules_sample": rules2[:4],
        },
        "checks_passed": both_recalled and len(conflict_set) > 0,
        "saved_tokens": 0,
        "saving_pct": 0,
    })

    # --- v3 related: lightweight graph edge for cross-topic recall ---
    c_add = {
        "claim": "Run ruff and mypy clean before every commit",
        "scope": "aurora,quality",
        "text": "提交前 ruff + mypy 全绿。",
        "query_local": "ruff mypy 提交",
    }
    ar_c = client.call_tool("add", c_add)
    c_id = extract_add_out(ar_c).get("id")
    client.call_tool("link", {"id": c_id, "related": a_id})
    gc = tool_json(client.call_tool("get", {"id": c_id}))
    rows.append({
        "id": "v3_related",
        "kind": "vault_vault",
        "title": "跨主题：related 边（质量 ↔ HTTP 重试）",
        "advantage": "相关但不替代的政策用 related 连成图；get / desk 统一视图，便于人工审规则网。",
        "user_message": "（维护）提交门禁和出站重试政策有关吗？",
        "find_args": None,
        "control": {"description": "无 related：需分别 list/记忆两条 id", "tokens": 0},
        "linked": {
            "description": "link related 后 get",
            "tokens": tok(compact(gc)),
            "rule_id": c_id,
            "get_related": gc.get("related") or [],
        },
        "checks_passed": a_id in (gc.get("related") or []),
        "saved_tokens": 0,
        "saving_pct": 0,
    })
    return rows


def tok(s):
    return tokenizer.count(s)


def tool_json(resp):
    r = resp.get("result", {})
    sc = r.get("structuredContent")
    if isinstance(sc, dict):
        return sc
    for c in r.get("content") or []:
        if isinstance(c, dict) and c.get("type") == "text":
            try:
                return json.loads(c.get("text") or "{}")
            except json.JSONDecodeError:
                pass
    return {}


def grep_paths(query, query_local):
    patterns = agent_search.distill_patterns(query, query_local)
    files = agent_search.search_files(PROJECT, patterns)
    return patterns, files


def run_scenario(client, sc, rule_id):
    user_t = tok(sc["user_message"])
    find_args = {
        "scope": sc["scope"],
        "query": sc["query"],
        "query_local": sc.get("query_local"),
    }
    fr = client.call_tool("find", find_args)
    rules = extract_rules(fr)
    shelves = extract_shelves(fr)
    docs = shelves.get("documents") or []
    links = shelves.get("links") or []

    if sc.get("control_read_from_grep"):
        q, ql = sc["grep_patterns_from"]
        _, gf = grep_paths(q, ql)
        control_paths = gf
    else:
        control_paths = sc.get("control_read") or []

    control_body, _ = read_hit_files(control_paths)
    control_total = user_t + tok(control_body)

    find_payload_t = tok(compact(find_args)) + tok(compact(rules)) + tok(
        compact({"documents": docs, "links": links})
    )
    linked_paths = sc.get("linked_read") or []
    linked_body, _ = read_hit_files(linked_paths) if linked_paths else ("", [])
    linked_total = user_t + find_payload_t + tok(linked_body)

    rule_hits = [r for r in rules if (r.get("id") or "") == rule_id]
    link_kinds = sorted({lk.get("kind") for lk in links if lk.get("kind")})
    source_links = [lk for lk in links if lk.get("kind") == "sources"]

    audit = {}
    if sc.get("audit_get") and rule_id:
        gr = client.call_tool("get", {"id": rule_id})
        gobj = tool_json(gr)
        audit["get_rule"] = {
            "resolved_sources": gobj.get("resolved_sources"),
            "claim": gobj.get("claim"),
        }
        chunk_id = None
        for d in docs:
            if _norm_path(d.get("path")) == "docs/03-error-handling.md":
                chunk_id = d.get("id")
                break
        if chunk_id:
            cr = client.call_tool("get", {"id": chunk_id})
            cobj = tool_json(cr)
            audit["get_chunk"] = {
                "id": chunk_id,
                "path": cobj.get("path"),
                "heading": cobj.get("heading"),
                "referenced_rules": cobj.get("referenced_rules"),
            }

    saved = control_total - linked_total
    saving_pct = (saved / control_total * 100) if control_total else 0.0

    return {
        "id": sc["id"],
        "title": sc["title"],
        "advantage": sc["advantage"],
        "user_message": sc["user_message"],
        "rule_id": rule_id,
        "find_args": find_args,
        "control": {
            "paths": control_paths,
            "tokens": control_total,
            "read_tokens": tok(control_body),
        },
        "linked": {
            "find_rules_count": len(rules),
            "find_docs_count": len(docs),
            "find_links_count": len(links),
            "link_kinds": link_kinds,
            "source_link_count": len(source_links),
            "rules_sample": rules[:3],
            "documents_sample": docs,
            "links_sample": links[:8],
            "read_paths": linked_paths,
            "tokens": linked_total,
            "find_bundle_tokens": find_payload_t,
            "read_tokens": tok(linked_body),
        },
        "rule_recalled": bool(rule_hits),
        "saved_tokens": saved,
        "saving_pct": round(saving_pct, 2),
        "audit": audit,
    }


def main():
    vault_dir = os.path.join(PROJECT, LINK_VAULT)
    if os.path.isdir(vault_dir):
        shutil.rmtree(vault_dir)

    client = MCPClient(
        imprint_mcp(),
        ["--project", PROJECT, "--vault", LINK_VAULT],
        cwd=PROJECT,
    )
    client.initialize()
    seeded = []
    rows = []
    try:
        for sc in SCENARIOS:
            sd = sc["seed"]
            add_args = {
                "claim": sd["claim"],
                "scope": sd["scope"],
                "text": sd["text"],
                "query_local": sd.get("query_local"),
                "sources": sd.get("sources"),
            }
            ar = client.call_tool("add", add_args)
            out = extract_add_out(ar)
            rid = out.get("id")
            if out.get("error"):
                raise RuntimeError(f"add failed {sc['id']}: {out['error']}")
            seeded.append({"scenario": sc["id"], "rule_id": rid, "add_args": add_args})
            rows.append(run_scenario(client, sc, rid))
    finally:
        client.close()

    if os.path.isdir(vault_dir):
        shutil.rmtree(vault_dir)
    client2 = MCPClient(
        imprint_mcp(),
        ["--project", PROJECT, "--vault", LINK_VAULT],
        cwd=PROJECT,
    )
    client2.initialize()
    vault_rows = []
    try:
        vault_rows = run_vault_graph(client2)
    finally:
        client2.close()

    total_control = sum(r["control"]["tokens"] for r in rows)
    total_linked = sum(r["linked"]["tokens"] for r in rows)
    saved = total_control - total_linked
    pct = (saved / total_control * 100) if total_control else 0.0

    result = {
        "meta": {
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tokenizer": tokenizer.label(),
            "imprint_mcp": public_bin(),
            "vault": LINK_VAULT,
            "doc_scenarios": len(SCENARIOS),
            "vault_scenarios": len(vault_rows),
        },
        "comparison": {
            "baseline_arm": "无 vault 关联：用户消息 + grep 命中后 Read 规范文档全文（或宽 grep 全部命中篇）。",
            "experiment_arm": "vault sources + shelves：一次 find(scope, query) 得 rules、documents、links；按场景仅 Read sources 指向的篇目或零 Read。",
            "link_types_doc": "持久 sources（规则→文档）；find.links kind=sources；get chunk → referenced_rules。",
            "link_types_vault": "持久 supersedes / related / conflicts_with（规则→规则）；find → conflict_set；get / desk /graph → referenced_by 等。",
        },
        "seeded_rules": seeded,
        "rows": rows,
        "vault_rows": vault_rows,
        "final": {
            "control_total": total_control,
            "linked_total": total_linked,
            "saved_tokens": saved,
            "saving_pct": round(pct, 2),
            "rules_recalled": sum(1 for r in rows if r["rule_recalled"]),
            "vault_checks_passed": sum(1 for r in vault_rows if r.get("checks_passed")),
            "vault_checks_total": len(vault_rows),
        },
    }
    os.makedirs(DATA, exist_ok=True)
    out_path = os.path.join(DATA, "linking_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("wrote", out_path)
    print(json.dumps(result["final"], ensure_ascii=False))


if __name__ == "__main__":
    main()
