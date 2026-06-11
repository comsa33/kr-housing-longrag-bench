# Roadmap to v1.0

Status date: 2026-06-09

This roadmap supersedes the older v0.5-centered expansion roadmap. The dataset is already public as a seed
benchmark, and the `v0.7` (research-preview) and `v0.8` (human-review repair) milestones are **released**.
The remaining work is to turn it into a stable, paper-grade, and eventually leaderboard-ready benchmark.
Repository/package boundaries are governed by `docs/repository_scope_policy.md`.

## 0. Current Baseline: v0.8 (released 2026-06-09)

`v0.8` is the current public-ready seed benchmark (release lineage v0.6.3 → v0.7 → v0.8):

- 1,997 verified QA (v0.8 regenerated all positional-cloze into natural questions and removed 14
  unrepairable items; was 2,011 in the v0.6/v0.7 build).
- 41 official announcements; 10 announcement providers; 9 announcement 시도; 12 task families.
- 282 effective near-duplicate clusters; cluster-weighted accuracy is the headline metric.
- Public split files: **published v0.8** = dev 1,608 / test_public 104 / test_hidden 285 (masked); the
  **v0.9 branch** merges `test_hidden` into `test_public` → dev 1,608 / **test_public 389**, no hidden split
  (not yet released).
- Hugging Face `load_dataset()` verified; the dataset viewer serves the v0.8 parquet conversion.
- GitHub CI green; Zenodo versioned DOI `10.5281/zenodo.20571211` (concept `10.5281/zenodo.20559127`).

What `v0.8` repaired (see `CHANGELOG.md`, `docs/dataset_statistics_v08.md`):

- Eliminated positional-cloze (34% → 0%); `question_style` is now 100% real_user/professional_analyst.
- Fixed source-grounded location mislabels (항동→구로구, jpdc→제주시, 발산8단지→강서구) and confirmed wrong
  answers (e.g. table 0910 평균 전용면적 29.58→24.10).
- Review was LLM-assisted (gpt-5.4 grounding triage + Claude cross-model verification), **not** a full
  human pass.

It is still **not**:

- fully human-validated (only an LLM-assisted grounding pass + targeted repairs so far);
- sealed-hidden (the hidden split is masked, not a sealed leaderboard);
- leaderboard-ready;
- supported by release-grade model baseline tables (only v0.7 smoke diagnostics exist);
- large enough for a strong v1.0 benchmark-paper claim.

The `v0.7` baseline scaffold and smoke diagnostics remain available (provider-agnostic runner for OpenAI,
Azure OpenAI, Anthropic, Gemini, and Ollama; locator-only, full-context, BM25/dense/hybrid RAG, and
oracle-page smoke protocols; retrieval and page-diversity diagnostics). These are **research-preview
diagnostics, not release-grade benchmark tables** — they should inform the next baseline design but must not
be advertised as leaderboard results.

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

| Version | Main objective | Release label | Status |
|---|---|---|---|
| `v0.7` | Baseline scaffold + reproducible prediction protocol (smoke-level) | public research preview | ✅ released 2026-06-06 |
| `v0.8` | QA quality repair (cloze regen + location/answer fixes; LLM-assisted review) | human-review repair build | ✅ released 2026-06-09 |
| `v0.9` | Real baseline result tables + human-validation sample + source/QA expansion | paper-candidate dataset | ▶ next |
| `v1.0` | Stable schema, sealed hidden protocol, baseline paper tables | paper-grade benchmark | planned |

Note: the original plan put "real baseline experiments" in v0.7 and "human review sign-off" in v0.8. In
practice v0.7 shipped only smoke-level diagnostics and v0.8's review was LLM-assisted, so **release-grade
baseline tables and a true human-validation sample are both carried forward into v0.9** (Sections 3-5).

## 3. v0.7: Baseline Experiments and Packaging — ✅ RELEASED (2026-06-06)

Goal: make the benchmark empirically useful, not just downloadable.

**Outcome:** released as a research preview (Zenodo DOI `10.5281/zenodo.20570856`). The baseline scaffold
and smoke protocols below shipped, but the results stayed **smoke-level**, not release-grade tables — so the
"release-grade baseline tables" deliverable is **carried forward into v0.9** (Section 5).

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

## 4. v0.8: Human Review and Repair — ✅ RELEASED (2026-06-09)

Goal: make quality claims defensible.

**What actually shipped** (see `CHANGELOG.md`, `docs/dataset_statistics_v08.md`):

- An **LLM-assisted grounding-review pipeline** (gpt-5.4 strict extract-then-compare triage + Claude
  cross-model verification), calibrated on a planted-error set before use.
- **Positional-cloze regeneration**: triage surfaced that 34% of items were templated `[위치 탐침]` cloze
  (string-matching, not understanding, and error-prone — sampled cloze gold was 8/8 wrong). All ~686 were
  regenerated into natural source-grounded questions (679) or removed → cloze 34% → 0%.
- **Source-grounded fixes**: location mislabels (항동→구로구, jpdc→제주시, 발산8단지→강서구) and confirmed
  wrong answers (table 0910 29.58→24.10); 14 unrepairable items removed (2,011 → 1,997).
- Updated dataset statistics, DATASET_CARD, README, CITATION, Zenodo metadata, and the HF card.

**Honest gap (carried forward).** This was **not** a full human pass. The original v0.8 plan called for a
10-20% stratified *human*-reviewed sample with reported inter-annotator agreement; that has **not** been
done, so the dataset card says "LLM-assisted review," not "human-validated." A real human-validation sample
is now a **v0.9** deliverable (Section 5). Also outstanding from v0.8:

