# Changelog

## v0.9.8 — machine-readable locator corrections for the dev review (2026-10-12)

No change to the questions, gold answers, locators in the question files, splits, exclusions, verdicts, or
any reported number of v0.9.7. This release makes the v0.9.7 locator corrections machine-readable and
corrects three statements in the v0.9.7 notes below.

- `data/errata_v0.9.7.csv` gains a last column `new_locator`, filled for the 30 locator_fixed rows
  (`old -> new`, several pages joined by ` ; `; 31 page mappings) and empty elsewhere; the other nine
  columns are unchanged. Use it with the question files, which keep the original locators.
- `scripts/v097/score_dev_review.py` writes the new column; `scripts/v097/recall_v097.py` reads the new
  locators from it and the exclusions from `data/v0.9.7/eval_exclusions.txt` (it asserts 30 items and 31
  mappings). It reproduces the v0.9.7 majority-page recall (dev 75.05%, pooled 78.89%; before the review
  74.90 / 78.74) given the bundle texts, which are not redistributed.
- v0.9.7 notes corrected: the author adjudicated 122 items (121 flagged and 1 with only a review-sheet
  note), not 121; the locator corrections cover 30 items and 31 page mappings, and the split
  10 / 15 / 1 / 5 counted pages; the locator rule was recorded before the new locators were computed, not
  before the review.

## v0.9.7 — full human review of dev and a second judge-validation sample (2026-10-12)

No change to the questions, schema, splits, or the test_public gold answers and verdicts of v0.9.6. This
release adds a two-annotator review of every evaluated dev item, the corrections and exclusions it produced,
and a second human-labeled sample for validating the two judges.

### Full review of dev (`results/human_review_v0.9.7/`, `data/errata_v0.9.7.csv`)
- **Scope.** All 1,534 evaluated dev items (1,608 minus the 67 legal items, which are not evaluated, and the
  7 items excluded after the 100-item sample review). Each item was labeled independently by two of four
  non-author annotators (native Korean speakers, not domain experts) in 31 blocks of 50 items that rotate
  through all six annotator pairs under seed 20261012; the same error definition as the test_public review (a "no" on any of: single interpretation,
  evidence supports the answer, answer correct and complete). Naturalness was not collected. The block
  assignment (`assignment.csv`) was fixed before labeling.
- **Labels.** 121 items flagged by at least one annotator (79 by both; 9 unsure marks, none by both);
  pairwise raw agreement 94.0-100% (Cohen's kappa 0.488-1.000, PABAK 0.880-1.000; by pair AB 96.8/0.774,
  AC 95.6/0.732, AD 94.0/0.488, BC 98.4/0.825, BD 98.8/0.897, CD 100/1.000). The author adjudicated 122 items
  (the 121 flagged items and 1 item with only a review-sheet note): 120 confirmed errors (7.8% of 1,534, Wilson 95% [6.6, 9.3]; test_public: 29 of 347, 8.4%);
  the 2 other flags were annotator misreadings; no flag arose from a review-sheet defect. Of the 100 items
  of the earlier sample review, 93 are in scope and the new labels agree with the earlier ones on 91. This
  result supersedes the sample estimate 7.0% [3.4, 13.7] (n=100).
- **By type.** dual_row 51, other 32, unspecified 18, wrong_gold 5, header_parse 5, multiple_schedules 5,
  scope 4. By family (errors/n): eligibility 28/56 (50.0% [37.3, 62.7]), schedule 5/20, multi-document 13/82,
  provider 3/25, table_numeric 47/485 (9.7% [7.4, 12.6]), region 2/27, aggregation 12/180, long_context
  10/474 (2.1% [1.1, 3.8]), answerability 0/90, format 0/60, long_distance 0/35. By route: script 47/496
  (9.5% [7.2, 12.4]), template_reworded 63/529 (11.9% [9.4, 14.9]), cloze_regenerated 10/509 (2.0% [1.1,
  3.6]); route is nearly determined by family in dev. Detector check: all 54 `auto_flag_unverified` items are
  confirmed errors (48 in scope, 6 among the 7 earlier sample exclusions; precision 48/48 = 100% [92.6,
  100]); the detectors recall 48 of the 120 errors (40.0% [31.7, 48.9]).
