# Dense / Hybrid RAG Smoke (v0.7)

**Scope.** A small **smoke test** comparing retrievers — BM25 (lexical) vs dense (embeddings) vs hybrid
(fusion) — on the same 22 `qa_id`s as the RAG smoke (`docs/rag_smoke_v07.md`). Smoke only: 22 items, one
task family (`long_context_retrieval`), 3 bundles, 32k/64k tiers — illustrative, not a benchmark/leaderboard
/ranking claim. Retrieval prompts/predictions are INTERNAL under `workspace_local/audit/baselines/`.

## 1. Method

Same page-aware ~1,200-char chunking as the RAG smoke. Retrievers (`scripts/build_rag_smoke_v07.py
--retriever …`, `scripts/rag_retrieval_diagnostics_v07.py --retriever …`):

- `bm25` — pure-python Okapi BM25 (word tokens + Korean char bigrams).
- `dense` — OpenAI `text-embedding-3-small` over the chunks, cosine similarity (lazy SDK; needs the key).
- `hybrid` — reciprocal-rank fusion (RRF, k=60) of the BM25 and dense rankings.

## 2. Retrieval quality (gold-page hit@k, same 22)

| retriever | hit@1 | hit@3 | hit@5 | gold-page rank (min/median/max) | failures@5 |
|---|---:|---:|---:|---:|---:|
| **bm25** | 68.2% | **100.0%** | 100.0% | 1 / 1 / 3 | 0 |
| dense | 31.8% | 59.1% | 86.4% | 1 / 3 / 7 | **3** |
| hybrid | 50.0% | 77.3% | 100.0% | 1 / 2 / 5 | 0 |

**BM25 is the best retriever on this slice; dense is the worst.** This is the opposite of the common
"dense > BM25" assumption — see §4 for why.

## 3. Answer accuracy (same 22, plain), all regimes × 2 models

| regime | gpt-4o-mini | gpt-5.4 |
|---|---:|---:|
| locator-only (no doc) | 0/22 = 0.0% | 1/22 = 4.5% |
| dense RAG | 6/22 = 27.3% | 10/22 = 45.5% |
| hybrid RAG | 6/22 = 27.3% | 15/22 = 68.2% |
| **bm25 RAG** | 10/22 = 45.5% | 18/22 = **81.8%** |
| oracle page | 9/22 = 40.9% | 18/22 = 81.8% |
| full-context | 13/22 = 59.1% | 19/22 = 86.4% |

Retrieval quality **predicts** answer accuracy: better retrieval → better answers. For gpt-5.4,
`full-context (86.4%) > bm25 = oracle (81.8%) > hybrid (68.2%) > dense (45.5%) ≫ locator (4.5%)`. bm25 ≈
oracle because bm25 retrieves the gold page essentially perfectly (hit@3 = 100%), so it has the same
sufficient context as the gold page.

Error decomposition (hit@5 vs answer correctness): bm25 and hybrid have **0 retrieval-misses** (all errors
are read-misses); **dense has 3 retrieval-misses** (gold page not in top-5) that turn into wrong answers —
which is exactly why dense scores lowest.

## 4. Why BM25 wins here (important caveat)

These `long_context_retrieval` questions **quote verbatim document text** (e.g. `… "공공분양주택 686세대"
다음에 제시된 값은 …`). Lexical BM25 matches that exact quoted string and ranks the gold page first
(median rank 1). Dense embeddings, on highly **repetitive** announcement pages (every page mentions
전용면적 / 세대 / 공급 …), are pulled toward topically-similar-but-wrong pages, so the gold page lands lower
(median rank 3, 3 misses@5). Hybrid recovers BM25's hit@5 = 100% but not its top-1/3 precision.

**So this slice favors lexical retrieval and is not evidence that dense is weak in general.** Dense/hybrid
are expected to help where the question does **not** quote the document (paraphrased / `real_user` /
cross-source questions). Evaluating that needs a different slice — a recommended next step.

## 5. Cost

Dense/hybrid add embeddings (`text-embedding-3-small`, ~210 chunk + 22 query vectors per retriever) plus
the answer calls (4 runs × 22, small prompts) — a few cents total. Predictions/metadata are INTERNAL.

## 6. Commands

```bash
B=workspace_local/audit/baselines
export OPENAI_API_KEY=...
# retrieval-quality comparison (embeddings; no answer calls):
for R in bm25 dense hybrid; do python3 scripts/rag_retrieval_diagnostics_v07.py --retriever $R --ks 1,3,5; done
# build + answer (per retriever/model), then score the same 22 with --pred-only:
python3 scripts/build_rag_smoke_v07.py --retriever dense  --k 5 --out $B/rag_dense_smoke_prompts.jsonl
python3 scripts/build_rag_smoke_v07.py --retriever hybrid --k 5 --out $B/rag_hybrid_smoke_prompts.jsonl
# (run scripts/run_llm_baseline_v07.py over each prompt file; score with eval_harness_v06.py --pred-only)
```

## 7. Caveats

- Smoke only (22 items, one task family, 3 bundles); not generalizable; no leaderboard / human-validated /
  sealed-hidden / hallucination-free / final-ranking claim. `gpt-5.4` is the only gpt-5-line model.
- The BM25-wins result is **slice-specific** (verbatim-quote questions); do not generalize it to "dense is
  worse" without a paraphrased-question slice.
- `contains_all` scoring can over-credit partial matches; dense is a single off-the-shelf embedding model
  (no reranker/fine-tuning).
