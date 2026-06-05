#!/usr/bin/env python3
"""Assemble the public v0.2 QA candidate file from deterministic + agent-authored items.

Inputs (internal staging):
  - workspace_local/audit/qa_det.jsonl        (deterministic, already verified-by-construction)
  - workspace_local/audit/qa_agent_raw.json   (agent items with reviewer verdicts)
Gate for agent items: reviewer_supported AND reviewer_unambiguous AND grounding (gold_terms/gold_numbers
verbatim in a cited source; answerability requires an 'unanswerable' marker). Failing items are dropped
and logged. Output (public): data/qa_v0.2_candidates.jsonl  (schema-compliant fields only).
"""
from __future__ import annotations

import json
from pathlib import Path

from qa_common import ROOT, norm, full_text

AUDIT = ROOT / "workspace_local" / "audit"
DET = AUDIT / "qa_det.jsonl"
AGENT = AUDIT / "qa_agent_raw.json"
OUT = ROOT / "data" / "qa_v0.2_candidates.jsonl"
PROV = AUDIT / "qa_v0.2_provenance.jsonl"

PUBLIC_FIELDS = ["qa_id", "split", "task_type", "question", "answer", "answer_type",
                 "source_ids", "required_capabilities", "evidence", "evaluation", "copyright_note"]
UNANS_MARKERS = ["확정할 수 없", "답할 수 없", "알 수 없", "unanswerable", "근거가 없", "근거 부재", "없음"]


def grounded(item: dict) -> tuple[bool, str]:
    ev = item.get("evaluation", {})
    metric = ev.get("metric", "")
    srcs = item.get("source_ids", [])
    if metric == "boolean_and_reason":
        ans = item.get("answer", "")
        if any(m in ans for m in UNANS_MARKERS):
            return True, "answerability marker present"
        return False, "no unanswerable marker in answer"
    # term/number grounding: each gold token must appear verbatim in >=1 cited source
    cited = [e["source_id"] for e in item.get("evidence", [])] or srcs
    corpora = {s: norm(full_text(s)) for s in set(cited)}
    for term in ev.get("gold_terms", []):
        nt = norm(term)
        if nt and not any(nt in c for c in corpora.values()):
            return False, f"gold_term not found in cited source: {term!r}"
    for num in ev.get("gold_numbers", []):
        if num and not any(num in c for c in corpora.values()):
            return False, f"gold_number not found in cited source: {num!r}"
    return True, "all gold tokens verbatim in cited source(s)"


def public_only(item: dict, qa_id: str, split: str = "dev") -> dict:
    out = {"qa_id": qa_id, "split": split}
    for f in PUBLIC_FIELDS:
        if f in ("qa_id", "split"):
            continue
        if f in item:
            out[f] = item[f]
    # normalize evidence to {source_id, locator} only
    out["evidence"] = [{"source_id": e["source_id"], "locator": e["locator"]}
                       for e in item.get("evidence", [])]
    # normalize evaluation to {metric, gold_terms?, gold_numbers?}
    ev = item.get("evaluation", {})
    nev = {"metric": ev.get("metric", "contains_all")}
    if ev.get("gold_terms"):
        nev["gold_terms"] = ev["gold_terms"]
    if ev.get("gold_numbers"):
        nev["gold_numbers"] = ev["gold_numbers"]
    out["evaluation"] = nev
    return out


def main() -> int:
    final, prov = [], []
    seq = 0

    # deterministic items (trusted; verified-by-construction)
    det = [json.loads(l) for l in DET.open(encoding="utf-8") if l.strip()] if DET.exists() else []
    for it in det:
        seq += 1
        qid = f"krhlrb_v02_{seq:03d}"
        final.append(public_only(it, qid))
        prov.append({"qa_id": qid, "origin": "deterministic", "orig_id": it.get("qa_id"),
                     "task_type": it["task_type"], "verification": "verified_by_script"})

    # agent items (gated)
    dropped = []
    if AGENT.exists():
        agent_rows = json.loads(AGENT.read_text(encoding="utf-8"))
        for row in agent_rows:
            it = row["item"]
            it.setdefault("task_type", row.get("task_type"))
            sup = row.get("reviewer_supported", False)
            unamb = row.get("reviewer_unambiguous", False)
            ok_g, why = grounded(it)
            if sup and unamb and ok_g:
                seq += 1
                qid = f"krhlrb_v02_{seq:03d}"
                final.append(public_only(it, qid))
                prov.append({"qa_id": qid, "origin": f"agent:{row.get('family')}",
                             "task_type": it["task_type"],
                             "verification": "reviewer_pass+grounded",
                             "reviewer_reason": row.get("reviewer_reason", "")})
            else:
                dropped.append({"family": row.get("family"), "task_type": it.get("task_type"),
                                "reviewer_supported": sup, "reviewer_unambiguous": unamb,
                                "grounding": why, "question": it.get("question", "")[:80]})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for it in final:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    with PROV.open("w", encoding="utf-8") as f:
        for p in prov:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    (AUDIT / "qa_dropped.json").write_text(json.dumps(dropped, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    fam = Counter(it["task_type"] for it in final)
    print("=== ASSEMBLE SUMMARY ===")
    print(f"  deterministic: {len(det)}   agent kept: {len(final)-len(det)}   agent dropped: {len(dropped)}")
    print(f"  TOTAL final QA: {len(final)}")
    for k, v in sorted(fam.items()):
        print(f"    {k}: {v}")
    print(f"  -> {OUT}")
    if dropped:
        print(f"  dropped detail -> {AUDIT/'qa_dropped.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
