# KR-Housing-LongRAG-Bench

[![CI](https://github.com/comsa33/kr-housing-longrag-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/comsa33/kr-housing-longrag-bench/actions/workflows/ci.yml)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20559127-blue.svg)](https://doi.org/10.5281/zenodo.20559127)

**A copyright-safe Korean long-context benchmark for testing whether full-context LLMs can replace or
complement RAG / table-tool pipelines** on real housing announcements (입주자모집공고), public
tabular data (MOLIT 실거래 / HUG 분양이력), and housing statutes.

- **What it is:** 1,997 verified QA over 41 official announcements (10 providers) + public tabular data +
  3 statutes, with evidence locators, deterministic predicates, answerability labels, and
  long-context-bundle references — **no raw PDFs/HWPs, no API keys**.
- **Current release:** `v0.9` (split consolidation + release-grade baselines; **1,997 QA**, on the v0.8
  LLM-triage repair build) — **public-ready seed benchmark, NOT leaderboard-ready** (see caveats below). v0.9
  merges the former `test_hidden` into `test_public` (389) and adds LLM-judge-scored baselines (§
  `docs/baseline_results.md`); the underlying v0.8 build regenerated all positional-cloze questions into natural
  source-grounded questions, fixes location/answer errors, and removes 14 unrepairable items; it supersedes
  earlier seed builds. See `CHANGELOG.md`.
- **v0.9.3 corrections and added labels:** a closed-book locator leak (64 count items showed as many row ids as the gold count; 4 ids embedded the gold date) is fixed in `scripts/run_llm_baseline.py`; page ids with Hangul (18 SH announcements) are now parsed by `scripts/build_rag_smoke.py`, which corrects dev gold-page recall (40.9% reported, 74.1% matched by text); 122 dev items whose 512k bundle lacks at least one of their gold pages are excluded from BM25, dense and full context (`data/v0.9.3/bundle_exclusions.txt`). Round-2 human labels (100 random dev items: 7 errors, 7.0% [3.4, 13.7], excluded from evaluation in `data/v0.9.3/eval_exclusions.txt`; independent labels on the 80 judge-validation predictions) and round-3 labels (74 Anthropic predictions on which six judges disagree) are in `results/human_review_v0.9.3/`. Re-run verdicts, two Anthropic models and a four-judge panel are in `results/judge_verdicts_v0.9.3/`. See CHANGELOG 0.9.3.
- **v0.9.5 model answers:** the final answer text of every judged prediction behind the reported results (24,074 model answers in `results/predictions_v0.9.5/`, mirroring the verdict files), so the evaluation can be re-judged. Reasoning traces, the model input prompts (which contain bundle text), bundle text and the unreported qwen3.5 runs are not included; 1 source-text span and 6 unverified phone numbers are masked. The model answers are **not** covered by CC BY 4.0 and remain subject to each model provider's terms; do not use them to train competing models. See CHANGELOG 0.9.5.
- **v0.9.4 additions:** dense bge-m3 retrieval with 50 passages on the 81 aggregation items for six models (verdicts in `results/judge_verdicts_v0.9.4/`, per-item coverage in `results/retrieval_v0.9.4/`), with the comparison rule fixed before any generation call; a gold-page recall rule that assigns each passage to one page (dev BM25 recall@5 74.9%, pooled 78.7%, test unchanged at 89.7%); and disclosures on the minimax-m3 reasoning flag and four July 2026 full-context re-calls. Questions, answers and evaluation scope are unchanged. Scripts: `scripts/v094/`. See CHANGELOG 0.9.4.
- **v0.9.2 human review and gold fixes:** three annotators reviewed all 347 evaluated `test_public` items; 29 have an error, 8.4% [5.9, 11.7] (Wilson 95%). This corrects the 0.8% figure of the v0.9.1 one-author sample audit: the same 118 items have 8 errors under the three-annotator review. 24 gold answers are corrected in `data/v0.9.2/gold_fixes.json` (questions unchanged; the QA files are byte-identical to v0.9.1) and 5 ill-posed items are excluded from evaluation (`data/v0.9.2/eval_exclusions.txt`). Evaluated: 1,883 items (dev 1,541 / test_public 342). Dev was not reviewed by people; 54 dev items carry unverified automatic flags and are still evaluated. Errata: `data/errata_v0.9.2.csv`. Primary judge `claude-sonnet-5-5`, secondary `gpt-4.1-mini`; verdicts in `results/judge_verdicts_v0.9.2/`, review labels in `results/human_review_v0.9.2/`.
- **v0.9.1 evaluation scope:** v0.9.1 evaluates 11 of 12 families; the legal family (`cross_document_legal_reasoning`, 109 items, 42 in `test_public`) is excluded because its gold answers follow the statute versions in the corpus (2015/2018), not the current statutes; see `data/errata_v0.9.1.csv`. The items stay in the data, and the QA files are unchanged. In scope: 1,888 items (dev 1,541 / test_public 347). A 118-item human sample audit of the evaluated `test_public` items is in `results/human_audit/` (1 error, 0.8% [0.1, 4.6]); per-item judge verdicts for every reported run are in `results/judge_verdicts/`.
- **Canonical v0.9 file:** `data/qa_v0.6_realistic_candidates.jsonl` (historical filename retained for
  compatibility). Splits: `data/qa_v0.6_dev.jsonl` (1,608),
  `data/qa_v0.6_test_public.jsonl` (389, answers included). v0.9 merged the former `test_hidden` (285) into
  `test_public`; `split_tags` mark the `ood_region` (116) / `ood_year` (50) generalization subsets.
- **Quickstart:** see [Quickstart / evaluation](#quickstart--evaluation) · **Stats:**
  [`docs/dataset_statistics.md`](docs/dataset_statistics.md) · **Baselines:**
  [`docs/baseline_results.md`](docs/baseline_results.md) · **License:** [`LICENSE`](LICENSE) ·
  **Cite:** [`CITATION.cff`](CITATION.cff)

This is a seed package, not a finished large-scale benchmark. It is structured so the dataset can grow into a paper-grade benchmark without redistributing copyrighted PDFs/HWPs.

## Current Release: v0.9 (split consolidation + baselines; 1,997 QA, on the v0.8 build)

**Canonical v0.9 set: `data/qa_v0.6_realistic_candidates.jsonl` — 1,997 verified QA**
(historical filename retained for compatibility) across 12 task families,
built over **41 official announcements** from 10 providers (LH, SH, GH, iH, JPDC, 부산도시공사,
광주광역시도시공사, 대구도시개발공사, 대전도시공사, 충북개발공사), plus MOLIT 실거래 / HUG 분양이력
tabular data and 3 housing statutes. It includes real table cell-grid QA, public-data predicate QA,
provider/region comparisons, eligibility/schedule items, answerability checks, and announcement-level
splits (`dev`/`test_public`) with announcement-level leakage verified at 0.
(`data/qa_v0.5_candidates.jsonl` is the pre-realism input build — same qa_ids/answers.)

The v0.8 LLM-triage repair build regenerated all positional-cloze ("X 다음 값" / [위치 탐침]) questions into
natural source-grounded questions or removed them (cloze-phrased 34% → ~0%; `question_style` now ∈
real_user/professional_analyst, real_user+analyst 100%), and fixed location/answer errors — on top of prior
quality passes that materialize **multi-provider** long-context bundles (32k–512k), clusters parametric
near-duplicates (1,997 → 282 clusters) for cluster-weighted scoring, and defines a release split policy.
Public release splits: `data/qa_v0.6_dev.jsonl` (1,608) and `data/qa_v0.6_test_public.jsonl` (389, answers
included); v0.9 merged the former `test_hidden` (285) into `test_public` (no sealed split — it was never a
leaderboard hidden set), retaining `ood_region`/`ood_year` subsets via `split_tags`.
The near-duplicate cluster structure is also released explicitly as
`data/cluster_map.jsonl` (one line per cluster: `cluster_id`, `task_type`,
`cluster_size`/`cluster_weight`, `released_member_count`, per-split counts, and
the member `qa_id`s; 282 clusters over the 1,997 items — counted by released
membership, 115 multi-item + 167 singleton). The same cluster fields are already
on every QA record, so the map is a convenience index for auditing the grouping
and reproducing cluster-weighted accuracy. `cluster_weight` = 1/`cluster_size`;
for three clusters `cluster_size` (a pre-release candidate-pool count) exceeds
`released_member_count`, so both are reported.
See `CHANGELOG.md` and `docs/dataset_statistics.md`.

**Scope claim — read carefully.** This is a **public-ready seed benchmark**. CI runs the public-safe gates
on every push/PR (`validate_dataset.py`, `check_public_release_readiness.py` → `public-ready`, realism +
surface scans, harness self-test, `py_compile`). The full grounding/recompute gate (`verify_qa.py`,
1,997/1,997) runs **locally** against the rebuilt internal corpus and self-skips on a clean checkout where
that corpus is absent. It is **not a leaderboard-ready or sealed-hidden benchmark**: v0.8 repairs came from an LLM triage (gpt-5.4) and LLM regeneration (Claude); no systematic item-level human review was recorded, there is no sealed hidden split (the former `test_hidden` was merged into the public test), question phrasing skews
analyst-style, and parametric near-duplicates exist (clustered for cluster-weighted scoring). For audit
and development, GitHub includes the canonical full-label file `data/qa_v0.6_realistic_candidates.jsonl`;
for public evaluation or Hugging Face loading, use the release split files (`dev`, `test_public`, all answers
included). No "perfect" or "hallucination-free"
claim is made — only what the gates verify.

To **run** the benchmark with full long-context bundles, reconstruct the internal context locally from
official URLs + your own API keys: `docs/public_reconstruction.md` and
`python3 scripts/rebuild_v04_from_public_manifest.py --check`.

**Legacy build artifacts** (`qa_seed`, `qa_v0.2`–`qa_v0.5` candidates and their build/verify scripts) are
**retained in place for reproducibility** — `validate_dataset.py` and `verify_qa.py` still validate every
prior version, and the v0.3–v0.5 helper modules are imported by the current verifier, so they are kept
rather than moved/deleted.

## Quickstart / evaluation

Scoring needs only the public files and the Python standard library (no third-party packages):

```bash
# build locator-only prompt inputs (public-safe; no document text)
python3 scripts/make_prompt.py                        # -> data/qa_v0.6_prompts.jsonl (legacy filename)

# score your predictions ({"qa_id","prediction"} JSONL); plain + cluster-weighted accuracy
python3 scripts/eval_harness.py --pred my_predictions.jsonl

# sanity: scorer/gold wiring and trivial baselines
python3 scripts/eval_harness.py --self-test
```

Full walkthrough (record fields, prediction format, dummy end-to-end example):
`docs/quickstart.md` (legacy filename, current public quickstart). Release-grade baseline results:
`docs/baseline_results.md`. Count tables: `docs/dataset_statistics.md`.

Optional developer setup with `uv`:

```bash
uv sync --extra dev
uv run pre-commit install
uv run pre-commit run --all-files
```

The `uv` environment is for development, Hugging Face smoke tests, and local hooks. Public scoring and
validation remain runnable with plain `python3`.

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

Canonical v0.9 release files (historical `v0.6` filenames retained for compatibility):

- `data/qa_v0.6_realistic_candidates.jsonl`: **canonical v0.9 full set** (1,997 QA; realism + cluster + bundle metadata)
- `data/qa_v0.6_dev.jsonl` (1,608) / `data/qa_v0.6_test_public.jsonl` (389): release splits, all answers included
  (v0.9 merged the former `test_hidden` into `test_public`; `split_tags` keep the `ood_region`/`ood_year` subsets)
- `data/qa_v0.6_prompts.jsonl`: locator-only prompt inputs (generated by `make_prompt.py`)
- `data/qa_v0.5_candidates.jsonl`: pre-realism input build (same qa_ids/answers)
- `data/v0.9.2/gold_fixes.json` / `data/v0.9.2/eval_exclusions.txt`: v0.9.2 gold fixes and the 5 items excluded from evaluation
- `data/errata_v0.9.3.csv` / `data/errata_v0.9.2.csv` / `data/errata_v0.9.1.csv`: per-item errata (v0.9.3 adds the round-2 dev confirmations, excluded from evaluation, and the 122 dev items without bundle evidence)
- `data/v0.9.3/eval_exclusions.txt` / `data/v0.9.3/bundle_exclusions.txt` / `data/v0.9.3/cb_locator_fix.jsonl`: v0.9.3 evaluation exclusions (5 test, 7 dev), bundle-setting exclusions and the closed-book locator fix list
- `data/source_manifest.jsonl`: source registry with access URL, license basis, and inclusion policy
- `data/task_schema.json`: JSON schema for QA examples

Scripts (scoring needs only the standard library):

- `scripts/make_prompt.py`: QA → locator-only prompt inputs (`--inline-context` for local full-context)
- `scripts/eval_harness.py`: score predictions; plain + cluster-weighted accuracy (`--self-test`)
- `scripts/validate_dataset.py` / `scripts/verify_qa.py`: schema + predicate-recompute/grounding gates
- `scripts/check_public_release_readiness.py` / `scripts/check_question_realism.py`: release gates

Docs:

- `docs/quickstart.md`: public quickstart (record fields, prediction format, end-to-end example)
- `docs/baseline_protocol.md`: evidence-access regimes (closed-book / RAG / full-context), the human-validated LLM-judge headline metric, and trivial baselines
- `docs/baseline_results.md`: release-grade baseline results
- `docs/dataset_statistics.md`: count tables (task/split/style/provider/region/bundle/cluster)
- `docs/public_reconstruction.md`: rebuild the internal corpus from official sources

## Recommended Paper Baselines

See `docs/baseline_results.md` for the current release-grade baseline results and
`docs/baseline_protocol.md` for the historical full-context vs RAG vs table/tool protocol. For new
experiments, report at least these system families:

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

DOI state: the **v0.9.5 versioned DOI is `10.5281/zenodo.TBD`** (minted on release); the v0.9.4 versioned DOI is `10.5281/zenodo.23300582` (Zenodo, 2026-10-12); the v0.9.3 versioned DOI is `10.5281/zenodo.23298455` (Zenodo, 2026-10-11); the v0.9.2 versioned DOI is `10.5281/zenodo.23291297` (Zenodo, 2026-10-11); the v0.9.1 versioned DOI is `10.5281/zenodo.23282680` (Zenodo, 2026-10-10); the v0.9 versioned DOI is `10.5281/zenodo.20640480` (2026-06-11); the **concept DOI
`10.5281/zenodo.20559127`** always resolves to the latest version. Prior versioned DOIs:
**v0.8 `10.5281/zenodo.20571211`**, **v0.7 `10.5281/zenodo.20570856`**, **v0.6.3 dataset build
`10.5281/zenodo.20563604`**.

The machine-readable citation metadata is also available in [`CITATION.cff`](CITATION.cff). GitHub's
"Cite this repository" button uses that file automatically.
