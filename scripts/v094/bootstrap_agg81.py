"""Bootstrap intervals on the 81 aggregation items (pair and cluster units) and accuracy by matched-row count,
for full context (512k), open-region and oracle contexts and the top-5 retrieval rows. Primary judge
(claude-sonnet-5-5) verdicts from released files only. No API calls.

Units: the 9 announcement-table pairs and the dataset's near-duplicate clusters; B=10000, seed 20261011.

Usage (from the repository root): python3 scripts/v094/bootstrap_agg81.py [--out tables.md]
"""
import ast, collections, json, math, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results"
def L(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
def lit(x): return ast.literal_eval(x) if isinstance(x, str) else x
G = {r["qa_id"]: r for r in L(ROOT / "data" / "qa_v0.6_test_public.jsonl")}
def wilson(c, n, z=1.96):
    p = c / n; d = 1 + z * z / n; centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))
def vfile(p): return {r["qa_id"]: bool(r["judge_correct"]) for r in L(p)}
JUD = {"claude": "claude-sonnet-5-5", "gpt": "gpt-4.1-mini"}
def rel(judge, tag): return vfile(RES / "judge_verdicts_v0.9.2" / judge / f"{tag}.jsonl")
def r93(j, tag): return vfile(RES / "judge_verdicts_v0.9.3" / JUD[j] / f"{tag}.jsonl")
NEWM = {"claude-sonnet-5-5", "claude-haiku-5-5"}
OLDFC = {"gpt-5.5": ["fc_gpt-5.5_test_public_512kexp", "fc_gpt-5.5_test_public_fixed512k"],
         "gpt-4.1-mini": ["fc_gpt-4.1-mini_test_public_512kexp", "fc_gpt-4.1-mini_test_public_fixed512k"],
         "minimax-m3": ["fc_minimax-m3-cloud_tp_512kexp", "fc_minimax-m3-cloud_tp_fixed"],
         "glm-5.2": ["fc_glm-5.2-cloud_tp_512kexp", "fc_glm-5.2-cloud_tp_fixed"]}
OLDRAG = {"gpt-4.1-mini": ("gpt-4.1-mini_rag", "jf386_gpt-4.1-mini_dense"), "gpt-5.5": ("gpt-5.5_rag", "jf386_gpt-5.5_dense"),
          "minimax-m3": ("rag_minimax-m3-cloud_tp", "jf386_minimax-m3_dense"), "glm-5.2": ("rag_glm-5.2-cloud_tp", "jf386_glm-5.2_dense")}
MODELS = ["gpt-5.5", "glm-5.2", "minimax-m3", "claude-sonnet-5-5", "claude-haiku-5-5", "gpt-4.1-mini"]
def fc(m, j="claude"):
    if m in NEWM: return r93(j, f"agg512k_{m}")
    v = {}
    for t in OLDFC[m]: v.update(rel(JUD[j], t) or {})
    return v
def e3(m, var, j="claude"): return r93(j, {"e3region": "openregion", "e3oracle": "oracle"}[var] + f"_agg81_{m}")
def rag(m, reg, j="claude"):
    if m in NEWM: return r93(j, f"{reg}_{m}")
    return rel(JUD[j], OLDRAG[m][0 if reg == "bm25" else 1])
AGG = [r["qa_id"] for r in L(RES / "item_sets" / "agg81.jsonl")]
SRCN = {"hug-sale-history": "hug", "molit-apt-trade-detail": "molit"}
SRC = {q: {"source": SRCN.get(lit(G[q]["gold_predicate"])["source"], lit(G[q]["gold_predicate"])["source"])} for q in AGG}
PAIR = {q: ((lit(G[q].get("announcement_ids")) or [""])[0], SRC[q]["source"]) for q in AGG}
CLU = {q: G[q]["cluster_id"] for q in AGG}
NROWS = {r["qa_id"]: int(r["n_rows"]) for r in L(RES / "retrieval_v0.9.4" / "k50_coverage_agg81.jsonl")}
CONDS = {"FC 512k": lambda m: fc(m), "open-region": lambda m: e3(m, "e3region"), "oracle": lambda m: e3(m, "e3oracle")}
V_ = {(m, c): fn(m) for m in MODELS for c, fn in CONDS.items()}
for k, v in V_.items(): assert all(q in v for q in AGG), (k, sum(q not in v for q in AGG))
B, SEED = 10000, 20261011
def boot(units, stat):
    groups = collections.defaultdict(list)
    for q in AGG: groups[units[q]].append(q)
    keys = sorted(groups); rnd = random.Random(SEED); out = []
    for _ in range(B):
        samp = [q for k in (rnd.choice(keys) for _ in keys) for q in groups[k]]
        out.append(stat(samp))
    out.sort(); return out[int(0.025 * B)], out[int(0.975 * B) - 1]