- **Treatment.** 79 gold answers corrected without changing the question (74 now accept any of several
  values, 5 replaced); the evidence locators of 30 items (31 page mappings) corrected under a rule recorded before the new
  locators were computed (by item: 10 unique under the rule, 15 author-selected among candidates, one of which
  moves two pages chosen among 2 and among 11, and 5 author-confirmed table-row addresses; the 122
  bundle-exclusion list is unchanged); 11 items excluded from evaluation (ill-posed as written; they stay in
  the data). `data/v0.9.7/eval_exclusions.txt` lists the 11 new exclusions;
  `data/errata_v0.9.7.csv` has one row per corrected or excluded item (qa_id, split, task_type,
  errata_type, status, old_answer, new_answer_or_accepted, source=human_review_v0.9.7, note; since v0.9.8
  also new_locator); the notes are
  deterministic sentences (type, action, new locator) and the annotators' free-text memos are not released. The 54
  detector flags are kept beside the review labels.
- **Re-judging.** The 636 reported dev predictions of the four OpenAI models on the 79 items whose gold
  changed (gold_accept_any 74, gold_replaced 5; closed-book, BM25, full context) were judged again by both
  judges with the v0.9.2 judge settings and the corrected gold (`results/judge_verdicts_v0.9.7/`; Claude
  batch msgbatch_01NoLXXdz2U3N41TTWrpfBtj for 635 requests and one direct call for the request that batch
  canceled; gpt-4.1-mini batch batch_6acc6b3780a881909a4bbcc950b1b212; 0 failures). The primary judge
  changed 70 verdicts (64 to correct, 6 to incorrect), the secondary 68 (58 and 10). Pooled accuracy under
  the primary judge (plain / cluster-weighted, %): gpt-4.1-mini closed-book 14.4 / 18.2, BM25 63.7 / 57.1,
  full context 83.1 / 70.0; gpt-5.4-mini 15.1 / 14.0, 61.7 / 54.9, 92.7 / 87.0; gpt-5.4-nano 7.8 / 9.8,
  51.7 / 43.4, 70.0 / 59.7; gpt-5.5 37.0 / 37.2, 66.0 / 59.1, 100.0 / 100.0. Against v0.9.6 the re-judge
  moves pooled plain accuracy by at most 1.1 points (cluster-weighted 3.4) and the 11 exclusions by at most
  0.2 points; test_public scores are unchanged (`scripts/v097/score_pooled_v097.py`). Evaluated dev items after this
  release: 1,523; dev items in the BM25 and full-context columns: 954 (1,523 minus the 447 items without a
  context bundle, 448 before one of them was excluded, and the unchanged 122 bundle exclusions); pooled n: closed-book 1,865, BM25
  1,293 (full-context samples unchanged). BM25 majority-page recall@5 after the exclusions: dev 75.05% on
  954 items (SH announcements 69.2% on 419, others 79.6% on 535), pooled 78.89% on 1,293, test_public 89.7%
  unchanged (before: 74.90 / 78.74).
- **Files.** `results/human_review_v0.9.7/{assignment.csv, annotator_labels.jsonl, adjudication.jsonl,
  seed.txt, prespec_dev_review_2026-10-12.md, INSTRUCTIONS_ko.md, README.md}`; `data/errata_v0.9.7.csv`;
  `data/v0.9.7/eval_exclusions.txt`; `results/judge_verdicts_v0.9.7/`; `scripts/v097/{export_dev_review.py,
  score_dev_review.py, locator_candidates.py, recall_v097.py, rejudge_v097.py, score_pooled_v097.py,
  multi_answer_bound_v097.py}`.

### Second judge-validation sample (`results/judge_validation_v0.9.7/`)
- **Sample.** 200 reported test_public predictions, 4 from each of 50 cells (eight models x closed-book,
  BM25, dense, full context; six models x k=50, open-region, oracle), seed 20261012, excluding the 2
  predictions that overlap the earlier 80-prediction sample; plus 16 auxiliary predictions whose answer
  string differs from the released one. Script: `scripts/v097/sample_judge_validation.py`.
- **Labels.** Two non-author annotators labeled all 216 independently (correct / incorrect / unsure) with
  model, setting and judge labels hidden; an answer that lists several values without committing to one
  counts as incorrect. Neither used unsure; raw agreement 99.5% (215/216) [97.4, 99.9], Cohen's kappa 0.991;
  the author adjudicated the one disagreement (in the auxiliary set).
