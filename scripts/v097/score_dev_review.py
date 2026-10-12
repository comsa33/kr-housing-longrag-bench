#!/usr/bin/env python3
"""Tally the dev full review and build the release files (prespec_dev_review_2026-10-12.md D-E). No API calls.

Step 1 (labels in, no adjudication yet):
  python3 score_dev_review.py --sheets DIR --assignment assignment.csv --dataset DATASET_ROOT \
      --adjudication-template adjudicate.csv
  Reads dev_review_<X>_INTERNAL.csv (verdict in {no_error, error, unsure}; type when error; memo) for every
  annotator letter in assignment.csv; checks that each assigned item has a valid verdict from both of its
  annotators; prints flag counts (>=1 / both), pair agreement (raw, Cohen kappa, PABAK; error vs not error,
  unsure counted as not error and reported), counts by type, family and route, the detector cross-table and
  the round-2 consistency; writes the adjudication template: every item with >=1 error label, plus items
  where an annotator wrote unsure with a sheet-problem memo ("시트").
Step 2 (adjudication filled):
  ... --adjudication adjudicate_final.csv --out OUT_DIR
  adjudicate_final.csv columns: qa_id, final_error (yes/no), final_type (dual_row, header_parse,
  multiple_schedules, wrong_gold, scope, unspecified, other), action, new_answer, new_locator, reason, note.
  - final_error = yes: action must be one of gold_accept_any (new_answer = alternatives joined by " | "),
    gold_replaced (new_answer = the new value), locator_fixed (new_locator; question and gold unchanged),
    excluded (question defect; kept in the release, excluded from evaluation); reason stays empty.
  - final_error = no: reason must be one of annotator_misread, sheet_defect, other; action stays empty.
    Rule D(ii): sheet_defect is counted separately and never as an error.
  Any other combination stops the script.
  Writes OUT_DIR/errata_v0.9.7.csv (v0.9.3 errata columns, status column v0.9.7_status),
  OUT_DIR/eval_exclusions_v0.9.7.txt (draft: the v0.9.3 list plus new exclusions),
  OUT_DIR/human_review_v0.9.7/{annotator_labels.jsonl, adjudication.jsonl, assignment.csv, seed.txt},
  and prints the final error rate (Wilson 95%) overall and by family, a route summary line (script /
  cloze_regenerated / template_reworded, as the test review reported 14.0% and 2.4%; route is nearly
  determined by family in dev), and the detector precision/recall.
"""
import argparse
import csv
import json
import math
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--sheets", required=True, help="directory holding dev_review_<X>_INTERNAL.csv (searched recursively)")
ap.add_argument("--assignment", required=True)
ap.add_argument("--dataset", required=True)
ap.add_argument("--adjudication-template")
ap.add_argument("--adjudication")
ap.add_argument("--out")
ap.add_argument("--seed", default="20261012")
a = ap.parse_args()
DS = Path(a.dataset).resolve()
TYPES = ["dual_row", "header_parse", "multiple_schedules", "wrong_gold", "scope", "unspecified", "other"]
ERRATA_TYPE = {"dual_row": "dual_row_gold", "header_parse": "ill_posed_header_parse",
               "multiple_schedules": "multiple_schedules", "wrong_gold": "wrong_gold", "scope": "scope_mismatch",
               "unspecified": "unspecified_type", "other": "other"}
ACTIONS = {"gold_accept_any": "gold_accept_any", "gold_replaced": "gold_replaced", "locator_fixed": "locator_fixed",
           "excluded": "excluded_from_evaluation"}
REASONS = ("annotator_misread", "sheet_defect", "other")
# Public errata notes are generated from type and action only (adjudication and annotator notes stay private).
TYPE_NOTE = {
    "dual_row": "The cited table has a second row for the same category (such as a dual-income row) and the question does not say which row",
    "header_parse": "A table header was parsed as a row or column label, so the question does not identify a cell",
    "multiple_schedules": "The cited cell or column holds several values for different groups or rounds",
    "wrong_gold": "The gold value does not match the cited source",
    "scope": "The scope of the question does not match the scope of the gold value",
    "unspecified": "The answer depends on a condition (such as the supply type) that the question does not name",
}
ACTION_NOTE = {
    "gold_accept_any": "the gold now accepts any of the listed values.",
    "gold_replaced": "the gold value was replaced.",
    "excluded": "the question is ill-posed, so the item stays in the release and is excluded from evaluation.",
}


