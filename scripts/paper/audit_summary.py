#!/usr/bin/env python3
"""Summarize the 118-item human audit of test_public (legal family excluded, v0.9.1 scope).

An item counts as an error when any of q1 (unambiguous question), q2 (evidence supports the gold
answer) or q3 (gold answer correct and complete) is "no". "unsure" answers are reported separately and
bound the estimate: lower = unsure counted as correct, upper = unsure counted as error. q4
(naturalness) is reported on its own and is not an error.

Strata and population sizes (test_public without the legal family): cloze-regenerated 168, script 179.
The weighted estimate uses these sizes; its 95% interval uses the stratified normal approximation and
is reported next to per-stratum Wilson intervals.

Usage: python3 scripts/paper/audit_summary.py <items.json> <verdicts>
  (public: python3 scripts/paper/build_audit_items.py . /tmp/items.json --ids-only &&
           python3 scripts/paper/audit_summary.py /tmp/items.json results/human_audit/human_audit_v091.jsonl)
  items.json   output of shared/scripts/build_audit_items.py (has id, route, family)
  verdicts_dir one JSON file per item as exported from the audit page store
"""
import glob
import json
import math
import os
import sys
from collections import Counter, defaultdict

POP = {"cloze": 168, "prog": 179}
Z = 1.96


def wilson(k, n):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load(items_path, vdir):
    items = [i for i in json.load(open(items_path)) if i["family"] != "cross_document_legal_reasoning"]
    v = {}
    if vdir.endswith(".jsonl"):  # released file: shared/audit/human_audit_v091.jsonl
        for line in open(vdir, encoding="utf-8"):
            r = json.loads(line)
            v[r["qa_id"]] = {"q1": r["q1_unambiguous"], "q2": r["q2_evidence_supports"],
                             "q3": r["q3_answer_correct_complete"], "q4": r["q4_natural"],
                             "errors": r["issue_types_ko"], "memo": r["memo_ko"]}
        return items, v
    for f in glob.glob(os.path.join(vdir, "*.json")):
        d = json.load(open(f))
        v[d.get("id", os.path.basename(f)[:-5])] = d.get("data", d)
    return items, v


def main():
    items, v = load(sys.argv[1], sys.argv[2])
    missing = [i["id"] for i in items if i["id"] not in v or not all(v[i["id"]].get(q) for q in ("q1", "q2", "q3", "q4"))]
    print(f"items {len(items)}  judged {len(items) - len(missing)}  missing {missing}")
    rows = []
    for i in items:
        d = v.get(i["id"], {})
        core = [d.get(q) for q in ("q1", "q2", "q3")]
        rows.append({"id": i["id"], "route": i["route"], "family": i["family"],
                     "err": "no" in core, "unsure": ("unsure" in core) and ("no" not in core),
                     "q": {q: d.get(q) for q in ("q1", "q2", "q3", "q4")},
                     "errors": d.get("errors", []), "memo": d.get("memo", ""), "sec": d.get("sec", 0)})

    print("\n== per stratum (error = any of q1-q3 'no') ==")
    est = {}
    for s in ("cloze", "prog"):
        r = [x for x in rows if x["route"] == s]
        n = len(r); k = sum(x["err"] for x in r); u = sum(x["unsure"] for x in r)
        lo, hi = wilson(k, n); lo2, hi2 = wilson(k + u, n)
        est[s] = (k, u, n)
        print(f"{s:6s} n={n:3d} errors={k:2d} ({100*k/n:.1f}%, Wilson [{100*lo:.1f}, {100*hi:.1f}])"
              f"  unsure-only={u}  upper bound errors+unsure={k+u} ({100*(k+u)/n:.1f}%, [{100*lo2:.1f}, {100*hi2:.1f}])")

    N = sum(POP.values())
    for label, add_unsure in (("lower (unsure=correct)", False), ("upper (unsure=error)", True)):
        p = 0.0; var = 0.0
        for s, (k, u, n) in est.items():
            ps = (k + (u if add_unsure else 0)) / n
            w = POP[s] / N
            p += w * ps
            fpc = (POP[s] - n) / (POP[s] - 1)
            var += (w ** 2) * ps * (1 - ps) / n * fpc
        h = Z * math.sqrt(var)
        print(f"weighted test_public (n={N}) {label}: {100*p:.1f}% [{100*max(0,p-h):.1f}, {100*min(1,p+h):.1f}]")

    print("\n== per question ==")
    for q in ("q1", "q2", "q3", "q4"):
        c = Counter(x["q"][q] for x in rows)
        print(q, dict(c))
    print("\n== by family (errors / n, unsure-only) ==")
    fam = defaultdict(list)
    for x in rows:
        fam[x["family"]].append(x)
    for f, r in sorted(fam.items()):
        print(f"{f:28s} {sum(x['err'] for x in r)}/{len(r)}  unsure={sum(x['unsure'] for x in r)}")
    print("\n== error types (items with a 'no' or 'unsure') ==")
    print(Counter(e for x in rows if x["err"] or x["unsure"] for e in x["errors"]))
    secs = sorted(x["sec"] for x in rows if x["sec"])
    if secs:
        print(f"\nseconds per item: median {secs[len(secs)//2]}, total {sum(secs)/3600:.1f} h")
    print("\n== flagged items ==")
    for x in rows:
        if x["err"] or x["unsure"] or x["q"]["q4"] != "yes":
            print(x["id"], x["route"], x["family"], x["q"], x["errors"], x["memo"][:160])


if __name__ == "__main__":
    main()
