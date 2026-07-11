# archive/ — historical construction-time material

This directory holds material used to **build** KR-Housing-LongRAG-Bench during
development (v0.2–v0.6 authoring) that is **not needed to reproduce the released
benchmark or its evaluation**. It is kept for provenance and transparency, not
for reproduction. Nothing in the active reproduction or evaluation path imports
or invokes anything here (verified by import + subprocess closure and by the CI
checks).

Reproduction and evaluation live at the repository root:

- **Reconstruct the corpus:** `scripts/rebuild_v04_from_public_manifest.py`
  (drives `acquire_*`, `extract_lh_announcements_v04`, `build_v03_indexes`,
  `build_bundles_v04`).
- **Build bundles / prompts, run baselines, judge, score:**
  `scripts/build_bundles_v06.py`, `scripts/run_llm_baseline_v07.py`,
  `scripts/run_batch_baseline_v09.py`, `scripts/llm_judge_v09.py`,
  `scripts/score_judge_v09.py`, and the rest of `scripts/`.
- **Validate the release:** `scripts/validate_dataset.py`, `scripts/verify_qa.py`.

## Contents

- `scripts/` — one-off QA-authoring and dataset-construction tools: candidate
  assembly (`assemble_qa*`, `build_qa_*_det`, `build_qa_candidates`),
  agent-tightening (`tighten_agent_qa*`), authoring packets / target manifests
  (`build_v04_authoring_packets`, `build_v05_targets_manifest`), human-review
  sampling (`draw_human_review_sample*`), near-duplicate clustering
  (`compute_near_dup_clusters_v06`), split creation (`make_v06_splits`), and
  other construction utilities. Their **outputs** (QA labels, cluster metadata,
  splits) are already in the released `data/`, so they are not required to run
  or score the benchmark.
- `docs/` — development process reports and plans (v0.3/v0.4 acquisition status,
  batch reports, plans, annotation batch report).
- `prompts/` — internal corpus/QA build prompts.

To restore any file, `git mv` it back to its original location; the full history
is preserved.
