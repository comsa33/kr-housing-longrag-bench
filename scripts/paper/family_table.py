#!/usr/bin/env python3
"""Accuracy by task family on test_public for one regime (paper Appendix: task family table).

Re-aggregates existing LLM-judge verdict files only (no model calls). Scoring rule as in
scripts/score_judge.py: a verdict counts as correct iff `judge_correct` is truthy.

    python3 shared/scripts/family_table.py [--regime bm25] [--exclude-family cross_document_legal_reasoning]

Works from the paper repo (dataset at ../kr-housing-longrag-bench) and from the dataset repo
(scripts/paper/). Verdicts are read from workspace_local/audit/baselines/<tag>.judged.jsonl when present,
else results/judge_verdicts/<tag>.jsonl.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
DEFAULT_ROOT = HERE.parents[2] if (HERE.parents[2] / "data").is_dir() else HERE.parents[3] / "kr-housing-longrag-bench"

# display name -> tag per regime (same tags as paired_rq1.py / score_judge.py)
RUNS = {
    "gpt-4.1-mini": {"cb": "gpt-4.1-mini_cb", "bm25": "gpt-4.1-mini_rag", "dense": "jf386_gpt-4.1-mini_dense", "fc": "gpt-4.1-mini_fc"},
    "gpt-5.4-mini": {"cb": "gpt-5.4-mini_cb", "bm25": "gpt-5.4-mini_rag", "dense": "jf386_gpt-5.4-mini_dense", "fc": "gpt-5.4-mini_fc"},
    "gpt-5.4-nano": {"cb": "gpt-5.4-nano_cb", "bm25": "gpt-5.4-nano_rag", "dense": "jf386_gpt-5.4-nano_dense", "fc": "gpt-5.4-nano_fc"},
    "gpt-5.5": {"cb": "gpt-5.5_cb", "bm25": "gpt-5.5_rag", "dense": "jf386_gpt-5.5_dense", "fc": "g55fc"},
    "minimax-m3": {"cb": "cb_minimax-m3-cloud_tp", "bm25": "rag_minimax-m3-cloud_tp", "dense": "jf386_minimax-m3_dense", "fc": "fc_minimax-m3-cloud_tp"},
    "glm-5.2": {"cb": "cb_glm-5.2-cloud_tp", "bm25": "rag_glm-5.2-cloud_tp", "dense": "jf386_glm-5.2_dense", "fc": "fc_glm-5.2-cloud_tp"},
    "qwen3.5": {"cb": "cb_qwen3.5-cloud_tp", "bm25": "rag_qwen3.5-cloud_tp", "dense": "jf386_qwen3.5_dense", "fc": "fc_qwen3.5-cloud_tp"},
}


def verdict_path(root: Path, tag: str) -> Path:
    p = root / "workspace_local" / "audit" / "baselines" / f"{tag}.judged.jsonl"
    return p if p.exists() else root / "results" / "judge_verdicts" / f"{tag}.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(DEFAULT_ROOT))
    ap.add_argument("--regime", default="bm25", choices=["cb", "bm25", "dense", "fc"])
    ap.add_argument("--models", default="gpt-4.1-mini,gpt-5.5,minimax-m3,glm-5.2")
    ap.add_argument("--min-n", type=int, default=4, help="hide families with fewer items")
    ap.add_argument("--exclude-family", default="")
    ap.add_argument("--exclude-bundle", default="")
    args = ap.parse_args()
    root = Path(args.dataset)
    xf = {s for s in args.exclude_family.split(",") if s}
    xb = {s for s in args.exclude_bundle.split(",") if s}
    gold = {}
    for line in (root / "data" / "qa_v0.6_test_public.jsonl").open(encoding="utf-8"):
        if line.strip():
            d = json.loads(line)
            if d.get("task_type") not in xf and d.get("bundle_id") not in xb:
                gold[d["qa_id"]] = d
    models = [m for m in args.models.split(",") if m]
    acc = {m: defaultdict(lambda: [0, 0]) for m in models}
    nfam = defaultdict(set)
    for m in models:
        for line in verdict_path(root, RUNS[m][args.regime]).open(encoding="utf-8"):
            if not line.strip():
                continue
            d = json.loads(line)
            g = gold.get(d["qa_id"])
            if not g:
                continue
            f = g["task_type"]
            acc[m][f][0] += 1
            acc[m][f][1] += 1 if d.get("judge_correct") else 0
            nfam[f].add(d["qa_id"])
    fams = sorted(nfam, key=lambda f: -len(nfam[f]))
    print(f"regime={args.regime}  items scored={sum(len(v) for v in nfam.values())}")
    print(f"{'family':32} {'n':>4} " + " ".join(f"{m:>13}" for m in models))
    for f in fams:
        if len(nfam[f]) < args.min_n:
            continue
        cells = []
        for m in models:
            n, h = acc[m][f]
            cells.append(f"{100*h/n:3.0f} ({h}/{n})" if n else "—")
        print(f"{f:32} {len(nfam[f]):>4} " + " ".join(f"{c:>13}" for c in cells))
    small = [f"{f} ({len(nfam[f])})" for f in fams if len(nfam[f]) < args.min_n]
    if small:
        print("hidden (<min-n):", ", ".join(small))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
