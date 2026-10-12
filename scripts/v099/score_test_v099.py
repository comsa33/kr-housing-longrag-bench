#!/usr/bin/env python3
"""test_public tables of the paper from released files only (no API calls), with the v0.9.9 bundle exclusions.

The bundle-based settings (BM25, dense bge-m3, full context) drop the items of --bundle-exclusions
(default data/v0.9.9/bundle_exclusions.txt: the 122 dev items and the 20 answerability items whose bundle
holds the asked-about announcement, 7 of them in test_public); closed-book keeps them.
--before uses data/v0.9.3/bundle_exclusions.txt and reproduces the v0.9.8 tables.

Prints:
  main    plain / cluster-weighted accuracy per model and setting (CB 342; BM25, dense on the items with a bundle;
          FC on the full-context sample)
  paired  all four settings on the same full-context sample items (CB restricted to those items too)
  m1      BM25 vs FC correct counts on the sample: all, without the 512k tier, without cross-source aggregation
  tier    FC plain accuracy by context tier
  hitmiss non-aggregation BM25 recall@k and BM25 accuracy on hit / miss items
          (results/retrieval_v0.9.4/nonagg_recall_test.csv, hit = recall@5 of 1.0)
  order   model order per setting under the primary and the secondary judge
  second  the main table under the secondary judge (gpt-4.1-mini); * = rounded value differs from the primary
  family  BM25 plain accuracy by task family (families with >= 4 items)
  hmtab   hit / miss accuracy with Wilson 95% intervals for BM25 and bge-m3

Verdicts: as reported (closed-book after the Section 4.1 correction, gpt-5.5 retries, glm-5.2 reasoning on).

Usage (from the repository root): python3 scripts/v099/score_test_v099.py [--bundle-exclusions FILE | --before]
"""
import csv
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
LEGAL = "cross_document_legal_reasoning"
P2, P3 = "judge_verdicts_v0.9.2/{j}/", "judge_verdicts_v0.9.3/{j}/"
MODELS = ["gpt-4.1-mini", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.5",
          "minimax-m3", "glm-5.2", "claude-sonnet-5-5", "claude-haiku-5-5"]
