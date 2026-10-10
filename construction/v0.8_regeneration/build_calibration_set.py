#!/usr/bin/env python3
"""Build a CLEAN triage calibration set with COMPLETE evidence.

Fixes over the first draft:
  - extract ALL page_ids (not just the first) -> multi-doc items get every cited doc
  - take each FULL page (marker-to-next-marker, no mid-table char cap)
  - keep only "confident-correct" items: the gold value must actually appear in the
    assembled evidence (so an ok item that passes review is genuinely answerable, and
    a planted error is genuinely wrong). Items whose gold is NOT in the cited evidence
    are skipped here (they are themselves suspicious -> a separate locator-bug check).

Outputs (INTERNAL, under workspace_local/):
  testset_shown.json   - what the judge sees (no is_bad)
  testset_truth.jsonl  - ground truth (is_bad, gold)
"""
import json, re, os, bisect

ROOT = "<repo>"
BUND = f"{ROOT}/workspace_local/processed/bundles-v06"
OUT = f"{ROOT}/workspace_local/audit/triage_compare"
DEV = f"{ROOT}/data/qa_v0.6_dev.jsonl"
MARKER = re.compile(r"\[[^\]\n]*\(p\.\d+\)\]")
PER_PAGE_CAP = 9000      # generous; a normal page/table fits
TOTAL_CAP = 26000

_bundle_cache = {}


def load_bundle(bid):
    if bid in _bundle_cache:
        return _bundle_cache[bid]
    p = f"{BUND}/{bid}.txt"
    if not os.path.exists(p):
        _bundle_cache[bid] = (None, None)
        return None, None
    txt = open(p, encoding="utf-8", errors="replace").read()
    starts = [m.start() for m in MARKER.finditer(txt)]
    _bundle_cache[bid] = (txt, starts)
    return txt, starts


def page_text(bid, page_id):
    txt, starts = load_bundle(bid)
    if txt is None:
        return None
    idx = txt.find(page_id)
    if idx < 0:
        return None
    # marker start at-or-before idx; block ends at next marker start
    i = bisect.bisect_right(starts, idx) - 1
    start = starts[i] if i >= 0 else idx
    end = starts[i + 1] if i + 1 < len(starts) else len(txt)
    return txt[start:end][:PER_PAGE_CAP]


def assemble_evidence(rec):
    pids = rec.get("page_ids") or []
    parts = []
    for pid in pids:
        t = page_text(rec.get("bundle_id"), pid)
        if t:
            parts.append(t)
    ev = "\n\n----\n\n".join(parts)
    return ev[:TOTAL_CAP]


def norm(s):
    return re.sub(r"[,\s]", "", str(s))


def gold_in_evidence(gold, ev):
    """Heuristic: the gold's most distinctive token appears in evidence (comma/space-insensitive for numbers)."""
    nums = re.findall(r"\d[\d,]{2,}", gold)        # multi-digit numbers
    if nums:
        ne = norm(ev)
        return any(norm(n) in ne for n in nums)
    # text answer: check a distinctive >=4-char chunk
    toks = [t for t in re.split(r"[\s,·()]+", gold) if len(t) >= 4]
    return any(t in ev for t in toks[:3]) if toks else False


def mutate(ans):
    """Plant a clearly-wrong value by changing the first salient number."""
    m = re.search(r"\d[\d,]*", ans)
    if not m:
        return None
    raw = m.group()
    n = int(raw.replace(",", ""))
    new = n + (13 if n > 5 else 3)
    new_s = f"{new:,}" if "," in raw else str(new)
    cand = ans[:m.start()] + new_s + ans[m.end():]
    return cand if cand != ans else None


TARGETS = {
    "long_context_retrieval": 8,
    "table_numeric_reasoning": 8,
    "multi_document_comparison": 4,
    "cross_document_legal_reasoning": 3,
    "eligibility_reasoning": 3,
    "schedule_reasoning": 2,
    "region_comparison": 2,
}

got = {k: 0 for k in TARGETS}
picked = []
skipped_no_gold = 0
for l in open(DEV, encoding="utf-8"):
    if not l.strip():
        continue
    r = json.loads(l)
    tt = r["task_type"]
    if tt not in TARGETS or got[tt] >= TARGETS[tt]:
        continue
    if (r.get("gold_predicate") or {}).get("op"):
        continue
    if not r.get("bundle_id") or not r.get("page_ids"):
        continue
    if not re.search(r"\d", str(r.get("answer", ""))):
        continue
    ev = assemble_evidence(r)
    if not ev or len(ev) < 120:
        continue
    if not gold_in_evidence(str(r["answer"]), ev):
        skipped_no_gold += 1
        continue                      # not confident-correct -> exclude from calibration
    picked.append((r, ev))
    got[tt] += 1
    if sum(got.values()) >= sum(TARGETS.values()):
        break

shown, truth = [], []
for idx, (r, ev) in enumerate(picked):
    is_bad = (idx % 2 == 1)
    cand = mutate(str(r["answer"])) if is_bad else str(r["answer"])
    if is_bad and not cand:
        is_bad, cand = False, str(r["answer"])
    shown.append({"qa_id": r["qa_id"], "task_type": r["task_type"],
                  "question": r["question"], "candidate_answer": cand, "evidence_text": ev})
    truth.append({"qa_id": r["qa_id"], "task_type": r["task_type"], "gold": str(r["answer"]),
                  "candidate_answer": cand, "is_bad": is_bad, "ev_len": len(ev)})

os.makedirs(OUT, exist_ok=True)
json.dump(shown, open(f"{OUT}/testset_shown.json", "w"), ensure_ascii=False, indent=1)
with open(f"{OUT}/testset_truth.jsonl", "w", encoding="utf-8") as f:
    for t in truth:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")

print(f"채택 {len(shown)}개 (gold가 근거에 없어 제외 {skipped_no_gold}개)\n")
print(f"task_type별: " + ", ".join(f"{k}:{v}" for k, v in got.items() if v))
print(f"\n{'qa_id':22}{'task_type':26}{'gold':12}{'shown':12}{'mark':6}ev_len")
for t in truth:
    print(f"{t['qa_id']:22}{t['task_type']:26}{t['gold'][:11]:12}{t['candidate_answer'][:11]:12}"
          f"{('BAD' if t['is_bad'] else 'ok'):6}{t['ev_len']}")
print(f"\nBAD {sum(x['is_bad'] for x in truth)} / ok {sum(not x['is_bad'] for x in truth)}")
