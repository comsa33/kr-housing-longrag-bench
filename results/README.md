# results/ — per-item judge verdicts behind the reported numbers

- `judge_verdicts/<tag>.jsonl`: one line per item, `{"qa_id": ..., "judge_correct": true|false}`. This is
  the LLM-judge verdict for one (model, regime, item set) run. Predictions, judge outputs and prompts are
  not included.
- `judge_verdicts/MANIFEST.csv`: one row per tag, giving the model, the regime (`cb`, `bm25`, `dense`,
  `fc`, or a judge-panel re-score), the item set, `n`, and where the run is used. Rows marked `not used` are
  partial runs or superseded re-runs. They are kept so the record is complete.
- `judge_verdicts/human80_labels.jsonl`: the human Y/N label for each of the 80 predictions in the
  judge-validation sample. The key is `{qa_id}__{model}__{regime}`.
- `item_sets/agg81.jsonl`: the 81 cross-source-aggregation items (test_public, 512k tier).

## Reproduce the tables

All commands run from the repository root and read only this directory:

```bash
python3 scripts/score_judge.py --verdicts-dir results/judge_verdicts          # main table, by split and tier
python3 scripts/paper/paired_rq1.py --verdicts-dir results/judge_verdicts     # four regimes on the same items
python3 scripts/paper/tier_small_window.py --verdicts-dir results/judge_verdicts
python3 scripts/kappa_panel.py --verdicts-dir results/judge_verdicts          # judge agreement and panel
```

Without `--verdicts-dir`, the scripts read `workspace_local/audit/baselines/` if it exists (the build
machine) and fall back to `results/judge_verdicts/` otherwise.

`scripts/paper/evidence_check_agg81.py` also needs the 512k bundle text. That text is not redistributed;
rebuild it first (`docs/public_reconstruction.md`).

- `human_audit/`: v0.9.1 human sample audit (118 items) and how to reproduce its summary; see `human_audit/README.md`.