FILES = {
    "cb": {"gpt-4.1-mini": [P2 + "gpt-4.1-mini_cb", P3 + "cbfix_gpt-4.1-mini_test_public"],
           "gpt-5.4-mini": [P2 + "gpt-5.4-mini_cb", P3 + "cbfix_gpt-5.4-mini_test_public"],
           "gpt-5.4-nano": [P2 + "gpt-5.4-nano_cb", P3 + "cbfix_gpt-5.4-nano_test_public"],
           "gpt-5.5": [P2 + "gpt-5.5_cb", P3 + "g55retry_cb_test_public", P3 + "cbfix_gpt-5.5_test_public"],
           "minimax-m3": [P2 + "cb_minimax-m3-cloud_tp", P3 + "cbfix_minimax-m3_test_public"],
           "glm-5.2": [P3 + "thinkon_cb_glm-5.2"],
           "claude-sonnet-5-5": [P3 + "cb_claude-sonnet-5-5"], "claude-haiku-5-5": [P3 + "cb_claude-haiku-5-5"]},
    "bm25": {"gpt-4.1-mini": [P2 + "gpt-4.1-mini_rag"], "gpt-5.4-mini": [P2 + "gpt-5.4-mini_rag"],
             "gpt-5.4-nano": [P2 + "gpt-5.4-nano_rag"], "gpt-5.5": [P2 + "gpt-5.5_rag"],
             "minimax-m3": [P2 + "rag_minimax-m3-cloud_tp"], "glm-5.2": [P3 + "thinkon_bm25_glm-5.2"],
             "claude-sonnet-5-5": [P3 + "bm25_claude-sonnet-5-5"], "claude-haiku-5-5": [P3 + "bm25_claude-haiku-5-5"]},
    "dense": {"gpt-4.1-mini": [P2 + "jf386_gpt-4.1-mini_dense"], "gpt-5.4-mini": [P2 + "jf386_gpt-5.4-mini_dense"],
              "gpt-5.4-nano": [P2 + "jf386_gpt-5.4-nano_dense"], "gpt-5.5": [P2 + "jf386_gpt-5.5_dense"],
              "minimax-m3": [P2 + "jf386_minimax-m3_dense"], "glm-5.2": [P3 + "thinkon_dense_glm-5.2"],
              "claude-sonnet-5-5": [P3 + "dense_claude-sonnet-5-5"], "claude-haiku-5-5": [P3 + "dense_claude-haiku-5-5"]},
    "fc": {"gpt-4.1-mini": [P2 + "gpt-4.1-mini_fc", P2 + "fc_gpt-4.1-mini_test_public_fixed512k"],
           "gpt-5.4-mini": [P2 + "gpt-5.4-mini_fc"], "gpt-5.4-nano": [P2 + "gpt-5.4-nano_fc"],
           "gpt-5.5": [P2 + "g55fc", P2 + "fc_gpt-5.5_test_public_fixed512k"],
           "minimax-m3": [P2 + "fc_minimax-m3-cloud_tp", P2 + "fc_minimax-m3-cloud_tp_fixed"],
           "glm-5.2": [P2 + "fc_glm-5.2-cloud_tp", P2 + "fc_glm-5.2-cloud_tp_fixed"],
           "claude-sonnet-5-5": [P3 + "fc_claude-sonnet-5-5"], "claude-haiku-5-5": [P3 + "fc_claude-haiku-5-5"]},
}
SETTINGS = ("cb", "bm25", "dense", "fc")


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def ids(p):
    return {l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")}


def verdicts(setting, model, judge="claude-sonnet-5-5"):
    v = {}
    for t in FILES[setting][model]:
        v.update({r["qa_id"]: bool(r["judge_correct"]) for r in jl(R / "results" / (t.format(j=judge) + ".jsonl"))})
    return v


if "--before" in sys.argv:
    BX = R / "data/v0.9.3/bundle_exclusions.txt"
elif "--bundle-exclusions" in sys.argv:
    BX = Path(sys.argv[sys.argv.index("--bundle-exclusions") + 1])
    BX = BX if BX.is_absolute() else R / BX
else:
    BX = R / "data/v0.9.9/bundle_exclusions.txt"
BEX = ids(BX)
G = {d["qa_id"]: d for d in jl(R / "data/qa_v0.6_test_public.jsonl")}
EX = ids(R / "data/v0.9.7/eval_exclusions.txt")
TEST = sorted(q for q, g in G.items() if g["task_type"] != LEGAL and q not in EX)
w = lambda q: float(G[q].get("cluster_weight", 1))


def items(setting, v):
    return [q for q in TEST if q in v and (setting == "cb" or q not in BEX)]


def wilson(k, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / d
    return 100 * (c - h), 100 * (c + h)


def acc(v, qs):
    return 100 * sum(v[q] for q in qs) / len(qs), 100 * sum(w(q) for q in qs if v[q]) / sum(w(q) for q in qs)


print(f"bundle exclusions: {BX.parent.name}/{BX.name} ({len(BEX)} items, {len(BEX & set(TEST))} in test_public scope)")
V = {s: {m: verdicts(s, m) for m in MODELS} for s in SETTINGS}

print("\n== main (plain / cw, primary judge)")
for m in MODELS:
    cells = []
    for s in SETTINGS:
        qs = items(s, V[s][m])
        p, c = acc(V[s][m], qs)
        cells.append(f"{s} {p:.1f}/{c:.1f} (n={len(qs)})")
    print(f"  {m}: " + " | ".join(cells))

print("\n== paired: all settings on the same full-context sample items (plain)")
for m in MODELS:
    sample = items("fc", V["fc"][m])
    cells = [f"{s} {acc(V[s][m], sample)[0]:.0f} ({sum(V[s][m][q] for q in sample)})" for s in SETTINGS]
    print(f"  {m}: n={len(sample)} | " + " | ".join(cells))

print("\n== m1: BM25 / FC correct counts on the sample")
for m in MODELS:
    sample = items("fc", V["fc"][m])
    out = []
    for name, qs in (("all", sample),
                     ("no 512k", [q for q in sample if G[q].get("context_tier") != "512k"]),
                     ("no agg", [q for q in sample if G[q]["task_type"] != "cross_source_aggregation"])):
        b, f = sum(V["bm25"][m][q] for q in qs), sum(V["fc"][m][q] for q in qs)
        out.append(f"{name} {b}/{f} ({f - b:+d}; n={len(qs)})")
    print(f"  {m}: " + " | ".join(out))

print("\n== tier: FC plain accuracy by context tier")
for m in MODELS:
    sample = items("fc", V["fc"][m])
    out = []
    for t in ("32k", "64k", "128k", "256k", "512k"):
        qs = [q for q in sample if G[q].get("context_tier") == t]
        if qs:
            out.append(f"{t} {acc(V['fc'][m], qs)[0]:.0f} (n={len(qs)})")
    print(f"  {m}: " + "; ".join(out))

print("\n== hitmiss: non-aggregation items, BM25")
rows = [r for r in csv.DictReader(open(R / "results/retrieval_v0.9.4/nonagg_recall_test.csv", encoding="utf-8"))
        if r["qa_id"] not in BEX]
rk = {k: 100 * sum(float(r[f"bm25_1200_r@{k}"]) for r in rows) / len(rows) for k in (5, 10, 20, 50)}
gain = sum(1 for r in rows if float(r["bm25_1200_r@20"]) >= 1 > float(r["bm25_1200_r@5"]))
print(f"  n={len(rows)}; BM25 recall@5 {rk[5]:.1f}, @10 {rk[10]:.1f}, @20 {rk[20]:.1f}, @50 {rk[50]:.1f}; "
      f"items gained from k=5 to k=20: {gain}")
hit = {r["qa_id"] for r in rows if float(r["bm25_1200_r@5"]) >= 1}
miss = {r["qa_id"] for r in rows if float(r["bm25_1200_r@5"]) == 0}
for m in MODELS:
    v = V["bm25"][m]
    h, mi = [q for q in hit if q in v], [q for q in miss if q in v]
    print(f"  {m}: hit {acc(v, h)[0]:.0f} (n={len(h)}) | miss {acc(v, mi)[0]:.0f} (n={len(mi)})")

print("\n== order: models by plain accuracy, primary vs secondary judge")
for s in ("bm25", "dense", "fc"):
    for judge in ("claude-sonnet-5-5", "gpt-4.1-mini"):
        vals = {}
        for m in MODELS:
            v = verdicts(s, m, judge)
            vals[m] = acc(v, items(s, v))[0]
        print(f"  {s} {judge}: " + ", ".join(f"{m} {vals[m]:.1f}" for m in sorted(vals, key=lambda m: -vals[m])))

print("\n== second: main table under the secondary judge (plain / cw; * = rounded value differs from primary)")
for m in MODELS:
    cells = []
    for s_ in SETTINGS:
        v2 = verdicts(s_, m, "gpt-4.1-mini")
        qs = items(s_, v2)
        p2, c2 = acc(v2, qs)
        p1, c1 = acc(V[s_][m], items(s_, V[s_][m]))
        mark = lambda a, b: f"{round(a)}{'*' if round(a) != round(b) else ''}"
        cells.append(f"{s_} {mark(p2, p1)} / {mark(c2, c1)}")
    print(f"  {m}: " + " | ".join(cells))

print("\n== family: BM25 plain accuracy by task family")
fams = {}
for q in items("bm25", V["bm25"][MODELS[0]]):
    fams.setdefault(G[q]["task_type"], []).append(q)
for f, qs in sorted(fams.items(), key=lambda x: -len(x[1])):
    if len(qs) >= 4:
        print(f"  {f} (n={len(qs)}): " + ", ".join(f"{m} {acc(V['bm25'][m], [q for q in qs if q in V['bm25'][m]])[0]:.0f}"
                                               for m in MODELS))

print("\n== hmtab: hit / miss accuracy with Wilson 95% intervals")
for retr, col in (("bm25", "bm25_1200_r@5"), ("dense", "dense_bge_1200_r@5")):
    h_ = {r["qa_id"] for r in rows if float(r[col]) >= 1}
    m_ = {r["qa_id"] for r in rows if float(r[col]) == 0}
    print(f"  {retr}: hit n={len(h_)}, miss n={len(m_)}")
    for m in MODELS:
        v = V[retr][m]
        out = []
        for name, S in (("hit", h_), ("miss", m_)):
            qs = [q for q in S if q in v]
            k = sum(v[q] for q in qs)
            lo, hi = wilson(k, len(qs))
            out.append(f"{name} {100 * k / len(qs):.0f} [{lo:.0f}, {hi:.0f}]")
        print(f"    {m}: " + " | ".join(out))
