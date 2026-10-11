# v0.9.2 human review of the evaluated test_public items

Three annotators reviewed all 347 test_public items in the v0.9.1 evaluation scope
(legal family excluded). Only labels are released here. Question, answer, evidence text and
free-text memos are not included because they can quote source documents.

## annotator_labels.jsonl

One row per (qa_id, annotator): 347 items x 3 annotators = 1,041 rows.

| field | values | meaning |
|---|---|---|
| `qa_id` | | item id in `data/qa_v0.6_test_public.jsonl` |
| `annotator` | `author`, `annotator2`, `annotator3` | `author` is the first author |
| `stratum` | `cloze_regenerated`, `script_generated` | construction path |
| `family` | task family | same as `task_type` |
| `q1_unambiguous` | yes / no / unsure | the question has one reading |
| `q2_evidence_supports` | yes / no / unsure | the cited evidence supports the gold answer |
| `q3_answer_correct_complete` | yes / no / unsure | the gold answer is correct and complete |
| `q4_natural` | yes / no / unsure | the question reads naturally |
| `error_label` | true / false | true if any of q1–q3 is "no" |

- "unsure" does not count as an error. q4 does not enter the error label.
- The author's labels for 118 items are the v0.9.1 sample audit (`results/human_audit/`).
  The author labelled the other 229 items in the v0.9.2 review.
- Errors per annotator: author 23, annotator2 29, annotator3 33.

## adjudication.jsonl

Every item with at least one error label (39 items) went to the author for a final decision.

| field | meaning |
|---|---|
| `qa_id` | item id |
| `n_flag` | number of annotators (1–3) whose `error_label` is true |
| `final_error` | `yes` / `no`, the adjudicated decision |

29 of the 39 items were confirmed as errors (29/347 = 8.4%). These 29 items are exactly
the 24 gold fixes and the 5 evaluation exclusions in `data/v0.9.2/gold_fixes.json`.
