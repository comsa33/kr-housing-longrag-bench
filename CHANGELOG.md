# Changelog

## v0.9.3 — leak and page-marker fixes, more human labels, re-run verdicts (release date TBD)

No change to the questions, answers, schema, or splits. `data/qa_*.jsonl` are byte-identical to v0.9.2, and
the v0.9.2 gold fixes and the 342-item test scope stay in force. The 7 dev errors confirmed by the round-2
human review are excluded from evaluation, as the confirmed ill-posed test items were in v0.9.2:
`data/v0.9.3/eval_exclusions.txt` lists the 5 test and 7 dev items (sections marked by split). v0.9.3
evaluation scope: legal family and these 12 items excluded, 1,876 items (dev 1,534 / test_public 342); the
122 dev items without bundle evidence are further excluded from the bundle settings.

### Changes from v0.9.2 and the figures they affect
- **Closed-book locator leak.** For 68 items the closed-book locator block revealed the answer: for 64 count
  items (test 17, dev 47) the number of listed `row_ids` equals the gold count, and for 4 items (test 1,
  dev 3) a page or bundle id embeds the gold date. `scripts/run_llm_baseline.py` now drops those fields for
  those items (`data/v0.9.3/cb_locator_fix.jsonl`; `--legacy-locators` restores the old prompts). The
  affected closed-book items were re-run for every model that can still be run. Affects closed-book scores
  only.
- **Empty answers.** gpt-5.5 returned no answer for 63 of 342 test and 234 of 1,541 dev closed-book items
  because its reasoning used the whole 4,000-token output cap. Under a rule fixed before any re-run, each
  was re-run once at 16,000 tokens; all were answered. The same rule (cap doubled for open models) was
  applied to 28 items of the leak-fixed gpt-5.5 run and to 8 open-model predictions; all were answered
  (`scripts/v093/list_empty_answers.py`).
- **Page markers with Hangul ids.** The page-marker pattern in `scripts/build_rag_smoke.py` read ASCII ids
  only, so the 18 SH announcements were not split into pages and their passages carried no page id. The
  retrieved text and the accuracy results are unchanged; dev gold-page recall was under-counted (40.9%
  reported, 74.1% when passages are matched to gold pages by text; test unchanged at 89.7%). The pattern is
  fixed; `KRH_LEGACY_PAGE_MARKERS=1` reproduces the reported runs.
- **Dev items without bundle evidence.** For 122 dev items (multi-document comparison 62, aggregation 36,
  region comparison 21, provider comparison 3; all 512k) the gold page is not in their 512k bundle. They are
  excluded from BM25, dense and full context and kept in closed-book (`data/v0.9.3/bundle_exclusions.txt`;
  `scripts/score_judge.py --exclude-bundle-ids`). All test items have their gold page in the bundle, and the
  table rows of the other 144 dev aggregation items are all in the bundle.
- **Models and judges.** qwen3.5 was withdrawn by its provider and is not reported. In the judge panel,
  deepseek-v3.2 was withdrawn and replaced by deepseek-v4.1-flash (κ 0.949 against the 80 human labels; the
  acceptance rule κ ≥ 0.85 was fixed in advance). The v0.9.2 deepseek-v3.2 verdicts stay published.
- **Settings restated.** minimax-m3 produced reasoning in its closed-book and retrieval runs although the
  run metadata say reasoning off. Prompt sizes: the 512k prompt is 330k–520k tokens depending on the
  model's tokenizer (511k by the cl100k count used for the tiers); the top-5 retrieval prompt is about 3k–5k.

### Added human labels (`results/human_review_v0.9.3/`)
- Round 2: the two non-author annotators reviewed 100 random in-scope dev items with the four checks of
  the test review. Both labelled the same 7 items as errors (κ 1.0) and the author confirmed all 7: dev error
  estimate 7/100 = 7.0% [3.4, 13.7]. The 7 items are excluded from evaluation in every setting
  (`excluded_from_evaluation` in `data/errata_v0.9.3.csv`; listed in `data/v0.9.3/eval_exclusions.txt`); they
  stay in the data with their gold unchanged. They also labelled the 80 judge-validation predictions
  independently (model names hidden): on the 78 items both labelled, they agree with each other and with the
  primary judge on all 78.
