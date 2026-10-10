#!/usr/bin/env python3
"""Draw the stratified human-audit sample from test_public and attach evidence text.

Strata (test_public, n=389):
  llm    = cross_document_legal_reasoning (LLM-agent authored)  -> all 42
  cloze  = v0.8 cloze-regenerated items (regen_verify_targets*) -> 45
  prog   = the rest (template/script generated)                 -> 73, proportional by family
Usage: python3 -I build_audit_items.py <dataset_repo> <out.json> [--ids-only]

--ids-only writes only {id, route, family} for the drawn sample and needs no source text, so it runs
from a public clone. The full mode also attaches page, table, statute and predicate evidence from the
internal corpus (workspace_local/processed), which is not redistributed.
The cloze-regenerated ids come from workspace_local/audit/triage_compare/regen_verify_targets*.json when
present, else from the released construction/v0.8_regeneration/regen_verify_gpt5*.jsonl (same 686 ids).
"""
import glob
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
IDS_ONLY = "--ids-only" in sys.argv[3:]
SEED = 20261010
sys.path.insert(0, str(REPO / "scripts"))

P = REPO / "workspace_local" / "processed"
T = REPO / "workspace_local" / "audit" / "triage_compare"

qa = [json.loads(l) for l in open(REPO / "data/qa_v0.6_test_public.jsonl") if l.strip()]
if (T / "regen_verify_targets.json").exists():
    cloze_ids = {x["qa_id"] for f in ("regen_verify_targets.json", "regen_verify_targets_68.json")
                 for x in json.load(open(T / f))}
else:
    C = REPO / "construction" / "v0.8_regeneration"
    cloze_ids = {json.loads(l)["qa_id"] for f in ("regen_verify_gpt5.jsonl", "regen_verify_gpt5_68.jsonl")
                 for l in open(C / f) if l.strip()}


def route(q):
    if q["task_type"] == "cross_document_legal_reasoning":
        return "llm"
    if q["qa_id"] in cloze_ids:
        return "cloze"
    return "prog"


PROG_ALLOC = {"cross_source_aggregation": 32, "table_numeric_reasoning": 25, "answerability_detection": 7,
              "eligibility_reasoning": 6, "schedule_reasoning": 2, "multi_document_comparison": 1}
CLOZE_ALLOC = {"long_context_retrieval": 38, "long_distance_retrieval": 7}

rng = random.Random(SEED)
by = defaultdict(list)
for q in qa:
    by[(route(q), q["task_type"])].append(q)
for k in by:
    by[k].sort(key=lambda x: x["qa_id"])

sample = []
sample += by[("llm", "cross_document_legal_reasoning")]
for fam, n in CLOZE_ALLOC.items():
    sample += rng.sample(by[("cloze", fam)], n)
for fam, n in PROG_ALLOC.items():
    sample += rng.sample(by[("prog", fam)], n)
rng.shuffle(sample)

if IDS_ONLY:
    items = [{"id": q["qa_id"], "route": route(q), "family": q["task_type"]} for q in sample]
    OUT.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    print("items", len(items), Counter(i["route"] for i in items))
    print(Counter(i["family"] for i in items))
    sys.exit(0)

import qa_v03_common as q3  # noqa: E402  (needs the internal corpus)

# ---- evidence stores
pages = {}
for f in glob.glob(str(P / "*/*/document_pages.jsonl")):
    for l in open(f):
        r = json.loads(l)
        pages[r["page_id"]] = r
cells = defaultdict(list)
for f in glob.glob(str(P / "*/*/table_cells.jsonl")):
    for l in open(f):
        r = json.loads(l)
        cells[r["table_id"]].append(r)
law = {}
for sid in ("law-housing-supply-rule", "law-public-housing-special-act-rule", "law-public-housing-special-act",
            "law-private-rental-housing-special-act"):
    fp = P / sid / "document_pages.jsonl"
    if fp.exists():
        law[sid] = [json.loads(l) for l in open(fp)]


def norm(s):
    return re.sub(r"\s+", "", s or "")


def highlight_terms(q):
    ev = q.get("evaluation") or {}
    terms = list(ev.get("gold_terms") or []) + list(ev.get("gold_numbers") or [])
    a = (q.get("answer") or "").strip()
    if a and len(a) <= 40:
        terms.append(a)
    for e in q.get("evidence", []):
        loc = e.get("locator", "")
        if not loc.startswith(("lh-", "predicate", "주택", "공공", "민간")) and len(loc) < 200 and " " in loc:
            terms.append(loc.strip("❚ "))
    return [t for t in dict.fromkeys(t.strip() for t in terms) if len(norm(t)) >= 1]


