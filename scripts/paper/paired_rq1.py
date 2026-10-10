#!/usr/bin/env python3
"""Paired RQ1 table: all four regimes scored on the SAME items (the full-context sample).

Re-aggregates existing LLM-judge verdict files only (no model calls). Scoring rule follows the
dataset repo's scripts/score_judge.py: a verdict line counts as correct iff `judge_correct` is truthy;
items are joined to data/qa_v0.6_test_public.jsonl for split / tier / cluster_weight; Wilson 95% CI
with z = 1.96 (same formula). Plain accuracy is the headline; cluster-weighted is reported alongside.

Item sets:
  * fc105 — the 105 test_public items that the full-window models (gpt-4.1-mini, gpt-5.5, minimax-m3,
    glm-5.2) answered under full-context (27/19/12/22/25 at 32k/64k/128k/256k/512k).
  * fc78  — the 78-item subset that fits a 256k/272k window (gpt-5.4-mini, gpt-5.4-nano, qwen3.5):
    fc105 minus the 25 512k items and the 2 nominal-256k bundles that exceed 262,144 tokens.
For every model the cb / bm25 / dense verdict files cover all 389 (386) test_public items, so each
regime is simply restricted to that model's own fc item set.

Usage (from the dataset repo root):
    python3 scripts/paper/paired_rq1.py [--md] [--verdicts-dir results/judge_verdicts]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verdict_paths import verdict_file  # noqa: E402

# (display name, cb tag, bm25 tag, dense tag, fc tag) — tags are the same ones score_judge.py reads.
RUNS = [
    ("gpt-4.1-mini", "gpt-4.1-mini_cb", "gpt-4.1-mini_rag", "jf386_gpt-4.1-mini_dense", "gpt-4.1-mini_fc"),
    ("gpt-5.4-mini", "gpt-5.4-mini_cb", "gpt-5.4-mini_rag", "jf386_gpt-5.4-mini_dense", "gpt-5.4-mini_fc"),
    ("gpt-5.4-nano", "gpt-5.4-nano_cb", "gpt-5.4-nano_rag", "jf386_gpt-5.4-nano_dense", "gpt-5.4-nano_fc"),
    ("gpt-5.5", "gpt-5.5_cb", "gpt-5.5_rag", "jf386_gpt-5.5_dense", "g55fc"),
    ("minimax-m3", "cb_minimax-m3-cloud_tp", "rag_minimax-m3-cloud_tp", "jf386_minimax-m3_dense", "fc_minimax-m3-cloud_tp"),
    ("glm-5.2", "cb_glm-5.2-cloud_tp", "rag_glm-5.2-cloud_tp", "jf386_glm-5.2_dense", "fc_glm-5.2-cloud_tp"),
    ("qwen3.5", "cb_qwen3.5-cloud_tp", "rag_qwen3.5-cloud_tp", "jf386_qwen3.5_dense", "fc_qwen3.5-cloud_tp"),
]
REGIMES = ("cb", "bm25", "dense", "fc")


def wilson(c: float, n: float) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    z = 1.96
    p = c / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def load_verdicts(path: Path, gold: dict) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for line in path.open(encoding="utf-8"):
        if not line.strip():
            continue
        d = json.loads(line)
        if d["qa_id"] in gold:
            out[d["qa_id"]] = bool(d.get("judge_correct"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(Path(__file__).resolve().parents[2]),
                    help="dataset repo root (default: this checkout)")
    ap.add_argument("--verdicts-dir", default=None,
                    help="read <tag>.jsonl verdicts from this directory only "
                         "(default: workspace_local/audit/baselines if present, else results/judge_verdicts)")
    ap.add_argument("--md", action="store_true", help="print a markdown table instead of plain text")
    args = ap.parse_args()
    root = Path(args.dataset)

    gold = {}
    for line in (root / "data" / "qa_v0.6_test_public.jsonl").open(encoding="utf-8"):
        if line.strip():
            d = json.loads(line)
            gold[d["qa_id"]] = d

    rows = []
    for name, *tags in RUNS:
        v = {r: load_verdicts(verdict_file(t, args.verdicts_dir), gold) for r, t in zip(REGIMES, tags)}
        items = sorted(v["fc"])
        missing = {r: [q for q in items if q not in v[r]] for r in REGIMES}
        assert not any(missing.values()), (name, missing)
        tiers = Counter(gold[q]["context_tier"] for q in items)
        cells = {}
        for r in REGIMES:
            n = len(items)
            hits = sum(v[r][q] for q in items)
            w = sum(float(gold[q].get("cluster_weight", 1.0)) for q in items)
            whits = sum(float(gold[q].get("cluster_weight", 1.0)) for q in items if v[r][q])
            lo, hi = wilson(hits, n)
            cells[r] = (hits, n, hits / n, lo, hi, whits / w if w else 0.0)
        rows.append((name, tiers, cells, dict(zip(REGIMES, tags))))

    if args.md:
        print("| Model | n | closed-book | BM25 RAG | dense RAG | full-context |")
        print("|---|---:|---:|---:|---:|---:|")
        for name, tiers, cells, _ in rows:
            n = cells["fc"][1]
            cell = lambda r: f"{cells[r][2]:.0%} [{cells[r][3]:.0%}, {cells[r][4]:.0%}] ({cells[r][0]}/{n}; cw {cells[r][5]:.0%})"
            print(f"| {name} | {n} | " + " | ".join(cell(r) for r in REGIMES) + " |")
        print()
        print("Run files (`results/judge_verdicts/<tag>.jsonl`):")
        for name, tiers, _, tags in rows:
            print(f"- {name}: " + ", ".join(f"{r}={t}" for r, t in tags.items())
                  + f"; fc tiers {dict(sorted(tiers.items()))}")
    else:
        for name, tiers, cells, tags in rows:
            print(f"{name:14} n={cells['fc'][1]:3} tiers={dict(sorted(tiers.items()))}")
            for r in REGIMES:
                h, n, p, lo, hi, cw = cells[r]
                print(f"   {r:6} {h:3}/{n:<3} {p:6.1%}  [{lo:.1%}, {hi:.1%}]  cw {cw:.1%}   <- {tags[r]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
