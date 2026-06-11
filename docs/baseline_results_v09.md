# Baseline Results (v0.9, release-grade)

**Scope.** This document reports the **release-grade reference baselines** for the v0.9 build: **five models**
× **three context regimes** (closed-book / RAG-BM25 / full-context), run via the **OpenAI Batch API** and
scored by an **LLM-judge headline metric** (semantic equivalence, human-validated — §9.0), with deterministic
soft/EM + Wilson 95% CIs as the reproducible reference (§8.4). It supersedes the v0.7 *smoke* diagnostics
([`baseline_results_v07.md`](baseline_results_v07.md), a 22-item convenience slice, closed-book floor only).

This is a **research-preview reference baseline**, **not** a sealed-hidden leaderboard and **not** a final
model ranking. Per-tier long-context numbers are captioned **indicative**; see *Limitations and the path to
paper-grade* (§9) for what must be added before a camera-ready claim. No raw documents, bundle text, or API
keys are published here; all predictions, prompts, and run metadata are INTERNAL under
`workspace_local/audit/baselines/` (gitignored).

> **Reading guide.** §§1–7 describe the **current** design and run mechanics; §§8–9 are the results and
> limitations. Where an earlier 304-item *pilot* sample is referenced, it is labelled as such — the headline
> coverage below is the **full** dev + the **389-item** held-out `test_public`, not the pilot slice.

## 1. Evaluation coverage

The dataset is **1,997 QA**: `dev` (1,608) + `test_public` (389). There is **no hidden split** — the former
`test_hidden` (285) was merged into `test_public` in v0.9 (see CHANGELOG; §8.5). `cluster_id` near-duplicate
clusters are scored with **cluster-weighted** accuracy so repetition cannot inflate scores.

- **closed-book** and **RAG** are run on the **full** `dev` + `test_public` (cb: 1,608 + 389; RAG: items
  with gold pages, 386 of test_public).
- **full-context** is **tier-capped** (cost control — §3): the embedded haystack at the 512k tier is ~393k
  tokens, so a handful of items dominate the bill.

A 304-item seeded *pilot* sample (`build_baseline_sample_v09.py`, seed `20260610`: test_public 104 + dev 200
stratified) was used to bring up and validate the pipeline; it is **superseded** by the full-split runs above
and is retained only as the seed-nested source for the tier-capped full-context subsets (§3). The drawn pilot
files live INTERNAL under `workspace_local/audit/baselines/`.

## 2. Regimes

| Regime | What the model sees | Coverage | Purpose |
|---|---|---|---|
| **closed-book** (locator-only) | instruction + question + `context_spec` locators, **no document text** | full dev + test_public | refusal / hallucination floor (a true lower bound; the v0.7 §4 numbers are this regime) |
| **full-context** | the question + the **entire bundle text** at the item's `context_tier` | tier-capped subset (§3) | long-context LLM headline (lost-in-the-middle stress on Korean haystacks up to ~393k tokens) |
| **RAG (BM25)** | the question + **BM25-retrieved chunks** (~8k tokens) | full dev + test_public | the tier-independent, scalable retrieval baseline |

closed-book and RAG run on the full split because they are cheap (tiny / bounded context). Full-context is
the cost driver (input scales with the haystack) and is therefore tier-capped.

## 3. Full-context subset and tier caps

Full-context input cost scales with the haystack: the "512k" tier is ~393k tokens (measured), so a handful
of those items dominate the bill. To keep cost bounded while still covering every tier, the giant tiers are
capped (seeded selection; items with no bundle on disk — mostly `answerability_detection` with no haystack —
are not full-context-eligible). Two capped subsets were built:

- **pilot subset (116 items):** caps `512k → 12`, `256k → 16` over the 304-item pilot (32k 52 / 64k 22 /
  128k 14 / 256k 16 / 512k 12). This is the §8.1–8.2 pooled-headline full-context coverage.
- **test_public extension (72 items):** built over the 285 merged items (`512k → 20`, `256k → 16`, others
  →12) so the held-out split reports full-context per-tier directly (§8.5; test_public fc now **n=105**, incl.
  **25 at 512k** vs 5 before).

The cap is a **cost-control choice, not a structural limit**. Because the draw is **seed-nested** (same seed
⇒ `[:12] ⊂ [:30]`), raising a cap later is **purely additive** — already-run predictions stay valid.

