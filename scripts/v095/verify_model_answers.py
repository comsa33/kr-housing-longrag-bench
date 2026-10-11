"""Build results/predictions_v0.9.5/ (model answers) from the judge inputs kept on the build machine.

Build-machine only: the judge-input files live under workspace_local/archive_scratchpads/ (not released).
Each released answer is the exact string the judge scored, except for the masking documented in
results/predictions_v0.9.5/README.md. No model calls.
Usage (from the repo root): python3 scripts/v095/build_model_answers.py
"""
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WS = os.environ.get("KRH_WORKSPACE", os.path.join(ROOT, "workspace_local"))
import json,glob,re,os,collections
WT=ROOT + "/"
O=WT+"results/predictions_v0.9.5/"
BUN=os.path.join(WS, "processed", "bundles-v06") + "/"
L=lambda p:[json.loads(l) for l in open(p,encoding="utf-8") if l.strip()]
G={}
for sp in ("dev","test_public"):
    for d in L(WT+f"data/qa_v0.6_{sp}.jsonl"): G[d["qa_id"]]=d
recs=[]
for f in sorted(glob.glob(O+"*/*.jsonl")):
    for r in L(f): r["_f"]=f[len(O):]; recs.append(r)
print("records",len(recs),"files",len({r['_f'] for r in recs}))
c=collections.Counter(r["_f"].split("/")[0] for r in recs); print(dict(c))
print("splits",collections.Counter(r["split"] for r in recs))
print("qwen present:",sum('qwen' in r['_f'] or 'qwen' in r['model'] for r in recs))
print("judge_label null (primary):",collections.Counter(r['_f'].split('/')[0] for r in recs if r['judge_label'] is None))
print("secondary null:",collections.Counter(r['_f'].split('/')[0] for r in recs if r['judge_label_secondary'] is None))
# equality vs judged strings
P=json.load(open(os.path.join(WS, "v095_preds_all.json")))
J={}
for p in P: J.setdefault(p["qa_id"],set()).add(p["prediction"])
VAR=os.path.join(WS, "audit", "baselines", "run_open", "variance") + "/"
diff=0;masked=0
for r in recs:
    if "[source text omitted" in r["prediction"] or "[phone number omitted]" in r["prediction"]: masked+=1; continue
    if r["_f"].startswith("variance/"):
        continue
    if r["prediction"] not in J.get(r["qa_id"],()): diff+=1
print("unmasked records not equal to a judged string:",diff,"masked records:",masked)
# overlap scan (stripped, 20-char shingles, longest run)
K=20; by=collections.defaultdict(list)
for i,r in enumerate(recs): by[str(G[r["qa_id"].split("__")[0]]["bundle_id"])].append(i)
mx=0; ge200=0; dist=[]
for b,ids in by.items():
    p=BUN+b+".txt"
    if not os.path.exists(p): continue
    t=re.sub(r"\s+","",open(p,encoding="utf-8").read()); H={hash(t[j:j+K]) for j in range(len(t)-K+1)}
    for i in ids:
        s=re.sub(r"\s+","",recs[i]["prediction"]); best=run=0
        for j in range(len(s)-K+1):
            if hash(s[j:j+K]) in H: run+=1; best=max(best,run)
            else: run=0
        L2=best+K-1 if best else 0; dist.append(L2); mx=max(mx,L2); ge200+=L2>=200
dist.sort(); print("overlap max",mx,">=200",ge200,"p99",dist[int(len(dist)*.99)],"n",len(dist))
allb="".join(open(f,encoding="utf-8").read() for f in glob.glob(BUN+"*.txt"))
PAT={"phone":re.compile(r"(?<!\d)(?:0\d{1,2}|1\d{3})[-.)\s]\d{3,4}[-.\s]\d{4}(?!\d)"),"mobile":re.compile(r"(?<!\d)01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)"),
 "email":re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),"rrn":re.compile(r"(?<!\d)\d{6}-[1-4]\d{6}(?!\d)"),"name_label":re.compile(r"(?:담당자|성명|이름|대표자)\s*[:：]?\s*[가-힣]{2,4}(?![가-힣])")}
for k,rx in PAT.items():
    ms=[m for r in recs for m in rx.findall(r["prediction"])]
    print(k,len(ms),"not in any bundle:",len({m for m in ms if m not in allb}))
