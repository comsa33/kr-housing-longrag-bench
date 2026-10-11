# v0.9.3 human labels (rounds 2 and 3)

The two non-author annotators of the v0.9.2 test review took part in two further rounds after the
v0.9.2 release. In every round they worked independently of each other and of the author, did not use
AI tools, and had up to one week. Only labels are released here. Questions, gold answers, evidence
text, model answers and free-text memos are not included because they quote source documents or
unreleased predictions.

## Round 2: 100 random dev items

`dev100_annotator_labels.jsonl` — one row per (qa_id, annotator): 100 items x 2 annotators. Fields as in
`results/human_review_v0.9.2/annotator_labels.jsonl` (`q1`–`q4`, `error_label` = any of q1–q3 is "no").
The items are a random sample (seed 20261011) of the in-scope dev items (legal family excluded).

`dev100_adjudication.jsonl` — the items with at least one error label (7). The author confirmed all 7
(`final_error`). Both annotators labelled the same 7 items as errors. Dev error estimate: 7/100 = 7.0%
(Wilson 95% [3.4, 13.7]). The 7 items are excluded from evaluation in every setting
(`excluded_from_evaluation` in `data/errata_v0.9.3.csv`; `data/v0.9.3/eval_exclusions.txt`); they stay in the
data with their gold unchanged.

## Round 2: independent labels on the 80 judge-validation predictions

`judge80_independent_labels.jsonl` — one row per (item, annotator); `item` is the key used in
`results/judge_verdicts/human80_labels.jsonl` (`{qa_id}__{model}__{regime}`), `label` is
correct / incorrect / unsure. The predictions come from four OpenAI models. On the 78 items both
annotators labelled (no unsure), they agree with each other and with the primary judge on all 78.

## Round 3: the 74 Anthropic predictions on which the judges disagree

`claude74_adjudication.jsonl` — one row per prediction: `qa_id`, `model`, `regime`, the two annotators'
labels, the author's label, the `final` label and its `source`. These are the 74 of the 2,722
claude-sonnet-5-5 / claude-haiku-5-5 predictions on which the six judges (primary, secondary and the four
panel judges) are not unanimous. Rule, fixed before any label was collected: if the two annotators agree
(correct/incorrect), that is the final label (`A2=A3`, 53); otherwise the author decides (`author`, 21).
Regimes `agg512k` reuse the full-context prediction for the 18 aggregation items of the full-context
sample, so those predictions appear under both `fc` and `agg512k`.
