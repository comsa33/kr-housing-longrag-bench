#!/usr/bin/env python3
"""Record confirmed factual metadata for the 4 non-statute sources into workspace_local/processed/.

These facts were read from the acquired HTML (kogl-license-guide, public-data-portal-use-policy,
hug-sale-history, molit-apt-official-price-2025) and are short, factual public-data-registry /
official-policy facts (not creative copyrighted content). Raw HTML stays internal-only.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "workspace_local" / "processed"

METADATA = {
    "kogl-license-guide": {
        "provider": "공공누리",
        "source_url": "https://www.kogl.or.kr/info/license.do",
        "license_types": {
            "제0유형": {"출처표시": False, "상업적이용": True, "2차적저작물": True,
                       "요약": "이용조건(출처표시 포함) 없이 자유롭게 이용"},
            "제1유형": {"출처표시": True, "상업적이용": True, "2차적저작물": True},
            "제2유형": {"출처표시": True, "상업적이용": False, "2차적저작물": True,
                       "요약": "출처표시 + 상업적 이용금지(비상업적만)"},
            "제3유형": {"출처표시": True, "상업적이용": True, "2차적저작물": False,
                       "요약": "출처표시 + 변경(2차적 저작물) 금지"},
            "제4유형": {"출처표시": True, "상업적이용": False, "2차적저작물": False,
                       "요약": "출처표시 + 상업적 이용금지 + 변경금지"},
            "AI유형": {"출처표시": False, "상업적이용": True, "2차적저작물": True,
                      "개별조건": "공공저작물을 학습한 AI 모델의 상업적 이용은 가능하나, 공공저작물로 제작한 "
                                "인공지능 학습용 데이터의 재판매는 금지"},
        },
    },
    "public-data-portal-use-policy": {
        "provider": "공공데이터포털",
        "source_url": "https://www.data.go.kr/en/ugs/selectPortalPolicyView.do",
        "key_facts": {
            "third_party_rights": "저작권 등 제3자 권리가 포함된 공공데이터는 권리자의 정당한 이용허락을 확보해야 한다.",
        },
    },
    "hug-sale-history": {
        "provider": "주택도시보증공사",
        "source_url": "https://www.data.go.kr/data/15057686/openapi.do",
        "confirmed_facts": {
            "데이터포맷": "XML",
            "비용부과유무": "무료",
            "이용허락범위": "이용허락범위 제한 없음",
            "수정일": "2026-01-29",
            "확인된_키워드_필드": ["세대수", "분양가", "보증발급일", "지역"],
        },
        "field_note": "전체 필드(사업장명·세대수·분양가격·지역명·모집공고승인일·분양개시일·보증발급일자)는 "
                      "API 명세 설명에 기재됨(seed QA 근거). 페이지 본문에서 직접 확인된 키워드 필드만 별도 표기.",
        "data_acquisition_blocker": "실데이터(행)는 data.go.kr serviceKey 필요 → 미취득.",
    },
    "molit-apt-official-price-2025": {
        "provider": "국토교통부",
        "source_url": "https://www.data.go.kr/data/3073746/fileData.do",
        "confirmed_facts": {
            "파일데이터명": "국토교통부_주택 공시가격 정보_20250626",
            "확장자": "CSV",
            "건수": "15,580,435건",
            "총행수_헤더포함": "15,580,436행",
            "인코딩": "UTF-8",
            "비용부과유무": "무료",
            "이용허락범위": "이용허락범위 제한 없음",
            "기준일": "2025-01-01 (25.1.1. 기준 공동주택 호별 공시가격)",
            "수정일": "2025-11-13",
        },
        "data_acquisition_blocker": "전체 CSV(약 15.58M행)는 포털 파일 다운로드 절차(세션/이용신청) 게이트 → 미취득.",
    },
}


def main() -> int:
    for sid, meta in METADATA.items():
        out = PROC / sid
        out.mkdir(parents=True, exist_ok=True)
        (out / "metadata.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        report = {
            "source_id": sid,
            "tooling": {"method": "manual read of acquired HTML + verification regex"},
            "extracted": "short factual public-data registry / official policy facts only",
            "failures": ([] if "data_acquisition_blocker" not in meta else
                         [{"item": "bulk data", "reason": meta["data_acquisition_blocker"],
                           "fallback": "URL + 메타데이터/스키마 라벨만 공개; 실데이터 취득은 다음 batch(키 발급/포털 다운로드)."}]),
            "confidence": "high (facts cross-checked against page text).",
        }
        (out / "extraction_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  wrote processed/{sid}/metadata.json + extraction_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
