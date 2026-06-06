# Baseline Results (v0.7, draft — scaffold)

**Scope.** This document describes the **provider-agnostic baseline runner scaffold**
(`scripts/run_llm_baseline_v07.py`) and how to produce/score prediction files. It does **not** contain
final benchmark results. No real model results are reported here unless an explicit paid run was executed
and recorded under `workspace_local/audit/baselines/`. This is a research-preview scaffold, not a
leaderboard, not human-validated, not sealed-hidden, and makes no perfect / hallucination-free claim.

As of this draft, only **offline smoke tests** (`--dry-run`, `--mock`) have been run — no paid API calls.
The results tables below are intentionally left empty pending real runs.

## 1. What the runner does

`scripts/run_llm_baseline_v07.py` reads the PUBLIC locator-only prompt file
(`data/qa_v0.6_prompts.jsonl`), builds a deterministic prompt per QA from `instruction` + `question` +
`context_spec` locators (no raw document text), calls one provider, and writes
`{"qa_id": ..., "prediction": ...}` JSONL that `scripts/eval_harness_v06.py` scores.

It is therefore a **locator-only / closed-book** baseline (the model sees *where* the evidence is, not the
text). A full-context variant (embedding bundle text via `make_prompt_v06.py --inline-context`) would be a
separate, explicitly-requested INTERNAL mode — see `docs/baseline_protocol_v06.md` class A.

All predictions, run logs (`.log`), and run metadata (`.meta.json`) are written **only** under
`workspace_local/audit/baselines/` (gitignored, internal). The runner refuses an `--out` path outside
`workspace_local/`. Hidden-split predictions stay internal and are never published.

## 2. Provider support

| Provider (`--provider`) | SDK / transport | Required env | Notes |
|---|---|---|---|
| `openai` | `openai` (extra `baseline`) | `OPENAI_API_KEY` | chat.completions |
| `azure_openai` | `openai` (extra `baseline`) | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION` | `--model` = Azure **deployment** name |
| `anthropic` | `anthropic` (extra `baseline`) | `ANTHROPIC_API_KEY` | messages API |
| `gemini` | `google-generativeai` (extra `baseline`) | `GEMINI_API_KEY` **or** `GOOGLE_API_KEY` | `GenerativeModel.generate_content` |
| `ollama` | **stdlib HTTP** (no SDK) | none (optional `OLLAMA_BASE_URL`, default `http://localhost:11434`) | needs a local `ollama serve` + pulled model |

SDKs are an **optional** pyproject extra and are imported **lazily** inside each adapter, so `--help`,
`--dry-run`, and `--mock` work with plain `python3` and no SDKs installed. Install provider SDKs with:

```bash
uv sync --extra baseline        # or: pip install 'kr-housing-longrag-bench[baseline]'
```

Public dataset validation/scoring never needs these SDKs (plain `python3` + stdlib).

## 3. Commands

Dry-run (prints planned requests; no SDK/key/API; writes nothing):

```bash
python3 scripts/run_llm_baseline_v07.py --provider openai --model gpt-4o-mini --split dev --limit 3 --dry-run
python3 scripts/run_llm_baseline_v07.py --provider ollama --model llama3.1     --split dev --limit 3 --dry-run
```

Offline plumbing smoke (deterministic fake response; writes a real prediction file; no key/SDK):

```bash
python3 scripts/run_llm_baseline_v07.py --provider openai --model mockmodel --split dev --limit 5 --mock
python3 scripts/eval_harness_v06.py --pred workspace_local/audit/baselines/openai_mockmodel_dev.jsonl --splits dev
```

Real sample run (needs the provider key; small smoke first, then full split):

```bash
export OPENAI_API_KEY=...      # provider-specific; see table above
python3 scripts/run_llm_baseline_v07.py --provider openai --model gpt-4o-mini --split dev --limit 20 \
    --temperature 0.0 --max-output-tokens 512 --sleep-seconds 0.5
# resume after an interruption / rate-limit:
python3 scripts/run_llm_baseline_v07.py --provider openai --model gpt-4o-mini --split dev --resume
python3 scripts/eval_harness_v06.py --pred workspace_local/audit/baselines/openai_gpt-4o-mini_dev.jsonl --splits dev
```

