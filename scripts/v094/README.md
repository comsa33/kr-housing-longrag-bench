# scripts/v094 — dense retrieval at k=50 and the gold-page recall rule

No script here calls an LLM API. The two scoring scripts read released files only; the others need the bundle
text and the stored retrieval prompts, which are not redistributed (rebuild the bundles first,
`docs/public_reconstruction.md`).

| script | needs | what it does |
|---|---|---|
| `score_k50.py` | released files | The k=50 table: accuracy with Wilson and pair-bootstrap intervals, d against full context (512k) with its interval and the pre-specified label, the secondary judge, the dense top-5 reference, the coverage cross-check, and the panel re-scores of the Anthropic models. |
| `hitmiss.py` | released files | Accuracy on the 258 non-aggregation test_public items split by gold-page hit at k=5, BM25 and bge-m3, eight models. |
| `build_prompts_k50.py` | bundles, stored prompts, local bge-m3 (Ollama) | Rebuilds the dense top-5 prompts and checks them against the stored ones (81/81 identical), then builds the k=50 prompts with only k changed. Output stays under `workspace_local/`. |
| `coverage_k50.py` | bundles, k=50 prompts | Writes `results/retrieval_v0.9.4/k50_coverage_agg81.jsonl`: whether the 50 passages hold the announcement page and how many matched rows they hold; checks that the ranker's top 50 equal the prompt passages. |
| `recall_majority_page.py` | bundles, stored BM25 prompts | BM25 gold-page recall@5 under the majority-page rule and the earlier any-overlap rule (test, dev, the 122 items, pooled, SH and non-SH). |
| `write_verdicts_k50.py` | raw judge batches (build machine) | Writes `results/judge_verdicts_v0.9.4/` (qa_id and verdict only) from the judge batch results and the panel outputs. |
| `k50_lib.py`, `k50_rows.py` | — | Shared retrieval helpers (imports `scripts/build_rag_smoke.py` and `scripts/qa_v03_common.py`). |

The reported retrieval runs used the v0.9.2 page markers: run the bundle-dependent scripts with
`KRH_LEGACY_PAGE_MARKERS=1`. Set `KRH_WORKSPACE` if the local workspace is not `workspace_local/`.

## Pre-specified setting and rule

Fixed before any generation call: the six full-window models read the 50 bge-m3 passages of the item's 512k
bundle with the chunker, prompt builder, passage order and template of the dense top-5 runs; output caps were
raised before the run (gpt-5.5 16,000; Anthropic models and glm-5.2 16,384; minimax-m3 32,768) with the
single-retry rule of `scripts/v093/` as a fallback. d is accuracy at k=50 minus full-context accuracy on the
same 81 items under the primary judge, with a 95% bootstrap over the 9 announcement–table pairs (10,000
resamples, seed 20261011); the label is "exceeds" if the interval lies above 0, "below" if below 0, and
"no detected difference" otherwise. The departures (minimax-m3 reasoning flag, two empty glm-5.2 answers) are
described in CHANGELOG 0.9.4.

## Recall rule

Each retrieved passage is located in its bundle and assigned to the one page that holds most of its
characters; a gold page counts as retrieved when a passage assigned to it is in the top five, and an item with
two gold pages scores half for each page retrieved. On test_public this equals matching page identifiers.
