#!/usr/bin/env python3
"""imprint token-savings + find-accuracy benchmark.

Two scenarios over the same multi-round aurora dialogue:

  baseline — no persistent memory. Every round the FULL text of all rules
             established so far is re-injected into the prompt.
  memory   — real imprint-mcp over MCP stdio. New rules are written once
             via `add`; later rounds `find` the relevant rules.

Token counting uses the public Grok-family tokenizer (see tokenizer.py).
Find accuracy: expected rules are those already stored whose scope tags
are a superset of the round's find_scope (AND).
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
from paths import BASE, DATA, PROJECT, TOKEN_VAULT, imprint_mcp, public_bin

SYSTEM = (
    "你是 aurora 项目的资深后端工程师。aurora 是一个 Python FastAPI 微服务。"
    "请严格遵循下方提供的项目规范完成每个任务，回答简洁、可直接落地为代码。"
)


def tok(s):
    return tokenizer.count(s)


def compact(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def shared_prompt(rd):
    return f"{SYSTEM}\n\n【用户消息】\n{rd['user_message']}\n\n【任务】\n{rd['task']}"


RULES_HEADER = "\n\n【项目规范】\n"


def rules_block(texts):
    return "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))


def scope_tags(s):
    return {t.strip() for t in (s or "").split(",") if t.strip()}


def extract_rules(resp):
    r = resp.get("result", {})
    sc = r.get("structuredContent")
    if isinstance(sc, dict) and "rules" in sc:
        return sc["rules"]
    content = r.get("content", [])
    if content:
        try:
            obj = json.loads(content[0].get("text", ""))
            if isinstance(obj, dict) and "rules" in obj:
                return obj["rules"]
        except Exception:
            pass
    return []


def extract_shelves(resp):
    r = resp.get("result", {})
    sc = r.get("structuredContent")
    if isinstance(sc, dict):
        return {"documents": sc.get("documents", []), "links": sc.get("links", [])}
    content = r.get("content", [])
    if content:
        try:
            obj = json.loads(content[0].get("text", ""))
            return {"documents": obj.get("documents", []), "links": obj.get("links", [])}
        except Exception:
            pass
    return {"documents": [], "links": []}


def resp_full_text_tokens(resp):
    content = resp.get("result", {}).get("content", [])
    s = ""
    for c in content:
        if isinstance(c, dict) and c.get("type") == "text":
            s += c.get("text", "") + "\n"
    return tok(s)


def extract_add_out(ar):
    r = ar.get("result", {})
    sc = r.get("structuredContent")
    if isinstance(sc, dict) and "id" in sc:
        return {"id": sc.get("id"), "confidence": sc.get("confidence"),
                "error": sc.get("error")}
    content = r.get("content", [])
    if content:
        try:
            obj = json.loads(content[0].get("text", ""))
            return {"id": obj.get("id"), "confidence": obj.get("confidence"),
                    "error": obj.get("error")}
        except Exception:
            pass
    if "error" in ar:
        return {"id": None, "error": ar["error"]}
    return {}


def expected_rules(catalog, find_scope):
    want = scope_tags(find_scope)
    return [r for r in catalog if want <= scope_tags(r["scope"])]


def run_baseline(dialogues):
    rows = []
    texts = []
    for rd in dialogues["rounds"]:
        shared_t = tok(shared_prompt(rd))
        inj = (RULES_HEADER + rules_block(texts)) if texts else ""
        rules_t = tok(inj) if inj else 0
        rows.append({
            "round": rd["round"],
            "phase": rd.get("phase", ""),
            "rules_in_context": len(texts),
            "shared_tokens": shared_t,
            "rules_fulltext_tokens": rules_t,
            "rules_injection_text": inj,
            "total_input_tokens": shared_t + rules_t,
        })
        for nr in rd["new_rules"]:
            texts.append(nr["text"])
    return rows


def run_memory(dialogues):
    vault_dir = os.path.join(PROJECT, TOKEN_VAULT)
    if os.path.isdir(vault_dir):
        shutil.rmtree(vault_dir)
    client = MCPClient(imprint_mcp(),
                       ["--project", PROJECT, "--vault", TOKEN_VAULT],
                       cwd=PROJECT)
    client.initialize()
    rows = []
    catalog = []
    try:
        for rd in dialogues["rounds"]:
            shared_t = tok(shared_prompt(rd))
            expected = expected_rules(catalog, rd["find_scope"])
            expect_claims = {r["claim"] for r in expected}

            find_args = {"scope": rd["find_scope"], "query": rd["find_query"],
                         "query_local": rd["find_query_local"], "top_k": 5}
            fr = client.call_tool("find", find_args)
            rules = extract_rules(fr)
            shelves = extract_shelves(fr)
            got_claims = []
            for rule in rules:
                c = (rule.get("claim") or "").strip()
                if c:
                    got_claims.append(c)
            got_set = set(got_claims)
            hit = expect_claims & got_set
            precision = (len(hit) / len(got_set)) if got_set else (1.0 if not expect_claims else 0.0)
            recall = (len(hit) / len(expect_claims)) if expect_claims else 1.0

            add_req_t = 0
            add_resp_t = 0
            add_ids = []
            add_errors = []
            for nr in rd["new_rules"]:
                add_args = {"claim": nr["claim"], "scope": nr["scope"],
                            "text": nr["text"], "query_local": nr["query_local"]}
                ar = client.call_tool("add", add_args)
                add_out = extract_add_out(ar)
                add_req_t += tok(compact(add_args))
                add_resp_t += tok(compact(add_out))
                add_ids.append(add_out.get("id"))
                if add_out.get("error"):
                    add_errors.append(str(add_out["error"]))
                catalog.append(nr)

            find_req_t = tok(compact(find_args))
            find_rules_t = tok(compact(rules))
            find_shelves_t = tok(compact(shelves))

            rows.append({
                "round": rd["round"],
                "phase": rd.get("phase", ""),
                "shared_tokens": shared_t,
                "shared_prompt_text": shared_prompt(rd),
                "find_args": find_args,
                "find_rules": rules,
                "rules_recalled": len(rules),
                "expected_count": len(expect_claims),
                "hit_count": len(hit),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "expected_claims": sorted(expect_claims),
                "recalled_claims": got_claims,
                "find_req_tokens": find_req_t,
                "find_rules_tokens": find_rules_t,
                "find_shelves_tokens": find_shelves_t,
                "find_full_text_tokens": resp_full_text_tokens(fr),
                "add_req_tokens": add_req_t,
                "add_resp_tokens": add_resp_t,
                "add_rule_ids": add_ids,
                "add_errors": add_errors,
                "core_input_tokens": (shared_t + find_req_t + find_rules_t
                                      + add_req_t + add_resp_t),
                "total_with_shelves": (shared_t + find_req_t + find_rules_t
                                       + find_shelves_t + add_req_t + add_resp_t),
            })
    finally:
        client.close()
    return rows


def summarize(base_rows, mem_rows):
    bc = mc = msc = 0
    out = []
    for b, m in zip(base_rows, mem_rows):
        bc += b["total_input_tokens"]
        mc += m["core_input_tokens"]
        msc += m["total_with_shelves"]
        out.append({
            "round": b["round"],
            "phase": b.get("phase", ""),
            "baseline_cum": bc,
            "memory_core_cum": mc,
            "memory_with_shelves_cum": msc,
            "saved_cum": bc - mc,
            "saving_pct": round((bc - mc) / bc * 100, 2) if bc else 0.0,
            "precision": m["precision"],
            "recall": m["recall"],
        })
    return out


def comparison_meta(dialogues):
    meta = dialogues.get("meta") or {}
    return {
        "question": "vault 实验组相对什么 baseline 省 token？",
        "baseline_arm": (
            "无持久化记忆：每轮把 dialogues.json 里迄今全部 new_rules[].text "
            "以「【项目规范】」编号列表全文塞进 prompt；不调用 imprint。"
        ),
        "experiment_arm": (
            "imprint vault（.imprint/vault.db）：新规只 add 一次；之后每轮仅计入 "
            "MCP find 请求 + 命中 rules 紧凑 JSON（及写入期 add 往返）。"
        ),
        "excluded_from_both_arms": [
            "Cursor alwaysApply 规则（如 .cursor/rules/imprint-memory.mdc）",
            "AGENTS.md、imprint init 嵌入的 body.md 等编辑器级系统提示",
            "desk / host HTTP、CLI 非 MCP 路径",
        ],
        "shared_in_both_arms": (
            "同一 SYSTEM 说明 + dialogues 当轮 user_message + task（见 measure.py SYSTEM）"
        ),
        "corpus": "experiment/dialogues.json",
        "corpus_note": meta.get("note") or "",
        "rules_source_field": "new_rules[].text（用户原话级规范正文，非 claim  alone）",
    }


def transparency_samples(dialogues, base_rows, mem_rows):
    by_round_b = {r["round"]: r for r in base_rows}
    by_round_m = {r["round"]: r for r in mem_rows}
    build_end = dialogues["meta"]["build_rounds"]
    first_comply = build_end + 1
    out = {}
    for label, rnd in [("last_build_round", build_end), ("first_comply_round", first_comply)]:
        b = by_round_b.get(rnd)
        m = by_round_m.get(rnd)
        rd = next(x for x in dialogues["rounds"] if x["round"] == rnd)
        if not b or not m:
            continue
        out[label] = {
            "round": rnd,
            "phase": b.get("phase"),
            "baseline": {
                "shared_prompt": shared_prompt(rd),
                "rules_injection": b.get("rules_injection_text") or "",
                "tokens": {
                    "shared": b["shared_tokens"],
                    "rules_fulltext": b["rules_fulltext_tokens"],
                    "total": b["total_input_tokens"],
                },
            },
            "memory_core": {
                "shared_prompt": m.get("shared_prompt_text") or shared_prompt(rd),
                "find_request_json": compact(m.get("find_args") or {}),
                "find_rules_json": compact(m.get("find_rules") or []),
                "tokens": {
                    "shared": m["shared_tokens"],
                    "find_req": m["find_req_tokens"],
                    "find_rules": m["find_rules_tokens"],
                    "add_req": m["add_req_tokens"],
                    "add_resp": m["add_resp_tokens"],
                    "core_total": m["core_input_tokens"],
                },
            },
        }
    return out


def accuracy_rollups(mem_rows):
    comply = [m for m in mem_rows if m.get("phase") == "comply"]
    all_rows = mem_rows
    def avg(rows, key):
        if not rows:
            return 0.0
        return round(sum(r[key] for r in rows) / len(rows), 4)
    return {
        "all_rounds_mean_precision": avg(all_rows, "precision"),
        "all_rounds_mean_recall": avg(all_rows, "recall"),
        "comply_mean_precision": avg(comply, "precision"),
        "comply_mean_recall": avg(comply, "recall"),
        "comply_rounds": len(comply),
        "perfect_comply": sum(1 for r in comply if r["precision"] == 1 and r["recall"] == 1),
    }


def main():
    dlg_path = os.path.join(BASE, "dialogues.json")
    if not os.path.isfile(dlg_path):
        raise SystemExit("run gen_dialogues.py first")
    with open(dlg_path, encoding="utf-8") as f:
        dialogues = json.load(f)

    base_rows = run_baseline(dialogues)
    mem_rows = run_memory(dialogues)
    summary = summarize(base_rows, mem_rows)
    acc = accuracy_rollups(mem_rows)

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "baseline.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "baseline", "rows": base_rows}, f,
                  ensure_ascii=False, indent=2)
    with open(os.path.join(DATA, "with_memory.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "memory", "rows": mem_rows}, f,
                  ensure_ascii=False, indent=2)
    result = {
        "meta": {
            "imprint_mcp": public_bin(),
            "tokenizer": tokenizer.label(),
            "scenario": "项目约定/规范协作",
            "rounds": len(dialogues["rounds"]),
            "vault": TOKEN_VAULT,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "comparison": comparison_meta(dialogues),
        },
        "samples": transparency_samples(dialogues, base_rows, mem_rows),
        "summary": summary,
        "accuracy": acc,
        "final": {
            "baseline_total": summary[-1]["baseline_cum"],
            "memory_core_total": summary[-1]["memory_core_cum"],
            "memory_with_shelves_total": summary[-1]["memory_with_shelves_cum"],
            "saved_tokens": summary[-1]["saved_cum"],
            "saving_pct": summary[-1]["saving_pct"],
        },
    }
    with open(os.path.join(DATA, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"final": result["final"], "accuracy": acc,
                      "tokenizer": tokenizer.label()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
