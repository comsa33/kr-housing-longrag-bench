# Release Checklist

Run before tagging any public release. All gate scripts must exit 0.

## 0. Release packaging (GitHub public package)

- [ ] `LICENSE` present: annotations under CC BY 4.0 + underlying-source-materials clause.
- [ ] `CITATION.cff` present and valid YAML (title / version / authors / license).
- [ ] `.github/workflows/ci.yml` present; runs the public-safe gates on push/PR and is green.
- [ ] `.gitignore` ignores all of `workspace_local/*` (incl. future subdirs like `tools/`) except the
      `.gitkeep` / `secrets/README.txt` placeholders.
- [ ] README first screen is external-user-oriented (what / version / canonical files / quickstart /
      eval / license / citation / caveats) and links the v0.6 docs.

## 1. Automated gates

Canonical v0.6 commands (the CI workflow runs these on a clean checkout):

```bash
python3 scripts/validate_dataset.py                                                      # schema + source resolution
python3 scripts/verify_qa.py --qa data/qa_v0.6_realistic_candidates.jsonl                # predicate recompute + grounding (deep pass needs local corpus)
python3 scripts/check_public_release_readiness.py --qa data/qa_v0.6_realistic_candidates.jsonl   # strict: public-ready or non-zero
python3 scripts/check_question_realism_v06.py --qa data/qa_v0.6_realistic_candidates.jsonl
python3 scripts/eval_harness_v06.py --self-test
python3 -m py_compile scripts/*.py
```

- [ ] `validate_dataset.py` exits 0 (ids unique, sources resolve, no raw corpus fields).
- [ ] `verify_qa.py` exits 0 with `failed=0` on v0.2–v0.5 + the v0.6 build **locally** (with the rebuilt
      internal corpus). On a clean checkout / CI it self-skips the deep grounding pass and exits 0.
- [ ] `check_public_release_readiness.py` reports the intended status (`public-ready` for a public tag);
      it tolerates an absent bundle manifest on a clean checkout (bundle_id resolution skipped, warned).

## 2. Copyright / leakage (must be 0)

- [ ] No raw artifacts tracked: no `*.pdf`, `*.hwp`, `*.hwpx`, `*.html`, `*.csv` outside `workspace_local/`.
- [ ] No forbidden raw fields in public JSON (`raw_text`, `document_text`, `pdf_text`, `hwp_text`,
      `full_context`, …) — enforced by `validate_dataset.py` and the readiness gate.
- [ ] No secret value appears in any tracked file (readiness gate greps the live key values).
- [ ] `answer` ≤ 120 chars; every `gold_term` ≤ 40 chars (no long verbatim excerpts).
- [ ] `.gitignore` still excludes `workspace_local/{raw,processed,audit,secrets}/*`.

## 3. Benchmark validity

- [ ] ≥ 8 distinct official announcements cited; no single announcement > 20% of non-table QA.
- [ ] ≥ 2,000 verified QA for a full public tag; families reviewed for over-reliance on cloze-style
      retrieval items.
- [ ] Context tiers present: 32k / 64k / 128k / 256k / 512k; positions early / middle / late / multi.
- [ ] No duplicate questions.
- [ ] Human-review sample drawn and signed off (see `docs/v0.4_batch_report.md` §Human review).

## 4. Reproducibility

- [ ] `scripts/rebuild_v04_from_public_manifest.py --check` passes on a clean checkout (given keys).
- [ ] `docs/public_reconstruction.md` lists every fetched URL class and key requirement.
- [ ] Public target manifest `data/v0.4_announcement_targets_seed.jsonl` resolves to live official URLs.

## 5. v0.5/v0.6-specific (announcement splits, providers, table cells)

- [ ] `verify_qa.py` v0.5 block passes (cell_ids/table_ids resolve; provider/region/split present).
- [ ] Split-leakage check passes: no announcement in more than one evaluation split.
- [ ] `check_public_release_readiness.py --qa data/qa_v0.5_candidates.jsonl` provider/region report
      reviewed; for a **public** tag it must reach 5+ providers, ≥8 announcement 시·도, and ≤60%
      single-provider share.
- [ ] Table cells are internal only (`workspace_local/.../table_cells.jsonl`); public QA carries only
      `table_ids`/`cell_ids` + short answers.
- [ ] `data/v0.5_announcement_targets.jsonl` backlog rows use official URLs or `needs_official_url`
      (no fabricated URLs).
- [ ] Hidden split policy is release-appropriate: if answers are included in-repo, label it as
      `test_hidden` metadata rather than a true hidden benchmark; for a leaderboard, publish questions
      only and keep answers private.

## 6. v0.6 quality (realism / clusters / harness / hidden split)

```bash
python3 scripts/check_question_realism_v06.py --qa data/qa_v0.6_realistic_candidates.jsonl
python3 scripts/eval_harness_v06.py --self-test        # scorer + gold wiring sanity (must be ~100%)
python3 scripts/verify_qa.py --qa data/qa_v0.6_realistic_candidates.jsonl
```

- [ ] Realism validator exits 0: 0 invariant changes vs source; cloze ≤ 15%; diagnostic_probe ≤ 20%;
      `question_style` present on every row.
- [ ] `eval_harness_v06.py --self-test` = 100% (per-metric scorer + gold/cluster wiring correct).
- [ ] `cluster_id`/`cluster_weight` present on every QA; report effective (cluster-weighted) size.
- [ ] Hidden split: `data/qa_v0.6_test_hidden_questions.jsonl` answers masked; gold only in
      `workspace_local/audit/qa_v0.6_test_hidden_answers.jsonl`; never label it human-validated.
- [ ] Human review: sample **prepared, verdict pending** — do NOT claim human-validated.
- [ ] `bundle_count` reported as `referenced-by-QA` vs `available` (no single ambiguous number).
- [ ] Canonical file naming per `docs/v0.6_quality_report.md` §8.

## 7. Honesty

- [ ] Report labels the batch correctly: `dev/seed`, `public-ready`, or `leaderboard-ready`.
- [ ] Known limitations stated (extraction noise, provider/source imbalance, statute effective-date vs
      announcement-year mismatch, near-duplicate parametric QA, human-review status).
- [ ] No overclaiming: if any gate fails, the release is not called public-ready.
