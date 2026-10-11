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

## v0.9.2

- `judge_verdicts_v0.9.2/claude-sonnet-5-5/<tag>.jsonl`: primary-judge verdicts, same format as above, for
  the 36 runs used in v0.9.2 (test_public; dev added for the 12 GPT core runs). Only items in the v0.9.2
  scope are included (legal family and the 5 excluded items removed), judged against the v0.9.2 gold.
- `judge_verdicts_v0.9.2/gpt-4.1-mini/<tag>.jsonl`: secondary judge. These are the v0.9.1 verdicts, except
  for the 24 gold-fixed items, which were re-judged against the v0.9.2 gold.
- `judge_verdicts_v0.9.2/human80_claude-sonnet-5-5.jsonl`: Claude verdicts on the 80 human-labelled
  predictions (`claude_sonnet_5_5`, `human`).
- `human_review_v0.9.2/`: three-annotator labels for the 347 evaluated test_public items and the 39
  adjudication decisions; see `human_review_v0.9.2/README.md`.
- How the verdicts were produced: `scripts/judge_v092/README.md`.

Reproduce the v0.9.2 tables (all scoring scripts take the same three options; without them they give
the v0.9.1 numbers):

```bash
X="--exclude-family cross_document_legal_reasoning --exclude-ids data/v0.9.2/eval_exclusions.txt"
V=results/judge_verdicts_v0.9.2/claude-sonnet-5-5      # or .../gpt-4.1-mini
python3 scripts/score_judge.py $X --verdicts-dir $V                 # test_public, dev, pooled
python3 scripts/paper/paired_rq1.py $X --verdicts-dir $V            # four regimes on the same items
python3 scripts/paper/tier_small_window.py $X --verdicts-dir $V [--exclude-bundle mix_multiprovider_256k]
python3 scripts/paper/family_table.py $X --verdicts-dir $V --regime bm25 --min-n 1
python3 scripts/paper/scope_counts.py $X
python3 scripts/v092/score29.py                                     # the 29 fixed or excluded items
```

## v0.9.3

- `judge_verdicts_v0.9.3/{claude-sonnet-5-5,gpt-4.1-mini}/<tag>.jsonl`: verdicts for the v0.9.3 re-runs and the two
  Anthropic models, same format. `cbfix_*` are the closed-book items whose locator leaked the answer, re-run
  without the leaking fields; they replace those items in the v0.9.2 closed-book runs. `g55retry_cb_*` are the
  gpt-5.5 closed-book items that were empty at the 4,000-token cap, re-run once at 16,000; they replace those
  items. `thinkon_*` are glm-5.2 with reasoning on. `oracle_agg81_*` / `openregion_agg81_*` are the aggregation
  set with only the matching rows, or with every row of the item's year (HUG) or month (MOLIT), plus the
  announcement page. `agg512k_*` reuse the full-context prediction for the 18 aggregation items of the
  full-context sample.
- `judge_verdicts_v0.9.3/panel/`: gemma4:31b, kimi-k2.6, mistral-large-3:675b and deepseek-v4.1-flash on all
  Anthropic predictions; deepseek-v4.1-flash also on the 80 human-labelled predictions and on the
  aggregation-set full-context predictions of gpt-5.5, gpt-4.1-mini, glm-5.2 and minimax-m3.
- `judge_verdicts_v0.9.3/MANIFEST.csv`: judge, tag, model, regime, split, n for every file.
- `human_review_v0.9.3/`: round-2 and round-3 human labels; see its README.

```bash
python3 scripts/score_judge.py --exclude-family cross_document_legal_reasoning \
    --exclude-ids data/v0.9.3/eval_exclusions.txt --exclude-bundle-ids data/v0.9.3/bundle_exclusions.txt \
    --verdicts-dir results/judge_verdicts_v0.9.2/claude-sonnet-5-5
python3 scripts/v093/score_claude_human.py
```

## v0.9.4

- `judge_verdicts_v0.9.4/{claude-sonnet-5-5,gpt-4.1-mini}/k50dense_<model>.jsonl`: dense bge-m3 retrieval with
  50 passages on the 81 aggregation items, same format. `k50dense_minimax-m3` is the run with reasoning on (the
  reported row); `k50dense_minimax-m3_reasoning-absent` is the run with the reported flag (off), for which the
  endpoint returned no reasoning. See CHANGELOG 0.9.4.
- `judge_verdicts_v0.9.4/panel/`: the four panel judges on the two Anthropic models' k=50 predictions.
- `judge_verdicts_v0.9.4/MANIFEST.csv`: judge, tag, model, regime, split, n for every file.
- `retrieval_v0.9.4/k50_coverage_agg81.jsonl`: per item, whether the 50 passages hold the announcement page and
  how many of the matched rows they hold.
- `retrieval_v0.9.4/nonagg_recall_test.csv`: gold-page recall@k (k = 5, 10, 20, 50) of BM25, bge-m3 and their
  reciprocal-rank fusion for the 258 non-aggregation test_public items.

```bash
python3 scripts/v094/score_k50.py      # k=50 table: accuracy, pair-bootstrap intervals, d vs full context, labels
python3 scripts/v094/hitmiss.py        # accuracy by gold-page hit at k=5
```
