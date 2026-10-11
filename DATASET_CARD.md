# Dataset Card

## Dataset Name

KR-Housing-LongRAG-Bench seed

## Intended Use

This seed benchmark is designed for research on Korean long-context document understanding, table reasoning, and RAG-vs-full-context evaluation in public housing and administrative domains.

## Dataset Status

**v0.9.5: model answers.** The final answer text of every judged prediction behind the reported results is released in `results/predictions_v0.9.5/` (24,074 model answers, mirroring the verdict files) so the evaluation can be re-judged. Reasoning traces, the model input prompts (which contain bundle text), bundle text and the unreported qwen3.5 runs are excluded; 1 source-text span and 6 unverified phone numbers are masked. The model answers are not covered by CC BY 4.0; each model provider's terms apply, and they must not be used to train competing models. Nothing else changes.

**v0.9.4: dense retrieval at k=50 on the aggregation set and a recall rule.** Six models read 50 bge-m3 passages on the 81 aggregation items under a comparison rule fixed before any generation call; the 50 passages hold the announcement page and every matched row for 63 items, and no model answers any of the other 18 correctly (verdicts: `results/judge_verdicts_v0.9.4/`). Gold-page recall now assigns each retrieved passage to one page: BM25 recall@5 is 74.9% on dev and 78.7% pooled (test unchanged at 89.7%). The 122 dev items of v0.9.3 are those whose 512k bundle lacks at least one gold page. The minimax-m3 reasoning flag and four July 2026 full-context re-calls are disclosed in the changelog. Questions, answers and evaluation scope are unchanged.

**v0.9.3: corrections and added human labels.** A closed-book locator leak (68 items) and a page-marker bug for Hangul page ids are fixed; 122 dev items whose 512k bundle lacks at least one of their gold pages are excluded from the bundle settings; the two non-author annotators reviewed 100 random dev items (7 errors, 7.0% [3.4, 13.7]; the 7 are excluded from evaluation), labelled the 80 judge-validation predictions, and labelled the 74 Anthropic predictions on which six judges disagree. The v0.9.2 gold fixes and test scope are unchanged. Human naturalness labels (q4) of the v0.9.2 review: two or more of three annotators marked 52 of 347 test items as not reading naturally (51 script-generated); naturalness is not an error criterion.

**v0.9.2: full human review of the evaluated test set.** Three annotators (the first author and two native Korean speakers who are not domain experts) independently labelled all 347 evaluated `test_public` items; the author adjudicated the 39 items that any annotator flagged. 29 items have an error, 8.4% [5.9, 11.7] (Wilson 95%): script-generated 25/179 = 14.0% [9.6, 19.8], cloze-regenerated 4/168 = 2.4% [0.9, 6.0]. Agreement before adjudication: Fleiss κ 0.705. This corrects the v0.9.1 sample-audit figure below (0.8%, one author, 118 items): the same 118 items have 8 errors under the three-annotator review. 24 gold answers are corrected (`data/v0.9.2/gold_fixes.json`; 23 accept-any, 1 replaced) and 5 ill-posed items are excluded from evaluation but kept in the data. Evaluation scope: 1,883 items (dev 1,541 / test_public 342). `dev` was not reviewed by people; 54 dev items carry unverified automatic flags (`data/errata_v0.9.2.csv`) and are still evaluated. Labels: `results/human_review_v0.9.2/`. Primary judge `claude-sonnet-5-5` (98.8%, κ 0.975 against 80 human labels), secondary `gpt-4.1-mini`.

**v0.9.1 evaluates 11 of 12 families; the legal family is excluded (statute versions), see errata** (`data/errata_v0.9.1.csv`). The 109 `cross_document_legal_reasoning` items stay in the data; their gold answers follow the statute versions in the corpus (2015/2018), which differ from the current statutes for some items. Evaluation scope: 1,888 items (dev 1,541 / test_public 347). Human sample audit (118 evaluated `test_public` items, one author, four checks): 1 error, 0.8% [0.1, 4.6]; see `results/human_audit/`.

