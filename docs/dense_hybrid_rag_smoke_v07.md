# Dense / Hybrid RAG Smoke (v0.7)

**Scope.** A small **smoke test** comparing retrievers — BM25 (lexical) vs dense (embeddings) vs hybrid
(fusion) — on the same 22 `qa_id`s as the RAG smoke (`docs/rag_smoke_v07.md`). Smoke only: 22 items, one
task family (`long_context_retrieval`), 3 bundles, 32k/64k tiers — illustrative, not a benchmark/leaderboard
/ranking claim. Retrieval prompts/predictions are INTERNAL under `workspace_local/audit/baselines/`.

## 1. Method

Same page-aware ~1,200-char chunking as the RAG smoke. Retrievers (`scripts/build_rag_smoke_v07.py
--retriever …`, `scripts/rag_retrieval_diagnostics_v07.py --retriever …`):

- `bm25` — pure-python Okapi BM25 (word tokens + Korean char bigrams).
- `dense` — OpenAI `text-embedding-3-small` over the chunks, **dot-product** similarity (these embeddings
  are unit-normalized, so dot product is equivalent to cosine for this fixed model; lazy SDK, needs the key
  + `uv sync --extra baseline`).
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

Retrieval quality **explains much of the answer-accuracy trend, but read failures remain substantial**.
For gpt-5.4, `full-context (86.4%) > bm25 = oracle (81.8%) > hybrid (68.2%) > dense (45.5%) ≫ locator
(4.5%)`. bm25 ≈ oracle because bm25 retrieves the gold page essentially perfectly (hit@3 = 100%), so it has
the same sufficient context as the gold page.

Error decomposition (gpt-5.4, hit@5 vs answer correctness):

| retriever | hit_correct | hit_wrong (read failure) | miss_correct | miss_wrong |
|---|---:|---:|---:|---:|
| bm25 | 18 | 4 | 0 | 0 |
| hybrid | 15 | 7 | 0 | 0 |
| dense | 9 | 10 | 1 | 2 |

dense had **3 gold-page misses@5, but only 2 became wrong answers** — the 3rd (`miss_correct = 1`) was
still answered correctly from another retrieved page. bm25 and hybrid had 0 gold-page misses, so all their
errors are **read failures** (gold page retrieved but the model answered wrong). Read failures dominate
every retriever (bm25 still has 4), so **read failures — not retrieval — are the larger error source
overall**; dense simply adds 2 retrieval-driven misses on top of more read failures.

> **Gold-page hit@k is an imperfect proxy.** Answers can appear on non-gold pages (dense's 1 `miss_correct`
> above is exactly that case), and retrieving the gold page does not guarantee the model reads the right
> span (hence the large read-failure counts). Treat hit@k as a retrieval signal, not a guarantee.

The 3 dense gold-page misses@5 are `krhlrb_v05_0543`, `krhlrb_v05_0545`, `krhlrb_v05_0546`: all target page
`…-p001`, but dense ranked it 6th/6th/7th and instead surfaced repetitive sibling pages (p002 / p002 /
p004) whose announcement boilerplate is embedding-similar to the question.

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
- Reported answer scores were measured under the prior cosine implementation. Switching dense similarity
  to dot-product leaves the **dense** ranking byte-identical (hit@k unchanged) and shifts only a few
  non-gold neighbour chunks for **hybrid** (4 of 22 prompts; hit@k still 50/77.3/100). Answers were **not**
  re-measured under dot-product (no paid reruns), so the hybrid answer numbers correspond to the cosine
  ordering; the qualitative ordering (bm25 > hybrid > dense) is unaffected.
- The BM25-wins result is **slice-specific** (verbatim-quote questions); do not generalize it to "dense is
  worse" without a paraphrased-question slice.
- `contains_all` scoring can over-credit partial matches; dense is a single off-the-shelf embedding model
  (no reranker/fine-tuning).
