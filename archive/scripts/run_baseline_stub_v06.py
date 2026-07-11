#!/usr/bin/env python3
"""Produce trivial baseline predictions for the v0.6 benchmark (NO model call).

These are reference floors/ceilings to sanity-check the eval harness and to give a paper its trivial
baselines, not real systems:

  oracle    — copies the gold answer (upper bound; should score ~100% via eval_harness_v06.py)
  dummy     — always answers a fixed "unanswerable" string (floor; only answerability_detection hits)
  random    — deterministically picks another item's gold answer (chance-level floor; fixed seed)
  echo      — echoes the question text (near-zero floor)

Gold is read from the SAME sources as the harness: dev/test_public from data/, test_hidden from the
INTERNAL workspace_local file. Because `oracle`/`random` predictions are DERIVED from gold answers
(incl. the masked test_hidden answers), ALL baseline prediction files are written under
workspace_local/audit/ (never the public data/ dir). Score them with:

  python3 scripts/eval_harness_v06.py --pred workspace_local/audit/baseline_oracle_v06.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = {
    "dev": ROOT / "data" / "qa_v0.6_dev.jsonl",
    "test_public": ROOT / "data" / "qa_v0.6_test_public.jsonl",
    "test_hidden": ROOT / "workspace_local" / "audit" / "qa_v0.6_test_hidden_answers.jsonl",
}
OUT_DIR = ROOT / "workspace_local" / "audit"
DUMMY_ANSWER = "제공된 자료만으로는 확정할 수 없음"
BASELINES = ("oracle", "dummy", "random", "echo")


def load(path: Path) -> list:
    return [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()] if path.exists() else []


def predict(name: str, items: list) -> dict:
    """Return qa_id -> prediction string for the named baseline."""
    if name == "oracle":
        return {it["qa_id"]: it.get("answer", "") for it in items}
    if name == "dummy":
        return {it["qa_id"]: DUMMY_ANSWER for it in items}
    if name == "echo":
        return {it["qa_id"]: it.get("question", "") for it in items}
    if name == "random":
        # Deterministic "random": shift gold answers by a fixed offset (no RNG → reproducible).
        answers = [it.get("answer", "") for it in items]
        n = len(answers)
        off = max(1, n // 3)
        return {it["qa_id"]: answers[(i + off) % n] for i, it in enumerate(items)}
    raise ValueError(f"unknown baseline {name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", choices=BASELINES + ("all",), default="all")
    ap.add_argument("--splits", default="dev,test_public,test_hidden")
    args = ap.parse_args()

    splits = [s.strip() for s in args.splits.split(",") if s.strip()]
    items: list = []
    for sp in splits:
        for it in load(GOLD[sp]):
            it["_split"] = sp
            items.append(it)
    if not items:
        print("no gold loaded")
        return 1

    names = list(BASELINES) if args.baseline == "all" else [args.baseline]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in names:
        preds = predict(name, items)
        out = OUT_DIR / f"baseline_{name}_v06.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for qid, p in preds.items():
                f.write(json.dumps({"qa_id": qid, "prediction": p}, ensure_ascii=False) + "\n")
        print(f"  {name:8s} -> {out.relative_to(ROOT)} ({len(preds)} predictions)")
    print(f"=== baseline stub v0.6: {len(items)} items over {splits}; INTERNAL (derived from gold) ===")
    print("score with: python3 scripts/eval_harness_v06.py --pred workspace_local/audit/baseline_<name>_v06.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
