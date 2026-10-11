#!/usr/bin/env python3
"""Pre-registered single-retry rule for empty answers (v0.9.3), helper (no API calls).

Rule (fixed before any re-run, 2026-10-11): an item whose scored prediction is empty because the output
cap was reached is re-run ONCE with a larger cap (gpt-5.5: 4,000 -> 16,000 max_completion_tokens; open
models: the cap doubled), with the same prompt and all other settings. If it is still empty, it stays wrong
and is counted. This script lists the empty items of a run and writes the prompt subset to re-run.

    python3 scripts/v093/list_empty_answers.py PRED.jsonl PROMPTS.jsonl --out RETRY_PROMPTS.jsonl
"""
import argparse, json
ap = argparse.ArgumentParser(); ap.add_argument("pred"); ap.add_argument("prompts"); ap.add_argument("--out", required=True)
a = ap.parse_args()
empty = {r["qa_id"] for r in map(json.loads, open(a.pred, encoding="utf-8")) if not str(r.get("prediction") or "").strip()}
n = 0
with open(a.out, "w", encoding="utf-8") as f:
    for l in open(a.prompts, encoding="utf-8"):
        if json.loads(l)["qa_id"] in empty: f.write(l); n += 1
print(f"empty predictions {len(empty)}; prompts written {n} -> {a.out}")
