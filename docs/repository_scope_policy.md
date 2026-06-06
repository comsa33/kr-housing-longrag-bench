# Repository Scope Policy

Status date: 2026-06-06

This repository is the public benchmark package for KR-Housing-LongRAG-Bench. It may contain data files,
dataset documentation, validation/scoring code, and minimal reproducible baseline scaffolds. It must not
become a dumping ground for paid experiment artifacts, private hidden-gold operation, raw source documents,
or provider-specific logs.

## 1. Current Decision

Keep one public repository through v0.7.

This is acceptable because the current baseline code is lightweight and supports benchmark usability:

- `scripts/eval_harness_v06.py` scores predictions;
- `scripts/make_prompt_v06.py` builds public locator-only prompts;
- `scripts/run_llm_baseline_v07.py` provides a minimal provider-agnostic runner;
- RAG/full-context scripts create internal prompt files only under `workspace_local/`;
- docs report smoke diagnostics without publishing raw bundle text, hidden gold, or prediction archives.

The single-repo approach is standard for a seed benchmark as long as public data consumers can clearly find:

- canonical data files;
- schema and dataset card;
- validation and scoring scripts;
- minimal baseline commands;
- release checklist and limitations.

## 2. What Belongs Here

Keep these in `kr-housing-longrag-bench`:

- public QA JSONL, split files, prompts, source manifest, and schema;
- dataset card, README, license, citation, release checklist, and roadmap;
- validators, verifiers, prompt builder, scorer, and public-safe readiness gates;
- minimal baseline runner code that writes outputs under `workspace_local/`;
- small smoke-test documentation when it clarifies benchmark usage;
- scripts needed to reconstruct or audit the public package from URL/locator metadata.

## 3. What Must Stay Internal

Keep these out of tracked public files:

- raw PDF/HWP/HWPX/CSV/API responses;
- extracted full document text;
- long-context bundle text;
- hidden answers and hidden scoring gold;
- API keys, service keys, cookies, screenshots of private portals, and credentials;
- provider logs, paid-run transcripts, model outputs, and full prompts containing raw context;
- local notebooks or caches that embed source text or predictions.

All such files belong under `workspace_local/` or outside the repo.

## 4. When to Split Repositories

Create a separate repo only when experiment machinery becomes large enough to blur the public package.

Recommended split:

- `kr-housing-longrag-bench`: public benchmark package.
- `kr-housing-longrag-experiments` or `kr-housing-longrag-baselines`: paid model runs, large result tables,
  retriever tuning, notebooks, prompt/prediction archives, and private hidden-track operation.

Split when any of these become true:

- provider-specific orchestration becomes more than a minimal runner;
- paid-run configs, caches, or predictions need their own lifecycle;
- private leaderboard scoring or sealed hidden infrastructure is introduced;
- public README/DATASET_CARD becomes hard to navigate because experiment material dominates;
- a release package requires excluding many tracked files rather than relying on clear public/internal
  boundaries.

Do not split just because the repo contains scoring scripts or baseline scaffolds. Those are normal parts of
a benchmark package.

## 5. Hugging Face, GitHub, and Zenodo Roles

Use the platforms differently:

- Hugging Face dataset repo: public data files, dataset card, schema-oriented metadata, and loading smoke.
- GitHub benchmark repo: source of truth for public data, validators, scoring scripts, docs, and releases.
- Zenodo: archived release snapshot and DOI.
- Optional experiment repo: volatile paid-run code, private predictions, notebooks, and sealed hidden
  operation.

Before any public release, these surfaces must agree on version, citation, license, and caveats.

## 6. Release Rule

A public release may include baseline docs, but only if they are clearly labelled:

- `locator-only`, `full-context smoke`, `RAG smoke`, or `retrieval-only diagnostics`;
- not leaderboard-ready;
- not human-validated unless the stated review coverage is complete;
- no hidden-gold disclosure;
- no general dense-vs-BM25 or model-ranking claim from smoke slices.

If these labels cannot be kept clear, move the experiment material to a separate experiment repo before
tagging.