- Round 3: they labelled the 74 predictions of claude-sonnet-5-5 and claude-haiku-5-5 (of 2,722) on which
  the six judges disagree; if they agreed, that label stands (53), otherwise the author decided (21), under
  a rule fixed before labelling. The primary judge had credited 21 of the 74 that the human labels mark
  wrong. Scores with the human labels differ from the primary judge by at most 4.9 points
  (`scripts/v093/score_claude_human.py`).
- In every round the annotators worked independently, did not use AI tools and had up to one week. They
  received no further payment after the first round.
- The v0.9.2 test review also recorded naturalness (q4): two or more of the three annotators marked 52 of
  347 items as not reading naturally (51 script-generated, 1 cloze-regenerated). Naturalness is not an error
  criterion; the items stay in the evaluation.

### New verdicts (`results/judge_verdicts_v0.9.3/`)
- Primary (claude-sonnet-5-5) and secondary (gpt-4.1-mini) verdicts for: the leak-fixed closed-book items
  (`cbfix_*`), the gpt-5.5 retries (`g55retry_*`), glm-5.2 with reasoning on (`thinkon_*`), the aggregation
  set with oracle rows and with all rows of the item's year or month (`oracle_agg81_*`, `openregion_agg81_*`),
  and all settings for claude-sonnet-5-5 and claude-haiku-5-5. `panel/` holds the four panel judges'
  verdicts on all Anthropic predictions, deepseek-v4.1-flash on the 80 human-labelled predictions and on the
  aggregation-set full-context predictions of the four original full-window models. `MANIFEST.csv` lists
  every file. Predictions and prompts stay internal, as in v0.9.2.

### Errata
- `data/errata_v0.9.3.csv`, 206 rows: the v0.9.2 rows (status column renamed `v0.9.3_status`), the 7 round-2
  dev confirmations, now excluded from evaluation (6 were among the v0.9.2 automatic flags) and the 122 dev items without bundle evidence.

### Scripts
- New `scripts/v093/` (`build_errata.py`, `build_human_labels.py`, `write_verdicts.py`, `check_fixes.py`,
  `list_empty_answers.py`, `score_cb_corrected.py`, `score_claude_human.py`); see its README.
- `scripts/score_judge.py --exclude-bundle-ids FILE`: drop items from the rag, dense and fc regimes only.

## v0.9.2 — full test review, gold fixes, Claude primary judge (2026-10-11)


No change to the questions, schema, or splits. `data/qa_*.jsonl` are byte-identical to v0.9.1. The gold
changes are published as a separate file, `data/v0.9.2/gold_fixes.json`, and the scoring scripts apply them.

### Human review of the full evaluated test set
- Three annotators (the first author and two native Korean speakers who are not domain experts) labelled
  all 347 evaluated `test_public` items independently with the four checks of the v0.9.1 audit. Items
  that at least one annotator marked as an error (39) were adjudicated by the author.
- Result: 29 of 347 items have an error, 8.4% [5.9, 11.7] (Wilson 95%). Script-generated items 25/179 =
  14.0% [9.6, 19.8]; cloze-regenerated items 4/168 = 2.4% [0.9, 6.0].
- Agreement before adjudication: Fleiss κ 0.705; pairwise raw agreement 94.2% / 94.2% / 98.3%.
- New `results/human_review_v0.9.2/`: per-annotator labels (347 × 3) and the 39 adjudication decisions.
  No question, answer, evidence or memo text is included.

### Correction of the v0.9.1 audit figure
- v0.9.1 reported a one-author sample audit of 118 items with 1 error, 0.8% [0.1, 4.6]. Under the
  three-annotator review, the same 118 items have 8 errors; the single v0.9.1 annotator had flagged 1 of
  them (0772). The 0.8% figure is therefore corrected to the full-review rate above. The v0.9.1 entry
  below and `results/human_audit/` are left as published.

### Gold fixes and evaluation scope (`data/v0.9.2/gold_fixes.json`)
- 24 items get a corrected gold answer. 23 accept any of several answers that the source supports
  (`accept_any`), and 1 gets a new answer (`replace`, `krhlrb_v05_0568`). Questions are unchanged.
- 5 items are excluded from evaluation because the question is ill-posed: 0994, 0995, 1125, 1132 (table
  header misparse) and 1369 (supply type not named). They stay in the data. The list is also in
  `data/v0.9.2/eval_exclusions.txt`.
