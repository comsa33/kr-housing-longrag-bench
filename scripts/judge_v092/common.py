"""Shared paths and helpers for the v0.9.2 re-judge (no API calls here).

Paths are relative to the dataset repo root. Model predictions live in the internal working
area `workspace_local/audit/baselines/` (gitignored, not released); pass `--baselines DIR` to the
build scripts to point elsewhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINES = ROOT / "workspace_local" / "audit" / "baselines"
RELEASED_V091 = ROOT / "results" / "judge_verdicts"            # v0.9.1 gpt-4.1-mini verdicts
GOLD_FIXES = ROOT / "data" / "v0.9.2" / "gold_fixes.json"
LEGAL = "cross_document_legal_reasoning"

sys.path.insert(0, str(ROOT / "scripts"))
from llm_judge import judge_prompt  # noqa: E402,F401  (pure function: instruction text + fields)

# Claude judge request parameters (Message Batches API). No temperature: the API rejects it
# for this model. The verdict is constrained by a JSON schema.
CLAUDE_MODEL = "claude-sonnet-5-5"
CLAUDE_OUTPUT = {"format": {"type": "json_schema", "schema": {
    "type": "object", "properties": {"verdict": {"type": "string", "enum": ["YES", "NO"]}},
    "required": ["verdict"], "additionalProperties": False}}}
CLAUDE_PARAMS = {"model": CLAUDE_MODEL, "max_tokens": 32, "thinking": {"type": "between_tools"},
                 "output_config": CLAUDE_OUTPUT}


def load(p: Path) -> list[dict]:
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def write_jsonl(p: Path, rows: list[dict]) -> None:
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def gold_fixes() -> dict:
    return json.load(open(GOLD_FIXES, encoding="utf-8"))


def multi_answer(answers: list[str]) -> str:
    """Gold text for an accept-any item, as shown to both judges."""
    return "다음 중 어느 하나와 일치하면 정답: " + " / ".join(f"({i}) {a}" for i, a in enumerate(answers, 1))


def gold_v092(item: dict, fix: dict, accept_any_format: str = "multi") -> str:
    """v0.9.2 gold string for the judge prompt.

    accept_any_format="or" reproduces the interim join ("A 또는 B") used in the first full batch;
    those verdicts were superseded by the multi-answer re-judge (see README).
    """
    q = item["qa_id"]
    if q in fix["replace"]:
        return fix["replace"][q]
    if q in fix["accept_any"]:
        a = fix["accept_any"][q]
        return multi_answer(a) if accept_any_format == "multi" else " 또는 ".join(a)
    return str(item.get("answer", ""))
