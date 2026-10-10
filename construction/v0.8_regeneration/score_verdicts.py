#!/usr/bin/env python3
"""Score a triage judge's verdicts against the planted-error truth file.

A "good" triage judge should flag the planted-BAD items (NOT_SUPPORTED/UNCLEAR)
and pass the ok items (SUPPORTED). The dangerous failure is a MISS: a BAD item
judged SUPPORTED -> a real error would slip through review.

Usage:
  python3 score_verdicts.py --verdicts <model_verdicts.json> --label haiku
  (truth defaults to ./testset_truth.jsonl next to this script)
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_verdicts(path):
    raw = open(path, encoding="utf-8").read().strip()
    # tolerate markdown fences / leading prose
    m = re.search(r"\[.*\]", raw, re.S)
    if m:
        raw = m.group(0)
    arr = json.loads(raw)
    return {v["qa_id"]: v for v in arr}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--truth", default=os.path.join(HERE, "testset_truth.jsonl"))
    ap.add_argument("--label", default="model")
    a = ap.parse_args()

    truth = [json.loads(l) for l in open(a.truth, encoding="utf-8") if l.strip()]
    verds = load_verdicts(a.verdicts)

    n_bad = sum(t["is_bad"] for t in truth)
    n_ok = sum(not t["is_bad"] for t in truth)
    catches = misses = false_flags = ok_pass = missing = 0

    print(f"\n=== {a.label} ===")
    print(f"{'qa_id':22}{'task_type':26}{'truth':6}{'verdict':16}{'result':10}")
    for t in truth:
        v = verds.get(t["qa_id"])
        if v is None:
            missing += 1
            print(f"{t['qa_id']:22}{t['task_type']:26}{('BAD' if t['is_bad'] else 'ok'):6}{'<missing>':16}{'NO-OUTPUT':10}")
            continue
        vd = str(v.get("verdict", "")).upper()
        flagged = vd in ("NOT_SUPPORTED", "UNCLEAR")
        if t["is_bad"]:
            if flagged:
                catches += 1; res = "CATCH ✓"
            else:
                misses += 1; res = "MISS ✗✗"   # dangerous
        else:
            if flagged:
                false_flags += 1; res = "false-flag"
            else:
                ok_pass += 1; res = "pass ✓"
        print(f"{t['qa_id']:22}{t['task_type']:26}{('BAD' if t['is_bad'] else 'ok'):6}{vd:16}{res:10}")

    cr = catches / n_bad if n_bad else 0
    ffr = false_flags / n_ok if n_ok else 0
    print(f"\n  planted errors caught : {catches}/{n_bad}  (catch-rate {cr:.0%})")
    print(f"  MISSES (slipped through): {misses}/{n_bad}   <- minimize this")
    print(f"  false-flags on ok items : {false_flags}/{n_ok}  (rate {ffr:.0%})  <- only costs review time")
    if missing:
        print(f"  no-output items         : {missing}")
    print()


if __name__ == "__main__":
    main()
