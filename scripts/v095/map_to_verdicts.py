"""Build results/predictions_v0.9.5/ (model answers) from the judge inputs kept on the build machine.

Build-machine only: the judge-input files live under workspace_local/archive_scratchpads/ (not released).
Each released answer is the exact string the judge scored, except for the masking documented in
results/predictions_v0.9.5/README.md. No model calls.
Usage (from the repo root): python3 scripts/v095/build_model_answers.py
"""
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WS = os.environ.get("KRH_WORKSPACE", os.path.join(ROOT, "workspace_local"))
import json, os, collections
R=os.path.join(ROOT, "results") + "/"
P=json.load(open(os.path.join(WS, "v095_preds_all.json")))
L=lambda p:[json.loads(l) for l in open(p) if l.strip()]
def vfile(src,split,tag):
    if src=="v0.9.2":
        if tag=="human80": return None
        if split=="test_public": return ("judge_verdicts_v0.9.2",tag)
        return ("judge_verdicts_v0.9.2",tag)  # dev: check
    if src=="v0.9.3":
        m={"e2_glm-5.2_bm25":"thinkon_bm25_glm-5.2","e2_glm-5.2_cb":"thinkon_cb_glm-5.2","e2_glm-5.2_dense":"thinkon_dense_glm-5.2",
           "g55retry_test":"g55retry_cb_test_public","g55retry_dev":"g55retry_cb_dev"}
        if tag in m: return ("judge_verdicts_v0.9.3",m[tag])
        if tag.startswith("e1_"):
            mod,sp=tag[3:].rsplit("_",1); sp={"test":"test_public","dev":"dev"}[sp]
            return ("judge_verdicts_v0.9.3",f"cbfix_{mod}_{sp}")
        for k,n in (("e3oracle_","oracle_agg81_"),("e3region_","openregion_agg81_")):
            if tag.startswith(k): return ("judge_verdicts_v0.9.3",n+tag[len(k):])
        mdl={"haiku55":"claude-haiku-5-5","sonnet55":"claude-sonnet-5-5"}[tag.split("_")[0]]
        s=tag.split("_",1)[1]
        s={"e3oracle":"oracle_agg81","e3region":"openregion_agg81"}.get(s,s)
        return ("judge_verdicts_v0.9.3",f"{s}_{mdl}")
    if src=="v0.9.4":
        m={"k50dense_minimax-m3-thinkon":"k50dense_minimax-m3","k50dense_minimax-m3":"k50dense_minimax-m3_reasoning-absent"}
        return ("judge_verdicts_v0.9.4",m.get(tag,tag))
G=collections.defaultdict(list)
for p in P: G[(p["src"],p["split"],p["tag"])].append(p)
rows=[]
for (src,split,tag),ps in sorted(G.items()):
    vf=vfile(src,split,tag); q={p["qa_id"] for p in ps}
    if vf is None: rows.append((src,split,tag,len(ps),"-","human80")); continue
    out=[]
    for j in ("claude-sonnet-5-5","gpt-4.1-mini"):
        f=R+vf[0]+"/"+j+"/"+vf[1]+".jsonl"
        if os.path.exists(f):
            vq={r["qa_id"] for r in L(f)}
            out.append(f"{j[:6]}:{'EQ' if vq==q else ('SUB' if q<=vq else 'X')}{len(vq)}")
        else: out.append(f"{j[:6]}:none")
    rows.append((src,split,tag,len(ps),vf[1]," ".join(out)))
for r in rows: print(*r)
