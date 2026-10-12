#!/usr/bin/env python3
"""Score the second judge-validation sample (prespec_judge_validation_2026-10-12.md §5-§6). No API calls.

Inputs:
  --sample   shared/annotated/judge_validation_2026-10-12/sample.csv (sample_id, stratum, qa_id, model, setting,
             task_type, judge_label, judge_label_secondary, ...)
  --ann-a / --ann-b   the two annotators' filled copies of annotator.csv (sample_id, label, memo);
             label in {correct, incorrect, unsure}
  --adjudication      CSV (sample_id, label_adjudicated in {correct, incorrect}) for the rows where the two
             annotators differ or either is unsure; omit it to print the rows that need adjudication
             (--adjudication-template OUT writes them as a CSV).
  --dataset  dataset repository root (v0.9.6) for the panel verdicts and the cell populations.

Reference label: the two annotators' label when they agree and neither is unsure; otherwise the adjudicated label.
Rows still without a reference label are left out of every agreement figure and counted.

Output (stdout, markdown): annotator agreement and kappa; primary and secondary judge vs reference (raw agreement
with Wilson 95%, Cohen kappa) on the main stratum, as sampled and post-stratified by cell (weight = cell pool / 4);
by setting, by model and by family (agreement and Wilson only; family groups cross_source_aggregation, long_context_retrieval, other); the six judges on the 56 Anthropic predictions of the main stratum; the auxiliary string-mismatch stratum
separately; and a registry entry draft.
"""
import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--sample", required=True)
ap.add_argument("--ann-a", required=True)
ap.add_argument("--ann-b", required=True)
ap.add_argument("--adjudication")
ap.add_argument("--adjudication-template")
ap.add_argument("--dataset", required=True)
a = ap.parse_args()

DS = Path(a.dataset).resolve()
PANEL = ["deepseek-v4.1-flash", "gemma4_31b", "kimi-k2.6", "mistral-large-3_675b"]
PANEL_TAG = {"cb": "v0.9.3/panel/panel_{j}_cb_{m}", "bm25": "v0.9.3/panel/panel_{j}_bm25_{m}",
             "dense": "v0.9.3/panel/panel_{j}_dense_{m}", "fc": "v0.9.3/panel/panel_{j}_fc_{m}",
             "k50": "v0.9.4/panel/panel_{j}_k50dense_{m}", "open-region": "v0.9.3/panel/panel_{j}_openregion_agg81_{m}",
             "oracle": "v0.9.3/panel/panel_{j}_oracle_agg81_{m}"}


def read(p):
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def kappa(x, y):
    n = len(x)
    if n == 0:
        return float("nan")
    po = sum(i == j for i, j in zip(x, y)) / n
    px, py = sum(x) / n, sum(y) / n
    pe = px * py + (1 - px) * (1 - py)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def fmt(k, n):
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% ({k}/{n}) [{100 * lo:.1f}, {100 * hi:.1f}]" if n else "n/a"


truthy = lambda v: str(v).strip().lower() in ("true", "1", "yes", "y", "correct")
sample = read(a.sample)
A = {r["sample_id"]: r["label"].strip().lower() for r in read(a.ann_a)}
B = {r["sample_id"]: r["label"].strip().lower() for r in read(a.ann_b)}
ok = {"correct", "incorrect", "unsure"}
bad = [(s, v) for d in (A, B) for s, v in d.items() if v not in ok]
if bad or set(A) != {r["sample_id"] for r in sample} or set(B) != set(A):
    sys.exit(f"label files do not match the sample or contain other values: {bad[:5]}")

adj = {}
if a.adjudication:
    adj = {r["sample_id"]: r["label_adjudicated"].strip().lower() for r in read(a.adjudication)}
need = [r for r in sample if A[r["sample_id"]] != B[r["sample_id"]] or "unsure" in (A[r["sample_id"]], B[r["sample_id"]])]
if a.adjudication_template:
    with open(a.adjudication_template, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "label_a", "label_b", "label_adjudicated", "note"])
        w.writeheader()
        for r in need:
            w.writerow({"sample_id": r["sample_id"], "label_a": A[r["sample_id"]], "label_b": B[r["sample_id"]],
                        "label_adjudicated": "", "note": ""})
    print(f"wrote adjudication template: {len(need)} rows")

ref = {}
for r in sample:
    s = r["sample_id"]
    if A[s] == B[s] and A[s] != "unsure":
        ref[s] = A[s] == "correct"
    elif adj.get(s) in ("correct", "incorrect"):
        ref[s] = adj[s] == "correct"
missing = [r["sample_id"] for r in sample if r["sample_id"] not in ref]

out = []
P = out.append
P("## Judge validation, round 2 (prespec_judge_validation_2026-10-12)")
P(f"- rows {len(sample)} (main {sum(r['stratum'] == 'main' for r in sample)}, "
  f"aux {sum(r['stratum'] != 'main' for r in sample)}); needing adjudication {len(need)}; "
  f"without a reference label {len(missing)}")

# annotators
both = [r["sample_id"] for r in sample if "unsure" not in (A[r["sample_id"]], B[r["sample_id"]])]
xa = [A[s] == "correct" for s in both]
xb = [B[s] == "correct" for s in both]
agree = sum(i == j for i, j in zip(xa, xb))
P(f"- annotators: unsure A {sum(v == 'unsure' for v in A.values())}, B {sum(v == 'unsure' for v in B.values())}, "
  f"both {sum(A[s] == B[s] == 'unsure' for s in A)}; raw agreement on rows without unsure {fmt(agree, len(both))}; "
  f"Cohen kappa {kappa(xa, xb):.3f}")


