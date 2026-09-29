#!/usr/bin/env python3
"""Measure find precision vs agent-style grep under the grep→find(paths)→Read protocol.

Outputs experiment/data/retrieval_precision.json consumed by
build_retrieval_report.py.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_client import MCPClient
import tokenizer
from measure_retrieval import (
    QUERIES, extract_documents, indexed_grep_paths, intersect_grep_find,
    host_default_read_files, _norm_path, _same_path,
)
import agent_search
from paths import DATA, PROJECT, RETRIEVAL_VAULT, imprint_mcp, find_top_k

FUZZ = [
    {"kind": "combo", "guess": "性能 缓存", "note": "性能与缓存分属多篇，目标在缓存策略",
     "target": "docs/10-performance.md"},
    {"kind": "combo", "guess": "连接池 超时", "note": "连接池与超时在库、观测、出站客户端中均出现",
     "target": "docs/04-database.md"},
    {"kind": "combo", "guess": "灰度发布 回滚", "note": "问句专名是灰度发布，蒸馏保留复合词与回滚",
     "target": "docs/08-deployment.md"},
    {"kind": "combo", "guess": "密钥 明文", "note": "密钥与明文在安全、配置、部署中均出现",
     "target": "docs/09-security.md"},
    {"kind": "combo", "guess": "幂等 重试", "note": "幂等与重试分散在异常、队列、HTTP、API；问句对应重试策略",
     "target": "docs/03-error-handling.md"},
    {"kind": "combo", "guess": "缓存 过期", "note": "缓存与过期日分别出现在性能与功能开关",
     "target": "docs/10-performance.md"},
    {"kind": "combo", "guess": "采样 追踪", "note": "采样与追踪在可观测性重合，日志与出站也沾边",
     "target": "docs/11-observability.md"},
    {"kind": "combo", "guess": "SQL 拼接", "note": "拼接出现在风格、日志、国际化；目标为参数化 SQL",
     "target": "docs/09-security.md"},
    {"kind": "combo", "guess": "镜像 缓存", "note": "镜像在部署与 i18n，缓存在性能与构建",
     "target": "docs/08-deployment.md"},
    {"kind": "combo", "guess": "批量 循环", "note": "循环出现在风格、架构、数据库；目标为禁止逐条查询",
     "target": "docs/10-performance.md"},
    {"kind": "combo", "guess": "trace_id 日志", "note": "trace_id 与日志在多篇交叉",
     "target": "docs/06-logging.md"},
    {"kind": "combo", "guess": "ISO8601 存储", "note": "ISO8601 同时出现在库、接口、国际化",
     "target": "docs/04-database.md"},
    {"kind": "combo", "guess": "死信 重试", "note": "重试出现在异常与 HTTP；目标为死信队列",
     "target": "docs/12-concurrency.md"},
    {"kind": "combo", "guess": "连接池 水位", "note": "连接池在库与 HTTP 客户端；目标为容量水位",
     "target": "docs/11-observability.md"},
    {"kind": "combo", "guess": "脱敏 日志", "note": "日志与脱敏在多篇出现；目标为日志敏感信息",
     "target": "docs/06-logging.md"},
    {"kind": "combo", "guess": "限流 降级", "note": "降级亦出现在队列背压",
     "target": "docs/10-performance.md"},
    {"kind": "ident", "guess": "repository", "note": "大小写与文档中的 Repository 不一致",
     "target": "docs/02-architecture.md"},
    {"kind": "ident", "guess": "snake case", "note": "空格与下划线 snake_case 不一致",
     "target": "docs/01-python-style.md"},
    {"kind": "ident", "guess": "messageid", "note": "连写，文档中为 message_id",
     "target": "docs/12-concurrency.md"},
    {"kind": "ident", "guess": "fstring", "note": "连写，文档中为 f-string",
     "target": "docs/01-python-style.md"},
    {"kind": "ident", "guess": "soft-delete", "query_local": "软删除",
     "note": "连字符与中文专名并用",
     "target": "docs/04-database.md"},
    {"kind": "ident", "guess": "DLQ", "query_local": "死信队列",
     "note": "英文缩写与中文专名并用",
     "target": "docs/12-concurrency.md"},
    {"kind": "ident", "guess": "openapi", "note": "大小写与 OpenAPI 不一致",
     "target": "docs/05-api-design.md"},
    {"kind": "ident", "guess": "featureflag", "query_local": "功能开关",
     "note": "英文连写与中文专名并用",
     "target": "docs/14-config.md"},
]


def tail(s):
    return s.split("/", 1)[1] if "/" in s else s


def grep_files(query, query_local=None):
    patterns = agent_search.distill_patterns(query, query_local)
    return patterns, agent_search.search_files(PROJECT, patterns)


def rank_of(docs, target):
    t = tail(target)
    for i, d in enumerate(docs, 1):
        if t in json.dumps(d, ensure_ascii=False):
            return i
    return None


def find_docs(client, query, query_local=None, grep_list=None, k=3):
    args = {"scope": "aurora", "query": query}
    if query_local:
        args["query_local"] = query_local
    indexed = indexed_grep_paths(grep_list or [])
    if len(indexed) > k:
        args["paths"] = indexed
    fr = client.call_tool("find", args)
    return extract_documents(fr), args


def main():
    k = find_top_k(PROJECT)
    client = MCPClient(imprint_mcp(),
                       ["--project", PROJECT, "--vault", RETRIEVAL_VAULT],
                       cwd=PROJECT)
    client.initialize()
    try:
        canonical = []
        hi = 0
        for q in QUERIES:
            _, gf = grep_files(q["query"], q.get("query_local"))
            docs, _ = find_docs(client, q["query"], q.get("query_local"), gf, k)
            r = rank_of(docs, q["target_file"])
            if r == 1:
                hi += 1
            canonical.append({
                "qid": q["qid"], "query": q["query"], "target": q["target_file"],
                "rank": r,
                "top": [{"path": d.get("path", ""), "score": d.get("score"),
                         "snippet": (d.get("snippet", "") or "")[:60]}
                        for d in docs],
            })

        fuzz = []
        for c in FUZZ:
            patterns, gf = grep_files(c["guess"], c.get("query_local"))
            indexed = indexed_grep_paths(gf)
            wide = len(indexed) > k
            docs, find_args = find_docs(client, c["guess"], c.get("query_local"), gf, k)
            r = rank_of(docs, c["target"])
            paths = [_norm_path(d.get("path")) for d in docs]
            if wide:
                read_paths = intersect_grep_find(indexed, paths)
                if not read_paths:
                    read_paths = host_default_read_files(indexed, gf)
            else:
                read_paths = host_default_read_files(indexed, gf)
            fuzz.append({
                "kind": c.get("kind") or "combo",
                "guess": c["guess"],
                "query_local": c.get("query_local"),
                "note": c["note"], "target": c["target"],
                "search_patterns": patterns,
                "grep_files": gf,
                "grep_hit_target": any(tail(c["target"]) == tail(g) for g in gf),
                "used_find_paths": wide,
                "find_paths": paths,
                "read_paths": read_paths,
                "find_rank": r,
                "shelves_paths": paths,
                "shelves_rank": r,
            })
    finally:
        client.close()

    result = {
        "meta": {"queries": len(QUERIES), "fuzz_cases": len(FUZZ),
                 "combo_cases": len([c for c in FUZZ if c.get("kind") == "combo"]),
                 "ident_cases": len([c for c in FUZZ if c.get("kind") == "ident"]),
                 "tokenizer": tokenizer.label(),
                 "control_search": agent_search.tool_label(),
                 "find_top_k": k},
        "canonical_precision": {
            "precision_at_1": hi, "total": len(QUERIES),
            "recall_at_k": len([c for c in canonical if c["rank"]]),
        },
        "canonical": canonical,
        "fuzz": fuzz,
    }
    os.makedirs(DATA, exist_ok=True)
    out = os.path.join(DATA, "retrieval_precision.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("wrote", out)
    print(json.dumps(result["canonical_precision"], ensure_ascii=False))


if __name__ == "__main__":
    main()