acc = lambda v: (lambda s: sum(v[q] for q in s) / len(s))
res = {"units": {"pair": len(set(PAIR.values())), "cluster": len(set(CLU.values()))}, "acc": {}, "diff": {}, "rows": {}}
lines = ["## 1. Aggregation 81: accuracy with Wilson vs cluster-bootstrap 95% CI (Claude judge)",
         f"Units: announcement–table pair ({res['units']['pair']} units of 9 items) and dataset near-duplicate cluster ({res['units']['cluster']} units: 24, 24, 12, 12, 3, 3, 3). B={B}, seed {SEED}.", "",
         "| Model | condition | acc | Wilson | pair bootstrap | cluster bootstrap |", "|---|---|---|---|---|---|"]
for m in MODELS:
    for c in CONDS:
        v = V_[(m, c)]; h = sum(v[q] for q in AGG); a = h / 81; w = wilson(h, 81)
        pb = boot(PAIR, acc(v)); cb = boot(CLU, acc(v))
        res["acc"][f"{m}|{c}"] = {"hits": h, "acc": a, "wilson": w, "pair": pb, "cluster": cb}
        f = lambda t: f"[{t[0]*100:.0f}, {t[1]*100:.0f}]"
        lines.append(f"| {m} | {c} | {a*100:.0f}% ({h}) | {f(w)} | {f(pb)} | {f(cb)} |")
lines += ["", "## 2. Paired differences (percentage points, same items), cluster bootstrap", "| comparison | condition | diff | pair bootstrap | cluster bootstrap |", "|---|---|---|---|---|"]
PAIRS_CMP = [("gpt-5.5", "glm-5.2"), ("glm-5.2", "minimax-m3"), ("claude-sonnet-5-5", "minimax-m3"), ("glm-5.2", "claude-sonnet-5-5"),
             ("claude-sonnet-5-5", "claude-haiku-5-5"), ("claude-haiku-5-5", "gpt-4.1-mini")]
for a_, b_ in PAIRS_CMP:
    for c in CONDS:
        va, vb = V_[(a_, c)], V_[(b_, c)]
        st = lambda s: (sum(va[q] for q in s) - sum(vb[q] for q in s)) / len(s)
        d = st(AGG); pb = boot(PAIR, st); cb = boot(CLU, st)
        res["diff"][f"{a_}-{b_}|{c}"] = {"diff": d, "pair": pb, "cluster": cb}
        lines.append(f"| {a_} − {b_} | {c} | {d*100:+.0f} | [{pb[0]*100:+.0f}, {pb[1]*100:+.0f}] | [{cb[0]*100:+.0f}, {cb[1]*100:+.0f}] |")
for m in MODELS:  # within-model condition gains
    for c1, c2 in (("open-region", "FC 512k"), ("oracle", "open-region")):
        va, vb = V_[(m, c1)], V_[(m, c2)]
        st = lambda s: (sum(va[q] for q in s) - sum(vb[q] for q in s)) / len(s)
        d = st(AGG); pb = boot(PAIR, st); cb = boot(CLU, st)
        res["diff"][f"{m}|{c1}-{c2}"] = {"diff": d, "pair": pb, "cluster": cb}
        lines.append(f"| {m}: {c1} − {c2} | — | {d*100:+.0f} | [{pb[0]*100:+.0f}, {pb[1]*100:+.0f}] | [{cb[0]*100:+.0f}, {cb[1]*100:+.0f}] |")
BINS = [(1, 3), (5, 7), (11, 21), (61, 77), (137, 223)]
binof = lambda n: next(f"{lo}–{hi}" for lo, hi in BINS if lo <= n <= hi)
lines += ["", "## 3. Accuracy by matched-row count (Claude judge, hits/n)"]
bins = collections.defaultdict(list)
for q in AGG: bins[binof(NROWS[q])].append(q)
hdr = [f"{lo}–{hi} (n={len(bins[f'{lo}–{hi}'])})" for lo, hi in BINS]
lines += ["| Model | condition | " + " | ".join(hdr) + " |", "|---|---|" + "---|" * len(BINS)]
for m in MODELS:
    conds = dict(CONDS); conds["BM25 k=5"] = lambda mm: rag(mm, "bm25"); conds["dense k=5"] = lambda mm: rag(mm, "dense")
    for c, fn in conds.items():
        v = V_[(m, c)] if (m, c) in V_ else fn(m)
        cells = []
        for lo, hi in BINS:
            qs = bins[f"{lo}–{hi}"]; assert all(q in v for q in qs), (m, c)
            h = sum(v[q] for q in qs); cells.append(f"{h}/{len(qs)}"); res["rows"][f"{m}|{c}|{lo}-{hi}"] = [h, len(qs)]
        lines.append(f"| {m} | {c} | " + " | ".join(cells) + " |")
lines.append("\nBins: 1–3 HUG, 5–7 HUG, 11–21 HUG, 61–77 HUG (all HUG), 137–223 = the 9 MOLIT items.")
assert all(SRC[q]["source"] == "molit" for q in bins["137–223"]) and all(SRC[q]["source"] == "hug" for lo, hi in BINS[:4] for q in bins[f"{lo}–{hi}"])
if "--out" in sys.argv: open(sys.argv[sys.argv.index("--out") + 1], "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
