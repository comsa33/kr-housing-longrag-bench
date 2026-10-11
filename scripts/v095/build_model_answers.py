"""Build results/predictions_v0.9.5/ (model answers) from the judge inputs kept on the build machine.

Build-machine only: the judge-input files live under workspace_local/archive_scratchpads/ (not released).
Each released answer is the exact string the judge scored, except for the masking documented in
results/predictions_v0.9.5/README.md. No model calls.
Usage (from the repo root): python3 scripts/v095/build_model_answers.py
"""
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WS = os.environ.get("KRH_WORKSPACE", os.path.join(ROOT, "workspace_local"))
import json, re, os, glob, csv, collections
WT=ROOT + "/"
R=WT+"results/"; OUT=R+"predictions_v0.9.5/"
B=WS + "/"
BUN=B+"processed/bundles-v06/"; VAR=B+"audit/baselines/run_open/variance/"
L=lambda p:[json.loads(l) for l in open(p,encoding="utf-8") if l.strip()]
G={}
for sp in ("dev","test_public"):
    for d in L(WT+f"data/qa_v0.6_{sp}.jsonl"): G[d["qa_id"]]=d
P=json.load(open(os.path.join(WS, "v095_preds_all.json")))
QWEN={"cb_qwen3.5-cloud_tp","fc_qwen3.5-cloud_tp","jf386_qwen3.5_dense","rag_qwen3.5-cloud_tp"}
exec(open(os.path.join(os.path.dirname(__file__), "map_to_verdicts.py")).read().split("G=collections.defaultdict")[0].split("P=json.load")[1].split("\n",1)[1])  # defines L, vfile
# manifests for model / regime
MAN={}
for r in csv.DictReader(open(R+"judge_verdicts/MANIFEST.csv")): MAN[("judge_verdicts_v0.9.2",r["tag"])]=(r["model"],r["regime"],r["item_set"])
for v in ("v0.9.3","v0.9.4"):
    for r in csv.DictReader(open(R+f"judge_verdicts_{v}/MANIFEST.csv")):
        if r["judge"]=="claude-sonnet-5-5": MAN[(f"judge_verdicts_{v}",r["tag"])]=(r["model"],r["regime"],r["split"])
MAN[("judge_verdicts_v0.9.4","k50dense_minimax-m3")]=("minimax-m3","dense k=50 (reasoning on; reported)","test_public")
groups=collections.OrderedDict()
for p in P:
    if p["tag"] in QWEN: continue
    if p["tag"]=="human80": key=("human80","human80"); 
    else: key=vfile(p["src"],p["split"],p["tag"])
    groups.setdefault(key,[]).append(p)
# variance runs (secondary judge only)
for f in sorted(glob.glob(R+"judge_verdicts/fc_*var*_r[23].jsonl")):
    tag=os.path.basename(f)[:-6]
    groups[("variance",tag)]=[{"qa_id":r["qa_id"],"split":"test_public","prediction":(r.get("prediction") or "").strip(),"tag":tag} for r in L(VAR+tag+".jsonl")]
# bundles
allb=""; bc={}
for fn in glob.glob(BUN+"*.txt"):
    t=open(fn,encoding="utf-8").read(); bc[os.path.basename(fn)[:-4]]=t; allb+=t+"\n"
K=20
HC={}
def shingles(bid):
    if bid not in HC:
        bst=re.sub(r"\s+","",bc.get(bid,"")); HC.clear(); HC[bid]={hash(bst[j:j+K]) for j in range(len(bst)-K+1)} if bst else set()
    return HC[bid]
def mask_overlap(s,bid):
    idx=[i for i,c in enumerate(s) if not c.isspace()]; st="".join(s[i] for i in idx)
    H=shingles(bid)
    spans=[];run=-1
    for i in range(len(st)-K+1):
        if hash(st[i:i+K]) in H:
            if run<0: run=i
        else:
            if run>=0: spans.append((run,i-1+K)); run=-1
    if run>=0: spans.append((run,len(st)))
    spans=[(a,b) for a,b in spans if b-a>=200]
    if not spans: return s,0,0
    out=s; n=0
    for a,b in reversed(spans):
        oa,ob=idx[a],idx[b-1]+1; seg=out[oa:ob]; n+=len(seg)
        out=out[:oa]+f"[source text omitted, {len(seg)} chars]"+out[ob:]
    return out,len(spans),n