Reasoning models (OpenAI `gpt-5*`, `o1`/`o3`/`o4*`): the adapter automatically sends
`max_completion_tokens` instead of `max_tokens` and omits `temperature` (these models reject the legacy
params). Use a **larger** `--max-output-tokens` (e.g. 4000) so reasoning tokens do not starve the answer:

```bash
python3 scripts/run_llm_baseline_v07.py --provider openai --model gpt-5.4 --split test_public \
    --max-output-tokens 4000 --sleep-seconds 0.1
```

Outputs per run (all internal):
`workspace_local/audit/baselines/<provider>_<model>_<split>.jsonl` (predictions),
`…​.meta.json` (provider, model, split, prompt_file, started/finished_at, limit, temperature,
max_output_tokens, counts, command args), `…​.log` (per-item errors).

## 4. Results — locator-only baseline (test_public, 2026-06-06)

First real runs (OpenAI, **locator-only / closed-book**: prompts carry no document text). 105/105
predictions written, 0 errors each; scored by `eval_harness_v06.py --splits test_public`. Predictions and
metadata are INTERNAL under `workspace_local/audit/baselines/`.

| Provider | Model | Split | Mode | Plain acc | Cluster-weighted | Date | Cost |
|---|---|---|---|---:|---:|---|---|
| openai | gpt-4o-mini | test_public (105) | locator-only | 3.8% (4/105) | 0.2% | 2026-06-06 | ~cents |
| openai | gpt-4o | test_public (105) | locator-only | 3.8% (4/105) | 0.2% | 2026-06-06 | ~cents |
| openai | gpt-5.4 | test_public (105) | locator-only | **6.7% (7/105)** | 0.3% | 2026-06-06 | ~cents |

Token basis (measured): test_public ≈ 31k input + ~9k output tokens per model; gpt-5.4 used
`max_completion_tokens` with ~0 reasoning tokens on these prompts, so total cost across all three runs was
a few cents (exact per-model price varies — confirm on the provider pricing page).

**What this shows.** In the locator-only setting the model sees *where* the evidence is, not the text, so a
well-behaved model correctly refuses ("제공된 자료만으로는 확정할 수 없음") instead of hallucinating. Only the
4 `answerability_detection` items are answerable without content, so **≈3.8% is effectively the ceiling**:
gpt-4o-mini == gpt-4o (3.8%); gpt-5.4 reaches 6.7% by getting a few retrieval items right, but the score is
dominated by the closed-book setting, not model strength. **Model comparison is therefore not meaningful on
locator-only** — it is a true lower bound and a no-hallucination check, not a capability ranking. Real model
differentiation requires the INTERNAL full-context (class A) mode (`make_prompt_v06.py --inline-context`,
which embeds bundle text) — a separate, explicitly-requested run. Compare against the trivial floors from
`scripts/run_baseline_stub_v06.py` (oracle/dummy/echo/random).

## 5. Caveats

- **Cost.** Real runs hit paid APIs. Start with `--limit` and `--sleep-seconds`; the full `dev` split is
  1,618 prompts, `test_public` is 105. Costs are not auto-computed (`cost_usd` is `null` in metadata) —
  record provider invoices separately.
- **Locator-only context.** These prompts contain no document text, so this is a closed-book lower bound,
  not the full-context (class A) number. Do not compare across context regimes without labeling them.
- **Hidden split.** `test_hidden` is INTERNAL: the runner refuses it unless `--allow-internal-hidden`,
  and hidden predictions/answers must never be published.
- **Partial-run scoring.** `eval_harness_v06.py` scores against the requested gold split. Missing and
  empty predictions are always counted wrong, so a `--limit` smoke run can be scored safely, but its
  result is still only a plumbing check, not a benchmark number.
- **Provider/model version drift.** Hosted models change behind a fixed name; pin and record exact model
  ids and run dates in `.meta.json`, and re-run when comparing across time.
- **Determinism.** `--temperature 0.0` reduces but does not guarantee identical outputs across providers
  or versions.
