"""Dense bge-m3 k=50 on the 81 aggregation items: the paper's k=50 table, from released files only.

Reads results/judge_verdicts_v0.9.4/ (k=50), results/judge_verdicts_v0.9.2/ and results/judge_verdicts_v0.9.3/
(full context 512k and dense top-5 references), results/item_sets/agg81.jsonl, the QA file, and
results/retrieval_v0.9.4/k50_coverage_agg81.jsonl. No API calls, no bundle text.

Pre-specified rule (fixed before any generation call): d = accuracy(k=50) - accuracy(full context 512k) on the
same 81 items under the primary judge; 95% bootstrap over the 9 announcement-table pairs (B=10000,
seed 20261011); "exceeds" if the interval lies above 0, "below" if below 0, otherwise "no detected difference".

Usage (from the repository root): python3 scripts/v094/score_k50.py
"""
import ast
import collections
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results"
PRIMARY, SECONDARY = "claude-sonnet-5-5", "gpt-4.1-mini"
B, SEED = 10000, 20261011


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def verdicts(*paths):
    out = {}
    for p in paths:
        out.update({r["qa_id"]: bool(r["judge_correct"]) for r in load(p)})
    return out


def v092(judge, tag):
    return RES / "judge_verdicts_v0.9.2" / judge / f"{tag}.jsonl"


def v093(judge, tag):
    return RES / "judge_verdicts_v0.9.3" / judge / f"{tag}.jsonl"


def v094(judge, tag):
    return RES / "judge_verdicts_v0.9.4" / judge / f"{tag}.jsonl"


# full context 512k and dense top-5 (the rows of the paper's aggregation table)
FC = {
    "gpt-5.5": lambda j: verdicts(v092(j, "fc_gpt-5.5_test_public_512kexp"), v092(j, "fc_gpt-5.5_test_public_fixed512k")),
    "gpt-4.1-mini": lambda j: verdicts(v092(j, "fc_gpt-4.1-mini_test_public_512kexp"), v092(j, "fc_gpt-4.1-mini_test_public_fixed512k")),
    "minimax-m3": lambda j: verdicts(v092(j, "fc_minimax-m3-cloud_tp_512kexp"), v092(j, "fc_minimax-m3-cloud_tp_fixed")),
    "glm-5.2": lambda j: verdicts(v092(j, "fc_glm-5.2-cloud_tp_512kexp"), v092(j, "fc_glm-5.2-cloud_tp_fixed")),
    "claude-sonnet-5-5": lambda j: verdicts(v093(j, "agg512k_claude-sonnet-5-5")),
    "claude-haiku-5-5": lambda j: verdicts(v093(j, "agg512k_claude-haiku-5-5")),
}
DENSE5 = {
    "gpt-5.5": lambda j: verdicts(v092(j, "jf386_gpt-5.5_dense")),
    "gpt-4.1-mini": lambda j: verdicts(v092(j, "jf386_gpt-4.1-mini_dense")),
    "minimax-m3": lambda j: verdicts(v092(j, "jf386_minimax-m3_dense")),
    "glm-5.2": lambda j: verdicts(v093(j, "thinkon_dense_glm-5.2")),
    "claude-sonnet-5-5": lambda j: verdicts(v093(j, "dense_claude-sonnet-5-5")),
    "claude-haiku-5-5": lambda j: verdicts(v093(j, "dense_claude-haiku-5-5")),
}
# k=50 rows: (label, released tag, reference model)
ROWS = [
    ("gpt-5.5", "k50dense_gpt-5.5", "gpt-5.5"),
    ("glm-5.2", "k50dense_glm-5.2", "glm-5.2"),
    ("minimax-m3 (reasoning on; reported)", "k50dense_minimax-m3", "minimax-m3"),
    ("minimax-m3 (flag off, no reasoning)", "k50dense_minimax-m3_reasoning-absent", "minimax-m3"),
    ("claude-sonnet-5-5", "k50dense_claude-sonnet-5-5", "claude-sonnet-5-5"),
    ("claude-haiku-5-5", "k50dense_claude-haiku-5-5", "claude-haiku-5-5"),
    ("gpt-4.1-mini", "k50dense_gpt-4.1-mini", "gpt-4.1-mini"),
]
PANEL = ["deepseek-v4.1-flash", "gemma4_31b", "kimi-k2.6", "mistral-large-3_675b"]


