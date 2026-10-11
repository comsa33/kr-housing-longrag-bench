# Model answers (v0.9.5)

**Notice — terms.** The model answers in this directory are **not** covered by the CC BY 4.0 license of the
KR-Housing annotations. They are outputs of third-party models and remain subject to each model provider's
terms of use (OpenAI, Anthropic, and the licenses of glm-5.2 and minimax-m3 served through Ollama). They are
released only so that readers can reproduce and re-judge the reported evaluation. Do not use them to train
models that compete with those providers' products.

## What is here
- The final answer text of every judged prediction behind the reported results: 24,074 answers
  (test_public 12,797, dev 11,277) in 85 JSONL files. Each line is
  `{qa_id, split, model, setting, prediction, judge_label, judge_label_secondary}`.
  `judge_label` is the released primary-judge (claude-sonnet-5-5) verdict and `judge_label_secondary` the
  released secondary-judge (gpt-4.1-mini) verdict for the same item; `null` where that judge did not score
  the run.
- The files mirror the verdict files one to one (`MANIFEST.csv` gives each file's model, setting, counts and
  verdict file):
  - `v0.9.2/` — main runs of the six original models (closed-book, BM25, dense, full-context sample, 512k
    aggregation layers); the OpenAI files hold test_public and dev answers together, as their verdict files do.
  - `v0.9.3/` — closed-book leak-fix re-runs (`cbfix_*`), gpt-5.5 empty-answer retries (`g55retry_*`),
    glm-5.2 reasoning-on runs (`thinkon_*`), open-region and oracle contexts, and all settings of
    claude-sonnet-5-5 and claude-haiku-5-5 (these include the 74 predictions labelled in the round-3 human
    review).
  - `v0.9.4/` — dense k=50 on the 81 aggregation items (seven rows, including the minimax-m3 run without
    reasoning that is not the reported result).
  - `variance/` — the second and third full-context runs of glm-5.2 and minimax-m3 (Section S8 of the paper);
    scored by the secondary judge only, so `judge_label` is null.
  - `human80/` — the 80 judge-validation predictions, keyed `{qa_id}__{model}__{regime}` as in
    `results/judge_verdicts/human80_labels.jsonl`.
- Each answer is the exact string the judge scored (the final layer after re-runs), except for the masking
  below. Empty answers are kept as empty strings or as `(빈 답)`, as the judge saw them.

## What is not here
- Reasoning traces (minimax-m3 and glm-5.2 return them; 4.6% of them copy 200 or more characters of bundle
  text), the model input prompts (which contain bundle text), bundle text, and provider logs.
- The unreported qwen3.5 runs.

## Masking
- **Source text:** a span is replaced by `[source text omitted, N chars]` when, after removing whitespace, a
  maximal run of overlapping 20-character windows that all occur in the item's bundle text covers 200 or more
  characters. One answer meets this criterion (glm-5.2 BM25, reasoning off; 573 characters replaced). After
  masking, the longest such run in any released answer is 162 characters.
- **Telephone numbers:** a phone-number-shaped string that occurs in no bundle text (so it was generated or
  recalled by the model and is unverified) is replaced by `[phone number omitted]`: 6 distinct numbers in 6
  answers. Numbers copied from the public notices are kept. No mobile numbers, e-mail addresses, resident
  registration numbers or personal names were found.
