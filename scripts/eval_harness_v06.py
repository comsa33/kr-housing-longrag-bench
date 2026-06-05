#!/usr/bin/env python3
"""v0.6 evaluation harness: score model predictions against gold, with cluster-weighted accuracy.

Gold sources (answers):
  dev          -> data/qa_v0.6_dev.jsonl
  test_public  -> data/qa_v0.6_test_public.jsonl
  test_hidden  -> workspace_local/audit/qa_v0.6_test_hidden_answers.jsonl  (INTERNAL; the public
                  data/qa_v0.6_test_hidden_questions.jsonl has answers masked)

Predictions: JSONL with {"qa_id": ..., "prediction": "..."}. Use --self-test to score gold-as-prediction
(sanity: should be ~100%). Scoring is per evaluation.metric against the canonical `answer`:
  exact_numbers      -> every numeric token of the gold answer appears in the prediction
  boolean_and_reason -> prediction contains an 'unanswerable' marker
  contains_all/exact_match/term_recall/span/other -> normalized gold answer is contained in prediction
Missing or empty predictions are always scored as incorrect.

Reports plain accuracy and CLUSTER-WEIGHTED accuracy (each near-dup cluster contributes ~1, not N),
broken down by split / task_type / question_style.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = {
    "dev": ROOT / "data" / "qa_v0.6_dev.jsonl",
    "test_public": ROOT / "data" / "qa_v0.6_test_public.jsonl",
    "test_hidden": ROOT / "workspace_local" / "audit" / "qa_v0.6_test_hidden_answers.jsonl",
}
UNANS = ["확정할 수 없", "답할 수 없", "알 수 없", "unanswerable", "근거가 없", "없음", "제공된 자료"]


def norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s))


def nums(s: str) -> list:
    return re.findall(r"\d[\d,]*(?:\.\d+)?", str(s))


def score(item: dict, pred: str) -> bool:
    metric = item.get("evaluation", {}).get("metric", "")
    ans = item.get("answer", "")
    if not pred or not norm(pred):  # missing / None / empty / whitespace-only -> incorrect
        return False
    if metric == "boolean_and_reason":
        return any(m in pred for m in UNANS)
    if metric == "exact_numbers":
        pn = norm(pred).replace(",", "")
        gold = [n.replace(",", "") for n in nums(ans)]
        return bool(gold) and all(n in pn for n in gold)
    npred, nans = norm(pred), norm(ans)
    return bool(nans) and (nans in npred or npred in nans)


def load(path: Path) -> list:
    return [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()] if path.exists() else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", default=None, help="JSONL of {qa_id, prediction}")
    ap.add_argument("--splits", default="dev,test_public,test_hidden")
    ap.add_argument("--self-test", action="store_true", help="use gold answer as the prediction (sanity)")
    args = ap.parse_args()

    splits = [s.strip() for s in args.splits.split(",") if s.strip()]
    gold = {}
    loaded_splits = []
    missing_splits = []
    for sp in splits:
        rows = load(GOLD[sp])
        if rows:
            loaded_splits.append(sp)
        else:
            missing_splits.append(sp)
        for it in rows:
            it["_split"] = sp
            gold[it["qa_id"]] = it
    if not gold:
        print("no gold loaded")
        return 1

    preds = {}
    if args.self_test:
        preds = {qid: it.get("answer", "") for qid, it in gold.items()}
    elif args.pred:
        for r in load(ROOT / args.pred):
            preds[r["qa_id"]] = r.get("prediction", "")
    else:
        print("provide --pred FILE or --self-test")
        return 2

    by = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])  # key -> [raw_correct, raw_total, w_correct, w_total]

    def add(key, ok, w):
        b = by[key]
        b[0] += int(ok); b[1] += 1; b[2] += w * int(ok); b[3] += w

    missing = 0
    for qid, it in gold.items():
        if qid not in preds:
            missing += 1
        ok = score(it, preds.get(qid, ""))
        w = it.get("cluster_weight", 1.0)
        for key in ("ALL", f"split:{it['_split']}", f"task:{it['task_type']}", f"style:{it.get('question_style','?')}"):
            add(key, ok, w)

    def line(key):
        c, t, wc, wt = by[key]
        return f"{key:34s} acc {c/t:6.1%} ({int(c)}/{int(t)})   cluster-weighted {wc/wt:6.1%}" if t else key

    mode = "self-test (gold-as-prediction)" if args.self_test else f"predictions={args.pred}"
    print(f"== v0.6 eval harness — {mode} ==")
    print(f"gold items: {len(gold)} over loaded splits {loaded_splits}; predictions missing: {missing}")
    if missing_splits:
        print(f"gold unavailable for requested splits {missing_splits} (expected for clean checkout hidden split)")
    print(line("ALL"))
    for grp in ("split:", "task:", "style:"):
        print(f"-- by {grp[:-1]} --")
        for key in sorted(k for k in by if k.startswith(grp)):
            print("  " + line(key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