Release: `v0.9` (split consolidation + release-grade baselines; **1,997 QA**, on the v0.8 build). Lineage:
`v0.1-seed` → … → `v0.6` quality → `v0.7` research-preview → `v0.8` LLM-triage repair → **`v0.9` split
merge (test_hidden→test_public 389) + baselines**. The underlying v0.8 build is the
first build where QA content was substantively repaired: all positional-cloze (`"X 다음 값"` / `[위치 탐침]`)
questions were regenerated into natural source-grounded questions or removed, location mislabels and
confirmed wrong answers were fixed, and 14 unrepairable items removed (2,011 → 1,997). It **supersedes the
v0.6 build** — the v0.7 "v0.6 unchanged" description no longer applies. See `CHANGELOG.md` and
`docs/dataset_statistics.md`.

Canonical v0.6 files: `data/qa_v0.6_realistic_candidates.jsonl` (full set, realism + cluster + bundle
metadata) and the release splits `data/qa_v0.6_dev.jsonl` (1,608) / `data/qa_v0.6_test_public.jsonl` (389,
answers included). **v0.9: the former `test_hidden` split (285) was merged into `test_public`** — a larger
public held-out test (389) is more valuable than a sealed set we cannot serve; the merged items keep their
`split_tags` so the `ood_region` (116) and `ood_year` (50) subsets remain reportable. Scoring: `scripts/eval_harness.py`
(plain + cluster-weighted accuracy). `data/qa_v0.5_candidates.jsonl` is the pre-realism build (same
qa_ids/answers; input to the realism pass).

This build is a copyright-safe, multi-provider announcement set: **1,997 verified QA** across 12 task
families over 41 official announcements from 10 providers, MOLIT/HUG public tabular data, and 3 housing
statutes. It contains QA labels, evidence locators, predicates, page/cell ids, source URLs,
context-bundle references, and reconstruction code — **no raw documents, row dumps, API keys, or bundle
text**. Raw materials and API keys stay internal under `workspace_local/` (gitignored) and are rebuilt
locally.

Verification: `validate_dataset.py` = 0; `verify_qa.py` = 0 (1,997/1,997, split-leakage OK);
`check_public_release_readiness.py` = 0; realism + public-surface scans = 0. See `docs/v0.5_batch_report.md`
(source expansion) and `docs/v0.6_quality_report.md` (realism / bundles / splits).

Usage: `docs/quickstart.md` (load → build prompts → score → baselines), `docs/baseline_protocol.md`
(full-context vs RAG vs table/tool protocol), `docs/dataset_statistics_v06.md` (count tables). Scoring:
`python3 scripts/eval_harness.py --pred <predictions>.jsonl` (plain + cluster-weighted accuracy).

v0.7 research-preview release: the `v0.7` release adds a provider-agnostic **baseline runner**,
**full-context / RAG smoke docs**, **retrieval diagnostics**, and a **repository scope policy** (index:
`docs/baseline_results_v07.md`) on top of the **same v0.6 dataset build (2,011 QA, unchanged)**. Those are
**smoke-scale research-preview diagnostics, not release-grade benchmark tables** — not leaderboard-ready,
not human-validated, not sealed-hidden, not a final model ranking — and they do not change this dataset.
No raw source documents, full prompts, predictions, bundle text, hidden gold, provider logs, or keys are
published; those stay internal under `workspace_local/` (`docs/repository_scope_policy.md`). From v0.9.5 the final answer text of the reported runs is released in `results/predictions_v0.9.5/` under the providers' terms, not CC BY 4.0.

**Scope: public-ready seed benchmark, NOT leaderboard-ready.** The v0.8 LLM-triage repair build regenerated all
positional-cloze into natural questions (cloze 34% → 0%; real_user+analyst → 100%) and fixed location/answer
errors, on top of the v0.6 quality pass that materialized multi-provider long-context bundles and defined splits. Release files: `data/qa_v0.6_dev.jsonl` (1,608),
`data/qa_v0.6_test_public.jsonl` (389, answers included).

Split policy (v0.9): there is **no hidden split**. The earlier `test_hidden` (285) was **not a sealed
leaderboard set** (its policy already disclaimed that), so it was merged into `test_public` to give a
properly-sized public held-out test (389) — including 124 items at the 512k tier and the `ood_region` /
`ood_year` generalization subsets. A future release can re-carve a sealed hidden split from grown data if a
leaderboard is ever stood up; `scripts/make_v06_splits.py` still supports a `test_hidden` split when present.
Honest caveats: **v0.8 repairs came from an LLM triage (gpt-5.4) and LLM regeneration (Claude); no systematic item-level human review was recorded**; question phrasing is now natural (real_user 64%, real_user+analyst 100%, cloze ≈ 0%); parametric
near-duplicates exist but are clustered (1,997 QA → 282 clusters) and the eval harness reports
cluster-weighted accuracy so repetition does not inflate scores; some providers contribute few
announcements / no table cells. No "perfect" or "hallucination-free" claim is made.

