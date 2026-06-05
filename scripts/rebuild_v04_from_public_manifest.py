#!/usr/bin/env python3
"""Reconstruct the internal v0.4 context from PUBLIC artifacts + local keys/files.

The public release ships QA labels, locators, predicates, source URLs, and this reconstruction
driver — NOT raw PDFs/HWPs, row dumps, or bundle text. An external user who wants to *run* the
benchmark (full-context / RAG / table-tool) rebuilds the internal corpus locally:

  1. official LH 모집공고 PDFs  -> data/v0.4_announcement_targets_seed.jsonl  (official URLs)
  2. MOLIT / HUG rows           -> data.go.kr open API + HUG API  (user's own keys)
  3. extraction + indexes + bundles -> deterministic, from the above

This driver only orchestrates the existing per-step scripts and checks preconditions. It downloads
ONLY from the official URLs in the public manifest and reads keys from workspace_local/secrets/.
Nothing here redistributes third-party documents.

Usage:
  python3 scripts/rebuild_v04_from_public_manifest.py --check        # preconditions only (no fetch)
  python3 scripts/rebuild_v04_from_public_manifest.py --steps all    # full rebuild
  python3 scripts/rebuild_v04_from_public_manifest.py --steps bundles,verify
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SECRETS = ROOT / "workspace_local" / "secrets"

# step name -> (description, [script + args], precondition keys)
STEPS = {
    "acquire_lh": ("Download official LH 모집공고 PDFs/HWPs from the public target manifest",
                   ["acquire_lh_announcements_from_manifest.py"], []),
    "extract_lh": ("Extract LH announcement pages + numeric facts (pdftotext)",
                   ["extract_lh_announcements_v04.py"], []),
    "acquire_molit": ("Fetch MOLIT apartment trade-detail rows (data.go.kr open API)",
                      ["acquire_molit_apt_trade_detail_rows.py"], ["data_go_kr.key"]),
    "acquire_hug": ("Fetch HUG sale-history rows (HUG API)",
                    ["acquire_hug_sale_history_rows.py"], ["hug_api.key"]),
    "indexes": ("Build internal MOLIT/HUG/LH evidence indices",
                ["build_v03_indexes.py"], []),
    "bundles": ("Materialize internal long-context bundles (32k..512k)",
                ["build_bundles_v04.py"], []),
    "validate": ("Lightweight schema/source validation", ["validate_dataset.py"], []),
    "verify": ("Deep deterministic verification (predicate recompute + grounding)", ["verify_qa.py"], []),
    "readiness": ("Public-release readiness gate", ["check_public_release_readiness.py", "--allow-dev"], []),
}

ORDER = ["acquire_lh", "extract_lh", "acquire_molit", "acquire_hug", "indexes", "bundles", "validate", "verify", "readiness"]


def have_tool(name: str) -> bool:
    from shutil import which
    return which(name) is not None


def check_preconditions(steps: list[str]) -> list[str]:
    problems = []
    needed_keys = set()
    for s in steps:
        for k in STEPS[s][2]:
            needed_keys.add(k)
    for k in needed_keys:
        if not (SECRETS / k).exists():
            problems.append(f"missing key: workspace_local/secrets/{k} (required by acquire steps)")
    if ("extract_lh" in steps) and not have_tool("pdftotext"):
        problems.append("missing tool: pdftotext (poppler) — required for LH extraction")
    if not (ROOT / "data" / "v0.4_announcement_targets_seed.jsonl").exists():
        problems.append("missing public target manifest: data/v0.4_announcement_targets_seed.jsonl")
    return problems


def run_step(name: str) -> int:
    desc, cmd, _ = STEPS[name]
    print(f"\n=== STEP {name}: {desc} ===")
    full = [sys.executable, str(SCRIPTS / cmd[0]), *cmd[1:]]
    print("  $", " ".join(full))
    return subprocess.run(full, cwd=str(ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default="all",
                    help="comma list from: " + ",".join(ORDER) + " (or 'all')")
    ap.add_argument("--check", action="store_true", help="check preconditions only; do not fetch/build")
    args = ap.parse_args()

    steps = ORDER if args.steps == "all" else [s.strip() for s in args.steps.split(",") if s.strip()]
    for s in steps:
        if s not in STEPS:
            print(f"unknown step {s!r}; valid: {', '.join(ORDER)}")
            return 2

    print("== v0.4 public reconstruction ==")
    print("  public inputs : data/v0.4_announcement_targets_seed.jsonl, data/source_manifest.jsonl, data/qa_v0.4_candidates.jsonl")
    print("  local secrets : workspace_local/secrets/{data_go_kr.key, hug_api.key}")
    print("  rebuilds      : workspace_local/{raw,processed,audit}/  (internal, not redistributed)")
    problems = check_preconditions(steps)
    if problems:
        print("\nPRECONDITIONS NOT MET:")
        for p in problems:
            print("  -", p)
        if args.check:
            return 1
        print("\nProceeding with available steps may fail; resolve the above for acquire steps.")
    else:
        print("\npreconditions OK for:", ", ".join(steps))

    if args.check:
        print("\n(--check) no steps executed.")
        return 0 if not problems else 1

    rc_total = 0
    for s in steps:
        rc = run_step(s)
        if rc != 0:
            print(f"  STEP {s} exited {rc}")
            rc_total = rc
            if s.startswith("acquire") or s in ("extract_lh",):
                print("  stopping: downstream steps depend on this step's output.")
                break
    print("\n== reconstruction finished ==" if rc_total == 0 else "\n== reconstruction finished with errors ==")
    return rc_total


if __name__ == "__main__":
    raise SystemExit(main())
