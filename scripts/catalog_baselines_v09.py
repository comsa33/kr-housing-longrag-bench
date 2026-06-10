#!/usr/bin/env python3
"""Catalog the INTERNAL v0.9 baseline artifacts into a human-readable INDEX.md.

Scans workspace_local/audit/baselines/, groups files by role (sample / prompts /
predictions / call-logs / run-meta / drivers / other), and writes an INDEX.md with
a naming legend and a predictions-status table (regime x model x split -> counts,
empties). Safe to run anytime (read-only scan; only writes INDEX.md). Re-run to refresh.

Usage:  python3 scripts/catalog_baselines_v09.py
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "workspace_local" / "audit" / "baselines"
PRED_RE = re.compile(r"^(cb|rag|fc)_(.+)_(test_public|dev|test_hidden)\.jsonl$")
REGIME = {"cb": "closed-book", "rag": "RAG(BM25)", "fc": "full-context"}
# Only these models are v0.9 baseline predictions; anything else matching the pattern
# (e.g. v0.7 smoke files rag_bm25_openai_gpt-4o-mini_*) is legacy and listed under "other".
V09_MODELS = {"gpt-4.1-mini", "minimax-m3-cloud"}

LEGEND = """\
# v0.9 baseline artifacts — INDEX

All files here are INTERNAL (gitignored). Public results live in `docs/baseline_results_v09.md`.

## Naming legend
- `baseline_sample_v09.jsonl` — the locked 304-item evaluation sample (seed 20260610).
  `…fc.jsonl` = 116-item full-context-eligible subset · `…manifest.json` = counts + cost projection.
- `<regime>_v09_prompts.jsonl` — INPUT prompts per regime: `closedbook` / `fullcontext` / `rag_bm25`.
- `<regime>_<model>_<split>.jsonl` — OUTPUT predictions `{qa_id, prediction}`.
  regime ∈ {cb=closed-book, rag=RAG(BM25), fc=full-context} · model ∈ {gpt-4.1-mini, minimax-m3-cloud}
  · split ∈ {test_public, dev}.
- `….calls.jsonl` — rich per-item call log `{qa_id, prediction, latency_s, prompt_chars,
  prompt_tokens, completion_tokens, [reasoning_tokens], thinking}` (joinable by qa_id).
- `….meta.json` — run metadata · `….log` — per-item error log.
- `run_v09_*.sh` / `score_v09.sh` — run + scoring drivers.

To score: `bash workspace_local/audit/baselines/score_v09.sh`.
To refresh this index: `python3 scripts/catalog_baselines_v09.py`.
"""


def count_lines(p: Path) -> int:
    return sum(1 for _ in p.open(encoding="utf-8")) if p.exists() else 0


def empties(p: Path) -> int:
    n = 0
    for line in p.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            if not str(json.loads(line).get("prediction", "")).strip():
                n += 1
        except json.JSONDecodeError:
            pass
    return n


def main() -> int:
    if not B.is_dir():
        raise SystemExit(f"no baselines dir: {B}")
    files = sorted(p for p in B.iterdir() if p.is_file())

    groups: dict[str, list[Path]] = defaultdict(list)
    preds: list[Path] = []
    for p in files:
        n = p.name
        if n == "INDEX.md":
            continue
        if n.startswith("baseline_sample_v09"):
            groups["sample"].append(p)
        elif n.endswith("_v09_prompts.jsonl"):
            groups["prompts"].append(p)
        elif n.endswith(".calls.jsonl"):
            groups["calls"].append(p)
        elif PRED_RE.match(n) and PRED_RE.match(n).group(2) in V09_MODELS:
            preds.append(p)
        elif n.endswith(".meta.json") or n.endswith(".log"):
            groups["runmeta"].append(p)
        elif n.startswith(("run_v09_", "score_v09", "catalog_")) or n.endswith(".sh"):
            groups["drivers"].append(p)
        else:
            groups["other"].append(p)

    lines = [LEGEND, "## Predictions status (regime × model × split)\n",
             "| regime | model | split | preds | empty | calls log |", "|---|---|---|---:|---:|---|"]
    grid: dict = defaultdict(dict)
    for p in sorted(preds):
        m = PRED_RE.match(p.name)
        reg, model, split = m.group(1), m.group(2), m.group(3)
        c = count_lines(p)
        e = empties(p)
        has_calls = "✓" if (p.with_suffix(".calls.jsonl")).exists() else "—"
        lines.append(f"| {REGIME[reg]} | {model} | {split} | {c} | {e} | {has_calls} |")
        grid[(model)][f"{reg}_{split}"] = c
    if not preds:
        lines.append("| _(no prediction files yet)_ | | | | | |")

    # other groups: just list with counts
    titles = {"sample": "Sample", "prompts": "Prompt sets (input)", "calls": "Call logs (rich)",
              "runmeta": "Run meta / logs", "drivers": "Drivers", "other": "Other / legacy (v07 etc.)"}
    for key in ("sample", "prompts", "calls", "drivers", "runmeta", "other"):
        gp = groups.get(key)
        if not gp:
            continue
        lines.append(f"\n## {titles[key]}")
        for p in gp:
            suffix = f"  ({count_lines(p)} lines)" if p.suffix == ".jsonl" else ""
            lines.append(f"- `{p.name}`{suffix}")

    out = B / "INDEX.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out}")
    print(f"     {len(preds)} prediction files, {len(groups.get('calls', []))} call logs, "
          f"{len(groups.get('other', []))} legacy/other")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
