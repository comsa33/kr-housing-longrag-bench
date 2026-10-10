#!/usr/bin/env python3
"""Stratified v0.8 review sample over UN-REVIEWED families (the 3 high-risk families already done).

Excludes predicate-backed items (gold_predicate.op) — those are deterministically verified by
verify_qa.py. Assembles SOURCE-AWARE evidence (bundle pages + cited statute articles). Deterministic
stride sampling per family (~rate). Output: review_targets_sample.json
"""
import json, re, os, bisect, glob, collections, math

ROOT = "<repo>"
BUND, PROC = f"{ROOT}/workspace_local/processed/bundles-v06", f"{ROOT}/workspace_local/processed"
OUT = f"{ROOT}/workspace_local/audit/triage_compare"
MARKER = re.compile(r"\[[^\]\n]*\(p\.\d+\)\]"); ART = re.compile(r"제\d+조(?:의\d+)?")
PC, TC = 9000, 30000
DONE = {"cross_document_legal_reasoning", "multi_document_comparison", "eligibility_reasoning"}
RATE = {"long_context_retrieval": 0.15, "table_numeric_reasoning": 0.18, "long_distance_retrieval": 0.22,
        "schedule_reasoning": 0.30, "region_comparison": 0.35, "provider_comparison": 0.35,
        "answerability_detection": 0.12, "format_robustness": 0.18, "cross_source_aggregation": 0.10,
        "correction_notice_reasoning": 1.0}

_bc = {}
def load_bundle(bid):
    if bid in _bc: return _bc[bid]
    p = f"{BUND}/{bid}.txt"
    if not os.path.exists(p): _bc[bid] = (None, None); return None, None
    t = open(p, encoding="utf-8", errors="replace").read()
    _bc[bid] = (t, [m.start() for m in MARKER.finditer(t)]); return _bc[bid]
def page(bid, pid):
    t, st = load_bundle(bid)
    if t is None: return None
    i = t.find(pid)
    if i < 0: return None
    k = bisect.bisect_right(st, i) - 1
    return t[(st[k] if k >= 0 else i):(st[k + 1] if k + 1 < len(st) else len(t))][:PC]
STAT = {}
for f in glob.glob(f"{PROC}/law-*/chunks.jsonl"):
    for l in open(f, encoding="utf-8"):
        if not l.strip(): continue
        try: r = json.loads(l)
        except Exception: continue
        cid = r.get("chunk_id", "")
        if "::" in cid:
            sid, art = cid.split("::", 1); m = ART.search(art)
            if m: STAT[(sid, m.group(0))] = r.get("text", "")
def statute(ev):
    out = []
    for e in (ev or []):
        sid = e.get("source_id", "")
        if sid.startswith("law"):
            for art in dict.fromkeys(ART.findall(e.get("locator", ""))):
                if (sid, art) in STAT: out.append(f"[{sid} {art}]\n{STAT[(sid,art)]}")
    return out
def assemble(r):
    parts = [p for pid in (r.get("page_ids") or []) if (p := page(r.get("bundle_id"), pid))]
    parts += statute(r.get("evidence"))
    return ("\n\n----\n\n".join(parts))[:TC]

rows = [json.loads(l) for l in open(f"{ROOT}/data/qa_v0.6_realistic_candidates.jsonl", encoding="utf-8") if l.strip()]
byfam = collections.defaultdict(list)
for r in rows:
    tt = r["task_type"]
    if tt in DONE or tt not in RATE: continue
    if (r.get("gold_predicate") or {}).get("op"): continue       # predicate -> verify_qa covers it
    if r.get("split") not in ("dev", "test_public"): continue     # public answers only
    byfam[tt].append(r)

sample = []
for tt, items in byfam.items():
    items.sort(key=lambda r: r["qa_id"])
    k = max(1, round(1 / RATE[tt]))
    picked = items[::k]
    for r in picked:
        ev = assemble(r)
        if not ev or len(ev) < 120: continue
        sample.append({"qa_id": r["qa_id"], "task_type": tt, "split": r["split"],
                       "question": r["question"], "gold_answer": str(r.get("answer", "")),
                       "evidence_text": ev, "has_evidence": True})

json.dump(sample, open(f"{OUT}/review_targets_sample.json", "w"), ensure_ascii=False, indent=1)
c = collections.Counter(x["task_type"] for x in sample)
print(f"표본 {len(sample)}개 → review_targets_sample.json")
for tt in sorted(c): print(f"  {tt:30} {c[tt]:4}  (모집단 {len(byfam[tt])})")