- v0.9.2 evaluation scope: legal family and the 5 items excluded, 1,883 items (dev 1,541 / test_public 342).
- `dev` was not reviewed by people. Detectors built from the test review flag 54 dev items (44 dual-row
  gold, 6 multiple schedules, 4 header misparse). These are unverified flags; the items are still evaluated.
  On `test_public` the detectors recover 25 of the 29 confirmed errors and flag no other item.

### Errata
- `data/errata_v0.9.2.csv`, 83 rows: the 29 confirmed test errors with type, old answer, new or accepted
  answers and status (dual-row gold 19, multiple schedules 3, header misparse 4, wrong gold 1, scope
  mismatch 1, unspecified type 1), and the 54 unverified dev flags. `data/errata_v0.9.1.csv` is unchanged.

### Judges
- Primary judge: `claude-sonnet-5-5` (Message Batches API; no temperature, which the API rejects for
  this model; JSON-schema verdict). Same instruction text as `scripts/llm_judge.py`. Accept-any gold is
  shown as `다음 중 어느 하나와 일치하면 정답: (1) … / (2) …`.
- Secondary judge: `gpt-4.1-mini`, with its v0.9.1 verdicts except on the 24 gold-fixed items, which were
  re-judged with the same prompts.
- Checks: agreement with the 80 human labels 98.8%, κ 0.975 (gpt-4.1-mini 96.2%, κ 0.924); 100/100
  identical verdicts on a re-run; 99.5% agreement between the two judges over 8,091 in-scope test verdicts
  and over 10,844 dev verdicts.
- New `results/judge_verdicts_v0.9.2/{claude-sonnet-5-5,gpt-4.1-mini}/<tag>.jsonl` (36 runs; test_public,
  plus dev for the 12 GPT core runs) and `human80_claude-sonnet-5-5.jsonl`.
- New `scripts/judge_v092/`: prompt builders, prediction mapping for test and dev, batch runner and parser,
  the gpt-4.1-mini re-judge input builder and the verdict writer. The rebuild reproduces the submitted
  inputs and the released verdict files exactly. Model predictions stay internal.

### Scripts
- `scripts/score_judge.py`, `scripts/score_retrieval.py` and `scripts/paper/{paired_rq1,tier_small_window,
  family_table,scope_counts}.py` take `--exclude-ids FILE`; `family_table.py` also takes `--verdicts-dir`.
  Defaults are unchanged and reproduce the v0.9.1 numbers. v0.9.2 numbers:
  `--exclude-family cross_document_legal_reasoning --exclude-ids data/v0.9.2/eval_exclusions.txt
  --verdicts-dir results/judge_verdicts_v0.9.2/claude-sonnet-5-5`.
- New `scripts/v092/`: `detect.py` (dev defect flags), `build_errata.py` (`data/errata_v0.9.2.csv`) and
  `score29.py` (scores on the 29 fixed or excluded items under old and new gold).

## v0.9.1 — result-reproduction files (2026-10-10)

No change to the QA items, answers, schema, or splits. `data/qa_*.jsonl` are byte-identical to v0.9.
This release adds the files needed to recompute the reported results, and it publishes code fixes made
after the v0.9 tag. The v0.9 archive (DOI 10.5281/zenodo.20640480, 2026-06-11) predates these fixes.

### Fixed (after v0.9; all reported runs use the fixed code)
- **512k bundle builder fix** (`8a9a497`, 2026-07-10). An earlier build of `mix_multiprovider_512k`
  omitted some statute articles and table rows that its legal and aggregation items require. The builder
  now embeds the cited statute articles and the MOLIT trade-detail slices as required components. The
  full-context verdicts that involve this bundle were re-run on the rebuilt bundle and merged on
  2026-07-11 (`16e2258`). Models that cannot take the 512k tier (gpt-5.4-mini, gpt-5.4-nano, qwen3.5)
  never received this bundle.
- **RAG chunker preamble fix** (`0606c59`, 2026-07-13). The page-marker chunker dropped text before the
  first page marker, so retrieval never indexed the aggregation tables and statute text at the front of
  the mix bundle. The reported BM25 and dense test_public runs use the fixed chunker: the
  `rag_{bm25,dense}_tp386_fixed` prompts retrieve `preamble-p000` pages.

