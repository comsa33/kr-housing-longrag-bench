#!/usr/bin/env python3
"""Summarize the independent-judge cross-check (paper Appendix: judge panel).

Reads the archived panel verdict files written by scripts/judge_panel_ollama.py and reports,
for each judge:
  * agreement % and Cohen's kappa vs the n=80 human labels (panel_items_human80.jsonl carries
    the human Y/N), directly comparable to the primary judge's 96.2% / kappa 0.924, and
  * plain LLM-judge accuracy (%) on the 81-item cross-source-aggregation slice for each
    evaluated model (gpt-5.5 / glm-5.2 / minimax-m3 / gpt-4.1-mini) --- the capability ladder.

Usage:
    python3 scripts/kappa_panel.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "workspace_local" / "audit" / "baselines"

# display name -> (lab, filesystem label of the panel_<label>_*.judged.jsonl files).
# The primary judge is read from files too (panel_gpt-4.1-mini_*), so every row is
# data-driven and reproducible from the shipped verdicts --- no hardcoded numbers.
JUDGES = [
    ("gpt-4.1-mini", "OpenAI", "gpt-4.1-mini"),  # primary judge (also a baseline)
    ("gemma4:31b", "Google", "gemma4_31b"),
    ("deepseek-v3.2", "DeepSeek", "deepseek-v3.2"),
    ("kimi-k2.6", "Moonshot", "kimi-k2.6"),
    ("mistral-large-3", "Mistral", "mistral-large-3_675b"),
]
MODELS = ["gpt-5.5", "glm-5.2", "minimax-m3", "gpt-4.1-mini"]


def cohen_kappa(a: list[int], b: list[int]) -> tuple[float, float]:
    """Two binary raters -> (observed agreement, Cohen's kappa)."""
    n = len(a)
    if n == 0:
        return (0.0, 0.0)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    kappa = (po - pe) / (1 - pe) if pe != 1 else 1.0
    return (po, kappa)


def load_verdicts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    out = {}
    for l in path.open(encoding="utf-8"):
        d = json.loads(l)
        out[d["qa_id"]] = 1 if d.get("judge_correct") else 0
    return out


def main() -> int:
    human = {}
    for l in (B / "panel_items_human80.jsonl").open(encoding="utf-8"):
        d = json.loads(l)
        human[d["qa_id"]] = 1 if d.get("human") == "Y" else 0

    print(f"{'judge':22} {'lab':>9} {'kappa':>6} {'agree':>7}   " + "  ".join(f"{m:>12}" for m in MODELS))
    for disp, lab, label in JUDGES:
        hv = load_verdicts(B / f"panel_{label}_human80.judged.jsonl")
        ids = [q for q in human if q in hv]
        po, k = cohen_kappa([human[q] for q in ids], [hv[q] for q in ids])
        cells = []
        for m in MODELS:
            av = load_verdicts(B / f"panel_{label}_agg81_{m}.judged.jsonl")
            n = len(av)
            c = sum(av.values())
            cells.append(f"{round(c/n*100) if n else 0} ({c}/{n})")
        flag = "" if len(ids) == 80 else f"  [human n={len(ids)}/80]"
        print(f"{disp:22} {lab:>9} {k:6.3f} {po*100:6.1f}%   " + "  ".join(f"{v:>12}" for v in cells) + flag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
