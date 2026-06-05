# Agent Workflow Rules

This repository is a public dataset package. Treat every change as either release maintenance,
benchmark development, or internal corpus work. Do not blur those modes.

## Current State

- Public release: `v0.6.3`
- Dataset build: `v0.6`
- Status: public-ready seed benchmark, not leaderboard-ready, not human-validated.
- Canonical public QA: `data/qa_v0.6_realistic_candidates.jsonl`
- Public split files:
  - `data/qa_v0.6_dev.jsonl`
  - `data/qa_v0.6_test_public.jsonl`
  - `data/qa_v0.6_test_hidden_questions.jsonl`
- Internal-only materials live under `workspace_local/` and must stay untracked except placeholders.

## Branch Policy

- `main` is release-only. Do not do experimental work on `main`.
- `develop` is the integration branch for post-`v0.6.3` work.
- Use `feature/<topic>` for non-trivial changes, for example:
  - `feature/baseline-results`
  - `feature/sealed-hidden-protocol`
  - `feature/human-review`
  - `feature/v07-source-expansion`
- Use `hotfix/<topic>` only for urgent fixes to an already public release.
- Prefer a separate worktree when another agent may be active:

```bash
git worktree add ../kr-housing-longrag-bench-develop develop
```

## Start-of-Session Checklist

Every Codex or Claude Code session must begin with:

```bash
git status -sb
git branch --show-current
git log --oneline --decorate -5
```

Then read:

- `AGENTS.md`
- `docs/agent_workflow.md`
- `docs/v1_roadmap.md`
- `docs/release_checklist.md`

If working on evaluation or baselines, also read:

- `docs/quickstart_v06.md`
- `docs/baseline_protocol_v06.md`
- `docs/dataset_statistics_v06.md`

## Local Environment

The repo remains usable with plain `python3` and the standard library for public scoring and validation.
For development, prefer `uv`:

```bash
uv sync --extra dev
uv run pre-commit install
```

Then run checks with either `python3 ...` or `uv run python ...`. Do not introduce mandatory runtime
dependencies for the public scoring path unless the README and CI are updated accordingly.

## Safety Rules

- Never commit raw PDFs, HWP/HWPX files, extracted full text, bundle text, API keys, cookies, or hidden
  gold answers.
- Never move or delete legacy `qa_v0.2`-`qa_v0.5` artifacts just because they look old. Current validators
  and reproducibility checks still depend on some legacy files and modules.
- Do not claim "leaderboard-ready", "sealed hidden", "human-validated", "perfect", or "hallucination-free"
  unless the relevant roadmap gate is actually complete.
- Hidden split policy:
  - Public hidden questions must have masked answers.
  - Gold answers must remain internal.
  - A true leaderboard needs a sealed harness outside the public repo.
- Hugging Face and Zenodo metadata must match the GitHub release version before a release is called done.

## Verification Commands

Run the smallest relevant set during development, and the full set before a public release.

```bash
python3 scripts/validate_dataset.py
python3 scripts/verify_qa.py --qa data/qa_v0.6_realistic_candidates.jsonl
python3 scripts/check_public_release_readiness.py --qa data/qa_v0.6_realistic_candidates.jsonl
python3 scripts/check_question_realism_v06.py --qa data/qa_v0.6_realistic_candidates.jsonl
python3 scripts/eval_harness_v06.py --self-test
python3 -m py_compile scripts/*.py
```

For external usability, also test:

```bash
python3 scripts/make_prompt_v06.py
python3 scripts/run_baseline_stub_v06.py
```

and verify Hugging Face loading from a fresh cache when HF files change.

If pre-commit is installed, run:

```bash
uv run pre-commit run --all-files
```

## Handoff Format

When handing off to another agent, include:

- Branch and commit SHA.
- Files changed.
- Exact commands run and exit status.
- Whether changes touch public data, docs, scripts, or internal-only files.
- Known caveats and what must not be claimed.
- Next recommended task.