### Added
- `results/judge_verdicts/`: per-item LLM-judge verdicts (`qa_id`, `judge_correct`) for all 114 judged
  runs, plus `MANIFEST.csv` (model, regime, item set, n, use). Also `human80_labels.jsonl` (human Y/N
  for the judge-validation sample) and `results/item_sets/agg81.jsonl`.
- `scripts/verdict_paths.py`. `score_judge.py` and `kappa_panel.py` take `--verdicts-dir` and fall back to
  `results/judge_verdicts/` when the internal working copy is absent.
- `scripts/paper/`: `paired_rq1.py`, `tier_small_window.py`, `evidence_check_agg81.py`, the analysis
  scripts behind the paper tables, adapted to this repository layout.
- `construction/`: QA construction scripts, docs and prompts restored from `archive/` (removed in
  `be18447`) plus `prompts/v0.5_worker_prompt.md` (from `docs/` at v0.9, removed in `1a6695f`), and `construction/v0.8_regeneration/` (triage and repair scripts with qa_id-level verdict
  summaries). This is provenance only; reproduction does not need it.

### Evaluation scope
- The v0.9.1 evaluation excludes the `cross_document_legal_reasoning` family (109 items, 42 in
  `test_public`); the items stay in the data. Scoring scripts take `--exclude-family` (and
  `--exclude-bundle`); the default reproduces the v0.9 numbers. In scope: 1,888 items (dev 1,541 /
  test_public 347). New `scripts/paper/family_table.py` and `scripts/paper/scope_counts.py`.
- Known issue: the `mix_multiprovider_256k` bundle is ~710k cl100k tokens, longer than the 512k bundle
  (`scripts/build_bundles.py` does not trim it). 37 items (dev 28, test_public 9) use it; use
  `--exclude-bundle mix_multiprovider_256k` to report the 256k tier without them.

### Added (errata and human audit)
- `data/errata_v0.9.1.csv`: one row per affected item (111). It covers the 109 legal-family items with the
  statute-version check (holds 72, partial 18, holds_basis_moved 12, does_not_hold 6, unverified 1), the
  reason they are excluded from v0.9.1 evaluation, and two items flagged by the human audit:
  `krhlrb_v05_0772` (incomplete gold answer: 130% given, 140% missing) and `krhlrb_v05_0361` (ambiguous
  question). The data files are not changed.
- `results/human_audit/human_audit_v091.jsonl`: one author's verdicts on a stratified sample of 118
  evaluated `test_public` items. There are four checks per item and no timing field. Result: 1 error, 0.8%
  [0.1, 4.6].
- `scripts/paper/build_audit_items.py` (seed 20261010; `--ids-only` runs without source text) and
  `scripts/paper/audit_summary.py`.

### Changed (wording)
- The v0.8 build is now called the "LLM-triage repair build" in README, DATASET_CARD, CITATION, Zenodo
  metadata, `docs/dataset_statistics.md` and this changelog. The earlier name, "human-review repair build",
  overstated the human role: v0.8 repairs came from an LLM triage (gpt-5.4) and LLM regeneration (Claude),
  and no systematic item-level human review was recorded. The LLM-judge validation (one annotator, 80
  predictions, κ=0.924) is a separate, real human check and is described as before.

### Changed since v0.9 (already on the branch, not new in this entry)
- `data/source_manifest.jsonl`: per-source `content_sha256` checksums (`90c63d4`).
- `data/cluster_map.jsonl` released (`d8524c5`).
- Script and doc files renamed without version suffixes; internal docs removed from the public tree.

## v0.9 — split consolidation + release-grade baselines (2026-06-11)

Same 1,997 QA and schema as v0.8; this is a split-policy + evaluation change, not a content rebuild.

### Changed
- **`test_hidden` (285) merged into `test_public`** → a single public held-out test of **389** (dev stays
  1,608). The former hidden split was never a sealed leaderboard set (its policy already said so), and a
  larger public test is more valuable than a sealed set we cannot serve. Announcement-level dev↔test
  disjointness is preserved (leakage = 0, `verify_qa.py`). The 512k tier grows 41 → **124**, and the
  `ood_region` (116) / `ood_year` (50) generalization subsets are retained via `split_tags`. A future
  release can re-carve a sealed hidden split from grown data; `make_v06_splits.py` still supports one.

