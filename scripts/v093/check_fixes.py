#!/usr/bin/env python3
"""Checks for the two v0.9.3 code fixes (no API calls).

1. Page markers: the v0.9.3 pattern reads Hangul page ids; the legacy pattern does not.
   With --bundles DIR, also counts the pages each pattern finds in the SH bundles.
2. Closed-book locator fix: with --cb-records FILE ... (the closed-book prompt records with context_spec,
   build machine only) and --e1-prompts FILE ... (the leak-fixed prompts that were run), checks that
   build_prompt reproduces every fixed prompt, leaves every other prompt unchanged, and that no count item
   still shows exactly as many row_ids as its gold count.

    python3 scripts/v093/check_fixes.py [--bundles DIR] [--cb-records F ...] [--e1-prompts F ...]
"""
import argparse, json, re, sys
from pathlib import Path
W = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(W / "scripts"))
import build_rag_smoke as rb
import run_llm_baseline as rl
ap = argparse.ArgumentParser(); ap.add_argument("--bundles"); ap.add_argument("--cb-records", nargs="*", default=[]); ap.add_argument("--e1-prompts", nargs="*", default=[])
a = ap.parse_args()
sample = "[sh-sh-13075-입주자-모집공고문-p001 (p.1)] 본문 [lh-announce-0000061086-public-sale-2026q2-p001 (p.1)] 본문"
new = [m.group(1) for m in rb.PAGE_RE_V093.finditer(sample)]; old = [m.group(1) for m in rb.PAGE_RE_LEGACY.finditer(sample)]
assert new == ["sh-sh-13075-입주자-모집공고문-p001", "lh-announce-0000061086-public-sale-2026q2-p001"], new
assert old == ["lh-announce-0000061086-public-sale-2026q2-p001"], old
print("page markers: v0.9.3 reads", len(new), "ids, legacy reads", len(old), "(SH id missed) -> OK")
if a.bundles:
    for p in sorted(Path(a.bundles).glob("sh-*.txt"))[:5]:
        t = p.read_text(encoding="utf-8")
        print(f"  {p.name}: pages v0.9.3 {len(list(rb.PAGE_RE_V093.finditer(t)))}, legacy {len(list(rb.PAGE_RE_LEGACY.finditer(t)))}")
if a.cb_records:
    gold = {}
    for sp in ("test_public", "dev"):
        for l in open(W / f"data/qa_v0.6_{sp}.jsonl", encoding="utf-8"):
            r = json.loads(l); gold[r["qa_id"]] = r
    fix = rl._cb_fix(); e1 = {}
    for f in a.e1_prompts:
        for l in open(f, encoding="utf-8"):
            r = json.loads(l); e1[(r.get("split"), r["qa_id"])] = r["prompt"]
    same = changed = repro = leak_left = 0
    for f in a.cb_records:
        for l in open(f, encoding="utf-8"):
            r = json.loads(l); q = r["qa_id"]
            rl.LEGACY_LOCATORS = True; p_old = rl.build_prompt(r)
            rl.LEGACY_LOCATORS = False; p_new = rl.build_prompt(r)
            if q in fix:
                changed += p_new != p_old
                k = (r.get("split"), q)
                if k in e1: repro += p_new == e1[k]; assert p_new == e1[k], ("fixed prompt differs from the run", q)
            else:
                same += p_new == p_old; assert p_new == p_old, ("unaffected prompt changed", q)
            g = gold.get(q, {}); gp = g.get("gold_predicate") or {}
            spec = r.get("context_spec") or {}; rids = [] if "row_ids" in fix.get(q, ()) else (spec.get("row_ids") or [])
            nums = {x.replace(",", "") for x in re.findall(r"\d[\d,]*", str(g.get("answer", "")))}
            leak_left += gp.get("op") == "count" and 0 < len(rids) <= 20 and str(len(rids)) in nums
    print(f"closed-book: unaffected prompts unchanged {same}, fixed prompts changed {changed}, fixed prompts equal to the run {repro}, count leaks left {leak_left}")
    assert leak_left == 0
