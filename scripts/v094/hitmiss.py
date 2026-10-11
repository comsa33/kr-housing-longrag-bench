"""Accuracy on the 258 non-aggregation test_public items, split by whether the retriever's top five passages
include the gold page (hit) or not (miss). Released files only, no API calls.

Hit = gold-page recall@5 of 1.0 in results/retrieval_v0.9.4/nonagg_recall_test.csv (BM25 and bge-m3, 1,200-character
passages, page-identifier match; on test_public this equals the majority-page rule of recall_majority_page.py).
Verdicts: primary judge (claude-sonnet-5-5); glm-5.2 is its reasoning-on run.

Usage (from the repository root): python3 scripts/v094/hitmiss.py
"""
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
J2 = ROOT / "results" / "judge_verdicts_v0.9.2" / "claude-sonnet-5-5"
J3 = ROOT / "results" / "judge_verdicts_v0.9.3" / "claude-sonnet-5-5"
TAGS = {  # model -> (bm25 file, dense file)
    "gpt-4.1-mini": (J2 / "gpt-4.1-mini_rag.jsonl", J2 / "jf386_gpt-4.1-mini_dense.jsonl"),
    "gpt-5.4-mini": (J2 / "gpt-5.4-mini_rag.jsonl", J2 / "jf386_gpt-5.4-mini_dense.jsonl"),
    "gpt-5.4-nano": (J2 / "gpt-5.4-nano_rag.jsonl", J2 / "jf386_gpt-5.4-nano_dense.jsonl"),
    "gpt-5.5": (J2 / "gpt-5.5_rag.jsonl", J2 / "jf386_gpt-5.5_dense.jsonl"),
    "minimax-m3": (J2 / "rag_minimax-m3-cloud_tp.jsonl", J2 / "jf386_minimax-m3_dense.jsonl"),
    "glm-5.2": (J3 / "thinkon_bm25_glm-5.2.jsonl", J3 / "thinkon_dense_glm-5.2.jsonl"),
    "claude-sonnet-5-5": (J3 / "bm25_claude-sonnet-5-5.jsonl", J3 / "dense_claude-sonnet-5-5.jsonl"),
    "claude-haiku-5-5": (J3 / "bm25_claude-haiku-5-5.jsonl", J3 / "dense_claude-haiku-5-5.jsonl"),
}
COL = {"bm25": "bm25_1200_r@5", "dense": "dense_bge_1200_r@5"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return {r["qa_id"]: bool(r["judge_correct"]) for r in map(json.loads, f) if r}


def wilson(c, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = c / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def cell(c, n):
    lo, hi = wilson(c, n)
    return f"{100 * c / n:.0f} [{100 * lo:.0f}, {100 * hi:.0f}] ({c}/{n})"


def main():
    rows = list(csv.DictReader(open(ROOT / "results" / "retrieval_v0.9.4" / "nonagg_recall_test.csv", encoding="utf-8")))
    items = [r["qa_id"] for r in rows]
    assert len(items) == 258
    for i, reg in enumerate(("bm25", "dense")):
        hit = {r["qa_id"] for r in rows if float(r[COL[reg]]) == 1.0}
        miss = set(items) - hit
        print(f"\n{reg}: hit {len(hit)}, miss {len(miss)}")
        print("| model | hit | miss |")
        print("|---|---|---|")
        th = tn = mh = mn = 0
        for m, files in TAGS.items():
            v = load(files[i])
            h = sum(v[q] for q in hit)
            mi = sum(v[q] for q in miss)
            th += h; tn += len(hit); mh += mi; mn += len(miss)
            print(f"| {m} | {cell(h, len(hit))} | {cell(mi, len(miss))} |")
        print(f"| pooled over 8 models (item-model pairs) | {100 * th / tn:.1f} | {100 * mh / mn:.1f} |")


if __name__ == "__main__":
    main()
