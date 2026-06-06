# Roadmap to v1.0

Status date: 2026-06-06

This roadmap supersedes the older v0.5-centered expansion roadmap for post-`v0.6.3` work. The dataset is
already public as a seed benchmark. The remaining work is to turn it into a stable, paper-grade, and
eventually leaderboard-ready benchmark. Repository/package boundaries are governed by
`docs/repository_scope_policy.md`.

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
- supported by release-grade model baseline tables;
- large enough for a strong v1.0 benchmark paper claim.

Post-`v0.6.3` development on `develop` has added a v0.7 baseline scaffold and smoke diagnostics:

- provider-agnostic baseline runner for OpenAI, Azure OpenAI, Anthropic, Gemini, and Ollama;
- locator-only, full-context, BM25 RAG, dense RAG, hybrid RAG, and oracle-page smoke protocols;
- retrieval diagnostics for read failures vs retrieval misses;
- page-diversity diagnostics showing dense misses on the 22-item quote slice were partly chunk-duplication
  artifacts;
- non-quote retrieval diagnostics showing that removing verbatim quotes hurts every retriever but BM25 still
  leads on that 69-item slice.

These are **research-preview diagnostics**, not release-grade benchmark tables. They should inform the next
baseline design but should not be advertised as leaderboard results.

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

## 3. v0.7: Baseline Experiments and Packaging

Goal: make the benchmark empirically useful, not just downloadable.

Completed on `develop`:

- `scripts/run_llm_baseline_v07.py`: provider-agnostic runner with public-safe output policy.
- `docs/baseline_results_v07.md`: locator-only baseline protocol and first closed-book floor numbers.
- `docs/full_context_smoke_v07.md`: 22-item full-context smoke showing document access changes the task from
  closed-book floor to usable accuracy.
- `docs/rag_smoke_v07.md`: BM25/oracle RAG smoke on the same 22 items.
- `docs/dense_hybrid_rag_smoke_v07.md`: BM25/dense/hybrid comparison and answer-error decomposition.
- `docs/rag_page_diversity_diagnostics_v07.md`: page-diversity retrieval diagnostics.
- `docs/rag_non_quote_retrieval_diagnostics_v07.md`: non-quote retrieval diagnostics.

Remaining v0.7 deliverables before tagging a public `v0.7` release:

- Expand `docs/baseline_results_v07.md` from the current smoke-level draft into a release-grade result
  document covering the command examples and result cuts below.
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

- At least 3 non-trivial baselines beyond oracle/dummy/echo/random are documented as smoke or release-grade.
- Every baseline produces `{qa_id, prediction}` JSONL and is scored by `scripts/eval_harness_v06.py`.
- Costs, model names, context limits, retrieval settings, and run date are recorded.
- No hidden answers are published.
- Public docs clearly separate:
  - dataset/evaluation artifacts suitable for `main`, Hugging Face, and Zenodo;
  - internal prompt/prediction artifacts under `workspace_local/`;
  - experimental diagnostics that should stay on `develop` until released.

Recommended next v0.7 work:

1. Package the v0.7 baseline scaffold for public readability:
   - update `README.md`, `DATASET_CARD.md`, and `docs/baseline_results_v07.md`;
   - summarize smoke results without overclaiming;
   - keep all full prompts, predictions, bundle text, and provider logs internal.
2. Decide whether to run a small paid page-diverse answer remeasurement:
   - only after explicit maintainer approval;
   - run on a fixed smoke slice;
   - report cost, model ids, and date.
3. Defer broad/full test_public answer runs until the smoke protocol is stable.

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

## 8. Repository Scope and Split Decision

Current decision: keep this as a **single benchmark repository** through v0.7 unless experiment artifacts
start crowding the public package. This is standard for a dataset/benchmark seed: public data files,
dataset card, validators, scoring scripts, and minimal baseline scaffolds can live together.

Do **not** split just because the repo contains baseline scripts. Split only when at least one condition is
true:

- provider-specific experiment code grows beyond minimal reproducible baselines;
- paid-run orchestration, caches, notebooks, or private submission handling become a substantial subsystem;
- hidden/leaderboard operation needs infrastructure that must not ship with the public dataset package;
- release consumers cannot tell which files are dataset artifacts vs internal experiment machinery.

If splitting becomes necessary, use:

- `kr-housing-longrag-bench`: public dataset, schema, validation, scoring, minimal baseline commands;
- `kr-housing-longrag-experiments` or `kr-housing-longrag-baselines`: paid runs, large result tables,
  notebooks, retriever tuning, sealed-hidden operations, and private prediction archives.

The boundary is detailed in `docs/repository_scope_policy.md`.

## 9. Immediate Next Tasks

Recommended order after the current `develop` baseline work:

1. Keep all v0.7 work on `develop`; do not touch `main` until a release decision is made.
2. Create `feature/v07-release-docs-and-scope`.
3. Update public-facing docs so v0.7 baseline work is discoverable but clearly labelled research-preview.
4. Confirm `docs/repository_scope_policy.md` is referenced from README, roadmap, and worker handoff docs.
5. Confirm no internal artifacts are tracked.
6. Run public-safe validation gates.
7. After docs are clean, decide whether to tag `v0.7` or keep collecting baseline evidence.
8. Schedule human review later when reviewers are available.
