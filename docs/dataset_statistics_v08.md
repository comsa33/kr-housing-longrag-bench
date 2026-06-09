# Dataset Statistics (v0.8)

Canonical set: `data/qa_v0.6_realistic_candidates.jsonl` — **1,997 verified QA** (v0.8 build) over **41
official announcements** from **10 announcement providers** + MOLIT/HUG public tabular data + 3 housing
statutes. Supersedes the v0.6 build (2,011 QA); see `CHANGELOG.md`.

> v0.8 = human-review repair build: all positional-cloze ("X 다음 값" / [위치 탐침]) questions were
> regenerated into natural, source-grounded questions or removed; location mislabels (항동→구로구,
> jpdc→제주시) and a set of confirmed wrong answers were fixed; 14 unrepairable items removed.

## 1. Headline

| Metric | v0.6 | **v0.8** |
|---|---|---|
| QA items | 2,011 | **1,997** |
| Near-duplicate clusters (effective size) | 286 | **282** |
| Official announcements | 41 | 41 |
| Announcement providers | 10 | 10 |
| Task families | 13 | **12** (correction_notice removed) |
| **Positional-cloze questions** | ~686 (34%) | **0** |
| **real_user + professional_analyst** | 92.2% | **100%** |

## 2. Task type

| task_type | count | % |
|---|---:|---:|
| long_context_retrieval | 616 | 30.8% |
| table_numeric_reasoning | 550 | 27.5% |
| cross_source_aggregation | 261 | 13.1% |
| cross_document_legal_reasoning | 109 | 5.5% |
| answerability_detection | 106 | 5.3% |
| multi_document_comparison | 83 | 4.2% |
| eligibility_reasoning | 73 | 3.7% |
| long_distance_retrieval | 62 | 3.1% |
| format_robustness | 60 | 3.0% |
| region_comparison | 27 | 1.4% |
| schedule_reasoning | 25 | 1.3% |
| provider_comparison | 25 | 1.3% |

## 3. Split (announcement-level; no announcement crosses an eval split)

| split | v0.6 | **v0.8** |
|---|---:|---:|
| dev | 1,618 | **1,608** |
| test_public | 105 | **104** |
| test_hidden | 288 | **285** |

## 4. Question style

| question_style | count | % |
|---|---:|---:|
| real_user | 1,278 | 64.0% |
| professional_analyst | 719 | 36.0% |
| diagnostic_probe (cloze) | 0 | 0.0% |

The v0.8 regeneration eliminated the templated positional-cloze style entirely. The 156 former
`diagnostic_probe` items and ~530 analyst-style cloze items are now natural `real_user`-style questions.

## 5. Answer type / metric

| answer_type | count | | metric | count |
|---|---:|---|---|---:|
| string | 632 | | contains_all | 1,182 |
| span | 627 | | exact_numbers | 562 |
| number | 562 | | term_recall | 120 |
| boolean_with_reason | 106 | | boolean_and_reason | 106 |
| date | 43 | | exact_match | 27 |
| text | 27 | | | |

## 6. Notes

- Cluster-weighted accuracy remains the headline metric (`scripts/eval_harness_v06.py`); the regeneration
  diversified former near-duplicate cloze families into distinct natural questions where the page supported
  it, but some parametric near-duplicates remain (clustered, weight = 1/size).
- All v0.8 question/answer/evaluation changes were propagated to the pre-realism source
  `data/qa_v0.5_candidates.jsonl` so the realism invariant (`check_question_realism_v06.py`) holds.
- Verification: `validate_dataset.py` = 0, `verify_qa.py` = 0 (1,997/1,997), `check_public_release_readiness.py`
  = public-ready, `check_question_realism_v06.py` = 0 failures.
