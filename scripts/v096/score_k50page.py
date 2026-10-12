"""k=50 + announcement page on the 18 uncovered aggregation items: per-model counts from released verdicts only.

Reads results/judge_verdicts_v0.9.6/ (k=50+page, primary and secondary judges, four panel judges on the two
Anthropic models), results/judge_verdicts_v0.9.4/ (k=50, same 18 items), results/judge_verdicts_v0.9.3/
(open-region, same 18 items) and results/retrieval_v0.9.4/k50_coverage_agg81.jsonl. No API calls.
Pre-specified report: correct of 18 per model; no interval (the 18 items come from two announcement-table pairs).
Usage (from the repository root): python3 scripts/v096/score_k50page.py
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; RES = ROOT / "results"
L = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
V = lambda p: {r["qa_id"]: bool(r["judge_correct"]) for r in L(p)}
ITEMS = sorted(r["qa_id"] for r in L(RES / "retrieval_v0.9.4/k50_coverage_agg81.jsonl") if not r["page"])
assert len(ITEMS) == 18
MODELS = ["gpt-5.5", "minimax-m3", "glm-5.2", "claude-sonnet-5-5", "claude-haiku-5-5", "gpt-4.1-mini"]
def cnt(p): v = V(p); assert set(v) >= set(ITEMS), p; return sum(v[q] for q in ITEMS)
print("| model | k=50 | k=50+page primary | k=50+page secondary | open-region |")
print("|---|---|---|---|---|")
for m in MODELS:
    pg1 = cnt(RES / f"judge_verdicts_v0.9.6/claude-sonnet-5-5/k50page_{m}.jsonl")
    pg2 = cnt(RES / f"judge_verdicts_v0.9.6/gpt-4.1-mini/k50page_{m}.jsonl")
    k50 = cnt(RES / f"judge_verdicts_v0.9.4/claude-sonnet-5-5/k50dense_{m}.jsonl")
    orr = cnt(RES / f"judge_verdicts_v0.9.3/claude-sonnet-5-5/openregion_agg81_{m}.jsonl")
    print(f"| {m} | {k50}/18 | {pg1}/18 | {pg2}/18 | {orr}/18 |")
print("\npanel (k=50+page):")
for f in sorted((RES / "judge_verdicts_v0.9.6/panel").glob("*.jsonl")):
    print(f.stem, f"{cnt(f)}/18")
