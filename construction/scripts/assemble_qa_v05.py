#!/usr/bin/env python3
"""Assemble data/qa_v0.5_candidates.jsonl = carried v0.4 QA (enriched with provider/region/type/split)
+ new v0.5 deterministic cell/eligibility/schedule/correction QA.

This staged v0.5-dev batch reuses the v0.4 corpus (10 LH announcements) — no new providers yet — so it
reuses the v0.4 bundles and adds:
  - provider / region_sido / region_sigungu / housing_type metadata on every item
  - announcement-level `split` (dev / test_public / test_hidden) with no same-announcement split leakage
  - table cell-grounded families (table_numeric over real cells, eligibility, schedule, correction)

Bundle fields are kept from v0.4 for carried items; new cell items attach to any v0.4 bundle that
contains their cited page (evidence_position = that page's band). Output carries only schema fields.
"""
from __future__ import annotations

import json
from collections import Counter

import qa_v03_common as C
import qa_v04_common as Q
import qa_v05_common as F

V04 = C.ROOT / "data" / "qa_v0.4_candidates.jsonl"
DET05 = C.ROOT / "workspace_local" / "audit" / "qa_v05_det.jsonl"
PROV05 = C.ROOT / "workspace_local" / "audit" / "qa_providers_v05_det.jsonl"
OUT = C.ROOT / "data" / "qa_v0.5_candidates.jsonl"
PROV = C.ROOT / "workspace_local" / "audit" / "qa_v0.5_provenance.jsonl"

PUBLIC = ["qa_id", "split", "split_tags", "task_type", "question", "answer", "answer_type",
          "source_ids", "required_capabilities", "evidence", "evaluation", "copyright_note",
          "provider", "region_sido", "region_sigungu", "housing_type", "program_type",
          "bundle_id", "context_tier", "evidence_position", "row_ids", "page_ids",
          "announcement_ids", "table_ids", "cell_ids", "gold_predicate"]


def enrich_metadata(it: dict) -> None:
    anns = F.item_announcements(it)
    if anns:
        sidos = {Q.ann_sido(a) for a in anns if Q.ann_sido(a)}
        sggs = {Q.ann_sigungu(a) for a in anns if Q.ann_sigungu(a)}
        htypes = {F.ann_housing_type(a) for a in anns}
        it["provider"] = F.PROVIDER_LH
        it["region_sido"] = next(iter(sidos)) if len(sidos) == 1 else "복수"
        it["region_sigungu"] = next(iter(sggs)) if len(sggs) == 1 else "복수"
        it["housing_type"] = next(iter(htypes)) if len(htypes) == 1 else "복수"
        it.setdefault("program_type", it["housing_type"])
    else:
        pred = it.get("gold_predicate", {}) or {}
        filt = pred.get("filter", {})
        reg = filt.get("_lawd_name") or filt.get("_query_area_name") or ""
        it["provider"] = "공공데이터(MOLIT/HUG)"
        it["region_sido"] = reg.split()[0] if reg else "전국"
        it["region_sigungu"] = reg if (reg and " " in reg) else ""
        it["housing_type"] = "실거래/분양이력"
        it.setdefault("program_type", "tabular_public_data")
    tags = []
    for a in anns:
        tags += F.ann_split_tags(a)
    if tags:
        it["split_tags"] = sorted(set(tags))
    sp = F.item_split(it)
    it["split"] = sp
    return sp is not None  # False -> drop (multi-doc item spanning split boundaries)


def attach_bundle_for_cell(it: dict) -> None:
    pids = it.get("page_ids", [])
    if not pids:
        return
    pos = Q.page_bundle_positions_v04().get(pids[0], [])
    if not pos:
        return
    pick = sorted(pos, key=lambda x: int(x["context_tier"].replace("k", "")))[len(pos) // 2]
    it["bundle_id"], it["context_tier"], it["evidence_position"] = pick["bundle_id"], pick["context_tier"], pick["position_band"]


def public_only(it: dict, qid: str) -> dict:
    out = {"qa_id": qid}
    for f in PUBLIC:
        if f == "qa_id":
            continue
        if f in it and it[f] not in (None, [], {}):
            out[f] = it[f]
    out["evidence"] = [{"source_id": e["source_id"], "locator": e["locator"]} for e in it.get("evidence", [])]
    ev = it.get("evaluation", {})
    nev = {"metric": ev.get("metric", "contains_all")}
    if ev.get("gold_terms"):
        nev["gold_terms"] = ev["gold_terms"]
    if ev.get("gold_numbers"):
        nev["gold_numbers"] = ev["gold_numbers"]
    out["evaluation"] = nev
    return out


def main() -> int:
    final, prov = [], []
    seen_q = set()
    seq = 0

    carried = [json.loads(l) for l in V04.open(encoding="utf-8") if l.strip()]
    n_dropped_split = 0
    for it in carried:
        if not enrich_metadata(it):
            n_dropped_split += 1
            continue
        if it["question"] in seen_q:
            continue
        seen_q.add(it["question"])
        seq += 1
        qid = f"krhlrb_v05_{seq:04d}"
        final.append(public_only(it, qid))
        prov.append({"qa_id": qid, "origin": "carried_v0.4", "task_type": it["task_type"], "split": it["split"]})

    new = [json.loads(l) for l in DET05.open(encoding="utf-8") if l.strip()] if DET05.exists() else []
    for it in new:
        if not enrich_metadata(it):
            n_dropped_split += 1
            continue
        attach_bundle_for_cell(it)
        if it["question"] in seen_q:
            continue
        seen_q.add(it["question"])
        seq += 1
        qid = f"krhlrb_v05_{seq:04d}"
        final.append(public_only(it, qid))
        prov.append({"qa_id": qid, "origin": "deterministic_v0.5_cells", "task_type": it["task_type"], "split": it["split"]})

    # new-provider QA (SH/GH/iH/JPDC) — already carry provider/region/type/split + page/cell ids
    prov_items = [json.loads(l) for l in PROV05.open(encoding="utf-8") if l.strip()] if PROV05.exists() else []
    n_prov = 0
    for it in prov_items:
        if it.get("question") in seen_q:
            continue
        seen_q.add(it["question"])
        seq += 1
        qid = f"krhlrb_v05_{seq:04d}"
        final.append(public_only(it, qid))
        prov.append({"qa_id": qid, "origin": "deterministic_v0.5_providers", "task_type": it["task_type"], "split": it["split"]})
        n_prov += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for it in final:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    with PROV.open("w", encoding="utf-8") as f:
        for p in prov:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    fam = Counter(it["task_type"] for it in final)
    sp = Counter(it["split"] for it in final)
    prv = Counter(it["provider"] for it in final)
    print(f"=== ASSEMBLE v0.5: TOTAL={len(final)} (dropped {n_dropped_split} split-spanning multi-doc) ===")
    for k, v in sorted(fam.items()):
        print(f"   {k:32s} {v}")
    print("  split:", dict(sp))
    print("  provider:", dict(prv))
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
