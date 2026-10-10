#!/usr/bin/env python3
"""v0.8 fix: 항동(sh-196920) location mislabel 서울특별시 -> 구로구 (source-grounded: the
announcement states '서울특별시 구로구 연동로 245' / '구로구 항동 100-13').

A) district-level comparison answers where 항동's part == '서울특별시'  -> answer + gold_terms
B) all 항동 items with region_sigungu == '서울특별시'                  -> region_sigungu (metadata)

Applies to canonical + dev + test_public + test_hidden (answer/gold only when NOT masked) and the
internal hidden-answers file if present. Province-level uses (cross_source_aggregation,
provider_comparison) are NOT in DISTRICT_FAMILIES, so they are left untouched. Run from repo root.
"""
import json, os

ROOT = "<repo>"
FILES = [f"{ROOT}/data/qa_v0.6_realistic_candidates.jsonl",
         f"{ROOT}/data/qa_v0.6_dev.jsonl",
         f"{ROOT}/data/qa_v0.6_test_public.jsonl",
         f"{ROOT}/data/qa_v0.6_test_hidden_questions.jsonl"]
HIDDEN_ANS = f"{ROOT}/workspace_local/audit/qa_v0.6_test_hidden_answers.jsonl"
DISTRICT_FAMILIES = {"multi_document_comparison", "region_comparison"}
MASK = "[HELD OUT]"


def is_hd(r):
    return any("196920" in str(a) for a in (r.get("announcement_ids") or []))

def hd_index(r):
    for i, a in enumerate(r.get("announcement_ids") or []):
        if "196920" in str(a):
            return i
    return -1

# Build the A-fix map from canonical (authoritative real answers)
canon = [json.loads(l) for l in open(FILES[0], encoding="utf-8") if l.strip()]
A_fix = {}   # qa_id -> (new_answer, new_gold_terms)
for r in canon:
    if r["task_type"] not in DISTRICT_FAMILIES or not is_hd(r):
        continue
    i = hd_index(r)
    parts = [p.strip() for p in str(r.get("answer", "")).split("/")]
    if i < 0 or i >= len(parts) or parts[i] != "서울특별시":
        continue
    parts[i] = "구로구"
    new_ans = " / ".join(parts)
    gt = (r.get("evaluation") or {}).get("gold_terms") or []
    new_gt = ["구로구" if x == "서울특별시" else x for x in gt]
    A_fix[r["qa_id"]] = (new_ans, new_gt)

print(f"A 답수정 대상 {len(A_fix)}개: {sorted(A_fix)}")

def patch_record(r, *, allow_answer):
    changed = []
    qid = r.get("qa_id")
    if qid in A_fix and allow_answer and str(r.get("answer", "")) != MASK:
        na, ngt = A_fix[qid]
        if r.get("answer") != na:
            r["answer"] = na; changed.append("answer")
        ev = r.get("evaluation")
        if isinstance(ev, dict) and ev.get("gold_terms") is not None and ev.get("gold_terms") != ngt:
            ev["gold_terms"] = ngt; changed.append("gold_terms")
    # B: metadata region_sigungu (never masked)
    if is_hd(r) and r.get("region_sigungu") == "서울특별시":
        r["region_sigungu"] = "구로구"; changed.append("region_sigungu")
    return changed

tot = {"answer": 0, "gold_terms": 0, "region_sigungu": 0}
for fp in FILES:
    if not os.path.exists(fp):
        continue
    recs = [json.loads(l) for l in open(fp, encoding="utf-8") if l.strip()]
    n = 0
    for r in recs:
        for c in patch_record(r, allow_answer=True):
            tot[c] += 1; n += 1
    with open(fp, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {os.path.basename(fp):40} {n} 필드 변경")

# internal hidden answers file (real answers for hidden split)
if os.path.exists(HIDDEN_ANS):
    recs = [json.loads(l) for l in open(HIDDEN_ANS, encoding="utf-8") if l.strip()]
    n = 0
    for r in recs:
        qid = r.get("qa_id")
        if qid in A_fix:
            na, ngt = A_fix[qid]
            if r.get("answer") not in (None, na):
                r["answer"] = na; n += 1
            ev = r.get("evaluation")
            if isinstance(ev, dict) and ev.get("gold_terms") is not None:
                ev["gold_terms"] = ngt; n += 1
    with open(HIDDEN_ANS, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  (internal) hidden_answers {n} 변경")
else:
    print("  (internal hidden-answers 파일 없음 — 해당 split에 A항목 없으면 무관)")

print("\n총 변경:", tot)
