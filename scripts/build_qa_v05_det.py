#!/usr/bin/env python3
"""v0.5 deterministic QA over real announcement TABLE CELLS (PyMuPDF grids) + correction notices.

New realistic families, all verified by construction before emit:
  - table_numeric_reasoning (cell-grounded) : a unique (row_header × col_header) cell, answer = cell_text,
    grounded verbatim in the cited page; row/col headers also present on the page.
  - eligibility_reasoning   : supply-type / eligibility matrix cells (특별공급·일반공급·소득·자산 등).
  - schedule_reasoning      : date cells with a stage row-header (청약/계약/당첨 일정).
  - correction_notice_reasoning : announcements whose notice text marks a 정정(correction).

Each item carries provider/region/housing_type/split metadata + page_ids + table_ids + cell_ids.
Output (internal): workspace_local/audit/qa_v05_det.jsonl
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

import qa_v04_common as Q
import qa_v05_common as F

OUT = Q.ROOT / "workspace_local" / "audit" / "qa_v05_det.jsonl"
DATE_RE = re.compile(r"20\d{2}\s*[.\-년]\s*\d{1,2}\s*[.\-월]\s*\d{1,2}")
SUPPLY_KW = ["특별공급", "일반공급", "신혼부부", "생애최초", "노부모부양", "다자녀", "신생아", "기관추천", "우선공급", "추첨"]
ELIG_ROW_KW = ["소득", "자산", "무주택", "거주", "입주자저축", "청약통장", "주택소유", "세대구성원", "재당첨", "나이", "혼인", "월평균", "가구원"]
COND_RE = re.compile(r"(%|％|이하|이상|미만|초과|해당|본인|구성원|무주택|만원|천원|억원|개월|이내|점|배)")

items = []
pattern_count = Counter()   # cap near-duplicate (row_header,col_header) patterns across announcements


def emit(it, ok, band=None):
    it["_ok"] = ok
    it["_band"] = band
    items.append(it)


def _base(ann_id, task_type, caps):
    mf = F.ann_meta_fields(ann_id)
    return {"split": mf["split"], "task_type": task_type,
            "provider": mf["provider"], "region_sido": mf["region_sido"],
            "region_sigungu": mf["region_sigungu"], "housing_type": mf["housing_type"],
            "source_ids": [Q.LH_V04], "required_capabilities": caps,
            "announcement_ids": [ann_id]}


def _unique_pairs(cells):
    """(row_header,col_header) -> the single cell if unique within its table, else dropped."""
    by_table = defaultdict(lambda: defaultdict(list))
    for c in cells:
        by_table[c["table_id"]][(c["row_header"], c["col_header"])].append(c)
    out = []
    for tid, pairs in by_table.items():
        for key, cs in pairs.items():
            if len(cs) == 1:
                out.append(cs[0])
    return out


def gen_table_cell_numeric(per_ann=26):
    for a in Q.announcement_ids():
        title = Q.ann_meta().get(a, {}).get("title_from_audit") or a
        cells = _unique_pairs(F.ann_cells(a))
        n = 0
        for c in sorted(cells, key=lambda x: (x["page_id"], x["table_id"], x["row_index"], x["col_index"])):
            if n >= per_ann:
                break
            rh, ch, ct = c["row_header"], c["col_header"], c["cell_text"]
            if not (rh and ch and ct) or rh == ct or ch == ct:
                continue
            # require a real measured quantity (value + unit) so addresses/phone/codes are excluded
            if c.get("normalized_value") is None or c.get("unit") is None or len(ct) > 24 or c["confidence"] < 0.9:
                continue
            if len(rh) > 30 or len(ch) > 30:
                continue
            pid = c["page_id"]
            # grounding: cell value AND both headers verbatim on the cited page
            if not (Q.grounded_in_pages(ct, [pid]) and Q.grounded_in_pages(rh, [pid]) and Q.grounded_in_pages(ch, [pid])):
                continue
            pat = (rh, ch)
            if pattern_count[pat] >= 3:   # cap near-duplicate patterns across announcements
                continue
            pno = pid.split("-p")[-1]
            it = _base(a, "table_numeric_reasoning", ["table_cell_lookup", "table_reading"])
            it.update({
                "question": f"「{title}」(p.{int(pno)})의 표에서 '{rh}' 항목의 '{ch}' 값은 무엇인가?",
                "answer": ct, "answer_type": "string",
                "evidence": [{"source_id": Q.LH_V04, "locator": f"{c['table_id']} (r{c['row_index']}c{c['col_index']}) '{rh}'×'{ch}'"}],
                "evaluation": {"metric": "contains_all", "gold_terms": [ct]},
                "page_ids": [pid], "table_ids": [c["table_id"]], "cell_ids": [F.cell_id(c)],
                "copyright_note": "공고 표 셀 단답(행·열 머리글 교차). 원문 전체는 내부 전용.",
            })
            emit(it, True, band="multi")
            pattern_count[pat] += 1
            n += 1


def gen_eligibility(per_ann=16):
    for a in Q.announcement_ids():
        title = Q.ann_meta().get(a, {}).get("title_from_audit") or a
        cells = _unique_pairs(F.ann_cells(a))
        n = 0
        for c in sorted(cells, key=lambda x: (x["page_id"], x["table_id"], x["row_index"], x["col_index"])):
            if n >= per_ann:
                break
            rh, ch, ct = c["row_header"], c["col_header"], c["cell_text"]
            if not (rh and ch and ct) or rh == ct or ch == ct or len(ct) > 30:
                continue
            if c["confidence"] < 0.9 or len(rh) > 28 or len(ch) > 28:
                continue
            # at least one header is an eligibility/supply concept and the cell is a condition/value
            kw_h = [h for h in (rh, ch) if any(k in h for k in SUPPLY_KW + ELIG_ROW_KW)]
            if not kw_h or not COND_RE.search(ct):
                continue
            concept = kw_h[0]
            crit = ch if concept == rh else rh
            pid = c["page_id"]
            if not (Q.grounded_in_pages(ct, [pid]) and Q.grounded_in_pages(concept, [pid]) and Q.grounded_in_pages(crit, [pid])):
                continue
            pat = ("ELIG", concept, crit)
            if pattern_count[pat] >= 3:
                continue
            pno = pid.split("-p")[-1]
            it = _base(a, "eligibility_reasoning", ["eligibility_reasoning", "table_reading", "multi_hop_reasoning"])
            it.update({
                "question": f"「{title}」(p.{int(pno)}) 자격요건 표에서 '{concept}'의 '{crit}' 기준은 무엇인가?",
                "answer": ct, "answer_type": "string",
                "evidence": [{"source_id": Q.LH_V04, "locator": f"{c['table_id']} '{concept}'×'{crit}'"}],
                "evaluation": {"metric": "contains_all", "gold_terms": [ct]},
                "page_ids": [pid], "table_ids": [c["table_id"]], "cell_ids": [F.cell_id(c)],
                "copyright_note": "공고 자격요건 표 셀 단답. 원문 전체는 내부 전용.",
            })
            emit(it, True, band="multi")
            pattern_count[pat] += 1
            n += 1


def gen_schedule(per_ann=6):
    for a in Q.announcement_ids():
        title = Q.ann_meta().get(a, {}).get("title_from_audit") or a
        n = 0
        seen = set()
        for c in F.ann_cells(a):
            if n >= per_ann:
                break
            rh, ch, ct = c["row_header"], c["col_header"], c["cell_text"]
            if not DATE_RE.search(ct) or len(ct) > 40:
                continue
            # use whichever header names the schedule stage (not echoing the date)
            label = None
            for h in (rh, ch):
                if h and h not in ct and ct not in h and 2 <= len(h) <= 28:
                    label = h
                    break
            if not label:
                continue
            pid = c["page_id"]
            if not (Q.grounded_in_pages(ct, [pid]) and Q.grounded_in_pages(label, [pid])):
                continue
            if (label, ct) in seen:
                continue
            seen.add((label, ct))
            pno = pid.split("-p")[-1]
            it = _base(a, "schedule_reasoning", ["schedule_reasoning", "table_reading"])
            it.update({
                "question": f"「{title}」(p.{int(pno)}) 일정 표에서 '{label}'의 일정(일자/시간)은 무엇인가?",
                "answer": ct, "answer_type": "string",
                "evidence": [{"source_id": Q.LH_V04, "locator": f"{c['table_id']} '{label}' 일정"}],
                "evaluation": {"metric": "contains_all", "gold_terms": [ct[:40]]},
                "page_ids": [pid], "table_ids": [c["table_id"]], "cell_ids": [F.cell_id(c)],
                "copyright_note": "공고 일정 표 셀 단답. 원문 전체는 내부 전용.",
            })
            emit(it, True, band="multi")
            n += 1


def gen_correction():
    for a in Q.announcement_ids():
        title = Q.ann_meta().get(a, {}).get("title_from_audit") or a
        # find a lead page that marks a correction
        pid = None
        for p in Q.ann_pages(a)[:6]:
            if "정정" in p["text"]:
                pid = p["page_id"]
                break
        if not pid:
            continue
        it = _base(a, "correction_notice_reasoning", ["correction_notice_reasoning", "announcement_reading"])
        it.update({
            "question": f"「{title}」은 최초 공고인가, 정정(訂正) 공고인가? 공고문 표기 근거를 함께 제시하라.",
            "answer": "정정 공고. 공고문에 '정정' 표기가 있음.", "answer_type": "string",
            "evidence": [{"source_id": Q.LH_V04, "locator": f"{pid} '정정' 표기"}],
            "evaluation": {"metric": "contains_all", "gold_terms": ["정정"]},
            "page_ids": [pid], "announcement_ids": [a],
            "copyright_note": "공고 정정 여부 판별(표기 근거). 원문 전체는 내부 전용.",
        })
        emit(it, Q.grounded_in_pages("정정", [pid]), band="early")


def main():
    gen_table_cell_numeric()
    gen_eligibility()
    gen_schedule()
    gen_correction()
    ok = [i for i in items if i["_ok"]]
    seen_q, dedup, ndup = set(), [], 0
    for it in ok:
        if it["question"] in seen_q:
            ndup += 1
            continue
        seen_q.add(it["question"])
        dedup.append(it)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for it in dedup:
            f.write(json.dumps({k: v for k, v in it.items() if not k.startswith("_")}, ensure_ascii=False) + "\n")
    fam = Counter(i["task_type"] for i in dedup)
    print(f"=== DET v0.5 (cells/schedule/eligibility/correction): {len(dedup)} (deduped {ndup}) ===")
    for k, v in sorted(fam.items()):
        print(f"   {k:32s} {v}")
    print(f"   dropped {len(items)-len(ok)} not grounded")
    print(f"   -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
