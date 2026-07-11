#!/usr/bin/env python3
"""Register the v0.3 MOLIT trade-detail source and mark v0.3 acquisition status on the manifest.

No raw data is added — only short factual registry metadata. Idempotent.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "data" / "source_manifest.jsonl"

NEW_SOURCES = [
    {
        "source_id": "molit-apt-trade-detail",
        "title": "국토교통부_아파트 매매 실거래가 상세 자료",
        "provider": "국토교통부",
        "source_type": "public_data_portal_open_api",
        "domain": "housing_price_table",
        "access_url": "https://www.data.go.kr/data/15057511/openapi.do",
        "registry_url": "https://www.data.go.kr/data/15057511/openapi.do",
        "license_basis": "Public Data Portal open API; 이용허락범위 제한 없음.",
        "license_status": "usable_public_data_no_known_restriction",
        "redistribution_policy": "Use rows for benchmark with provenance (_row_id). Do not redistribute raw payloads; "
                                 "public release carries row IDs, locators, predicates, short answers.",
        "corpus_inclusion": "rows_internal_only",
        "retrieved_at": "2026-06-04",
        "notes": "아파트 매매 실거래 상세(거래금액·전용면적·층·건축년도·법정동·거래연월). v0.3 표/수치 QA 핵심.",
    },
]

# v0.3 acquisition status to stamp on existing/new sources that were used this batch
V03_STATUS = {
    "lh-sale-announcements": {
        "batch": "v0.3", "acquired_internal": True,
        "internal_artifacts": ["workspace_local/raw/lh-sale-announcements/",
                                "workspace_local/processed/lh-sale-announcements/document_pages.jsonl",
                                "workspace_local/processed/lh-sale-announcements/numeric_facts.jsonl"],
        "announcements": 1, "announcement_title": "대전대동2 1블록 공공분양 입주자모집공고",
        "release_decision": "url_and_labels_only",
        "note": "공식 입주자모집공고 1건 내부 취득·추출(42페이지/537 numeric fact). 공개는 page locator+단답만.",
    },
    "hug-sale-history": {
        "batch": "v0.3", "acquired_internal": True,
        "internal_artifacts": ["workspace_local/processed/hug-sale-history/rows_v0.3.jsonl"],
        "rows": 623, "years": ["2023", "2024", "2025"], "regions": 16,
        "release_decision": "url_and_labels_only",
        "note": "오픈API 실데이터 623행 내부 취득. 공개는 _row_id+predicate+단답만.",
    },
    "molit-apt-trade-detail": {
        "batch": "v0.3", "acquired_internal": True,
        "internal_artifacts": ["workspace_local/processed/molit-apt-trade-detail/rows_v0.3.jsonl"],
        "rows": 20370, "year": "2025",
        "districts": ["서울 종로구", "서초구", "강남구", "송파구", "대전 동구", "유성구"],
        "release_decision": "url_and_labels_only",
        "note": "오픈API 실거래 상세 20,370행 내부 취득. 공개는 _row_id+predicate+단답만.",
    },
}


def main() -> int:
    rows = [json.loads(l) for l in MAN.open(encoding="utf-8") if l.strip()]
    by_id = {r["source_id"]: r for r in rows}
    for ns in NEW_SOURCES:
        if ns["source_id"] not in by_id:
            rows.append(ns)
            by_id[ns["source_id"]] = ns
    for sid, status in V03_STATUS.items():
        if sid in by_id:
            by_id[sid]["v0.3_acquisition"] = status
    with MAN.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"manifest sources now: {len(rows)} (added/ensured molit-apt-trade-detail; stamped v0.3 status on "
          f"{sum(1 for s in V03_STATUS if s in by_id)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
