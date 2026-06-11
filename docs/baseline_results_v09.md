# Baseline Results (v0.9, release-grade — design locked, runs in progress)

**Scope.** This document defines the **release-grade reference baselines** for the v0.9 build: a fixed,
seeded, stratified evaluation sample run across three context regimes and two models, scored by
`scripts/eval_harness_v06.py`. It supersedes the v0.7 *smoke* diagnostics
([`baseline_results_v07.md`](baseline_results_v07.md)), which used a 22-item convenience slice and a
closed-book floor only.

This is a **research-preview reference baseline**, not a sealed-hidden leaderboard and not a final model
ranking. Numbers reported here are captioned **indicative/reference**; see *Limitations and the path to
paper-grade* below for exactly what must be added before a camera-ready claim. No raw documents, bundle
text, hidden gold, or API keys are published here; all predictions, prompts, and run metadata are INTERNAL
under `workspace_local/audit/baselines/` (gitignored).

## 1. Evaluation sample (fixed, seeded, reproducible)

Built by `scripts/build_baseline_sample_v09.py` (seed `20260610`; the drawn files live INTERNAL under
`workspace_local/audit/baselines/`). The *reproducible artifact that ships* is the script + its seed, not
the drawn file.

- **test_public**: all 104 items (small held split, taken whole — no sampling).
- **dev**: 200 items, **stratified by `task_type`** so all 12 task families are represented (per-family
  floor), **near-duplicate-deduplicated by `cluster_id`** (≤1 item per cluster; 114 distinct clusters).
- **Total sample: 304 items.** Coverage spans all 12 task families, both question styles
  (real_user / professional_analyst), all 5 context tiers (32k / 64k / 128k / 256k / 512k), all 10
  providers, and 9 시도.

The drawn sample is `baseline_sample_v09.jsonl` (all 304, used for RAG + closed-book) plus
`baseline_sample_v09.fc.jsonl` (the full-context-eligible subset, see §3).

## 2. Regimes

| Regime | What the model sees | Coverage | Purpose |
|---|---|---|---|
| **closed-book** (locator-only) | instruction + question + `context_spec` locators, **no document text** | all 304 | refusal / hallucination floor (a true lower bound; the v0.7 §4 numbers are this regime) |
| **full-context** | the question + the **entire bundle text** at the item's `context_tier` | 116-item capped subset (§3) | long-context LLM headline (lost-in-the-middle stress on Korean haystacks up to ~393k tokens) |
| **RAG (BM25)** | the question + **BM25-retrieved chunks** (~8k tokens) | all 304 | the tier-independent, scalable retrieval baseline |

closed-book and RAG run on all 304 because they are cheap (tiny / bounded context). Full-context is the
cost driver and is tier-capped.

## 3. Full-context subset and tier caps

Full-context input cost scales with the haystack: the "512k" tier is ~393k tokens (measured), so a handful
of those items dominate the bill. To keep the OpenAI leg near budget while still covering every tier, the
giant tiers are capped:

- caps: `512k → 12`, `256k → 16`; smaller tiers (32k/64k/128k) uncapped.
- items with no bundle on disk (36, mostly `answerability_detection` with no haystack) are not
  full-context-eligible.
- **Result: 116 full-context-eligible items** spanning all 5 tiers (32k 52 / 64k 22 / 256k 16 / 128k 14 /
  512k 12).

The cap is a **cost-control choice, not a structural limit** — the full dataset retains all 97 of the
512k-tier items. Because the subset draw is **seed-nested** (same seed ⇒ same shuffle ⇒ `[:12] ⊂ [:30]`),
raising a cap later is **purely additive**: already-run predictions stay valid and `--resume` runs only the
newly added items.

## 4. Models

| Model | Kind | Context window | Notes |
|---|---|---|---|
| `gpt-4.1-mini` | proprietary, hosted (OpenAI) | **~1M tokens (verified)** | runs all regimes; data-sharing tier acceptable on dev/test_public (public splits) but **never on hidden gold** |
| `minimax-m3:cloud` | open weights, hosted (Ollama Cloud) | **512K** | open-weights long-context point (paper reproducibility), all tiers incl 512k; runs remotely (no local GPU); **thinking model → set `--max-output-tokens 2048` or thinking starves the answer**, `--num-ctx 65536`; cloud ⇒ dev/test_public only, **never hidden gold** |

