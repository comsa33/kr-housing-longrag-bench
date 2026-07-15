# Quickstart (v0.6)

How to load the dataset, build prompts, run the eval harness, and score your own predictions.
Everything here uses only **public** files (no raw corpus). **This version has no hidden split** —
`test_public` is a public held-out set (the former `test_hidden` was merged into it; see `CHANGELOG.md`).

## 1. Files

Canonical release artifacts (all under `data/`):

| File | Rows | Contents |
|---|---:|---|
| `qa_v0.6_realistic_candidates.jsonl` | 1,997 | **canonical full set** — realism + cluster + bundle metadata |
| `qa_v0.6_dev.jsonl` | 1,608 | dev split, answers included |
| `qa_v0.6_test_public.jsonl` | 389 | public held-out split, answers included |
| `qa_v0.6_prompts.jsonl` | 1,997 | locator-only prompt inputs (generated; see §3) |
| `source_manifest.jsonl` | — | source registry (URLs/metadata) every `source_id` resolves to |

The harness scores `dev` and `test_public` immediately. This version has no hidden split, so there is no
masked-answer file. Long-context bundle **text** is internal (`workspace_local/processed/bundles-v06/`),
rebuilt locally — the public QA carries only `bundle_id` + tier/position.

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

## 2. Setup

```bash
python3 --version          # 3.10+
pip install tiktoken pymupdf olefile     # only needed to REBUILD bundles/cells, not to score
```

Scoring and prompt-building (§3–§5) need **no** third-party packages — standard library only.

## 3. Build prompt inputs

```bash
python3 scripts/make_prompt.py
# -> data/qa_v0.6_prompts.jsonl  (locator-only, public-safe)
```

Each record carries `instruction`, `question`, and a `context_spec` describing *where* the evidence is
(`bundle_id`/`context_tier`/`evidence_position`, `page_ids`/`source_ids`/`row_ids`/`table_ids`/`cell_ids`,
`predicate_source`, `retrieval_mode`) — **no document text**. To embed the actual bundle text for a
local full-context run (INTERNAL output under `workspace_local/`):

```bash
python3 scripts/make_prompt.py --inline-context     # requires rebuilt bundles
```

## 4. Score predictions

A prediction file is JSONL, one object per QA:

```json
{"qa_id": "krhlrb_v05_0001", "prediction": "your model answer text"}
```

Run your model over `qa_v0.6_prompts.jsonl`, write predictions, then:

```bash
python3 scripts/eval_harness.py --pred my_predictions.jsonl
```

The harness reports plain **and cluster-weighted** accuracy by split / task_type / question_style, scored
per `evaluation.metric` (`exact_numbers` / `boolean_and_reason` / contained-answer). To score only some splits:

```bash
python3 scripts/eval_harness.py --pred my_predictions.jsonl --splits dev,test_public
```

## 5. Self-test + trivial baselines

Confirm the scorer/gold wiring (gold-as-prediction → 100%). This covers `dev` + `test_public`
(1,997 items; this version has no hidden split):

```bash
python3 scripts/eval_harness.py --self-test
```

Generate reference floors/ceiling (written to `workspace_local/audit/`, INTERNAL — `oracle`/`random` are
derived from gold):

```bash
python3 scripts/eval_harness.py --pred workspace_local/audit/baseline_oracle_v06.jsonl   # ~100%
python3 scripts/eval_harness.py --pred workspace_local/audit/baseline_dummy_v06.jsonl    # ~5%
```

Reference numbers (all splits): oracle 100.0% / dummy 5.3% / echo 2.5% / random 1.4% (plain). See
`docs/baseline_protocol.md` for the full-context vs RAG vs table/tool protocol.

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
python3 scripts/eval_harness.py --pred my_predictions.jsonl --splits dev
```

This scores only the answerability items (the fixed "unanswerable" string), demonstrating the
prediction → scoring loop end to end.

## 7. Verification gates

```bash
python3 scripts/validate_dataset.py
python3 scripts/verify_qa.py --qa data/qa_v0.6_realistic_candidates.jsonl
python3 scripts/check_public_release_readiness.py --qa data/qa_v0.6_realistic_candidates.jsonl --allow-dev
python3 scripts/check_question_realism.py --qa data/qa_v0.6_realistic_candidates.jsonl
```

See `docs/dataset_statistics.md` for
the count tables.
