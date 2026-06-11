#!/usr/bin/env python3
"""Patch the full-context prompts for the 4 cross_source_aggregation items at the 512k tier.

These items ask an aggregate over HUG (주택도시보증공사) sale-history (e.g. "2023 경기도 분양 사업장
건수") whose gold is computed from a structured table that was NEVER embedded in the full-context
bundle — only the LH announcements were. So the model could not answer in the fc regime and was
scored wrong, artificially deflating the 512k fc number (see baseline_results_v09.md §8.2/§8.5).

This is a full-context regime by definition: every source the question needs must be in the bundle.
We therefore inject the HUG rows as a compact readable table (624 raw rows; 623 are valid — one empty
대구-2023 placeholder, immaterial: all four golds reproduce identically and no gold references it) into the
4 prompts, just before the question. The canonical bundle (build_bundles_v06.py) embeds the 623 valid rows.
Only the cross_source items are touched; the other 512k items are left byte-identical so their already-
run predictions stay valid. Output: a 4-item prompt file to re-run on the models that can ingest 512k
(gpt-4.1-mini, gpt-5.5; the 272k-window gpt-5.4 family still ✗ctx and need no re-run).

    python3 scripts/fix_fc_hug_bundle_v09.py
    -> workspace_local/audit/baselines/fullcontext_v09_prompts.hugfix.jsonl  (4 items)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "workspace_local" / "audit" / "baselines"
ROWS = ROOT / "workspace_local" / "processed" / "hug-sale-history" / "rows_v0.3.jsonl"
FC_PROMPTS = B / "fullcontext_v09_prompts.jsonl"
CROSS_SOURCE_IDS = ["krhlrb_v05_1801", "krhlrb_v05_0455", "krhlrb_v05_0434", "krhlrb_v05_0436"]
QMARK = "\n\n[질문]\n"  # injection point: HUG table goes immediately before the question block


def build_hug_table() -> str:
    """Compact, count/avg-friendly rendering of the HUG sale-history rows (624 raw from rows_v0.3.jsonl)."""
    rows = [json.loads(l) for l in ROWS.open(encoding="utf-8") if l.strip()]
    rows.sort(key=lambda r: (r["_query_area_name"], r["_query_year"], r["_row_id"]))
    out = [
        "===== [참고자료] HUG 분양이력 자료 (주택도시보증공사, 분양보증 발급 사업장) =====",
        f"총 {len(rows)}개 사업장. 각 행 = 분양 사업장 1건. "
        "‘분양 사업장 건수’는 해당 지역·연도 행의 개수이고, ‘평균 총세대수(TOT_HOCO)’는 그 행들의 "
        "총세대수 평균입니다.",
        "지역 | 연도 | 사업장명 | 총세대수(TOT_HOCO) | 일반분양세대(GNRL_SILT_HOCO)",
    ]
    for r in rows:
        out.append(" | ".join([
            r.get("_query_area_name", ""), r.get("_query_year", ""),
            r.get("BSU_NM", ""), str(r.get("TOT_HOCO", "")), str(r.get("GNRL_SILT_HOCO", "")),
        ]))
    out.append("===== [참고자료 끝] =====")
    return "\n".join(out)


def main() -> int:
    hug = build_hug_table()
    want = set(CROSS_SOURCE_IDS)
    patched = []
    seen = set()
    for line in FC_PROMPTS.open(encoding="utf-8"):
        rec = json.loads(line)
        if rec.get("qa_id") not in want:
            continue
        seen.add(rec["qa_id"])
        p = rec["prompt"]
        if QMARK not in p:
            raise SystemExit(f"[fail] {rec['qa_id']}: question marker not found, cannot inject safely")
        head, q = p.split(QMARK, 1)
        rec = dict(rec)
        rec["prompt"] = head + "\n\n" + hug + QMARK + q
        rec["_hugfix"] = True
        patched.append(rec)

    missing = want - seen
    if missing:
        raise SystemExit(f"[fail] missing fc prompts for: {sorted(missing)}")

    out = B / "fullcontext_v09_prompts.hugfix.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for rec in patched:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[ok] {out} ({len(patched)} items)")
    print(f"  HUG table: {len(hug):,} chars (~{len(hug)/2.45:,.0f} tokens)")
    for rec in patched:
        print(f"  {rec['qa_id']}: prompt {len(rec['prompt']):,} chars (~{len(rec['prompt'])/2.45:,.0f} tok)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
