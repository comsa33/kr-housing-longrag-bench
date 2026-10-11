#!/usr/bin/env python3
"""Closed-book accuracy before and after the v0.9.3 corrections, from released verdicts only (no API calls).

After = the v0.9.2 closed-book verdicts with the leak-fixed items replaced by `cbfix_*` and, for gpt-5.5,
the empty-at-cap items replaced by `g55retry_cb_*`. Plain accuracy on the v0.9.2 scope (primary judge).

    python3 scripts/v093/score_cb_corrected.py
"""
import json
from pathlib import Path
W = Path(__file__).resolve().parents[2]
V2 = W / "results/judge_verdicts_v0.9.2/claude-sonnet-5-5"; V3 = W / "results/judge_verdicts_v0.9.3/claude-sonnet-5-5"
def load(p): return {r["qa_id"]: r["judge_correct"] for r in map(json.loads, open(p))} if p.exists() else {}
split = {}
for sp in ("dev", "test_public"):
    for l in open(W / f"data/qa_v0.6_{sp}.jsonl", encoding="utf-8"): split[json.loads(l)["qa_id"]] = sp
RUNS = {"gpt-4.1-mini": "gpt-4.1-mini_cb", "gpt-5.4-mini": "gpt-5.4-mini_cb", "gpt-5.4-nano": "gpt-5.4-nano_cb",
        "gpt-5.5": "gpt-5.5_cb", "minimax-m3": "cb_minimax-m3-cloud_tp", "glm-5.2 (reasoning off)": "cb_glm-5.2-cloud_tp"}
print("| model | split | n | before | after |")
for m, tag in RUNS.items():
    before = load(V2 / f"{tag}.jsonl"); after = dict(before); key = m.split(" ")[0]
    for sp in ("test_public", "dev"):
        after.update({q: v for q, v in load(V3 / f"cbfix_{key}_{sp}.jsonl").items() if q in after})
        if key == "gpt-5.5": after.update({q: v for q, v in load(V3 / f"g55retry_cb_{sp}.jsonl").items() if q in after})
    for sp in ("test_public", "dev"):
        qs = [q for q in before if split.get(q) == sp]
        if qs: print(f"| {m} | {sp} | {len(qs)} | {100*sum(before[q] for q in qs)/len(qs):.1f} | {100*sum(after[q] for q in qs)/len(qs):.1f} |")