- ~20 `cross_document_legal_reasoning` gold answers are grounded paraphrases that omit secondary qualifiers
  (grounded but not exhaustive) → precision pass in v0.9;
- `region_sigungu == region_sido` on ~270 items whose 시·군·구 was not resolved → v0.9 metadata sweep.

## 5. v0.9: Baselines, Human Validation, and Expansion

Goal: close the two biggest credibility gaps for a benchmark paper (no real baseline tables; no human
validation), clean up v0.8 carry-overs, then reduce seed-benchmark limitations.

**Priority 0 — carried forward from v0.7/v0.8 (do these first):**

1. **Release-grade baseline result tables.** ▶ **DONE (2026-06-11)** — see
   [`docs/baseline_results_v09.md`](baseline_results_v09.md) §8: 4 OpenAI models (gpt-4.1-mini, **gpt-5.5
   winner**, gpt-5.4-mini/nano) × 3 regimes via OpenAI Batch, headline = **LLM-judge**.
   Key result: the legacy `contains_all` metric systematically undercounts and fabricated a FALSE
   "512k collapse" (0% → judge 42%); no collapse exists. Gating status:
   **(a) ✅ LLM-judge validated** vs human (n=80, agreement 96.2 %, κ=0.924, §9.0);
   **(b) ✅ test_public reported separately** (§8.5) and **the former `test_hidden` (285) merged into
   `test_public` → 389** (no hidden split; no local-model leg needed);
   **(c) open-weights leg DEFERRED** — `minimax-m3:cloud` is hosted (weights unreleased as of 2026-06), so it
   does NOT qualify; a genuinely open-weights model is to be selected by verifying live availability;
   **(d) ✅ HUG cross_source full-context fix applied** (20 items, §8.6) — both prompt-level (released runs)
   **and at the dataset level** (`build_bundles_v06.py` now embeds the HUG table in `mix_multiprovider_512k`);
   **(e) optional dense/hybrid RAG**; **(f) grow the dataset LAST**.
   ⚠️ Cost: the multi-model run cost far more than the single-model `~$5.5` estimate — one day booked **~$148**
   (gpt-5.5 reasoning output is the driver; never re-run gpt-5.5 on cb/rag — see baseline §5).
   *Original pilot design notes follow (superseded).* A fixed, seeded, stratified pilot sample
   (`scripts/build_baseline_sample_v09.py`, seed `20260610`: test_public 104 + dev 200 stratified over all
   12 task families, cluster-deduplicated; 304 items) was used to bring up the pipeline; the headline runs
   cover the **full** dev + **389-item** test_public. Regimes — closed-book (locator-only, v0.7 floor),
   **full-context**, **RAG (BM25)**; the verified context-window finding: `gpt-4.1-mini`
   (**1M context, ingests our 393k-token 512k tier**, whereas gpt-4o-mini's 128k window rejects it) and
   gpt-5.5 cover 512k, while the gpt-5.4 family caps at 272k. Full-context is the cost driver, so the giant tiers are capped
   (`512k→12`, `256k→16` ⇒ 116 full-context-eligible items; RAG/closed-book run all 304) to land at
   **≈$5.5** on the OpenAI leg (full-context ~$4.5 + RAG ~$1; measured at ~2.45 chars/token); the local
   leg is $0. Report plain + cluster-weighted accuracy cut by
   split / task_type / context_tier / question_style; record model ids, context limits, retrieval settings,
   cost, and date. **Extensible by design** (see the doc): the sample draw is seed-nested, so raising a
   tier cap is purely additive and `--resume` re-runs only new items; adding a model is orthogonal; and the
   local (non-data-sharing) gemma leg is the path to eventual hidden-split baselines. For the paper this
   v0.9 set is captioned **indicative/reference** — before camera-ready, lift the 512k/256k caps (tighter
   CIs), add 1-2 models (gpt-5-mini / Qwen), and add dense/hybrid RAG. This is the single
   highest-leverage next task.
2. **Human-validation sample.** A 10-20% stratified sample (plus 100% of high-risk legal/multi-document
   items) reviewed by a human, with inter-annotator agreement reported. Upgrades the card from
   "LLM-assisted" toward "human-validated."
3. **v0.8 quality carry-overs.** Fix the ~20 legal paraphrase-precision items; run the
   `region_sigungu`→시·군·구 metadata sweep (~270 items).

**Then — expansion and balance targets:**

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

`v0.7` and `v0.8` are released; `main == develop` at the v0.8 DOI-sync state. Recommended order:

1. **Stand up release-grade baselines (Section 5, Priority 0.1).** Pick 3-5 systems and a fixed evaluation
   slice; produce `{qa_id, prediction}` JSONL scored by `scripts/eval_harness_v06.py`; keep prompts,
   predictions, and bundle text internal under `workspace_local/`. Draft `docs/baseline_results_v09.md`.
   This is the highest-leverage single move.
2. **Start a human-validation sample in parallel (Section 5, Priority 0.2)** — stratified by
   task_type / provider / split; fill verdicts; report pass rates + inter-annotator agreement.
3. **Clear v0.8 carry-overs (Section 5, Priority 0.3):** legal paraphrase precision (~20 items) and the
   `region_sigungu` metadata sweep (~270 items).
4. **Then expand** toward the v0.9 size/coverage targets (more non-LH announcements per provider,
   underrepresented regions, better HWP/HWPX table extraction).
5. Keep every change on `develop` behind the public-safe gates; tag a `v0.9` release (GitHub + HF + a new
   Zenodo versioned DOI) only when baselines + validation + cleanups land and `docs/release_checklist.md`
   passes.
6. Defer the sealed-hidden track (Section 7) until after the v0.9 baselines; v1.0 must not claim
   leaderboard readiness without it.
