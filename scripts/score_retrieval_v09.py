#!/usr/bin/env python3
"""Retrieval-quality metrics for the v0.9 RAG baseline (recall@k / hit@k).

Reads a RAG prompt file produced by scripts/build_baseline_rag_v09.py (each record
carries `retrieved_page_ids` and `gold_page_ids`) and reports, over items that have
gold pages:

  recall@k = |retrieved ∩ gold| / |gold|          (fraction of gold pages retrieved)
  hit@k    = 1 if any gold page was retrieved       (did retrieval surface ANY evidence)

both plain and cluster-weighted (joining gold for cluster_weight + task_type),
cut by split / task_type / context_tier. This is a property of the RETRIEVER (model-
independent), so it is scored from the prompt file, not from predictions.

Internal-only inputs (bundle-derived); prints a table, writes nothing.

Usage:
    python3 scripts/score_retrieval_v09.py \\
        --rag workspace_local/audit/baselines/rag_bm25_v09_prompts.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = {
    "dev": ROOT / "data" / "qa_v0.6_dev.jsonl",
    "test_public": ROOT / "data" / "qa_v0.6_test_public.jsonl",
}


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rag", required=True, help="RAG prompt JSONL from build_baseline_rag_v09.py")
    args = ap.parse_args()

    rag_path = Path(args.rag) if Path(args.rag).is_absolute() else ROOT / args.rag
    if not rag_path.is_file():
        raise SystemExit(f"--rag not found: {rag_path}")
    recs = load_jsonl(rag_path)

    gold: dict[str, dict] = {}
    for f in GOLD.values():
        for r in load_jsonl(f):
            gold[r["qa_id"]] = r

    # key -> [recall_sum, w_recall_sum, hit_sum, w_hit_sum, w_sum, n]
    by: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    def add(key: str, recall: float, hit: float, w: float) -> None:
        b = by[key]
        b[0] += recall; b[1] += w * recall; b[2] += hit; b[3] += w * hit; b[4] += w; b[5] += 1

    k_vals, scored = set(), 0
    for r in recs:
        g = set(r.get("gold_page_ids") or [])
        if not g:
            continue  # no gold pages -> retrieval recall undefined
        scored += 1
        k_vals.add(r.get("k"))
        retr = set(r.get("retrieved_page_ids") or [])
        recall = len(retr & g) / len(g)
        hit = 1.0 if (retr & g) else 0.0
        it = gold.get(r["qa_id"], {})
        w = it.get("cluster_weight", 1.0)
        task = it.get("task_type", "?")
        tier = r.get("context_tier", it.get("context_tier", "?"))
        for key in ("ALL", f"split:{r.get('split','?')}", f"task:{task}", f"tier:{tier}"):
            add(key, recall, hit, w)

    def line(key: str) -> str:
        rs, wrs, hs, whs, ws, n = by[key]
        if not n:
            return key
        return (f"{key:34s} recall@k {rs/n:6.1%}  hit@k {hs/n:6.1%}   "
                f"cw-recall {wrs/ws:6.1%}  cw-hit {whs/ws:6.1%}  (n={int(n)})")

    kdisp = ",".join(str(x) for x in sorted(v for v in k_vals if v is not None))
    print(f"== v0.9 retrieval metrics — {rag_path.name} (k={kdisp}; items with gold pages={scored}) ==")
    print(line("ALL"))
    for grp in ("split:", "task:", "tier:"):
        print(f"-- by {grp[:-1]} --")
        for key in sorted(k for k in by if k.startswith(grp)):
            print("  " + line(key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
