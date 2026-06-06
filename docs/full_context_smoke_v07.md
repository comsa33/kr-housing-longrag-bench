# Full-Context Baseline Smoke (v0.7)

**Scope.** A small **smoke test** of the full-context (class A) pipeline — not a full benchmark, not a
leaderboard, not human-validated, not sealed-hidden, and not a final model ranking. It shows that the
runner can feed real long-context bundle text to a model and that scoring works, and it quantifies the
locator-only → full-context lift on a single small slice. Numbers below come from 22 `test_public` items
only (one task family, three bundles), so they are illustrative, not generalizable.

Full-context **prompts embed raw bundle text**, so they (and the predictions) are kept **INTERNAL** under
`workspace_local/audit/baselines/` (gitignored). No bundle text or full-context prompt is published here.

## 1. Sample selection

Deterministic (sorted by `qa_id`, no RNG), via `scripts/build_full_context_smoke_v07.py`:

- split `test_public`, `bundle_id` present, `context_tier` ∈ {32k, 64k} (small tiers chosen to keep cost
  low and to fit smaller-context models).
- This slice happens to be **22 items, all `long_context_retrieval`, over 3 bundles** — so task-type
  balancing was **not possible** here (the 32k/64k bundle-bearing `test_public` items are all one family).
  Tier mix: 32k ×15, 64k ×7. The smoke therefore measures full-context lift on retrieval items.

Each selected QA gets a full-context prompt = `instruction` + the bundle text from
`workspace_local/processed/bundles-v06/<bundle_id>.txt` + `question`, written to the INTERNAL file
`workspace_local/audit/baselines/full_context_smoke_prompts.jsonl` (avg ≈ 31.7k input tokens/item).

## 2. Commands

```bash
# 1) build the INTERNAL full-context prompts (embeds bundle text; stays under workspace_local/)
python3 scripts/build_full_context_smoke_v07.py            # 22 items, tiers 32k/64k

# 2) run (at most 2 OpenAI models); --out keeps a distinct name from the locator-only files
B=workspace_local/audit/baselines
export OPENAI_API_KEY=...
uv run --extra baseline python scripts/run_llm_baseline_v07.py --provider openai --model gpt-4o-mini \
    --split test_public --prompt-file $B/full_context_smoke_prompts.jsonl \
    --out $B/fullctx_openai_gpt-4o-mini_test_public.jsonl --max-output-tokens 512 --sleep-seconds 0.2
uv run --extra baseline python scripts/run_llm_baseline_v07.py --provider openai --model gpt-5.4 \
    --split test_public --prompt-file $B/full_context_smoke_prompts.jsonl \
    --out $B/fullctx_openai_gpt-5.4_test_public.jsonl --max-output-tokens 4000 --sleep-seconds 0.2
```

The runner uses a record's `prompt` field directly when present (full-context), otherwise it builds the
locator-only prompt — so the same runner serves both regimes.

## 3. Results — locator-only vs full-context, SAME 22 qa_ids (2026-06-06, OpenAI)

Scored with `scripts/eval_harness_v06.py`'s scorer on the same 22 `qa_id`s (test_public, 32k/64k,
`long_context_retrieval`). 22/22 predictions, 0 errors per run.

| Model | locator-only (no doc text) | full-context (doc embedded) | lift |
|---|---:|---:|---:|
| gpt-4o-mini | 0/22 = 0.0% | 13/22 = **59.1%** | +59 pp |
| gpt-5.4 | 1/22 = 4.5% | 19/22 = **86.4%** | +82 pp |

What it shows:

- Adding the document text turns a near-zero closed-book floor into a usable score — the lift (+59 / +82
  pp) is the value of actually reading the long context, measured on identical questions.
- With full context, **model differentiation becomes meaningful**: gpt-5.4 (86.4%) > gpt-4o-mini (59.1%)
  on this slice. (Recall that on locator-only both were ~floor; see `docs/baseline_results_v07.md`.)
- Spot-checked answers are genuine reads (e.g. gpt-5.4 returns `59㎡` / `390세대` / `74㎡` lifted from the
  embedded announcement), not format guesses.

Reproduce via the official harness — `--pred-only` scores only the qa_ids present in the prediction file
(the same-22 subset), so unrun items do not dilute it:

```bash
B=workspace_local/audit/baselines
python3 scripts/eval_harness_v06.py --pred $B/fullctx_openai_gpt-4o-mini_test_public.jsonl --pred-only --splits test_public
python3 scripts/eval_harness_v06.py --pred $B/fullctx_openai_gpt-5.4_test_public.jsonl   --pred-only --splits test_public
# same 22 ids, locator-only side (use --ids-file with any qa_id list or JSONL carrying qa_id):
python3 scripts/eval_harness_v06.py --pred $B/openai_gpt-5.4_test_public.jsonl --ids-file $B/full_context_smoke_prompts.jsonl --splits test_public
```

Each prints `[subset: 22 of 105 gold items]` and reproduces the table above (e.g. gpt-5.4 full-context
19/22 = 86.4%). Without `--pred-only`/`--ids-file` the harness scores the full 105-item split, so the
unrun items count as incorrect and dilute the number.

## 4. Cost

| Model | items | input tokens | max_output | approx cost |
|---|---:|---:|---:|---:|
| gpt-4o-mini | 22 | ~0.70M (avg ~31.7k/item) | 512 | ~$0.1 |
| gpt-5.4 | 22 | ~0.70M | 4000 | ~$2–3 |

Total ≈ a few dollars (exact per-model price varies — confirm on the provider pricing page). Measured via
`tiktoken` (o200k). Predictions/metadata are INTERNAL under `workspace_local/audit/baselines/`.

## 5. Caveats

- **Smoke only**: 22 items, one task family (`long_context_retrieval`), 3 bundles, 32k/64k tiers. Not a
  benchmark result and not generalizable; no leaderboard / human-validated / final-ranking claim.
- Full `test_public` full-context was **not** run (high cost — the 256k/512k tiers dominate the split and a
  flagship full sweep would exceed the working budget). Run it only with explicit approval; only 7 distinct
  bundles back `test_public`, so prompt caching should cut cost materially.
- The lenient `contains_all` scorer can over-credit partial matches; numbers are indicative.
- Model labels are the exact OpenAI model ids supplied to the API on the run date, not a public-model
  ranking claim. `gpt-5.4` is the only gpt-5-line model reported.
- Bundle text and full-context prompts are internal and rebuilt locally; nothing here publishes them.
