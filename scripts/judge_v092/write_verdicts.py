#!/usr/bin/env python3
"""Write the released v0.9.2 verdict files from parsed batch results. No API calls.

    python3 scripts/judge_v092/write_verdicts.py \
        --test-index WORK/index.jsonl \
        --claude-test WORK/verdicts_smoke.json WORK/verdicts_full.json \
        --claude-multi WORK/verdicts_multi.json \
        --claude-dev DEVWORK/verdicts_devsmoke.json DEVWORK/verdicts_devfull.json \
        --gpt-goldfix WORK/gpt_raw_goldfix.jsonl --gpt-multi WORK/gpt_raw_multi.jsonl \
        --out results/judge_verdicts_v0.9.2

Rules
- claude-sonnet-5-5/<tag>.jsonl: Claude verdict per (tag, qa_id); for accept-any items the
  multi-answer verdict replaces the first-batch verdict. Dev rows are added for the GPT core tags.
- gpt-4.1-mini/<tag>.jsonl: the released v0.9.1 verdict (results/judge_verdicts/<tag>.jsonl),
  restricted to the v0.9.2 scope; the 24 gold-fixed items take the re-judge verdict
  (multi-answer batch for accept-any items, gold-fix batch for the replaced item).
- human80_claude-sonnet-5-5.jsonl: Claude verdicts on the human-labelled judge-validation sample.
Scope: legal family and data/v0.9.2/eval_exclusions ids dropped. Rows sorted by qa_id.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from common import LEGAL, RELEASED_V091, ROOT, gold_fixes, load, write_jsonl


def gpt_raw(p: str) -> dict[str, bool]:
    return {r["custom_id"]: "YES" in r["response"]["body"]["choices"][0]["message"]["content"].upper()
            for r in load(Path(p))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-index", required=True)
    ap.add_argument("--claude-test", nargs="+", required=True)
    ap.add_argument("--claude-multi", required=True)
    ap.add_argument("--claude-dev", nargs="*", default=[])
    ap.add_argument("--gpt-goldfix", required=True)
    ap.add_argument("--gpt-multi", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    fix = gold_fixes()
    excl = set(fix["exclude_from_evaluation"])
    gold = {d["qa_id"]: d for sp in ("dev", "test_public") for d in load(ROOT / f"data/qa_v0.6_{sp}.jsonl")}
    ins = {q for q, d in gold.items() if d.get("task_type") != LEGAL and q not in excl}

    idx = {d["custom_id"]: d for d in load(Path(a.test_index))}
    first = {}
    for f in a.claude_test:
        first.update({o["custom_id"]: o for o in json.load(open(f))})
    multi = {o["orig_custom_id"]: o for o in json.load(open(a.claude_multi))}
    claude: dict[str, dict[str, bool]] = defaultdict(dict)
    human80 = []
    for cid, i in idx.items():
        o = first[cid]
        if i["set"] == "human80":
            human80.append({"qa_id": i["qa_id"], "claude_sonnet_5_5": o["claude"] == "YES", "human": i["human"]})
            continue
        v = multi[cid]["claude"] if cid in multi else o["claude"]
        claude[i["tag"]][i["qa_id"]] = v == "YES"
    for f in a.claude_dev:
        for o in json.load(open(f)):
            claude[o["tag"]][o["qa_id"]] = o["claude"] == "YES"

    g_fix, g_multi = gpt_raw(a.gpt_goldfix), gpt_raw(a.gpt_multi)
    gpt: dict[str, dict[str, bool]] = {}
    for tag in claude:
        v = {r["qa_id"]: bool(r["judge_correct"]) for r in load(RELEASED_V091 / f"{tag}.jsonl") if r["qa_id"] in ins}
        for cid, i in idx.items():
            if i["set"] == "core_or_agg" and i["tag"] == tag:
                if "g" + cid[1:] in g_multi:
                    v[i["qa_id"]] = g_multi["g" + cid[1:]]
                elif cid in g_fix:
                    v[i["qa_id"]] = g_fix[cid]
        gpt[tag] = v

    for judge, table in (("claude-sonnet-5-5", claude), ("gpt-4.1-mini", gpt)):
        (out / judge).mkdir(parents=True, exist_ok=True)
        for tag, v in table.items():
            write_jsonl(out / judge / f"{tag}.jsonl", [{"qa_id": q, "judge_correct": v[q]} for q in sorted(v)])
    write_jsonl(out / "human80_claude-sonnet-5-5.jsonl", human80)
    print("tags", len(claude), "claude rows", sum(map(len, claude.values())), "gpt rows", sum(map(len, gpt.values())),
          "human80", len(human80))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
