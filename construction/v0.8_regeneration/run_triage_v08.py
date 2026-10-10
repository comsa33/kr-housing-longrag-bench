#!/usr/bin/env python3
"""v0.8 LLM-assisted triage runner (provider: OpenAI). INTERNAL outputs only.

Two modes:
  --mode calibrate : input items have {qa_id, question, candidate_answer, evidence_text}
                     -> judge SUPPORTED / NOT_SUPPORTED (grounding). Scoreable by score_verdicts.py.
  --mode review    : input items have {qa_id, question, gold_answer, evidence_text}
                     -> judge OK / FLAG with an issue type (the real v0.8 review).

Per-item API call, temperature 0, RESUMABLE (skips qa_ids already in the .jsonl checkpoint).
Reads key from workspace_local/secrets/openai_api.key. Writes <out>.jsonl (incremental) and
<out>.json (final array) under workspace_local/audit/triage_compare/. No raw docs leave the box
beyond the cited evidence excerpts already in the targets file.

Usage:
  python3 run_triage_v08.py --mode calibrate --targets testset_shown.json --model gpt-4o
  python3 run_triage_v08.py --mode review   --targets review_targets_hirisk.json --model gpt-4o --limit 30
  python3 run_triage_v08.py --mode review   --targets review_targets_hirisk.json --model gpt-4o --resume
"""
import argparse, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
KEYFILE = os.path.join(ROOT, "workspace_local", "secrets", "openai_api.key")

CALIB_SYS = (
    "You validate Korean housing-document QA items. GROUNDING CHECK only — judge solely from the "
    "provided evidence, no outside knowledge. Read numbers and table cells carefully (OCR noise like "
    "doubled characters may appear). Reply with ONE JSON object and nothing else."
)
CALIB_USER = (
    "Work in TWO strict steps.\n"
    "STEP 1: From the EVIDENCE ONLY, find the exact value/fact the question asks for. Call it evidence_value "
    "(read table cells and numbers digit-by-digit; OCR noise like doubled chars may appear). If the evidence "
    "does not contain it, evidence_value = null.\n"
    "STEP 2: Compare evidence_value to candidate_answer. Mark SUPPORTED ONLY if evidence_value clearly matches "
    "candidate_answer as the SAME value (ignore commas/spacing/formatting). If they differ in ANY digit/word, or "
    "evidence_value is null, mark NOT_SUPPORTED. Topic overlap is NOT support — the value must match.\n"
    'Reply with ONE JSON object: {{"qa_id":"{qa_id}","verdict":"SUPPORTED|NOT_SUPPORTED","derived_answer":"<evidence_value>","reason":"<=15 words: evidence_value vs candidate>"}}\n\n'
    "# question\n{question}\n\n# candidate_answer\n{candidate_answer}\n\n# evidence\n{evidence_text}"
)
REVIEW_SYS = (
    "You are a meticulous reviewer validating Korean housing-document benchmark QA items before publication. "
    "Judge ONLY from the provided evidence (no outside knowledge); read tables/numbers carefully despite OCR noise. "
    "Reply with ONE JSON object and nothing else."
)
REVIEW_USER = (
    "Validate this benchmark QA item in STRICT steps.\n"
    "STEP 1: From the EVIDENCE ONLY, independently derive the answer to the question (read tables/numbers "
    "digit-by-digit; OCR noise like doubled chars may appear). Call it evidence_value (null if the evidence "
    "does not contain it).\n"
    "STEP 2: Compare evidence_value to gold_answer. If they differ in any digit/fact -> issue=wrong_answer. "
    "If evidence_value is null -> issue=weak_grounding.\n"
    "STEP 3: Judge the QUESTION itself: ambiguous/under-specified -> ambiguous_question; unnatural, templated, "
    "or cloze-like phrasing a real user would not ask -> unrealistic_question.\n"
    "Verdict OK only if gold matches the evidence AND the question is clear and natural; else FLAG with the "
    "single most important issue.\n"
    'Reply ONE JSON object: {{"qa_id":"{qa_id}","verdict":"OK|FLAG","issue":null|"wrong_answer"|"weak_grounding"|"ambiguous_question"|"unrealistic_question","derived_answer":"<evidence_value>","reason":"<=20 words"}}\n\n'
    "# question\n{question}\n\n# gold_answer\n{gold_answer}\n\n# evidence\n{evidence_text}"
)


