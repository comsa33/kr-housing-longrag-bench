#!/usr/bin/env python3
"""Build a BLIND human-validation CSV for the LLM-judge (lever 3 validation).

Standard inter-annotator-agreement setup: sample a stratified set of judged predictions,
write {question, gold, prediction} WITHOUT the judge verdict, so the human annotator (Ruo)
labels human_correct (Y/N) independently — no anchoring. We later join by qa_id+model+regime
to the stored judge verdicts and report raw agreement % + Cohen's kappa.

Stratified to surface judge errors: balances the judge's YES vs NO, and force-includes the
ambiguous categories where a judge is most likely wrong (legal paraphrase, comparisons,
cross_source, abstention, the 512k tier). Substantive regimes only (rag, fc).

Open the CSV (UTF-8-BOM, Excel/Sheets-friendly) and fill the `human_correct` column with Y or N.

    python3 scripts/make_judge_validation_csv.py [--n 80] [--seed 20260611]
    -> workspace_local/audit/baselines/judge_validation.csv  (INTERNAL; gold answers inside)
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "workspace_local" / "audit" / "baselines"
HARD = {"cross_source_aggregation", "cross_document_legal_reasoning", "multi_document_comparison",
        "region_comparison", "provider_comparison", "answerability_detection"}
TAGS = ([("g55fc", "gpt-5.5", "fc")]
        + [(f"{m}_{r}", m, r) for m in ("gpt-4.1-mini", "gpt-5.4-mini", "gpt-5.4-nano") for r in ("rag", "fc")]
        + [("gpt-5.5_rag", "gpt-5.5", "rag")])


def load(p: Path) -> list:
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()] if p.exists() else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--seed", type=int, default=20260611)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    gi = {}
    for sp in ("dev", "test_public"):
        for d in load(ROOT / "data" / f"qa_v0.6_{sp}.jsonl"):
            gi[d["qa_id"]] = d

    # candidates: (qa_id, model, regime, judge, gold, pred, tier, task)
    cands = []
    for tag, model, regime in TAGS:
        jf = B / f"{tag}.judged.jsonl"
        if not jf.exists():
            continue
        judged = {d["qa_id"]: d["judge_correct"] for d in load(jf)}
        preds = {}
        for sp in ("test_public", "dev"):
            for d in load(B / f"{regime}_{model}_{sp}.jsonl"):
                preds[d["qa_id"]] = d.get("prediction", "")
        for qid, jv in judged.items():
            g = gi.get(qid, {})
            cands.append({"qa_id": qid, "model": model, "regime": regime, "judge": jv,
                          "tier": g.get("context_tier"), "task": g.get("task_type"),
                          "question": g.get("question", ""), "gold": str(g.get("answer", "")),
                          "pred": preds.get(qid, "")})

    rng.shuffle(cands)
    picked, seen = [], set()

    def take(pool, k):
        for c in pool:
            key = (c["qa_id"], c["model"], c["regime"])
            if key in seen:
                continue
            seen.add(key); picked.append(c)
            k -= 1
            if k <= 0:
                break

    # force-include hard categories (both verdicts) + 512k, then balance the rest YES/NO
    for task in HARD:
        for jv in (True, False):
            take([c for c in cands if c["task"] == task and c["judge"] is jv], 3)
    take([c for c in cands if c["tier"] == "512k"], 8)
    half = max(0, (args.n - len(picked)) // 2)
    take([c for c in cands if c["judge"] is False], half)
    take([c for c in cands if c["judge"] is True], args.n - len(picked))

    rng.shuffle(picked)
    out = B / "judge_validation.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row", "qa_id", "model", "regime", "context_tier", "task_type",
                    "question", "gold_answer", "model_prediction", "human_correct(Y/N)", "notes"])
        for i, c in enumerate(picked, 1):
            w.writerow([i, c["qa_id"], c["model"], c["regime"], c["tier"], c["task"],
                        c["question"], c["gold"], c["pred"], "", ""])
    # private key file (judge verdicts) — NOT given to the annotator; used to score agreement later
    key = B / "judge_validation.key.jsonl"
    with key.open("w", encoding="utf-8") as f:
        for c in picked:
            f.write(json.dumps({"qa_id": c["qa_id"], "model": c["model"], "regime": c["regime"],
                                "judge": c["judge"]}, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"[ok] {out} ({len(picked)} items)  + key {key.name}")
    print("  judge verdict balance:", dict(Counter('YES' if c['judge'] else 'NO' for c in picked)))
    print("  by task:", dict(Counter(c['task'] for c in picked)))
    print("  512k items:", sum(1 for c in picked if c['tier'] == '512k'))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
