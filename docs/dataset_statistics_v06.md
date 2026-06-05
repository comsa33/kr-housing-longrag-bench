# Dataset Statistics (v0.6)

Canonical set: `data/qa_v0.6_realistic_candidates.jsonl` — **2,011 verified QA** over **41 official
announcements** from **10 announcement providers** + MOLIT/HUG public tabular data + 3 housing statutes.
All counts below are reproducible:

```bash
python3 scripts/check_public_release_readiness.py --qa data/qa_v0.6_realistic_candidates.jsonl --allow-dev
python3 scripts/eval_harness_v06.py --self-test          # cluster wiring
```

Status: **public-ready seed benchmark, not leaderboard-ready** (human-review verdicts pending;
`test_hidden` answers internal-but-in-repo). No human-validated / hallucination-free claim is made.

## 1. Headline

| Metric | Value |
|---|---|
| QA items | 2,011 |
| Near-duplicate clusters (effective size) | 286 |
| Official announcements | 41 |
| Announcement providers | 10 |
| Announcement 시·도 | 9 |
| Top announcement-provider share (LH) | 34.2% (target ≤ 60%) |
| Bundle-bearing QA | 1,553 |
| Distinct bundles referenced by QA / available | 110 / 194 |

## 2. Task type

| task_type | count | % |
|---|---:|---:|
| long_context_retrieval | 624 | 31.0% |
| table_numeric_reasoning | 551 | 27.4% |
| cross_source_aggregation | 261 | 13.0% |
| cross_document_legal_reasoning | 109 | 5.4% |
| answerability_detection | 106 | 5.3% |
| multi_document_comparison | 83 | 4.1% |
| eligibility_reasoning | 73 | 3.6% |
| long_distance_retrieval | 62 | 3.1% |
| format_robustness | 60 | 3.0% |
| schedule_reasoning | 28 | 1.4% |
| region_comparison | 27 | 1.3% |
| provider_comparison | 25 | 1.2% |
| correction_notice_reasoning | 2 | 0.1% |

## 3. Split (announcement-level; no announcement crosses an eval split)

| split | count | answers |
|---|---:|---|
| dev | 1,618 | included (`data/qa_v0.6_dev.jsonl`) |
| test_public | 105 | included (`data/qa_v0.6_test_public.jsonl`) |
| test_hidden | 288 | masked in `data/qa_v0.6_test_hidden_questions.jsonl`; gold internal only |

## 4. Question style

| question_style | count | % |
|---|---:|---:|
| professional_analyst | 1,250 | 62.2% |
| real_user | 605 | 30.1% |
| diagnostic_probe | 156 | 7.8% |

real_user + professional_analyst = 92.2%; cloze-phrased ≈ 7.8% (down from 34% pre-realism).
`diagnostic_probe` is the intentional position/passkey stress slice.

## 5. Answer type / metric

| answer_type | count | | metric | count |
|---|---:|---|---|---:|
| span | 686 | | contains_all | 1,205 |
| string | 639 | | exact_numbers | 553 |
| number | 553 | | term_recall | 120 |
| boolean_with_reason | 106 | | boolean_and_reason | 106 |
| text | 27 | | exact_match | 27 |

## 6. Provider (announcement providers + tabular/comparison buckets)

| provider | count |
|---|---:|
| 한국토지주택공사 (LH) | 549 |
| 서울주택도시공사 (SH) | 532 |
| 공공데이터(MOLIT/HUG) | 353 |
| 경기주택도시공사 (GH) | 111 |
| 대전도시공사 | 109 |
| 광주광역시도시공사 | 93 |
| 제주특별자치도개발공사 (JPDC) | 75 |
| 복수(비교) | 52 |
| 인천도시공사 (iH) | 45 |
| 부산도시공사 | 40 |
| 충북개발공사 | 31 |
| 대구도시개발공사 | 21 |

The dominance gate counts only real announcement providers (excludes `공공데이터(MOLIT/HUG)` and
`복수(비교)`): announcement-QA total 1,606, LH share **34.2%** ≤ 60%.

## 7. Region (시·도)

| region_sido | count |
|---|---:|
| 서울특별시 | 662 |
| 경기도 | 560 |
| 대전광역시 | 267 |
| 복수 | 117 |
| 광주광역시 | 97 |
| 충청북도 | 87 |
| 제주특별자치도 | 76 |
| 인천광역시 | 57 |
| 부산광역시 | 49 |
| 대구광역시 | 23 |

(plus small tabular-slice regions from public data: 충남 4, 울산 4, 강원 3, 세종 2, …). The
announcement-provider 시·도 count used by the readiness gate is **9** (excludes the public-data slices and
`복수`).

## 8. Context bundles (1,553 bundle-bearing QA)

| context_tier | count | | evidence_position | count |
|---|---:|---|---|---:|
| 512k | 504 | | early | 566 |
| 32k | 436 | | multi | 499 |
| 256k | 316 | | late | 422 |
| 64k | 156 | | middle | 66 |
| 128k | 141 | | | |

Bundles are materialized internally (`workspace_local/processed/bundles-v06/`) and rebuilt locally; only
locators + tier/position metadata are public. Tier + position cuts support length-degradation and
lost-in-the-middle analyses (see `docs/baseline_protocol_v06.md`).

## 9. Near-duplicate clustering

2,011 QA → **286 clusters** (`cluster_id`/`cluster_size`/`cluster_weight = 1/size`). 169 clusters are
singletons (59%); the largest families are the parametric retrieval and cross-source templates.
`scripts/eval_harness_v06.py` reports cluster-weighted accuracy so breadth — not repetition — drives the
score; cluster-weighted ALL is the headline number for paper claims.
