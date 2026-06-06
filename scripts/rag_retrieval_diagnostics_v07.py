#!/usr/bin/env python3
"""Retrieval diagnostics for the v0.7 RAG smoke (no model/API calls).

For the same 22-item slice as the RAG smoke, measure BM25 retrieval QUALITY (not answer accuracy):
  - gold-page hit@k / recall@k: does the BM25 top-k include a chunk from the QA's gold page?
  - gold-page rank: where the best gold-page chunk lands in the BM25 ranking.
  - retrieved token length at each k (context cost of RAG).
  - failure cases: items whose gold page is NOT in top-k.
  - (optional) cross-reference with internal BM25 prediction files to split answer errors into
    "retrieval miss" vs "read miss".

Reads internal bundle text + (optionally) internal prediction files under workspace_local/, but EMITS
only aggregate stats + qa_ids (no bundle text), so the output is public-safe. Reuses the smoke's
chunker/BM25 (scripts/build_rag_smoke_v07.py) and the harness scorer (scripts/eval_harness_v06.py).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_rag_smoke_v07 as rb  # noqa: E402  (chunker + BM25)
import eval_harness_v06 as eh      # noqa: E402  (canonical scorer)

QA = ROOT / "data" / "qa_v0.6_realistic_candidates.jsonl"
BUNDLES = ROOT / "workspace_local" / "processed" / "bundles-v06"
BASELINES = ROOT / "workspace_local" / "audit" / "baselines"

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("o200k_base")
    def toklen(s: str) -> int:
        return len(_ENC.encode(s))
except Exception:  # pragma: no cover - tiktoken optional
    def toklen(s: str) -> int:
        return len(s) // 2


def select(split: str, tiers: set, max_items: int) -> list:
    with QA.open(encoding="utf-8") as f:
        rows = [json.loads(l) for l in f if l.strip()]
    pool = [r for r in rows
            if r.get("split") == split and r.get("bundle_id") and r.get("context_tier") in tiers]
    pool.sort(key=lambda r: r["qa_id"])
    return pool[:max_items]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test_public")
    ap.add_argument("--tiers", default="32k,64k")
    ap.add_argument("--max-items", type=int, default=40)
    ap.add_argument("--chunk-chars", type=int, default=1200)
    ap.add_argument("--retriever", choices=["bm25", "dense", "hybrid"], default="bm25",
                    help="ranking method for hit@k; dense/hybrid need OPENAI_API_KEY and the optional "
                         "baseline deps (uv sync --extra baseline)")
    ap.add_argument("--ks", default="1,3,5,10")
    ap.add_argument("--per-page-max", type=int, default=0,
                    help="cap chunks per page in the ranking (page-diverse retrieval); 0 = off")
    ap.add_argument("--cross-ref", default="gpt-4o-mini,gpt-5.4",
                    help="internal prediction model ids to split errors into retrieval-miss vs read-miss")
    args = ap.parse_args()

    ks = [int(x) for x in args.ks.split(",") if x.strip()]
    tiers = {t.strip() for t in args.tiers.split(",") if t.strip()}
    pool = select(args.split, tiers, args.max_items)
    if not pool:
        print("no QA matched the selection")
        return 1
    if not BUNDLES.exists() or not any(BUNDLES.glob("*.txt")):
        print(f"internal bundle text under {BUNDLES.relative_to(ROOT)} is absent — rebuild bundles locally")
        return 1

    chunks_cache: dict = {}
    bm25_cache: dict = {}
    dense_cache: dict = {}
    rows = []  # per-item diagnostics
    for r in pool:
        bid = r["bundle_id"]
        if bid not in chunks_cache:
            bf = BUNDLES / f"{bid}.txt"
            chunks_cache[bid] = rb.split_chunks(bf.read_text(encoding="utf-8"), args.chunk_chars) if bf.exists() else []
        chunks = chunks_cache[bid]
        if not chunks:
            print(f"  WARN: no bundle pages for {bid}; skipping {r['qa_id']}")
            continue
        # full ranking for the retriever (indexes built lazily/cached in rb.rank_chunks), then page-diverse
        full = rb.rank_chunks(args.retriever, r, chunks, bid, bm25_cache, dense_cache)
        ranking = rb.diversify(full, [pid for pid, _ in chunks], args.per_page_max)
        gold_pages = set(r.get("page_ids") or [])
        gold_rank = None
        for rank, idx in enumerate(ranking, 1):
            if chunks[idx][0] in gold_pages:
                gold_rank = rank
                break
        toks_at = {k: sum(toklen(chunks[i][1]) for i in ranking[:k]) for k in ks}
        top5_pages = [chunks[i][0] for i in ranking[:5]]
        rows.append({"qa_id": r["qa_id"], "bundle": bid, "n_chunks": len(chunks),
                     "gold_rank": gold_rank, "toks_at": toks_at,
                     "dup5": len(top5_pages) - len(set(top5_pages))})

    if not rows:
        print("no items had bundle text; nothing to diagnose")
        return 1
    n = len(rows)
    pp = f", per_page_max={args.per_page_max}" if args.per_page_max else ""
    print(f"== RAG retrieval diagnostics [{args.retriever}{pp}] ({args.split}, tiers={sorted(tiers)}, "
          f"{n} items, chunk_chars={args.chunk_chars}) ==")
    print(f"avg chunks/bundle: {sum(x['n_chunks'] for x in rows) / n:.1f}; "
          f"gold-page found in bundle: {sum(1 for x in rows if x['gold_rank'])}/{n}; "
          f"avg same-page duplicate chunks in top-5: {sum(x['dup5'] for x in rows) / n:.2f}")
    print("\nk   hit@k(gold page in top-k)   avg retrieved tokens")
    for k in ks:
        hit = sum(1 for x in rows if x["gold_rank"] and x["gold_rank"] <= k)
        avg_tok = sum(x["toks_at"][k] for x in rows) / n
        print(f"{k:<3} {hit:>2}/{n} = {hit / n:6.1%}            {avg_tok:8.0f}")

    ranks = [x["gold_rank"] for x in rows if x["gold_rank"]]
    if ranks:
        print(f"\ngold-page rank: min={min(ranks)} median={sorted(ranks)[len(ranks)//2]} max={max(ranks)}")

    miss = [x for x in rows if not (x["gold_rank"] and x["gold_rank"] <= 5)]
    print(f"\nfailure cases (gold page NOT in top-5): {len(miss)}")
    for x in miss:
        print(f"  {x['qa_id']}  gold_rank={x['gold_rank']}")

    # cross-reference retrieval hit@5 with answer correctness from internal BM25 predictions
    models = [m.strip() for m in args.cross_ref.split(",") if m.strip()]
    # Cross-ref must use the SELECTED split's gold + prediction files (not a hardcoded test_public),
    # otherwise a non-default --split scores against the wrong files and reports misleading all-zeros.
    gold_path = ROOT / "data" / f"qa_v0.6_{args.split}.jsonl"
    gold = {}
    if gold_path.is_file():
        with gold_path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    it = json.loads(line)
                    gold[it["qa_id"]] = it
    by_id = {x["qa_id"]: x for x in rows}
    for m in models:
        pf = BASELINES / f"rag_{args.retriever}_openai_{m}_{args.split}.jsonl"
        if not gold:
            print(f"\n[cross-ref {m}] gold answers for split={args.split} unavailable ({gold_path.name}); skipped")
            continue
        if not pf.is_file():
            print(f"\n[cross-ref {m}] prediction file absent ({pf.relative_to(ROOT)}); skipped")
            continue
        preds = {}
        with pf.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    it = json.loads(line)
                    preds[it["qa_id"]] = it["prediction"]
        cells = {"hit_correct": 0, "hit_wrong": 0, "miss_correct": 0, "miss_wrong": 0}
        for qid, d in by_id.items():
            if qid not in preds or qid not in gold:
                continue
            hit = bool(d["gold_rank"] and d["gold_rank"] <= 5)
            ok = eh.score(gold[qid], preds[qid])
            cells[f"{'hit' if hit else 'miss'}_{'correct' if ok else 'wrong'}"] += 1
        print(f"\n[cross-ref {m}] retrieval hit@5 vs answer correctness:")
        print(f"  retrieved gold (hit@5):  correct {cells['hit_correct']}  wrong {cells['hit_wrong']}")
        print(f"  missed gold  (miss@5):   correct {cells['miss_correct']}  wrong {cells['miss_wrong']}")
        misses = cells["miss_correct"] + cells["miss_wrong"]
        print(f"  -> answer errors: read failures (gold retrieved but wrong) {cells['hit_wrong']}; "
              f"gold-page misses@5 {misses} (of which wrong {cells['miss_wrong']}, "
              f"still-correct {cells['miss_correct']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
