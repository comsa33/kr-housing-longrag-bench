#!/usr/bin/env python3
"""Build data/errata_v0.9.2.csv (no API calls).

Rows: the 29 test_public items confirmed as errors by the three-annotator review
(results/human_review_v0.9.2/adjudication.jsonl, final_error=yes) with their gold_fixes.json status,
then the dev items auto-flagged by detect.py (primary flags; unverified, still evaluated).

    python3 scripts/v092/detect.py data/qa_v0.6_dev.jsonl --out-primary DEV_FLAGS.jsonl
    python3 scripts/v092/build_errata.py DEV_FLAGS.jsonl [--out data/errata_v0.9.2.csv]
"""
import argparse, json, csv, collections
from pathlib import Path
_ap = argparse.ArgumentParser(); _ap.add_argument('dev_flags'); _ap.add_argument('--out')
_a = _ap.parse_args()
W = str(Path(__file__).resolve().parents[2])
OUT = _a.out or f'{W}/data/errata_v0.9.2.csv'
G=json.load(open(f'{W}/data/v0.9.2/gold_fixes.json'))
tp={json.loads(l)['qa_id']:json.loads(l) for l in open(f'{W}/data/qa_v0.6_test_public.jsonl')}
dv={json.loads(l)['qa_id']:json.loads(l) for l in open(f'{W}/data/qa_v0.6_dev.jsonl')}
adj=[r for r in (json.loads(l) for l in open(f'{W}/results/human_review_v0.9.2/adjudication.jsonl',encoding='utf-8')) if r['final_error']=='yes']
assert len(adj)==29
# type + short English paraphrase of the adjudication note (author's final_note)
T={}
for q in ['0869','0870','0871','0872','0873','0874']:
    T[q]=('dual_row_gold','Table lists a single-income row and a dual-income (both spouses earning) row under this category; question does not say which, gold held only the first. Both accepted.')
for q in ['0772','0773','0774','0775','0776','0777','0826','0827','0828','0829','0830','0831']:
    T[q]=('dual_row_gold','Category has a 130% row and a dual-income 140% row, so the asked row x household-size cell has two values; gold held only the 130% value. Both accepted.')
T['0563']=('dual_row_gold','Source states 130% with a separate 200% threshold for dual-income couples; question does not separate the two, gold held only 130%. Both accepted.')
T['0895']=('multiple_schedules',"'신청일시' is a column header covering three applicant groups (pre-subscription winners, special supply, general supply); gold held only the special-supply date. All three accepted.")
T['0896']=('multiple_schedules',"'신혼희망타운' groups two applicant rows (pre-subscription winners; newlyweds etc.) with different dates; gold held only the first. Both accepted.")
T['0897']=('multiple_schedules',"'신청일시' is a column header with two schedules (pre-subscription winners; newlyweds etc.); gold held only the second. Both accepted.")
for q in ['0994','0995']:
    T[q]=('ill_posed_header_parse',"'110%' is a cell value of the first-renewal column, not a row label (header misparse); the question is ill-posed. Value 120% matches the source. Excluded.")
for q in ['1125','1132']:
    T[q]=('ill_posed_header_parse',"First data value '110%' was parsed as a header, giving an ill-posed question; 120% matches the source but the question does not stand. Excluded.")
T['0568']=('wrong_gold','Gold 11.07 is the winner-announcement date; general-supply (lottery) applications run 10.28-10.29. Gold replaced.')
T['1419']=('scope_mismatch','24 units of 20 m2 is the whole-complex composition; this notice supplies no 20 m2 units. Both readings accepted.')
T['1369']=('unspecified_type','Renewal limit depends on the supply type (4 times/8 years for newlywed-newborn II, 1 time/2 years for the other type), which the question does not name. Excluded.')
assert set(T)=={r['qa_id'][-4:] for r in adj}, set(T)^{r['qa_id'][-4:] for r in adj}
cols=['qa_id','split','task_type','errata_type','v0.9.2_status','old_answer','new_answer_or_accepted','source','note']
rows=[]
for r in sorted(adj,key=lambda r:r['qa_id']):
    q=r['qa_id']; it=tp[q]; et,note=T[q[-4:]]
    if q in G['accept_any']: st='gold_accept_any'; new=' | '.join(G['accept_any'][q])
    elif q in G['replace']: st='gold_replaced'; new=G['replace'][q]
    elif q in G['exclude_from_evaluation']: st='excluded_from_evaluation'; new=''
    else: raise SystemExit('not in gold_fixes: '+q)
    rows.append(dict(qa_id=q,split=it['split'],task_type=it['task_type'],errata_type=et,**{'v0.9.2_status':st},old_answer=it['answer'],
                     new_answer_or_accepted=new,source='human_review_v0.9.2',note=note))
PT={'P1_dual_row':'dual_row_gold','P2_multi_schedule':'multiple_schedules','P3_header_misparse':'ill_posed_header_parse'}
PN={'P1_dual_row':'Auto-flag: the target row is followed by a dual-income continuation row with a second value in the same column (same pattern as test 0772-0777). Not human-reviewed.',
    'P2_multi_schedule':'Auto-flag: the target column holds more than one schedule under the same header (same pattern as test 0895-0897). Not human-reviewed.',
    'P3_header_misparse':'Auto-flag: the row label named in the question is a cell value from a header-misparsed table (same pattern as test 0994/0995). Not human-reviewed.'}
fl=collections.OrderedDict()
for l in open(_a.dev_flags, encoding='utf-8'):
    f=json.loads(l); fl.setdefault(f['qa_id'],[])
    if f['pattern'] not in fl[f['qa_id']]: fl[f['qa_id']].append(f['pattern'])
for q,ps in sorted(fl.items()):
    it=dv[q]
    rows.append(dict(qa_id=q,split=it['split'],task_type=it['task_type'],errata_type=';'.join(PT[p] for p in ps),**{'v0.9.2_status':'unverified_flag_still_evaluated'},
                     old_answer=it['answer'],new_answer_or_accepted='',source='auto_flag_unverified',note=' '.join(PN[p] for p in ps)))
with open(OUT,'w',newline='',encoding='utf-8') as fo:
    w=csv.DictWriter(fo,fieldnames=cols); w.writeheader(); w.writerows(rows)
c=collections.Counter((r['source'],r['errata_type'],r['v0.9.2_status']) for r in rows)
for k,v in sorted(c.items()): print(v,k)
print('total',len(rows))