- **Result (main 200).** Primary judge claude-sonnet-5-5 agrees with the adjudicated label on 200 of 200
  (Wilson 95% [98.1, 100.0]; kappa 1.000; 100.0% post-stratified to cell weights). Secondary judge
  gpt-4.1-mini: 198 of 200 (99.0% [96.4, 99.7]; kappa 0.980; 99.6% post-stratified); the two disagreements
  are one k=50 and one oracle prediction (one gpt-4.1-mini, one claude-haiku-5-5; both aggregation items).
  By setting, model and task family the primary judge agrees on every label; the secondary judge on 23/24
  for k=50 and oracle, 27/28 for gpt-4.1-mini and claude-haiku-5-5, 102/104 for aggregation items.
- **Panel on the 56 Anthropic predictions in the sample.** claude-sonnet-5-5, deepseek-v4.1-flash and
  gemma4:31b 56/56 (kappa 1.000); gpt-4.1-mini, kimi-k2.6 and mistral-large-3 55/56 (kappa 0.963).
- **Auxiliary 16.** Both judges 16/16.
- **Files.** `results/judge_validation_v0.9.7/{sample.csv, labels_a.csv, labels_b.csv, adjudication.csv,
  prespec_judge_validation_2026-10-12.md, INSTRUCTIONS_ko.md, README.md}` and `scripts/v097/score_judge_validation.py`. The earlier 80-prediction sample stays in
  `results/human_review_v0.9.3/`.

### Scripts
- `scripts/v097/`: export_dev_review.py, score_dev_review.py, locator_candidates.py, recall_v097.py,
  rejudge_v097.py, score_pooled_v097.py, multi_answer_bound_v097.py, sample_judge_validation.py,
  score_judge_validation.py (see
  `scripts/v097/README.md` for what each needs; only `rejudge_v097.py` submit/fetch call a model API).

## v0.9.6 — dense k=50 plus the announcement page on the 18 uncovered aggregation items (2026-10-12)

No change to the questions, answers, schema, splits, gold fixes, evaluation scope, or any number released in
v0.9.5. This release adds one pre-specified run.

### k=50 + announcement page (`results/judge_verdicts_v0.9.6/`, `results/predictions_v0.9.6/`)
- **Why.** At dense bge-m3 k=50, 18 of the 81 cross-source aggregation items have every matching table row in
  their 50 passages but no chunk of the announcement page that states the condition, and no model answers any
  of them correctly. All 18 come from two of the nine announcement-table pairs (LH 0000061086 x HUG and
  LH 0000061016 x HUG, 9 items each); the other 63 items already contain a chunk of their page.
- **Pre-specified.** The setting, models, caps, judges and the reported quantity were fixed in the paper's
  results registry before any generation call; the text is copied verbatim, with commit hashes and
  timestamps, to `results/judge_verdicts_v0.9.6/PRESPECIFICATION.md`.
- **Prompt.** Each item's exact k=50 prompt (same 50 bge-m3 passages, v0.9.2 chunker, same template) with the
  whole gold announcement page (4,490 or 4,936 characters) inserted as one more passage in reading order;
  nothing else changes. The page is added in full, as one passage, whereas the k=50 coverage rule counts a
  page as present when any one of its 1,200-character chunks is retrieved. `scripts/v096/build_prompts_k50page.py`
  rebuilds the 18 prompts and checks that removing the added block gives back the k=50 prompt exactly.
- **Run.** The six full-window models with their k=50 settings (minimax-m3 and glm-5.2 with reasoning on) and
  the same output caps; OpenAI and Anthropic through the Batch APIs, Ollama with three concurrent workers.
  108 of 108 answered; 0 empty, 0 at the cap, no retries.
- **Result (correct of 18, primary judge claude-sonnet-5-5; secondary gpt-4.1-mini in parentheses).**
  gpt-5.5 18 (18), minimax-m3 17 (17), glm-5.2 18 (16), claude-sonnet-5-5 15 (14), claude-haiku-5-5 7 (6),
  gpt-4.1-mini 1 (1). On the same 18 items every model scores 0 at k=50, and open-region gives 18, 18, 17, 17,
  7 and 2. The four panel judges give claude-sonnet-5-5 14 to 15 and claude-haiku-5-5 6 to 7. Because the 18
  items come from only two announcements, the effect of the missing page cannot be separated from these two
  announcements, and no interval is reported. `scripts/v096/score_k50page.py` reproduces every count from the
  released verdicts.
