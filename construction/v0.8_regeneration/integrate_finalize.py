#!/usr/bin/env python3
"""Finalize v0.8 (a): integrate the 68 regenerated items (gpt-5.4 OK) + fix 0910 + remove 13 broken items.
DRY-RUN by default; --apply to write. Run from repo root.
"""
import json, re, os, sys, collections

ROOT = "<repo>"
TC = f"{ROOT}/workspace_local/audit/triage_compare"
MASK = "[HELD OUT]"
APPLY = "--apply" in sys.argv
REAL_FILES = [f"{ROOT}/data/qa_v0.6_realistic_candidates.jsonl", f"{ROOT}/data/qa_v0.6_dev.jsonl",
              f"{ROOT}/data/qa_v0.6_test_public.jsonl", f"{ROOT}/data/qa_v0.5_candidates.jsonl"]
HIDDEN_PUB = f"{ROOT}/data/qa_v0.6_test_hidden_questions.jsonl"
HIDDEN_ANS = f"{ROOT}/workspace_local/audit/qa_v0.6_test_hidden_answers.jsonl"


def make_eval(answer, atype):
    if atype == "number":
        nums = [n.strip(",.") for n in re.findall(r"\d[\d,\.]*", answer)]
        return {"metric": "exact_numbers", "gold_numbers": nums or [answer]}
    a = str(answer).strip()
    return {"metric": "contains_all", "gold_terms": [a if len(a) <= 40 else a[:40].rstrip()]}


# --- 1. 68 regen, gpt-5.4 OK ---
G68 = json.load(open(f"{TC}/regen_results_68.json", encoding="utf-8"))
genmap = {it["qa_id"]: it for g in G68 for it in (g.get("gen") or [])}
gpt = {r["qa_id"]: r for r in json.load(open(f"{TC}/regen_verify_gpt5_68.json", encoding="utf-8"))}
regen = {}
flag68 = []
for qid, gi in genmap.items():
    v = gpt.get(qid)
    if v and v.get("verdict") == "OK":
        regen[qid] = {"question": gi["new_question"], "answer": gi["new_answer"],
                      "answer_type": gi["answer_type"], "quote": gi.get("evidence_quote", "")}
    else:
        flag68.append(qid)

# --- 2. answer fix (0910) ---
answer_fix = {"krhlrb_v05_0910": ("24.10", "number")}

# --- 3. removals: planned 13 + any 68-FLAG ---
actions = json.load(open(f"{TC}/noncloze_actions.json", encoding="utf-8"))
remove = set(actions["remove"]) | set(flag68)

print(f"68 regen → OK 통합 {len(regen)} / FLAG(제거로) {len(flag68)}")
print(f"answer-fix: {list(answer_fix)} | 제거 총 {len(remove)} (계획13 + 68-FLAG {len(flag68)})")
if not APPLY:
    print("\n[DRY-RUN] --apply 로 적용")


def process(fp, *, real):
    if not os.path.exists(fp):
        return (0, 0, 0)
    recs = [json.loads(l) for l in open(fp, encoding="utf-8") if l.strip()]
    kept = []
    nreg = nfix = nrm = 0
    for r in recs:
        qid = r.get("qa_id")
        if qid in remove:
            nrm += 1
            continue
        if qid in regen:
            f = regen[qid]
            r["question"] = f["question"]
            if real and r.get("answer") != MASK:
                r["answer"] = f["answer"]; r["answer_type"] = f["answer_type"]
                r["evaluation"] = make_eval(f["answer"], f["answer_type"])
                r["evidence"] = [{"source_id": (r.get("source_ids") or ["?"])[0], "locator": (f["quote"] or "")[:200]}]
                r["question_style"] = "real_user"
                r["original_question"] = f["question"]
                r["rewrite_rationale"] = "regenerated from positional-cloze to natural grounded question (v0.8)"
            nreg += 1
        elif qid in answer_fix and real and r.get("answer") != MASK:
            ans, at = answer_fix[qid]
            r["answer"] = ans; r["answer_type"] = at; r["evaluation"] = make_eval(ans, at)
            nfix += 1
        kept.append(r)
    if APPLY and (nreg or nfix or nrm):
        with open(fp, "w", encoding="utf-8") as fh:
            for r in kept:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return (nreg, nfix, nrm)


print("\n파일별 (regen, fix, remove):")
for fp in REAL_FILES:
    print(f"  {os.path.basename(fp):40} {process(fp, real=True)}")
print(f"  {os.path.basename(HIDDEN_PUB):40} {process(HIDDEN_PUB, real=False)}")
if os.path.exists(HIDDEN_ANS):
    print(f"  hidden_answers(internal){'':16} {process(HIDDEN_ANS, real=True)}")
