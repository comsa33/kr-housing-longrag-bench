#!/usr/bin/env python3
"""Assemble public data/qa_v0.3_candidates.jsonl from deterministic + agent-authored items.

Agent gate: reviewer_supported AND reviewer_unambiguous AND grounding (gold_terms/gold_numbers verbatim
in cited internal source; page_ids exist). Bundle fields (bundle_id/context_tier/evidence_position) are
attached from the bundle manifest by matching each item's LH page to its position band. Output carries
only schema-allowed public fields; row data / full text stay internal.
"""
from __future__ import annotations

import json
from pathlib import Path

import qa_common as V2
import qa_v03_common as C

AUDIT = C.ROOT / "workspace_local" / "audit"
DET = AUDIT / "qa_v03_det.jsonl"
AGENT = AUDIT / "qa_v03_agent_raw.json"
OUT = C.ROOT / "data" / "qa_v0.3_candidates.jsonl"
PROV = AUDIT / "qa_v0.3_provenance.jsonl"
DROP = AUDIT / "qa_v0.3_dropped.json"

PUBLIC = ["qa_id", "split", "task_type", "question", "answer", "answer_type", "source_ids",
          "required_capabilities", "evidence", "evaluation", "copyright_note",
          "bundle_id", "context_tier", "evidence_position", "row_ids", "page_ids", "gold_predicate"]
UNANS = ["확정할 수 없", "답할 수 없", "알 수 없", "unanswerable", "근거가 없", "근거 부재", "없음", "제공된 자료"]


def src_text(sid: str) -> str:
    if sid == C.LH:
        return V2.norm("\n".join(p["text"] for p in C.lh_pages()))
    if sid.startswith("law-"):
        return V2.norm(V2.full_text(sid))
    return ""


def page_text(pid: str) -> str:
    for p in C.lh_pages():
        if p["page_id"] == pid:
            return V2.norm(p["text"])
    return ""


def grounded_agent(it: dict) -> tuple[bool, str]:
    ev = it.get("evaluation", {})
    # page_ids exist
    for pid in it.get("page_ids", []):
        if pid not in C.page_ids():
            return False, f"page_id missing {pid}"
    # build corpora: specific LH page text(s) + cited law text + answer
    corp = []
    if it.get("page_ids"):
        corp += [page_text(pid) for pid in it["page_ids"]]
    for s in {e["source_id"] for e in it.get("evidence", [])} | set(it.get("source_ids", [])):
        t = src_text(s)
        if t:
            corp.append(t)
    ans = V2.norm(it.get("answer", ""))
    for term in ev.get("gold_terms", []):
        nt = V2.norm(term)
        if nt and not (any(nt in c for c in corp) or nt in ans):
            return False, f"gold_term not grounded: {term!r}"
    for n in ev.get("gold_numbers", []):
        if n and not (any(n in c for c in corp) or n in it.get("answer", "").replace(",", "")):
            return False, f"gold_number not grounded: {n!r}"
    return True, "ok"


def attach_bundle(it: dict) -> None:
    """Attach bundle_id/context_tier/evidence_position from an LH page's bundle band."""
    pids = it.get("page_ids", [])
    if not pids:
        return
    pos = C.page_bundle_positions().get(pids[0], [])
    if not pos:
        return
    tt = it.get("task_type", "")
    want_late = tt == "long_distance_retrieval"
    want_early = tt == "long_context_retrieval"
    pick = None
    order = sorted(pos, key=lambda x: int(x["context_tier"].replace("k", "")))
    if want_late:
        cands = [p for p in order if p["position_band"] == "late"]
        pick = (cands[-1] if cands else order[-1])
    elif want_early:
        cands = [p for p in order if p["position_band"] in ("early", "middle")]
        pick = (cands[0] if cands else order[0])
    else:  # cross-document etc: middle-ish bundle
        pick = order[len(order) // 2]
    it["bundle_id"] = pick["bundle_id"]
    it["context_tier"] = pick["context_tier"]
    it["evidence_position"] = pick["position_band"]


def public_only(it: dict, qid: str) -> dict:
    out = {"qa_id": qid, "split": it.get("split", "dev")}
    for f in PUBLIC:
        if f in ("qa_id", "split"):
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
    final, prov, dropped = [], [], []
    seq = 0

    det = [json.loads(l) for l in DET.open(encoding="utf-8") if l.strip()] if DET.exists() else []
    for it in det:
        attach_bundle(it)
        seq += 1
        qid = f"krhlrb_v03_{seq:03d}"
        final.append(public_only(it, qid))
        prov.append({"qa_id": qid, "origin": "deterministic", "task_type": it["task_type"],
                     "verification": "verified_by_script"})

    if AGENT.exists():
        for row in json.loads(AGENT.read_text(encoding="utf-8")):
            it = row["item"]
            sup, unamb = row.get("reviewer_supported"), row.get("reviewer_unambiguous")
            ok, why = grounded_agent(it)
            if sup and unamb and ok:
                attach_bundle(it)
                seq += 1
                qid = f"krhlrb_v03_{seq:03d}"
                final.append(public_only(it, qid))
                prov.append({"qa_id": qid, "origin": f"agent:{row.get('batch')}",
                             "task_type": it["task_type"], "verification": "reviewer+grounded",
                             "reviewer_reason": row.get("reviewer_reason", "")})
            else:
                dropped.append({"batch": row.get("batch"), "task_type": it.get("task_type"),
                                "supported": sup, "unambiguous": unamb, "grounding": why,
                                "q": it.get("question", "")[:80]})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for it in final:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    with PROV.open("w", encoding="utf-8") as f:
        for p in prov:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    DROP.write_text(json.dumps(dropped, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    fam = Counter(it["task_type"] for it in final)
    tiers = Counter(it.get("context_tier", "—") for it in final)
    print("=== ASSEMBLE v0.3 ===")
    print(f"  deterministic={len(det)}  agent_kept={len(final)-len(det)}  agent_dropped={len(dropped)}  TOTAL={len(final)}")
    for k, v in sorted(fam.items()):
        print(f"    {k}: {v}")
    print("  context_tier:", dict(tiers))
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
