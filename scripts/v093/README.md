# scripts/v093 — v0.9.3 corrections and their checks

No script here calls an API.

| script | what it does |
|---|---|
| `build_errata.py` | Writes `data/errata_v0.9.3.csv` (v0.9.2 rows, round-2 dev confirmations, the 122 dev items without bundle evidence) and `data/v0.9.3/bundle_exclusions.txt`. |
| `build_human_labels.py` | Writes `results/human_review_v0.9.3/` (labels only) from the round-2 and round-3 annotation files, which stay off the repository because they quote evidence and model answers. |
| `write_verdicts.py` | Writes `results/judge_verdicts_v0.9.3/` from the raw judge batch results and the panel outputs (build machine). |
| `check_fixes.py` | Checks the two code fixes: Hangul page markers (`build_rag_smoke.py`) and the closed-book locator fix (`run_llm_baseline.py`). |
| `list_empty_answers.py` | Lists empty predictions of a run and writes the prompts for the single retry. |
| `score_cb_corrected.py` | Closed-book accuracy before and after the leak fix and the gpt-5.5 retries, from released verdicts only. |
| `score_claude_human.py` | Anthropic-model scores under the primary judge, the secondary judge, the panel mean and the round-3 human labels, from released files only. |

## Code fixes

- **Closed-book locator leak** (`scripts/run_llm_baseline.py`, `build_prompt`). For the 68 items in
  `data/v0.9.3/cb_locator_fix.jsonl` the locator block revealed the answer: for 64 count items the number of
  `row_ids` equals the gold count, and for 4 items a page/bundle id embeds the gold date. `build_prompt`
  now drops those fields for those items. `--legacy-locators` restores the v0.9.2 prompts.
  `check_fixes.py --cb-records ... --e1-prompts ...` confirms that the fixed prompts equal the prompts that
  were re-run, that all 1,929 other closed-book prompts are unchanged, and that no count leak remains.
- **Page markers with Hangul ids** (`scripts/build_rag_smoke.py`, `PAGE_RE`). The v0.9.2 pattern read ASCII
  page ids only, so the 18 SH announcements were not split into pages and their passages carried no page id;
  the retrieved text was unchanged, but gold-page recall on dev was under-counted (40.9% reported, 74.1% when
  passages are matched to gold pages by text). The reported retrieval runs used the old pattern; set
  `KRH_LEGACY_PAGE_MARKERS=1` to reproduce them exactly. New runs use the fixed pattern, which changes the
  page split (and so the passages) of SH bundles.

## Empty answers: single retry

The rule (fixed before any re-run) is in `list_empty_answers.py`. It was applied to gpt-5.5 closed-book
(63 test and 233 dev items empty at the 4,000-token cap; all answered at 16,000), to the leak-fixed gpt-5.5
re-run (28), and to 8 open-model predictions in the re-runs (cap doubled; all answered).