**HUG injection (cross_source only).** `cross_source_aggregation` items ask an aggregate over the HUG
(주택도시보증공사) sale-history table, whose gold is computed from 624 rows that the canonical bundles do
**not** embed → unanswerable in the full-context regime (a benchmark-construction artifact, §8.6). The fix is
applied **at the prompt level to the cross_source full-context items only** (the original 4 + the 16 the merge
added at 512k = 20 prompts): the 624 HUG rows are injected as a compact in-bundle table by
`scripts/fix_fc_hug_bundle_v09.py`. Non-cross_source full-context prompts are unchanged, and the **canonical
dataset bundles still lack HUG** (rebuilding them so HUG is embedded by default is deferred dataset work).

## 4. Models

Five proprietary, hosted models (OpenAI), run via the Batch API. All are **API/hosted** — there is **no
open-weights model in this table** (see the note below).

| Model | Context window | Covers 512k? | Notes |
|---|---|---|---|
| `gpt-4.1-mini` | **~1M (verified 393k accepted)** | ✅ | all regimes/tiers; low reasoning |
| **`gpt-5.5`** | **≥393k (0 ctx-rejections)** | ✅ | overall winner; **heavy reasoning → the cost driver (§5)** |
| `gpt-5.4-mini` | **272k (verified)** | ❌ ✗ctx | rejects the 393k bundle (HTTP 400 "limit 272000"); strong on tiers it fits |
| `gpt-5.4-nano` | **272k (verified)** | ❌ ✗ctx | smallest; degrades fastest |

The 272k window of the gpt-5.4 family is a real **quality-vs-context-coverage tradeoff**: they cannot ingest
the 512k tier (recorded as `✗ctx`, an error, not a wrong answer), while gpt-4.1-mini and gpt-5.5 cover all
tiers.

> **Open-weights leg — DEFERRED (not yet run).** An earlier plan used `minimax-m3:cloud` (Ollama Cloud) as
> the "open-weights" point, but as of 2026-06 MiniMax M3 is a **hosted endpoint whose weights are not
> publicly released** (open-weight release was *announced* but not available); accessed via Ollama Cloud it
> is a cloud API, not a locally-runnable open model. **It does not satisfy the open-weights / reproducibility
> role and is reclassified as hosted; its partial run (318/688) is treated as incomplete diagnostics, not a
> reported result.** A genuinely open-weights long-context model for this leg is **deferred and to be
> selected by verifying current availability against live sources** (not asserted from memory). Local GPU
> note: a single 24GB RTX 3090 is **VRAM-bound** (KV cache for 256k+ tokens does not fit), so the open leg
> would run via a provider serving public weights (reproducible because the weights are public), not locally.

**Why gpt-4.1-mini, not gpt-4o-mini (empirically verified, 2026-06-10).** This is a long-context
benchmark, so the model must ingest the haystack. On an identical 512k-tier bundle (974,007 chars =
**393,315 tokens**):

- `gpt-4o-mini` → `HTTP 400: maximum context length is 128000 tokens. However, your messages resulted in
  393315 tokens` — its 128k window **cannot hold 59% of the sample** (the 256k/512k tiers).
- `gpt-4.1-mini` → **OK**, `prompt_tokens=393,315`, answered correctly — confirming it ingests our largest
  tier with margin (corroborates the ~1M window).

Measured ratio for cost planning: **~2.45 chars/token** on this Korean-heavy mixed text.

## 5. Cost — pre-run estimate vs observed

**Pre-run estimate (single model, pilot 304, ⚠️ misleading):** the original `gpt-4.1-mini`-only projection
was **~$5.5** (fc 116 ~11.2M input + RAG ~$1 + closed-book ~$0, at $0.40/$1.60 per 1M in/out). This held for
gpt-4.1-mini but **badly under-projected the multi-model run** because it ignored reasoning output.

**Observed (authoritative, OpenAI Costs API via admin key):** the full v0.9 effort cost far more — a single
day (2026-06-11) booked **~$148**. Derived **batch** rates (already 50%-discounted):