def public_note(ftype, act, new_locator):
    if act == "locator_fixed":
        pages = ", ".join(x.split(" -> ")[1] for x in new_locator.split(" ; "))
        return (f"The cited page does not state the gold value; question and gold unchanged, evidence locator "
                f"moved to {pages}.")
    lead = TYPE_NOTE.get(ftype, "The source supports more than one answer" if act == "gold_accept_any"
                         else "The item has a defect not covered by the other types")
    return f"{lead}; {ACTION_NOTE[act]}"


def read(p):
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def wilson(k, n, z=1.96):
    if not n:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def fmt(k, n):
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% ({k}/{n}) [{100 * lo:.1f}, {100 * hi:.1f}]" if n else "n/a"


def kappa(x, y):
    n = len(x)
    po = sum(i == j for i, j in zip(x, y)) / n
    px, py = sum(x) / n, sum(y) / n
    pe = px * py + (1 - px) * (1 - py)
    return po, (float("nan") if pe == 1 else (po - pe) / (1 - pe)), 2 * po - 1


asg = {r["qa_id"]: r for r in read(a.assignment)}
names = sorted({r["annotator_a"] for r in asg.values()} | {r["annotator_b"] for r in asg.values()})
lab = {}  # (qa_id, annotator) -> row
problems = []
for nm in names:
    fs = list(Path(a.sheets).rglob(f"dev_review_{nm}_INTERNAL.csv"))
    if len(fs) != 1:
        sys.exit(f"annotator {nm}: expected one sheet, found {len(fs)}")
    for r in read(fs[0]):
        v = (r.get("verdict") or "").strip().lower()
        t = (r.get("type") or "").strip().lower()
        if v not in ("no_error", "error", "unsure"):
            problems.append((nm, r["qa_id"], f"verdict '{v}'"))
        if v == "error" and t not in TYPES:
            problems.append((nm, r["qa_id"], f"type '{t}'"))
        lab[(r["qa_id"], nm)] = {"verdict": v, "type": t if v == "error" else "", "memo": r.get("memo", ""),
                                 "block": r.get("block", "")}
for q, r in asg.items():
    for nm in (r["annotator_a"], r["annotator_b"]):
        if (q, nm) not in lab:
            problems.append((nm, q, "missing row"))
extra = [k for k in lab if k[0] not in asg or k[1] not in (asg[k[0]]["annotator_a"], asg[k[0]]["annotator_b"])]
if problems or extra:
    print(f"label problems: {len(problems)} {problems[:10]}; rows not in the assignment: {extra[:5]}")
    sys.exit(1)

pairs_of = {q: (r["annotator_a"], r["annotator_b"]) for q, r in asg.items()}
err = lambda q, nm: lab[(q, nm)]["verdict"] == "error"
nflag = {q: sum(err(q, nm) for nm in pairs_of[q]) for q in asg}
sheet_memo = {q for q in asg for nm in pairs_of[q]
              if lab[(q, nm)]["verdict"] == "unsure" and "시트" in lab[(q, nm)]["memo"]}
N = len(asg)
print(f"## dev full review ({N} items, annotators {names})")
print(f"- >=1 error label {sum(v >= 1 for v in nflag.values())}, both {sum(v == 2 for v in nflag.values())}; "
      f"unsure labels {sum(l['verdict'] == 'unsure' for l in lab.values())}, items unsure by both "
      f"{sum(all(lab[(q, nm)]['verdict'] == 'unsure' for nm in pairs_of[q]) for q in asg)}; "
      f"sheet-problem memos {len(sheet_memo)}")
print("- pair agreement (error vs not error; unsure = not error):")
by_pair = defaultdict(list)
for q, p in pairs_of.items():
    by_pair[p].append(q)
for p in sorted(by_pair):
    qs = by_pair[p]
    po, k, pabak = kappa([err(q, p[0]) for q in qs], [err(q, p[1]) for q in qs])
    print(f"  - {''.join(p)} (n={len(qs)}): raw {100 * po:.1f}%, kappa {k:.3f}, PABAK {pabak:.3f}")
