#!/usr/bin/env python3
"""Anthropic-model scores under the primary judge, the four panel judges and the round-3 human labels.
Reads only released files (results/judge_verdicts_v0.9.3, results/human_review_v0.9.3). No API calls.

The human-labelled score uses the round-3 final label for the 74 predictions on which the six judges
disagree and the (unanimous) judge verdict elsewhere.

    python3 scripts/v093/score_claude_human.py
"""
import json, collections
from pathlib import Path
W = Path(__file__).resolve().parents[2]; V = W / "results/judge_verdicts_v0.9.3"
PANEL = ["gemma4_31b", "kimi-k2.6", "mistral-large-3_675b", "deepseek-v4.1-flash"]
def load(p): return {r["qa_id"]: r["judge_correct"] for r in map(json.loads, open(p))}
hum = collections.defaultdict(dict)
for r in map(json.loads, open(W / "results/human_review_v0.9.3/claude74_adjudication.jsonl")):
    reg = {"e3oracle": "oracle_agg81", "e3region": "openregion_agg81"}.get(r["regime"], r["regime"])
    hum[f"{reg}_{r['model']}"][r["qa_id"]] = r["final"] == "correct"
print("| run | n | primary | secondary | panel mean (4) | human-labelled |")
for p in sorted((V / "claude-sonnet-5-5").glob("*claude-*.jsonl")):
    tag = p.stem; pr = load(p); se = load(V / "gpt-4.1-mini" / p.name)
    pm = sum(sum(load(V / "panel" / f"panel_{j}_{tag}.jsonl").values()) for j in PANEL) / 4
    h = {q: hum[tag].get(q, v) for q, v in pr.items()}
    n = len(pr); f = lambda c: f"{100 * c / n:.1f}"
    print(f"| {tag} | {n} | {f(sum(pr.values()))} | {f(sum(se.values()))} | {f(pm)} | {f(sum(h.values()))} |")
