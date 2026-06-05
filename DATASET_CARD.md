# Dataset Card

## Dataset Name

KR-Housing-LongRAG-Bench seed

## Intended Use

This seed benchmark is designed for research on Korean long-context document understanding, table reasoning, and RAG-vs-full-context evaluation in public housing and administrative domains.

## Dataset Status

Version: `v0.4-public` (seed lineage: `v0.1-seed` → `v0.2` → `v0.3-dev` → `v0.4-public`)

This version is a copyright-safe, multi-announcement build: **812 verified QA** over 10 official LH
입주자모집공고 + MOLIT/HUG public tabular data + 3 housing statutes. It contains QA labels, evidence
locators, predicates, source URLs, context-bundle references, and reconstruction code — **no raw source
documents, row dumps, or bundle text**. Raw materials and API keys are kept internal under
`workspace_local/` (gitignored) and rebuilt locally via `scripts/rebuild_v04_from_public_manifest.py`.

Verification: `validate_dataset.py`, `verify_qa.py` (812/812), and `check_public_release_readiness.py`
(public-ready) all pass; leakage scan = 0. Honest caveat: single provider (LH) and 3 시·도 — broadening
source diversity is the v0.5 priority. See `docs/v0.4_batch_report.md`.

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

- Source diversity: announcements are LH-only across 3 시·도 (broadening providers/regions is the
  v0.5 priority). Treat provider/region generalization claims cautiously.
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

