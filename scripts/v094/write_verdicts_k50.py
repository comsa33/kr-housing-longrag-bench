"""Write results/judge_verdicts_v0.9.4/ from the raw k=50 judge batch results and the panel outputs.

Build machine only: the raw batch files hold the predictions and stay off the repository. Output files hold
{"qa_id", "judge_correct"} only. No API calls.

Usage: python3 scripts/v094/write_verdicts_k50.py --run-dir <k50 run directory with judge/>
"""
import argparse, collections, csv, glob, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "judge_verdicts_v0.9.4"
# run model key -> released tag suffix
TAGS = {
    "gpt-5.5": "k50dense_gpt-5.5",
    "gpt-4.1-mini": "k50dense_gpt-4.1-mini",
    "glm-5.2": "k50dense_glm-5.2",
    "minimax-m3-thinkon": "k50dense_minimax-m3",                     # reported row: reasoning on
    "minimax-m3": "k50dense_minimax-m3_reasoning-absent",            # flag off, endpoint returned no reasoning
    "claude-sonnet-5-5": "k50dense_claude-sonnet-5-5",
    "claude-haiku-5-5": "k50dense_claude-haiku-5-5",
}
REGIME = {"k50dense_minimax-m3": "dense k=50 (reasoning on; reported)",
          "k50dense_minimax-m3_reasoning-absent": "dense k=50 (flag off, no reasoning; not reported as the result)"}
PANEL_WHO = {"sonnet55": "claude-sonnet-5-5", "haiku55": "claude-haiku-5-5"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    a = ap.parse_args()
    J = Path(a.run_dir) / "judge"
    idx = {}
    for f in glob.glob(str(J / "index_*.jsonl")):
        for l in open(f):
            r = json.loads(l)
            idx[r["custom_id"]] = r
    V = {"claude-sonnet-5-5": collections.defaultdict(dict), "gpt-4.1-mini": collections.defaultdict(dict)}
    for f in glob.glob(str(J / "raw_claude_requests_*.jsonl")):
        for l in open(f):
            r = json.loads(l); i = idx[r["custom_id"]]; res = r["result"]
            assert res["type"] == "succeeded", r["custom_id"]
            t = "".join(b.get("text", "") for b in res["message"]["content"] if b["type"] == "text")
            V["claude-sonnet-5-5"][i["model"]][i["qa_id"]] = json.loads(t)["verdict"] == "YES"
    for f in glob.glob(str(J / "raw_gpt_requests_*.jsonl")):
        for l in open(f):
            r = json.loads(l); i = idx[r["custom_id"]]
            t = (r["response"]["body"]["choices"][0]["message"].get("content") or "").strip().upper()
            V["gpt-4.1-mini"][i["model"]][i["qa_id"]] = t.startswith("YES")
    rows = []
    for judge, by_model in V.items():
        (OUT / judge).mkdir(parents=True, exist_ok=True)
        for m, tag in TAGS.items():
            d = by_model[m]
            assert len(d) == 81, (judge, m, len(d))
            with open(OUT / judge / f"{tag}.jsonl", "w") as fh:
                for q in sorted(d):
                    fh.write(json.dumps({"qa_id": q, "judge_correct": bool(d[q])}) + "\n")
            model = "minimax-m3" if m.startswith("minimax") else m
            rows.append([judge, tag, model, REGIME.get(tag, "dense k=50"), "test_public", 81])
    (OUT / "panel").mkdir(parents=True, exist_ok=True)
    for p in sorted(glob.glob(str(J / "panel_out" / "panel_*_k50dense.judged.jsonl"))):
        name = Path(p).name[len("panel_"):-len("_k50dense.judged.jsonl")]
        judge, who = name.rsplit("_", 1)
        rr = [json.loads(l) for l in open(p)]
        assert len(rr) == 81 and len({r["qa_id"] for r in rr}) == 81, p
        tag = f"panel_{judge}_k50dense_{PANEL_WHO[who]}"
        with open(OUT / "panel" / f"{tag}.jsonl", "w") as fh:
            for r in sorted(rr, key=lambda r: r["qa_id"]):
                fh.write(json.dumps({"qa_id": r["qa_id"], "judge_correct": bool(r["judge_correct"])}) + "\n")
        rows.append([judge, tag, PANEL_WHO[who], "dense k=50 (panel re-score)", "test_public", 81])
    with open(OUT / "MANIFEST.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["judge", "tag", "model", "regime", "split", "n"])
        w.writerows(rows)
    print(len(rows), "files")


if __name__ == "__main__":
    main()
