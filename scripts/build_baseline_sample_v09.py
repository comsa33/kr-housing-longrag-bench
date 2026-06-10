#!/usr/bin/env python3
"""v0.9 release-grade baseline evaluation sample (stratified, reproducible).

Draws the fixed QA slice the v0.9 baseline result tables are computed on:

  * test_public : ALL items (small held split, 104) — taken whole, no sampling.
  * dev         : stratified by task_type (all 12 families represented via a
                  per-family floor), near-duplicate-deduplicated by cluster_id
                  (at most --per-cluster items per cluster), seeded RNG.

This is a *release-grade* sample, NOT the v0.7 "same-22" convenience slice: it
covers every task family and reports the style / context-tier / provider spread
so the resulting numbers are representative rather than cherry-picked.

The drawn sample (qa_id list + manifest with seed/counts) is written INTERNAL
under workspace_local/audit/baselines/ (gitignored). The reproducible artifact
that ships is THIS script + its seed, not the drawn file.

Usage:
    python3 scripts/build_baseline_sample_v09.py                 # default target 200, seed pinned
    python3 scripts/build_baseline_sample_v09.py --dev-target 200 --per-cluster 1 --seed 20260610
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "data" / "qa_v0.6_dev.jsonl"
TEST_PUBLIC = ROOT / "data" / "qa_v0.6_test_public.jsonl"
OUT_DIR = ROOT / "workspace_local" / "audit" / "baselines"
BUNDLES = ROOT / "workspace_local" / "processed" / "bundles-v06"

# Fields carried into the sample manifest (no answers / gold predicates — those
# stay in the split files; the sample is a locator list, not a gold dump).
CARRY = ["qa_id", "split", "task_type", "question_style", "context_tier",
         "cluster_id", "provider", "region_sido", "answer_type", "bundle_id"]

# Measured empirically on mix_multiprovider_512k.txt: 974,007 chars -> 393,315
# prompt_tokens via the OpenAI tokenizer (gpt-4.1-mini, 2026-06-10). Korean-heavy
# mixed text. Use a slightly conservative ratio (more tokens) for cost planning.
CHARS_PER_TOKEN = 2.45
# gpt-4.1-mini list price (USD per 1M tokens), to confirm against live billing.
PRICE_IN_PER_M = 0.40
PRICE_OUT_PER_M = 1.60
RAG_CTX_TOKENS = 8000      # approx retrieved-context size per RAG item
OUT_TOKENS = 64            # short final-answer cap

# Full-context regime is the expensive one; cap the giant tiers so the run lands
# near the ~$9 budget while still covering every tier. Smaller tiers uncapped.
DEFAULT_FC_CAPS = {"512k": 18, "256k": 22}


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def slim(row: dict) -> dict:
    return {k: row.get(k) for k in CARRY}


def draw_dev(rows: list[dict], target: int, per_cluster: int, seed: int) -> list[dict]:
    """Stratify dev by task_type with a per-family floor, dedup by cluster_id."""
    rng = random.Random(seed)
    by_family: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_family[r["task_type"]].append(r)
    families = sorted(by_family)
    n_fam = len(families)

    # Per-family quota: proportional to family size, but with a floor so every
    # family is represented (capped at what the family can supply post-dedup).
    floor = max(4, target // (n_fam * 2))
    total = len(rows)
    quotas: dict[str, int] = {}
    for fam in families:
        prop = round(target * len(by_family[fam]) / total)
        quotas[fam] = max(floor, prop)

    picked: list[dict] = []
    for fam in families:
        pool = by_family[fam]
        rng.shuffle(pool)
        # Prefer one (or --per-cluster) item per distinct cluster first.
        seen_cluster: Counter = Counter()
        ordered_primary, ordered_overflow = [], []
        for r in pool:
            cid = r.get("cluster_id")
            if seen_cluster[cid] < per_cluster:
                seen_cluster[cid] += 1
                ordered_primary.append(r)
            else:
                ordered_overflow.append(r)
        ordered = ordered_primary + ordered_overflow  # dedup-preferred, then fill
        picked.extend(ordered[: quotas[fam]])

    # If rounding/floors overshoot the target, trim the largest families first
    # (keep at least `floor` each); if undershoot, leave as-is (coverage > exact N).
    rng.shuffle(picked)
    if len(picked) > target:
        # trim from over-represented families
        by_fam_pick: dict[str, list[dict]] = defaultdict(list)
        for r in picked:
            by_fam_pick[r["task_type"]].append(r)
        while sum(len(v) for v in by_fam_pick.values()) > target:
            biggest = max(by_fam_pick, key=lambda f: len(by_fam_pick[f]))
            if len(by_fam_pick[biggest]) <= floor:
                break
            by_fam_pick[biggest].pop()
        picked = [r for v in by_fam_pick.values() for r in v]
    return picked


def dist(rows: list[dict], key: str) -> dict:
    return dict(Counter(r.get(key) for r in rows).most_common())


def bundle_tokens(row: dict) -> int | None:
    """Approx prompt tokens for a full-context run of this item (bundle chars / ratio).

    Returns None when the item has no bundle or the bundle text is absent on disk
    (a clean checkout without the internal corpus) — those can't run full-context.
    """
    bid = row.get("bundle_id")
    if not bid:
        return None
    f = BUNDLES / f"{bid}.txt"
    if not f.exists():
        return None
    return int(f.stat().st_size / CHARS_PER_TOKEN)


def build_fc_subset(sample: list[dict], caps: dict[str, int], seed: int) -> list[dict]:
    """Full-context-eligible subset: drop bundle-less items, cap the giant tiers."""
    rng = random.Random(seed + 1)
    eligible = [r for r in sample if bundle_tokens(r) is not None]
    by_tier: dict[str, list[dict]] = defaultdict(list)
    for r in eligible:
        by_tier[r.get("context_tier")].append(r)
    out: list[dict] = []
    for tier, rows in by_tier.items():
        cap = caps.get(tier)
        if cap is not None and len(rows) > cap:
            rng.shuffle(rows)
            rows = rows[:cap]
        out.extend(rows)
    return out


def project_cost(sample: list[dict], fc_subset: list[dict]) -> dict:
    fc_in = sum(bundle_tokens(r) or 0 for r in fc_subset)
    fc_out = OUT_TOKENS * len(fc_subset)
    rag_in = RAG_CTX_TOKENS * len(sample)
    rag_out = OUT_TOKENS * len(sample)
    fc_usd = fc_in / 1e6 * PRICE_IN_PER_M + fc_out / 1e6 * PRICE_OUT_PER_M
    rag_usd = rag_in / 1e6 * PRICE_IN_PER_M + rag_out / 1e6 * PRICE_OUT_PER_M
    return {
        "model": "gpt-4.1-mini",
        "price_in_per_M": PRICE_IN_PER_M, "price_out_per_M": PRICE_OUT_PER_M,
        "chars_per_token": CHARS_PER_TOKEN,
        "full_context": {"items": len(fc_subset), "input_tokens": fc_in,
                         "by_tier": dist(fc_subset, "context_tier"),
                         "est_usd": round(fc_usd, 2)},
        "rag_bm25": {"items": len(sample), "input_tokens": rag_in, "est_usd": round(rag_usd, 2)},
        "total_est_usd": round(fc_usd + rag_usd, 2),
        "note": "closed-book regime is ~free (locator-only, tiny prompts); gemma4:12b local leg is $0.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-target", type=int, default=200)
    ap.add_argument("--per-cluster", type=int, default=1)
    ap.add_argument("--seed", type=int, default=20260610)
    ap.add_argument("--fc-cap-512k", type=int, default=DEFAULT_FC_CAPS["512k"])
    ap.add_argument("--fc-cap-256k", type=int, default=DEFAULT_FC_CAPS["256k"])
    args = ap.parse_args()

    dev_rows = load(DEV)
    tp_rows = load(TEST_PUBLIC)

    dev_pick = draw_dev(dev_rows, args.dev_target, args.per_cluster, args.seed)
    sample = [slim(r) for r in tp_rows] + [slim(r) for r in dev_pick]

    caps = {"512k": args.fc_cap_512k, "256k": args.fc_cap_256k}
    fc_subset = build_fc_subset(sample, caps, args.seed)
    projection = project_cost(sample, fc_subset)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_jsonl = OUT_DIR / "baseline_sample_v09.jsonl"          # all 304 (RAG + closed-book)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in sample:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    out_fc = OUT_DIR / "baseline_sample_v09.fc.jsonl"          # full-context-eligible subset
    with out_fc.open("w", encoding="utf-8") as f:
        for r in fc_subset:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "seed": args.seed,
        "dev_target": args.dev_target,
        "per_cluster": args.per_cluster,
        "fc_caps": caps,
        "counts": {
            "total": len(sample),
            "test_public": len(tp_rows),
            "dev": len(dev_pick),
            "dev_distinct_clusters": len({r.get("cluster_id") for r in dev_pick}),
            "full_context_eligible": len(fc_subset),
            "no_bundle_on_disk": sum(1 for r in sample if bundle_tokens(r) is None),
        },
        "dev_by_task_type": dist(dev_pick, "task_type"),
        "dev_by_question_style": dist(dev_pick, "question_style"),
        "dev_by_context_tier": dist(dev_pick, "context_tier"),
        "sample_by_context_tier": dist(sample, "context_tier"),
        "dev_by_provider": dist(dev_pick, "provider"),
        "cost_projection": projection,
    }
    out_manifest = OUT_DIR / "baseline_sample_v09.manifest.json"
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] wrote {out_jsonl} ({len(sample)} items)")
    print(f"[ok] wrote {out_fc} ({len(fc_subset)} full-context-eligible items)")
    print(f"[ok] wrote {out_manifest}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
