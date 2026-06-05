# KR-Housing-LongRAG-Bench

Copyright-safe seed benchmark for evaluating whether long-context LLMs can replace or complement RAG on Korean real-world housing, public announcement, legal-rule, and tabular public-data tasks.

This is a seed package, not a finished large-scale benchmark. It is structured so the dataset can grow into a paper-grade benchmark without redistributing copyrighted PDFs/HWPs.

## Current build: v0.6 (2,011 QA)

**Canonical set: `data/qa_v0.6_realistic_candidates.jsonl` — 2,011 verified QA** across 13 task families,
built over **41 official announcements** from 10 providers (LH, SH, GH, iH, JPDC, 부산도시공사,
광주광역시도시공사, 대구도시개발공사, 대전도시공사, 충북개발공사), plus MOLIT 실거래 / HUG 분양이력
tabular data and 3 housing statutes. It includes real table cell-grid QA, public-data predicate QA,
provider/region comparisons, eligibility/schedule items, answerability checks, and announcement-level
splits (`dev`/`test_public`/`test_hidden`) with split leakage verified at 0.
(`data/qa_v0.5_candidates.jsonl` is the pre-realism input build — same qa_ids/answers.)

The v0.6 quality pass naturalizes question phrasing while keeping every answer/predicate/evidence
byte-identical to the verified source (cloze-phrased questions cut from 34% → ~8%; `question_style` ∈
real_user/professional_analyst/diagnostic_probe), materializes **multi-provider** long-context bundles
(32k–512k; 1,553 bundle-bearing QA, 961 non-LH), clusters parametric near-duplicates (2,011 → 286
clusters) for cluster-weighted scoring, and defines a release split policy. Release splits:
`data/qa_v0.6_dev.jsonl` (1,618), `data/qa_v0.6_test_public.jsonl` (105), and
`data/qa_v0.6_test_hidden_questions.jsonl` (288, answers masked; gold answers kept internal only).
See `docs/v0.6_quality_report.md` and `docs/dataset_statistics_v06.md`.

**Scope claim — read carefully.** This is a **public-ready seed benchmark** (automated gates pass:
`validate_dataset.py`, `verify_qa.py` 2,011/2,011, `check_public_release_readiness.py`, realism + surface
scans). It is **not a leaderboard-ready or sealed-hidden benchmark**: human-review verdicts are still
blank, the `test_hidden` answers are masked in the public file but present in-repo internally (not served
by a held-out harness), question phrasing skews analyst-style, and parametric near-duplicates exist. No
"perfect" or "hallucination-free" claim is made — only what the gates verify.

To **run** the benchmark, reconstruct the internal context locally from official URLs + your own API keys:
`docs/public_reconstruction.md` and `python3 scripts/rebuild_v04_from_public_manifest.py --check`. Release
gating: `docs/release_checklist.md`.

Earlier sets (`qa_seed`, `qa_v0.2`, `qa_v0.3`, `qa_v0.4` candidates) are retained for continuity.

## Quickstart / evaluation

Scoring needs only the public files and the Python standard library (no third-party packages):

```bash
# build locator-only prompt inputs (public-safe; no document text)
python3 scripts/make_prompt_v06.py                        # -> data/qa_v0.6_prompts.jsonl

# score your predictions ({"qa_id","prediction"} JSONL); plain + cluster-weighted accuracy
python3 scripts/eval_harness_v06.py --pred my_predictions.jsonl

# sanity: scorer/gold wiring (gold-as-prediction -> 100%) and trivial baselines
python3 scripts/eval_harness_v06.py --self-test
python3 scripts/run_baseline_stub_v06.py                  # oracle/dummy/random/echo (INTERNAL outputs)
```

Full walkthrough (record fields, prediction format, dummy end-to-end example):
`docs/quickstart_v06.md`. Full-context vs RAG vs table/tool protocol and trivial-baseline numbers:
`docs/baseline_protocol_v06.md`. Count tables: `docs/dataset_statistics_v06.md`.

## Research Framing

Main question:

> In Korean real-world housing and administrative document settings, can full long-context prompting replace retrieval, table tools, or hybrid RAG?

Target abilities:

- Long-context retrieval from housing announcements and rule documents
- Table and numeric reasoning over public housing price and sale-history data
- Cross-document aggregation across announcement, law, and public-data sources
- Answerability detection when the source bundle does not contain enough evidence
- Cost and latency comparison between full-context, RAG, and tool/table pipelines

## Copyright-Safe Scope

The current seed uses only:

- Public Data Portal entries marked with `이용허락범위 제한 없음`
- Korean statutes, rules, notices, and similar official texts that fall under the non-protected categories described in Korean Copyright Act Article 7
- Short factual metadata and QA labels authored for this benchmark

The current seed does not include:

- Raw PDF/HWP corpus files
- Private bank product descriptions
- Insurance clauses
- Private construction-company announcement PDFs
- Images, floor plans, brochures, or rendered design assets

Source documents should be fetched by users from the official URLs in `data/source_manifest.jsonl`.

## Internal Raw Corpus Handling

For annotation and verification, workers do need to inspect original documents.

Use `workspace_local/` for that work:

- `workspace_local/raw/`: downloaded official PDFs/HWPs/CSVs for internal inspection
- `workspace_local/processed/`: extracted text, OCR output, parsed tables, and chunk files
- `workspace_local/audit/`: per-source download logs, hashes, and license screenshots/notes

`workspace_local/` is intentionally excluded from release. Public benchmark releases should contain source URLs, QA labels, evidence locators, and evaluation code, not raw source documents, unless each raw document has explicit redistribution permission.

## Files

Canonical v0.6 data:

- `data/qa_v0.6_realistic_candidates.jsonl`: **canonical full set** (2,011 QA; realism + cluster + bundle metadata)
- `data/qa_v0.6_dev.jsonl` / `data/qa_v0.6_test_public.jsonl`: release splits with answers
- `data/qa_v0.6_test_hidden_questions.jsonl`: hidden split, answers masked (gold kept internal only)
- `data/qa_v0.6_prompts.jsonl`: locator-only prompt inputs (generated by `make_prompt_v06.py`)
- `data/qa_v0.5_candidates.jsonl`: pre-realism input build (same qa_ids/answers)
- `data/source_manifest.jsonl`: source registry with access URL, license basis, and inclusion policy
- `data/task_schema.json`: JSON schema for QA examples

Scripts (scoring needs only the standard library):

- `scripts/make_prompt_v06.py`: QA → locator-only prompt inputs (`--inline-context` for local full-context)
- `scripts/eval_harness_v06.py`: score predictions; plain + cluster-weighted accuracy (`--self-test`)
- `scripts/run_baseline_stub_v06.py`: trivial oracle/dummy/random/echo baselines (INTERNAL outputs)
- `scripts/validate_dataset.py` / `scripts/verify_qa.py`: schema + predicate-recompute/grounding gates
- `scripts/check_public_release_readiness.py` / `scripts/check_question_realism_v06.py`: release gates

Docs:

- `docs/quickstart_v06.md`: load → build prompts → score → baselines (with a runnable dummy example)
- `docs/baseline_protocol_v06.md`: full-context vs RAG vs table/tool evaluation protocol (draft)
- `docs/dataset_statistics_v06.md`: count tables (task/split/style/provider/region/bundle/cluster)
- `docs/v0.6_quality_report.md`: realism / bundles / splits / verification report
- `docs/release_checklist.md`: pre-tag gate checklist
- `docs/source_selection_and_license_audit.md`: license and source policy
- `prompts/worker_corpus_build_prompt.md`: worker prompt for acquisition/license/extraction/annotation

## Recommended Paper Baselines

See `docs/baseline_protocol_v06.md` for the full-context vs RAG vs table/tool protocol, the per-tier /
per-position reporting cuts, and the trivial-baseline floors. Evaluate at least these systems:

- Full-context prompting with 32K, 64K, 128K, 256K, and 512K budgets
- BM25 RAG
- Dense-vector RAG
- Hybrid RAG
- Hierarchical RAG
- Table/tool pipeline for CSV/API-backed sources
- Full-context plus retrieved evidence

## Dataset License

The benchmark annotations in this repository are intended for release under CC BY 4.0. Underlying source materials remain governed by their own public-data, public-work, or statutory status. Do not redistribute raw third-party documents unless their license permits it.