- **Model answers.** The 108 final answers, the exact strings the primary judge scored, in
  `results/predictions_v0.9.6/` with the v0.9.5 format, terms and masking rules; no span or phone number
  needed masking (0 and 0). Reasoning traces and prompts are not included.

## v0.9.5 — model answers released (2026-10-12)

No change to the questions, answers, schema, splits, gold fixes, evaluation scope, verdicts, or any reported
number of v0.9.4.

### Model answers (`results/predictions_v0.9.5/`)
- **What.** The final answer text of every judged prediction behind the reported results: 24,074 model
  answers (test_public 12,797, dev 11,277) in 85 JSONL files that mirror the released verdict files one to
  one (`MANIFEST.csv`). Each line is `{qa_id, split, model, setting, prediction, judge_label,
  judge_label_secondary}` with the released primary (claude-sonnet-5-5) and secondary (gpt-4.1-mini)
  verdicts. Covered: the main runs of the eight models, the closed-book leak-fix re-runs, the gpt-5.5
  empty-answer retries, the glm-5.2 reasoning-on runs, the open-region and oracle contexts, dense k=50
  (seven rows, including the minimax-m3 run without reasoning), the second and third full-context runs of
  Section S8 (secondary judge only), the dev runs behind the pooled tables, and the 80 judge-validation
  predictions. The 74 predictions of the round-3 human review are among the Anthropic files.
- **Exact strings.** Each answer is the string the judge scored, after re-runs; `scripts/v095/` rebuilds the
  files from the judge inputs and checks that every file has the same qa_id set as its verdict file.
- **Excluded.** Reasoning traces (4.6% of them copy 200 or more characters of bundle text), the model input prompts (which contain bundle text), bundle
  text, provider logs, and the unreported qwen3.5 runs.
- **Masking.** A span is replaced by `[source text omitted, N chars]` when, after removing whitespace, a
  maximal run of overlapping 20-character windows that all occur in the item's bundle text covers 200 or more
  characters: 1 answer (573 characters). A phone-number-shaped string that occurs in no bundle text is
  replaced by `[phone number omitted]`: 6 distinct numbers in 6 answers. After masking, the longest bundle
  overlap in any answer is 162 characters, and no mobile number, e-mail address, resident registration number
  or labelled personal name remains.
- **Terms.** The model answers are not covered by the CC BY 4.0 license of the annotations and remain
  subject to each model provider's terms of use (LICENSE §3; `results/predictions_v0.9.5/README.md`). They
  are released for reproducing and re-judging the evaluation; do not use them to train models that compete
  with those providers' products.

## v0.9.4 — dense retrieval at k=50 on the aggregation set, recall rule, disclosures (2026-10-12)

No change to the questions, answers, schema, splits, gold fixes, or evaluation scope of v0.9.3 (1,876 items:
dev 1,534 / test_public 342; legal family and the 12 items of `data/v0.9.3/eval_exclusions.txt` excluded).
Every number below can be recomputed from released files with the scripts in `scripts/v094/`.

### Dense bge-m3 retrieval at k=50 on the 81 aggregation items (`results/judge_verdicts_v0.9.4/`)
- **Setting, fixed before any generation call.** The six full-window models (gpt-5.5, glm-5.2, minimax-m3,
  claude-sonnet-5-5, claude-haiku-5-5, gpt-4.1-mini) read the 50 bge-m3 passages of the item's 512k bundle,
  with the chunker (v0.9.2 page markers, `KRH_LEGACY_PAGE_MARKERS=1`), prompt builder, passage order and
  template of the reported dense top-5 runs; only k changed. Rebuilding k=5 with the same code reproduces the
  stored dense prompts 81/81. Output caps were raised before the run (gpt-5.5 16,000; Anthropic models and
  glm-5.2 16,384; minimax-m3 32,768) with the single-retry rule of v0.9.3 as a fallback. Ollama `num_ctx` was
  131,072 (the reported runs used 32,768, which cannot hold these prompts).
