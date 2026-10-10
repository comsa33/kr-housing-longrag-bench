#!/usr/bin/env python3
"""Emit v0.6 release split files from data/qa_v0.6_realistic_candidates.jsonl.

  data/qa_v0.6_dev.jsonl                      : split=dev, answers included
  data/qa_v0.6_test_public.jsonl              : split=test_public, answers included
  data/qa_v0.6_test_hidden_questions.jsonl    : split=test_hidden, answers/predicate/gold MASKED (public)
  workspace_local/audit/qa_v0.6_test_hidden_answers.jsonl : split=test_hidden, full (INTERNAL only)

A truly-hidden split must not ship answers in a public file, so test_hidden public rows carry only the
question + locators (answer='[HELD OUT]', gold_predicate/gold_terms/gold_numbers removed). Announcement-
level splits guarantee no announcement crosses dev/test boundaries (verified separately).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "qa_v0.6_realistic_candidates.jsonl"
DEV = ROOT / "data" / "qa_v0.6_dev.jsonl"
TPUB = ROOT / "data" / "qa_v0.6_test_public.jsonl"
THID_Q = ROOT / "data" / "qa_v0.6_test_hidden_questions.jsonl"
THID_A = ROOT / "workspace_local" / "audit" / "qa_v0.6_test_hidden_answers.jsonl"


def mask(item: dict) -> dict:
    out = dict(item)
    out["answer"] = "[HELD OUT]"
    out.pop("gold_predicate", None)
    out.pop("row_ids", None)  # row_ids enumerate predicate matches -> would leak the answer set
    ev = dict(out.get("evaluation", {}))
    ev = {"metric": ev.get("metric", "")}  # drop gold_terms / gold_numbers
    out["evaluation"] = ev
    out["answer_masked"] = True
    return out


def write(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main() -> int:
    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    dev = [r for r in rows if r.get("split") == "dev"]
    tpub = [r for r in rows if r.get("split") == "test_public"]
    thid = [r for r in rows if r.get("split") == "test_hidden"]

    write(DEV, dev)
    write(TPUB, tpub)
    # test_hidden was merged into test_public in v0.9 (a larger public held-out test is more valuable than a
    # sealed set we cannot serve; see DATASET_CARD). Emit hidden files only if any test_hidden rows remain
    # (kept so a future release can re-carve a hidden split from grown data).
    if thid:
        write(THID_Q, [mask(r) for r in thid])
        write(THID_A, thid)

    # leakage guard: no announcement may cross any two distinct splits (dev / test_public / test_hidden)
    import re
    def anns(r):
        s = set(r.get("announcement_ids", []) or [])
        for p in r.get("page_ids", []) or []:
            m = re.match(r"(.+)-p\d{3}$", p)
            if m:
                s.add(m.group(1))
        return s
    split_of_ann = {}
    leak = []
    for r in rows:
        for a in anns(r):
            sp = r.get("split")
            if a in split_of_ann and split_of_ann[a] != sp:
                leak.append((a, split_of_ann[a], sp))
            split_of_ann.setdefault(a, sp)

    print("=== v0.6 splits ===")
    print(f"  dev: {len(dev)} -> {DEV.name}")
    print(f"  test_public: {len(tpub)} -> {TPUB.name}")
    print(f"  test_hidden: {len(thid)} ({'merged into test_public (v0.9)' if not thid else 'masked -> ' + THID_Q.name})")
    leak_anns = {a for a, _, _ in leak}
    print(f"  cross-split announcement leakage: {len(leak_anns)}" + (f"  !! {sorted(leak)[:3]}" if leak else ""))
    return 1 if leak else 0


if __name__ == "__main__":
    raise SystemExit(main())
