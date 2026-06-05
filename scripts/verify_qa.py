#!/usr/bin/env python3
"""Independent deterministic verification of public QA files (v0.2 + v0.3).

v0.2: gold_terms/gold_numbers grounded verbatim in cited statute/metadata text.
v0.3 (additional):
  - source_ids / evidence source_ids resolve against manifest + excluded
  - page_ids exist in the LH announcement page set
  - row_ids exist in the cited HUG/MOLIT row set AND are within the predicate's matching set
  - gold_predicate recomputes to the gold answer (same engine the generator used)
  - text answers grounded in cited internal source (LH pages / statute text)
  - answerability items carry an 'unanswerable' marker
  - family sanity: cross_document_legal cites LH + a statute; cross_source cites >=2 sources

Writes workspace_local/audit/verification_report*.json. Exit !=0 on any hard failure (CI gate).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import qa_common as V2
import qa_v03_common as V3
import qa_v04_common as V4
import qa_v05_common as V5
import providers_v05 as P5

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AUDIT = ROOT / "workspace_local" / "audit"

UNANS_MARKERS = ["확정할 수 없", "답할 수 없", "알 수 없", "unanswerable", "근거가 없", "근거 부재", "없음", "제공된 자료"]
REQUIRED = ["qa_id", "split", "task_type", "question", "answer", "answer_type",
            "source_ids", "required_capabilities", "evidence", "evaluation", "copyright_note"]
TIERS = {"32k", "64k", "128k", "256k", "512k"}
POSITIONS = {"early", "middle", "late", "multi"}


@lru_cache(maxsize=None)
def resolvable_ids() -> frozenset:
    ids = set()
    for fn in ("source_manifest.jsonl", "excluded_sources.jsonl"):
        for l in (DATA / fn).open(encoding="utf-8"):
            if l.strip():
                ids.add(json.loads(l)["source_id"])
    return frozenset(ids)


@lru_cache(maxsize=None)
def lh_text() -> str:
    return V2.norm("\n".join(p["text"] for p in V3.lh_pages()))


def source_text(sid: str) -> str:
    if sid == V3.LH:
        return lh_text()
    if sid.startswith("law-") or sid in ("kogl-license-guide", "public-data-portal-use-policy"):
        return V2.norm(V2.full_text(sid))
    return ""  # row sources: grounded via predicate/row_ids, not free text


# ----------------------------------------------------------------- v0.2 check
def check_v02(item: dict, ids: frozenset) -> dict:
    errs = []
    for f in REQUIRED:
        if f not in item:
            errs.append(f"missing {f}")
    for s in item.get("source_ids", []):
        if s not in ids:
            errs.append(f"unknown source_id {s}")
    for e in item.get("evidence", []):
        if e.get("source_id") not in ids:
            errs.append(f"unknown evidence source_id {e.get('source_id')}")
    ev = item.get("evaluation", {})
    if ev.get("metric") == "boolean_and_reason":
        if not any(m in item.get("answer", "") for m in UNANS_MARKERS):
            errs.append("answerability lacks unanswerable marker")
    else:
        cited = [e["source_id"] for e in item.get("evidence", [])] or item.get("source_ids", [])
        corpora = {s: V2.norm(V2.full_text(s)) for s in set(cited)}
        for t in ev.get("gold_terms", []):
            if V2.norm(t) and not any(V2.norm(t) in c for c in corpora.values()):
                errs.append(f"gold_term not grounded: {t!r}")
        for n in ev.get("gold_numbers", []):
            if n and not any(n in c for c in corpora.values()):
                errs.append(f"gold_number not grounded: {n!r}")
    return {"qa_id": item.get("qa_id"), "task_type": item.get("task_type"),
            "status": "FAIL" if errs else "verified", "errors": errs}


# ----------------------------------------------------------------- v0.3 check
def check_v03(item: dict, ids: frozenset) -> dict:
    errs = []
    qid = item.get("qa_id")
    for f in REQUIRED:
        if f not in item:
            errs.append(f"missing {f}")
    for s in item.get("source_ids", []):
        if s not in ids:
            errs.append(f"unknown source_id {s}")
    for e in item.get("evidence", []):
        if e.get("source_id") not in ids:
            errs.append(f"unknown evidence source_id {e.get('source_id')}")
        if not e.get("locator"):
            errs.append("evidence missing locator")

    tier = item.get("context_tier")
    if tier is not None and tier not in TIERS:
        errs.append(f"bad context_tier {tier}")
    pos = item.get("evidence_position")
    if pos is not None and pos not in POSITIONS:
        errs.append(f"bad evidence_position {pos}")

    # page_ids exist
    for pid in item.get("page_ids", []):
        if pid not in V3.page_ids():
            errs.append(f"page_id not found: {pid}")

    # gold_predicate recompute (table/aggregation)
    pred = item.get("gold_predicate")
    matched_ids = None
    if pred:
        try:
            val, matched_ids = V3.recompute(pred)
        except Exception as exc:  # noqa: BLE001
            errs.append(f"predicate error: {exc!r}")
            val = None
        if val is None:
            errs.append("predicate produced no value")
        else:
            ev = item.get("evaluation", {})
            sval = str(val)
            if pred["op"] in ("argmax", "argmin"):
                if sval not in (ev.get("gold_terms", []) + [item.get("answer", "")]) \
                        and sval not in item.get("answer", ""):
                    errs.append(f"argmax/min value {sval!r} not in answer/gold_terms")
            else:
                golds = [str(g) for g in ev.get("gold_numbers", [])]
                if sval not in golds and sval not in item.get("answer", "").replace(",", ""):
                    errs.append(f"predicate value {sval} != gold_numbers {golds}")

    # row_ids exist + (if predicate) are within the matching set
    for rid in item.get("row_ids", []):
        src = V3.HUG if rid.startswith("HUG-") else (V3.MOLIT if rid.startswith("MOLIT-") else None)
        if src is None or rid not in V3.rows_by_id(src):
            errs.append(f"row_id not found: {rid}")
        elif matched_ids is not None and rid not in matched_ids:
            errs.append(f"row_id {rid} not in predicate match set")

    # grounding for text answers (no predicate) / answerability
    ev = item.get("evaluation", {})
    metric = ev.get("metric", "")
    if metric == "boolean_and_reason":
        if not any(m in item.get("answer", "") for m in UNANS_MARKERS):
            errs.append("answerability lacks unanswerable marker")
    elif not pred:
        cited = [e["source_id"] for e in item.get("evidence", [])] or item.get("source_ids", [])
        corpora = [source_text(s) for s in set(cited)]
        corpora = [c for c in corpora if c]
        ans = item.get("answer", "")
        for t in ev.get("gold_terms", []):
            nt = V2.norm(t)
            if nt and not (any(nt in c for c in corpora) or nt in V2.norm(ans)):
                errs.append(f"gold_term not grounded: {t!r}")
        for n in ev.get("gold_numbers", []):
            if n and not (any(n in c for c in corpora) or n in ans.replace(",", "")):
                errs.append(f"gold_number not grounded: {n!r}")

    # family sanity
    tt = item.get("task_type")
    srcs = set(item.get("source_ids", []))
    if tt == "cross_document_legal_reasoning":
        if not (any(s.startswith("law-") for s in srcs) and V3.LH in srcs):
            errs.append("cross_document_legal must cite LH announcement + a statute")
    if tt == "cross_source_aggregation" and len(srcs) < 2:
        errs.append("cross_source_aggregation must cite >=2 sources")

    return {"qa_id": qid, "task_type": tt, "status": "FAIL" if errs else "verified", "errors": errs}


# ----------------------------------------------------------------- v0.4 check
@lru_cache(maxsize=None)
def all_bundle_ids() -> frozenset:
    return V4.bundle_ids_v04() | frozenset(b["bundle_id"] for b in V3.bundles())


def _v04_corpus(item: dict) -> list:
    corp = [V4.page_text(pid) for pid in item.get("page_ids", [])]
    for s in {e["source_id"] for e in item.get("evidence", [])} | set(item.get("source_ids", [])):
        if s in V4.STATUTES:
            corp.append(V2.full_text(s))
    return [c for c in corp if c]


def check_v04(item: dict, ids: frozenset) -> dict:
    errs = []
    qid = item.get("qa_id")
    for f in REQUIRED:
        if f not in item:
            errs.append(f"missing {f}")
    for s in item.get("source_ids", []):
        if s not in ids:
            errs.append(f"unknown source_id {s}")
    for e in item.get("evidence", []):
        if e.get("source_id") not in ids:
            errs.append(f"unknown evidence source_id {e.get('source_id')}")
        if not e.get("locator"):
            errs.append("evidence missing locator")

    tier = item.get("context_tier")
    if tier is not None and tier not in TIERS:
        errs.append(f"bad context_tier {tier}")
    pos = item.get("evidence_position")
    if pos is not None and pos not in POSITIONS:
        errs.append(f"bad evidence_position {pos}")
    bid = item.get("bundle_id")
    if bid and bid not in all_bundle_ids():
        errs.append(f"unknown bundle_id {bid}")
    # a bundle-bearing item must carry both tier and position
    if bid and (tier is None or pos is None):
        errs.append("bundle_id present without context_tier/evidence_position")

    for pid in item.get("page_ids", []):
        if pid not in V4.v04_page_ids():
            errs.append(f"page_id not found: {pid}")

    pred = item.get("gold_predicate")
    matched_ids = None
    if pred:
        try:
            val, matched_ids = V3.recompute(pred)
        except Exception as exc:  # noqa: BLE001
            errs.append(f"predicate error: {exc!r}")
            val = None
        if val is None:
            errs.append("predicate produced no value")
        else:
            ev = item.get("evaluation", {})
            sval = str(val)
            if pred["op"] in ("argmax", "argmin"):
                if sval not in (ev.get("gold_terms", []) + [item.get("answer", "")]) and sval not in item.get("answer", ""):
                    errs.append(f"argmax/min value {sval!r} not in answer/gold_terms")
            else:
                golds = [str(g) for g in ev.get("gold_numbers", [])]
                if sval not in golds and sval not in item.get("answer", "").replace(",", ""):
                    errs.append(f"predicate value {sval} != gold_numbers {golds}")

    for rid in item.get("row_ids", []):
        src = V3.HUG if rid.startswith("HUG-") else (V3.MOLIT if rid.startswith("MOLIT-") else None)
        if src is None or rid not in V3.rows_by_id(src):
            errs.append(f"row_id not found: {rid}")
        elif matched_ids is not None and rid not in matched_ids:
            errs.append(f"row_id {rid} not in predicate match set")

    ev = item.get("evaluation", {})
    metric = ev.get("metric", "")
    if metric == "boolean_and_reason":
        if not any(m in item.get("answer", "") for m in UNANS_MARKERS):
            errs.append("answerability lacks unanswerable marker")
    elif not pred:
        corp = _v04_corpus(item)
        ans = item.get("answer", "")
        for t in ev.get("gold_terms", []):
            nt = V2.norm(t)
            if nt and not (any(nt in V2.norm(c) for c in corp) or nt in V2.norm(ans)):
                errs.append(f"gold_term not grounded: {t!r}")
        for n in ev.get("gold_numbers", []):
            if n and not (any(n in c for c in corp) or n in ans.replace(",", "")):
                errs.append(f"gold_number not grounded: {n!r}")
    else:
        # predicate item that also cites an LH page (cross_source): the region hop term must be grounded
        if item.get("page_ids"):
            corp = _v04_corpus(item)
            ans = item.get("answer", "")
            for t in ev.get("gold_terms", []):
                nt = V2.norm(t)
                if nt and not nt.isdigit() and not (any(nt in V2.norm(c) for c in corp) or nt in V2.norm(ans)):
                    errs.append(f"cross-source region term not grounded in cited page: {t!r}")

    tt = item.get("task_type")
    srcs = set(item.get("source_ids", []))
    if tt == "cross_document_legal_reasoning":
        if not (any(s in V4.STATUTES for s in srcs) and V4.LH_V04 in srcs):
            errs.append("cross_document_legal must cite LH-v04 + a statute")
    if tt == "cross_source_aggregation" and len(srcs) < 2:
        errs.append("cross_source_aggregation must cite >=2 sources")
    if tt == "multi_document_comparison":
        anns = {m.group(1) for p in item.get("page_ids", [])
                if (m := re.match(r"(lh-[a-z0-9-]+)-p\d{3}$", p))}
        if len(anns) < 2:
            errs.append("multi_document_comparison must cite >=2 announcements")

    return {"qa_id": qid, "task_type": tt, "status": "FAIL" if errs else "verified", "errors": errs}


V05_SPLITS = {"dev", "test_public", "test_hidden", "ood_provider", "ood_region", "ood_year"}


def _p5_corpus(item: dict) -> list:
    """Grounding corpus across ALL providers: cited page text (provider-agnostic) + cited statute text."""
    corp = [P5.page_text(pid) for pid in item.get("page_ids", [])]
    for s in {e["source_id"] for e in item.get("evidence", [])} | set(item.get("source_ids", [])):
        if s in V4.STATUTES:
            corp.append(V2.full_text(s))
    return [c for c in corp if c]


def check_v05(item: dict, ids: frozenset) -> dict:
    """Self-contained, provider-aware v0.5 check (LH-v04 + SH/GH/iH/JPDC)."""
    errs = []
    qid = item.get("qa_id")
    for f in REQUIRED:
        if f not in item:
            errs.append(f"missing {f}")
    for fld in ("provider", "region_sido", "housing_type", "split"):
        if not item.get(fld):
            errs.append(f"missing {fld}")
    if item.get("split") and item["split"] not in V05_SPLITS:
        errs.append(f"bad split {item.get('split')}")
    for s in item.get("source_ids", []):
        if s not in ids:
            errs.append(f"unknown source_id {s}")
    for e in item.get("evidence", []):
        if e.get("source_id") not in ids:
            errs.append(f"unknown evidence source_id {e.get('source_id')}")
        if not e.get("locator"):
            errs.append("evidence missing locator")
    tier = item.get("context_tier")
    if tier is not None and tier not in TIERS:
        errs.append(f"bad context_tier {tier}")
    pos = item.get("evidence_position")
    if pos is not None and pos not in POSITIONS:
        errs.append(f"bad evidence_position {pos}")
    bid = item.get("bundle_id")
    if bid and bid not in all_bundle_ids():
        errs.append(f"unknown bundle_id {bid}")
    # page / cell / table id existence (all providers)
    for pid in item.get("page_ids", []):
        if pid not in P5.all_page_ids():
            errs.append(f"page_id not found: {pid}")
    for cid in item.get("cell_ids", []):
        if cid not in P5.all_cell_ids():
            errs.append(f"cell_id not found: {cid}")
    for tid in item.get("table_ids", []):
        if tid not in P5.all_table_ids():
            errs.append(f"table_id not found: {tid}")

    # predicate recompute (MOLIT/HUG table items)
    pred = item.get("gold_predicate")
    matched_ids = None
    if pred:
        try:
            val, matched_ids = V3.recompute(pred)
        except Exception as exc:  # noqa: BLE001
            errs.append(f"predicate error: {exc!r}")
            val = None
        if val is None:
            errs.append("predicate produced no value")
        else:
            ev = item.get("evaluation", {})
            sval = str(val)
            if pred["op"] in ("argmax", "argmin"):
                if sval not in (ev.get("gold_terms", []) + [item.get("answer", "")]) and sval not in item.get("answer", ""):
                    errs.append(f"argmax/min value {sval!r} not in answer/gold_terms")
            else:
                golds = [str(g) for g in ev.get("gold_numbers", [])]
                if sval not in golds and sval not in item.get("answer", "").replace(",", ""):
                    errs.append(f"predicate value {sval} != gold_numbers {golds}")
    for rid in item.get("row_ids", []):
        src = V3.HUG if rid.startswith("HUG-") else (V3.MOLIT if rid.startswith("MOLIT-") else None)
        if src is None or rid not in V3.rows_by_id(src):
            errs.append(f"row_id not found: {rid}")
        elif matched_ids is not None and rid not in matched_ids:
            errs.append(f"row_id {rid} not in predicate match set")

    # grounding
    ev = item.get("evaluation", {})
    metric = ev.get("metric", "")
    if metric == "boolean_and_reason":
        if not any(m in item.get("answer", "") for m in UNANS_MARKERS):
            errs.append("answerability lacks unanswerable marker")
    elif not pred:
        corp = _p5_corpus(item)
        ans = item.get("answer", "")
        for t in ev.get("gold_terms", []):
            nt = V2.norm(t)
            if nt and not (any(nt in V2.norm(c) for c in corp) or nt in V2.norm(ans)):
                errs.append(f"gold_term not grounded: {t!r}")
        for n in ev.get("gold_numbers", []):
            if n and not (any(n in c for c in corp) or n in ans.replace(",", "")):
                errs.append(f"gold_number not grounded: {n!r}")
    elif item.get("page_ids"):
        corp = _p5_corpus(item)
        ans = item.get("answer", "")
        for t in ev.get("gold_terms", []):
            nt = V2.norm(t)
            if nt and not nt.isdigit() and not (any(nt in V2.norm(c) for c in corp) or nt in V2.norm(ans)):
                errs.append(f"cross-source region term not grounded in cited page: {t!r}")

    # family sanity
    tt = item.get("task_type")
    srcs = set(item.get("source_ids", []))
    anns = {m.group(1) for p in item.get("page_ids", []) if (m := re.match(r"(.+)-p\d{3}$", p))}
    if tt == "cross_document_legal_reasoning" and not (any(s in V4.STATUTES for s in srcs) and V4.LH_V04 in srcs):
        errs.append("cross_document_legal must cite LH-v04 + a statute")
    if tt == "cross_source_aggregation" and len(srcs) < 2:
        errs.append("cross_source_aggregation must cite >=2 sources")
    if tt == "multi_document_comparison" and len(anns) < 2:
        errs.append("multi_document_comparison must cite >=2 announcements")
    if tt == "provider_comparison" and len(srcs) < 2:
        errs.append("provider_comparison must cite >=2 provider sources")
    if tt == "region_comparison" and len(anns) < 2:
        errs.append("region_comparison must cite >=2 announcements")

    return {"qa_id": qid, "task_type": tt, "status": "FAIL" if errs else "verified", "errors": errs}


def check_split_leakage(path: Path) -> bool:
    """Dataset-level: no announcement may appear in more than one EVALUATION split."""
    if not path.exists():
        return True
    rows = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    eval_splits = {"test_public", "test_hidden", "ood_provider", "ood_region", "ood_year"}
    ann_splits: dict = {}
    for r in rows:
        for a in V5.item_announcements(r):
            ann_splits.setdefault(a, set()).add(r.get("split"))
    leaks = {a: sorted(s) for a, s in ann_splits.items() if len({x for x in s if x in eval_splits}) > 1}
    if leaks:
        print(f"  SPLIT LEAKAGE: {len(leaks)} announcements in >1 eval split")
        for a, s in list(leaks.items())[:10]:
            print(f"    {a}: {s}")
        return False
    print(f"  split-leakage check: OK ({len(ann_splits)} announcements, none in >1 eval split)")
    return True


def run_file(path: Path, checker, ids: frozenset, label: str) -> bool:
    if not path.exists():
        print(f"  ({path.name} absent — skipped)")
        return True
    rows = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    reports = [checker(r, ids) for r in rows]
    failed = [r for r in reports if r["status"] == "FAIL"]
    fams = Counter(r["task_type"] for r in rows)
    report = {"file": path.name, "total": len(rows), "verified": len(rows) - len(failed),
              "failed": len(failed), "by_task_family": dict(fams),
              "failures": failed}
    (AUDIT / f"verification_report_{label}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"== {path.name}: total={len(rows)} verified={report['verified']} failed={len(failed)} ==")
    for k, v in sorted(fams.items()):
        print(f"    {k}: {v}")
    for r in failed[:40]:
        print(f"    FAIL {r['qa_id']} [{r['task_type']}]: {'; '.join(r['errors'][:3])}")
    return not failed


def main() -> int:
    AUDIT.mkdir(parents=True, exist_ok=True)
    ids = resolvable_ids()
    ok2 = run_file(DATA / "qa_v0.2_candidates.jsonl", check_v02, ids, "v02")
    ok3 = run_file(DATA / "qa_v0.3_candidates.jsonl", check_v03, ids, "v03")
    ok4 = run_file(DATA / "qa_v0.4_candidates.jsonl", check_v04, ids, "v04")
    ok5 = run_file(DATA / "qa_v0.5_candidates.jsonl", check_v05, ids, "v05")
    ok5_leak = check_split_leakage(DATA / "qa_v0.5_candidates.jsonl")
    return 0 if (ok2 and ok3 and ok4 and ok5 and ok5_leak) else 1


if __name__ == "__main__":
    raise SystemExit(main())
