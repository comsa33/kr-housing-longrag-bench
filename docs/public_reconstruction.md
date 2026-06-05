# Public Reconstruction Guide (v0.4)

KR-Housing-LongRAG-Bench releases **QA labels, evidence locators, predicates, source URLs, and
reconstruction code** — not raw third-party documents, row dumps, or long-context bundle text. To
*run* the benchmark (full-context vs RAG vs table/tool), an external user rebuilds the internal
context locally from official sources. This guide explains exactly what is fetched, where local keys
are needed, what stays internal, and how to validate the rebuild.

## What ships publicly

| Released (in this repo) | Not released (rebuilt locally into `workspace_local/`) |
|---|---|
| `data/qa_v0.4_candidates.jsonl` (questions, short answers, locators, predicates) | Raw LH PDF/HWP, MOLIT/HUG row dumps, OCR/extracted page text |
| `data/v0.4_announcement_targets_seed.jsonl` (official LH page URLs) | `workspace_local/processed/lh-sale-announcements-v04/**` page text + facts |
| `data/source_manifest.jsonl`, `data/task_schema.json` | `workspace_local/processed/bundles-v04/**` context bundle text |
| `scripts/**` (acquisition, extraction, bundle, verify, reconstruction) | `workspace_local/secrets/**` API keys |

`workspace_local/` is gitignored end-to-end (`raw/`, `processed/`, `audit/`, `secrets/`).

## Prerequisites

- Python 3.10+, and `pip install tiktoken olefile pymupdf pypdf pandas beautifulsoup4 lxml openpyxl`.
- `pdftotext` (poppler) on PATH — used for LH announcement extraction.
- Local API keys placed in `workspace_local/secrets/`:
  - `data_go_kr.key` — a [data.go.kr](https://www.data.go.kr) open-API serviceKey
    (MOLIT 아파트 매매 실거래가 상세, dataset id `15057511`). The open-API key works without IP restriction.
  - `hug_api.key` — a HUG 분양보증 분양이력 API key.
  These are **yours**; the project never distributes keys. Without them, the LH-only families still
  reconstruct, but table/cross-source families cannot.

## One-command rebuild

```bash
python3 scripts/rebuild_v04_from_public_manifest.py --check     # verify preconditions (no fetch)
python3 scripts/rebuild_v04_from_public_manifest.py --steps all # full local rebuild
```

The driver runs these steps in order (each is an independent script you can run directly):

| Step | Script | Fetches from | Output (internal) |
|---|---|---|---|
| `acquire_lh` | `acquire_lh_announcements_from_manifest.py` | official LH pages in the target manifest | `workspace_local/raw/lh-sale-announcements-v04/**` |
| `extract_lh` | `extract_lh_announcements_v04.py` | (local PDFs) | `…/processed/lh-sale-announcements-v04/**`, `audit/index_lh_v04.json` |
| `acquire_molit` | `acquire_molit_apt_trade_detail_rows.py` | data.go.kr (your key) | `…/processed/molit-apt-trade-detail/rows_v0.3.jsonl` |
| `acquire_hug` | `acquire_hug_sale_history_rows.py` | HUG API (your key) | `…/processed/hug-sale-history/rows_v0.3.jsonl` |
| `indexes` | `build_v03_indexes.py` | (local) | `audit/index_{molit,hug,lh}.json` |
| `bundles` | `build_bundles_v04.py` | (local) | `…/processed/bundles-v04/**` + `manifest.jsonl` |
| `validate` | `validate_dataset.py` | (local) | exit 0 on success |
| `verify` | `verify_qa.py` | (local) | `audit/verification_report_v04.json` |
| `readiness` | `check_public_release_readiness.py --allow-dev` | (local) | release status |

## Mapping a QA item to its context

Each QA item carries the locators needed to rebuild its evidence deterministically:

- `gold_predicate` — for `table_numeric_reasoning` / `cross_source_aggregation` / `format_robustness` /
  `answerability_detection`: a structured `{source, filter, op, field?}` recomputed against the rebuilt
  MOLIT/HUG rows by `scripts/qa_v03_common.recompute()`. The same function both produced and verifies
  the gold answer, so the number is correct by construction and independently re-checkable.
- `page_ids` — for LH families: page identifiers `lh-<announcement>-pNNN` resolving to
  `workspace_local/processed/lh-sale-announcements-v04/<announcement>/document_pages.jsonl`.
- `row_ids` — sampled MOLIT/HUG `_row_id`s inside the predicate's matching set.
- `bundle_id` + `context_tier` + `evidence_position` — the long-context bundle (under
  `workspace_local/processed/bundles-v04/`) and where the evidence sits (`early`/`middle`/`late`/`multi`).

## Running the experiments

With the rebuild complete you have, per QA item: the question, the gold answer, the exact context
bundle file, and the evidence position. Suggested baselines (see `docs/evaluation_protocol.md`):
full-context at 32k/64k/128k/256k/512k, BM25 / dense / hybrid / hierarchical RAG, and a table/tool
pipeline that executes `gold_predicate`-style queries against the rebuilt rows.

## v0.5 additions

`data/qa_v0.5_candidates.jsonl` (902 QA) supersedes v0.4 and adds table-cell-grounded QA, new families
(eligibility/schedule/correction), and announcement-level splits (`dev`/`test_public`/`test_hidden`).
After the steps above, also run:

```bash
python3 scripts/extract_table_cells_v05.py      # PyMuPDF table cells -> workspace_local (internal)
python3 scripts/build_qa_v05_det.py             # new cell/eligibility/schedule/correction QA
python3 scripts/assemble_qa_v05.py              # -> data/qa_v0.5_candidates.jsonl (+ split assignment)
python3 scripts/verify_qa.py                     # includes v0.5 checks + split-leakage
```

A v0.5 QA item adds `provider`, `region_sido`, `region_sigungu`, `housing_type`, `split`, and (for
cell-grounded items) `table_ids` / `cell_ids` resolving to
`workspace_local/processed/lh-sale-announcements-v04/<announcement>/table_cells.jsonl`. v0.5 reuses the
v0.4 context bundles (same 10-announcement corpus). The v0.5 source/provider backlog (for diversity
expansion) is `data/v0.5_announcement_targets.jsonl`.

## Copyright posture

Korean statutes/rules/official notices are non-protected works (Copyright Act Art. 7). Public-data
entries used here are marked `이용허락범위 제한 없음`. LH 입주자모집공고 are official public-agency
notices; the project still keeps their raw files internal and releases only URLs + locators + short
answers. Do not redistribute the rebuilt raw files. See `docs/source_selection_and_license_audit.md`.
