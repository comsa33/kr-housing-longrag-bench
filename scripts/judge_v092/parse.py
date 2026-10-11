#!/usr/bin/env python3
"""Parse raw Claude batch results into verdicts.

    python3 scripts/judge_v092/parse.py WORKDIR NAME INDEX.jsonl

Reads WORKDIR/raw_NAME.jsonl, joins each custom_id to its INDEX row and writes
WORKDIR/verdicts_NAME.json (index fields + "claude": "YES"/"NO"). Requests that did not succeed or
whose text is not the schema JSON are counted, not guessed. If the index has human-80 rows, prints
the agreement with the human labels.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path


def main() -> int:
    work, name, index = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    idx = {}
    for line in open(index, encoding="utf-8"):
        d = json.loads(line)
        idx[d["custom_id"]] = d
    out, bad, usage = [], collections.Counter(), collections.Counter()
    for line in open(work / f"raw_{name}.jsonl", encoding="utf-8"):
        r = json.loads(line)
        res = r["result"]
        if res["type"] != "succeeded":
            bad[res["type"]] += 1
            continue
        m = res["message"]
        usage["in"] += m["usage"]["input_tokens"]
        usage["out"] += m["usage"]["output_tokens"]
        txt = "".join(b.get("text", "") for b in m["content"] if b["type"] == "text")
        try:
            v = json.loads(txt)["verdict"]
        except Exception:
            bad["unparsed"] += 1
            continue
        out.append({**idx[r["custom_id"]], "claude": v})
    json.dump(out, open(work / f"verdicts_{name}.json", "w"), ensure_ascii=False)
    print("parsed", len(out), "bad", dict(bad), "usage", dict(usage))
    h = [o for o in out if o.get("set") == "human80"]
    if h:
        agree = sum((o["claude"] == "YES") == (o["human"] == "Y") for o in h)
        print(f"human80 agreement {agree}/{len(h)} = {100 * agree / len(h):.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
