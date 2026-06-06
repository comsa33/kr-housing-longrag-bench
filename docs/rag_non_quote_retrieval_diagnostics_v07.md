# RAG Non-Quote Retrieval Diagnostics (v0.7)

**Retrieval-diagnostics only — no answer-accuracy claims, no paid answer generation.** Tests the caveat
from PR #7/#8: the earlier BM25 > dense result was on a 22-item slice whose questions **quote verbatim
document text**, which favours lexical retrieval. This slice keeps only **non-quote** bundled questions and
asks whether dense/hybrid behave differently when there is no exact string to match. Produced by
`scripts/rag_retrieval_diagnostics_v07.py --slice non_quote` (dense/hybrid use embeddings; no answer
calls). Aggregate output only; no bundle text published.

## 1. Why this slice

If BM25 only wins because questions echo document text, then removing verbatim-quote questions should let
dense/hybrid catch up or overtake. This slice selects bundled `test_public` questions that do **not** quote
the bundle, so retrieval must work from paraphrase / intent rather than exact strings.

## 2. Selection

`select_non_quote(split="test_public")`: `bundle_id` present, at least one gold `page_id` present in the
bundle (so gold-page retrieval is evaluable), `question_style ∈ {real_user, professional_analyst}`
(excludes `diagnostic_probe`), and **no content quote** (a `"…"`/`"…"` substring ≥ 5 chars, excluding the
`「」` title) that appears verbatim in the bundle text. Any tier/task_type qualifies.

- **Selected: 69 QA**, 5 bundles, gold page present in bundle for 69/69.
- question_style: real_user 26, professional_analyst 43.
- task_type: cross_document_legal_reasoning 23, cross_source_aggregation 18, table_numeric_reasoning 18,
  answerability_detection 4, schedule_reasoning 3, long_context_retrieval 2, correction_notice_reasoning 1.
- Tiers skew large (256k/512k), and two bundles are 890-chunk `mix_multiprovider` bundles (≈ 10
  announcements concatenated), so gold-page retrieval here is genuinely harder than the 32k/64k smoke
  (avg ≈ 651 chunks/bundle vs ≈ 70).

## 3. Retrieval comparison (same 69 qa_ids, single embedding pass)

| retriever | per_page_max | hit@1 | hit@3 | hit@5 | gold-page rank (med/max) | same-page dups in top-5 | failures@5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **bm25** | 0 | 31.9% | 53.6% | **60.9%** | 3 / 120 | 0.75 | 27 |
| bm25 | 1 | 31.9% | 53.6% | 60.9% | 3 / 63 | 0.00 | 27 |
| dense | 0 | 18.8% | 30.4% | 40.6% | 8 / 272 | 0.65 | 41 |
| dense | 1 | 18.8% | 37.7% | 52.2% | 5 / 98 | 0.00 | 33 |
| hybrid | 0 | 21.7% | 43.5% | 58.0% | 4 / 74 | 0.64 | 29 |
| hybrid | 1 | 21.7% | 49.3% | 58.0% | 4 / 43 | 0.00 | 29 |

(Retrieved tokens at k=5 ≈ 2.7–2.85k for all. Tool runs of `--slice non_quote --retriever {dense,hybrid}`
reproduced these numbers exactly.)

## 4. Findings

- **Everyone drops sharply vs the quote slice.** BM25 hit@5 falls 100% → 60.9%, dense 86.4% → 40.6%,
  hybrid 100% → 58.0%. So verbatim quotes were a **large lexical signal** for every retriever — that part
  of the PR #7/#8 caveat holds.
- **But BM25 still wins on non-quote questions**, at every k: bm25 hit@5 **60.9%** > hybrid 58.0% > dense
  40.6%. Removing the quotes did **not** make dense competitive, let alone superior.
- **Does this support or weaken the "BM25 wins because questions quote text" hypothesis?** It **partially
  supports and partially weakens it.** Supports: quotes clearly inflated lexical retrieval (all retrievers
  drop without them). Weakens: the lead is **not** purely a quoting artifact — BM25 still leads on
  paraphrased questions, because Korean housing announcements are dense with distinctive surface tokens
  (place names, 단지/블록 codes, dates, 세대/㎡ numbers) that lexical matching catches and that off-the-shelf
  embeddings blur in a repetitive corpus.
- **Page diversity still helps dense/hybrid** (dense hit@5 40.6% → 52.2%, misses 41 → 33; hybrid hit@3
  43.5% → 49.3%), consistent with PR #8 — but it does **not** change the retriever ranking (BM25 still
  leads). BM25 itself is essentially unaffected by the cap (it already retrieved few same-page duplicates).

## 5. Caveats

- **Retrieval-only. No answer-accuracy claim. No paid answer generation was run** (dense/hybrid used
  embeddings only; cross-ref is skipped for the non_quote slice because no predictions exist for it).
- Smoke-scale (69 items, 5 bundles, test_public). hit@k is an imperfect proxy (answers can sit on non-gold
  pages; retrieving the gold page does not guarantee a correct read).
- The slice is dominated by large 256k/512k bundles (incl. two 890-chunk multi-provider mixes), which makes
  gold-page retrieval hard for everyone (gold-page ranks up to 272); a smaller-bundle non-quote slice could
  look different.
- The non-quote filter is a heuristic (verbatim content-quote ≥ 5 chars in the bundle); some paraphrase may
  remain. Result is specific to this slice + the current ~1,200-char chunker + `text-embedding-3-small`.
- **Not a general dense-vs-BM25 conclusion.** A stronger embedding model, a reranker, or a different
  chunker could change the picture. `gpt-5.4` references are model ids, not a ranking claim.

## 6. Reproduce

```bash
python3 scripts/rag_retrieval_diagnostics_v07.py --slice non_quote --retriever bm25 --max-items 100 --ks 1,3,5
export OPENAI_API_KEY=...   # dense/hybrid only; uv sync --extra baseline
for R in dense hybrid; do for PP in 0 1; do
  python3 scripts/rag_retrieval_diagnostics_v07.py --slice non_quote --retriever $R --per-page-max $PP --max-items 100 --ks 1,3,5
done; done
```
