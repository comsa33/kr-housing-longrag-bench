#!/usr/bin/env python3
"""temp=0 run-to-run variance sub-study for the open-weight baselines (EACL leg).

Standard: report mean +/- std over K>=3 (here K=5) FULL-test_public runs, not a
subset. Run 1 (r1) = the existing main run in run_open/ (no suffix); this driver
produces the ADDITIONAL repeats (r2..r5) into run_open/variance/.

Per (model, repeat) it runs each regime through the crash-safe runner with
--resume, then strips empty predictions and re-runs them (escalating max-output
tokens), matching the main pipeline so the repeats are apples-to-apples with the
reported (cleaned) numbers. The residual empty/degeneration rate per run is
reported separately.

Inference is Ollama-only (flat subscription, pace across 2h session windows via
--resume; a quota/rate-limit hit just leaves items unwritten -> retried next
window). NO gpt models here (they stay single-run; this study characterizes the
open reasoning models' temp-0 non-determinism).

Usage:
    python3 scripts/run_variance.py --model minimax-m3:cloud \
        --label minimax-m3-cloud --rk r2
    # regimes default to all the model supports; qwen3.5 auto-skips fc_groupB (512k cap)

Then judge each {regime}_{label}_tp_{rk}.jsonl with llm_judge.py and compute
stats with the --stats mode of this script.
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, "scripts", "run_llm_baseline.py")
RO = os.path.join(ROOT, "workspace_local", "audit", "baselines", "run_open")
PROMPTS = os.path.join(RO, "prompts")
VO = os.path.join(RO, "variance")
PY = sys.executable

# regime -> (think, num_ctx, base_mot, prompt_file, is_fc)
# fc is split into groupA (<=256K) and groupB (512k, HUG-overridden); qwen skips B.
REGIMES = {
    "cb":  ("off", 8192,   2048, "cb_all_tp.jsonl",   False),
    "rag": ("off", 32768,  2048, "rag_all_tp.jsonl",  False),
    "fcA": ("on",  262144, 8192, "fc_groupA_tp.jsonl", True),
    "fcB": ("on",  262144, 8192, "fc_groupB_tp.jsonl", True),
}
# fcA + fcB both write to the same combined fc output (matches r1).
FC_OUT_KEY = "fc"


def out_path(regime_or_key, label, rk):
    key = FC_OUT_KEY if regime_or_key in ("fcA", "fcB") else regime_or_key
    return os.path.join(VO, f"{key}_{label}_tp_{rk}.jsonl")


def empties(path):
    ids = []
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if not (d.get("prediction") or "").strip():
                ids.append(d["qa_id"])
    return ids


def strip_ids(path, ids):
    idset = set(ids)
    for p in (path, path.replace(".jsonl", ".calls.jsonl")):
        if not os.path.exists(p):
            continue
        kept = [l for l in open(p) if l.strip() and json.loads(l).get("qa_id") not in idset]
        with open(p, "w") as f:
            f.writelines(kept)


def run_once(model, think, ctx, mot, prompt_file, out):
    cmd = [PY, RUNNER, "--provider", "ollama", "--resume", "--split", "test_public",
           "--model", model, "--think", think, "--num-ctx", str(ctx),
           "--max-output-tokens", str(mot), "--prompt-file", prompt_file, "--out", out]
    print(f"    $ {' '.join(cmd[3:])}", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=False)


def run_regime(model, regime, label, rk, max_passes=3):
    think, ctx, base_mot, pf_name, is_fc = REGIMES[regime]
    pf = os.path.join(PROMPTS, pf_name)
    out = out_path(regime, label, rk)
    if not os.path.exists(pf):
        print(f"  !! missing prompt {pf}"); return
    print(f"  [{regime}] -> {os.path.basename(out)}")
    run_once(model, think, ctx, base_mot, pf, out)
    # strip empties + retry, escalating mot (fc reasoning items may need more room)
    mot = base_mot
    for p in range(max_passes):
        emp = empties(out)
        if not emp:
            break
        mot = min(mot * 2, 16384)
        print(f"    pass {p+1}: {len(emp)} empty -> strip + rerun @ mot={mot}")
        strip_ids(out, emp)
        run_once(model, think, ctx, mot, pf, out)
    n = sum(1 for l in open(out) if l.strip()) if os.path.exists(out) else 0
    print(f"  [{regime}] done: n={n}, residual empty={len(empties(out))}")


def cmd_run(args):
    os.makedirs(VO, exist_ok=True)
    is_qwen = "qwen" in args.model.lower()
    order = args.regimes.split(",") if args.regimes else ["fcB", "fcA", "rag", "cb"]
    if is_qwen:
        order = [r for r in order if r != "fcB"]  # 256K cap: cannot ingest 512k
    print(f"== variance run: model={args.model} label={args.label} rk={args.rk} regimes={order} ==")
    for regime in order:
        run_regime(args.model, regime, args.label, args.rk)
    print(f"== {args.label} {args.rk} complete ==")
    return 0


def cmd_stats(args):
    """Aggregate mean+/-std over repeats from judged files.

    Reads judged verdicts {regime}_{label}_tp_{rk}.judged.jsonl (rk in r1..rK;
    r1 = the main run, judged file lives in baselines/ root without _r suffix).
    Prints per-model per-regime plain accuracy mean +/- std across repeats.
    """
    import statistics
    B = os.path.join(ROOT, "workspace_local", "audit", "baselines")
    labels = args.labels.split(",")
    ks = args.ks.split(",")
    for label in labels:
        print(f"\n== {label} ==")
        for regime in ("cb", "rag", "fc"):
            accs = []
            for k in ks:
                # r1 judged lives in baselines/ root w/o suffix; repeats in variance/ or root
                cands = [
                    os.path.join(B, f"{regime}_{label}_tp.judged.jsonl") if k == "r1" else None,
                    os.path.join(B, f"{regime}_{label}_tp_{k}.judged.jsonl"),
                ]
                path = next((c for c in cands if c and os.path.exists(c)), None)
                if not path:
                    continue
                v = [json.loads(l) for l in open(path) if l.strip()]
                if not v:
                    continue
                accs.append(100.0 * sum(int(x["judge_correct"]) for x in v) / len(v))
            if len(accs) >= 2:
                m = statistics.mean(accs)
                s = statistics.pstdev(accs) if len(accs) > 1 else 0.0
                print(f"  {regime:3}: {m:5.1f} +/- {s:4.1f}  (K={len(accs)} runs: {['%.1f'%a for a in accs]})")
            elif accs:
                print(f"  {regime:3}: {accs[0]:5.1f}  (only 1 run judged so far)")
            else:
                print(f"  {regime:3}: (no judged runs yet)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="action")
    r = sub.add_parser("run"); r.set_defaults(fn=cmd_run)
    r.add_argument("--model", required=True)
    r.add_argument("--label", required=True)
    r.add_argument("--rk", required=True, help="repeat id, e.g. r2")
    r.add_argument("--regimes", default="", help="comma list; default fcB,fcA,rag,cb")
    s = sub.add_parser("stats"); s.set_defaults(fn=cmd_stats)
    s.add_argument("--labels", default="minimax-m3-cloud,glm-5.2-cloud,qwen3.5-cloud")
    s.add_argument("--ks", default="r1,r2,r3,r4,r5")
    args = ap.parse_args()
    if not getattr(args, "fn", None):
        ap.print_help(); return 2
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