def lit(x):
    return ast.literal_eval(x) if isinstance(x, str) else x


def wilson(c, n, z=1.96):
    p = c / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def main():
    agg = [r["qa_id"] for r in load(RES / "item_sets" / "agg81.jsonl")]
    qa = {r["qa_id"]: r for r in load(ROOT / "data" / "qa_v0.6_test_public.jsonl")}
    pair = {}
    for q in agg:
        r = qa[q]
        ann = (lit(r.get("announcement_ids")) or [""])[0]
        pair[q] = (ann, lit(r["gold_predicate"])["source"])
    groups = collections.defaultdict(list)
    for q in agg:
        groups[pair[q]].append(q)
    keys = sorted(groups)
    assert len(keys) == 9, len(keys)

    def boot(stat):
        rnd = random.Random(SEED)
        out = []
        for _ in range(B):
            samp = [q for k in (rnd.choice(keys) for _ in keys) for q in groups[k]]
            out.append(stat(samp))
        out.sort()
        return out[int(0.025 * B)], out[int(0.975 * B) - 1]

    cov = {r["qa_id"]: r for r in load(RES / "retrieval_v0.9.4" / "k50_coverage_agg81.jsonl")}
    pct = lambda x: f"{100 * x:.0f}"
    print(f"Aggregation set: {len(agg)} items, {len(keys)} announcement-table pairs; "
          f"{sum(cov[q]['full'] for q in agg)} items fully covered (page and every matched row) at k=50.\n")
    print("| model | k=50 acc (n) | Wilson | pair bootstrap | FC 512k | d (pp) | pair bootstrap | label | secondary | dense k=5 | correct, not covered | wrong, covered |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for label, tag, ref in ROWS:
        k = verdicts(v094(PRIMARY, tag))
        f = FC[ref](PRIMARY)
        d5 = DENSE5[ref](PRIMARY)
        s = verdicts(v094(SECONDARY, tag))
        assert all(q in k and q in f and q in d5 and q in s for q in agg), label
        h = sum(k[q] for q in agg)
        hf = sum(f[q] for q in agg)
        h5 = sum(d5[q] for q in agg)
        hs = sum(s[q] for q in agg)
        pb = boot(lambda smp: sum(k[q] for q in smp) / len(smp))
        dstat = lambda smp: (sum(k[q] for q in smp) - sum(f[q] for q in smp)) / len(smp)
        d = dstat(agg)
        dpb = boot(dstat)
        lab = "exceeds" if dpb[0] > 0 else ("below" if dpb[1] < 0 else "no detected difference")
        wl = wilson(h, 81)
        cnc = sum(1 for q in agg if k[q] and not cov[q]["full"])
        wc = sum(1 for q in agg if not k[q] and cov[q]["full"])
        print(f"| {label} | {pct(h / 81)}% ({h}) | [{pct(wl[0])}, {pct(wl[1])}] | [{pct(pb[0])}, {pct(pb[1])}] | "
              f"{pct(hf / 81)}% ({hf}) | {100 * d:+.0f} | [{100 * dpb[0]:+.0f}, {100 * dpb[1]:+.0f}] | {lab} | "
              f"{pct(hs / 81)}% ({hs}) | {pct(h5 / 81)}% ({h5}) | {cnc} | {wc} |")
    print("\nPanel re-scores of the Anthropic k=50 predictions (accuracy %, n=81 each):")
    for m in ("claude-sonnet-5-5", "claude-haiku-5-5"):
        cells = [f"primary {pct(sum(verdicts(v094(PRIMARY, 'k50dense_' + m)).values()) / 81)}",
                 f"gpt-4.1-mini {pct(sum(verdicts(v094(SECONDARY, 'k50dense_' + m)).values()) / 81)}"]
        for j in PANEL:
            v = verdicts(RES / "judge_verdicts_v0.9.4" / "panel" / f"panel_{j}_k50dense_{m}.jsonl")
            assert len(v) == 81
            cells.append(f"{j} {pct(sum(v.values()) / 81)}")
        print(f"- {m}: " + ", ".join(cells))


if __name__ == "__main__":
    main()
