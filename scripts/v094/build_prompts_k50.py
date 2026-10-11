"""Build bge-m3 top-k prompts for the 81 aggregation items with the exact code of the reported dense runs.

Step A (verification): rebuild k=5 and compare to the stored prompt files
  rag_dense_agg81_fixed_prompts.jsonl and rag_dense_tp386_fixed_prompts.jsonl (the source of jf386_*_dense).
Step B: build k=50 with only k changed -> $KRH_WORKSPACE/v094/prompts_dense_k50_agg81.jsonl (contains bundle text;
not redistributed). Chunker: v0.9.2 page markers (KRH_LEGACY_PAGE_MARKERS=1), as in every reported retrieval run.
Needs the rebuilt 512k bundle, a local Ollama bge-m3 endpoint, and the stored k=5 prompt files (build machine).

Usage (from the repository root): python3 scripts/v094/build_prompts_k50.py [k]
"""
import os, sys, json, copy
from pathlib import Path
os.environ["KRH_LEGACY_PAGE_MARKERS"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k50_lib as lib
from k50_lib import R
HERE = lib.OUT
HERE.mkdir(parents=True, exist_ok=True)
K = int(sys.argv[1]) if len(sys.argv) > 1 else 50

qa = lib.test_qa()
agg = lib.load_jsonl(lib.BASEL / "rag_dense_agg81_fixed_prompts.jsonl")
tp = {r["qa_id"]: r for r in lib.load_jsonl(lib.BASEL / "rag_dense_tp386_fixed_prompts.jsonl")}
assert len(agg) == 81
bc, dc = {}, {}
same_agg = same_tp = 0
for s in agg:
    rec = qa[s["qa_id"]]; bid = s["bundle_id"]
    picked = R.retrieve("dense_bge", rec, lib.chunks_for(bid, 1200), 5, bid, bc, dc, s["per_page_max"])
    p = R.rag_prompt(rec, picked)
    same_agg += p == s["prompt"]
    same_tp += p == tp[s["qa_id"]]["prompt"]
lib.save_cache()
print(f"k=5 rebuild: identical to agg81 file {same_agg}/81, to tp386 file {same_tp}/81", flush=True)
assert same_agg == 81 and same_tp == 81, "k=5 rebuild not identical; stop"

out = []
for s in agg:
    rec = qa[s["qa_id"]]; bid = s["bundle_id"]
    picked = R.retrieve("dense_bge", rec, lib.chunks_for(bid, 1200), K, bid, bc, dc, s["per_page_max"])
    r = copy.deepcopy(s)
    r["prompt"] = R.rag_prompt(rec, picked)
    r["k"] = K; r["n_passages"] = len(picked)
    pages = []
    for pid, _ in picked:
        if pid not in pages: pages.append(pid)
    r["retrieved_page_ids"] = pages
    out.append(r)
lib.save_cache()
fn = HERE / f"prompts_dense_k{K}_agg81.jsonl"
with open(fn, "w", encoding="utf-8") as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
chars = sorted(len(r["prompt"]) for r in out)
print(f"k={K}: wrote {fn.name}; n_passages {min(r['n_passages'] for r in out)}-{max(r['n_passages'] for r in out)}; prompt chars median {chars[40]} max {chars[-1]}")