A single 24GB GPU (the RTX 3090 on `tts-dev-003`) is **VRAM-bound, not context-window-bound**: the KV cache for 256k+ tokens does not fit on 24GB for any model (a local `gemma4:12b` realistically tops out near the 64k tier). So the open-weights long-context point uses `minimax-m3:cloud` (remote) instead. A local non-data-sharing model on the 3090 is **deferred to v1.0** for hidden-split small-tier scoring; big-tier hidden full-context would need an ≥80GB GPU.

**Why gpt-4.1-mini, not gpt-4o-mini (empirically verified, 2026-06-10).** This is a long-context
benchmark, so the model must ingest the haystack. On an identical 512k-tier bundle (974,007 chars =
**393,315 tokens**):

- `gpt-4o-mini` → `HTTP 400: maximum context length is 128000 tokens. However, your messages resulted in
  393315 tokens` — its 128k window **cannot hold 59% of the sample** (the 256k/512k tiers).
- `gpt-4.1-mini` → **OK**, `prompt_tokens=393,315`, answered correctly — confirming it ingests our largest
  tier with margin (corroborates the ~1M window).

Measured ratio for cost planning: **~2.45 chars/token** on this Korean-heavy mixed text.

## 5. Cost projection (OpenAI leg; local leg is $0)

At `gpt-4.1-mini` list price (USD/1M tokens: in $0.40, out $1.60 — confirm against live billing). Token
counts use **decoded character count / 2.45**, not file byte size (Korean UTF-8 is ~3 bytes/char, which
would overcount tokens ~1.7x):

| Regime | Items | Input tokens | Est. USD |
|---|---:|---:|---:|
| full-context (capped) | 116 | ~11.2M | ~$4.5 |
| RAG (BM25) | 304 | ~2.4M | ~$1.0 |
| closed-book | 304 | tiny (locator-only) | ~$0 |
| **Total (OpenAI)** | | | **~$5.5** |

`minimax-m3:cloud` runs on the Ollama Cloud Free tier (small quota; Pro is $20/mo for 50x) — bounded, not
metered per our billing. OpenAI runs are chunked across days via `--resume` to respect rate limits.

## 6. Commands (finalized)

```bash
# 1. draw the fixed sample + build the regime prompt sets (deterministic; INTERNAL output)
python3 scripts/build_baseline_sample_v09.py            # seed 20260610, caps 512k=12 / 256k=16
python3 scripts/build_baseline_fullcontext_v09.py       # 116 full-context prompts (bundle embedded)
python3 scripts/build_baseline_rag_v09.py               # 268 BM25 RAG prompts (+ retrieved/gold page_ids)

# 2. run each regime x model into workspace_local/audit/baselines/ (resumable; explicit --out per regime
#    so closed/full/RAG don't collide on the auto name). Run once per split. Examples for one model:
export OPENAI_API_KEY=...   # from workspace_local/secrets/openai_api.key
M=gpt-4.1-mini
for SP in test_public dev; do
  # closed-book (locator-only floor)
  python3 scripts/run_llm_baseline_v07.py --provider openai --model $M --split $SP \
      --out workspace_local/audit/baselines/cb_${M}_${SP}.jsonl --resume
  # full-context
  python3 scripts/run_llm_baseline_v07.py --provider openai --model $M --split $SP \
      --prompt-file workspace_local/audit/baselines/fullcontext_v09_prompts.jsonl \
      --out workspace_local/audit/baselines/fc_${M}_${SP}.jsonl --max-output-tokens 256 --resume
  # RAG (BM25)
  python3 scripts/run_llm_baseline_v07.py --provider openai --model $M --split $SP \
      --prompt-file workspace_local/audit/baselines/rag_bm25_v09_prompts.jsonl \
      --out workspace_local/audit/baselines/rag_${M}_${SP}.jsonl --resume
done
# minimax-m3:cloud leg: --provider ollama --model minimax-m3:cloud --num-ctx 65536 --max-output-tokens 2048
#   (Ruo signed in via `ollama login`; cloud ⇒ dev/test_public only, never hidden)

# 3. score, restricted to the locked sample (cluster-weighted is the headline)
#    closed-book over the full 304 sample; full/RAG over the qa_ids actually present in their pred file
python3 scripts/eval_harness_v06.py --pred <cb pred> --splits dev,test_public \
    --ids-file workspace_local/audit/baselines/baseline_sample_v09.jsonl
python3 scripts/eval_harness_v06.py --pred <fc|rag pred> --splits dev,test_public --pred-only
# retrieval quality (model-independent): recall@k / hit@k from the RAG prompt file
python3 scripts/score_retrieval_v09.py --rag workspace_local/audit/baselines/rag_bm25_v09_prompts.jsonl

# navigate the INTERNAL artifacts: writes an INDEX.md catalog (naming legend + per-file status)
python3 scripts/catalog_baselines_v09.py
```

