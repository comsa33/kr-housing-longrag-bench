#!/usr/bin/env python3
"""Shared v0.4 loaders: multi-announcement LH corpus + region resolution + grounding helpers.

v0.4 expands the single-LH v0.3 corpus to 10 official LH announcements
(workspace_local/processed/lh-sale-announcements-v04/<announcement_id>/). LH announcement facts are
extracted by a regex over pdftotext output (NOT a structured table), so LH-based QA is grounded by
verbatim gold_term/value match against the cited page text — NOT by predicate recompute. The MOLIT/HUG
predicate recompute engine is reused unchanged from qa_v03_common for table/cross-source aggregation.

All corpus loaded here lives ONLY under workspace_local/processed (internal, gitignored); public QA
files carry locators + short answers + predicates, never page text.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache

import qa_common as V2
import qa_v03_common as C

ROOT = C.ROOT
PROC = C.PROC
AUDIT = ROOT / "workspace_local" / "audit"

LH_V04 = "lh-sale-announcements-v04"
V04_DIR = PROC / LH_V04

# Statute sources reused from v0.2/v0.3 for cross_document_legal_reasoning.
STATUTES = (
    "law-housing-supply-rule",
    "law-public-housing-special-act-rule",
    "law-private-rental-housing-special-act",
)

# Sido tokens in priority order (longer/more specific first where they overlap).
SIDO = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시", "울산광역시",
    "세종특별자치시", "경기도", "강원특별자치도", "강원도", "충청북도", "충청남도",
    "전북특별자치도", "전라북도", "전라남도", "경상북도", "경상남도", "제주특별자치도",
]
# Map an announcement sido token to the HUG _query_area_name vocabulary (HUG uses pre-2023 names).
SIDO_TO_HUG = {
    "강원특별자치도": "강원도", "강원도": "강원도",
    "전북특별자치도": "전라북도", "전라북도": "전라북도",
    "경기도": "경기도", "대전광역시": "대전광역시", "충청북도": "충청북도",
    "충청남도": "충청남도", "전라남도": "전라남도", "경상북도": "경상북도",
    "경상남도": "경상남도", "서울특별시": "서울특별시", "부산광역시": "부산광역시",
    "대구광역시": "대구광역시", "인천광역시": "인천광역시", "광주광역시": "광주광역시",
    "울산광역시": "울산광역시", "제주특별자치도": "제주특별자치도",
}


def _jl(path):
    return C._load_jsonl(path)


@lru_cache(maxsize=None)
def announcement_ids() -> tuple:
    if not V04_DIR.exists():
        return tuple()
    return tuple(sorted(p.name for p in V04_DIR.iterdir()
                        if p.is_dir() and (p / "document_pages.jsonl").exists()))


@lru_cache(maxsize=None)
def ann_pages(ann_id: str) -> list:
    return _jl(V04_DIR / ann_id / "document_pages.jsonl")


@lru_cache(maxsize=None)
def ann_facts(ann_id: str) -> list:
    return _jl(V04_DIR / ann_id / "numeric_facts.jsonl")


@lru_cache(maxsize=None)
def all_pages() -> list:
    out = []
    for a in announcement_ids():
        out.extend(ann_pages(a))
    return out


@lru_cache(maxsize=None)
def page_by_id() -> dict:
    return {p["page_id"]: p for p in all_pages()}


@lru_cache(maxsize=None)
def v04_page_ids() -> frozenset:
    return frozenset(page_by_id().keys())


@lru_cache(maxsize=None)
def ann_meta() -> dict:
    """announcement_id -> metadata from the merged extraction index (title/date/region/url)."""
    idx_path = AUDIT / "index_lh_v04.json"
    out = {}
    if idx_path.exists():
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
        for a in idx.get("announcements", []):
            out[a["announcement_id"]] = a
    return out


def page_text(pid: str) -> str:
    p = page_by_id().get(pid)
    return p["text"] if p else ""


def page_no_of(pid: str) -> int | None:
    p = page_by_id().get(pid)
    return p["page_no"] if p else None


def page_id_for(ann_id: str, page_no: int) -> str:
    return f"{ann_id}-p{page_no:03d}"


# ----------------------------------------------------------------- region resolution
@lru_cache(maxsize=None)
def supply_location(ann_id: str) -> str:
    """The 공급위치/건설위치 line value from the first pages (verbatim, for grounding)."""
    for p in ann_pages(ann_id)[:4]:
        m = re.search(r"(?:공급위치|건설위치)\s*[:：]\s*([^\n]+)", p["text"])
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


@lru_cache(maxsize=None)
def ann_sido(ann_id: str) -> str | None:
    loc = supply_location(ann_id)
    for s in SIDO:
        if s in loc:
            return s
    return None


@lru_cache(maxsize=None)
def ann_sigungu(ann_id: str) -> str | None:
    """'<sido> <gu/si>' matching MOLIT _lawd_name when the region is covered, else None."""
    loc = supply_location(ann_id)
    sido = ann_sido(ann_id)
    if not sido:
        return None
    # find a 구/시 token following the sido in the location string
    after = loc.split(sido, 1)[1] if sido in loc else ""
    m = re.search(r"([가-힣]+(?:구|시|군))", after)
    if not m:
        return None
    return f"{sido} {m.group(1)}"


@lru_cache(maxsize=None)
def ann_short_region(ann_id: str) -> str:
    """A short verbatim region token guaranteed present in page 1 (for gold_terms)."""
    sg = ann_sigungu(ann_id)
    if sg:
        return sg.split()[-1]  # e.g. 동구 / 시흥시 / 남양주시
    return ann_sido(ann_id) or ""


# ----------------------------------------------------------------- fact uniqueness (cloze)
@lru_cache(maxsize=None)
def ann_fact_value_counts(ann_id: str) -> dict:
    return dict(Counter(f["value_text"] for f in ann_facts(ann_id)))


def ann_unique_facts(ann_id: str, max_page: int = 999) -> list:
    """Facts whose value_text is unique within the announcement and on page <= max_page."""
    vc = ann_fact_value_counts(ann_id)
    return [f for f in ann_facts(ann_id)
            if f["page_no"] <= max_page and vc.get(f["value_text"]) == 1]


# ----------------------------------------------------------------- grounding helpers
def text_has(haystack: str, term: str) -> bool:
    return V2.norm(term) in V2.norm(haystack)


def grounded_in_pages(term: str, page_ids: list) -> bool:
    nt = V2.norm(term)
    if not nt:
        return False
    return any(nt in V2.norm(page_text(pid)) for pid in page_ids)


def statute_text(sid: str) -> str:
    return V2.full_text(sid)


# ----------------------------------------------------------------- bundles (v0.4)
BUNDLES_V04 = PROC / "bundles-v04"


@lru_cache(maxsize=None)
def bundles_v04() -> list:
    mf = BUNDLES_V04 / "manifest.jsonl"
    return _jl(mf) if mf.exists() else []


@lru_cache(maxsize=None)
def page_bundle_positions_v04() -> dict:
    """page_id -> list of {bundle_id, context_tier, position_band} across all v0.4 bundles."""
    out: dict = {}
    for b in bundles_v04():
        for comp in b["components"]:
            if comp["type"] == "lh_page":
                out.setdefault(comp["id"], []).append(
                    {"bundle_id": b["bundle_id"], "context_tier": b["context_tier"],
                     "position_band": comp["position_band"]})
    return out


@lru_cache(maxsize=None)
def bundle_ids_v04() -> frozenset:
    return frozenset(b["bundle_id"] for b in bundles_v04())