### Removed
- `data/qa_v0.6_test_hidden_questions.jsonl` (masked-answer hidden file) — no longer a separate split.

### Added (evaluation, see `docs/baseline_results.md`)
- Release-grade baselines: 5 models × 3 regimes (closed-book / RAG-BM25 / full-context) via the OpenAI
  Batch API, **LLM-judge headline metric human-validated** (n=80, agreement 96.2 %, Cohen's κ=0.924).
- **HUG bundle fix (dataset level):** `mix_multiprovider_512k` — the bundle every `cross_source_aggregation`
  item references — now **embeds the complete HUG sale-history table** (`build_bundles.py`), so these
  questions are answerable in the full-context regime instead of being an unanswerable artifact. The fix
  turns the 512k tier into a real capability signal (gpt-5.5 76% vs gpt-4.1-mini 20% at n=25). Only that one
  bundle changed on rebuild; the other 166 are byte-identical.

## v0.8 — LLM-triage repair build (1,997 QA)

_Renamed in v0.9.1; earlier releases called this the "human-review repair build", which overstated the human role._

Supersedes the v0.6 dataset build. The v0.7 release falsely described the data as "v0.6 unchanged"; v0.8
is the first build where the QA content was substantively repaired through an LLM triage pass
(gpt-5.4 grounding triage + cross-model verification + source-grounded fixes).

### Changed
- **Positional-cloze eliminated.** All ~686 templated `"X 다음/앞에 제시된 값은?"` / `[위치 탐침]` questions
  (34% of the dataset — a string-matching probe, not document understanding) were regenerated into natural,
  source-grounded questions (679 regenerated; Claude generate → gpt-5.4 cross-model verify) or removed.
  `question_style` is now 100% `real_user`/`professional_analyst` (was 92.2%); cloze-phrased ≈ 0% (was 7.8%).
- **Location mislabels fixed (source-grounded):** 항동(sh-196920) 서울특별시→구로구 (15 answers + 51
  region_sigungu); jpdc-ildo 제주특별자치도→제주시; 발산8단지 region_sigungu →서울특별시 강서구. region_sigungu
  normalized to the full `서울특별시 구로구` form. (Verified ih-cheonwon / bmc-youth as correctly 시·도-level
  city-wide programs — NOT changed.)
- **Confirmed wrong answers fixed:** table 0910 평균 전용면적 29.58→24.10 (gold cited the wrong row).

### Removed (14 unrepairable / confirmed-broken items; 2,011 → 1,997)
- correction_notice_reasoning 0901/0902 (gold falsely claimed `정정 공고` from an unrelated `정정` string),
  ungrounded table item 1035, malformed schedule items 1148/1157/1160, and 8 cloze items whose regeneration
  did not pass cross-model verification.

### Known limitations (carried to v0.9)
- ~20 `cross_document_legal_reasoning` gold answers are concise, grounded paraphrases of the cited statute
  article that omit secondary qualifiers (e.g. `1세대 1주택`, `시·도지사 승인 예외`); grounded but not exhaustive.
- `region_sigungu == region_sido` remains on ~270 items for announcements whose true 시·군·구 was not resolved
  (a v0.9 metadata sweep); the 항동/jpdc/발산 cases were fixed.
- v0.8 repairs came from an LLM triage (gpt-5.4) and LLM regeneration (Claude); no systematic item-level human review was recorded.

### Tooling
- Provider-agnostic triage/verification runner (`run_triage_v08.py`), regeneration + integration pipeline,
  and gates all green: `validate_dataset.py`, `verify_qa.py` (1,997/1,997), `check_public_release_readiness.py`
  (public-ready), `check_question_realism.py` (0 failures).

## v0.7 — research preview (over v0.6 build, 2,011 QA)
Added a provider-agnostic baseline runner, full-context / RAG smoke diagnostics, retrieval diagnostics, and
a repository scope policy on top of the (then-unchanged) v0.6 dataset build. Zenodo DOI 10.5281/zenodo.20570856.

## v0.6.x — source-expansion + quality / realism build (2,011 QA)
Multi-provider source expansion, realism phrasing pass, near-duplicate clustering, materialized
long-context bundles, and public release splits. Archived as v0.6.3 (DOI 10.5281/zenodo.20563604).
