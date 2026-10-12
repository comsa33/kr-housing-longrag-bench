#!/usr/bin/env python3
"""BM25 gold-page recall@5 (majority-page rule) after the full dev review (v0.9.7 candidate). No API calls.

Same computation as the dataset's scripts/v094/recall_majority_page.py, with two changes taken from the dev review:
- the 11 dev items excluded in eval_exclusions_v0.9.7.txt are dropped as well;
- the gold pages of the locator_fixed items are replaced by the adjudicated new pages
  (adjudication_filled_v2.csv, column new_locator "old -> new ; old -> new").
The 122 items keep being reported separately (their membership is unchanged by the new pages).

Usage (from file-search-map-reduce-agent/):
  KRH_WORKSPACE=kr-housing-longrag-bench/workspace_local python3 \
    kr-housing-longrag-bench-paper/shared/scripts/peerreview_check/recall_v097.py \
    kr-housing-longrag-bench-v096 EXCLUSIONS_V097 ADJUDICATION_V2 [--before]
--before reproduces the v0.9.4 figures (no extra exclusions, no locator changes) as a check.
"""
import csv
import importlib.util
import sys
from pathlib import Path

DS, EXCL97, ADJ = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3])
BEFORE = "--before" in sys.argv
spec = importlib.util.spec_from_file_location("rmp", DS / "scripts/v094/recall_majority_page.py")
rmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rmp)

new_dev_excl = set() if BEFORE else (rmp.ids(EXCL97) - rmp.ids(DS / "data/v0.9.3/eval_exclusions.txt"))
relocate = {}
if not BEFORE:
    for r in csv.DictReader(open(ADJ, encoding="utf-8-sig")):
        if r["action"].strip() == "locator_fixed" and r["new_locator"].strip():
            relocate[r["qa_id"]] = dict(p.split(" -> ") for p in r["new_locator"].split(" ; "))

orig_load = rmp.load


def load(p):
    rows = orig_load(p)
    if Path(p).name in [fn for fn, _ in rmp.PROMPTS]:
        out = []
        for r in rows:
            if r["qa_id"] in new_dev_excl:
                continue
            if r["qa_id"] in relocate:
                m = relocate[r["qa_id"]]
                r = dict(r, gold_page_ids=[m.get(g, g) for g in (r.get("gold_page_ids") or [])])
            out.append(r)
        return out
    return rows


rmp.load = load
rmp.ROOT = DS
print(f"extra dev exclusions {len(new_dev_excl)}, relocated items {len(relocate)}"
      + (" (--before: v0.9.4 reproduction)" if BEFORE else ""))
rmp.main()