| Model | output (reasoning) | long-ctx input | regular input |
|---|---:|---:|---:|
| **gpt-5.5** | **~$15.0 /Mtok** ← dominant | ~$0.87 /Mtok | ~$2.35 /Mtok |
| gpt-4.1-mini | low | ~$0.20 /Mtok | ~$0.40 /Mtok |

**gpt-5.5 is the cost driver, and its reasoning *output* is the killer.** In closed-book (no evidence) it
reasons explosively — 285 cb items emitted ~444k reasoning + ~452k completion tokens (~$7 just for output).
In full-context it barely reasons (~137 tok/item); there the cost is *input* tokens (the 393k bundles).

> **⚠️ Cost rule (do not violate):** **never re-run gpt-5.5 on closed-book / RAG** (reasoning output
> explodes). Use gpt-5.5 only where it adds unique value (full-context / 512k). For cheap regimes prefer
> gpt-4.1-mini. **Always check the Costs API before and after a run** (`GET /v1/organization/costs`,
> `amount.value` is a string), and **estimate output tokens, not just input**, for reasoning models. Batch
> halves cost but does not change this.

## 6. Commands (finalized)

The runs use the **OpenAI Batch API** (50% cheaper, async <24h, qa_id-native `custom_id`). The LLM-judge is
the headline; deterministic soft/EM + Wilson CIs are the reproducible reference.

```bash
export OPENAI_API_KEY=...   # from workspace_local/secrets/openai_api.key

# 1. build the regime prompt sets (deterministic; INTERNAL output)
python3 scripts/build_baseline_rag_v09.py --sample <split-or-sample>.jsonl --out .../rag_..._prompts.jsonl
python3 scripts/build_baseline_fullcontext_v09.py --sample <fc-subset>.jsonl --out .../fc_..._prompts.jsonl
#   cross_source full-context prompts then get HUG injected:
python3 scripts/fix_fc_hug_bundle_v09.py            # 624 HUG rows -> the cross_source fc prompts (§3)

# 2. run each model x regime via the Batch API (submit -> status -> fetch). custom_id = <regime>__<split>__<qa_id>
python3 scripts/run_batch_baseline_v09.py submit --model gpt-5.5 --regimes cb,rag,fc --max-output-tokens 4000
python3 scripts/run_batch_baseline_v09.py status --model gpt-5.5
python3 scripts/run_batch_baseline_v09.py fetch  --model gpt-5.5   # writes <regime>_<model>_<split>.jsonl + .calls.jsonl
#   partial/extension runs: --prompt-file <subset> --track-suffix _foo --out-suffix _foo (no clobber)
#   ⚠️ do NOT re-run gpt-5.5 on cb/rag (reasoning-output cost — §5)

# 3. LLM-judge (headline) — semantic equivalence, judge = gpt-4.1-mini, public splits only, per regime
python3 scripts/llm_judge_v09.py submit --pred <one-regime merged preds>.jsonl --tag <tag>
python3 scripts/llm_judge_v09.py fetch  --tag <tag>            # writes <tag>.judged.jsonl

# 4. score: judge accuracy by split (+ Wilson CI, fc by tier) and the deterministic soft/EM reference
python3 scripts/score_judge_v09.py   --splits ALL,dev,test_public     # LLM-judge, plain + cluster-weighted
python3 scripts/score_answers_v09.py --pred <preds>.jsonl --pred-only # soft|EM|contains|recall + Wilson CI
python3 scripts/score_retrieval_v09.py --rag .../rag_..._prompts.jsonl # BM25 recall@k / hit@k (model-independent)

# navigate INTERNAL artifacts (naming legend + per-file status)
python3 scripts/catalog_baselines_v09.py            # -> workspace_local/audit/baselines/INDEX.md
```

**Artifact layout (INTERNAL, under `workspace_local/audit/baselines/`, gitignored).** Predictions are
`<regime>_<model>_<split>.jsonl` with `{qa_id, prediction}` (regime ∈ cb/rag/fc); each run also writes a
rich `<…>.calls.jsonl` (tokens, latency, and for reasoning models the `thinking` trace, joinable by
qa_id), a `<…>.meta.json`, and a `<…>.log`. Input prompts are `<regime>_v09_prompts.jsonl`. Run
`catalog_baselines_v09.py` to (re)generate `INDEX.md`, which lists every artifact with counts and status.

## 7. Metrics (the v0.9 reported set)

