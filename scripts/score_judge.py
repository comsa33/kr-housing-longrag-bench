#!/usr/bin/env python3
"""Aggregate the LLM-judge verdicts (`<tag>.judged.jsonl`) into per-split tables.

The §8 headline judge numbers were first computed POOLING dev+test_public (a development-set
red flag for a paper). This scorer cuts the SAME verdicts by split so test_public (the held-out
eval) can headline on its own, with a Wilson 95% CI (it is small, n≈104). full-context is also
broken down by context_tier within each split.

Judge verdict files carry only {qa_id, judge_correct}; split / task_type / context_tier /
cluster_weight are joined from the gold split files (public splits only — hidden never here).

    python3 scripts/score_judge.py                 # all models, by split (+ fc tier)
    python3 scripts/score_judge.py --splits test_public
    python3 scripts/score_judge.py --verdicts-dir results/judge_verdicts   # released copy only
    python3 scripts/score_judge.py --exclude-family cross_document_legal_reasoning   # v0.9.1 scope
    python3 scripts/score_judge.py --exclude-family cross_document_legal_reasoning \
        --exclude-ids data/v0.9.2/eval_exclusions.txt \
        --verdicts-dir results/judge_verdicts_v0.9.2/claude-sonnet-5-5             # v0.9.2 scope
    # v0.9.3 scope: --exclude-ids data/v0.9.3/eval_exclusions.txt (5 test + 7 dev, all settings) and
    # --exclude-bundle-ids data/v0.9.3/bundle_exclusions.txt (122 dev items whose gold page is not in their
    # 512k bundle; dropped from rag/dense/fc only)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verdict_paths import verdict_file  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MODELS = ["gpt-4.1-mini", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.5"]
# Open-weight models (EACL leg): test_public only, judged tags = "{regime}_{label}_tp".
# These rows contribute to test_public and ALL only (no dev run), so dev shows "—".
# qwen3.5 is added once its judged files land (fc ≤256K only — no 512k tier).
OPEN = [("minimax-m3", "minimax-m3-cloud"), ("glm-5.2", "glm-5.2-cloud"), ("qwen3.5", "qwen3.5-cloud")]
MODELS += [disp for disp, _ in OPEN]
# (tag, model, regime); gpt-5.5 fc verdicts live under the "g55fc" tag
TAGS = ([("g55fc", "gpt-5.5", "fc")]
        + [(f"{m}_{r}", m, r) for m in ("gpt-4.1-mini", "gpt-5.4-mini", "gpt-5.4-nano")
           for r in ("cb", "rag", "fc")]
        + [("gpt-5.5_cb", "gpt-5.5", "cb"), ("gpt-5.5_rag", "gpt-5.5", "rag")]
        + [(f"{r}_{label}_tp", disp, r) for disp, label in OPEN
           for r in ("cb", "rag", "fc")]
        # dense (bge-m3) RAG, test_public only, chunker-fixed re-run of 2026-07-13
        + [(f"jf386_{m}_dense", m, "dense") for m in
           ("gpt-4.1-mini", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.5", "minimax-m3", "glm-5.2", "qwen3.5")])
TIERS = ["32k", "64k", "128k", "256k", "512k"]


def read_id_file(path: str | None) -> set[str]:
    """qa_ids listed one per line in `path` ('#' starts a comment); empty set when path is None."""
    if not path:
        return set()
    ids = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            ids.add(line)
    return ids


def wilson(c: float, n: float) -> tuple[float, float]:
    """Wilson 95% CI for a (possibly cluster-weighted) proportion; n = effective count."""
    if n <= 0:
        return (0.0, 0.0)
    z = 1.96
    p = c / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", default="ALL,dev,test_public",
                    help="comma list; ALL = dev+test_public pooled")
    ap.add_argument("--verdicts-dir", default=None,
                    help="read <tag>.jsonl verdicts from this directory only "
                         "(default: workspace_local/audit/baselines if present, else results/judge_verdicts)")
    ap.add_argument("--exclude-family", default="",
                    help="comma list of task_type values to drop, e.g. cross_document_legal_reasoning")
    ap.add_argument("--exclude-bundle", default="",
                    help="comma list of bundle_id values to drop, e.g. mix_multiprovider_256k")
    ap.add_argument("--exclude-ids", default=None, metavar="FILE",
                    help="file of qa_ids to drop (one per line, '#' comments), "
                         "e.g. data/v0.9.2/eval_exclusions.txt; default: none")
    ap.add_argument("--exclude-bundle-ids", default=None, metavar="FILE",
                    help="file of qa_ids to drop from the bundle-based regimes only (rag, dense, fc), "
                         "e.g. data/v0.9.3/bundle_exclusions.txt; closed-book keeps them")
    args = ap.parse_args()
    want = [s.strip() for s in args.splits.split(",") if s.strip()]

    xf = {s for s in args.exclude_family.split(",") if s}
    xb = {s for s in args.exclude_bundle.split(",") if s}
    xi = read_id_file(args.exclude_ids)
    xbi = read_id_file(args.exclude_bundle_ids)
    gi: dict[str, dict] = {}
    for sp in ("dev", "test_public"):
        f = ROOT / "data" / f"qa_v0.6_{sp}.jsonl"
        if f.exists():
            for line in f.open(encoding="utf-8"):
                d = json.loads(line)
                if d.get("task_type") in xf or d.get("bundle_id") in xb or d["qa_id"] in xi:
                    continue
                gi[d["qa_id"]] = d

    # acc[(model, regime, split)] = [n, w_n, hits, w_hits]
    acc: dict = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    # tier_acc[(model, split, tier)] = [n, hits]  (fc only, plain)
    tier_acc: dict = defaultdict(lambda: [0, 0])

    for tag, model, regime in TAGS:
        jf = verdict_file(tag, args.verdicts_dir)
        if not jf.exists():
            continue
        for line in jf.open(encoding="utf-8"):
            d = json.loads(line)
            g = gi.get(d["qa_id"])
            if not g or (regime != "cb" and d["qa_id"] in xbi):
                continue
            ok = 1.0 if d.get("judge_correct") else 0.0
            cw = float(g.get("cluster_weight", 1.0))
            sp = g.get("split", "?")
            for bucket in ("ALL", sp):
                a = acc[(model, regime, bucket)]
                a[0] += 1; a[1] += cw; a[2] += ok; a[3] += cw * ok
            if regime == "fc":
                t = g.get("context_tier")
                for bucket in ("ALL", sp):
                    tier_acc[(model, bucket, t)][0] += 1
                    tier_acc[(model, bucket, t)][1] += int(ok)

    for split in want:
        print(f"\n===== JUDGE accuracy — split = {split} =====")
        print(f"{'model':16} | {'cb plain/cw (95% CI cw)':28} | {'bm25 plain/cw':18} | {'dense plain/cw':18} | {'fc plain/cw':18}")
        for model in MODELS:
            row = f"{model:16} |"
            for regime in ("cb", "rag", "dense", "fc"):
                a = acc.get((model, regime, split))
                if not a or a[0] == 0:
                    row += f" {'—':27}|" if regime == "cb" else f" {'—':17}|"
                    continue
                plain = a[2] / a[0]
                cw = a[3] / a[1] if a[1] else 0.0
                if regime == "cb":
                    lo, hi = wilson(a[3], a[1])
                    row += f" {plain:4.0%}/{cw:4.0%} [{lo:.0%}-{hi:.0%}] n{int(a[0]):<5}|"
                else:
                    row += f" {plain:4.0%}/{cw:4.0%} n{int(a[0]):<5}|"
            print(row)
        # fc tier breakdown
        print(f"  -- fc by tier (plain) -- {'':4}" + " ".join(f"{t:>8}" for t in TIERS))
        for model in MODELS:
            cells = []
            for t in TIERS:
                v = tier_acc.get((model, split, t))
                cells.append(f"{v[1]/v[0]:4.0%}n{v[0]:<3}" if v and v[0] else "   ✗ctx")
            print(f"  {model:16} " + " ".join(f"{c:>8}" for c in cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
