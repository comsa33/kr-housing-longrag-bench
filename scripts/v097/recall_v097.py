#!/usr/bin/env python3
"""BM25 gold-page recall@5 (majority-page rule) after the full dev review (v0.9.7 candidate). No API calls.

Same computation as the dataset's scripts/v094/recall_majority_page.py, with two changes taken from the dev review:
- the 11 dev items newly listed in data/v0.9.7/eval_exclusions.txt are dropped as well;
- the gold pages of the locator_fixed items are replaced by the new pages in the released
  data/errata_v0.9.7.csv, column new_locator ("old_page -> new_page", several joined by " ; "; added in v0.9.8).
The 122 items keep being reported separately (their membership is unchanged by the new pages).
Like the v0.9.4 script, it needs the bundle text and the stored BM25 prompt files under workspace_local/
(not redistributed); the exclusions and the new locators come from released files only.

Usage (from the repository root):
  KRH_WORKSPACE=<workspace_local> python3 scripts/v097/recall_v097.py . [--errata PATH] [--before]
--errata reads the new_locator column from another copy of the errata file (default data/errata_v0.9.7.csv).
--before reproduces the v0.9.4 figures (no extra exclusions, no locator changes) as a check.
"""
import csv
import importlib.util
import sys
from pathlib import Path

DS = Path(sys.argv[1]).resolve()
ERRATA = Path(sys.argv[sys.argv.index("--errata") + 1]) if "--errata" in sys.argv else DS / "data/errata_v0.9.7.csv"
BEFORE = "--before" in sys.argv
spec = importlib.util.spec_from_file_location("rmp", DS / "scripts/v094/recall_majority_page.py")
rmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rmp)

new_dev_excl = set() if BEFORE else (rmp.ids(DS / "data/v0.9.7/eval_exclusions.txt")
                                     - rmp.ids(DS / "data/v0.9.3/eval_exclusions.txt"))
relocate = {}
if not BEFORE:
    for r in csv.DictReader(open(ERRATA, encoding="utf-8")):
        if r["v0.9.7_status"] == "locator_fixed":
            relocate[r["qa_id"]] = dict(p.split(" -> ") for p in r["new_locator"].split(" ; "))
    assert len(relocate) == 30 and sum(map(len, relocate.values())) == 31, "expected 30 items / 31 page mappings"

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
