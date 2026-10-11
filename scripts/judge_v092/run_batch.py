#!/usr/bin/env python3
"""Claude judge via the Message Batches API: submit / status / fetch.

    python3 scripts/judge_v092/run_batch.py submit WORKDIR NAME PROMPTS.jsonl IDS.txt|ALL
    python3 scripts/judge_v092/run_batch.py status WORKDIR NAME
    python3 scripts/judge_v092/run_batch.py fetch  WORKDIR NAME

The API key is read by the SDK from ANTHROPIC_API_KEY; never write it to WORKDIR.
`submit` records the batch id and request parameters in WORKDIR/batch_NAME.json and refuses to
resubmit the same NAME. `fetch` saves the raw results verbatim to WORKDIR/raw_NAME.jsonl before any
parsing (see parse.py).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from common import CLAUDE_PARAMS as PARAMS


def main() -> int:
    import anthropic
    cmd, work, name = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    c = anthropic.Anthropic()
    track = work / f"batch_{name}.json"
    if cmd == "submit":
        assert not track.exists(), "already submitted: " + str(track)
        prompts = [json.loads(l) for l in open(sys.argv[4], encoding="utf-8")]
        sel = None if sys.argv[5] == "ALL" else set(open(sys.argv[5]).read().split())
        reqs = [{"custom_id": p["custom_id"],
                 "params": {**PARAMS, "messages": [{"role": "user", "content": p["prompt"]}]}}
                for p in prompts if sel is None or p["custom_id"] in sel]
        b = c.messages.batches.create(requests=reqs)
        json.dump({"id": b.id, "n": len(reqs), "params": PARAMS,
                   "submitted": time.strftime("%Y-%m-%dT%H:%M:%S")}, open(track, "w"), indent=1)
        print("submitted", b.id, len(reqs))
    elif cmd == "status":
        t = json.load(open(track))
        b = c.messages.batches.retrieve(t["id"])
        print(b.processing_status, b.request_counts)
    elif cmd == "fetch":
        t = json.load(open(track))
        b = c.messages.batches.retrieve(t["id"])
        assert b.processing_status == "ended", b.processing_status
        raw = work / f"raw_{name}.jsonl"
        with open(raw, "w") as f:
            for r in c.messages.batches.results(t["id"]):
                f.write(r.model_dump_json() + "\n")
        print("saved raw", raw, b.request_counts)
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
