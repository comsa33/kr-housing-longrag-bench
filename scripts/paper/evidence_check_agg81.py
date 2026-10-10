#!/usr/bin/env python3
"""Evidence-completeness check for the 81 cross_source_aggregation items (test_public, 512k tier).

For every item: (1) recompute its gold predicate with the dataset repo's own engine
(scripts/qa_v03_common.recompute) and confirm the value matches the released answer; (2) confirm that
EVERY row the predicate matches is present, verbatim as rendered by scripts/build_bundles.py, in the
evidence-complete bundle text workspace_local/processed/bundles-v06/mix_multiprovider_512k.txt.
Read-only; no model calls.

The bundle text is NOT shipped (source licences); rebuild it first with
scripts/rebuild_v04_from_public_manifest.py and scripts/build_bundles.py. The 81 item ids are
read from results/item_sets/agg81.jsonl.

    python3 scripts/paper/evidence_check_agg81.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(Path(__file__).resolve().parents[2]),
                    help="dataset repo root (default: this checkout)")
    args = ap.parse_args()
    root = Path(args.dataset)
    sys.path.insert(0, str(root / "scripts"))
    import qa_v03_common as C  # noqa: E402

    ids = [json.loads(l)["qa_id"] for l in (root / "results/item_sets/agg81.jsonl").open() if l.strip()]
    tp = {}
    for l in (root / "data/qa_v0.6_test_public.jsonl").open(encoding="utf-8"):
        if l.strip():
            d = json.loads(l)
            tp[d["qa_id"]] = d
    bundle = (root / "workspace_local/processed/bundles-v06/mix_multiprovider_512k.txt").read_text(encoding="utf-8")
    lines = set(bundle.splitlines())

    hug = {r["_row_id"]: r for r in C.hug_rows()}
    molit = {r["_row_id"]: r for r in C.molit_rows()}

    def rendered(source: str, rid: str) -> str:
        if source == "hug-sale-history":
            r = hug[rid]
            return " | ".join([r.get("_query_area_name", ""), r.get("_query_year", ""), r.get("BSU_NM", ""),
                               str(r.get("TOT_HOCO", "")), str(r.get("GNRL_SILT_HOCO", ""))])
        r = molit[rid]
        return (f"{r['_row_id']} | {r['_lawd_name']} {r['umdNm']} | {r['aptNm']} | "
                f"{r['excluUseAr']}㎡ {r['dealAmount']}만원 | {r['_deal_ymd']}")

    n_ok = n_val = n_rows = 0
    fails = []
    for q in ids:
        item = tp[q]
        pred = item["gold_predicate"]
        val, rids = C.recompute(pred)
        gold_num = re.sub(r"[^0-9.]", "", str(item["answer"]))
        val_ok = gold_num != "" and abs(float(val) - float(gold_num)) < 1e-6
        missing = [rid for rid in rids if rendered(pred["source"], rid) not in lines]
        n_val += val_ok
        n_rows += not missing
        if val_ok and not missing:
            n_ok += 1
        else:
            fails.append((q, val, item["answer"], len(rids), len(missing)))
    print(f"items={len(ids)}  predicate==answer: {n_val}/{len(ids)}  all matched rows in bundle: {n_rows}/{len(ids)}  both: {n_ok}/{len(ids)}")
    print("matched rows per item: min/max =", min(len(C.recompute(tp[q]['gold_predicate'])[1]) for q in ids),
          max(len(C.recompute(tp[q]['gold_predicate'])[1]) for q in ids))
    for f in fails:
        print("FAIL", f)
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
