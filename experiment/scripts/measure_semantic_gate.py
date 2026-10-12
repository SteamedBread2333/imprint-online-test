#!/usr/bin/env python3
"""End-to-end semantic write gate: duplicate / conflict / unrelated calibration pairs.

Requires a live imprint-embed-sidecar on IMPRINT_EMBED_URL (default :4174) with
ready=true. Uses imprint CLI add on an isolated temp vault (embed enabled).
Sample pairs come from sidecar samples.py (20+20+20).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, embed_url, imprint_bin, public_bin, sidecar_dir

SIDECAR = sidecar_dir()
sys.path.insert(0, SIDECAR)
from samples import CONFLICT, DUPLICATE, UNRELATED  # noqa: E402

THRESHOLDS = {
    "duplicate_threshold": 0.65,
    "relate_contradiction_min": 0.40,
    "relate_entailment_min": 0.35,
    "relate_bidirectional": True,
    "duplicate_high_cosine_block": 0.80,
    "timeout_seconds": 8,
    "model": "BAAI/bge-small-zh-v1.5",
    "relate_model": "cross-encoder/nli-deberta-v3-base",
}


def health_ready() -> bool:
    url = f"{embed_url()}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return b'"ready": true' in resp.read()
    except (OSError, urllib.error.URLError):
        return False


def write_embed_bench_yaml(workdir: str) -> None:
    pkg = SIDECAR.replace("\\", "/")
    cfg = THRESHOLDS
    body = textwrap.dedent(
        f"""\
        host:
          listen: 127.0.0.1:9470
        plugins:
          embed:
            enabled: true
            package: {pkg}
            config:
              port: 4174
              model: {cfg["model"]}
              relate_model: {cfg["relate_model"]}
              duplicate_threshold: {cfg["duplicate_threshold"]}
              relate_contradiction_min: {cfg["relate_contradiction_min"]}
              relate_entailment_min: {cfg["relate_entailment_min"]}
              relate_bidirectional: true
              duplicate_high_cosine_block: {cfg["duplicate_high_cosine_block"]}
              timeout_seconds: {cfg["timeout_seconds"]}
        """
    )
    with open(os.path.join(workdir, "imprint.yaml"), "w", encoding="utf-8") as f:
        f.write(body)


def ensure_sidecar_ready(workdir: str, bin_path: str) -> None:
    if health_ready():
        print("embed sidecar ready", flush=True)
        return
    print("starting embed plugin (sidecar must be installed; see sidecar scripts/setup.sh)", flush=True)
    subprocess.check_call([bin_path, "plugin", "start", "embed"], cwd=workdir)
    deadline = time.time() + 180
    while time.time() < deadline:
        if health_ready():
            print("embed sidecar ready", flush=True)
            return
        time.sleep(1)
    raise RuntimeError(f"sidecar not ready on {embed_url()} after 180s")


def imprint_add(vault: str, workdir: str, bin_path: str, claim: str, scope: str, text: str) -> dict:
    cmd = [
        bin_path,
        "--vault",
        vault,
        "--json",
        "add",
        claim,
        "--scope",
        scope,
        "--text",
        text,
    ]
    proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
    raw = (proc.stdout or proc.stderr or "").strip()
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"_error": raw, "_code": proc.returncode}


def run_pair_group(
    group: str,
    pairs: list[tuple[str, str]],
    vault: str,
    workdir: str,
    bin_path: str,
    *,
    mode: str,
) -> list[dict]:
    rows: list[dict] = []
    for i, (a, b) in enumerate(pairs):
        scope = f"gate-{group}-{i:02d}"
        r1 = imprint_add(vault, workdir, bin_path, a, scope, "seed")
        row: dict = {
            "index": i,
            "group": group,
            "claim_a": a,
            "claim_b": b,
            "seed_ok": "id" in r1,
            "seed_id": r1.get("id"),
        }
        if "id" not in r1:
            row["outcome"] = "seed_failed"
            row["ok"] = False
            row["detail"] = r1
            rows.append(row)
            continue
        r2 = imprint_add(vault, workdir, bin_path, b, scope, "second")
        code = r2.get("code")
        similar = r2.get("similar") or []
        candidates = r2.get("candidates") or []
        row["second_code"] = code
        row["second_id"] = r2.get("id")
        row["similar_count"] = len(similar)
        row["similar_ids"] = [s.get("id") for s in similar if isinstance(s, dict)]
        row["candidate_count"] = len(candidates)
        row["candidate_ids"] = [s.get("id") for s in candidates if isinstance(s, dict)]

        if mode == "duplicate":
            row["ok"] = code == "duplicate"
            row["outcome"] = "blocked_duplicate" if row["ok"] else "missed_duplicate"
        elif mode == "conflict":
            false_block = code == "duplicate"
            added = "id" in r2
            if false_block:
                row["ok"] = False
                row["outcome"] = "false_duplicate_block"
            elif similar:
                row["ok"] = True
                row["outcome"] = "advisory_similar"
            elif added:
                row["ok"] = True
                row["outcome"] = "added_ok"
            else:
                row["ok"] = False
                row["outcome"] = "unexpected"
        else:  # unrelated
            false_block = code == "duplicate"
            added = "id" in r2
            row["ok"] = not false_block and added
            if false_block:
                row["outcome"] = "false_duplicate_block"
            elif added:
                row["outcome"] = "added_ok"
            else:
                row["outcome"] = "unexpected"
        rows.append(row)
    return rows


def summarize(rows: list[dict], total: int) -> dict:
    ok = sum(1 for r in rows if r.get("ok"))
    return {"total": total, "passed": ok, "failed": total - ok}


def main() -> int:
    os.makedirs(DATA, exist_ok=True)
    bin_path = imprint_bin()
    bench_dir = tempfile.mkdtemp(prefix="imprint-semantic-gate-")
    vault = os.path.join(bench_dir, "vault")
    try:
        write_embed_bench_yaml(bench_dir)
        ensure_sidecar_ready(bench_dir, bin_path)

        dup_rows = run_pair_group("duplicate", DUPLICATE, vault, bench_dir, bin_path, mode="duplicate")
        con_rows = run_pair_group("conflict", CONFLICT, vault, bench_dir, bin_path, mode="conflict")
        un_rows = run_pair_group("unrelated", UNRELATED, vault, bench_dir, bin_path, mode="unrelated")

        dup_s = summarize(dup_rows, len(DUPLICATE))
        con_s = summarize(con_rows, len(CONFLICT))
        un_s = summarize(un_rows, len(UNRELATED))
        con_advisory = sum(1 for r in con_rows if r.get("outcome") == "advisory_similar")
        con_false = sum(1 for r in con_rows if r.get("outcome") == "false_duplicate_block")
        un_false = sum(1 for r in un_rows if r.get("outcome") == "false_duplicate_block")

        dup_recall = dup_s["passed"] / dup_s["total"] * 100 if dup_s["total"] else 0.0
        passed = dup_s["failed"] == 0 and con_false == 0 and un_false == 0

        out = {
            "meta": {
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "imprint_bin": public_bin(bin_path),
                "embed_url": embed_url(),
                "sidecar_package": os.path.basename(SIDECAR),
                "thresholds": THRESHOLDS,
            },
            "final": {
                "duplicate_total": dup_s["total"],
                "duplicate_blocked": dup_s["passed"],
                "duplicate_recall_pct": round(dup_recall, 2),
                "conflict_total": con_s["total"],
                "conflict_passed": con_s["passed"],
                "conflict_false_block": con_false,
                "conflict_advisory": con_advisory,
                "unrelated_total": un_s["total"],
                "unrelated_passed": un_s["passed"],
                "unrelated_false_block": un_false,
                "passed": passed,
            },
            "groups": {
                "duplicate": dup_rows,
                "conflict": con_rows,
                "unrelated": un_rows,
            },
        }

        summary_path = os.path.join(DATA, "semantic_gate_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"wrote {summary_path}", flush=True)

        print(
            f"duplicate block {dup_s['passed']}/{dup_s['total']} "
            f"· conflict false_block {con_false}/{con_s['total']} "
            f"· advisory {con_advisory}/{con_s['total']} "
            f"· unrelated false_block {un_false}/{un_s['total']}",
            flush=True,
        )
        return 0 if passed else 1
    finally:
        shutil.rmtree(bench_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
