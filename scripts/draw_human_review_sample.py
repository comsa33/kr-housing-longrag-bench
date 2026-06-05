#!/usr/bin/env python3
"""Draw a family-stratified random human-review sample from the v0.4 candidate set.

Automated verification (verify_qa.py) checks predicate recompute + verbatim grounding, but cannot
judge naturalness, ambiguity, or whether a question is a *good* benchmark item. This draws a
reproducible (fixed-seed) sample of N per family for human sign-off and writes an internal review
sheet with the evidence a reviewer needs plus blank verdict/notes fields.

Output (internal): workspace_local/audit/human_review_sample_v04.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "qa_v0.4_candidates.jsonl"
OUT = ROOT / "workspace_local" / "audit" / "human_review_sample_v04.jsonl"

CHECKS = {
    "table_numeric_reasoning": "predicate가 질문과 일치하고 답이 재계산값과 같은가? 단위/필터 정확?",
    "cross_source_aggregation": "공고→지역 hop이 타당하고 predicate 집계가 질문과 맞는가?",
    "format_robustness": "4개 포맷 모두 동일 행 수가 맞는가? 형식 표현이 자연스러운가?",
    "answerability_detection": "정말 제공 자료만으로 답할 수 없는 항목인가(부재 확인)?",
    "long_context_retrieval": "cloze 스템이 모호하지 않고 정답이 유일한가? 지나친 발췌 아님?",
    "long_distance_retrieval": "정답이 후반부 페이지에 실재하고 유일한가?",
    "cross_document_legal_reasoning": "공고 사실 + 법조문이 실제로 일치/연결되는가? 과장 없음?",
    "multi_document_comparison": "두 공고 비교가 사실이고 양쪽 근거가 실재하는가?",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-family", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20260605)
    args = ap.parse_args()

    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    by_fam = defaultdict(list)
    for r in rows:
        by_fam[r["task_type"]].append(r)

    rng = random.Random(args.seed)
    sample = []
    for fam, items in sorted(by_fam.items()):
        picks = items if len(items) <= args.per_family else rng.sample(items, args.per_family)
        for r in picks:
            sample.append({
                "qa_id": r["qa_id"], "task_type": r["task_type"],
                "question": r["question"], "answer": r["answer"],
                "source_ids": r.get("source_ids"), "page_ids": r.get("page_ids"),
                "row_ids": (r.get("row_ids") or [])[:3], "gold_predicate": r.get("gold_predicate"),
                "evidence": r.get("evidence"), "evaluation": r.get("evaluation"),
                "bundle_id": r.get("bundle_id"), "evidence_position": r.get("evidence_position"),
                "what_to_check": CHECKS.get(r["task_type"], "근거 실재 + 모호성 없음 확인"),
                "verdict": "", "reviewer": "", "notes": "",
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for s in sample:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"=== human-review sample: {len(sample)} items (<= {args.per_family}/family, seed={args.seed}) ===")
    for fam, items in sorted(by_fam.items()):
        n = min(len(items), args.per_family)
        print(f"   {fam:32s} {n}/{len(items)}")
    print(f"  -> {OUT}")
    print("  reviewers: fill 'verdict' (ok/edit/drop) + 'notes'; summarize into docs/v0.4_batch_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
