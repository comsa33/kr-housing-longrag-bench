#!/usr/bin/env python3
"""Build INTERNAL dense-RAG (bge-m3) prompt records for the v0.9 baseline.

Dense counterpart of build_baseline_rag.py. Everything is identical EXCEPT the
retriever: instead of pure-python Okapi BM25, it retrieves with bge-m3 (a strong
multilingual/Korean dense encoder) served by a local Ollama daemon (/api/embed).
Same page-aware ≤1200-char chunking, same top-k, same rag_prompt template → the
ONLY variable is sparse-vs-dense retrieval, so dense-RAG vs BM25-RAG is a clean
apples-to-apples comparison (B3: refute the "BM25-only RAG" critique).

The BM25 path (build_baseline_rag.py) is untouched; this writes to a SEPARATE
`rag_dense_*` output and never overwrites the BM25 prompts or any judged file.

To pair EXACTLY with the BM25 run, feed the same locked sample: pass a sample
JSONL whose records carry qa_id / split / bundle_id (e.g. one derived from the
BM25 prompt files). Retrieval is deterministic given the model + normalized
embeddings.

Safety: retrieved passages are raw bundle text → output ONLY under
workspace_local/ (refuses any --out outside it). No paid API (bge-m3 runs on the
local Ollama daemon; `ollama pull bge-m3` once, then `ollama serve`).

Usage (plain python3 — only urllib + numpy; no torch/sentence-transformers):
    python3 scripts/build_baseline_rag_dense.py \\
        --sample workspace_local/audit/baselines/baseline_sample_dense_tp389.jsonl \\
        --out workspace_local/audit/baselines/rag_dense_v09_prompts.jsonl
    # then per model (identical to BM25, just a different --prompt-file):
    python3 scripts/run_llm_baseline.py --provider openai --model gpt-4.1-mini \\
        --split test_public --prompt-file workspace_local/audit/baselines/rag_dense_v09_prompts.jsonl \\
        --out workspace_local/audit/baselines/rag_dense_gpt-4.1-mini_test_public.jsonl --resume
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

# Reuse the shared retrieval stack (OllamaBGEIndex + dense_bge dispatch live here).
from build_rag_smoke import split_chunks, retrieve, rag_prompt, OLLAMA_EMBED_MODEL, DENSE_BGE_LABEL  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "workspace_local" / "audit" / "baselines" / "baseline_sample_v09.jsonl"
SPLIT_FILES = {
    "dev": ROOT / "data" / "qa_v0.6_dev.jsonl",
    "test_public": ROOT / "data" / "qa_v0.6_test_public.jsonl",
}
BUNDLES = ROOT / "workspace_local" / "processed" / "bundles-v06"
DEFAULT_OUT = ROOT / "workspace_local" / "audit" / "baselines" / "rag_dense_v09_prompts.jsonl"


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
    ap.add_argument("--sample", default=None, help="sample JSONL (default: the locked sample); pass a "
                    "test_public-only list to pair exactly with the BM25 test_public RAG run")
    args = ap.parse_args()

    out = Path(args.out).resolve() if args.out else DEFAULT_OUT
    if not out.is_relative_to((ROOT / "workspace_local").resolve()):
        raise SystemExit(f"--out must be under workspace_local/ (embeds bundle text). Got: {out}")
    sample_path = (Path(args.sample) if args.sample else SAMPLE)
    if not sample_path.is_absolute():
        sample_path = ROOT / sample_path
    if not sample_path.exists():
        raise SystemExit(f"missing sample {sample_path} — run scripts/build_baseline_sample.py first")

    sample = load_jsonl(sample_path)
    # qa_id -> full QA record (need question + gold page_ids + instruction).
    qa_by_id: dict[str, dict] = {}
    for f in SPLIT_FILES.values():
        for r in load_jsonl(f):
            qa_by_id[r["qa_id"]] = r

    chunks_cache: dict = {}
    bm25_cache: dict = {}     # unused for dense_bge, kept for the shared retrieve() signature
    dense_cache: dict = {}    # bid -> BGEDenseIndex (encoded once per bundle)
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
        picked = retrieve("dense_bge", rec, chunks, args.k, bid, bm25_cache, dense_cache, args.per_page_max)
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
            "retriever": "dense_bge",
            "embedder": OLLAMA_EMBED_MODEL,
            "embed_backend": DENSE_BGE_LABEL,
            "k": args.k,
            "per_page_max": args.per_page_max,
            "n_passages": len(picked),
            "retrieved_page_ids": retrieved_pages,
            "gold_page_ids": gold_pages,
            "context_tier": s.get("context_tier"),
            "bundle_id": bid,
            "answer_type": s.get("answer_type"),
            "regime": "rag_dense",
        })

    if not written:
        out.unlink(missing_ok=True)
        raise SystemExit(
            f"no dense-RAG prompts written — internal bundle text under {BUNDLES.relative_to(ROOT)} is absent. "
            "Rebuild bundles locally; RAG needs the internal corpus."
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in written:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_split = collections.Counter(r["split"] for r in written)
    mean_recall = sum(recalls) / len(recalls) if recalls else 0.0
    print(f"[ok] wrote {out} ({len(written)} RAG-dense[{DENSE_BGE_LABEL}] prompts; no_bundle skipped {no_bundle}, "
          f"no_passage {no_passage})")
    print(f"     by split: {dict(by_split)}  | k={args.k} per_page_max={args.per_page_max}")
    print(f"     gold-page recall@{args.k} (sanity, items with gold pages={len(recalls)}): {mean_recall:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
