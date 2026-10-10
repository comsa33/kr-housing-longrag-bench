#!/usr/bin/env python3
"""WP5: draw a 400+ stratified human-review sample from the v0.6 realism QA (internal, verdicts blank).

Coverage: all task families, all providers, all question_styles (incl. rewritten cloze→natural and
diagnostic_probe), and enough agent-authored / multi-doc / legal / table items. Human review is NOT
marked complete here — `verdict` stays blank until a reviewer fills it.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "qa_v0.6_realistic_candidates.jsonl"
OUT = ROOT / "workspace_local" / "audit" / "human_review_sample_v06.jsonl"
AGENT_FAMILIES = {"cross_document_legal_reasoning", "multi_document_comparison"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20260605)
    args = ap.parse_args()
    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    rng = random.Random(args.seed)
    picked, ids = [], set()

    def add(items, k):
        for r in (items if len(items) <= k else rng.sample(items, k)):
            if r["qa_id"] in ids:
                continue
            ids.add(r["qa_id"])
            picked.append({
                "qa_id": r["qa_id"], "task_type": r["task_type"], "question_style": r.get("question_style"),
                "split": r.get("split"), "provider": r.get("provider"), "region_sido": r.get("region_sido"),
                "original_question": r.get("original_question"), "question": r["question"],
                "answer": r["answer"], "evidence": r.get("evidence"), "page_ids": r.get("page_ids"),
                "table_ids": r.get("table_ids"), "cell_ids": r.get("cell_ids"),
                "gold_predicate": r.get("gold_predicate"), "evaluation": r.get("evaluation"),
                "bundle_id": r.get("bundle_id"), "evidence_position": r.get("evidence_position"),
                # BLANK reviewer fields — fill during human review
                "reviewer_id": "", "verdict": "", "error_type": "", "notes": "", "reviewed_at": "",
            })

    by_fam = defaultdict(list)
    by_prov = defaultdict(list)
    by_style = defaultdict(list)
    for r in rows:
        by_fam[r["task_type"]].append(r)
        by_prov[r.get("provider", "?")].append(r)
        by_style[r.get("question_style", "?")].append(r)

    # stratify: per family, per provider, per style, plus extra from agent families
    for fam, items in sorted(by_fam.items()):
        add(items, 24)
    for prov, items in sorted(by_prov.items()):
        add(items, 12)
    for style, items in sorted(by_style.items()):
        add(items, 30)
    # ensure >=50 agent-authored
    if sum(1 for p in picked if p["task_type"] in AGENT_FAMILIES) < 50:
        pool = [r for f in AGENT_FAMILIES for r in by_fam.get(f, []) if r["qa_id"] not in ids]
        rng.shuffle(pool)
        add(pool, 50)
    # top up to target with a random spread
    if len(picked) < args.target:
        pool = [r for r in rows if r["qa_id"] not in ids]
        rng.shuffle(pool)
        add(pool, args.target - len(picked))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in picked), encoding="utf-8")
    print(f"=== human-review sample v0.6: {len(picked)} items (seed={args.seed}, verdicts BLANK) ===")
    print("  families:", dict(Counter(p["task_type"] for p in picked)))
    print("  styles:", dict(Counter(p["question_style"] for p in picked)))
    print("  providers:", len({p["provider"] for p in picked}), "| agent-family:",
          sum(1 for p in picked if p["task_type"] in AGENT_FAMILIES))
    print(f"  -> {OUT}  (human review NOT complete; fill 'verdict')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
