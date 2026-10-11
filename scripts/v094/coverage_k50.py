"""Per-item coverage of the k=50 dense context: the announcement page AND every matched row present.
Checks that the ranker's top 50 equal the chunks placed in the k=50 prompts (build_prompts_k50.py output) and
writes results/retrieval_v0.9.4/k50_coverage_agg81.jsonl. Build machine (needs bundles and bge-m3).

Usage (from the repository root): python3 scripts/v094/coverage_k50.py"""
import os, sys, json
from pathlib import Path
os.environ["KRH_LEGACY_PAGE_MARKERS"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k50_lib as lib
import k50_rows as rows
from k50_lib import R
HERE = lib.OUT
qa = lib.test_qa(); agg, _ = rows.build(qa); rk = lib.Ranker()
ch = lib.chunks_for(rows.AGG_BUNDLE, 1200)
P = {json.loads(l)["qa_id"]: json.loads(l) for l in open(HERE / "prompts_dense_k50_agg81.jsonl")}
bc, dc = {}, {}
per, same = {}, 0
for it in agg:
    q = it["rec"]["qa_id"]; idx = rk.full("dense_bge", it["rec"], rows.AGG_BUNDLE, 1200)[:50]
    picked = R.retrieve("dense_bge", it["rec"], ch, 50, rows.AGG_BUNDLE, bc, dc, 0)
    same += sorted(ch[i][1] for i in idx) == sorted(t for _, t in picked)
    page = set(it["rec"]["page_ids"]) <= {ch[i][0] for i in idx}
    cov = rows.covered(it, idx, 1200)
    per[q] = {"page": page, "rows_covered": cov, "n_rows": it["n_rows"], "full": page and cov == it["n_rows"],
              "op": it["rec"]["gold_predicate"]["op"]}
    assert P[q]["bundle_id"] == rows.AGG_BUNDLE
lib.save_cache()
print("ranker top-50 == prompt chunks:", same, "/", len(agg), "| full", sum(v["full"] for v in per.values()),
      "page", sum(v["page"] for v in per.values()), "rows-only", sum(v["rows_covered"] == v["n_rows"] for v in per.values()))
with open(lib.DS / "results" / "retrieval_v0.9.4" / "k50_coverage_agg81.jsonl", "w") as f:
    for q in sorted(per):
        f.write(json.dumps({"qa_id": q, **per[q]}) + "\n")
