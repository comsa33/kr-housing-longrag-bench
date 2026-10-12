# results/human_review_v0.9.7/ — full human review of the evaluated dev items

Every evaluated `dev` item (1,534 = 1,608 minus 67 legal items minus the 7 errors confirmed in v0.9.3) was
labelled by exactly two of four non-author annotators, independently and without AI tools. The author
adjudicated every item that at least one annotator marked as an error, and every item an annotator marked
unsure because of a sheet problem (122 items). The protocol was fixed before labelling:
`prespec_dev_review_2026-10-12.md` (in Korean; the annotator instructions are `INSTRUCTIONS_ko.md`).

- `assignment.csv`: `qa_id`, `block`, `annotator_a`, `annotator_b`, `stage`, `family`, `route`. 31 blocks of 50
  items (the last 34) rotate over the six annotator pairs (seed in `seed.txt`). Annotators are A to D.
  `stage` 1 marks the 964 items used by the BM25 and full-context columns (before this review's exclusions).
- `annotator_labels.jsonl`: one row per (item, annotator): `verdict` (`no_error` / `error` / `unsure`) and
  `type` for errors (`dual_row`, `header_parse`, `multiple_schedules`, `wrong_gold`, `scope`, `unspecified`,
  `other`). Free-text notes are not released.
- `adjudication.jsonl`: the 122 adjudicated items: `n_flag`, `final_error`, `final_type`, `action`
  (`gold_accept_any`, `gold_replaced`, `locator_fixed`, `excluded`) or `reason` when not an error.

Result: 120 errors in 1,534 items (7.8%, Wilson 95% [6.6, 9.3]). Corrections are listed item by item in
`data/errata_v0.9.7.csv`; the 11 items with an ill-posed question are added to
`data/v0.9.7/eval_exclusions.txt` and stay in the release. Scripts: `scripts/v097/`.