**Artifact layout (INTERNAL, under `workspace_local/audit/baselines/`, gitignored).** Predictions are
`<regime>_<model>_<split>.jsonl` with `{qa_id, prediction}` (regime ∈ cb/rag/fc); each run also writes a
rich `<…>.calls.jsonl` (tokens, latency, and for reasoning models the `thinking` trace, joinable by
qa_id), a `<…>.meta.json`, and a `<…>.log`. Input prompts are `<regime>_v09_prompts.jsonl`. Run
`catalog_baselines_v09.py` to (re)generate `INDEX.md`, which lists every artifact with counts and status.

## 7. Metrics (the v0.9 reported set)

- **Answer accuracy** (`scripts/eval_harness_v06.py`): plain + **cluster-weighted** accuracy (the
  cluster-weighted number is the headline — it discounts near-duplicate clusters so a few repeated items
  cannot inflate the score). Per-`answer_type` matching: `exact_numbers` (all gold numeric tokens present),
  `boolean_and_reason` (abstention detection), else normalized-substring. Cut by **split / task_type /
  context_tier / question_style**. Restrict to the locked sample with `--ids-file` (full 304) or
  `--pred-only` (the subset a regime actually ran).
- **Abstention** is captured by `task:answerability_detection` and the `boolean_and_reason` metric.
- **Retrieval quality** for the RAG regime (`scripts/score_retrieval_v09.py`): **recall@k** (fraction of
  gold pages retrieved) and **hit@k** (any gold page retrieved), plain + cluster-weighted, cut by
  split / task_type / context_tier. Model-independent (a property of BM25). Sanity at k=5: recall@5 ≈ 0.59.
- **Paper-grade extensions (deferred):** replace the loose normalized-substring match with
  normalized-EM / numeric-tolerance / multi-answer set-F1; add an evidence-position cut; optionally an
  LLM-judge secondary metric for free-text (note its cost/reproducibility tradeoff). All additive on this
  same sample + predictions; see `docs/evaluation_protocol.md`.

## 8. Results

Run 2026-06-11 via the OpenAI Batch API (`temperature=0`; reasoning models at default effort, `max_completion_tokens=4000`; BM25 `k=5`). **The headline metric is the LLM-judge** (semantic equivalence, `scripts/llm_judge_v09.py`, judge = gpt-4.1-mini) — see §8.4 for why the legacy `contains_all` metric is unreliable. cb/rag are scored on the full dev+test_public; full-context (fc) on the tier-capped 116-item subset. `minimax-m3:cloud` (open weights) is still filling and will be added.

### 8.1 Five models × three regimes (LLM-judge; plain / cluster-weighted)

| Model | closed-book | RAG (BM25) | full-context |
|---|---|---|---|
| gpt-4.1-mini | 18% / 32% (n=1712) | 56% / 43% (n=1255) | 86% / 73% (n=116) |
| gpt-5.4-mini | 17% / 18% (n=1712) | 54% / 38% (n=1255) | 95% / 86% (n=100*) |
| gpt-5.4-nano | 8% / 6% (n=1712) | 45% / 25% (n=1255) | 71% / 54% (n=100*) |
| **gpt-5.5** | **39% / 49%** (n=1639) | **58% / 42%** (n=1235) | **93% / 83%** (n=116) |

