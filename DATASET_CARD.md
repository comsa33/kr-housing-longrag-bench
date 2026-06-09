# Dataset Card

## Dataset Name

KR-Housing-LongRAG-Bench seed

## Intended Use

This seed benchmark is designed for research on Korean long-context document understanding, table reasoning, and RAG-vs-full-context evaluation in public housing and administrative domains.

## Dataset Status

Release: `v0.8` (human-review repair build; **1,997 QA**). Lineage: `v0.1-seed` → … → `v0.6`
source-expansion → `v0.6` quality → `v0.7` research-preview → **`v0.8` human-review repair**. v0.8 is the
first build where QA content was substantively repaired: all positional-cloze (`"X 다음 값"` / `[위치 탐침]`)
questions were regenerated into natural source-grounded questions or removed, location mislabels and
confirmed wrong answers were fixed, and 14 unrepairable items removed (2,011 → 1,997). It **supersedes the
v0.6 build** — the v0.7 "v0.6 unchanged" description no longer applies. See `CHANGELOG.md` and
`docs/dataset_statistics_v08.md`.

Canonical v0.6 files: `data/qa_v0.6_realistic_candidates.jsonl` (full set, realism + cluster + bundle
metadata) and the release splits `data/qa_v0.6_dev.jsonl` / `data/qa_v0.6_test_public.jsonl` /
`data/qa_v0.6_test_hidden_questions.jsonl` (answers masked). Scoring: `scripts/eval_harness_v06.py`
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

Usage: `docs/quickstart_v06.md` (load → build prompts → score → baselines), `docs/baseline_protocol_v06.md`
(full-context vs RAG vs table/tool protocol), `docs/dataset_statistics_v06.md` (count tables). Scoring:
`python3 scripts/eval_harness_v06.py --pred <predictions>.jsonl` (plain + cluster-weighted accuracy).

v0.7 research-preview release: the `v0.7` release adds a provider-agnostic **baseline runner**,
**full-context / RAG smoke docs**, **retrieval diagnostics**, and a **repository scope policy** (index:
`docs/baseline_results_v07.md`) on top of the **same v0.6 dataset build (2,011 QA, unchanged)**. Those are
**smoke-scale research-preview diagnostics, not release-grade benchmark tables** — not leaderboard-ready,
not human-validated, not sealed-hidden, not a final model ranking — and they do not change this dataset.
No raw source documents, full prompts, predictions, bundle text, hidden gold, provider logs, or keys are
published; those stay internal under `workspace_local/` (`docs/repository_scope_policy.md`).

**Scope: public-ready seed benchmark, NOT leaderboard-ready.** The v0.8 human-review build regenerated all
positional-cloze into natural questions (cloze 34% → 0%; real_user+analyst → 100%) and fixed location/answer
errors, on top of the v0.6 quality pass that materialized multi-provider long-context bundles and defined splits. Release files: `data/qa_v0.6_dev.jsonl`,
`data/qa_v0.6_test_public.jsonl`, `data/qa_v0.6_test_hidden_questions.jsonl` (answers masked).

Hidden-split policy: the `test_hidden` split is **not a sealed leaderboard hidden set**. The release split
file masks answers, sets gold predicates to `null`, and leaves gold row ids empty. GitHub also includes a
canonical full-label file for audit/development, so a true leaderboard benchmark would need a separate
held-out harness. Honest caveats: v0.8 human review was **LLM-assisted (gpt-5.4 + Claude cross-model), not a full human
pass**; question phrasing is now natural (real_user 64%, real_user+analyst 100%, cloze ≈ 0%); parametric
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

The current QA labels were manually authored from official source metadata and legal/license policy pages. They are intended as seed examples and validation checks for the benchmark format, not as the final evaluation set.

For paper-grade expansion, use this workflow:

1. Select only sources with confirmed public-data/public-work permission.
2. Fetch source documents from official URLs during benchmark construction.
3. Build long source bundles from announcement, law/rule, and tabular public-data sources.
4. Create QA items with answer, evidence locator, answerability label, and required capabilities.
5. Verify each QA item by at least two annotators or by one annotator plus independent rule/table execution.
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

If you use this benchmark, cite the **v0.8 release**. The v0.8 versioned DOI is minted on the v0.8 Zenodo
release; until then use the concept DOI (always resolves to the latest version):

```bibtex
@dataset{lee_kr_housing_longrag_bench_2026,
  author    = {Lee, Ruo},
  title     = {KR-Housing-LongRAG-Bench},
  year      = {2026},
  version   = {v0.8 (human-review repair build; 1,997 QA)},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20559127},
  url       = {https://doi.org/10.5281/zenodo.20559127},
  note      = {v0.8 regenerates all positional-cloze questions into natural source-grounded questions and fixes location/answer errors; supersedes the v0.6/v0.7 builds. The v0.8 versioned DOI is minted on the v0.8 Zenodo release.}
}
```

DOI state: the concept DOI `10.5281/zenodo.20559127` always resolves to the latest version; the v0.8
versioned DOI is assigned on the v0.8 Zenodo release. Prior versioned DOIs: v0.7 `10.5281/zenodo.20570856`,
v0.6.3 dataset build `10.5281/zenodo.20563604` (the v0.7 release reuses that v0.6 data).

Machine-readable citation metadata is provided in `CITATION.cff`.
