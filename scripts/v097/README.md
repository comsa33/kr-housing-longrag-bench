# scripts/v097 — dev full review and second judge validation

No script here calls a model API except `rejudge_v097.py submit-*`/`fetch-*`.

| script | needs | does |
|---|---|---|
| `export_dev_review.py` | bundles and extracted pages (workspace_local/) | builds the review sheets and `assignment.csv` for the 1,534 dev items; checks the sheets |
| `score_dev_review.py` | sheets, assignment, adjudication | agreement, flags, adjudication template; writes `errata_v0.9.7.csv`, `eval_exclusions`, `results/human_review_v0.9.7/` |
| `locator_candidates.py` | extracted pages, bundle manifest | new evidence pages for the `locator_fixed` items by the pre-recorded rule |
| `recall_v097.py` | bundles, stored BM25 prompts | BM25 gold-page recall@5 after the review (wraps `scripts/v094/recall_majority_page.py`) |
| `sample_judge_validation.py` | released files | draws the 216-prediction judge-validation sample (seed 20261012) |
| `score_judge_validation.py` | released files and labels | scores the judges against the human labels (`results/judge_validation_v0.9.7/`) |
| `score_pooled_v097.py` | released files | pooled and dev accuracy of the four hosted models before and after the dev review (S3 tables) |
| `multi_answer_bound_v097.py` | released files | pooled accuracy lost if the accept-any items were scored against a single answer (S3) |
| `rejudge_v097.py` | released files; API keys for submit/fetch | re-judges the reported dev predictions of the gold-changed items with both judges |

Run `sample_judge_validation.py` and `score_judge_validation.py` from the repository root; the others take
paths as arguments (see each docstring).
