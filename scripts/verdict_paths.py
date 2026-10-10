#!/usr/bin/env python3
"""Locate LLM-judge verdict files for the scoring scripts.

Two layouts hold the same verdicts:

* `results/judge_verdicts/<tag>.jsonl` — the released copy ({qa_id, judge_correct} only),
  present in every clone.
* `workspace_local/audit/baselines/<tag>.judged.jsonl` — the internal working copy written by
  `scripts/llm_judge.py` / `scripts/judge_panel_ollama.py` (gitignored).

Default: use the internal copy when it exists (unchanged behaviour on the build machine),
otherwise the released copy. `--verdicts-dir DIR` forces one directory; the file name is then
`<tag>.jsonl` or `<tag>.judged.jsonl`, whichever exists.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERNAL = ROOT / "workspace_local" / "audit" / "baselines"
RELEASED = ROOT / "results" / "judge_verdicts"


def verdict_file(tag: str, verdicts_dir: str | Path | None = None) -> Path:
    """Path of the verdict file for `tag` (may not exist; callers check)."""
    dirs = [Path(verdicts_dir)] if verdicts_dir else [INTERNAL, RELEASED]
    for d in dirs:
        for name in (f"{tag}.judged.jsonl", f"{tag}.jsonl"):
            p = d / name
            if p.exists():
                return p
    return dirs[0] / f"{tag}.jsonl"


def human80_file(verdicts_dir: str | Path | None = None) -> Path:
    """Human Y/N labels of the n=80 judge-validation sample ({qa_id, human, ...})."""
    if verdicts_dir:
        return Path(verdicts_dir) / "human80_labels.jsonl"
    internal = INTERNAL / "panel_items_human80.jsonl"
    return internal if internal.exists() else RELEASED / "human80_labels.jsonl"
