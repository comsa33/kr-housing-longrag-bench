# results/human_audit/ — v0.9.1 human sample audit

`human_audit_v091.jsonl` has one line per audited item, 118 lines. The file has no timing field; that is
intentional.

**Sample.** `scripts/paper/build_audit_items.py` (seed 20261010) draws a stratified sample of 160
test_public items:
- all 42 `cross_document_legal_reasoning` items;
- 45 of the v0.8 cloze-regenerated items;
- 73 script-generated items, allocated by family.

The legal family is outside the v0.9.1 evaluation scope (see `data/errata_v0.9.1.csv`), so the release
holds verdicts for the other 118 items: 45 cloze-regenerated and 73 script-generated, out of 168 and 179
in the evaluated test_public.

**Judge and fields.** One author judged each item against its cited evidence on four checks:
- `q1_unambiguous`: the question is unambiguous;
- `q2_evidence_supports`: the evidence supports the gold answer;
- `q3_answer_correct_complete`: the gold answer is correct and complete;
- `q4_natural`: the question reads naturally.

Each check is `yes`, `no` or `unsure`. `issue_types_ko` and `memo_ko` are the annotator's notes, in Korean.

**Error rule.** An item counts as an error when any of q1–q3 is `no`. `unsure` answers bound the estimate.
`scripts/paper/audit_summary.py` reports per-stratum Wilson intervals and the stratum-weighted rate for
the 347 evaluated test_public items.

**Reproduce from a public clone.**

```bash
python3 scripts/paper/build_audit_items.py . /tmp/audit_items.json --ids-only
python3 scripts/paper/audit_summary.py /tmp/audit_items.json results/human_audit/human_audit_v091.jsonl
```

`--ids-only` draws the same sample without source text. The full mode also attaches page, table and
statute evidence from the internal corpus, which is not redistributed.

**Result.**

| Scope | Errors | Rate | Wilson 95% |
|---|---|---|---|
| Cloze-regenerated | 0/45 | 0.0% | [0.0, 7.9] |
| Script-generated | 1/73 | 1.4% | [0.2, 7.4] |
| All | 1/118 | 0.8% | [0.1, 4.6] |

- Weighted over the 347 evaluated test_public items, the rate is 0.7% when the one `unsure` item counts as
  correct and 1.4% when it counts as an error.
- Both flagged items are listed in `data/errata_v0.9.1.csv`:
  - `krhlrb_v05_0772`: the gold answer is incomplete;
  - `krhlrb_v05_0361`: the question is ambiguous.
