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
| `gpt-4.1-mini` | proprietary, hosted (OpenAI) | **~1M tokens (verified)** | runs all regimes; data-sharing free/paid tier is acceptable on dev/test_public (public splits) but **never on hidden gold** |
| `gemma4:12b` | open weights, local | 256K | served via `ollama` on `tts-dev-003` (RTX 3090, 24GB); **must set `num_ctx=65536`** or the 64k bundle is silently truncated; ≤256k tiers only; **the non-data-sharing path for eventual hidden-split baselines** |

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

`gemma4:12b` runs (all regimes it can fit) cost $0 (local GPU). Runs are chunked across days via `--resume`
to respect rate limits; cost is bounded, not free-tier-gated.

## 6. Commands (to be finalized as the runners are wired)

```bash
# 1. draw the fixed sample (deterministic; internal output)
python3 scripts/build_baseline_sample_v09.py            # seed 20260610, caps 512k=12 / 256k=16

# 2. run each regime/model into workspace_local/audit/baselines/ (resumable, daily chunks)
#    closed-book   : scripts/run_llm_baseline_v07.py (locator-only prompts)
#    full-context  : full-context prompts (bundle text embedded) over baseline_sample_v09.fc.jsonl
#    RAG (BM25)    : BM25-retrieved context over baseline_sample_v09.jsonl
#    gemma4:12b    : --provider ollama --base-url <ssh-tunnelled 3090>, num_ctx=65536

# 3. score every prediction file
python3 scripts/eval_harness_v06.py --pred workspace_local/audit/baselines/<file>.jsonl
```

## 7. Results

**TBD** — populated as runs complete. Tables will report plain + cluster-weighted accuracy overall and cut
by split / task_type / context_tier / question_style, per (model × regime), with model ids, context limits,
retrieval settings, cost, and run date. The cluster-weighted metric stays the headline.

## 8. Limitations and the path to paper-grade

This v0.9 set is a **reference baseline**, captioned **indicative**. Before a camera-ready paper claim:

- **Lift the 512k/256k caps** so long-context-degradation claims rest on more than ~12 items per tier
  (tighter confidence intervals). Additive on this exact sample.
- **Add 1-2 models** (e.g. `gpt-5-mini`, an open Qwen) to show the spread. Orthogonal — just another runner
  invocation and eval.
- **Add dense / hybrid RAG** alongside BM25 (the v0.7 retrieval diagnostics tooling already exists).
- **Human-validate the eval** on a stratified sample (separate v0.9 Priority 0.2), and note that
  `contains_all` scoring can over-credit partial matches.
- **Hidden-split baselines** run only through the local non-data-sharing model (`gemma4:12b`), never an
  OpenAI data-sharing tier.

None of this requires rework: the seeded-nested sample + `--resume` + model-orthogonal scoring make every
addition accumulate on top of what is reported here.
