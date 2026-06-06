# RAG Page-Diversity Diagnostics (v0.7)

**Retrieval-diagnostics only — no model/API answer calls.** Diagnoses whether the dense underperformance
seen in `docs/dense_hybrid_rag_smoke_v07.md` is caused by retrieving **repeated chunks from the same page**
(lack of page diversity), rather than a pure semantic-retrieval failure. Same 22-item slice (test_public,
bundle, 32k/64k tiers, all `long_context_retrieval`). Produced by
`scripts/rag_retrieval_diagnostics_v07.py --per-page-max N` (page-diversity also available in
`scripts/build_rag_smoke_v07.py --per-page-max N`). Aggregate output only; no bundle text published.

## 1. Why repeated pages/chunks matter here

Korean housing announcements are **highly repetitive**: every page repeats boilerplate (전용면적 / 세대 /
공급 / 신청자격 …), so many ~1,200-char chunks are near-duplicates across sibling pages. Page embeddings are
therefore all topically similar, and a dense ranker can fill the top-k with **several chunks from one
repetitive page**, crowding out the single gold page. `--per-page-max N` caps chunks per page in the
ranking (preserving order), which surfaces the gold page if it was buried behind sibling-page chunks.

## 2. Retrieval comparison (same 22 qa_ids)

| retriever | per_page_max | hit@1 | hit@3 | hit@5 | gold-page rank (min/med/max) | same-page dups in top-5 | failures@5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25 | 0 (off) | 68.2% | 100.0% | 100.0% | 1 / 1 / 3 | 1.50 | 0 |
| bm25 | 1 | 68.2% | 100.0% | 100.0% | 1 / 1 / 2 | 0.00 | 0 |
| **dense** | **0 (off)** | 31.8% | 59.1% | 86.4% | 1 / 3 / 7 | 1.77 | **3** |
| **dense** | **1** | 31.8% | **86.4%** | **100.0%** | 1 / 2 / 5 | 0.00 | **0** |
| hybrid | 0 (off) | 50.0% | 77.3% | 100.0% | 1 / 2 / 5 | 1.86 | 0 |
| hybrid | 1 | 50.0% | 95.5% | 100.0% | 1 / 2 / 4 | 0.00 | 0 |

Retrieved token length at k=5 is essentially unchanged (~2.8k; the cap swaps which chunks fill the top-k,
not how many).

> The dense/hybrid numbers above come from a **single embedding pass** (per_page_max 0 and 1 share the
> same embeddings, so the 0→1 comparison is exact). **Separate embedding fetches can show rank-boundary
> drift**: re-fetching embeddings shifted dense/hybrid hit@3 by about ±1 item where similarities are near
> ties (e.g. dense hit@3 was 59.1% here and 63.6% on a separate fetch). The page-diversity **improvement**
> — recovering all 3 dense misses and reaching hit@5 = 100% — is robust to that drift; bm25 is fully
> deterministic.

## 3. Does page diversity fix dense retrieval misses?

**Yes, for hit@3/hit@5.** With `--per-page-max 1`:

- dense hit@3 **59.1% → 86.4%**, hit@5 **86.4% → 100.0%**, failures **3 → 0**.
- hybrid hit@3 **77.3% → 95.5%**.
- bm25 is unchanged (it never depended on duplicate same-page chunks; its top-5 dup count just drops
  1.50 → 0).
- **hit@1 is unchanged for every retriever** — page diversity pulls the gold page *up into* the top-k, but
  the single best chunk at rank 1 is unaffected.

Dense gold-page misses@5 before vs after:

| qa_id | gold page | dense rank (off) | dense rank (per_page_max=1) | recovered? |
|---|---|---:|---:|---|
| `krhlrb_v05_0543` | …-p001 | 6 | ≤ 5 | ✅ |
| `krhlrb_v05_0545` | …-p001 | 6 | ≤ 5 | ✅ |
| `krhlrb_v05_0546` | …-p001 | 7 | ≤ 5 | ✅ |

All 3 misses are recovered: each targeted page `p001` but was buried behind repetitive sibling pages
(p002 / p002 / p004); capping to one chunk per page lifts `p001` into the top-5.

## 4. Does this change the PR #7 interpretation?

**It refines it.** PR #7 reported BM25 > dense on this slice. This diagnostic shows the dense **retrieval**
gap was substantially a **chunk-duplication artifact**, not purely semantic: page-diverse dense closes most
of the hit@3 gap (86.4% vs BM25 100%) and matches BM25 at hit@5 (100%), recovering all 3 misses. BM25 still
leads at hit@1 (68.2% vs 31.8%).

It does **not** overturn PR #7's *answer-accuracy* numbers: those were measured on the non-diverse prompts.
**No answer-accuracy claim is made here** — the existing predictions correspond to non-diverse retrieval,
so they cannot be reused to claim page-diverse answer accuracy, and no new paid answer calls were run.
Measuring whether the retrieval fix translates into higher answers is a separate, paid step.

## 5. Caveats

- Retrieval-diagnostics only; **no answer-accuracy claims**, no paid answer generation. hit@k is an
  imperfect proxy (answers can appear on non-gold pages; retrieving the gold page does not guarantee the
  model reads the right span).
- This result is **specific to this 22-item smoke slice and the current ~1,200-char chunker**; a different
  chunk size or chunking strategy could change the duplication pattern. **Not a general dense-vs-BM25
  conclusion** — this slice's questions quote verbatim document text, favouring lexical BM25; page
  diversity narrows the retrieval gap but does not establish dense superiority anywhere.
- `--per-page-max 1` is a blunt cap; smarter de-duplication (MMR, page-level pooling) is out of scope.
  `gpt-5.4` references elsewhere are model ids, not a ranking claim.

## 6. Reproduce

```bash
export OPENAI_API_KEY=...   # dense/hybrid only; uv sync --extra baseline
for R in bm25 dense hybrid; do for PP in 0 1; do
  python3 scripts/rag_retrieval_diagnostics_v07.py --retriever $R --per-page-max $PP --ks 1,3,5
done; done
```
