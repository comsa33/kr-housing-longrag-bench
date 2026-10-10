#!/usr/bin/env python3
"""Full-context accuracy by context tier for every model, from the existing judge verdict files.

Same inputs and scoring rule as paired_rq1.py (dataset repo scripts/score_judge.py): a verdict counts
as correct iff `judge_correct` is truthy; tiers are joined from data/qa_v0.6_test_public.jsonl.
Reports hits/n per tier so the small-window models (gpt-5.4-mini, gpt-5.4-nano, qwen3.5), which
have no 512k tier and 20 items at 256k, are documented with their n.

    python3 scripts/paper/tier_small_window.py [--verdicts-dir results/judge_verdicts]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verdict_paths import verdict_file  # noqa: E402

FC_TAGS = [
    ("gpt-4.1-mini", "gpt-4.1-mini_fc"), ("gpt-5.4-mini", "gpt-5.4-mini_fc"),
    ("gpt-5.4-nano", "gpt-5.4-nano_fc"), ("gpt-5.5", "g55fc"),
    ("minimax-m3", "fc_minimax-m3-cloud_tp"), ("glm-5.2", "fc_glm-5.2-cloud_tp"),
    ("qwen3.5", "fc_qwen3.5-cloud_tp"),
]
TIERS = ["32k", "64k", "128k", "256k", "512k"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(Path(__file__).resolve().parents[2]),
                    help="dataset repo root (default: this checkout)")
    ap.add_argument("--verdicts-dir", default=None,
                    help="read <tag>.jsonl verdicts from this directory only "
                         "(default: workspace_local/audit/baselines if present, else results/judge_verdicts)")
    ap.add_argument("--exclude-family", default="",
                    help="comma list of task_type values to drop from scoring, e.g. cross_document_legal_reasoning")
    ap.add_argument("--exclude-bundle", default="",
                    help="comma list of bundle_id values to drop from scoring, e.g. mix_multiprovider_256k")
    args = ap.parse_args()
    root = Path(args.dataset)
    gold = {}
    for line in (root / "data/qa_v0.6_test_public.jsonl").open(encoding="utf-8"):
        if line.strip():
            d = json.loads(line)
            gold[d["qa_id"]] = d
    xf = {s for s in args.exclude_family.split(",") if s}
    xb = {s for s in args.exclude_bundle.split(",") if s}
    gold = {q: g for q, g in gold.items() if g.get("task_type") not in xf and g.get("bundle_id") not in xb}
    print(f"{'model':14}" + "".join(f"{t:>14}" for t in TIERS))
    for name, tag in FC_TAGS:
        acc = defaultdict(lambda: [0, 0])
        for line in verdict_file(tag, args.verdicts_dir).open(encoding="utf-8"):
            if not line.strip():
                continue
            d = json.loads(line)
            g = gold.get(d["qa_id"])
            if not g:
                continue
            t = g["context_tier"]
            acc[t][0] += 1
            acc[t][1] += 1 if d.get("judge_correct") else 0
        cells = []
        for t in TIERS:
            n, h = acc[t]
            cells.append(f"{100*h/n:3.0f}% ({h}/{n})" if n else "    reject   ")
        print(f"{name:14}" + "".join(f"{c:>14}" for c in cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
