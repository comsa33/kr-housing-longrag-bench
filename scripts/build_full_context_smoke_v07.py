#!/usr/bin/env python3
"""Build a small INTERNAL full-context (class A) prompt set for a v0.7 smoke test.

Selects a few `test_public` QA that have a bundle and a SMALL context tier (32k/64k), embeds the actual
bundle text (from workspace_local/processed/bundles-v06/<bundle_id>.txt) into a full-context prompt, and
writes them to an INTERNAL file under workspace_local/audit/baselines/ so they can be fed to
scripts/run_llm_baseline_v07.py (which uses a record's `prompt` field directly).

Safety:
  * The output embeds raw bundle text, so it is written ONLY under workspace_local/ (gitignored). The
    script refuses any --out outside workspace_local/. Never publish this file or the bundle text.
  * Selection is deterministic (sorted by qa_id; no RNG), so the sample is reproducible.

This is a SMOKE selector (20-40 items), not a full benchmark run.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "data" / "qa_v0.6_realistic_candidates.jsonl"
BUNDLES = ROOT / "workspace_local" / "processed" / "bundles-v06"
DEFAULT_OUT = ROOT / "workspace_local" / "audit" / "baselines" / "full_context_smoke_prompts.jsonl"


def full_context_prompt(rec: dict, bundle_text: str) -> str:
    instr = rec.get("instruction", "주어진 근거 자료로 질문에 답하라.")
    question = rec.get("question", "")
    return (
        f"{instr}\n\n"
        f"[제공 문서] (아래 공고/번들 본문에서 근거를 찾으세요.)\n{bundle_text}\n\n"
        f"[질문]\n{question}\n\n"
        f"[지시] 위 문서 내용에 근거하여 답하세요. 문서에서 찾을 수 없으면 "
        f"'제공된 자료만으로는 확정할 수 없음'이라고 답하세요. 군더더기 없이 최종 답만 간단히 출력하세요."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test_public", choices=["test_public", "dev"])
    ap.add_argument("--tiers", default="32k,64k", help="comma-separated context tiers to include")
    ap.add_argument("--max-items", type=int, default=40, help="cap on selected items (smoke: 20-40)")
    ap.add_argument("--out", default=None, help="output JSONL (must be under workspace_local/)")
    args = ap.parse_args()

    out = Path(args.out).resolve() if args.out else DEFAULT_OUT
    wl = (ROOT / "workspace_local").resolve()
    if not out.is_relative_to(wl):
        raise SystemExit(f"--out must be under workspace_local/ (embeds bundle text). Got: {out}")

    tiers = {t.strip() for t in args.tiers.split(",") if t.strip()}
    rows = [json.loads(l) for l in QA.open(encoding="utf-8") if l.strip()]
    pool = [r for r in rows
            if r.get("split") == args.split and r.get("bundle_id") and r.get("context_tier") in tiers]
    pool.sort(key=lambda r: r["qa_id"])  # deterministic
    pool = pool[: args.max_items]
    if not pool:
        raise SystemExit("no QA matched the selection (split/tier/bundle)")

    out.parent.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    written = 0
    with out.open("w", encoding="utf-8") as f:
        for r in pool:
            bid = r["bundle_id"]
            if bid not in cache:
                bf = BUNDLES / f"{bid}.txt"
                cache[bid] = bf.read_text(encoding="utf-8") if bf.exists() else ""
            text = cache[bid]
            if not text:
                print(f"  WARN: missing bundle text for {bid}; skipping {r['qa_id']}")
                continue
            rec = {"qa_id": r["qa_id"], "split": r["split"], "task_type": r["task_type"],
                   "context_tier": r["context_tier"], "bundle_id": bid, "answer_type": r.get("answer_type"),
                   "question_style": r.get("question_style"),
                   "prompt": full_context_prompt(r, text)}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1

    print(f"=== full-context smoke selection ({args.split}, tiers={sorted(tiers)}) ===")
    print(f"selected {written} items over {len({r['bundle_id'] for r in pool})} bundles -> {out.relative_to(ROOT)} (INTERNAL)")
    print(f"tier:   {dict(collections.Counter(r['context_tier'] for r in pool))}")
    print(f"task:   {dict(collections.Counter(r['task_type'] for r in pool))}")
    print("qa_ids: " + ",".join(r["qa_id"] for r in pool))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
