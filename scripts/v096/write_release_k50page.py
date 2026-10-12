"""Write the v0.9.6 release files for the k=50 + announcement-page run (18 items x 6 models).

Build-machine only: reads the judge inputs and raw batch outputs kept under
$KRH_WORKSPACE/archive_scratchpads/2026-10-12/bad0f45b-f680-4f0e-baa1-8aae8abe8a23/k50page/ (not released).
Writes, with no model calls:
  results/judge_verdicts_v0.9.6/{claude-sonnet-5-5,gpt-4.1-mini}/k50page_<model>.jsonl  ({qa_id, judge_correct})
  results/judge_verdicts_v0.9.6/panel/panel_<judge>_k50page_<model>.jsonl             ({qa_id, judge_correct})
  results/judge_verdicts_v0.9.6/MANIFEST.csv
  results/predictions_v0.9.6/k50page_<model>.jsonl + MANIFEST.csv  (the exact strings the primary judge scored,
  masked with the v0.9.5 rules: a >=200-character run shared with the bundle text after removing whitespace,
  and phone numbers that occur in no bundle)
Usage (from the repository root): python3 scripts/v096/write_release_k50page.py
"""
import collections
import csv
import glob
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WS = Path(os.environ.get("KRH_WORKSPACE", ROOT / "workspace_local"))
SRC = WS / "archive_scratchpads/2026-10-12/bad0f45b-f680-4f0e-baa1-8aae8abe8a23/k50page"
RES = ROOT / "results"
VOUT = RES / "judge_verdicts_v0.9.6"
POUT = RES / "predictions_v0.9.6"
PRIMARY, SECONDARY = "claude-sonnet-5-5", "gpt-4.1-mini"
MODELS = ["gpt-5.5", "minimax-m3", "glm-5.2", "claude-sonnet-5-5", "claude-haiku-5-5", "gpt-4.1-mini"]
PANEL_MODEL = {"sonnet55": "claude-sonnet-5-5", "haiku55": "claude-haiku-5-5"}
SETTING = "dense k=50 + announcement page"
L = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def pred_of(prompt):
    return prompt.rsplit("\n[모델답변]", 1)[1].rsplit("\n\n판정:", 1)[0].strip()


# --- verdicts and judged strings
idx = {r["custom_id"]: r for f in glob.glob(str(SRC / "judge/index_*.jsonl")) for r in L(f)}
prim, sec, judged = collections.defaultdict(dict), collections.defaultdict(dict), collections.defaultdict(dict)
for f in glob.glob(str(SRC / "judge/raw_claude_requests_*.jsonl")):
    for r in L(f):
        i = idx[r["custom_id"]]; res = r["result"]
        assert res["type"] == "succeeded", r["custom_id"]
        t = "".join(b.get("text", "") for b in res["message"]["content"] if b["type"] == "text")
        prim[i["model"]][i["qa_id"]] = json.loads(t)["verdict"] == "YES"
for f in glob.glob(str(SRC / "judge/raw_gpt_requests_*.jsonl")):
    for r in L(f):
        i = idx[r["custom_id"]]
        txt = (r["response"]["body"]["choices"][0]["message"].get("content") or "").strip().upper()
        sec[i["model"]][i["qa_id"]] = txt.startswith("YES")
for f in glob.glob(str(SRC / "judge/claude_requests_*.jsonl")):
    for r in L(f):
        i = idx[r["custom_id"]]; judged[i["model"]][i["qa_id"]] = pred_of(r["params"]["messages"][0]["content"])
items = sorted(json.loads(l)["qa_id"] for l in open(SRC / "prompts_k50page_18.jsonl"))
for m in MODELS:
    assert sorted(prim[m]) == items and sorted(sec[m]) == items and sorted(judged[m]) == items, m

man = []
for judge, D in ((PRIMARY, prim), (SECONDARY, sec)):
    (VOUT / judge).mkdir(parents=True, exist_ok=True)
    for m in MODELS:
        with open(VOUT / judge / f"k50page_{m}.jsonl", "w", encoding="utf-8") as fo:
            for q in items: fo.write(json.dumps({"qa_id": q, "judge_correct": D[m][q]}) + "\n")
        man.append((judge, f"k50page_{m}", m, SETTING, "test_public", len(items)))
