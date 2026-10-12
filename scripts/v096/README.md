# scripts/v096 — k=50 + announcement page (pre-specified run)

- `build_prompts_k50page.py` (build machine): rebuilds the 18 prompts from the stored k=50 prompts and the
  rebuilt 512k bundles, and checks that removing the added page block gives back each k=50 prompt exactly.
- `write_release_k50page.py` (build machine): writes `results/judge_verdicts_v0.9.6/` and
  `results/predictions_v0.9.6/` from the archived judge inputs and batch outputs, with the v0.9.5 masking rules.
- `score_k50page.py` (released files only): per-model correct of 18 under the primary and secondary judges and
  the four panel judges, next to k=50 and open-region on the same 18 items.

Pre-specification document: `results/judge_verdicts_v0.9.6/PRESPECIFICATION.md`.
