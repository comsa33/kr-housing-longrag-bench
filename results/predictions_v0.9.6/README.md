# Model answers, v0.9.6 (k=50 + announcement page)

The 108 final answers of the pre-specified run on the 18 aggregation items whose k=50 passages lack the
announcement page (six models x 18 items), one file per model, mirroring
`results/judge_verdicts_v0.9.6/{claude-sonnet-5-5,gpt-4.1-mini}/k50page_<model>.jsonl` (`MANIFEST.csv`).

- Line format, as in `predictions_v0.9.5/`: `{qa_id, split, model, setting, prediction, judge_label,
  judge_label_secondary}`; `judge_label` is the released primary-judge (claude-sonnet-5-5) verdict and
  `judge_label_secondary` the secondary-judge (gpt-4.1-mini) verdict.
- Each answer is the exact string the primary judge scored.
- Masking rules of v0.9.5 (a run of 200 or more characters shared with the item's bundle text after removing
  whitespace; phone numbers that occur in no bundle): nothing needed masking (0 spans, 0 numbers).
- Not included: reasoning traces, the model input prompts (which contain bundle text), bundle text, provider
  logs.

**Terms.** These model answers are not covered by the CC BY 4.0 license of the annotations and remain subject
to each model provider's terms of use (LICENSE §3). They are released for reproducing and re-judging the
evaluation; do not use them to train models that compete with the providers' models.