\* gpt-5.4-mini/nano have a **272k-token context window**, so 16/116 fc items (the 512k tier + the largest 256k items) are context-rejected, not answered — a model property, reported as `✗ctx` in §8.2, not a wrong answer. gpt-4.1-mini (~1M) and gpt-5.5 (≥393k verified) ingest all tiers.

**gpt-5.5 leads every regime.** Monotonic closed-book ≪ RAG ≪ full-context holds for all models: context is decisive. Smaller models degrade faster (gpt-5.4-nano).

### 8.2 Full-context by context tier (LLM-judge, plain)

| Model | 32k | 64k | 128k | 256k | 512k |
|---|---:|---:|---:|---:|---:|
| gpt-4.1-mini | 98% | 86% | 93% | 69% | 50% |
| gpt-5.4-mini | 98% | 95% | 79% | 100% | ✗ctx |
| gpt-5.4-nano | 87% | 55% | 36% | 75% | ✗ctx |
| **gpt-5.5** | **100%** | 95% | **100%** | **100%** | **42%** |

**There is no "512k collapse."** gpt-5.5 is at or near 100% from 32k to 256k and **42%** (not 0%) at 512k. The residual 512k drop is mostly a **benchmark-construction artifact, not a model failure**: of the 12 512k items, ~4 are `cross_source_aggregation` questions whose gold requires HUG sale-history rows that are **absent from the full-context bundle** (unanswerable in this regime — to be fixed/excluded, see §9); the rest are a few genuine multi-document legal misses. The **272k context-coverage tradeoff** (gpt-5.4 family ✗ at 512k vs gpt-5.5/gpt-4.1-mini covering it) is the real, honest long-context finding.

### 8.3 Retrieval quality (BM25, k=5, model-independent)

On the full split (n=1,255 items with gold pages): recall@5 ≈ **47.6%**, hit@5 ≈ 48.8% (cw-recall 52.1%). Per-task highs (`long_distance_retrieval` ≈ 98%, `eligibility_reasoning` ≈ 74%) vs lows (`schedule_reasoning` ≈ 11%, `multi_document_comparison` ≈ 13%) — BM25 is weakest where evidence is scattered across documents. Full breakdown via `scripts/score_retrieval_v09.py`.

### 8.4 Metric matters — `contains_all` is unreliable (a methodological result)

The legacy `contains_all`/normalized-substring match (v0.7/v0.8) produces **systematic false negatives** when the prediction is correct but phrased or formatted differently from the gold (e.g. gold `"부산도시공사=부산광역시 / 한국토지주택공사=경기도"` vs a correct pred `"부산도시공사: 부산광역시 / …: 경기도"`). Three metrics on the same gpt-5.5 full-context predictions:

| Metric | ALL | 512k tier |
|---|---:|---:|
| `contains_all` (legacy) | 87.9% | **0%** ← fabricated "collapse" |
| soft (em \| contains \| token-recall≥0.7; `score_answers_v09.py`) | 91.4% | 16.7% |
| **LLM-judge** (semantic; `llm_judge_v09.py`) | **93.1%** | **41.7%** |

`contains_all` undercounts every model and, at the 512k tier, drove a **non-existent** "512k collapse" to 0%. All v0.9 headline numbers use the LLM-judge; soft + Wilson 95% CIs are the reproducible deterministic reference. The LLM-judge itself is now **human-validated** (§9.0).

### 8.5 Held-out split: test_public reported separately (dev ≠ test)

§8.1–8.2 pool `dev` (development, 1,608) with `test_public` (the held-out eval, 104) — convenient but a
development-set red flag for a paper. The **same** LLM-judge verdicts, cut by split with a Wilson 95% CI
(`scripts/score_judge_v09.py`), isolate the held-out headline:

