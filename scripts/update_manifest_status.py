#!/usr/bin/env python3
"""Augment data/source_manifest.jsonl with confirmed v0.2 acquisition status (from audit records).

Adds a `v0.2_acquisition` object to each processed source. No raw text is added; only short factual
status (acquired flag, date, pinned statute version, internal-only full-text flag, data blockers).
Existing fields/order preserved.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AUDIT = ROOT / "workspace_local" / "audit"
MAN = DATA / "source_manifest.jsonl"

STATUTE_IDS = {"law-housing-supply-rule", "law-public-housing-special-act-rule",
               "law-private-rental-housing-special-act"}
META_ONLY = {"hug-sale-history", "molit-apt-official-price-2025"}


def main() -> int:
    rows = [json.loads(l) for l in MAN.open(encoding="utf-8") if l.strip()]
    for r in rows:
        sid = r["source_id"]
        af = AUDIT / f"{sid}.json"
        if not af.exists():
            continue
        audit = json.loads(af.read_text(encoding="utf-8"))
        status = {
            "batch": "v0.2",
            "acquired": True,
            "downloaded_at": audit.get("downloaded_at"),
            "audit_file": f"workspace_local/audit/{sid}.json",
            "release_decision": audit.get("release_decision"),
        }
        if sid in STATUTE_IDS:
            pv = audit.get("pinned_version", {})
            status.update({
                "pinned_lsiSeq": pv.get("lsiSeq"),
                "pinned_efYd": pv.get("efYd"),
                "internal_full_text_extracted": True,
                "extraction_dir": f"workspace_local/processed/{sid}/",
                "note": "조문/별표참조/chunk 추출 완료(내부 전용). 공개물은 locator+단답만.",
            })
        elif sid in META_ONLY:
            status.update({
                "internal_full_text_extracted": False,
                "data_acquisition_blocker": audit.get("data_acquisition_blocker"),
                "note": "메타데이터만 취득. 실데이터(행)는 키/포털 게이트로 미취득.",
            })
        else:  # policy pages
            status.update({
                "internal_full_text_extracted": True,
                "extraction_dir": f"workspace_local/processed/{sid}/",
                "note": "정책/유형 사실값 추출 완료(내부 전용).",
            })
        r["v0.2_acquisition"] = status

    with MAN.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"updated {sum(1 for r in rows if 'v0.2_acquisition' in r)}/{len(rows)} manifest entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
