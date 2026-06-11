#!/usr/bin/env python3
"""Build INTERNAL RAG (BM25) prompt records for the v0.9 baseline.

Reads the LOCKED sample (baseline_sample_v09.jsonl), joins each item to its split
file for the question + gold page_ids, runs pure-python Okapi BM25 over the item's
bundle pages, embeds the top-k retrieved passages into a runner-ready `prompt`, and
records the retrieved vs gold page_ids so the scorer can compute retrieval recall@k.

Reuses the dep-free retrieval stack from build_rag_smoke_v07.py (BM25, page-aware
chunking, rag_prompt). RAG covers the sample items that HAVE a bundle on disk
(retrieval needs a corpus); bundle-less items — e.g. answerability_detection with no
haystack — are reported and skipped (they still run in the closed-book regime).

Safety: retrieved passages are raw bundle text → output ONLY under workspace_local/
(refuses any --out outside it). Deterministic. No API calls (BM25 is local).

Usage:
    python3 scripts/build_baseline_rag_v09.py            # k=5, chunk 1200 chars, BM25
    # then per split:
    python3 scripts/run_llm_baseline_v07.py --provider openai --model gpt-4.1-mini \\
        --split test_public --prompt-file workspace_local/audit/baselines/rag_bm25_v09_prompts.jsonl \\
        --out workspace_local/audit/baselines/rag_gpt-4.1-mini_test_public.jsonl --resume
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

# Reuse the dep-free retrieval stack (same scripts/ dir; build_rag_smoke_v07's main is guarded).
from build_rag_smoke_v07 import split_chunks, retrieve, rag_prompt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "workspace_local" / "audit" / "baselines" / "baseline_sample_v09.jsonl"
SPLIT_FILES = {
    "dev": ROOT / "data" / "qa_v0.6_dev.jsonl",
    "test_public": ROOT / "data" / "qa_v0.6_test_public.jsonl",
}
BUNDLES = ROOT / "workspace_local" / "processed" / "bundles-v06"
DEFAULT_OUT = ROOT / "workspace_local" / "audit" / "baselines" / "rag_bm25_v09_prompts.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def pages_of(passages: list) -> list[str]:
    """Unique page_ids among the retrieved passages, in reading order."""
    seen, out = set(), []
    for pid, _ in passages:
        if pid not in seen:
            seen.add(pid)
            out.append(pid)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5, help="top-k passages")
    ap.add_argument("--chunk-chars", type=int, default=1200, help="passage size for sub-page chunking")
    ap.add_argument("--per-page-max", type=int, default=0, help="cap chunks per page (page-diverse); 0=off")
    ap.add_argument("--out", default=None, help="output JSONL (must be under workspace_local/)")
    ap.add_argument("--sample", default=None, help="sample JSONL (default: the locked 304); pass a full "
                    "dev+test_public list to build RAG prompts over the full split")
    args = ap.parse_args()

    out = Path(args.out).resolve() if args.out else DEFAULT_OUT
    if not out.is_relative_to((ROOT / "workspace_local").resolve()):
        raise SystemExit(f"--out must be under workspace_local/ (embeds bundle text). Got: {out}")
    sample_path = (Path(args.sample) if args.sample else SAMPLE)
    if not sample_path.is_absolute():
        sample_path = ROOT / sample_path
    if not sample_path.exists():
        raise SystemExit(f"missing sample {sample_path} — run scripts/build_baseline_sample_v09.py first")

    sample = load_jsonl(sample_path)
    # qa_id -> full QA record (need question + gold page_ids + instruction).
    qa_by_id: dict[str, dict] = {}
    for f in SPLIT_FILES.values():
        for r in load_jsonl(f):
            qa_by_id[r["qa_id"]] = r

    chunks_cache: dict = {}
    bm25_cache: dict = {}
    written, no_bundle, no_passage, recalls = [], 0, 0, []
    for s in sample:
        qid, bid = s["qa_id"], s.get("bundle_id")
        rec = qa_by_id.get(qid)
        if not rec:
            continue
        bf = BUNDLES / f"{bid}.txt" if bid else None
        if not bid or not bf.exists():
            no_bundle += 1
            continue
        if bid not in chunks_cache:
            chunks_cache[bid] = split_chunks(bf.read_text(encoding="utf-8"), args.chunk_chars)
        chunks = chunks_cache[bid]
        if not chunks:
            no_passage += 1
            continue
        picked = retrieve("bm25", rec, chunks, args.k, bid, bm25_cache, {}, args.per_page_max)
        if not picked:
            no_passage += 1
            continue
        retrieved_pages = pages_of(picked)
        gold_pages = list(rec.get("page_ids") or [])
        if gold_pages:
            recall = len(set(retrieved_pages) & set(gold_pages)) / len(set(gold_pages))
            recalls.append(recall)
        written.append({
            "qa_id": qid,
            "split": s["split"],
            "prompt": rag_prompt(rec, picked),
            "retriever": "bm25",
            "k": args.k,
            "per_page_max": args.per_page_max,
            "n_passages": len(picked),
            "retrieved_page_ids": retrieved_pages,
            "gold_page_ids": gold_pages,
            "context_tier": s.get("context_tier"),
            "bundle_id": bid,
            "answer_type": s.get("answer_type"),
            "regime": "rag_bm25",
        })

    if not written:
        out.unlink(missing_ok=True)
        raise SystemExit(
            f"no RAG prompts written — internal bundle text under {BUNDLES.relative_to(ROOT)} is absent. "
            "Rebuild bundles locally; RAG needs the internal corpus."
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in written:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_split = collections.Counter(r["split"] for r in written)
    mean_recall = sum(recalls) / len(recalls) if recalls else 0.0
    print(f"[ok] wrote {out} ({len(written)} RAG-bm25 prompts; no_bundle skipped {no_bundle}, "
          f"no_passage {no_passage})")
    print(f"     by split: {dict(by_split)}  | k={args.k} per_page_max={args.per_page_max}")
    print(f"     gold-page recall@{args.k} (sanity, items with gold pages={len(recalls)}): {mean_recall:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
