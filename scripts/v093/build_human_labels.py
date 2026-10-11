#!/usr/bin/env python3
"""Write results/human_review_v0.9.3/ from the round-2 and round-3 annotation files (labels only, no text).

Round 2 (after the v0.9.2 release): the two non-author annotators reviewed 100 random in-scope dev items
(same four questions as the v0.9.2 test review) and labelled the 80 judge-validation predictions
independently (model names hidden, order shuffled). Round 3: they labelled the 74 Anthropic predictions on
which the six judges disagree; the author settled disagreements and unsure cases under a rule fixed before
labelling. Inputs are the annotation CSVs kept off the repository (they quote evidence and model answers).

    python3 scripts/v093/build_human_labels.py ROUND2_DIR CLAUDE74_LABELS_JSON
"""
import csv, json, sys
from pathlib import Path
W = Path(__file__).resolve().parents[2]; R2 = Path(sys.argv[1]); R3 = Path(sys.argv[2])
OUT = W / "results/human_review_v0.9.3"; OUT.mkdir(parents=True, exist_ok=True)
def rows(p): return list(csv.DictReader(open(p, encoding="utf-8-sig")))
Q = ["q1_unambiguous", "q2_evidence_supports", "q3_answer_correct_complete", "q4_natural"]
out = []
for ann, f in (("annotator2", "a_dev100.csv"), ("annotator3", "b_dev100.csv")):
    for r in rows(R2 / "in" / f):
        lab = {q: r[q].strip().lower() for q in Q}
        out.append({"qa_id": r["qa_id"], "annotator": ann, "stratum": r["stratum"], "family": r["family"], **lab,
                    "error_label": any(lab[q] == "no" for q in Q[:3])})
assert len(out) == 200
with open(OUT / "dev100_annotator_labels.jsonl", "w", encoding="utf-8") as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
flag = {}
for r in out: flag.setdefault(r["qa_id"], 0); flag[r["qa_id"]] += r["error_label"]
fin = {r["qa_id"]: r["final_error(yes/no)"].strip().lower() for r in rows(R2 / "in" / "dev_adjudicate_7_final.csv")}
adj = [{"qa_id": q, "n_flag": n, "final_error": fin[q]} for q, n in sorted(flag.items()) if n]
assert {a["qa_id"] for a in adj} == set(fin), "adjudicated set must equal the flagged set"
with open(OUT / "dev100_adjudication.jsonl", "w") as f:
    for a in adj: f.write(json.dumps(a) + "\n")
key = {str(k["no"]): k["item_id"] for k in json.load(open(R2 / "judge80_key_DO_NOT_SEND.json"))}
j80 = []
for ann, f in (("annotator2", "a_judge80.csv"), ("annotator3", "b_judge80.csv")):
    for r in rows(R2 / "in" / f):
        j80.append({"item": key[r["no"]], "annotator": ann, "label": r["judgment(correct/incorrect/unsure)"].strip().lower()})
assert len(j80) == 160
with open(OUT / "judge80_independent_labels.jsonl", "w") as f:
    for r in j80: f.write(json.dumps(r) + "\n")
TAG = {"sonnet55": "claude-sonnet-5-5", "haiku55": "claude-haiku-5-5"}
r3 = json.load(open(R3))
with open(OUT / "claude74_adjudication.jsonl", "w") as f:
    for r in r3:
        m, reg = r["tag"].split("_", 1)
        f.write(json.dumps({"qa_id": r["qa_id"], "model": TAG[m], "regime": reg, "annotator2": r["annotator2"],
                            "annotator3": r["annotator3"], "author": r["author"], "final": r["final"], "source": r["source"]}) + "\n")
print("dev100 rows", len(out), "adjudicated", len(adj), "confirmed", sum(a["final_error"] == "yes" for a in adj), "judge80 rows", len(j80), "claude74", len(r3))
