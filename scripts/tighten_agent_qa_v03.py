#!/usr/bin/env python3
"""Trim over-long agent gold_terms to short verbatim substrings (no long excerpts in public files).

A prefix of a verbatim phrase is still a verbatim substring, so grounding is preserved. Operates on
workspace_local/audit/qa_v03_agent_raw.json in place (backup kept).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import qa_common as V2
import qa_v03_common as C

RAW = C.ROOT / "workspace_local" / "audit" / "qa_v03_agent_raw.json"
MAX = 26


def lh_norm() -> str:
    return V2.norm("\n".join(p["text"] for p in C.lh_pages()))


def trim(term: str) -> str:
    if len(term) <= MAX:
        return term
    cut = term[:MAX]
    if " " in cut[10:]:
        cut = cut[:cut.rindex(" ")]
    return cut.strip()


def main() -> int:
    rows = json.loads(RAW.read_text(encoding="utf-8"))
    shutil.copy(RAW, RAW.with_suffix(".json.bak"))
    lh = lh_norm()
    law_cache = {}
    n = 0
    for row in rows:
        it = row["item"]
        cited = set(it.get("source_ids", [])) | {e["source_id"] for e in it.get("evidence", [])}
        corp = [lh] if C.LH in cited else []
        for s in cited:
            if s.startswith("law-"):
                corp.append(law_cache.setdefault(s, V2.norm(V2.full_text(s))))
        gts = it.get("evaluation", {}).get("gold_terms", [])
        for i, t in enumerate(gts):
            if len(t) > MAX:
                nt = trim(t)
                if V2.norm(nt) and any(V2.norm(nt) in c for c in corp):
                    gts[i] = nt
                    n += 1
    RAW.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"trimmed {n} long gold_terms (backup: {RAW.with_suffix('.json.bak').name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
