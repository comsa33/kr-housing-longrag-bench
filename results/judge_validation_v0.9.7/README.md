# Judge validation, round 2 (sample drawn 2026-10-12)

Second human check of the LLM judges on reported `test_public` predictions. The pre-specification
(`prespec_judge_validation_2026-10-12.md`) fixes the sample, the seed (20261012), the labelling rule, and the
reporting units before any label was collected.

- `sample.csv`: the 216 sampled predictions. Columns: `sample_id`, `stratum` (`main`: 50 model x setting cells
  x 4; `aux_string_mismatch`: 2 per model whose gold string is not in the prediction), `qa_id`, `model`,
  `setting`, `task_type`, `metric`, the primary (`claude-sonnet-5-5`) and secondary (`gpt-4.1-mini`) judge
  labels as released, and `reference_label` (the two annotators' label when they agree, otherwise the
  adjudicated label). The prediction texts are in `results/predictions_v0.9.5/`.
- `labels_a.csv`, `labels_b.csv`: independent labels of two non-author annotators (`correct` / `incorrect` /
  `unsure`), model names hidden and order shuffled. Free-text notes are not released.
- `adjudication.csv`: the rows on which the annotators differed, with the author's label.
- `INSTRUCTIONS_ko.md`: the annotator instructions (Korean).
- Scripts: `sample_judge_validation.py` (draw) and `score_judge_validation.py` (score).