## Data Sources

The seed source registry currently includes:

- LH public housing announcement source pages listed on the Public Data Portal
- LH third-new-town pre-subscription announcement source pages listed on the Public Data Portal
- HUG housing sale-history public API metadata
- MOLIT apartment official price CSV metadata
- Korean housing laws and rules available through the National Law Information Center
- Public-data and public-work license policy sources

## Annotation Method

QA items were generated by scripts from official source content (94%) or written by an LLM agent (6%), and v0.8 repairs came from an LLM triage (gpt-5.4) and LLM regeneration (Claude); see the paper's Section 3.2 and `construction/`. No systematic item-level human review was recorded during construction. After release, v0.9.2 added a three-annotator review of the 347 evaluated `test_public` items (labels only, `results/human_review_v0.9.2/`); `dev` has not been reviewed by people.

Recommended workflow for future expansion (step 5 has not been applied to the current release):

1. Select only sources with confirmed public-data/public-work permission.
2. Fetch source documents from official URLs during benchmark construction.
3. Build long source bundles from announcement, law/rule, and tabular public-data sources.
4. Create QA items with answer, evidence locator, answerability label, and required capabilities.
5. Verify each QA item by at least two annotators or by one annotator plus independent rule/table execution. (Done for the 347 evaluated `test_public` items in v0.9.2 with three annotators; not done for `dev`. Rule/table execution covers predicate-backed items only.)
6. Release source URLs and QA labels, not raw PDFs/HWPs, unless redistribution is clearly allowed.

## Known Limitations

- Source diversity is now substantially broader (10 providers, 9 announcement 시·도), but several new
  providers contribute only 1-3 announcements. Treat provider-generalization claims cautiously until more
  announcements are added per provider.
- Several source URLs point to portals or file-download pages rather than fixed local artifacts.
- Long-context bundles **are** materialized for evaluation, but only inside `workspace_local/`
  (internal, gitignored); they are rebuilt locally via `scripts/rebuild_v04_from_public_manifest.py`
  rather than redistributed.
- Statutes are captured at their v0.2 effective dates (2015/2018) while announcements are 2024–2026;
  cross-document items target provisions stable across those versions.
- Private finance, insurance, and construction-company materials are excluded until explicit permission
  is obtained.

## Responsible Use

Do not use this benchmark to provide legal, financial, or housing eligibility advice to real applicants. The benchmark is for model evaluation only.

## Citation

If you use this benchmark, cite the **v0.9.5 release** by its Zenodo versioned DOI (or use the concept DOI to
always cite the latest version):

```bibtex
@dataset{lee_kr_housing_longrag_bench_2026,
  author    = {Lee, Ruo},
  title     = {KR-Housing-LongRAG-Bench},
  year      = {2026},
  version   = {v0.9.5 (1,997 QA; model answers released)},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.TBD},
  url       = {https://doi.org/10.5281/zenodo.TBD},
  note      = {v0.9.5 keeps the 1,997 QA, questions, splits, gold fixes, evaluation scope, verdicts and every reported number of v0.9.4 and adds the model answers of every judged prediction (not covered by CC BY 4.0; provider terms apply).}
}
```

DOI state: the v0.9.5 versioned DOI is `10.5281/zenodo.TBD` (minted on release); the v0.9.4 versioned DOI is `10.5281/zenodo.23300582` (Zenodo, 2026-10-12); the v0.9.3 versioned DOI is `10.5281/zenodo.23298455` (Zenodo, 2026-10-11); the v0.9.2 versioned DOI is `10.5281/zenodo.23291297` (Zenodo, 2026-10-11); the v0.9.1 versioned DOI is `10.5281/zenodo.23282680` (Zenodo, 2026-10-10); the v0.9 versioned DOI is `10.5281/zenodo.20640480` (2026-06-11); the concept DOI
`10.5281/zenodo.20559127` always resolves to the latest version. Prior versioned DOIs: v0.8 `10.5281/zenodo.20571211`, v0.7 `10.5281/zenodo.20570856`,
v0.6.3 dataset build `10.5281/zenodo.20563604` (the v0.7 release reuses that v0.6 data).

Machine-readable citation metadata is provided in `CITATION.cff`.
