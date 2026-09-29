"""Load logical → imprint id map for record.html (desk .imprint vault)."""
from __future__ import annotations

import json
import os

from paths import DATA, LINK_VAULT, PROJECT

STATE_PATHS = (
    os.path.join(PROJECT, LINK_VAULT, "state", "record-vault-seed.json"),
    os.path.join(PROJECT, ".imprint", "state", "record-vault-seed.json"),
)
DATA_COPY = os.path.join(DATA, "record_vault_map.json")


def load_id_map() -> dict[str, str]:
    logical: dict[str, str] = {}
    for path in (*STATE_PATHS, DATA_COPY):
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            blob = json.load(f)
        for k, v in (blob.get("logical") or {}).items():
            if v and v != "linked":
                logical[k] = v
    return logical


def resolve(id_map: dict[str, str], key: str, fallback: str = "") -> str:
    return id_map.get(key) or fallback


def rule_key(case_id: str, node_id: str) -> str:
    return f"{case_id}:{node_id}"


def bench_key(scenario_id: str) -> str:
    return f"bench:{scenario_id}"


def copy_state_to_data(state_path: str | None = None) -> str | None:
    src = state_path
    if not src:
        for candidate in STATE_PATHS:
            if os.path.isfile(candidate):
                src = candidate
                break
    if not os.path.isfile(src):
        return None
    with open(src, encoding="utf-8") as f:
        blob = json.load(f)
    os.makedirs(DATA, exist_ok=True)
    with open(DATA_COPY, "w", encoding="utf-8") as f:
        json.dump(blob, f, ensure_ascii=False, indent=2)
    return DATA_COPY