PH=re.compile(r"(?<!\d)(?:0\d{1,2}|1\d{3})[-.)\s]\d{3,4}[-.\s]\d{4}(?!\d)")
stats=collections.Counter(); masked_phone=set(); maskrec=[]
def labels(dirn,tag,judge):
    if dirn in ("human80","variance") and judge=="claude-sonnet-5-5" and dirn=="variance": return {}
    f=R+(f"{dirn}/{judge}/{tag}.jsonl" if dirn.startswith("judge_verdicts_") else "")
    if dirn=="variance" and judge=="gpt-4.1-mini": f=R+f"judge_verdicts/{tag}.jsonl"
    if dirn=="human80": f=R+"judge_verdicts_v0.9.2/human80_claude-sonnet-5-5.jsonl" if judge=="claude-sonnet-5-5" else R+"judge_verdicts/panel_gpt-4.1-mini_human80.jsonl"
    if not f or not os.path.exists(f): return {}
    out={}
    for r in L(f): out[r["qa_id"]]=r.get("judge_correct", r.get("claude_sonnet_5_5"))
    return out
os.makedirs(OUT,exist_ok=True)
# global masking pass sorted by bundle (one shingle set in memory at a time)
allrecs=[(k,p) for k,ps in groups.items() for p in ps]
allrecs.sort(key=lambda kp:str(G[kp[1]["qa_id"].split("__")[0]]["bundle_id"]))
for (k,p) in allrecs:
    s2,ns,nc=mask_overlap(p["prediction"],str(G[p["qa_id"].split("__")[0]]["bundle_id"]))
    p["_m"]=(s2,ns,nc)
man=[]; rep=[]
SUB={"judge_verdicts_v0.9.2":"v0.9.2","judge_verdicts_v0.9.3":"v0.9.3","judge_verdicts_v0.9.4":"v0.9.4","variance":"variance","human80":"human80"}
for (dirn,tag),ps in groups.items():
    sub=SUB[dirn]; os.makedirs(OUT+sub,exist_ok=True)
    pri=labels(dirn,tag,"claude-sonnet-5-5"); sec=labels(dirn,tag,"gpt-4.1-mini")
    if dirn=="human80": model=regime="(see qa_id)"
    elif dirn=="variance": model="glm-5.2" if "glm" in tag else "minimax-m3"; regime="fc (run %s)"%tag[-2:]
    else: model,regime,_=MAN.get((dirn,tag),("?","?","?"))
    vq=set(pri) if dirn!="variance" else set(sec)
    q=[p["qa_id"] for p in ps]
    rep.append((sub,tag,len(ps),len(vq),set(q)==vq if dirn!="v0.9.2" else set(q)==vq, len(q)==len(set(q))))
    with open(OUT+f"{sub}/{tag}.jsonl","w",encoding="utf-8") as fo:
        for p in sorted(ps,key=lambda x:(str(G[x["qa_id"].split("__")[0]]["bundle_id"]),x.get("split",""),x["qa_id"])):
            s=p["prediction"]
            base=p["qa_id"].split("__")[0]
            s2,ns,nc=p["_m"]
            if ns: stats["overlap_spans"]+=ns; stats["overlap_chars"]+=nc; maskrec.append((sub,tag,p["qa_id"],nc))
            for m in set(PH.findall(s2)):
                if m not in allb: s2=s2.replace(m,"[phone number omitted]"); masked_phone.add(m); stats["phone_mask_items"]+=1
            rec={"qa_id":p["qa_id"],"split":p.get("split","test_public"),"model":model,"setting":regime,"prediction":s2,
                 "judge_label":pri.get(p["qa_id"]),"judge_label_secondary":sec.get(p["qa_id"])}
            fo.write(json.dumps(rec,ensure_ascii=False)+"\n"); stats["records"]+=1
    vfile_rel={"variance":f"judge_verdicts/{tag}.jsonl","human80":"judge_verdicts_v0.9.2/human80_claude-sonnet-5-5.jsonl"}.get(dirn,f"{dirn}/{{claude-sonnet-5-5,gpt-4.1-mini}}/{tag}.jsonl")
    man.append((f"{sub}/{tag}.jsonl",model,regime,len(ps),collections.Counter(p.get("split","test_public") for p in ps),vfile_rel))
with open(OUT+"MANIFEST.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["file","model","setting","n","n_test_public","n_dev","verdict_file"])
    for fn,m,r,n,sp,v in man: w.writerow([fn,m,r,n,sp.get("test_public",0),sp.get("dev",0),v])
print("files",len(man),dict(stats),"distinct phones masked",len(masked_phone))
print("overlap masked:",maskrec)
bad=[r for r in rep if not r[4] or not r[5]]
print("qa-set mismatches:",bad)
json.dump(rep,open(os.path.join(WS, "v095_rep.json"),"w"))
