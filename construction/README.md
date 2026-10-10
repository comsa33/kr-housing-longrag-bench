# construction/ — provenance only, not needed for reproduction

Nothing here is needed to load, run, or score the benchmark. The released labels are in `data/`, and the
scoring path is `scripts/` plus `results/`. This directory records how the QA items were built and
repaired, so readers can audit the process.

The scripts were run inside the original working tree and are kept as they were. Paths that pointed to
the author's machine now read `<repo>`. Several scripts read inputs that are not redistributed: raw
announcements, extracted text, context bundles, and the retired hidden-answer file. So most of them will
not run from a clean clone.

## Contents

| Path | What it is | Origin |
|---|---|---|
| `scripts/` | QA authoring and construction tools for v0.2–v0.6: candidate assembly, deterministic QA builders, agent-answer tightening, authoring packets, human-review sampling, near-duplicate clustering, split creation | `archive/scripts/` at commit `5f7cf93` (removed from the tree in `be18447`) |
| `docs/` | Development reports and plans for v0.3/v0.4 | `archive/docs/` at `5f7cf93` |
| `prompts/` | Corpus and QA build prompts given to coding agents during v0.3/v0.4 | `archive/prompts/` at `5f7cf93` |
| `v0.8_regeneration/` | v0.8 repair pass: LLM grounding triage, cloze regeneration, and the fixes applied | internal working directory, copied for this release |

## v0.8_regeneration/

**Scripts**

- `run_triage_v08.py`: the triage runner. Its system prompts are inline.
- `build_review_manifest.py`, `build_sample_manifest.py`: build the review inputs.
- `build_calibration_set.py`, `score_verdicts.py`: judge calibration on a planted-error set.
- `integrate_regen.py`, `integrate_finalize.py`, `apply_sweep_fixes.py`, `apply_hangdong_fix.py`: apply
  the repairs to `data/`.

**Verdict summaries**

Each record keeps only `{qa_id, verdict, issue}`. Evidence excerpts, model reasons, derived answers and
source text were removed.

| File | Content |
|---|---|
| `review_gpt5_v2.jsonl` | Pass 1, high-risk families: 230 items reviewed, 57 `FLAG` |
| `review_gpt5_sample.jsonl` | Pass 2, stratified sample of the remaining families: 145 items, 52 `FLAG` |
| `review_gpt5_hirisk.jsonl` | Earlier 15-item high-risk pilot: 7 `FLAG` |
| `confirmed_errors.jsonl` | 15 items confirmed as label errors. All 15 come from the pass-2 flags. `issue` = mismatch type and task family |
| `noncloze_actions.jsonl` | Actions on non-cloze items: 1 answer fixed (`krhlrb_v05_0910`), 13 removed |
| `regen_verify_gpt5.jsonl`, `regen_verify_gpt5_68.jsonl` | LLM verification of regenerated cloze items (618 and 68 items) |
| `regen_flagged.jsonl` | Regenerated items flagged by that verification (7) |

No item-level human verdicts were recorded for these passes. One author informally inspected files and
asked the LLM to re-check items that looked wrong; that is not a systematic review.

Not included, because they contain source text: review targets, worklists, regeneration inputs and
results, calibration inputs, and the review queue with evidence excerpts.