def table_block(table_id, target_cells):
    cs = cells.get(table_id, [])
    if not cs:
        return None
    nr = max(c["row_index"] for c in cs) + 1
    nc = max(c["col_index"] for c in cs) + 1
    grid = [["" for _ in range(min(nc, 16))] for _ in range(min(nr, 30))]
    for c in cs:
        if c["row_index"] < len(grid) and c["col_index"] < len(grid[0]):
            grid[c["row_index"]][c["col_index"]] = (c["cell_text"] or "")[:120]
    tgt = []
    for cid in target_cells:
        m = re.search(r"#r(\d+)c(\d+)$", cid)
        if m:
            r, c = int(m.group(1)), int(m.group(2))
            tgt.append([r, c])
            hit = [x for x in cs if x["row_index"] == r and x["col_index"] == c]
    return {"kind": "table", "label": f"표 {table_id.split('-')[-1]} (p.{table_id.split('-p')[-1].split('-')[0]})",
            "grid": grid, "targets": tgt, "truncated": nr > 30 or nc > 16}


def law_block(sid, locator):
    m = re.search(r"제(\d+)조(의\d+)?", locator)
    if not m or sid not in law:
        return None
    label = m.group(0)
    for r in law[sid]:
        if r.get("unit_type") == "article" and (r.get("article_label") == label or
                                                 (r.get("article_label") or "").startswith(label + "(")):
            return {"kind": "text", "label": f"법령 · {locator}", "text": r["text"]}
    return None


def page_block(pid, why=""):
    r = pages.get(pid)
    if not r:
        return None
    return {"kind": "text", "label": f"공고 원문 · p.{r.get('page_no')}" + (f" · {why}" if why else ""),
            "text": r["text"]}


FIELD_KO = {"_query_area_name": "시·도", "_query_year": "분양연도", "AREA_DCD_NM": "시·도",
            "AREA_DTL_DCD_NM": "시·군·구", "BIZ_DIVN_NM": "사업구분"}
OP_KO = {"count": "건수", "avg": "평균", "sum": "합계", "min": "최솟값", "max": "최댓값", "median": "중앙값",
         "argmax": "최댓값인 행", "argmin": "최솟값인 행"}


def agg_block(pred):
    try:
        val, ids = q3.recompute(pred)
    except Exception as ex:  # keep the item reviewable even if recompute fails
        return {"kind": "pred", "label": "집계 조건", "error": str(ex), "pred": pred}
    rows = q3.select(pred)
    src = "HUG 분양이력" if pred["source"] == q3.HUG else "국토부 실거래/공시가격"
    filt = [f"{FIELD_KO.get(k, k)} = {v if not isinstance(v, dict) else v}" for k, v in pred.get("filter", {}).items()]
    keep = ["AREA_DTL_DCD_NM", "BSU_NM", "BIZ_DIVN_NM", "GNRL_SILT_HOCO", "SILT_OPEN_DT", "COLL_ANNO_APVL_DT",
            "_query_year", "_query_area_name"]
    shown = [{k: r.get(k) for k in keep if k in r} for r in rows]
    if pred.get("field"):
        for s, r in zip(shown, rows):
            s[pred["field"]] = r.get(pred["field"])
    return {"kind": "pred", "label": f"집계 조건 ({src})", "source": src, "filters": filt,
            "op": OP_KO.get(pred["op"], pred["op"]), "field": pred.get("field"), "value": val,
            "n_rows": len(ids), "rows": shown}


items = []
for q in sample:
    blocks = []
    fam = q["task_type"]
    if fam == "cross_source_aggregation":
        for pid in q["page_ids"]:
            b = page_block(pid, "1단계: 공고에서 지역 찾기")
            if b:
                blocks.append(b)
        if q.get("gold_predicate"):
            blocks.append(agg_block(q["gold_predicate"]))
    elif fam in ("table_numeric_reasoning", "eligibility_reasoning", "schedule_reasoning") and q.get("table_ids"):
        for tid in q["table_ids"]:
            b = table_block(tid, q.get("cell_ids") or [])
            if b:
                blocks.append(b)
        for pid in q["page_ids"]:
            b = page_block(pid)
            if b:
                b["collapsed"] = True
                blocks.append(b)
    else:
        for pid in q["page_ids"]:
            b = page_block(pid)
            if b:
                blocks.append(b)
    if fam == "cross_document_legal_reasoning":
        for e in q["evidence"]:
            if e["source_id"].startswith("law-"):
                b = law_block(e["source_id"], e["locator"])
                if b:
                    blocks.append(b)
    if not blocks and q.get("gold_predicate"):
        blocks.append(agg_block(q["gold_predicate"]))
    items.append({
        "id": q["qa_id"], "route": route(q), "family": fam, "question": q["question"], "answer": q["answer"],
        "locators": [e["locator"] for e in q.get("evidence", [])], "terms": highlight_terms(q),
        "blocks": blocks,
    })

OUT.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
print("items", len(items), Counter(i["route"] for i in items), "bytes", OUT.stat().st_size)
print("no-evidence", [i["id"] for i in items if not i["blocks"]])
print(Counter(i["family"] for i in items))
