# Agent Workflow

This document is the operating contract for Codex, Claude Code, and any future worker sessions on
KR-Housing-LongRAG-Bench. It exists so new sessions can continue without relying on chat history.

## 1. Working Modes

Use one of these modes at the start of every task.

| Mode | Branch | Typical owner | Allowed output |
|---|---|---|---|
| Release maintenance | `main` or `hotfix/*` | Codex | small fixes, release metadata, CI/HF/GitHub/Zenodo checks |
| Dataset development | `develop` or `feature/*` | Claude Code or Codex | scripts, docs, public QA/schema changes |
| Internal corpus work | `feature/*` | Claude Code | `workspace_local/` raw/processed/audit outputs plus public-safe derived metadata |
| Review / verification | any non-dirty branch | Codex or reviewer agent | findings, validation results, small fixes |

If a task is not an urgent public-release fix, do it on `develop` or a feature branch.

## 2. Branch and Worktree Rules

Recommended branch graph:

```text
main                 public releases only
  v0.6.3             latest public tag
develop              post-v0.6.3 integration
feature/<topic>      isolated substantial work
hotfix/<topic>       urgent release patch
```

When multiple agents may work at once, use separate worktrees instead of switching the same directory:

```bash
git fetch origin
git checkout develop
git pull origin develop
git worktree add ../kr-housing-longrag-bench-baselines -b feature/baseline-results develop
```

Do not force-push unless the maintainer explicitly approves it. Do not rewrite `main` after a public
release unless preserving tags/branches first.

## 3. Session Start Procedure

Run:

```bash
git status -sb
git branch --show-current
git log --oneline --decorate -5
```

Then classify the task:

- Is it public release maintenance?
- Is it new benchmark development?
- Does it touch internal corpus files?
- Does it require network upload or remote validation?

Read the relevant docs before editing:

- General: `AGENTS.md`, `docs/v1_roadmap.md`, `docs/release_checklist.md`
- Baselines: `docs/baseline_protocol_v06.md`, `docs/quickstart_v06.md`
- Source expansion: `docs/source_selection_and_license_audit.md`, `docs/public_reconstruction.md`
- Release packaging: `README.md`, `DATASET_CARD.md`, `CITATION.cff`, HF package under
  `workspace_local/publish/huggingface-v0.6/`

Optional development environment:

```bash
uv sync --extra dev
uv run pre-commit install
```

The public validation/scoring path must continue to work with plain `python3` and the standard library.
Use `uv` for developer reproducibility, Hugging Face smoke tests, and pre-commit tooling.

## 4. Division of Labor

Codex is best used for:

- release packaging and verification;
- GitHub / Hugging Face / Zenodo checks;
- CI and public usability smoke tests;
- docs cleanup;
- smaller deterministic scripts;
- final review before publishing.

Claude Code is best used for:

- large extraction or QA-generation batches;
- multi-file pipeline changes;
- provider/source expansion;
- bulk data normalization;
- authoring larger candidate sets from internal corpus files.

Either agent may do small fixes, but every substantial worker result needs a separate verification pass.

## 5. Public vs Internal Files

Public-safe files may include:

- QA labels and short answers;
- evidence locators;
- source URLs;
- structured predicates;
- provider/region/type metadata;
- validation and scoring scripts;
- documentation and citation metadata.

Internal-only files must remain under `workspace_local/`:

- raw PDF/HWP/HWPX documents;
- extracted full text;
- bundle text;
- raw API rows;
- hidden gold answers;
- service keys and credentials;
- screenshots or license-capture artifacts.

Before committing, run:

```bash
git status --short
git diff --check
python3 scripts/validate_dataset.py
```

If public data files changed, also run the full verification suite in `AGENTS.md`.

If the `uv` environment is available, run local hooks before committing:

```bash
uv run pre-commit run --all-files
```

## 6. Release Procedure

For a public release:

1. Confirm clean branch state and intended release version.
2. Run all release gates in `docs/release_checklist.md`.
3. Confirm no raw/internal files are tracked.
4. Update `README.md`, `DATASET_CARD.md`, `CITATION.cff`, and Hugging Face package metadata.
5. Commit and push.
6. Confirm GitHub CI success.
7. Create GitHub release.
8. Archive with Zenodo and record the DOI.
9. Update citation docs with the final DOI.
10. Upload the Hugging Face package.
11. Run a fresh external `load_dataset()` smoke test.

Do not mark a release complete until GitHub, Hugging Face, Zenodo, and CI all agree on the version.

## 7. External Smoke Test

Minimum public consumer checks:

```bash
python3 scripts/validate_dataset.py
python3 scripts/check_public_release_readiness.py --qa data/qa_v0.6_realistic_candidates.jsonl
python3 scripts/eval_harness_v06.py --self-test
python3 scripts/make_prompt_v06.py
```

For Hugging Face:

```python
from datasets import load_dataset

repo = "comsa33/kr-housing-longrag-bench"
qa = load_dataset(repo, "qa")
prompts = load_dataset(repo, "prompts")
meta = load_dataset(repo, "metadata")

assert len(qa["dev"]) == 1618
assert len(qa["test_public"]) == 105
assert len(qa["test_hidden"]) == 288
assert len(prompts["prompts"]) == 2011
assert len(meta["source_manifest"]) == 20
assert qa["test_hidden"][0]["answer"] == "[HELD OUT]"
```

## 8. Handoff Prompt Template

Use this when handing work to Claude Code or another worker:

```text
You are working on KR-Housing-LongRAG-Bench.

Start by reading AGENTS.md, docs/agent_workflow.md, docs/v1_roadmap.md, and docs/release_checklist.md.
Run git status -sb, git branch --show-current, and git log --oneline --decorate -5 before editing.

Current task:
<specific objective>

Branch policy:
- Do not work on main unless this is an approved hotfix.
- Use develop or create feature/<topic>.

Non-negotiables:
- Do not commit workspace_local raw/processed/audit/secrets contents.
- Do not publish hidden gold answers.
- Do not claim leaderboard-ready, sealed hidden, human-validated, perfect, or hallucination-free.
- Preserve legacy v0.2-v0.5 artifacts unless you can prove the validators no longer need them.

Required verification before reporting:
<commands>

Final report must include:
- files changed;
- commands run and exit codes;
- public/internal file impact;
- remaining caveats;
- next recommended step.
```
