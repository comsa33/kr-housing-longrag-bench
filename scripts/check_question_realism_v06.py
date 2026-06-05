#!/usr/bin/env python3
"""v0.6 question-realism validator (separate semantic guard the grounding verifier can't provide).

Checks the realism-rewritten QA file against the verified source (default data/qa_v0.5_candidates.jsonl):
the rewrite may ONLY change `question` (+ add original_question/question_style/rewrite_rationale); every
answer/evidence/predicate/id field must be byte-identical to the source.

HARD FAIL (exit 1):
  - any of answer/answer_type/evidence/source_ids/page_ids/row_ids/table_ids/cell_ids/gold_predicate/
    evaluation/split changed vs source (semantic-drift guard)
  - question_style missing/invalid or original_question missing
  - cloze-phrased share > 15%
  - diagnostic_probe share > 20%
  - forbidden scraped-markup tokens present
WARN: near-duplicate cluster share high; per-task_type real_user share low.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVARIANT = ["answer", "answer_type", "evidence", "source_ids", "page_ids", "row_ids",
             "table_ids", "cell_ids", "gold_predicate", "evaluation", "split"]
STYLES = {"real_user", "professional_analyst", "diagnostic_probe"}
FORBIDDEN = ("getDetailView", "return false", "onclick", "javascript:", "serviceKey")


def load(p: Path) -> list:
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()] if p.exists() else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qa", default="data/qa_v0.6_realistic_candidates.jsonl")
    ap.add_argument("--source", default="data/qa_v0.5_candidates.jsonl")
    ap.add_argument("--max-cloze", type=float, default=0.15)
    ap.add_argument("--max-diagnostic", type=float, default=0.20)
    args = ap.parse_args()

    rows = load(ROOT / args.qa)
    src = {r["qa_id"]: r for r in load(ROOT / args.source)}
    failures, warnings = [], []
    if not rows:
        print(f"FAIL: empty/missing {args.qa}")
        return 1

    styles, fam_style = Counter(), defaultdict(Counter)
    cloze = 0
    for r in rows:
        qid = r.get("qa_id", "?")
        # invariance vs source
        o = src.get(qid)
        if o is None:
            failures.append(f"{qid}: qa_id not in source (new/renamed item)")
        else:
            for k in INVARIANT:
                if o.get(k) != r.get(k):
                    failures.append(f"{qid}: invariant field '{k}' changed vs source")
                    break
        # realism fields
        st = r.get("question_style")
        if st not in STYLES:
            failures.append(f"{qid}: missing/invalid question_style {st!r}")
        if not r.get("original_question"):
            failures.append(f"{qid}: missing original_question")
        styles[st] += 1
        fam_style[r.get("task_type", "?")][st] += 1
        q = r.get("question", "")
        if "빈칸" in q or "____" in q:
            cloze += 1
        for tok in FORBIDDEN:
            if tok in q:
                failures.append(f"{qid}: forbidden token {tok!r} in question")

    n = len(rows)
    cloze_pct = cloze / n
    diag_pct = styles.get("diagnostic_probe", 0) / n
    if cloze_pct > args.max_cloze:
        failures.append(f"cloze-phrased share {cloze_pct:.1%} > {args.max_cloze:.0%}")
    if diag_pct > args.max_diagnostic:
        failures.append(f"diagnostic_probe share {diag_pct:.1%} > {args.max_diagnostic:.0%}")

    # near-duplicate clusters (token Jaccard >= 0.92 within task_type)
    near = 0
    by_fam = defaultdict(list)
    for r in rows:
        by_fam[r.get("task_type", "?")].append(set(re.findall(r"[0-9A-Za-z가-힣]+", r.get("question", ""))))
    for toks in by_fam.values():
        for i in range(len(toks)):
            for j in range(i + 1, len(toks)):
                if toks[i] and toks[j] and len(toks[i] & toks[j]) / len(toks[i] | toks[j]) >= 0.92:
                    near += 1
                    break
    if near > n * 0.12:
        warnings.append(f"near-duplicate questions ~{near} ({near/n:.1%}) — review templating")
    # per-task_type real_user share (info/warn)
    for fam, c in sorted(fam_style.items()):
        ru = (c.get("real_user", 0) + c.get("professional_analyst", 0)) / max(sum(c.values()), 1)
        if ru < 0.5 and sum(c.values()) >= 20:
            warnings.append(f"task_type {fam}: real_user+analyst share {ru:.0%} < 50%")

    print("== question realism v0.6 ==")
    print(f"qa: {args.qa}  count: {n}")
    print(f"question_style: {dict(styles)}")
    print(f"cloze-phrased: {cloze} ({cloze_pct:.1%})  |  diagnostic_probe: {diag_pct:.1%}")
    print(f"real_user+professional_analyst: {(styles.get('real_user',0)+styles.get('professional_analyst',0))/n:.1%}")
    print(f"near-duplicate clusters (approx): {near}")
    for w in warnings:
        print(f"WARN: {w}")
    for f in failures[:40]:
        print(f"FAIL: {f}")
    print(f"failures: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