- **Decision rule, fixed before any generation call.** d = accuracy at k=50 minus full-context (512k)
  accuracy on the same 81 items under the primary judge, with a 95% bootstrap over the 9
  announcement–table pairs (10,000 resamples, seed 20261011): "exceeds" if the interval lies above 0,
  "below" if it lies below 0, otherwise "no detected difference".
- **Results (primary judge).** gpt-5.5 78% (63/81; full context 100%; d −22 [−56, 0]); glm-5.2 72%
  (88%; −16 [−43, +5]); minimax-m3 75% (68%; +7 [−25, +35]); claude-sonnet-5-5 69% (74%; −5 [−35, +20]);
  claude-haiku-5-5 21% (23%; −2 [−15, +11]); gpt-4.1-mini 12% (9%; +4 [−2, +11]). Every label is "no
  detected difference"; the gpt-5.5 interval reaches 0. The 50 passages hold the announcement page and every
  matched row for 63 items; in the other 18 every matched row is present but the announcement page is
  missing, and no model answers any of those 18 correctly. Per-item coverage:
  `results/retrieval_v0.9.4/k50_coverage_agg81.jsonl`. The HUG table spans 27 passages, so k=50 holds
  nearly all of it.
- **minimax-m3 reasoning mode.** Every reported minimax-m3 run reasoned: closed-book, BM25 and dense top-5
  under the flag "off" (traces on 389/389, 386/386, 386/386 calls) and full context and the v0.9.3
  shortened contexts under "on". With the same "off" flag and unchanged client code, the endpoint returned
  no reasoning on any of the 81 k=50 items (23%, "below"). A run with reasoning explicitly on is the reported
  row; the choice between the two runs was made after both were seen. Both are released
  (`k50dense_minimax-m3`, `k50dense_minimax-m3_reasoning-absent`).
- **Empty answers.** glm-5.2 returned 5 empty answers on the first pass (2 at the cap while reasoning, 3
  stopped under 500 tokens); the retry at 32,768 answered 3. Items 1891 and 1904 again stopped at about 300
  tokens, far below the cap, with the answer only in the reasoning trace; both are scored wrong. The glm-5.2
  label is the same under either treatment. All other models: 0 empty, 0 at the cap.
- **Judges.** Primary claude-sonnet-5-5 and secondary gpt-4.1-mini on all 7 rows; the four panel judges
  (deepseek-v4.1-flash, gemma4, kimi-k2.6, mistral-large-3) on the two Anthropic models. On this run the
  primary judge scores claude-sonnet-5-5 at 69% and the four panel judges at 63% to 68%.

### Retrieval recall rule (`scripts/v094/recall_majority_page.py`)
- Gold-page recall now assigns each retrieved passage to the one page that holds most of its characters; an
  item with two gold pages scores half for each page retrieved. The v0.9.3 text-matching figure counted a
  passage crossing a page boundary for both pages, which inflated SH recall.
- BM25 recall@5 on the evaluated items with their gold pages in the bundle: test_public 89.7% (unchanged),
  dev 74.9%, pooled dev + test 78.7%. This supersedes the v0.9.3 dev figure of 74.1% (text-matched, before the
  122 items and the 7 dev errors were excluded). The rule changes only SH items (dev 67.8%
  against 80.4% for the other dev items). Retrieved text and accuracy are unchanged.
- Accuracy on the 258 non-aggregation test_public items split by gold-page hit at k=5
  (`scripts/v094/hitmiss.py`, `results/retrieval_v0.9.4/nonagg_recall_test.csv`): with BM25, pooled over
  eight models, 91.7% on hit items against 32.3% on miss items; with bge-m3, 86.4% against 15.9%.

### Corrections and disclosures
- The 122 dev items of `data/v0.9.3/bundle_exclusions.txt` are items whose 512k bundle lacks at least one of
  their gold pages (60 lack every gold page, 62 lack one of two), not items with no gold page in the bundle.
- minimax-m3 full context (512k): 4 aggregation answers (0435, 0438, 0442, 1896) were empty at the
  16,384-token cap on the first call in July 2026; when the run resumed on 2026-07-10 they were called once
  more at the same cap, before the v0.9.3 retry rule existed. The scored answers are from that call; the
  primary judge marks all 4 correct. Without that call minimax-m3 would score 51 instead of 55 of the 81
  aggregation items.

## v0.9.3 — leak and page-marker fixes, more human labels, re-run verdicts (2026-10-11)

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
