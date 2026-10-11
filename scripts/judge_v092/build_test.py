#!/usr/bin/env python3
"""Build Claude judge inputs for test_public (v0.9.2 scope). No API calls.

For every judged run (tag) the prediction for each in-scope qa_id is taken from the same
prediction file the v0.9.1 gpt-4.1-mini verdict was produced from. A run's predictions come in
layers (base run, then re-runs for fixed bundles); a later layer overrides an earlier one only
for qa_ids whose released verdict came from that layer's tag. Every in-scope qa_id must resolve.

Prediction files are internal (`workspace_local/audit/baselines/`, not released).

Writes to --out:
  prompts.jsonl / index.jsonl              all core + aggregation runs, plus the human-80 sample
                                           (custom_id r#####)
  prompts_multi.jsonl / index_multi.jsonl  accept-any items only, multi-answer gold
                                           (custom_id g#####, same suffix as the r id)

    python3 scripts/judge_v092/build_test.py --out WORKDIR [--baselines DIR]
"""
from __future__ import annotations

import argparse
import collections
from pathlib import Path

from common import (BASELINES, LEGAL, RELEASED_V091, ROOT, gold_fixes, gold_v092, judge_prompt,
                    load, write_jsonl)


def preds(p: Path) -> dict[str, str]:
    return {r["qa_id"]: r.get("prediction", "") for r in load(p)}


def verdicts(tag: str) -> dict[str, bool] | None:
    p = RELEASED_V091 / f"{tag}.jsonl"
    return {r["qa_id"]: bool(r["judge_correct"]) for r in load(p)} if p.exists() else None


def gpt_layers(M: str, R: str) -> tuple[str, list]:
    """(release tag, [(sub-tag or None for the base layer, prediction file), ...])."""
    tag = "g55fc" if (M, R) == ("gpt-5.5", "fc") else f"{M}_{R}"
    st = f"{R}_{M}_test_public.jsonl"
    if R == "fc" and M in ("gpt-4.1-mini", "gpt-5.5"):
        segs = [(None, st + ".prehugfix"), (tag + "_hugfix", f"fc_{M}_test_public_hugfix.jsonl"),
                (tag + "_new285", f"fc_{M}_test_public_new285.jsonl"),
                (tag + "_new285hugfc", f"fc_{M}_test_public_new285hugfc.jsonl"),
                (f"fc_{M}_test_public_fixed512k", f"fc_{M}_test_public_fixed512k.jsonl")]
    elif R == "rag":
        segs = [(f"jf386_{M}_bm25", f"ragbm25fx386_{M}_test_public.jsonl")]
    else:
        segs = [(None, st + ".pre285"), (tag + "_new285", f"{R}_{M}_test_public_new285.jsonl")]
        if (M, R) == ("gpt-5.5", "cb"):
            segs.append((tag + "_g55miss", "cb_gpt-5.5_test_public_g55miss.jsonl"))
    return tag, segs


