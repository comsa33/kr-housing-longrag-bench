# Baseline Evaluation Protocol (v0.6, draft)

This protocol describes how to evaluate three system classes on KR-Housing-LongRAG-Bench and how to read
the trivial baselines. It is a **draft for the paper**, not a leaderboard spec — the `test_hidden` split
is not yet served behind a sealed harness (see `docs/v0.6_quality_report.md` §4).

## 0. Inputs and scoring

- Questions / context locators per QA: `scripts/make_prompt_v06.py` → `data/qa_v0.6_prompts.jsonl`
  (locator-only, public-safe: `context_spec` says *where* the evidence is — bundle/tier/position,
  `page_ids`/`source_ids`/`row_ids`/`table_ids`/`cell_ids`, predicate source — but carries no document
  text).
- A prediction file is JSONL: `{"qa_id": ..., "prediction": "..."}`.
- Scoring is by `scripts/eval_harness_v06.py`, per `evaluation.metric` (`exact_numbers` /
  `boolean_and_reason` / contained-answer). It reports plain **and cluster-weighted** accuracy by
  split / task_type / question_style. Cluster-weighting (`cluster_weight = 1/cluster_size`) keeps
  parametric near-duplicate families from inflating the score.

```bash
python3 scripts/eval_harness_v06.py --pred <predictions>.jsonl
```

## 1. System classes to compare

The benchmark is designed to separate three pipelines on the **same** QA:

| Class | What it sees | How to build the context |
|---|---|---|
| **A. Full-context LLM** | the whole long-context bundle in one prompt | `make_prompt_v06.py --inline-context` (INTERNAL output under `workspace_local/`; embeds the bundle text named by `context_spec.bundle_id` at tier `context_tier`, evidence at `evidence_position`) |
| **B. RAG / retrieval** | top-k retrieved passages from the same announcement/source corpus | retrieve over the rebuilt corpus (`scripts/rebuild_v04_from_public_manifest.py`); the gold `page_ids`/`source_ids` give an oracle-retrieval ceiling |
| **C. Table / tool pipeline** | structured rows/cells + a tool/operator | for `table_numeric_reasoning` / `format_robustness` / `cross_source_aggregation`, query the source named by `context_spec.predicate_source` over `row_ids`/`cell_ids`; the gold operator stays hidden |

All three emit the same `{qa_id, prediction}` JSONL and are scored by the one harness, so differences are
attributable to the pipeline, not the metric.

Recommended reporting cuts (all produced by the harness): by **context_tier** (32k→512k — does
full-context degrade with length?), by **evidence_position** (early/middle/late/multi — lost-in-the-middle),
by **task_type** (retrieval vs numeric vs legal vs answerability), and **cluster-weighted ALL**.

## 2. Trivial baselines (floors / ceiling)

`scripts/run_baseline_stub_v06.py` writes four reference prediction files to `workspace_local/audit/`
(INTERNAL — `oracle`/`random` are derived from gold answers, including the masked `test_hidden` answers):

| Baseline | Prediction | Plain acc (all splits) | Cluster-weighted | Role |
|---|---|---|---|---|
| `oracle` | gold answer | 100.0% | 100.0% | harness/gold sanity ceiling |
| `dummy` | fixed "unanswerable" string | 5.3% | 1.7% | matches only `answerability_detection` (106 items) |
| `echo` | the question text | 2.5% | 1.0% | degenerate floor |
| `random` | another item's gold answer (fixed offset) | 1.4% | 1.1% | chance-level floor |

```bash
python3 scripts/run_baseline_stub_v06.py            # writes baseline_{oracle,dummy,random,echo}_v06.jsonl
python3 scripts/eval_harness_v06.py --pred workspace_local/audit/baseline_oracle_v06.jsonl
```

`oracle` = 100% confirms the scorer + gold wiring (same as `eval_harness_v06.py --self-test`). The three
floors bracket where a real system must land to show signal; note the plain-vs-cluster-weighted gap on
`dummy` (5.3% → 1.7%) — the answerability items are parametrically related, so cluster-weighting is the
honest headline number.

## 3. Protocol steps

1. Freeze inputs: `make_prompt_v06.py` for locators (A/B/C share these); add `--inline-context` only for
   class A, locally.
2. Run each system → one `{qa_id, prediction}` JSONL per system.
3. Score every file with `eval_harness_v06.py`; report plain + cluster-weighted by split, task_type,
   context_tier, evidence_position.
4. Always include the four trivial baselines so absolute numbers are interpretable.
5. Report `test_hidden` only via the internal gold + this harness; never publish hidden answers.

## 4. Caveats

- Not a sealed leaderboard yet; `test_hidden` answers are internal-but-in-repo.
- Bundles are internal (`workspace_local/`), rebuilt locally — not redistributed.
- Class B/C results depend on the retriever/tool you supply; the gold locators give an oracle-retrieval
  ceiling but a real retriever should be reported separately.
- Cluster-weighted accuracy is the primary metric for paper claims; plain accuracy is secondary.
