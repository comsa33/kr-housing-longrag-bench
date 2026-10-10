#!/usr/bin/env python3
"""WP8: draw a fixed-seed, family-stratified human-review sample (300+) from qa_v0.5_candidates.jsonl.

Guarantees coverage of every task family and >=50 items from the agent-authored families
(cross_document_legal_reasoning, multi_document_comparison). Each row carries the evidence a reviewer
needs plus BLANK reviewer fields. Human review is NOT marked complete here — verdicts must be filled in.

Output (internal): workspace_local/audit/human_review_sample_v05.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "qa_v0.5_candidates.jsonl"
OUT = ROOT / "workspace_local" / "audit" / "human_review_sample_v05.jsonl"
AGENT_FAMILIES = {"cross_document_legal_reasoning", "multi_document_comparison"}

CHECKS = {
    "table_numeric_reasoning": "predicate/셀 값이 질문과 일치하고 단위·필터 정확한가?",
    "cross_source_aggregation": "공고→지역 hop이 타당하고 집계가 질문과 맞는가?",
    "format_robustness": "4개 포맷 모두 동일 행 수가 맞는가?",
    "answerability_detection": "정말 제공 자료만으로 답할 수 없는가(부재 확인)?",
    "long_context_retrieval": "cloze 정답이 유일하고 모호하지 않은가?",
    "long_distance_retrieval": "정답이 후반부 페이지에 실재하고 유일한가?",
    "cross_document_legal_reasoning": "공고 사실 + 법조문이 실제로 연결/일치하는가? 과장 없는가?",
    "multi_document_comparison": "두 공고 비교가 사실이고 양쪽 근거가 실재하는가?",
    "eligibility_reasoning": "자격요건 셀(행×열)이 질문과 맞고 답이 표에 실재하는가?",
    "schedule_reasoning": "해당 단계의 일정(일자)이 표에 실재하는가?",
    "correction_notice_reasoning": "정정 표기가 공고문에 실재하고 판정이 맞는가?",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-family", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20260605)
    args = ap.parse_args()

    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    by_fam = defaultdict(list)
    for r in rows:
        by_fam[r["task_type"]].append(r)

    rng = random.Random(args.seed)
    sample, picked_ids = [], set()

    def take(items, k):
        picks = items if len(items) <= k else rng.sample(items, k)
        for r in picks:
            if r["qa_id"] in picked_ids:
                continue
            picked_ids.add(r["qa_id"])
            sample.append({
                "qa_id": r["qa_id"], "task_type": r["task_type"], "split": r.get("split"),
                "provider": r.get("provider"), "region_sido": r.get("region_sido"),
                "question": r["question"], "answer": r["answer"],
                "source_ids": r.get("source_ids"), "page_ids": r.get("page_ids"),
                "table_ids": r.get("table_ids"), "cell_ids": r.get("cell_ids"),
                "row_ids": (r.get("row_ids") or [])[:3], "gold_predicate": r.get("gold_predicate"),
                "evidence": r.get("evidence"), "evaluation": r.get("evaluation"),
                "what_to_check": CHECKS.get(r["task_type"], "근거 실재 + 모호성 없음 확인"),
                # BLANK reviewer fields — fill during human review
                "reviewer_id": "", "verdict": "", "error_type": "", "notes": "", "reviewed_at": "",
            })

    for fam, items in sorted(by_fam.items()):
        take(items, args.per_family)
    # ensure >=50 from agent-authored families
    agent_n = sum(1 for s in sample if s["task_type"] in AGENT_FAMILIES)
    if agent_n < 50:
        pool = [r for f in AGENT_FAMILIES for r in by_fam.get(f, []) if r["qa_id"] not in picked_ids]
        rng.shuffle(pool)
        take(pool, 50 - agent_n)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for s in sample:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    fam = Counter(s["task_type"] for s in sample)
    agent_n = sum(1 for s in sample if s["task_type"] in AGENT_FAMILIES)
    print(f"=== human-review sample v0.5: {len(sample)} items (<= {args.per_family}/family, seed={args.seed}) ===")
    for k, v in sorted(fam.items()):
        print(f"   {k:32s} {v}")
    print(f"   agent-authored-family items: {agent_n} (target >=50)")
    print(f"   splits: {dict(Counter(s['split'] for s in sample))}")
    print(f"   -> {OUT}  (verdict fields BLANK; human review pending)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