def all_tags() -> dict[str, list]:
    tags: dict[str, list] = {}
    for M in ("gpt-4.1-mini", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.5"):
        for R in ("cb", "rag", "fc"):
            t, s = gpt_layers(M, R)
            tags[t] = s
        tags[f"jf386_{M}_dense"] = [(None, f"ragdensefx386_{M}_test_public.jsonl")]
    for m in ("minimax-m3", "glm-5.2", "qwen3.5"):
        for R in ("cb", "rag", "fc"):
            t = f"{R}_{m}-cloud_tp"
            if R == "rag":
                tags[t] = [(f"jf386_{m}_bm25", f"rag_bm25_{m}-cloud_tp386_fixed_tp.jsonl")]
            elif R == "fc" and m != "qwen3.5":
                tags[t] = [(None, f"run_open/{t}.jsonl"), (f"{t}_fixed", f"run_open/{t}_fixed.jsonl")]
            else:
                tags[t] = [(None, f"run_open/{t}.jsonl")]
        tags[f"jf386_{m}_dense"] = [(None, f"rag_dense_{m}-cloud_tp386_fixed_tp.jsonl")]
    # aggregation / 512k runs (full context on the evidence-complete 512k bundle)
    for f in ("fc_gpt-5.5_test_public_512kexp", "fc_gpt-5.5_test_public_fixed512k",
              "fc_gpt-4.1-mini_test_public_512kexp", "fc_gpt-4.1-mini_test_public_fixed512k",
              "run_open/fc_minimax-m3-cloud_tp_512kexp", "run_open/fc_minimax-m3-cloud_tp_fixed",
              "run_open/fc_glm-5.2-cloud_tp_512kexp", "run_open/fc_glm-5.2-cloud_tp_fixed"):
        tags[Path(f).name] = [(None, f + ".jsonl")]
    return tags


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="work directory for prompts/index files")
    ap.add_argument("--baselines", default=str(BASELINES), help="internal prediction directory")
    ap.add_argument("--accept-any-format", default="or", choices=["or", "multi"],
                    help="gold text of accept-any items in prompts.jsonl; 'or' reproduces the first "
                         "full batch, whose accept-any verdicts were replaced by prompts_multi.jsonl")
    args = ap.parse_args()
    B, out = Path(args.baselines), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    gold = {d["qa_id"]: d for d in load(ROOT / "data/qa_v0.6_test_public.jsonl")}
    fix = gold_fixes()
    excl = set(fix["exclude_from_evaluation"])
    inscope = {q for q, d in gold.items() if d.get("task_type") != LEGAL and q not in excl}

    reqs, idx = [], []
    for tag, segs in all_tags().items():
        v = verdicts(tag)
        want = sorted(q for q in v if q in inscope)
        src: dict[str, str] = {}
        for sub, f in segs:
            p = preds(B / f)
            if sub is None:
                src.update(p)
            else:
                sv = verdicts(sub)
                src.update({q: p[q] for q in p if q in v and sv is not None and q in sv})
        miss = [q for q in want if q not in src]
        assert not miss, (tag, len(miss))
        for q in want:
            cid = f"r{len(reqs):05d}"
            reqs.append({"custom_id": cid, "prompt": judge_prompt(
                gold[q].get("question", ""), gold_v092(gold[q], fix, args.accept_any_format), src[q])})
            idx.append({"custom_id": cid, "set": "core_or_agg", "tag": tag, "qa_id": q,
                        "gold_fixed": q in fix["replace"] or q in fix["accept_any"]})
    # human-80 judge-validation sample (gold and prediction as labelled by the human)
    for r in load(B / "panel_items_human80.jsonl"):
        cid = f"r{len(reqs):05d}"
        reqs.append({"custom_id": cid, "prompt": judge_prompt(r["question"], r["gold"], r["prediction"])})
        idx.append({"custom_id": cid, "set": "human80", "tag": "human80", "qa_id": r["qa_id"], "human": r["human"]})
    write_jsonl(out / "prompts.jsonl", reqs)
    write_jsonl(out / "index.jsonl", idx)

    # multi-answer re-judge set: accept-any items only
    mreqs, midx = [], []
    for r, i in zip(reqs, idx):
        if i["set"] == "core_or_agg" and i["qa_id"] in fix["accept_any"]:
            g = gold[i["qa_id"]]
            cid = "g" + i["custom_id"][1:]
            mreqs.append({"custom_id": cid, "prompt": judge_prompt(
                g.get("question", ""), gold_v092(g, fix, "multi"), _pred_of(r["prompt"]))})
            midx.append({**i, "custom_id": cid, "orig_custom_id": i["custom_id"]})
    write_jsonl(out / "prompts_multi.jsonl", mreqs)
    write_jsonl(out / "index_multi.jsonl", midx)

    print("requests", len(reqs), "by set", dict(collections.Counter(i["set"] for i in idx)),
          "tags", len({i["tag"] for i in idx}))
    print("gold-fixed calls", sum(i.get("gold_fixed", False) for i in idx), "multi-answer calls", len(mreqs))
    return 0


def _pred_of(prompt: str) -> str:
    """Prediction text back out of a judge prompt (inverse of judge_prompt's last field)."""
    p = prompt.split("\n[모델답변] ", 1)[1].rsplit("\n\n판정:", 1)[0]
    return "" if p == "(빈 답)" else p


if __name__ == "__main__":
    raise SystemExit(main())
