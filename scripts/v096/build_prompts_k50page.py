"""k=50 + announcement page on the 18 uncovered aggregation items (pre-specified 2026-10-12).

For each of the 18 items whose k=50 bge-m3 passages contain no chunk of the gold announcement page
(results/retrieval_v0.9.4/k50_coverage_agg81.jsonl, page=false), take the exact k=50 prompt and insert the
whole gold page (v0.9.2 chunker page split) as ONE more passage in reading order, in the same passage format.
Nothing else changes. Checks: the rebuilt k=50 prompt equals the stored one; the new prompt differs from it only
by the inserted block; the other 63 items' k=50 prompts already contain a chunk of their gold page.

Build-machine only (needs the rebuilt 512k bundles, the stored k=50 prompts and the bge-m3 embedding cache);
outputs contain bundle text and are not redistributed.
Usage (from the repository root):
  python3 scripts/v096/build_prompts_k50page.py [K50_PROMPTS] [BGE_CACHE]
defaults: $KRH_WORKSPACE/v094/prompts_dense_k50_agg81.jsonl and $KRH_WORKSPACE/v094/cache/bge_m3_emb.pkl
"""
import json, os, sys
from pathlib import Path
os.environ["KRH_LEGACY_PAGE_MARKERS"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "v094"))
import k50_lib as lib
from k50_lib import R
OUT = lib.WORK / "v096"; OUT.mkdir(parents=True, exist_ok=True)
K50P = Path(sys.argv[1]) if len(sys.argv) > 1 else lib.OUT / "prompts_dense_k50_agg81.jsonl"
if len(sys.argv) > 2: lib.CACHE_F = Path(sys.argv[2])
qa = lib.test_qa(); rk = lib.Ranker()
P = {json.loads(l)["qa_id"]: json.loads(l) for l in open(K50P, encoding="utf-8")}
cov = {json.loads(l)["qa_id"]: json.loads(l) for l in open(ROOT / "results/retrieval_v0.9.4/k50_coverage_agg81.jsonl")}
unc = sorted(q for q, v in cov.items() if not v["page"]); assert len(unc) == 18, len(unc)
out, rep, ok63 = [], [], 0
for q, s in P.items():
    rec = qa[q]; bid = s["bundle_id"]; ch = lib.chunks_for(bid, 1200); gold = set(rec["page_ids"])
    if q not in unc:
        ok63 += any(f"[{g} (p." in s["prompt"] for g in gold); continue
    idx = sorted(rk.full("dense_bge", rec, bid, 1200)[:50]); picked = [ch[i] for i in idx]
    assert R.rag_prompt(rec, picked) == s["prompt"], q
    assert not any(ch[i][0] in gold for i in idx), q
    pages = dict(R.split_pages((lib.BUNDLES / f"{bid}.txt").read_text(encoding="utf-8")))
    assert len(gold) == 1; g = next(iter(gold))
    first = min(i for i, (pid, _) in enumerate(ch) if pid == g)
    pos = sum(1 for i in idx if i < first)
    np_ = R.rag_prompt(rec, picked[:pos] + [(g, pages[g])] + picked[pos:])
    r = dict(s); r["prompt"] = np_; r["setting"] = "k50page"; r["added_page"] = g; r["insert_pos"] = pos
    out.append(r); rep.append({"qa_id": q, "page": g, "insert_pos": pos, "page_chars": len(pages[g]),
                                "added_chars": len(np_) - len(s["prompt"])})
lib.save_cache()
print("other 63 contain a gold-page chunk:", ok63, "/ 63")
with open(OUT / "prompts_k50page_18.jsonl", "w", encoding="utf-8") as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
json.dump(rep, open(OUT / "build_report.json", "w"), indent=1)
for x in rep: print(x)
