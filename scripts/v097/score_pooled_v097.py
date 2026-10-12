#!/usr/bin/env python3
"""Pooled (dev + test_public) and dev accuracy of the four hosted OpenAI models after the full dev review (v0.9.7).
Released files only, no API calls.

Three states per cell (closed-book, BM25, full context; primary and secondary judge):
  v096   : the published scope (v0.9.3 exclusions; 122 dev items out of BM25/FC) and verdicts -> reproduces S3
  excl   : + the 11 new v0.9.7 exclusions, verdicts unchanged
  v097   : + the v0.9.7 re-judged verdicts of the 79 gold-changed dev items (results/judge_verdicts_v0.9.7/),
           with BM25/FC scoped by --bundle-exclusions (default data/v0.9.9/bundle_exclusions.txt: the 122 dev items
           plus the 20 answerability items of v0.9.9; data/v0.9.3/bundle_exclusions.txt gives the v0.9.7/v0.9.8 values)
Plain and cluster-weighted accuracy as scripts/score_judge.py (weights = released cluster_weight).

Usage: python3 score_pooled_v097.py DATASET [--bundle-exclusions FILE] [--json OUT.json]
"""
import json
import sys
from pathlib import Path

R = Path(sys.argv[1]).resolve()
LEGAL = "cross_document_legal_reasoning"


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def ids(p):
    return {l.strip() for l in open(p) if l.strip() and not l.startswith("#")}


G = {d["qa_id"]: d for sp in ("dev", "test_public") for d in jl(R / f"data/qa_v0.6_{sp}.jsonl")}
EX3, EX7 = ids(R / "data/v0.9.3/eval_exclusions.txt"), ids(R / "data/v0.9.7/eval_exclusions.txt")
B122 = ids(R / "data/v0.9.3/bundle_exclusions.txt")


def _opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


_bx = _opt("--bundle-exclusions")
if _bx is None:
    _bx = R / "data/v0.9.9/bundle_exclusions.txt"
    _bx = _bx if _bx.exists() else R / "data/v0.9.3/bundle_exclusions.txt"
B_FINAL = ids(Path(_bx) if Path(_bx).is_absolute() else R / _bx)
JUDGES = ("claude-sonnet-5-5", "gpt-4.1-mini")


def V(judge, ver, tag):
    p = R / f"results/judge_verdicts_{ver}/{judge}/{tag}.jsonl"
    return {r["qa_id"]: bool(r["judge_correct"]) for r in jl(p)} if p.exists() else {}


M = {"gpt-4.1-mini": ("gpt-4.1-mini_cb", "gpt-4.1-mini_rag", "gpt-4.1-mini_fc"),
     "gpt-5.4-mini": ("gpt-5.4-mini_cb", "gpt-5.4-mini_rag", "gpt-5.4-mini_fc"),
     "gpt-5.4-nano": ("gpt-5.4-nano_cb", "gpt-5.4-nano_rag", "gpt-5.4-nano_fc"),
     "gpt-5.5": ("gpt-5.5_cb", "gpt-5.5_rag", "g55fc")}


def verdicts(judge, m, setting, rejudged):
    cb, rag, fc = M[m]
    if setting == "cb":
        v = V(judge, "v0.9.2", cb)
        for sp in ("dev", "test_public"):
            v.update(V(judge, "v0.9.3", f"cbfix_{m}_{sp}"))
        if m == "gpt-5.5":
            v.update(V(judge, "v0.9.3", "g55retry_cb_dev"))
            v.update(V(judge, "v0.9.3", "g55retry_cb_test_public"))
        if rejudged:
            v.update(V(judge, "v0.9.7", f"rejudge_{cb}"))
            if m == "gpt-5.5":
                v.update(V(judge, "v0.9.7", "rejudge_g55retry_cb_dev"))
        return v
    tag = rag if setting == "bm25" else fc
    v = V(judge, "v0.9.2", tag)
    if rejudged:
        v.update(V(judge, "v0.9.7", f"rejudge_{tag}"))
    return v


