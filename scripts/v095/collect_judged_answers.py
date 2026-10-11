"""Build results/predictions_v0.9.5/ (model answers) from the judge inputs kept on the build machine.

Build-machine only: the judge-input files live under workspace_local/archive_scratchpads/ (not released).
Each released answer is the exact string the judge scored, except for the masking documented in
results/predictions_v0.9.5/README.md. No model calls.
Usage (from the repo root): python3 scripts/v095/build_model_answers.py
"""
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WS = os.environ.get("KRH_WORKSPACE", os.path.join(ROOT, "workspace_local"))
import json, collections, sys
X = os.path.join(WS, "archive_scratchpads", "2026-10-12") + "/"
L = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
def pred_of(prompt): return prompt.rsplit("\n[모델답변]", 1)[1].rsplit("\n\n판정:", 1)[0].strip()
out = []
for d, split in (("fd300867-9e50-4cd3-969c-6e13c9c436ba/jv_test/", "test_public"), ("fd300867-9e50-4cd3-969c-6e13c9c436ba/jv_dev/", "dev")):
    idx = {r["custom_id"]: r for r in L(X + d + "index.jsonl")}
    for r in L(X + d + "prompts.jsonl"):
        i = idx[r["custom_id"]]; out.append({"src": "v0.9.2", "tag": i["tag"], "split": split, "qa_id": i["qa_id"], "cid": r["custom_id"], "prediction": pred_of(r["prompt"])})
d = "d1aa983f-5aba-4857-9c7c-65001ddacd81/judge_new/"
idx = {r["custom_id"]: r for r in L(X + d + "index_v2.jsonl")}
for r in L(X + d + "claude_requests_v2.jsonl"):
    i = idx.get(r["custom_id"])
    if i: out.append({"src": "v0.9.3", "tag": i["tag"], "split": i["split"], "qa_id": i["qa_id"], "cid": r["custom_id"], "prediction": pred_of(r["params"]["messages"][0]["content"])})
d = "bad0f45b-f680-4f0e-baa1-8aae8abe8a23/k50/judge/"
for s in "ABC":
    idx = {r["custom_id"]: r for r in L(X + d + f"index_{s}.jsonl")}
    for r in L(X + d + f"claude_requests_{s}.jsonl"):
        i = idx[r["custom_id"]]; out.append({"src": "v0.9.4", "tag": i["tag"], "split": "test_public", "qa_id": i["qa_id"], "cid": r["custom_id"], "prediction": pred_of(r["params"]["messages"][0]["content"])})
json.dump(out, open(os.path.join(WS, "v095_preds_all.json"), "w"), ensure_ascii=False)
c = collections.Counter((o["src"], o["split"], o["tag"]) for o in out)
for k, v in sorted(c.items()): print(*k, v)
print("total", len(out))