types = Counter(lab[(q, nm)]["type"] for q in asg for nm in pairs_of[q] if err(q, nm))
print("- error labels by type:", dict(types))
for col in ("family", "route"):
    c1 = Counter(asg[q][col] for q in asg if nflag[q] >= 1)
    c2 = Counter(asg[q][col] for q in asg if nflag[q] == 2)
    n = Counter(asg[q][col] for q in asg)
    print(f"- by {col} (items, >=1, both):", {k: (n[k], c1[k], c2[k]) for k in sorted(n)})

det = {r["qa_id"]: r["errata_type"] for r in read(DS / "data/errata_v0.9.2.csv")
       if r["split"] == "dev" and r["source"] == "auto_flag_unverified"}
det_in = {q for q in det if q in asg}
print(f"- detector flags in scope {len(det_in)}/{len(det)}: >=1 error label {sum(nflag[q] >= 1 for q in det_in)}, "
      f"both {sum(nflag[q] == 2 for q in det_in)}; items with >=1 error label not flagged "
      f"{sum(1 for q in asg if nflag[q] >= 1 and q not in det)}")
prev = defaultdict(list)
for l in open(DS / "results/human_review_v0.9.3/dev100_annotator_labels.jsonl"):
    d = json.loads(l)
    prev[d["qa_id"]].append(bool(d["error_label"]))
prev_final = {json.loads(l)["qa_id"]: json.loads(l)["final_error"] == "yes"
              for l in open(DS / "results/human_review_v0.9.3/dev100_adjudication.jsonl")}
r2 = [q for q in prev if q in asg]
same = sum((any(prev[q])) == (nflag[q] >= 1) for q in r2)
print(f"- round-2 100 items in scope {len(r2)}: same >=1-flag status {same}/{len(r2)}; "
      f"round-2 confirmed errors in scope {sum(prev_final.get(q, False) for q in r2)} (should be 0: they were excluded)")

