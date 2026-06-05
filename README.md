# KR-Housing-LongRAG-Bench

[![CI](https://github.com/comsa33/kr-housing-longrag-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/comsa33/kr-housing-longrag-bench/actions/workflows/ci.yml)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)

**A copyright-safe Korean long-context benchmark for testing whether full-context LLMs can replace or
complement RAG / table-tool pipelines** on real housing announcements (입주자모집공고), public
tabular data (MOLIT 실거래 / HUG 분양이력), and housing statutes.

- **What it is:** 2,011 verified QA over 41 official announcements (10 providers) + public tabular data +
  3 statutes, with evidence locators, deterministic predicates, answerability labels, and
  long-context-bundle references — **no raw PDFs/HWPs, no answers leaked, no API keys**.
- **Current version:** `v0.6` — **public-ready seed benchmark, NOT leaderboard-ready** (see caveats below).
- **Canonical file:** `data/qa_v0.6_realistic_candidates.jsonl`. Splits: `data/qa_v0.6_dev.jsonl` (1,618),
  `data/qa_v0.6_test_public.jsonl` (105), `data/qa_v0.6_test_hidden_questions.jsonl` (288, answers masked).
- **Quickstart:** [`docs/quickstart_v06.md`](docs/quickstart_v06.md) · **Stats:**
  [`docs/dataset_statistics_v06.md`](docs/dataset_statistics_v06.md) · **Baselines:**
  [`docs/baseline_protocol_v06.md`](docs/baseline_protocol_v06.md) · **License:** [`LICENSE`](LICENSE) ·
  **Cite:** [`CITATION.cff`](CITATION.cff)

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

**Scope claim — read carefully.** This is a **public-ready seed benchmark**. CI runs the public-safe gates
on every push/PR (`validate_dataset.py`, `check_public_release_readiness.py` → `public-ready`, realism +
surface scans, harness self-test, `py_compile`). The full grounding/recompute gate (`verify_qa.py`,
2,011/2,011) runs **locally** against the rebuilt internal corpus and self-skips on a clean checkout where
that corpus is absent. It is **not a leaderboard-ready or sealed-hidden benchmark**: human-review verdicts
are still pending, the `test_hidden` answers are masked in the public file but present in-repo internally
(not served by a held-out harness), question phrasing skews analyst-style, and parametric near-duplicates
exist (clustered for cluster-weighted scoring). No "perfect" or "hallucination-free" claim is made — only
what the gates verify.

To **run** the benchmark with full long-context bundles, reconstruct the internal context locally from
official URLs + your own API keys: `docs/public_reconstruction.md` and
`python3 scripts/rebuild_v04_from_public_manifest.py --check`. Release gating: `docs/release_checklist.md`.

**Legacy build artifacts** (`qa_seed`, `qa_v0.2`–`qa_v0.5` candidates and their build/verify scripts) are
**retained in place for reproducibility** — `validate_dataset.py` and `verify_qa.py` still validate every
prior version, and the v0.3–v0.5 helper modules are imported by the current verifier, so they are kept
rather than moved/deleted.

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

## License

The benchmark **annotations** in this repository (QA labels, evidence locators, predicates, metadata, and
evaluation code) are released under **CC BY 4.0** — see [`LICENSE`](LICENSE). **Underlying source
materials** (announcements, public-data rows, statute text) remain governed by their own public-data,
public-work, or statutory status; do not redistribute raw third-party documents unless their license
permits it. Korean statutes/rules fall under the non-protected categories of Copyright Act Article 7.

## Citation

If you use this benchmark, cite the v0.6 seed release as:

```bibtex
@dataset{lee_kr_housing_longrag_bench_2026,
  author    = {Lee, Ruo},
  title     = {KR-Housing-LongRAG-Bench},
  year      = {2026},
  version   = {v0.6},
  publisher = {GitHub and Hugging Face},
  url       = {https://github.com/comsa33/kr-housing-longrag-bench},
  note      = {Public-ready seed benchmark for Korean housing long-context, RAG, and table reasoning evaluation}
}
```

The machine-readable citation metadata is also available in [`CITATION.cff`](CITATION.cff). GitHub's
"Cite this repository" button uses that file automatically.
