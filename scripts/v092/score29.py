#!/usr/bin/env python3
"""Scores on the 24 gold-fixed and 5 excluded test_public items, per core run (no API calls).

Compares v0.9.1 gold + gpt-4.1-mini verdicts (results/judge_verdicts) with v0.9.2 gold under the
Claude and gpt-4.1-mini judges (results/judge_verdicts_v0.9.2). Prints a markdown table.

    python3 scripts/v092/score29.py
"""
import json, os, sys
from pathlib import Path
W = str(Path(__file__).resolve().parents[2])
G=json.load(open(f'{W}/data/v0.9.2/gold_fixes.json'))
FIX=list(G['accept_any'])+list(G['replace']); EXC=list(G['exclude_from_evaluation'])
assert len(FIX)==24 and len(EXC)==5
CD=f'{W}/results/judge_verdicts_v0.9.2/claude-sonnet-5-5'; GD=f'{W}/results/judge_verdicts_v0.9.2/gpt-4.1-mini'; OD=f'{W}/results/judge_verdicts'
tags=sorted(t[:-6] for t in os.listdir(CD) if t.endswith('.jsonl') and '512kexp' not in t and 'fixed' not in t)
assert len(tags)==28, tags
def load(p):
    d={}
    for l in open(p):
        r=json.loads(l); d[r['qa_id']]=r['judge_correct']
    return d
def mr(t):
    m={'g55fc':('gpt-5.5','fc')}
    if t in m: return m[t]
    if t.startswith('jf386_'): _,mo,_r=t.split('_'); return mo,'dense'
    if t.endswith('_tp'):
        r,mo=t.split('_',1); mo=mo.replace('-cloud_tp',''); return mo,{'rag':'bm25'}.get(r,r)
    mo,r=t.rsplit('_',1); return mo,{'rag':'bm25'}.get(r,r)
tp={}
for l in open(f'{W}/data/qa_v0.6_test_public.jsonl'):
    r=json.loads(l); tp[r['qa_id']]=r
rows=[]; per256=[]
for t in tags:
    mo,rg=mr(t); c=load(f'{CD}/{t}.jsonl'); g=load(f'{GD}/{t}.jsonl'); o=load(f'{OD}/{t}.jsonl')
    fx=[q for q in FIX if q in c]; missing_o=[q for q in fx if q not in o]
    ex=[q for q in EXC if q in o]
    rows.append(dict(model=mo,regime=rg,tag=t,n_fix=len(fx),old=sum(o.get(q,False) for q in fx),cl=sum(c[q] for q in fx),gp=sum(g[q] for q in fx if q in g),
                     n_exc=len(ex),exc_old=sum(o[q] for q in ex),miss_old=missing_o, exc_in_claude=[q for q in EXC if q in c]))
    if rg=='fc':
        for q in FIX+EXC:
            if tp[q].get('context_tier')=='256k' and (q in c or q in o):
                per256.append((mo,q,tp[q]['task_type'],'fixed' if q in FIX else 'excluded',o.get(q),c.get(q),g.get(q)))
order=['gpt-4.1-mini','gpt-5.4-mini','gpt-5.4-nano','gpt-5.5','minimax-m3','glm-5.2','qwen3.5']
rorder=['cb','bm25','dense','fc']
rows.sort(key=lambda r:(order.index(r['model']),rorder.index(r['regime'])))
out=['| Model | Regime | tag | n fixed | v0.9.1 gold, gpt (old) | v0.9.2 gold, Claude | v0.9.2 gold, gpt | n excl | excl: v0.9.1 gpt correct |','|---|---|---|---:|---:|---:|---:|---:|---:|']
for r in rows:
    out.append(f"| {r['model']} | {r['regime']} | {r['tag']} | {r['n_fix']} | {r['old']} | {r['cl']} | {r['gp']} | {r['n_exc']} | {r['exc_old']} |")
    if r['miss_old']: out.append(f"|  | note: missing in v0.9.1 verdicts: {r['miss_old']} |")
tot=lambda k:sum(r[k] for r in rows)
out.append(f"| **Total** | | | {tot('n_fix')} | {tot('old')} | {tot('cl')} | {tot('gp')} | {tot('n_exc')} | {tot('exc_old')} |")
out.append('')
out.append('256k-tier items among the 29, fc regime (✓ correct / ✗ wrong / — not in run):')
out.append('')
out.append('| Model | qa_id | task_type | status | v0.9.1 gpt | v0.9.2 Claude | v0.9.2 gpt |'); out.append('|---|---|---|---|---|---|---|')
f=lambda v:'—' if v is None else ('✓' if v else '✗')
for p in sorted(per256,key=lambda x:(order.index(x[0]),x[1])):
    out.append(f"| {p[0]} | {p[1][-4:]} | {p[2]} | {p[3]} | {f(p[4])} | {f(p[5])} | {f(p[6])} |")
print('\n'.join(out))
print('\nexcluded ids present in Claude verdict files (should be none):', {r['tag']:r['exc_in_claude'] for r in rows if r['exc_in_claude']})
print('256k ids among 29:', [q for q in FIX+EXC if tp[q].get('context_tier')=='256k'])
