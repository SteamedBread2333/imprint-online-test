#!/usr/bin/env python3
"""Seed record.html rules + graph edges into the project vault (default .imprint).

Covers:
  - §5 narrative graphs (record_graph_data.CASE_GRAPHS)
  - §3 doc-link scenarios (measure_linking.SCENARIOS) when not already present
  - §4 vault-graph demos (supersede camelCase, extra related) when not redundant

Re-run is idempotent via .imprint/state/record-vault-seed.json mapping.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_client import MCPClient
from measure import extract_add_out
from measure_linking import SCENARIOS, tool_json
from paths import LINK_VAULT, PROJECT, imprint_mcp
from record_graph_data import CASE_GRAPHS
from record_vault_map import copy_state_to_data

STATE_NAME = "record-vault-seed.json"
RECORD_TAG = "record"


def state_path(vault_rel: str) -> str:
    root = vault_rel if os.path.isabs(vault_rel) else os.path.join(PROJECT, vault_rel)
    return os.path.join(root, "state", STATE_NAME)


def load_state(path: str) -> dict:
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"logical": {}, "imprint_ids": []}


def save_state(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def scope_tags(node: dict) -> str:
    tags = list(node.get("scope") or [])
    if RECORD_TAG not in tags:
        tags.append(RECORD_TAG)
    return ",".join(tags)


def sources_for(rule_key: str, spec: dict) -> list[dict] | None:
    nodes = {n["id"]: n for n in spec["nodes"]}
    out: list[dict] = []
    for e in spec.get("edges") or []:
        if e.get("kind") != "sources" or e.get("source") != rule_key:
            continue
        doc = nodes.get(e.get("target"))
        if not doc or doc.get("kind") != "document":
            continue
        ref: dict = {"path": doc["path"]}
        if doc.get("heading"):
            ref["heading"] = doc["heading"]
        out.append(ref)
    return out or None


def clean_add_kwargs(kwargs: dict) -> dict:
    out = {k: v for k, v in kwargs.items() if v is not None}
    if out.get("sources") is None:
        out.pop("sources", None)
    return out


def parse_tool_error(ar: dict) -> dict | None:
    r = ar.get("result") or {}
    if not r.get("isError"):
        return None
    for c in r.get("content") or []:
        if isinstance(c, dict) and c.get("type") == "text":
            try:
                return json.loads(c.get("text") or "{}")
            except json.JSONDecodeError:
                return {"error": c.get("text")}
    return None


def mcp_add(client: MCPClient, logical: str, state: dict, reuse_similar: bool = True, **kwargs) -> str:
    if logical in state["logical"]:
        return state["logical"][logical]
    ar = client.call_tool("add", clean_add_kwargs(kwargs))
    out = extract_add_out(ar)
    rid = out.get("id")
    if not rid:
        err = parse_tool_error(ar) or {}
        if reuse_similar and err.get("code") == "duplicate":
            cands = err.get("candidates") or []
            if cands and cands[0].get("id"):
                rid = cands[0]["id"]
        if not rid:
            msg = out.get("error") or err.get("error") or ar
            raise RuntimeError(f"add {logical}: {msg}")
    state["logical"][logical] = rid
    if rid not in state["imprint_ids"]:
        state["imprint_ids"].append(rid)
    return rid


def mcp_supersede(client: MCPClient, logical_new: str, old_id: str, state: dict, node: dict, sources) -> str:
    key = f"{logical_new}:active"
    if key in state["logical"]:
        return state["logical"][key]
    sup = {
        "old_id": old_id,
        "claim": node["claim"],
        "scope": scope_tags(node),
        "text": node.get("text") or node["claim"],
        "reason": "record seed",
        "sources": sources,
    }
    if node.get("query_local"):
        sup["query_local"] = node["query_local"]
    sr = client.call_tool("supersede", clean_add_kwargs(sup))
    obj = tool_json(sr)
    rid = obj.get("id") or extract_add_out(sr).get("id")
    if not rid:
        raise RuntimeError(f"supersede {logical_new}: {sr}")
    state["logical"][logical_new] = rid
    state["logical"][key] = rid
    if rid not in state["imprint_ids"]:
        state["imprint_ids"].append(rid)
    return rid


def seed_case(client: MCPClient, case_id: str, spec: dict, state: dict) -> None:
    prefix = f"{case_id}:"
    rules = {n["id"]: n for n in spec["nodes"] if n.get("kind") != "document"}
    edges = spec.get("edges") or []
    idmap: dict[str, str] = {}

    for rid, node in rules.items():
        if node.get("status") == "superseded":
            lk = prefix + rid
            idmap[rid] = mcp_add(
                client,
                lk,
                state,
                claim=node["claim"],
                scope=scope_tags(node),
                text=node.get("text") or node["claim"],
                query_local=node.get("query_local"),
            )

    for e in edges:
        if e.get("kind") != "supersedes":
            continue
        new_key, old_key = e["source"], e["target"]
        new_node = rules[new_key]
        src = sources_for(new_key, spec)
        old_imprint = idmap.get(old_key) or state["logical"].get(prefix + old_key)
        if not old_imprint:
            raise RuntimeError(f"{case_id}: missing old rule for supersede {old_key}")
        idmap[new_key] = mcp_supersede(
            client, prefix + new_key, old_imprint, state, new_node, src
        )

    for rid, node in rules.items():
        if rid in idmap:
            continue
        lk = prefix + rid
        src = sources_for(rid, spec)
        conflicts = None
        for e in edges:
            if e.get("kind") == "conflicts_with" and e.get("target") == rid:
                src_key = e.get("source")
                other = idmap.get(src_key) or state["logical"].get(prefix + src_key)
                if other:
                    conflicts = other
                    break
        add_kw = {
            "claim": node["claim"],
            "scope": scope_tags(node),
            "text": node.get("text") or node["claim"],
            "query_local": node.get("query_local"),
            "sources": src,
        }
        if conflicts:
            add_kw["conflicts"] = conflicts
        idmap[rid] = mcp_add(client, lk, state, **add_kw)

    for e in edges:
        if e.get("kind") != "related":
            continue
        a = idmap.get(e["source"]) or state["logical"].get(prefix + e["source"])
        b = idmap.get(e["target"]) or state["logical"].get(prefix + e["target"])
        if not a or not b:
            continue
        client.call_tool("link", {"id": a, "related": b})


def seed_linking_scenarios(client: MCPClient, state: dict) -> None:
    for sc in SCENARIOS:
        lk = f"bench:{sc['id']}"
        if lk in state["logical"]:
            continue
        sd = sc["seed"]
        mcp_add(
            client,
            lk,
            state,
            claim=sd["claim"],
            scope=sd["scope"] + f",{RECORD_TAG}",
            text=sd["text"],
            query_local=sd.get("query_local"),
            sources=sd.get("sources"),
        )


def seed_vault_extras(client: MCPClient, state: dict) -> None:
    """camelCase supersede + quality related to case_b retry (if present)."""
    if "bench:v1_supersede:old" not in state["logical"]:
        old_id = mcp_add(
            client,
            "bench:v1_supersede:old",
            state,
            claim="Use camelCase for Python function names in aurora",
            scope=f"aurora,python,{RECORD_TAG}",
            text="历史约定：函数名用 camelCase（已废弃，仅作对照）。",
            query_local="camelCase 函数名 命名",
        )
        mcp_supersede(
            client,
            "bench:v1_supersede:new",
            old_id,
            state,
            {
                "claim": "Use snake_case for functions/variables and PascalCase for classes",
                "text": "函数和变量统一 snake_case，类名 PascalCase。",
                "scope": ["aurora", "python"],
            },
            None,
        )

    retry_key = "case_b:r-retry"
    ruff_key = "case_e:r-ruff"
    retry_id = state["logical"].get(retry_key)
    ruff_id = state["logical"].get(ruff_key)
    if retry_id and ruff_id and "bench:v3_related" not in state["logical"]:
        client.call_tool("link", {"id": ruff_id, "related": retry_id})
        state["logical"]["bench:v3_related"] = "linked"


def seed_vault(
    vault_rel: str,
    *,
    force: bool = False,
    include_bench_scenarios: bool = True,
    include_vault_extras: bool = True,
    include_cases: bool = True,
) -> dict:
    sp = state_path(vault_rel)
    if force and os.path.isfile(sp):
        os.remove(sp)
    state = load_state(sp)

    client = MCPClient(
        imprint_mcp(),
        ["--project", PROJECT, "--vault", vault_rel],
        cwd=PROJECT,
    )
    client.initialize()
    try:
        if include_cases:
            for case_id in sorted(CASE_GRAPHS.keys()):
                seed_case(client, case_id, CASE_GRAPHS[case_id], state)
        if include_bench_scenarios:
            seed_linking_scenarios(client, state)
        if include_vault_extras:
            seed_vault_extras(client, state)
    finally:
        client.close()

    save_state(sp, state)
    copy_state_to_data(sp)
    return state


def merge_bench_state(vault_rel: str, logical_ids: dict[str, str]) -> None:
    """Attach §3–§4 measure_linking rule ids before seeding §5 cases."""
    sp = state_path(vault_rel)
    state = load_state(sp)
    for k, v in logical_ids.items():
        if v and v != "linked":
            state["logical"][k] = v
            if v not in state["imprint_ids"]:
                state["imprint_ids"].append(v)
    save_state(sp, state)


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed record report graph into imprint vault")
    ap.add_argument(
        "--vault",
        default=LINK_VAULT,
        help=f"vault directory (default {LINK_VAULT})",
    )
    ap.add_argument("--force", action="store_true", help="ignore existing state and re-seed (may duplicate)")
    args = ap.parse_args()

    state = seed_vault(args.vault, force=args.force)
    sp = state_path(args.vault)
    copied = copy_state_to_data(sp)
    print(f"wrote {sp}")
    if copied:
        print(f"copied map → {copied} (for record.html build)")
    print(f"seeded {len(state['imprint_ids'])} imprint rules (scope tag `{RECORD_TAG}` on record layer)")
    print("restart host if running: imprint down && imprint up && imprint desk open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
