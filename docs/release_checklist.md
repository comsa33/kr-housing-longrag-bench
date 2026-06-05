# v0.4 Release Checklist

Run before tagging any public release. All gate scripts must exit 0.

## 1. Automated gates

```bash
python3 scripts/validate_dataset.py                              # schema + source resolution
python3 scripts/verify_qa.py                                     # predicate recompute + grounding (CI gate)
python3 scripts/check_public_release_readiness.py --allow-dev    # dev/seed status report
python3 scripts/check_public_release_readiness.py                # strict: exits non-zero unless public-ready
```

- [ ] `validate_dataset.py` exits 0 (ids unique, sources resolve, no raw corpus fields).
- [ ] `verify_qa.py` exits 0 with `failed=0` on v0.2, v0.3, and v0.4.
- [ ] `check_public_release_readiness.py` reports the intended status (`public-ready` for a public tag).

## 2. Copyright / leakage (must be 0)

- [ ] No raw artifacts tracked: no `*.pdf`, `*.hwp`, `*.hwpx`, `*.html`, `*.csv` outside `workspace_local/`.
- [ ] No forbidden raw fields in public JSON (`raw_text`, `document_text`, `pdf_text`, `hwp_text`,
      `full_context`, …) — enforced by `validate_dataset.py` and the readiness gate.
- [ ] No secret value appears in any tracked file (readiness gate greps the live key values).
- [ ] `answer` ≤ 120 chars; every `gold_term` ≤ 40 chars (no long verbatim excerpts).
- [ ] `.gitignore` still excludes `workspace_local/{raw,processed,audit,secrets}/*`.

## 3. Benchmark validity

- [ ] ≥ 8 distinct official announcements cited; no single announcement > 20% of non-table QA.
- [ ] ≥ 700 verified QA (target 900+); families balanced per `docs/v0.4_public_plan.md`.
- [ ] Context tiers present: 32k / 64k / 128k / 256k / 512k; positions early / middle / late / multi.
- [ ] No duplicate questions.
- [ ] Human-review sample drawn and signed off (see `docs/v0.4_batch_report.md` §Human review).

## 4. Reproducibility

- [ ] `scripts/rebuild_v04_from_public_manifest.py --check` passes on a clean checkout (given keys).
- [ ] `docs/public_reconstruction.md` lists every fetched URL class and key requirement.
- [ ] Public target manifest `data/v0.4_announcement_targets_seed.jsonl` resolves to live official URLs.

## 5. Honesty

- [ ] Report labels the batch correctly: `dev/seed`, `v0.4-dev expanded`, or `v0.4-public ready`.
- [ ] Known limitations stated (extraction noise, single-provider (LH only), statute effective-date vs
      announcement-year mismatch, table coverage = 6 자치구).
- [ ] No overclaiming: if any gate fails, the release is not called public-ready.
