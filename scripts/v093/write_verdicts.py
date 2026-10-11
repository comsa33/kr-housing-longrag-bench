#!/usr/bin/env python3
"""Write results/judge_verdicts_v0.9.3/ from the raw judge batch results (no API calls).

Inputs (build machine): JUDGE_DIR with index_v2.jsonl, raw_claude_requests_v2.jsonl,
raw_gpt_requests_v2.jsonl; PANEL_DIR with panel_<judge>_<tag>.judged.jsonl (Ollama Cloud panel).
Output format as in v0.9.2: one line per item, {"qa_id": ..., "judge_correct": true|false}.

    python3 scripts/v093/write_verdicts.py JUDGE_DIR PANEL_DIR
"""
import csv, glob, json, os, re, sys, collections
from pathlib import Path
W = Path(__file__).resolve().parents[2]; J, P = Path(sys.argv[1]), Path(sys.argv[2])
OUT = W / "results/judge_verdicts_v0.9.3"
MODEL = {"sonnet55": "claude-sonnet-5-5", "haiku55": "claude-haiku-5-5"}
def rename(tag):
    m = re.match(r"e1_(.+)_(test|dev)$", tag)
    if m: return f"cbfix_{m[1]}_{'test_public' if m[2] == 'test' else 'dev'}", m[1], "cb (leak-fixed re-run, affected items)"
    m = re.match(r"e2_(.+)_(cb|bm25|dense)$", tag)
    if m: return f"thinkon_{m[2]}_{m[1]}", m[1], f"{m[2]} (reasoning on)"
    m = re.match(r"e3(oracle|region)_(.+)$", tag)
    if m: return f"{'oracle' if m[1] == 'oracle' else 'openregion'}_agg81_{m[2]}", m[2], f"agg81 {m[1] if m[1]=='oracle' else 'open-region'} rows"
    m = re.match(r"g55retry_(test|dev)$", tag)
    if m: return f"g55retry_cb_{'test_public' if m[1] == 'test' else 'dev'}", "gpt-5.5", "cb (single retry of empty answers)"
    m = re.match(r"(sonnet55|haiku55)_(.+)$", tag)
    if m:
        reg = {"e3oracle": "oracle_agg81", "e3region": "openregion_agg81"}.get(m[2], m[2])
        return f"{reg}_{MODEL[m[1]]}", MODEL[m[1]], reg.replace("_", " ")
    raise SystemExit("unknown tag " + tag)
idx = {json.loads(l)["custom_id"]: json.loads(l) for l in open(J / "index_v2.jsonl")}
V = {"claude-sonnet-5-5": collections.defaultdict(dict), "gpt-4.1-mini": collections.defaultdict(dict)}
for l in open(J / "raw_claude_requests_v2.jsonl"):
    r = json.loads(l); i = idx[r["custom_id"]]; m = r["result"]["message"]
    assert m["stop_reason"] == "end_turn"
    t = "".join(b.get("text", "") for b in m["content"] if b["type"] == "text")
    V["claude-sonnet-5-5"][i["tag"]][i["qa_id"]] = json.loads(t)["verdict"] == "YES"
for l in open(J / "raw_gpt_requests_v2.jsonl"):
    r = json.loads(l); i = idx[r["custom_id"]]; c = (r["response"]["body"]["choices"][0]["message"]["content"] or "").strip().upper()
    assert c.startswith(("YES", "NO")), c
    V["gpt-4.1-mini"][i["tag"]][i["qa_id"]] = c.startswith("YES")
man = []
for judge, tags in V.items():
    (OUT / judge).mkdir(parents=True, exist_ok=True)
    for tag, d in sorted(tags.items()):
        name, model, regime = rename(tag)
        with open(OUT / judge / f"{name}.jsonl", "w") as f:
            for q in sorted(d): f.write(json.dumps({"qa_id": q, "judge_correct": d[q]}) + "\n")
        split = "dev" if name.endswith("_dev") else "test_public"
        man.append({"judge": judge, "tag": name, "model": model, "regime": regime, "split": split, "n": len(d)})
(OUT / "panel").mkdir(parents=True, exist_ok=True)
for f in sorted(glob.glob(str(P / "panel_*.judged.jsonl"))):
    b = os.path.basename(f)[len("panel_"):-len(".judged.jsonl")]
    judge = next(j for j in ("gemma4_31b", "kimi-k2.6", "mistral-large-3_675b", "deepseek-v4.1-flash") if b.startswith(j + "_"))
    rest = b[len(judge) + 1:]
    if rest == "human80": name, model, regime, split = "human80", "four OpenAI models", "judge validation (80 human-labelled)", "mixed"
    elif rest.startswith("agg81_"): name, model, regime, split = f"fc_agg81_{rest[6:]}", rest[6:], "fc agg81 (512k)", "test_public"
    else: name, model, regime = rename(rest); split = "test_public"
    rows = [json.loads(l) for l in open(f)]
    with open(OUT / "panel" / f"panel_{judge}_{name}.jsonl", "w") as g:
        for r in sorted(rows, key=lambda r: r["qa_id"]): g.write(json.dumps({"qa_id": r["qa_id"], "judge_correct": bool(r["judge_correct"])}) + "\n")
    man.append({"judge": judge, "tag": f"panel_{judge}_{name}", "model": model, "regime": regime, "split": split, "n": len(rows)})
with open(OUT / "MANIFEST.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["judge", "tag", "model", "regime", "split", "n"]); w.writeheader(); w.writerows(man)
print("files", len(man), collections.Counter(m["judge"] for m in man))