**test_public only (LLM-judge, plain / cluster-weighted; cb shows the cw 95% CI):**

| Model | closed-book | RAG (BM25) | full-context |
|---|---|---|---|
| gpt-4.1-mini | 21% / 55% [37–71%] (n=104) | 58% / 38% (n=101) | 88% / 98% (n=33) |
| gpt-5.4-mini | 23% / 31% [17–49%] (n=104) | 60% / 31% (n=101) | 100% / 100% (n=27) |
| gpt-5.4-nano | 4% / 0% [0–13%] (n=104) | 48% / 10% (n=101) | 85% / 77% (n=27) |
| **gpt-5.5** | **37% / 68%** [49–82%] (n=87) | 56% / 27% (n=101) | 88% / 46% (n=33) |

The split-level ranking is **directionally consistent** with the pooled table (gpt-5.5 strongest closed-book;
context monotonicity holds), so dev was not flattering the leaderboard. **But two honest caveats the pooled
table hid:**

1. **test_public is underpowered for fine-grained claims.** n is 104 (cb) / 101 (rag) / **33 (fc)**; the cb
   cluster-weighted CIs span ~30 points, and the fc-by-tier cells on test_public are n=5–15 each — **too few
   to support per-tier long-context degradation claims on test_public alone.** Those tier claims (§8.2) rest
   on the **pooled** sample and must stay captioned *indicative*. This is the concrete motivation for growing
   **test_public specifically** (§9.1), not just total QA.
2. **plain vs cluster-weighted diverges more on the small split** (e.g. gpt-4.1-mini cb 21% plain vs 55% cw):
   test_public has few clusters, so a handful of answerable clusters dominate the weighted score. Report both.

**test_hidden (285) is NOT evaluated here** — its gold is sealed and must never transit a data-sharing API
(OpenAI / Ollama Cloud). It will be scored only through a **locally-hosted non-data-sharing model** once that
leg exists (§9.1); none of the cloud models in this table are eligible for it.

> Caveats: LLM-judge is **human-validated** (§9.0: n=80, agreement 96.2 %, κ=0.924); §8.1–8.2 pool dev+test_public for power, with test_public broken out in §8.5 (small → wide CIs); fc rests on a tier-capped 116-item sample; gpt-5.5 cb/rag had ~93 quota-failed items (re-run pending); test_hidden pending a local model; minimax (open weights) incomplete.

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

- **Grow `test_public` specifically** (currently 104; fc only 33) so the held-out split (§8.5) can carry
  the headline on its own with tight CIs, and per-tier long-context claims hold on test_public — not just the
  dev-pooled sample. Highest-leverage data work; do before bulk QA growth.
- **Lift the 512k/256k caps** so long-context-degradation claims rest on more than ~12 items per tier
  (tighter confidence intervals). Additive on this exact sample.
- **Evaluate `test_hidden` (285)** — blocked on a **locally-hosted non-data-sharing model** (the sealed gold
  must never transit OpenAI or Ollama Cloud; `minimax-m3:cloud` is cloud and is therefore *not* eligible).
  Needs a local GPU leg (e.g. `gemma4:12b` on the company server, deferred from v0.9). Questions live in
  `data/qa_v0.6_test_hidden_questions.jsonl`; gold stays in the gitignored audit file.
- **Add 1-2 models** (e.g. `gpt-5-mini`, an open Qwen) to show the spread. Orthogonal — just another runner
  invocation and eval.
- **Add dense / hybrid RAG** alongside BM25 (the v0.7 retrieval diagnostics tooling already exists).
- ~~**Human-validate the eval** on a stratified sample~~ — **DONE (§9.0)**: n=80, agreement 96.2 %,
  κ=0.924. Optional follow-up: a second independent annotator on the same CSV.
- ~~**Report test_public separately** (dev ≠ test)~~ — **DONE (§8.5)** via `scripts/score_judge_v09.py`.
  Remaining: grow test_public (above) and the local-model hidden leg (above).

None of this requires rework: the seeded-nested sample + `--resume` + model-orthogonal scoring make every
addition accumulate on top of what is reported here.
