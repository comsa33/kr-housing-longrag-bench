# Roadmap to v1.0

Status date: 2026-06-06

This roadmap supersedes the older v0.5-centered expansion roadmap for post-`v0.6.3` work. The dataset is
already public as a seed benchmark. The remaining work is to turn it into a stable, paper-grade, and
eventually leaderboard-ready benchmark.

## 0. Current Baseline: v0.6.3

`v0.6.3` is a public-ready seed benchmark:

- 2,011 verified QA.
- 41 official announcements.
- 10 announcement providers.
- 9 announcement 시도.
- 13 task families.
- Public split files with masked hidden questions.
- Hugging Face loading verified through `load_dataset()`.
- GitHub CI green.
- Zenodo DOI minted.

It is not yet:

- human-validated;
- sealed-hidden;
- leaderboard-ready;
- supported by real model baseline tables;
- large enough for a strong v1.0 benchmark paper claim.

## 1. Target v1.0 Claim

Recommended claim:

> KR-Housing-LongRAG-Bench evaluates Korean real-world housing long-context, RAG, and table/tool systems
> on official housing announcements, public tabular data, and housing law, using grounded QA with
> provider/region-diverse sources and cluster-weighted scoring.

Avoid these claims:

- general Korean long-context coverage;
- complete Korean housing-policy coverage;
- legal or eligibility advice;
- hallucination-free;
- human-validated before review is complete;
- leaderboard-ready before the hidden harness is sealed.

## 2. Version Targets

| Version | Main objective | Release label |
|---|---|---|
| `v0.7` | Real baseline experiments and reproducible prediction protocol | public research preview |
| `v0.8` | Human review sign-off and QA quality repair | human-reviewed seed |
| `v0.9` | Source/QA expansion and context-bundle balancing | paper-candidate dataset |
| `v1.0` | Stable schema, sealed hidden protocol, baseline paper tables | paper-grade benchmark |

## 3. v0.7: Baseline Experiments

Goal: make the benchmark empirically useful, not just downloadable.

Minimum deliverables:

- Baseline result document: `docs/baseline_results_v07.md`.
- Prediction files under `workspace_local/audit/baselines/` for any run that uses gold/internal context.
- Public-safe command examples for:
  - full-context LLM;
  - BM25 retrieval;
  - dense or hybrid RAG;
  - table/tool pipeline;
  - oracle locator ceiling.
- Result cuts:
  - plain accuracy;
  - cluster-weighted accuracy;
  - split;
  - task_type;
  - context_tier;
  - evidence_position;
  - question_style.

Acceptance criteria:

- At least 3 non-trivial baselines beyond oracle/dummy/echo/random.
- Every baseline produces `{qa_id, prediction}` JSONL and is scored by `scripts/eval_harness_v06.py`.
- Costs, model names, context limits, retrieval settings, and run date are recorded.
- No hidden answers are published.

## 4. v0.8: Human Review and Repair

Goal: make quality claims defensible.

Minimum deliverables:

- Review protocol document.
- Stratified review sample with verdicts filled.
- Error taxonomy:
  - wrong answer;
  - weak grounding;
  - ambiguous question;
  - unrealistic question;
  - extraction artifact;
  - split or leakage issue;
  - copyright/publication concern.
- Repair pass for failed or ambiguous items.
- Updated dataset statistics after removals/repairs.

Acceptance criteria:

- 10-20% stratified sample reviewed.
- 100% review of high-risk agent-authored legal/multi-document items.
- Family/provider/split review pass rates reported.
- Items that fail review are fixed or removed.
- Dataset card may say "human-reviewed sample" only with exact coverage, not "fully human-validated"
  unless full review is actually complete.

## 5. v0.9: Expansion and Balance

Goal: reduce seed-benchmark limitations before paper submission.

Minimum targets:

| Area | v0.9 target |
|---|---:|
| Official announcements | 75+ |
| Providers | 10+ |
| 시도 | 12+ |
| Verified QA | 3,500+ |
| Effective clusters | 600+ |
| Table/cell-grid announcements | 40+ |
| Hidden questions | 600+ |
| Major task families | 250+ each where feasible |

Priority expansions:

- Add more non-LH announcements per provider.
- Add underrepresented regions.
- Improve HWP/HWPX table extraction, especially currently text-only providers.
- Add more schedule, eligibility, correction-notice, and realistic applicant-style questions.
- Balance context tiers and evidence positions across providers.

Acceptance criteria:

- No provider dominance above threshold.
- Announcement-level split leakage remains 0.
- Public release still contains no raw documents or hidden gold.
- Near-duplicate clusters are reported and cluster-weighted metrics remain the headline.

## 6. v1.0: Paper-Grade Benchmark

Goal: stable public benchmark suitable for a main dataset paper or benchmark paper.

Minimum targets:

| Area | v1.0 target |
|---|---:|
| Official announcements | 100+ |
| Providers | 10+ |
| 시도 | 12+ |
| Verified QA | 5,000+ |
| Effective clusters | 1,000+ |
| Hidden questions | 1,000+ |
| Human review | 10-20% stratified + all high-risk items |
| Baselines | full-context, BM25, dense/hybrid RAG, hierarchical RAG, table/tool |
| Schema | frozen, versioned, migration notes included |
| Release | GitHub + HF + Zenodo + CI + external smoke test |

v1.0 can be called paper-grade only when:

- human review is complete and reported;
- baseline tables exist;
- hidden protocol is clear;
- release package loads on Hugging Face;
- all validators pass;
- limitations are stated without overclaiming.

## 7. Sealed Hidden Track

The current hidden split is masked in public split files but not a sealed leaderboard. To become sealed:

1. Keep public hidden questions only in GitHub/HF.
2. Keep hidden gold outside the public repo and outside public HF files.
3. Provide a maintainer-only scoring route:
   - private evaluation script;
   - private HF repo;
   - hosted eval endpoint;
   - or manual submission queue.
4. Publish only aggregate scores unless participants consent to release predictions.
5. Record anti-leakage policy and update `DATASET_CARD.md`.

This can be deferred until after v0.7 baselines, but v1.0 should not claim leaderboard readiness without it.

## 8. Immediate Next Tasks

Recommended order after `v0.6.3`:

1. Create and push `develop`.
2. Keep this workflow and roadmap on `develop`.
3. Start `feature/baseline-results`.
4. Run at least one cheap non-trivial baseline end to end.
5. Document the baseline result table.
6. Design sealed-hidden operation, but do not block baseline work on it.
7. Schedule human review later when reviewers are available.

