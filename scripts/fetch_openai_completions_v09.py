#!/usr/bin/env python3
"""Pull our stored OpenAI chat completions (input/output/usage) back from the API.

When data logging/sharing is enabled, OpenAI retains recent chat completions and exposes them via
GET /v1/chat/completions (list) + /v1/chat/completions/{id}/messages (the input). This recovers the
rich per-request data the local runner did not save for the gpt-4.1-mini run (token usage, exact output),
and lets us reconcile to qa_id by matching the output/input text to our prediction/prompt files.

Pages newest-first until `--since` (unix seconds) or pages exhausted, dumps each completion to an
INTERNAL jsonl, and prints per-model aggregates (count, prompt/completion tokens, est USD). With
`--with-input` it also fetches each completion's input message (1 extra call each; slower).

Output is INTERNAL (workspace_local/, gitignored). Needs OPENAI_API_KEY.

Usage:
    python3 scripts/fetch_openai_completions_v09.py --since 1749513600
    python3 scripts/fetch_openai_completions_v09.py --since 1749513600 --with-input
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "workspace_local" / "audit" / "baselines" / "openai_stored_completions.jsonl"
# gpt-4.1-mini list price (USD per 1M tokens) for a rough cost estimate; confirm on the dashboard.
PRICE = {"gpt-4.1-mini": (0.40, 1.60), "gpt-4.1-nano": (0.10, 0.40)}


def _key() -> str:
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k
    t = (ROOT / "workspace_local" / "secrets" / "openai_api.key").read_text()
    m = re.search(r"sk-[A-Za-z0-9_\-]+", t)
    return m.group(0) if m else t.strip()


def _get(url: str, key: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=0, help="stop paging at completions created before this unix time")
    ap.add_argument("--with-input", action="store_true", help="also fetch each completion's input message (slower)")
    ap.add_argument("--max-pages", type=int, default=80)
    args = ap.parse_args()
    key = _key()

    rows: list[dict] = []
    after = None
    for _ in range(args.max_pages):
        url = "https://api.openai.com/v1/chat/completions?limit=100"
        if after:
            url += f"&after={after}"
        try:
            page = _get(url, key)
        except urllib.error.HTTPError as e:
            raise SystemExit(f"list failed: HTTP {e.code} {e.read().decode('utf-8','ignore')[:200]}")
        data = page.get("data", [])
        if not data:
            break
        stop = False
        for c in data:
            if args.since and c.get("created", 0) < args.since:
                stop = True
                break
            u = c.get("usage") or {}
            rec = {
                "id": c.get("id"), "request_id": c.get("request_id"), "created": c.get("created"),
                "model": c.get("model"), "prompt_tokens": u.get("prompt_tokens"),
                "completion_tokens": u.get("completion_tokens"), "total_tokens": u.get("total_tokens"),
                "output": (c.get("choices") or [{}])[0].get("message", {}).get("content"),
            }
            if args.with_input:
                try:
                    msgs = _get(f"https://api.openai.com/v1/chat/completions/{c['id']}/messages?limit=10", key)
                    rec["input"] = next((m.get("content") for m in msgs.get("data", []) if m.get("role") == "user"), None)
                except urllib.error.HTTPError:
                    rec["input"] = None
            rows.append(rec)
        after = page.get("last_id")
        if stop or not page.get("has_more"):
            break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    agg: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])  # model -> [count, prompt_tok, completion_tok]
    for r in rows:
        a = agg[r["model"]]
        a[0] += 1
        a[1] += r.get("prompt_tokens") or 0
        a[2] += r.get("completion_tokens") or 0

    print(f"[ok] wrote {OUT} ({len(rows)} completions)")
    print(f"{'model':<28} {'count':>6} {'prompt_tok':>12} {'compl_tok':>11} {'est_usd':>9}")
    for model, (n, pt, ct) in sorted(agg.items()):
        base = next((p for k, p in PRICE.items() if model.startswith(k)), None)
        usd = (pt / 1e6 * base[0] + ct / 1e6 * base[1]) if base else None
        print(f"{model:<28} {n:>6} {pt:>12,} {ct:>11,} {('$'+format(usd,'.2f')) if usd is not None else '—':>9}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
