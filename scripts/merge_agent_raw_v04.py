#!/usr/bin/env python3
"""Merge per-batch agent QA files (written by the Workflow stage) into one raw file for assembly.

Reads workspace_local/audit/authoring/out/*.json (each a list of
{batch, item, reviewer_supported, reviewer_unambiguous, reviewer_reason}) and concatenates them into
workspace_local/audit/qa_v04_agent_raw.json, which assemble_qa_v04.py consumes (and re-gates).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "workspace_local" / "audit" / "authoring" / "out"
DEST = ROOT / "workspace_local" / "audit" / "qa_v04_agent_raw.json"


def main() -> int:
    merged = []
    bad = []
    if OUTDIR.exists():
        for p in sorted(OUTDIR.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                bad.append((p.name, str(exc)))
                continue
            if isinstance(data, list):
                merged.extend(data)
            else:
                bad.append((p.name, "not a list"))
    DEST.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    fam = Counter(r.get("item", {}).get("task_type", "?") for r in merged)
    sup = sum(1 for r in merged if r.get("reviewer_supported") and r.get("reviewer_unambiguous"))
    print(f"=== MERGE agent raw: {len(merged)} candidates from {OUTDIR.name}/ ===")
    for k, v in sorted(fam.items()):
        print(f"   {k:32s} {v}")
    print(f"   reviewer-passed (supported & unambiguous): {sup}")
    if bad:
        print(f"   WARN unreadable files: {bad}")
    print(f"   -> {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
