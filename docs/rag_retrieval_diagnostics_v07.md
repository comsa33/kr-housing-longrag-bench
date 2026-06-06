# RAG Retrieval Diagnostics (v0.7)

Retrieval-quality analysis for the RAG smoke (`docs/rag_smoke_v07.md`), separate from answer accuracy.
It measures whether BM25 actually retrieves the gold page, and splits the RAG answer errors into
**retrieval-miss** vs **read-miss**. Produced by `scripts/rag_retrieval_diagnostics_v07.py` — **no model /
API calls**; it reads internal bundle text + internal BM25 prediction files but emits only aggregate stats
+ qa_ids (no bundle text), so this report is public-safe.

Slice: the same 22 `test_public` items as the RAG smoke (bundle, tier 32k/64k, all
`long_context_retrieval`); BM25 over ~1,200-char page-aware chunks (avg 70.5 chunks/bundle).

## 1. Gold-page retrieval (hit@k / recall@k)

`hit@k` = fraction of items whose **gold page** has at least one chunk in the BM25 top-k. Gold page is
present in the bundle for **22/22** items.

| k | hit@k (gold page in top-k) | avg retrieved tokens |
|---:|---:|---:|
| 1 | 15/22 = 68.2% | 689 |
| 3 | 22/22 = **100.0%** | 2,024 |
| 5 | 22/22 = 100.0% | 3,307 |
| 10 | 22/22 = 100.0% | 6,307 |

Gold-page rank in the BM25 ranking: **min 1 / median 1 / max 3**. **Failure cases (gold page not in
top-5): 0.** So at k ≥ 3, BM25 retrieves the gold page for every item, and the top-5 used by the smoke
(~3.3k tokens) always contains it.

## 2. Where do RAG errors come from? (retrieval-miss vs read-miss)

Cross-referencing retrieval `hit@5` with answer correctness from the internal BM25 predictions:

| Model | correct | wrong | of which retrieval-miss | of which read-miss |
|---|---:|---:|---:|---:|
| gpt-4o-mini | 10/22 | 12 | 0 | 12 |
| gpt-5.4 | 18/22 | 4 | 0 | 4 |

**Every RAG error on this slice is a read-miss** (the gold page was retrieved but the model still answered
wrong); **zero retrieval-misses**. So on this slice retrieval is **not** the bottleneck — the gap between
RAG and full-context, and between models, is driven by reading the retrieved page, not by finding it. This
is consistent with RAG ≈ full-context in `docs/rag_smoke_v07.md`.

## 3. Caveats (important)

- **These questions embed the locator.** The `long_context_retrieval` questions name the announcement and
  page in the text (e.g. `「…0000061086」(p.1) 공고문에서 …`), which makes lexical BM25 retrieval easy
  (hit@3 = 100%). This slice is therefore **not a realistic retrieval stress test**; it isolates reading,
  not retrieval. A real retrieval evaluation needs questions that do **not** name the page (e.g.
  `real_user`-style questions, cross-source, or other task families).
- Smoke only: 22 items, one task family, 3 bundles, 32k/64k tiers — not generalizable; no leaderboard /
  human-validated / final-ranking claim.
- BM25 is a simple lexical retriever (word tokens + Korean char bigrams); a dense/hybrid retriever is a
  separate, likely stronger baseline (next step). `gpt-5.4` is the only gpt-5-line model reported.

## 4. Reproduce

```bash
python3 scripts/rag_retrieval_diagnostics_v07.py          # hit@k, gold-page rank, token length, cross-ref
```

(`--ks 1,3,5,10`, `--chunk-chars 1200`, `--cross-ref gpt-4o-mini,gpt-5.4` are configurable.) Requires the
internal bundles under `workspace_local/`; the cross-ref section needs the internal BM25 prediction files
from the RAG smoke. Aggregate output only — no bundle text is printed.
