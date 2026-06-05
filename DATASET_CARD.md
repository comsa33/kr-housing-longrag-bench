# Dataset Card

## Dataset Name

KR-Housing-LongRAG-Bench seed

## Intended Use

This seed benchmark is designed for research on Korean long-context document understanding, table reasoning, and RAG-vs-full-context evaluation in public housing and administrative domains.

## Dataset Status

Version: `v0.6-source-expansion` (lineage: `v0.1-seed` → `v0.2` → `v0.3-dev` → `v0.4-public` → `v0.5-dev` → `v0.6`)

This build is a copyright-safe, multi-provider announcement set: **2,011 verified QA** across 13 task
families over 41 official announcements from 10 providers, MOLIT/HUG public tabular data, and 3 housing
statutes. It contains QA labels, evidence locators, predicates, page/cell ids, source URLs,
context-bundle references, and reconstruction code — **no raw documents, row dumps, API keys, or bundle
text**. Raw materials and API keys stay internal under `workspace_local/` (gitignored) and are rebuilt
locally.

Verification: `validate_dataset.py` = 0; `verify_qa.py` = 0 (v0.5 file, current v0.6 build: 2,011/2,011,
split-leakage OK); `check_public_release_readiness.py` = 0 (**public-ready**); public-surface leakage
scan = 0. Honest caveats: long-context cloze items are a large share of the set, near-duplicate
parametric QA pairs are warned but grounded, non-LH context bundles are not yet materialized, and
human-review sign-off is pending. See `docs/v0.5_batch_report.md`.

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