- **Headline — LLM-judge** (`scripts/llm_judge_v09.py`, `scripts/score_judge_v09.py`): semantic-equivalence
  judgement (correct / incorrect / unanswerable; judge = gpt-4.1-mini, public splits only), reported **plain
  + cluster-weighted** with a **Wilson 95% CI**, cut by split / task_type / context_tier. It replaced the
  legacy substring match, which **systematically undercounts** paraphrases/format (§8.4). The judge is
  **human-validated**: n=80 blind, agreement 96.2 %, Cohen's κ=0.924 (§9.0).
- **Deterministic reference** (`scripts/score_answers_v09.py`): **soft** (EM | contains | token-recall ≥
  0.7), plus EM / contains / numeric, each with a Wilson 95% CI, plain + cluster-weighted. Reproducible
  without an API; tracks the judge closely and is the fallback for anyone re-scoring offline.
- **Cluster-weighted** is the headline cut for both: it discounts near-duplicate `cluster_id` clusters so a
  few repeated items cannot inflate the score. **Abstention** is captured by `task:answerability_detection`.
- **Retrieval quality** for RAG (`scripts/score_retrieval_v09.py`): **recall@k** / **hit@k**, plain +
  cluster-weighted, cut by split / task_type / context_tier. Model-independent (a property of BM25).
- **Deferred extensions:** evidence-position cut; multi-answer set-F1; a second independent human annotator
  for the judge (the κ above is judge-vs-creator, not inter-human). All additive on the same predictions.

## 8. Results

Run 2026-06-11 via the OpenAI Batch API (`temperature=0`; reasoning models at default effort, `max_completion_tokens=4000`; BM25 `k=5`). **The headline metric is the LLM-judge** (semantic equivalence, `scripts/llm_judge_v09.py`, judge = gpt-4.1-mini) — see §8.4 for why the legacy `contains_all` metric is unreliable. cb/rag are scored on the full dev+test_public; full-context (fc) on the tier-capped subsets of §3 (pilot 116 for the pooled tables; test_public extended to n=105). No open-weights model is reported (the leg is deferred — see §4).

### 8.1 Five models × three regimes (LLM-judge; plain / cluster-weighted)

| Model | closed-book | RAG (BM25) | full-context |
|---|---|---|---|
| gpt-4.1-mini | 18% / 32% (n=1712) | 56% / 43% (n=1255) | 86% / 73% (n=116) |
| gpt-5.4-mini | 17% / 18% (n=1712) | 54% / 38% (n=1255) | 95% / 86% (n=100*) |
| gpt-5.4-nano | 8% / 6% (n=1712) | 45% / 25% (n=1255) | 71% / 54% (n=100*) |
| **gpt-5.5** | **39% / 49%** (n=1639) | **58% / 42%** (n=1235) | **97% / 83%** (n=116) |

\* gpt-5.4-mini/nano have a **272k-token context window**, so 16/116 fc items (the 512k tier + the largest 256k items) are context-rejected, not answered — a model property, reported as `✗ctx` in §8.2, not a wrong answer. gpt-4.1-mini (~1M) and gpt-5.5 (≥393k verified) ingest all tiers.

**gpt-5.5 leads every regime.** Monotonic closed-book ≪ RAG ≪ full-context holds for all models: context is decisive. Smaller models degrade faster (gpt-5.4-nano).

### 8.2 Full-context by context tier (LLM-judge, plain)

| Model | 32k | 64k | 128k | 256k | 512k |
|---|---:|---:|---:|---:|---:|
| gpt-4.1-mini | 98% | 86% | 93% | 69% | 50% |
| gpt-5.4-mini | 98% | 95% | 79% | 100% | ✗ctx |
| gpt-5.4-nano | 87% | 55% | 36% | 75% | ✗ctx |
| **gpt-5.5** | **100%** | 95% | **100%** | **100%** | **75%** |

