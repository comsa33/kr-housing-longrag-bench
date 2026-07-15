# Baseline Evaluation Protocol

How the paper's baselines are scored on KR-Housing-LongRAG-Bench, and how to read the trivial sanity
baselines. This version has **no hidden split**; `test_public` (389) is a public held-out set (the former
`test_hidden` was merged into it — see `CHANGELOG.md`).

## 0. Metric

The **headline metric is a human-validated LLM-judge** (`scripts/llm_judge.py`, judge `gpt-4.1-mini`;
validated on a human sample: n=80, agreement 96.2%, Cohen's κ=0.924), because exact/substring matching
systematically undercounts correct paraphrases and formatting variants. A **deterministic soft-match
reference** (`scripts/score_answers.py`: exact-match | contains | token-recall) ships for API-free
re-scoring and tracks the judge closely. We report **plain accuracy as the primary headline and
cluster-weighted accuracy as a robustness/sensitivity cut** (`cluster_weight = 1/cluster_size` keeps
near-duplicate families from inflating the score). `scripts/score_judge.py` aggregates the LLM-judge
verdicts by split / task_type / context_tier.

```bash
python3 scripts/llm_judge.py submit --pred <one-regime preds>.jsonl   # headline (LLM-judge)
python3 scripts/score_judge.py                                        # aggregate verdicts by split/tier
python3 scripts/eval_harness.py --pred <predictions>.jsonl           # deterministic reference + floors
```

## 1. Evidence-access regimes

The **same** questions are scored under three regimes (paper §4), so differences are attributable to
evidence access, not the metric:

| Regime | What the model sees |
|---|---|
| **Closed-book** | question + locator metadata only, no document body — a parametric-recall floor |
| **RAG** | top-5 retrieved passages (sparse BM25 and a dense `bge-m3` retriever) from the item's own bundle |
| **Full-context** | the entire context bundle at the item's tier (up to the 512k tier) |

Recommended reporting cuts (all produced by the scorers): by **context_tier** (32k→512k), by
**evidence_position** (early/middle/late/multi — lost-in-the-middle), by **task_type**, and
**cluster-weighted ALL**.

## 2. Trivial baselines (floors / ceiling)

Deterministic-reference sanity checks (`scripts/eval_harness.py`; `oracle`/`random` are derived from gold
answers and are INTERNAL):

| Baseline | Prediction | Role |
|---|---|---|
| `oracle` | gold answer | scorer/gold sanity ceiling (100%) |
| `dummy` | fixed "unanswerable" string | matches only `answerability_detection` items |
| `echo` | the question text | degenerate floor |
| `random` | another item's gold answer (fixed offset) | chance-level floor |

```bash
python3 scripts/eval_harness.py --self-test   # oracle=100% confirms the scorer + gold wiring
```

## 3. Protocol steps

1. Build prompts per regime (paper §4; closed-book/RAG locators are public, full-context inline-context is
   INTERNAL under `workspace_local/`).
2. Run each model × regime → one `{qa_id, prediction}` JSONL per run.
3. Judge with `llm_judge.py` and aggregate with `score_judge.py` (headline); also run the deterministic
   `score_answers.py` / `eval_harness.py` reference.
4. Report plain + cluster-weighted by split / task_type / context_tier; always include the trivial
   baselines so absolute numbers are interpretable.

## 4. Caveats

- No sealed hidden split; `test_public` is a public held-out set, not a leaderboard test.
- Bundles are internal (`workspace_local/`), rebuilt locally — not redistributed.
- RAG results depend on the retriever supplied; the gold locators give an oracle-retrieval ceiling, and a
  real retriever (BM25 / dense) should be reported separately.
- Plain accuracy is the primary headline; cluster-weighted accuracy is the robustness cut.