def load_key():
    return open(KEYFILE, encoding="utf-8").read().strip()


def parse_json_obj(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["calibrate", "review"], required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--sleep", type=float, default=0.3)
    a = ap.parse_args()

    targets_path = a.targets if os.path.isabs(a.targets) else os.path.join(HERE, a.targets)
    items = json.load(open(targets_path, encoding="utf-8"))
    if a.mode == "review":
        items = [x for x in items if x.get("evidence_text") and x.get("has_evidence", True)]
    if a.limit:
        items = items[:a.limit]

    base = a.out or f"verdicts_{a.model.replace('/', '_')}_{a.mode}"
    jsonl_path = os.path.join(HERE, base + ".jsonl")
    json_path = os.path.join(HERE, base + ".json")

    done = {}
    if a.resume and os.path.exists(jsonl_path):
        for l in open(jsonl_path, encoding="utf-8"):
            if l.strip():
                try:
                    o = json.loads(l); done[o["qa_id"]] = o
                except Exception:
                    pass
        print(f"[resume] {len(done)} already done")

    try:
        from openai import OpenAI
    except Exception:
        print("openai SDK 필요: pip install openai", file=sys.stderr); sys.exit(2)
    client = OpenAI(api_key=load_key())

    sys_msg = CALIB_SYS if a.mode == "calibrate" else REVIEW_SYS
    tmpl = CALIB_USER if a.mode == "calibrate" else REVIEW_USER

    out_f = open(jsonl_path, "a", encoding="utf-8")
    results = list(done.values())
    n_call = 0
    for it in items:
        if it["qa_id"] in done:
            continue
        user = tmpl.format(qa_id=it["qa_id"], question=it.get("question", ""),
                           candidate_answer=it.get("candidate_answer", ""),
                           gold_answer=it.get("gold_answer", ""),
                           evidence_text=(it.get("evidence_text", "") or "")[:24000])
        try:
            kw = {"model": a.model,
                  "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": user}]}
            if re.match(r"(gpt-5|o[1-9])", a.model):   # reasoning models: no temperature, max_completion_tokens
                kw["max_completion_tokens"] = 2000
            else:
                kw["temperature"] = 0
                kw["max_tokens"] = 300
            resp = client.chat.completions.create(**kw)
            txt = resp.choices[0].message.content
        except Exception as e:
            print(f"  [err] {it['qa_id']}: {e}", file=sys.stderr)
            txt = None
        obj = parse_json_obj(txt) or {"qa_id": it["qa_id"], "verdict": "PARSE_FAIL", "reason": str(txt)[:80]}
        obj["qa_id"] = it["qa_id"]
        obj.setdefault("task_type", it.get("task_type"))
        out_f.write(json.dumps(obj, ensure_ascii=False) + "\n"); out_f.flush()
        results.append(obj); n_call += 1
        if n_call % 10 == 0:
            print(f"  ...{n_call} called")
        time.sleep(a.sleep)
    out_f.close()
    json.dump(results, open(json_path, "w"), ensure_ascii=False, indent=1)

    print(f"\n완료: {n_call} new calls, total {len(results)} -> {json_path}")
    if a.mode == "review":
        from collections import Counter
        c = Counter(r.get("verdict") for r in results)
        iss = Counter(r.get("issue") for r in results if r.get("verdict") == "FLAG")
        print("verdict:", dict(c))
        print("issues :", dict(iss))


if __name__ == "__main__":
    main()
