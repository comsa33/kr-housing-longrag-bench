#!/usr/bin/env python3
"""Pooled multi-answer sensitivity after the v0.9.7 re-judge (released files only, no API calls).

How much pooled accuracy (dev + test_public, four OpenAI models, primary judge) would drop if the accept-any items
were scored against a single answer. An item counts as lost when it is correct under the multi-answer gold and
wrong under the single original answer:
  test_public (23 accept-any items of v0.9.2): primary-judge multi-answer verdict (judge_verdicts_v0.9.2 /
    v0.9.3 overlays) YES and gpt-4.1-mini strict verdict on the original gold (results/judge_verdicts, v0.9.1) NO
    (as in the registry's Q9 table);
  dev (74 gold_accept_any items of v0.9.7): primary-judge v0.9.7 re-judged verdict YES and the v0.9.2
    primary-judge verdict on the original single gold NO.
Usage: python3 multi_answer_bound_v097.py DATASET_V097
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
R = Path(sys.argv[1]).resolve()
sys.argv = [sys.argv[0], str(R)] + sys.argv[2:]
import score_pooled_v097 as sp  # noqa: E402  (also prints its tables; silenced below)

acc_test = set(json.load(open(R / "data/v0.9.2/gold_fixes.json"))["accept_any"])
acc_dev = {r["qa_id"] for r in csv.DictReader(open(R / "data/errata_v0.9.7.csv")) if r["v0.9.7_status"] == "gold_accept_any"}
J = "claude-sonnet-5-5"
rows = []
for m, (cb, rag, fc) in sp.M.items():
    for setting, tag in (("cb", cb), ("bm25", rag), ("fc", fc)):
        keep = sp.scope(sp.EX7, "pooled", setting, sp.B_FINAL)
        multi = sp.verdicts(J, m, setting, True)
        strict_test = {r["qa_id"]: bool(r["judge_correct"]) for r in sp.jl(R / f"results/judge_verdicts/{tag}.jsonl")}
        single_dev = sp.V(J, "v0.9.2", tag)
        if setting == "cb" and m == "gpt-5.5":
            single_dev.update(sp.V(J, "v0.9.3", "g55retry_cb_dev"))
        n_items = [q for q in multi if q in keep]
        wn = sum(float(sp.G[q].get("cluster_weight", 1)) for q in n_items)
        t_in = [q for q in n_items if q in acc_test]
        d_in = [q for q in n_items if q in acc_dev]
        t_lost = [q for q in t_in if multi[q] and strict_test.get(q) is False]
        d_lost = [q for q in d_in if multi[q] and single_dev.get(q) is False]
        lost = t_lost + d_lost
        w = sum(float(sp.G[q].get("cluster_weight", 1)) for q in lost)
        rows.append((m, setting, len(n_items), len(t_in), len(d_in), len(t_lost), len(d_lost),
                     100 * len(lost) / len(n_items), 100 * w / wn))
print("\n=== multi-answer sensitivity (pooled, primary judge) ===")
print("| model | setting | pooled n | accept-any test / dev in cell | lost test / dev | plain pp | cw pp |")
print("|---|---|---:|---|---|---:|---:|")
for r in rows:
    print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} / {r[4]} | {r[5]} / {r[6]} | {r[7]:.2f} | {r[8]:.2f} |")
bp = max(rows, key=lambda r: r[7]); bc = max(rows, key=lambda r: r[8])
print(f"max plain {bp[7]:.2f} ({bp[0]} {bp[1]}); max cw {bc[8]:.2f} ({bc[0]} {bc[1]})")
print(f"accept-any items in scope: test {len(acc_test)}, dev {len(acc_dev)}, total {len(acc_test) + len(acc_dev)}")