(VOUT / "panel").mkdir(parents=True, exist_ok=True)
panel_counts = {}
for f in sorted(glob.glob(str(SRC / "judge/panel_out/*.judged.jsonl"))):
    stem = Path(f).name.replace("panel_", "").replace("_k50page.judged.jsonl", "")
    judge, short = stem.rsplit("_", 1); m = PANEL_MODEL[short]
    rows = L(f); assert sorted(r["qa_id"] for r in rows) == items and all(r["judge_correct"] is not None for r in rows), f
    tag = f"panel_{judge}_k50page_{m}"
    with open(VOUT / "panel" / f"{tag}.jsonl", "w", encoding="utf-8") as fo:
        for r in sorted(rows, key=lambda r: r["qa_id"]):
            fo.write(json.dumps({"qa_id": r["qa_id"], "judge_correct": bool(r["judge_correct"])}) + "\n")
    man.append((judge, tag, m, SETTING + " (panel re-score)", "test_public", len(rows)))
    panel_counts[tag] = sum(bool(r["judge_correct"]) for r in rows)
with open(VOUT / "MANIFEST.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["judge", "tag", "model", "regime", "split", "n"]); w.writerows(man)

# --- model answers with the v0.9.5 masking rules
G = {}
for sp in ("dev", "test_public"):
    for d in L(ROOT / f"data/qa_v0.6_{sp}.jsonl"): G[d["qa_id"]] = d
BUN = WS / "processed/bundles-v06"
allb = "\n".join(p.read_text(encoding="utf-8") for p in BUN.glob("*.txt"))
K = 20
PH = re.compile(r"(?<!\d)(?:0\d{1,2}|1\d{3})[-.)\s]\d{3,4}[-.\s]\d{4}(?!\d)")


def mask_overlap(s, bid):
    bst = re.sub(r"\s+", "", (BUN / f"{bid}.txt").read_text(encoding="utf-8"))
    H = {hash(bst[j:j + K]) for j in range(len(bst) - K + 1)}
    pos = [i for i, c in enumerate(s) if not c.isspace()]; st = "".join(s[i] for i in pos)
    spans, run = [], -1
    for i in range(len(st) - K + 1):
        if hash(st[i:i + K]) in H:
            run = i if run < 0 else run
        elif run >= 0:
            spans.append((run, i - 1 + K)); run = -1
    if run >= 0: spans.append((run, len(st)))
    spans = [(a, b) for a, b in spans if b - a >= 200]
    out = s
    for a, b in reversed(spans):
        oa, ob = pos[a], pos[b - 1] + 1
        out = out[:oa] + f"[source text omitted, {ob - oa} chars]" + out[ob:]
    return out, len(spans)


POUT.mkdir(parents=True, exist_ok=True)
stats = collections.Counter(); pman = []
raw_preds = {m: {r["qa_id"]: r["prediction"] for r in L(SRC / f"preds/{m}.jsonl")} for m in MODELS}
for m in MODELS:
    with open(POUT / f"k50page_{m}.jsonl", "w", encoding="utf-8") as fo:
        for q in items:
            s = judged[m][q]
            stats["equal_to_parsed_pred"] += s == raw_preds[m][q].strip()
            s2, ns = mask_overlap(s, G[q]["bundle_id"]); stats["overlap_masked"] += ns
            for ph in set(PH.findall(s2)):
                if ph not in allb: s2 = s2.replace(ph, "[phone number omitted]"); stats["phone_masked"] += 1
            fo.write(json.dumps({"qa_id": q, "split": "test_public", "model": m, "setting": SETTING, "prediction": s2,
                                 "judge_label": prim[m][q], "judge_label_secondary": sec[m][q]},
                                ensure_ascii=False) + "\n")
            stats["records"] += 1
    pman.append((f"k50page_{m}.jsonl", m, SETTING, len(items), len(items), 0,
                 f"judge_verdicts_v0.9.6/{{claude-sonnet-5-5,gpt-4.1-mini}}/k50page_{m}.jsonl"))
with open(POUT / "MANIFEST.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["file", "model", "setting", "n", "n_test_public", "n_dev", "verdict_file"]); w.writerows(pman)
print(dict(stats))
print({m: (sum(prim[m].values()), sum(sec[m].values())) for m in MODELS})
print(panel_counts)