def block(rows, label, weights=None, with_kappa=True):
    rows = [r for r in rows if r["sample_id"] in ref]
    res = []
    for jname, col in (("primary", "judge_label"), ("secondary", "judge_label_secondary")):
        j = [truthy(r[col]) for r in rows]
        h = [ref[r["sample_id"]] for r in rows]
        k = sum(x == y for x, y in zip(j, h))
        line = f"{jname} {fmt(k, len(rows))}" + (f", kappa {kappa(j, h):.3f}" if with_kappa else "")
        if weights:
            wsum = sum(weights[(r["model"], r["setting"])] for r in rows)
            wk = sum(weights[(r["model"], r["setting"])] * (x == y) for r, x, y in zip(rows, j, h))
            line += f"; post-stratified {100 * wk / wsum:.1f}%"
        res.append(line)
    P(f"- {label} (n={len(rows)}): " + " | ".join(res))


# cell populations (same rules as sample_judge_validation.py; run from the dataset root semantics)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import os  # noqa: E402
cwd = os.getcwd()
os.chdir(DS)
import sample_judge_validation as sj  # noqa: E402
sj.ROOT = DS
sj.P = DS / "results" / "predictions_v0.9.5"
qa = {json.loads(l)["qa_id"]: json.loads(l) for l in open(DS / "data/qa_v0.6_test_public.jsonl")}
excl = {l.strip() for l in open(DS / "data/v0.9.3/eval_exclusions.txt") if l.strip() and l[0] != "#"}
scope = {q for q, r in qa.items() if r["task_type"] != "cross_document_legal_reasoning" and q not in excl}
fc_items = {r["qa_id"] for r in sj.load(sj.FC_ITEMS_FROM)}
agg = {json.loads(l)["qa_id"] for l in open(DS / "results/item_sets/agg81.jsonl")}
h80 = set()
for r in sj.load("human80/human80"):
    q, m, s = r["qa_id"].split("__")
    h80.add((q, m, {"rag": "bm25"}.get(s, s)))
pool = {}
for setting, by_model in sj.SETTINGS.items():
    for model, files in by_model.items():
        ids = set()
        for fn in files:
            ids |= {r["qa_id"] for r in sj.load(fn) if r.get("split", "test_public") == "test_public"}
        ids &= scope
        if setting == "fc":
            ids &= fc_items
        if setting in ("k50", "open-region", "oracle"):
            ids &= agg
        pool[(model, setting)] = len({q for q in ids if (q, model, setting) not in h80})
os.chdir(cwd)
per_cell = Counter((r["model"], r["setting"]) for r in sample if r["stratum"] == "main")
weights = {c: pool[c] / per_cell[c] for c in per_cell}

main = [r for r in sample if r["stratum"] == "main"]
block(main, "main stratum, overall", weights)
P("- by setting:")
for s in sj.SETTINGS:
    block([r for r in main if r["setting"] == s], f"  {s}", with_kappa=False)
P("- by model:")
for m in sj.CB:
    block([r for r in main if r["model"] == m], f"  {m}", with_kappa=False)
P("- by family:")
for f, sel in (("cross_source_aggregation", lambda t: t == "cross_source_aggregation"),
               ("long_context_retrieval", lambda t: t == "long_context_retrieval"),
               ("other", lambda t: t not in ("cross_source_aggregation", "long_context_retrieval"))):
    block([r for r in main if sel(r["task_type"])], f"  {f}", with_kappa=False)

# panel on the Anthropic predictions of the main stratum
anth = [r for r in main if r["model"].startswith("claude") and r["sample_id"] in ref]
pv = {}
for jn in PANEL:
    for s, tpl in PANEL_TAG.items():
        for m in ("claude-sonnet-5-5", "claude-haiku-5-5"):
            v, rest = tpl.split("/", 1)
            fp = DS / "results" / f"judge_verdicts_{v}" / (rest.format(j=jn, m=m) + ".jsonl")
            for l in open(fp):
                d = json.loads(l)
                pv[(jn, s, m, d["qa_id"])] = bool(d["judge_correct"])
P(f"- six judges on the Anthropic predictions of the main stratum (n={len(anth)}):")
for jn, get in [("primary", lambda r: truthy(r["judge_label"])), ("secondary", lambda r: truthy(r["judge_label_secondary"]))] + \
        [(jn, (lambda jn: lambda r: pv[(jn, r["setting"], r["model"], r["qa_id"])])(jn)) for jn in PANEL]:
    j = [get(r) for r in anth]
    h = [ref[r["sample_id"]] for r in anth]
    P(f"  - {jn}: {fmt(sum(x == y for x, y in zip(j, h)), len(anth))}, kappa {kappa(j, h):.3f}")

aux = [r for r in sample if r["stratum"] != "main"]
if aux:
    block(aux, "auxiliary string-mismatch stratum (reported separately)")

P("")
P("### Registry entry draft")
P("```markdown")
P("### Judge validation, round 2 (2026-10-12 sample; shared/annotated/judge_validation_2026-10-12/, "
  "script shared/scripts/peerreview_check/score_judge_validation.py)")
for l in out[1:]:
    if not l.startswith("###") and l:
        P(l)
P("```")
print("\n".join(out))
if missing:
    print(f"\nrows without a reference label (adjudicate first): {missing[:20]}{' ...' if len(missing) > 20 else ''}")