def score(v, keep):
    q = [k for k in v if k in keep]
    n = len(q)
    h = sum(v[k] for k in q)
    wn = sum(float(G[k].get("cluster_weight", 1)) for k in q)
    wh = sum(float(G[k].get("cluster_weight", 1)) for k in q if v[k])
    return {"n": n, "hits": h, "plain": 100 * h / n if n else 0, "cw": 100 * wh / wn if wn else 0}


def scope(excl, split, setting, bex=None):
    s = {q for q, g in G.items() if g["task_type"] != LEGAL and q not in excl and (split == "pooled" or g["split"] == split)}
    if setting != "cb":
        s -= B122 if bex is None else bex
    return s


rows, out = [], {}
for judge in JUDGES:
    for m in M:
        for setting in ("cb", "bm25", "fc"):
            for split in ("pooled", "dev"):
                a = score(verdicts(judge, m, setting, False), scope(EX3, split, setting))
                b = score(verdicts(judge, m, setting, False), scope(EX7, split, setting))
                c = score(verdicts(judge, m, setting, True), scope(EX7, split, setting, B_FINAL))
                out[f"{judge}|{m}|{setting}|{split}"] = {"v096": a, "excl": b, "v097": c}
                rows.append((judge, m, setting, split, a, b, c))

f = lambda s: f"{s['plain']:.1f} / {s['cw']:.1f} (n={s['n']})"
print("| judge | model | setting | split | v0.9.6 published scope | + 11 exclusions | + re-judged gold (v0.9.7) | "
      "change from re-judge (plain pp) | total change (plain pp) |")
print("|---|---|---|---|---|---|---|---:|---:|")
for judge, m, s, sp, a, b, c in rows:
    print(f"| {judge} | {m} | {s} | {sp} | {f(a)} | {f(b)} | {f(c)} | {c['plain'] - b['plain']:+.2f} | {c['plain'] - a['plain']:+.2f} |")

print("\nS3 pooled table (primary judge, plain / cluster-weighted, rounded), v0.9.6 -> v0.9.7:")
for m in M:
    cells = []
    for s in ("cb", "bm25", "fc"):
        a, c = out[f"claude-sonnet-5-5|{m}|{s}|pooled"]["v096"], out[f"claude-sonnet-5-5|{m}|{s}|pooled"]["v097"]
        cells.append(f"{a['plain']:.0f}/{a['cw']:.0f} -> {c['plain']:.0f}/{c['cw']:.0f}")
    print(f"  {m}: CB {cells[0]} | BM25 {cells[1]} | FC {cells[2]}")
n = {s: out[f"claude-sonnet-5-5|gpt-5.5|{s}|pooled"]["v097"]["n"] for s in ("cb", "bm25", "fc")}
n54 = out["claude-sonnet-5-5|gpt-5.4-mini|fc|pooled"]["v097"]["n"]
print(f"  n: closed-book {n['cb']}; BM25 {n['bm25']}; FC {n['fc']} (4.1-mini, 5.5) and {n54} (5.4 models)")
mx = max(abs(r[6]["plain"] - r[5]["plain"]) for r in rows if r[3] == "pooled")
mxa = max(rows, key=lambda r: abs(r[6]["plain"] - r[5]["plain"]) if r[3] == "pooled" else -1)
print(f"\nLargest pooled change from the re-judge (gold changes only): {mx:.2f} pp ({mxa[0]}, {mxa[1]}, {mxa[2]})")

print("\nPooled full context by tier (primary judge, plain), v0.9.6 -> v0.9.7:")
for m in M:
    cells = []
    for t in ("32k", "64k", "128k", "256k", "512k"):
        a = score(verdicts("claude-sonnet-5-5", m, "fc", False), {q for q in scope(EX3, "pooled", "fc") if G[q].get("context_tier") == t})
        c = score(verdicts("claude-sonnet-5-5", m, "fc", True), {q for q in scope(EX7, "pooled", "fc", B_FINAL) if G[q].get("context_tier") == t})
        if a["n"] or c["n"]:
            cells.append(f"{t} {a['plain']:.0f}->{c['plain']:.0f} (n {a['n']}->{c['n']})")
    print(f"  {m}: " + "; ".join(cells))
print(f"\nbundle exclusions for the final state: {len(B_FINAL)} items ({_bx})")
if _opt("--json"):
    json.dump(out, open(_opt("--json"), "w"), indent=1)
