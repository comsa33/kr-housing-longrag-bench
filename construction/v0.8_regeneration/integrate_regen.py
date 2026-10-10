#!/usr/bin/env python3
"""Integrate regenerated (natural) questions back into the dataset, replacing positional-cloze items.

Reads regen_results.json (gen + verify per group). For each VERIFIED item:
  GOOD       -> use gen item
  NEEDS_WORK -> use corrected_question/corrected_answer if both present, else FLAG
  BAD        -> FLAG (removal candidate)
  (no verify yet) -> SKIP (not ready)

Per integrated item updates (invariant fields kept identical across v0.5 & v0.6):
  question, answer, answer_type, evidence(locator=quote), evaluation(number->exact_numbers else contains_all),
  question_style='real_user', rewrite_rationale.
Files: canonical + dev + test_public (real answer) ; test_hidden public (question only, answer stays masked) ;
  v0.5 source (invariant fields identical) ; internal hidden answers (real answer).

DRY-RUN by default. Pass --apply to write.
"""
import json, re, os, sys, collections

ROOT = "<repo>"
TC = f"{ROOT}/workspace_local/audit/triage_compare"
MASK = "[HELD OUT]"
APPLY = "--apply" in sys.argv

# files where REAL answer/evaluation may be written:
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


# ---- build final map: integrate items gpt-5.4 verified OK ----
G = json.load(open(f"{TC}/regen_results.json", encoding="utf-8"))
genmap = {}
for grp in G:
    for it in (grp.get("gen") or []):
        genmap[it["qa_id"]] = it
gpt = {r["qa_id"]: r for r in json.load(open(f"{TC}/regen_verify_gpt5.json", encoding="utf-8"))}

final = {}        # qa_id -> {question, answer, answer_type, quote}
flagged = collections.defaultdict(list)
for qid, gi in genmap.items():
    v = gpt.get(qid)
    if not v:
        flagged["no_verify"].append(qid); continue
    if v.get("verdict") == "OK":
        final[qid] = {"question": gi["new_question"], "answer": gi["new_answer"],
                      "answer_type": gi["answer_type"], "quote": gi.get("evidence_quote", "")}
    else:
        flagged[v.get("issue") or "flag"].append(qid)

not_verified = flagged.get("no_verify", [])
print(f"생성 {len(genmap)} | gpt-5.4 OK(통합대상) {len(final)} | "
      f"FLAG(보류) {sum(len(v) for k, v in flagged.items() if k != 'no_verify')}")
print(f"  flagged: { {k: len(v) for k, v in flagged.items()} }")
if not APPLY:
    print("\n[DRY-RUN] 파일 미수정. 적용하려면 --apply")


def patch_record(r, *, real):
    qid = r.get("qa_id")
    f = final.get(qid)
    if not f:
        return False
    r["question"] = f["question"]                      # question: 모든 파일
    if real and r.get("answer") != MASK:
        r["answer"] = f["answer"]
        r["answer_type"] = f["answer_type"]
        r["evaluation"] = make_eval(f["answer"], f["answer_type"])
        sid = (r.get("source_ids") or ["?"])[0]
        r["evidence"] = [{"source_id": sid, "locator": (f["quote"] or "")[:200]}]
        r["question_style"] = "real_user"
        r["original_question"] = f["question"]
        r["rewrite_rationale"] = "regenerated from positional-cloze to natural grounded question (v0.8)"
    return True


def process(fp, *, real):
    if not os.path.exists(fp):
        return 0
    recs = [json.loads(l) for l in open(fp, encoding="utf-8") if l.strip()]
    n = sum(1 for r in recs if patch_record(r, real=real))
    if APPLY and n:
        with open(fp, "w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return n


print("\n파일별 변경 항목 수:")
for fp in REAL_FILES:
    print(f"  {os.path.basename(fp):42} {process(fp, real=True)}")
print(f"  {os.path.basename(HIDDEN_PUB):42} {process(HIDDEN_PUB, real=False)} (question만)")
if os.path.exists(HIDDEN_ANS):
    print(f"  hidden_answers(internal){'':18} {process(HIDDEN_ANS, real=True)}")

# flagged 목록 저장
json.dump({"flagged": dict(flagged), "not_verified": not_verified},
          open(f"{TC}/regen_flagged.json", "w"), ensure_ascii=False, indent=1)
print(f"\nflagged/미검증 목록 → regen_flagged.json")