targets = sorted(q for q in asg if nflag[q] >= 1 or q in sheet_memo)
if a.adjudication_template:
    with open(a.adjudication_template, "w", newline="", encoding="utf-8-sig") as f:
        cols = ["qa_id", "family", "route", "n_flag", "annotators", "types", "memos", "detector_flag",
                "final_error", "final_type", "action", "new_answer", "new_locator", "reason", "note"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for q in targets:
            p = pairs_of[q]
            w.writerow({"qa_id": q, "family": asg[q]["family"], "route": asg[q]["route"], "n_flag": nflag[q],
                        "annotators": "".join(p),
                        "types": " / ".join(f"{nm}:{lab[(q, nm)]['verdict']}:{lab[(q, nm)]['type']}" for nm in p),
                        "memos": " / ".join(f"{nm}:{lab[(q, nm)]['memo']}" for nm in p if lab[(q, nm)]["memo"]),
                        "detector_flag": det.get(q, ""), "final_error": "", "final_type": "", "action": "",
                        "new_answer": "", "new_locator": "", "reason": "", "note": ""})
    print(f"wrote adjudication template: {len(targets)} items")

if not a.adjudication:
    sys.exit(0)

adj = {r["qa_id"]: r for r in read(a.adjudication)}
miss = [q for q in targets if q not in adj]


def invalid(r):
    fe, act, rs = r["final_error"].strip(), r["action"].strip(), r["reason"].strip()
    if fe == "yes":
        return (r["final_type"].strip() not in TYPES or act not in ACTIONS or rs
                or (act in ("gold_accept_any", "gold_replaced") and not r["new_answer"].strip())
                or (act == "locator_fixed" and not r["new_locator"].strip()))
    if fe == "no":
        return rs not in REASONS or bool(act)
    return True


badrow = [(q, r) for q, r in adj.items() if invalid(r)]
if miss or badrow:
    sys.exit(f"adjudication incomplete: missing {miss[:10]}; invalid rows {[q for q, _ in badrow][:10]}")
final = {q: q in adj and adj[q]["final_error"].strip() == "yes" for q in asg}
k = sum(final.values())
print(f"\n### final (after adjudication)\n- dev error rate {fmt(k, N)}")
print("- not errors after adjudication, by reason:",
      dict(Counter(adj[q]["reason"].strip() for q in targets if not final[q])), "(sheet_defect = rule D(ii))")
print("- final types:", dict(Counter(adj[q]["final_type"].strip() for q in asg if final[q])))
print("- actions:", dict(Counter(adj[q]["action"].strip() for q in asg if final[q])))
for col, title in (("family", "by family"), ("route", "route summary (route is nearly determined by family in dev)")):
    cells = defaultdict(lambda: [0, 0])
    for q in asg:
        cells[asg[q][col]][0] += final[q]
        cells[asg[q][col]][1] += 1
    if col == "family":
        print(f"- {title}:")
        for f_, (e, n) in sorted(cells.items()):
            print(f"  - {f_}: {fmt(e, n)}")
    else:
        print(f"- {title}: " + "; ".join(f"{r_} {fmt(e, n)}" for r_, (e, n) in sorted(cells.items())))
tp = sum(final[q] for q in det_in)
print(f"- detector: precision {fmt(tp, len(det_in))}; recall {fmt(tp, k)}")

if a.out:
    out = Path(a.out)
    hr = out / "human_review_v0.9.7"
    hr.mkdir(parents=True, exist_ok=True)
    qa = {json.loads(l)["qa_id"]: json.loads(l) for l in open(DS / "data/qa_v0.6_dev.jsonl")}
    with open(out / "errata_v0.9.7.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["qa_id", "split", "task_type", "errata_type", "v0.9.7_status", "old_answer",
                    "new_answer_or_accepted", "source", "note"])
        for q in sorted(q for q in asg if final[q]):
            r = adj[q]
            act = r["action"].strip()
            new = (r["new_answer"].strip() if act in ("gold_accept_any", "gold_replaced")
                   else r["new_locator"].strip() if act == "locator_fixed" else "")
            w.writerow([q, "dev", qa[q]["task_type"], ERRATA_TYPE[r["final_type"].strip()], ACTIONS[act],
                        qa[q]["answer"], "" if act == "locator_fixed" else new, "human_review_v0.9.7",
                        public_note(r["final_type"].strip(), act, r["new_locator"].strip())])
    old = [l.rstrip("\n") for l in open(DS / "data/v0.9.3/eval_exclusions.txt")]
    new = sorted(q for q in asg if final[q] and adj[q]["action"].strip() == "excluded")
    (out / "eval_exclusions_v0.9.7.txt").write_text(
        "\n".join(l.replace("v0.9.3", "v0.9.7", 1) if i == 0 else l for i, l in enumerate(old))
        + "\n# --- dev (new in v0.9.7): question defects confirmed in the full dev review ---\n"
        + "".join(q + "\n" for q in new), encoding="utf-8")
    with open(hr / "annotator_labels.jsonl", "w", encoding="utf-8") as f:
        for q in sorted(asg):
            for nm in pairs_of[q]:
                l = lab[(q, nm)]
                f.write(json.dumps({"qa_id": q, "annotator": nm, "block": asg[q]["block"],
                                    "verdict": l["verdict"], "type": l["type"]}, ensure_ascii=False) + "\n")
    with open(hr / "adjudication.jsonl", "w", encoding="utf-8") as f:
        for q in targets:
            r = adj[q]
            f.write(json.dumps({"qa_id": q, "n_flag": nflag[q],
                                "final_error": "yes" if final[q] else "no",
                                "final_type": r["final_type"].strip() if final[q] else "",
                                "action": r["action"].strip() if final[q] else "",
                                "reason": "" if final[q] else r["reason"].strip()}, ensure_ascii=False) + "\n")
    shutil.copy(a.assignment, hr / "assignment.csv")
    (hr / "seed.txt").write_text(f"{a.seed}\n", encoding="utf-8")
    print(f"wrote {out}/errata_v0.9.7.csv, eval_exclusions_v0.9.7.txt (draft, {len(new)} new), "
          f"human_review_v0.9.7/ (labels {sum(1 for _ in open(hr / 'annotator_labels.jsonl'))}, adjudication {len(targets)})")
