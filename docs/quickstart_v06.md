# Quickstart (v0.6)

How to load the dataset, build prompts, run the eval harness, and score your own predictions.
Everything here uses only **public** files (no raw corpus, no answers for the hidden split).

## 1. Files

Canonical release artifacts (all under `data/`):

| File | Rows | Contents |
|---|---:|---|
| `qa_v0.6_realistic_candidates.jsonl` | 2,011 | **canonical full set** — realism + cluster + bundle metadata |
| `qa_v0.6_dev.jsonl` | 1,618 | dev split, answers included |
| `qa_v0.6_test_public.jsonl` | 105 | public test split, answers included |
| `qa_v0.6_test_hidden_questions.jsonl` | 288 | hidden split, **answers masked** (`answer="[HELD OUT]"`, no gold predicate/terms/numbers/row_ids) |
| `qa_v0.6_prompts.jsonl` | 2,011 | locator-only prompt inputs (generated; see §3) |
| `source_manifest.jsonl` | — | source registry (URLs/metadata) every `source_id` resolves to |

The hidden-split gold answers live only in an INTERNAL file (`workspace_local/audit/
qa_v0.6_test_hidden_answers.jsonl`), used by the harness; they are never published. Long-context bundle
**text** is also internal (`workspace_local/processed/bundles-v06/`), rebuilt locally — the public QA
carries only `bundle_id` + tier/position.

### QA record fields (public)

```
qa_id, task_type, split, question, answer, answer_type,
evaluation{metric, gold_terms?, gold_numbers?}, gold_predicate{source, ...},
source_ids[], page_ids[], row_ids?[], table_ids?[], cell_ids?[],
provider, region_sido, housing_type, announcement_ids[],
question_style, original_question, rewrite_rationale,
cluster_id, cluster_size, cluster_weight,
bundle_id?, context_tier?, evidence_position?
```

(For `test_hidden` the answer/gold fields are masked; the others remain.)

## 2. Setup

```bash
python3 --version          # 3.10+
pip install tiktoken pymupdf olefile     # only needed to REBUILD bundles/cells, not to score
```

Scoring and prompt-building (§3–§5) need **no** third-party packages — standard library only.

## 3. Build prompt inputs

```bash
python3 scripts/make_prompt_v06.py
# -> data/qa_v0.6_prompts.jsonl  (locator-only, public-safe)
```

Each record carries `instruction`, `question`, and a `context_spec` describing *where* the evidence is
(`bundle_id`/`context_tier`/`evidence_position`, `page_ids`/`source_ids`/`row_ids`/`table_ids`/`cell_ids`,
`predicate_source`, `retrieval_mode`) — **no document text**. To embed the actual bundle text for a
local full-context run (INTERNAL output under `workspace_local/`):

```bash
python3 scripts/make_prompt_v06.py --inline-context     # requires rebuilt bundles
```

## 4. Score predictions

A prediction file is JSONL, one object per QA:

```json
{"qa_id": "krhlrb_v05_0001", "prediction": "your model answer text"}
```

Run your model over `qa_v0.6_prompts.jsonl`, write predictions, then:

```bash
python3 scripts/eval_harness_v06.py --pred my_predictions.jsonl
```

The harness reports plain **and cluster-weighted** accuracy by split / task_type / question_style, scored
per `evaluation.metric` (`exact_numbers` / `boolean_and_reason` / contained-answer). For `test_hidden` it
loads gold from the internal answers file automatically. To score only some splits:

```bash
python3 scripts/eval_harness_v06.py --pred my_predictions.jsonl --splits dev,test_public
```

## 5. Self-test + trivial baselines

Confirm the scorer/gold wiring (gold-as-prediction → 100%):

```bash
python3 scripts/eval_harness_v06.py --self-test
```

Generate reference floors/ceiling (written to `workspace_local/audit/`, INTERNAL — `oracle`/`random` are
derived from gold):

```bash
python3 scripts/run_baseline_stub_v06.py
python3 scripts/eval_harness_v06.py --pred workspace_local/audit/baseline_oracle_v06.jsonl   # ~100%
python3 scripts/eval_harness_v06.py --pred workspace_local/audit/baseline_dummy_v06.jsonl    # ~5%
```

Reference numbers (all splits): oracle 100.0% / dummy 5.3% / echo 2.5% / random 1.4% (plain). See
`docs/baseline_protocol_v06.md` for the full-context vs RAG vs table/tool protocol.

## 6. Dummy prediction example (end-to-end)

```bash
# 1) make a trivial prediction file from the public dev questions (always answers the same string)
python3 - <<'PY'
import json
out = open("my_predictions.jsonl", "w", encoding="utf-8")
for l in open("data/qa_v0.6_dev.jsonl", encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        out.write(json.dumps({"qa_id": r["qa_id"], "prediction": "제공된 자료만으로는 확정할 수 없음"},
                             ensure_ascii=False) + "\n")
out.close()
PY

# 2) score it (dev only)
python3 scripts/eval_harness_v06.py --pred my_predictions.jsonl --splits dev
```

This scores only the answerability items (the fixed "unanswerable" string), demonstrating the
prediction → scoring loop end to end.

## 7. Verification gates

```bash
python3 scripts/validate_dataset.py
python3 scripts/verify_qa.py --qa data/qa_v0.6_realistic_candidates.jsonl
python3 scripts/check_public_release_readiness.py --qa data/qa_v0.6_realistic_candidates.jsonl --allow-dev
python3 scripts/check_question_realism_v06.py --qa data/qa_v0.6_realistic_candidates.jsonl
```

See `docs/release_checklist.md` for the full pre-tag checklist and `docs/dataset_statistics_v06.md` for
the count tables.
