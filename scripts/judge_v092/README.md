# v0.9.2 judge: Claude primary, gpt-4.1-mini secondary

Code that produced `results/judge_verdicts_v0.9.2/`. The build and write steps make no API calls.
`run_batch.py` calls the Anthropic API and needs `ANTHROPIC_API_KEY` in the environment; no key is
stored in this repo.

Model predictions are internal (`workspace_local/audit/baselines/`, not released), so the build
steps run only on the build machine. The released verdict files are the reproducible artifact.

## Judge settings

| | primary | secondary |
|---|---|---|
| model | `claude-sonnet-5-5` | `gpt-4.1-mini` |
| API | Message Batches API | OpenAI Batch API (`/v1/chat/completions`) |
| sampling | no temperature (the API rejects it for this model) | temperature 0 |
| thinking | `{"type": "between_tools"}` | — |
| output | JSON schema `{"verdict": "YES" \| "NO"}`, `max_tokens` 32 | free text, `max_tokens` 4, correct iff "YES" in reply |
| prompt | `scripts/llm_judge.py` `judge_prompt()` | same text |

Gold shown to the judges is the v0.9.2 gold (`data/v0.9.2/gold_fixes.json`). Accept-any items use
`다음 중 어느 하나와 일치하면 정답: (1) … / (2) …`. The replaced item (0568) uses the new answer.

The secondary judge keeps its v0.9.1 verdicts (`results/judge_verdicts/`) except on the 24
gold-fixed items, which were re-judged with the same prompts as Claude.

## Files

| script | does |
|---|---|
| `common.py` | paths, Claude request parameters, v0.9.2 gold formatting |
| `build_test.py` | maps each test_public run to the prediction file its v0.9.1 verdict came from; writes `prompts.jsonl`/`index.jsonl` (r ids, includes the human-80 sample) and `prompts_multi.jsonl`/`index_multi.jsonl` (accept-any items, g ids) |
| `build_dev.py` | the same for dev; checks each layer's verdicts against the released v0.9.1 verdicts and the prediction files against independent copies; writes `dev_mapping.json` |
| `run_batch.py` | `submit` / `status` / `fetch` a Claude batch; raw results are saved before parsing |
| `parse.py` | raw results to verdicts; counts failed or unparsed requests; prints human-80 agreement |
| `build_gpt_rejudge.py` | OpenAI batch input for the gpt-4.1-mini re-judge of gold-fixed items |
| `write_verdicts.py` | writes `results/judge_verdicts_v0.9.2/` from the parsed verdicts |

The first full test batch showed accept-any gold as `A 또는 B` (`build_test.py` default
`--accept-any-format or`, kept so the submitted batch can be rebuilt). Those 511 verdicts were
replaced by the multi-answer batch; only the multi-answer verdicts are released.

## Procedure and batches

1. Build test inputs (8,171 requests: 8,091 run×item pairs over 36 runs plus the 80 human-labelled items).
2. Smoke: 124 requests (all 80 human-80 items plus 44 run items), `msgbatch_012TAWa8ggzoDQRuQCwV1fhx`.
   Checked: every request succeeded, every reply parsed, human-80 agreement.
3. Full test: the remaining 8,047 requests, `msgbatch_01WbUBYRHy7h15dtwfLTvj3e`.
4. Multi-answer re-judge of the accept-any items: 511 requests, `msgbatch_01AvYBM8obCACUBiaLscXAG7`.
5. Self-consistency: 100 requests from step 2–3 submitted again, `msgbatch_01N95vTPFTp8nRqVk7DRkAW3`.
6. gpt-4.1-mini re-judge: 532 gold-fixed pairs `batch_6acaf965832881908424cc5f341d46b7`;
   511 accept-any pairs with multi-answer gold `batch_6acafabcaadc81908cdcf3b139d46584`.
7. Dev: smoke 52 `msgbatch_01DHLQohcT8TSCXhx8uCEACD`, full 10,792 `msgbatch_016xnasL6GjbYk1iNuyqAQqC`.
   All requests succeeded, 0 unparsed. Every in-scope dev qa_id resolves to exactly one prediction.
8. `write_verdicts.py`.

## Validation results

- Human-80 labels: Claude 98.8% agreement, κ 0.975 (n=80); gpt-4.1-mini 96.2%, κ 0.924.
  Per-item Claude verdicts: `results/judge_verdicts_v0.9.2/human80_claude-sonnet-5-5.jsonl`.
- Self-consistency: 100/100 identical verdicts on the re-run.
- Agreement with gpt-4.1-mini: 99.5% over 8,091 in-scope test verdicts (≥ 96.8% in every one
  of the 36 runs); 99.5% over 10,844 dev verdicts.

## Rebuild check

Run on the build machine (`WORK`, `DEV` are scratch directories holding the batch results):

    python3 scripts/judge_v092/build_test.py --out WORK
    python3 scripts/judge_v092/build_dev.py  --out DEV
    python3 scripts/judge_v092/build_gpt_rejudge.py WORK/prompts.jsonl WORK/index.jsonl WORK/gpt_input_goldfix.jsonl --gold-fixed
    python3 scripts/judge_v092/build_gpt_rejudge.py WORK/prompts_multi.jsonl WORK/index_multi.jsonl WORK/gpt_input_multi.jsonl
    python3 scripts/judge_v092/write_verdicts.py --test-index WORK/index.jsonl \
        --claude-test WORK/verdicts_smoke.json WORK/verdicts_full.json --claude-multi WORK/verdicts_multi.json \
        --claude-dev DEV/verdicts_devsmoke.json DEV/verdicts_devfull.json \
        --gpt-goldfix WORK/gpt_raw_goldfix.jsonl --gpt-multi WORK/gpt_raw_multi.jsonl --out OUT
    diff -r OUT results/judge_verdicts_v0.9.2

On 2026-10-11 the rebuilt prompt, index and OpenAI input files were byte-identical to the
submitted ones, and `diff -r` reported no difference.

`build_dev.py` reports three layers whose prediction file is newer than its judge submission.
For each, the cross-check copies written before the judge batch hold identical predictions.
