#!/usr/bin/env python3
"""Build OpenAI Batch API input for the gpt-4.1-mini re-judge of gold-fixed items. No API calls.

The secondary judge keeps its v0.9.1 verdicts except on the 24 gold-fixed items, which were
re-judged with the same prompt text the Claude judge saw:

    # 1) all 24 gold-fixed items (532 run x item pairs), from prompts.jsonl
    python3 scripts/judge_v092/build_gpt_rejudge.py WORKDIR/prompts.jsonl WORKDIR/index.jsonl \
        WORKDIR/gpt_input_goldfix.jsonl --gold-fixed
    # 2) the 23 accept-any items with the multi-answer gold (511 pairs); this supersedes (1) for them
    python3 scripts/judge_v092/build_gpt_rejudge.py WORKDIR/prompts_multi.jsonl WORKDIR/index_multi.jsonl \
        WORKDIR/gpt_input_multi.jsonl

Request body as in scripts/llm_judge.py (max_tokens 4, temperature 0). Submit the file with the
OpenAI Batch API (/v1/chat/completions); a verdict is correct iff "YES" is in the reply (upper-cased),
the same rule llm_judge.py applies.
"""
from __future__ import annotations

import argparse
import json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prompts")
    ap.add_argument("index")
    ap.add_argument("out")
    ap.add_argument("--gold-fixed", action="store_true", help="keep only index rows with gold_fixed=true")
    ap.add_argument("--model", default="gpt-4.1-mini")
    a = ap.parse_args()
    idx = {}
    for line in open(a.index, encoding="utf-8"):
        d = json.loads(line)
        idx[d["custom_id"]] = d
    n = 0
    with open(a.out, "w", encoding="utf-8") as f:
        for line in open(a.prompts, encoding="utf-8"):
            p = json.loads(line)
            i = idx[p["custom_id"]]
            if i.get("set") != "core_or_agg" or (a.gold_fixed and not i.get("gold_fixed")):
                continue
            f.write(json.dumps({"custom_id": p["custom_id"], "method": "POST", "url": "/v1/chat/completions",
                                "body": {"model": a.model, "messages": [{"role": "user", "content": p["prompt"]}],
                                         "max_tokens": 4, "temperature": 0.0}}, ensure_ascii=False) + "\n")
            n += 1
    print("requests", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
