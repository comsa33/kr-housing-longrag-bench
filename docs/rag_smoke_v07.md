# RAG (class B) Baseline Smoke (v0.7)

**Scope.** A small **smoke test** of a RAG (retrieval) pipeline, to put a "full-context vs RAG" data point
next to the full-context smoke (`docs/full_context_smoke_v07.md`) on the **same 22 `qa_id`s**. Smoke only —
not a benchmark, leaderboard, or model ranking. 22 items, one task family (`long_context_retrieval`), 3
bundles, 32k/64k tiers; numbers are illustrative, not generalizable.

Retrieved passages are raw bundle text, so RAG prompts and predictions are kept **INTERNAL** under
`workspace_local/audit/baselines/` (gitignored). Nothing here publishes bundle text.

## 1. Method

`scripts/build_rag_smoke_v07.py` (deterministic; same 22-item slice as the full-context smoke):

- The bundle is split into pages on its `[공고 … -pNNN (p.N)]` markers, then each page is windowed into
  ~1,200-char passages (sub-page chunking) that keep their `page_id`.
- **Retrievers** (`--retriever`):
  - `bm25` — pure-python Okapi BM25 (word tokens + Korean char bigrams; k1=1.5, b=0.75), top-`k` passages
    by the question (default k=5). No third-party deps.
  - `oracle` — the passages whose `page_id` matches the QA's **gold** `page_ids` ("oracle page": gold page
    only). This is a minimal-sufficient-context condition, **not** a guaranteed ceiling (a wider retriever
    can score higher by also pulling neighbouring context).
- The RAG prompt embeds only the retrieved passages (+ instruction + question), so context is ~9× smaller
  than full-context: avg ≈ **3.6k tokens (BM25)** / **3.3k (oracle)** vs **31.7k (full-context)**.

The runner consumes these via its `prompt` field (`select_prompt`), identical plumbing to the
full-context smoke; `--dry-run` redacts the embedded passages.

## 2. Commands

```bash
B=workspace_local/audit/baselines
python3 scripts/build_rag_smoke_v07.py --retriever bm25   --k 5            # -> rag_bm25_smoke_prompts.jsonl
python3 scripts/build_rag_smoke_v07.py --retriever oracle                  # -> rag_oracle_smoke_prompts.jsonl
export OPENAI_API_KEY=...
for R in bm25 oracle; do for M in gpt-4o-mini gpt-5.4; do
  uv run --extra baseline python scripts/run_llm_baseline_v07.py --provider openai --model $M \
    --split test_public --prompt-file $B/rag_${R}_smoke_prompts.jsonl \
    --out $B/rag_${R}_openai_${M}_test_public.jsonl --max-output-tokens 4000 --sleep-seconds 0.15
done; done
# score on the same 22 qa_ids (any 22-id source works as --ids-file; --pred-only also works per file):
python3 scripts/eval_harness_v06.py --pred $B/rag_bm25_openai_gpt-5.4_test_public.jsonl --pred-only --splits test_public
```

## 3. Results — same 22 qa_ids, 4 context regimes (2026-06-06, OpenAI; 22/22, 0 errors)

| Context regime | approx tokens | gpt-4o-mini | gpt-5.4 |
|---|---:|---:|---:|
| locator-only (no doc) | ~0.3k | 0/22 = 0.0% | 1/22 = 4.5% |
| **RAG (BM25 top-5)** | ~3.6k | **10/22 = 45.5%** | **18/22 = 81.8%** |
| oracle page (gold page only) | ~3.3k | 9/22 = 40.9% | 18/22 = 81.8% |
| full-context (whole bundle) | ~31.7k | 13/22 = 59.1% | 19/22 = 86.4% |

What it shows (on this slice):

- **RAG recovers most of the full-context lift at ~1/9 the context**: BM25 reaches 77% (45.5/59.1) of
  full-context for gpt-4o-mini and 95% (81.8/86.4) for gpt-5.4. So retrieval is a cheap substitute that
  closes most — but not all — of the gap; full-context still edges it here.
- Clean ordering **full-context ≥ RAG ≥ locator**. The stronger model (gpt-5.4) is higher at every level,
  i.e. model strength matters once any real context is supplied.
- `oracle page` ≈ or slightly below BM25, because it supplies only the single gold page while BM25 top-5
  pulls neighbouring context too — so it is a minimal-context point, not a ceiling.
- Cluster-weighted numbers are high (~85–97%) because these 22 items are near-duplicate retrieval
  templates (few clusters); for this tiny slice **plain accuracy is the more informative metric**.

## 4. Cost

88 calls total (2 retrievers × 2 models × 22), small prompts (~3.3–3.6k input tokens each) → a few cents
total. Predictions/metadata are INTERNAL under `workspace_local/audit/baselines/`.

## 5. Caveats

- Smoke only: 22 items, one task family, 3 bundles, 32k/64k tiers — illustrative, not a benchmark result.
  No leaderboard / human-validated / sealed-hidden / hallucination-free / final-ranking claim.
- The BM25 retriever is a simple lexical baseline (no embeddings/rerankers); a dense/hybrid retriever
  would be a separate, stronger baseline. `oracle` is gold-page-only, not a max-score ceiling.
- `contains_all` scoring can over-credit partial matches; numbers are indicative.
- Full `test_public` and higher tiers (256k/512k) were not run for RAG (cost / smoke scope). gpt-5.4 is
  the only gpt-5-line model reported.
