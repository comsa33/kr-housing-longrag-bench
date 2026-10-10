#!/usr/bin/env python3
"""v0.8 sweep fixes (source-verified by systematic-error-sweep workflow):

ANSWER (invariant -> also patch v0.5 source):
  - jpdc 1734: '제주특별자치도 / 서귀포시' -> '제주시 / 서귀포시' (grounded: 제주시 일도이동)

region_sigungu METADATA (not invariant; canonical+splits only):
  - 항동(sh-196920): '구로구' -> '서울특별시 구로구'  (format: match the 700+ Seoul full-form convention; fixes my earlier bare-form)
  - jpdc-ildo: '제주특별자치도' -> '제주시'           (grounded)
  - 발산8단지(sh-3827): '서울특별시' -> '서울특별시 강서구'  (발산동 is uniquely in 강서구)

NOT touched (verified correct city-wide programs): ih-cheonwon (인천광역시), bmc-youth (부산광역시).
NOT touched (multi-district, no clean fix): dgdc-youth (대구광역시).
"""
import json, os
ROOT = "<repo>"
PUB = [f"{ROOT}/data/qa_v0.6_realistic_candidates.jsonl", f"{ROOT}/data/qa_v0.6_dev.jsonl",
       f"{ROOT}/data/qa_v0.6_test_public.jsonl", f"{ROOT}/data/qa_v0.6_test_hidden_questions.jsonl"]
V5 = f"{ROOT}/data/qa_v0.5_candidates.jsonl"
MASK = "[HELD OUT]"
ANS_FIX = {"krhlrb_v05_1734": ("제주시 / 서귀포시", ["제주시", "서귀포시"])}

def aid_has(r, s): return any(s in str(a) for a in (r.get("announcement_ids") or []))

def sigungu_fix(r):
    cur = r.get("region_sigungu")
    if aid_has(r, "sh-196920") and cur == "구로구": return "서울특별시 구로구"
    if aid_has(r, "jpdc-jpdc-2025-04-29-ildo") and cur == "제주특별자치도": return "제주시"
    if aid_has(r, "발산8단지") and cur == "서울특별시": return "서울특별시 강서구"
    return None

def patch(recs, *, with_answer):
    c = {"answer": 0, "gold_terms": 0, "region_sigungu": 0}
    for r in recs:
        qid = r.get("qa_id")
        if with_answer and qid in ANS_FIX and str(r.get("answer", "")) != MASK:
            na, ngt = ANS_FIX[qid]
            if r.get("answer") != na: r["answer"] = na; c["answer"] += 1
            ev = r.get("evaluation")
            if isinstance(ev, dict) and ev.get("gold_terms") is not None and ev["gold_terms"] != ngt:
                ev["gold_terms"] = ngt; c["gold_terms"] += 1
        ns = sigungu_fix(r)
        if ns and r.get("region_sigungu") != ns:
            r["region_sigungu"] = ns; c["region_sigungu"] += 1
    return c

tot = {"answer": 0, "gold_terms": 0, "region_sigungu": 0}
for fp in PUB:
    if not os.path.exists(fp): continue
    recs = [json.loads(l) for l in open(fp, encoding="utf-8") if l.strip()]
    c = patch(recs, with_answer=True)
    with open(fp, "w", encoding="utf-8") as f:
        for r in recs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for k in tot: tot[k] += c[k]
    print(f"  {os.path.basename(fp):40} {c}")

# v0.5 source: answer/evaluation invariant only (NOT region_sigungu)
recs = [json.loads(l) for l in open(V5, encoding="utf-8") if l.strip()]
n = 0
for r in recs:
    qid = r.get("qa_id")
    if qid in ANS_FIX:
        na, ngt = ANS_FIX[qid]
        if r.get("answer") != na: r["answer"] = na; n += 1
        ev = r.get("evaluation")
        if isinstance(ev, dict) and ev.get("gold_terms") is not None and ev["gold_terms"] != ngt:
            ev["gold_terms"] = ngt; n += 1
with open(V5, "w", encoding="utf-8") as f:
    for r in recs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"  qa_v0.5_candidates.jsonl (answer invariant)  {n} fields")
print("\n총:", tot)
