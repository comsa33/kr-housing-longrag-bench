#!/usr/bin/env python3
"""Build data/errata_v0.9.3.csv and data/v0.9.3/bundle_exclusions.txt (no API calls).

errata_v0.9.3 = every errata_v0.9.2 row, with
  * the dev items confirmed by the round-2 human review (100 random dev items, two annotators,
    author adjudication) excluded from evaluation (same principle as the confirmed test errors that were
    excluded in v0.9.2; gold unchanged, items kept in the data),
  * one row per confirmed round-2 error that the v0.9.2 detectors had not flagged,
  * one row per dev item whose gold page is not in its 512k bundle
    (data/v0.9.3/dev_gold_page_not_in_bundle.csv); these are excluded from the bundle-based
    settings (BM25, dense, full context) and kept in closed-book.

    python3 scripts/v093/build_errata.py
"""
import csv, json
from pathlib import Path
W = Path(__file__).resolve().parents[2]
old = list(csv.DictReader(open(W / "data/errata_v0.9.2.csv", encoding="utf-8")))
dv = {json.loads(l)["qa_id"]: json.loads(l) for l in open(W / "data/qa_v0.6_dev.jsonl", encoding="utf-8")}
# round-2 confirmed dev errors (author-adjudicated; registry "v0.9.2 round 2 human review")
R2 = {
    "krhlrb_v05_0875": "dual_row_gold", "krhlrb_v05_0884": "dual_row_gold", "krhlrb_v05_0788": "dual_row_gold",
    "krhlrb_v05_0800": "dual_row_gold", "krhlrb_v05_1056": "dual_row_gold",
    "krhlrb_v05_1142": "multiple_schedules", "krhlrb_v05_0596": "block_total_vs_round_count",
}
R2_NOTE = {
    "dual_row_gold": "Round-2 human review confirmed: the category has two income rows (e.g. single-income and dual-income); the question does not say which. Excluded from evaluation in v0.9.3 (confirmed error, round-2 human review); item kept in the data.",
    "multiple_schedules": "Round-2 human review confirmed: the column groups six interim-payment dates; gold holds only the first. Excluded from evaluation in v0.9.3 (confirmed error, round-2 human review); item kept in the data.",
    "block_total_vs_round_count": "Round-2 human review confirmed: the notice gives both the block total and the count supplied in this round; the question does not say which. Excluded from evaluation in v0.9.3 (confirmed error, round-2 human review); item kept in the data.",
}
cols = ["qa_id", "split", "task_type", "errata_type", "v0.9.3_status", "old_answer", "new_answer_or_accepted", "source", "note"]
rows, seen = [], set()
for r in old:
    r = dict(r); r["v0.9.3_status"] = r.pop("v0.9.2_status")
    if r["qa_id"] in R2:
        r["v0.9.3_status"] = "excluded_from_evaluation"; r["source"] = "human_review_round2"; r["note"] = R2_NOTE[R2[r["qa_id"]]]
    rows.append(r); seen.add(r["qa_id"])
for q, t in R2.items():
    if q not in seen:
        d = dv[q]; rows.append({"qa_id": q, "split": "dev", "task_type": d["task_type"], "errata_type": t,
                                "v0.9.3_status": "excluded_from_evaluation", "old_answer": d.get("answer", ""),
                                "new_answer_or_accepted": "", "source": "human_review_round2", "note": R2_NOTE[t]})
nb = list(csv.DictReader(open(W / "data/v0.9.3/dev_gold_page_not_in_bundle.csv", encoding="utf-8")))
assert len(nb) == 122 and len({r["qa_id"] for r in nb}) == 122
for r in nb:
    d = dv[r["qa_id"]]
    rows.append({"qa_id": r["qa_id"], "split": "dev", "task_type": r["task_type"], "errata_type": "gold_page_not_in_bundle",
                 "v0.9.3_status": "excluded_from_bundle_settings", "old_answer": d.get("answer", ""), "new_answer_or_accepted": "",
                 "source": "bundle_check_v0.9.3",
                 "note": f"Gold page(s) {r['gold_page_ids']} are not in bundle {r['bundle_id']}; the item cannot be answered from its bundle. Excluded from BM25, dense and full context; kept in closed-book."})
with open(W / "data/errata_v0.9.3.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
with open(W / "data/v0.9.3/eval_exclusions.txt", "w", encoding="utf-8") as f:
    f.write("# v0.9.3: items excluded from evaluation in every setting (closed-book included).\n"
            "# test_public (5, unchanged from v0.9.2): ill-posed questions found in the three-annotator test review.\n"
            "# dev (7, new in v0.9.3): confirmed errors from the round-2 human review of 100 random dev items.\n"
            "# Use with: --exclude-ids data/v0.9.3/eval_exclusions.txt\n")
    g = json.load(open(W / "data/v0.9.2/gold_fixes.json", encoding="utf-8"))
    f.write("# --- test_public ---\n")
    for q in sorted(g["exclude_from_evaluation"]): f.write(q + "\n")
    f.write("# --- dev ---\n")
    for q in sorted(R2): f.write(q + "\n")
with open(W / "data/v0.9.3/bundle_exclusions.txt", "w", encoding="utf-8") as f:
    f.write("# v0.9.3: dev items whose gold page is not in their 512k bundle (bundle check, see CHANGELOG 0.9.3).\n"
            "# Exclude from the bundle-based settings (BM25, dense, full context); keep in closed-book.\n"
            "# Use with: --exclude-ids data/v0.9.3/bundle_exclusions.txt (bundle settings only)\n")
    for r in sorted(nb, key=lambda r: r["qa_id"]): f.write(r["qa_id"] + "\n")
import collections
print("rows", len(rows), collections.Counter((r["split"], r["v0.9.3_status"]) for r in rows))