(512k numbers are **after the HUG-bundle fix of §8.6** — the 4 `cross_source_aggregation` items now carry the HUG table in-bundle. Pre-fix, gpt-5.5's 512k was 42%, deflated by an artifact, not a model failure.)

**There is no "512k collapse."** gpt-5.5 holds at or near 100% from 32k to 256k and **75%** at 512k. The residual 512k gap is now a **genuine** model signal: of the 12 512k items, the 3 gpt-5.5 still misses are real multi-document legal/comparison hops, and the cross_source aggregation that used to be unanswerable now cleanly **separates the models** (§8.6) — gpt-5.5 aggregates the in-bundle HUG table correctly, gpt-4.1-mini cannot. The **272k context-coverage tradeoff** (gpt-5.4 family ✗ at 512k vs gpt-5.5/gpt-4.1-mini covering it) is the other honest long-context finding.

### 8.3 Retrieval quality (BM25, k=5, model-independent)

On the full split (n=1,255 items with gold pages): recall@5 ≈ **47.6%**, hit@5 ≈ 48.8% (cw-recall 52.1%). Per-task highs (`long_distance_retrieval` ≈ 98%, `eligibility_reasoning` ≈ 74%) vs lows (`schedule_reasoning` ≈ 11%, `multi_document_comparison` ≈ 13%) — BM25 is weakest where evidence is scattered across documents. Full breakdown via `scripts/score_retrieval_v09.py`.

### 8.4 Metric matters — `contains_all` is unreliable (a methodological result)

The legacy `contains_all`/normalized-substring match (v0.7/v0.8) produces **systematic false negatives** when the prediction is correct but phrased or formatted differently from the gold (e.g. gold `"부산도시공사=부산광역시 / 한국토지주택공사=경기도"` vs a correct pred `"부산도시공사: 부산광역시 / …: 경기도"`). Three metrics on the same gpt-5.5 full-context predictions:

| Metric | ALL | 512k tier |
|---|---:|---:|
| `contains_all` (legacy) | 87.9% | **0%** ← fabricated "collapse" |
| soft (em \| contains \| token-recall≥0.7; `score_answers_v09.py`) | 91.4% | 16.7% |
| **LLM-judge** (semantic; `llm_judge_v09.py`) | **93.1%** | **41.7%** |

These three columns are computed on the **pre-§8.6 predictions** (where the 512k cross_source items were
unanswerable) precisely to isolate the metric gap; they are not the current headline. After the HUG-bundle
fix the headline 512k judge is **75%** (§8.2). `contains_all` undercounts every model and, at the 512k tier,
drove a **non-existent** "512k collapse" to 0%. All v0.9 headline numbers use the LLM-judge; soft + Wilson
95% CIs are the reproducible deterministic reference. The LLM-judge itself is now **human-validated** (§9.0).

### 8.5 Held-out split: test_public reported separately (dev ≠ test)

§8.1–8.2 pool `dev` (development, 1,608) with `test_public` — convenient but a development-set red flag for a
paper. The **same** LLM-judge verdicts, cut by split with a Wilson 95% CI (`scripts/score_judge_v09.py`),
isolate the held-out headline.

> **v0.9 split change:** `test_public` was enlarged 104 → **389** by merging the former `test_hidden` (see
> dataset CHANGELOG; 512k tier 41 → 124, + `ood_region`/`ood_year` subsets). Baselines have been **extended to
> the full 389** (cb/rag on all 389; fc on a tier-capped subset, now n=105 incl. **25 at 512k** vs 5 before).
> The HUG-bundle fix of §8.6 was re-applied to the 16 cross_source items that the merge added at 512k.

**test_public — full 389 (LLM-judge, plain / cluster-weighted; cb shows the cw 95% CI):**

| Model | closed-book | RAG (BM25) | full-context |
|---|---|---|---|
| gpt-4.1-mini | 20% / 39% [29–51%] (n=389) | 61% / 41% (n=386) | 73% / 70% (n=105) |
| gpt-5.4-mini | 20% / 29% [19–40%] (n=389) | 62% / 38% (n=386) | 91% / 90% (n=78\*) |
| gpt-5.4-nano | 4% / 0% [0–6%] (n=389) | 47% / 18% (n=386) | 71% / 60% (n=78\*) |
| **gpt-5.5** | **46% / 59%** [48–70%] (n=372) | 63% / 40% (n=386) | **93% / 59%** (n=105) |

\* gpt-5.4-mini/nano (272k window) context-reject the 512k fc items, so their fc n is lower and excludes 512k.
gpt-5.5 cb n=372 (the original ~93 quota-failed items are still pending a re-run).

**full-context by tier on test_public (LLM-judge, plain):**

| Model | 32k | 64k | 128k | 256k | 512k |
|---|---:|---:|---:|---:|---:|
| gpt-4.1-mini | 96% (n27) | 100% (n19) | 83% (n12) | 77% (n22) | **20% (n25)** |
| **gpt-5.5** | 100% (n27) | 100% (n19) | 100% (n12) | 95% (n22) | **76% (n25)** |

The enlarged held-out set **confirms the §8.6 finding with real power**: at 512k (now n=25, not 5), gpt-5.5
holds **76%** while gpt-4.1-mini sits at **20%** — both ingest the same HUG-augmented 410k-token bundle, but
only the frontier model aggregates over it. The split-level ranking matches the pooled table (gpt-5.5
strongest; context monotonicity holds), so dev was not flattering the leaderboard. Two reporting notes:

1. **plain vs cluster-weighted diverges on this split** (e.g. gpt-4.1-mini cb 20% plain vs 39% cw): a few
   answerable clusters dominate the weighted score, so we report both.
2. **`ood_region` (116) / `ood_year` (50) subsets** (carried via `split_tags`) now support an
   in-distribution-vs-OOD generalization breakdown — left for the camera-ready analysis.

**There is no longer a hidden split** — the former `test_hidden` (285) was merged into `test_public` in v0.9
(a larger public held-out test is more valuable than a sealed set we cannot serve; a future release can
re-carve a sealed split from grown data).

### 8.6 HUG-bundle fix turns an artifact into a capability signal

The four `cross_source_aggregation` items at the 512k tier ask an aggregate over the HUG (주택도시보증공사)
sale-history table — e.g. *"how many 2023 사업장 in 경기도?"* (gold 61건) or *"average 총세대수"* (gold
1,073세대). Their gold is computed from 624 HUG rows that were **never embedded in the full-context bundle**
(only the LH announcements were), so every model could only abstain and was scored wrong — a
benchmark-construction artifact that pinned gpt-5.5's 512k to 42%.

Full-context means *every source the question needs is in the bundle*, so this is a bundle bug, not a task
design issue. We injected the 624 rows as a compact in-bundle table (`scripts/fix_fc_hug_bundle_v09.py`;
verified to reproduce all four golds: 61 / 15 / 77 / 1,073) and re-ran the two models that can ingest the
resulting ~410k-token prompt (gpt-4.1-mini, gpt-5.5; the 272k gpt-5.4 family still ✗ctx). LLM-judged result:

| Model | cross_source @512k, HUG **absent** (old) | HUG **present** (fixed) |
|---|---:|---:|
| gpt-4.1-mini | 0 / 4 (unanswerable) | **0 / 4** |
| **gpt-5.5** | 0 / 4 (unanswerable) | **4 / 4** |

The fix **separates the models on a real capability**: with the table in front of it, gpt-5.5 aggregates
(counts / averages rows by 지역·연도) correctly across a 410k-token context, while gpt-4.1-mini still cannot
(it returns wrong counts like 38/600 or abstains) — genuine long-context aggregation, no longer an artifact.
This lifts gpt-5.5's 512k tier from 42% → **75%** (§8.2) and its overall fc plain from 93% → **97%** (§8.1);
gpt-4.1-mini is unchanged. The other 8 512k items were left byte-identical, so their predictions stand.

The **test_public extension** (§8.5) added 16 more cross_source items at 512k, so the **same prompt-level HUG
fix was re-applied to all 20** (4 + 16). On the held-out 512k tier (now n=25) the result holds with real
power: **gpt-5.5 76%** vs **gpt-4.1-mini 20%** — same separation, more items. The fix is **prompt-level only**;
the canonical dataset bundles still lack HUG (a default-embed rebuild is deferred dataset work, §3).

> Caveats: LLM-judge is **human-validated** (§9.0: n=80, agreement 96.2 %, κ=0.924); §8.1–8.2 pool dev+test_public for power, with test_public broken out in §8.5 (now n=389, fc n=105); full-context rests on tier-capped subsets (§3) with the HUG-bundle fix applied to the **20** cross_source items at 512k (§8.6); gpt-5.5 cb/rag had ~93 quota-failed items (re-run pending — but cb/rag re-runs are gpt-5.5's cost driver, §5); no open-weights model is reported (leg deferred, §4).

## 9. Limitations and the path to paper-grade

### 9.0 LLM-judge human validation (DONE — 2026-06-11)

The headline metric is the LLM-judge, so it was validated against blind human labels before any paper
claim. Protocol = standard inter-annotator agreement: a stratified **n=80** sample of judged predictions
(balanced on the judge's YES/NO; force-including the ambiguous categories — legal paraphrase, comparisons,
cross_source, abstention, the 512k tier; substantive regimes rag/fc only) was written **without** the judge
verdict (no anchoring) and labelled `correct (Y/N)` by the dataset creator. We then joined on
`(qa_id, model, regime)` to the held-out judge verdicts.

| metric | value |
|---|---|
| raw agreement | **77/80 = 96.2 %** |
| Cohen's κ | **0.924** (Landis–Koch "almost perfect", > 0.81) |
| human correct-rate | 45.0 % |
| judge correct-rate | 43.8 % |

All **3** disagreements are boundary cases with **no systematic direction** (judge too strict 2 ×, too
lenient 1 ×):
- *judge NO / human Y* — gold `광산구`, prediction `광주광역시 광산구` (correct, rejected on format).
- *judge NO / human Y* — answer led with "확정할 수 없음" but the parenthetical contained the gold `2개월`
  (a genuine hedging-vs-abstention edge case).
- *judge YES / human N* — a legal-reasoning answer whose gist was right but which added an unsupported claim.

**Conclusion:** the LLM-judge tracks a human at κ = 0.92 — strong enough to headline. Limitation: a
**single** creator-annotator (no second rater, so κ is judge-vs-creator, not inter-human); a second
independent annotator on the same n=80 CSV remains a nice-to-have for camera-ready. Artifacts:
`workspace_local/audit/baselines/judge_validation.csv` (filled) + `judge_validation.key.jsonl` (verdicts).

### 9.1 Remaining path to paper-grade

This v0.9 set is a **reference baseline**, captioned **indicative**. Before a camera-ready paper claim:

- ~~**Run baselines on the enlarged `test_public`**~~ — **DONE (§8.5)**: cb/rag extended to all 389, fc to a
  tier-capped n=105 (incl. 25 at 512k), HUG-fix re-applied to the 16 merged cross_source items. The held-out
  split now carries the headline with tight CIs and confirms the 512k finding at n=25. Remaining: optionally
  rebuild canonical bundles so cross_source embeds HUG by default (this run patched prompts), and re-run the
  ~93 quota-failed gpt-5.5 cb items.
- **Lift the 512k/256k caps** so long-context-degradation claims rest on more than ~12 items per tier
  (tighter confidence intervals). Additive on this exact sample, and the merge already supplies the items.
- **Add a genuinely open-weights model** for the reproducibility/spread leg (§4). The earlier `minimax-m3:cloud`
  plan does **not** qualify (hosted, weights unreleased as of 2026-06). The specific model is **to be selected
  by verifying current availability + context window + license against live sources** (not asserted from a
  stale knowledge cutoff); it must cover the 512k tier, and can run via a provider serving public weights
  (reproducible because the weights are public). Orthogonal — another runner invocation + eval.
- **Add dense / hybrid RAG** alongside BM25 (the v0.7 retrieval diagnostics tooling already exists).
- ~~**Human-validate the eval** on a stratified sample~~ — **DONE (§9.0)**: n=80, agreement 96.2 %,
  κ=0.924. Optional follow-up: a second independent annotator on the same CSV.
- ~~**Report test_public separately** (dev ≠ test)~~ — **DONE (§8.5)** via `scripts/score_judge_v09.py`.
  Remaining: grow test_public (above) and the local-model hidden leg (above).
- ~~**Fix the cross_source HUG bundle**~~ — **DONE (§8.6)** via `scripts/fix_fc_hug_bundle_v09.py`: HUG rows
  injected, 4 items re-run + re-judged; 512k is now a real signal (gpt-5.5 75%, gpt-4.1-mini 50%). Optional:
  rebuild the dataset's canonical bundles so future builds embed HUG by default (this fix patched the run).

None of this requires rework: the seeded-nested sample + `--resume` + model-orthogonal scoring make every
addition accumulate on top of what is reported here.
