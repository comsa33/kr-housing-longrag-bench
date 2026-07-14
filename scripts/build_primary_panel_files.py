#!/usr/bin/env python3
"""Materialize the PRIMARY judge (gpt-4.1-mini) in the same panel-verdict format as the
external judges, so scripts/kappa_panel.py reads all five judges uniformly from files
(no hardcoded numbers) and the whole judge appendix reproduces from shipped verdicts.

Two outputs, both in the panel_<label>_* convention kappa_panel.py expects:

  panel_gpt-4.1-mini_human80.judged.jsonl
      The primary judge's verdicts on the n=80 human-validation sample, taken from the
      FROZEN validation snapshot `judge_validation.key.jsonl` (NOT the current canonical
      judged files --- those were re-judged after the bundle/preamble fixes and no longer
      match the point-in-time 96.2% / kappa 0.924 the paper reports). Row id = the same
      unique `{qa_id}__{model}__{regime}` key as panel_items_human80.jsonl, because two
      qa_ids recur with different model predictions.

  panel_gpt-4.1-mini_agg81_<model>.judged.jsonl   (model in gpt-5.5/glm-5.2/minimax-m3/gpt-4.1-mini)
      The primary judge's verdicts on the 81 cross-source-aggregation items, reconstructed
      from the evidence-complete 512k run = the `*_512kexp` (63 items) + `*_fixed512k`
      / `*_tp_fixed` (18 items) judged files, i.e. exactly the set behind tab:agg.

Usage:  python3 scripts/build_primary_panel_files.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "workspace_local" / "audit" / "baselines"


def judged(tag: str) -> dict[str, int]:
    for base in (B, B / "run_open"):
        f = base / f"{tag}.judged.jsonl"
        if f.exists():
            return {json.loads(l)["qa_id"]: (1 if json.loads(l).get("judge_correct") else 0)
                    for l in f.open(encoding="utf-8")}
    return {}


def main() -> int:
    # 1. human80 from the frozen validation snapshot (reproduces 96.2% / kappa 0.924).
    key = {(d["qa_id"], d["model"], d["regime"]): (str(d["judge"]) == "True")
           for d in (json.loads(l) for l in (B / "judge_validation.key.jsonl").open(encoding="utf-8"))}
    rows = [r for r in csv.DictReader((B / "judge_validation.csv").open(encoding="utf-8"))
            if r["human_correct(Y/N)"].strip() in ("Y", "N")]
    with (B / "panel_gpt-4.1-mini_human80.judged.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            rid = f"{r['qa_id']}__{r['model']}__{r['regime']}"
            v = key.get((r["qa_id"], r["model"], r["regime"]))
            f.write(json.dumps({"qa_id": rid, "judge_correct": bool(v),
                                "raw": "YES" if v else "NO"}, ensure_ascii=False) + "\n")

    # 2. agg81 per model from the evidence-complete 512k run (512kexp + fixed).
    gi = {}
    for sp in ("dev", "test_public"):
        for l in (ROOT / "data" / f"qa_v0.6_{sp}.jsonl").open(encoding="utf-8"):
            d = json.loads(l)
            gi[d["qa_id"]] = d
    agg = {q for q, g in gi.items()
           if g.get("split") == "test_public" and g.get("task_type") == "cross_source_aggregation"}
    srcs = {
        "gpt-5.5": ["fc_gpt-5.5_test_public_512kexp", "fc_gpt-5.5_test_public_fixed512k"],
        "gpt-4.1-mini": ["fc_gpt-4.1-mini_test_public_512kexp", "fc_gpt-4.1-mini_test_public_fixed512k"],
        "minimax-m3": ["fc_minimax-m3-cloud_tp_512kexp", "fc_minimax-m3-cloud_tp_fixed"],
        "glm-5.2": ["fc_glm-5.2-cloud_tp_512kexp", "fc_glm-5.2-cloud_tp_fixed"],
    }
    for m, tags in srcs.items():
        v: dict[str, int] = {}
        for t in tags:
            for qid, ok in judged(t).items():
                if qid in agg:
                    v[qid] = ok
        with (B / f"panel_gpt-4.1-mini_agg81_{m}.judged.jsonl").open("w", encoding="utf-8") as f:
            for qid in sorted(agg):
                if qid in v:
                    f.write(json.dumps({"qa_id": qid, "judge_correct": bool(v[qid]),
                                        "raw": "YES" if v[qid] else "NO"}, ensure_ascii=False) + "\n")
        print(f"  gpt-4.1-mini agg {m}: {sum(v.values())}/{len(v)}")
    print("[ok] primary-judge panel files written; run scripts/kappa_panel.py to verify.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
