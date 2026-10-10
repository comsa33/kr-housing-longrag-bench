#!/usr/bin/env python3
"""Deterministically generate v0.3 QA whose gold answer is recomputed from real rows.

Families produced here (verified-by-construction via qa_v03_common.recompute):
  - table_numeric_reasoning : MOLIT/HUG filter+aggregate (count/avg/max/min/median/argmax)
  - format_robustness       : same MOLIT slice asked across text/markdown/csv/json renderings
  - answerability_detection : empty-slice negative controls (count==0 => unanswerable)

Public QA carries question, short answer, source_id, locator, row_ids (sample), gold_predicate.
Row data stays internal. Output staging: workspace_local/audit/qa_v03_det.jsonl
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import qa_v03_common as C

OUT = C.ROOT / "workspace_local" / "audit" / "qa_v03_det.jsonl"
FMT_DIR = C.PROC / "format_variants"

MONTH_KO = lambda ym: f"{ym[:4]}년 {int(ym[4:6])}월"
items: list[dict] = []


def rid_sample(ids: list[str], k: int = 20) -> list[str]:
    return ids[:k]


def emit(it: dict, ok: bool, why: str = "") -> None:
    it["_ok"] = ok
    it["_why"] = why
    items.append(it)


def molit_loc(pred: dict) -> str:
    return f"MOLIT 아파트 매매 실거래가 상세 / predicate: {C.predicate_human(pred)}"


def add_table(source, slice_label, pred, question, answer, ans_type, caps, metric, gold, loc):
    val, ids = C.recompute(pred)
    ok = val is not None
    it = {
        "split": "dev", "task_type": "table_numeric_reasoning",
        "question": question, "answer": answer, "answer_type": ans_type,
        "source_ids": [source], "required_capabilities": caps,
        "evidence": [{"source_id": source, "locator": loc}],
        "evaluation": {"metric": metric, **gold},
        "row_ids": rid_sample(ids), "gold_predicate": pred,
        "copyright_note": "공공데이터 실데이터 행에서 결정론 집계. 공개물은 predicate+row_id+단답만.",
    }
    emit(it, ok)


# ----------------------------------------------------------------- MOLIT table
def gen_molit_table():
    idx = json.loads((C.ROOT / "workspace_local" / "audit" / "index_molit.json").read_text(encoding="utf-8"))
    slices = idx["district_month_slices"]
    # diversify: per district pick up to 3 months with healthy counts
    by_dist: dict[str, list] = {}
    for s in slices:
        by_dist.setdefault(s["district"], []).append(s)
    plan = []
    for dist, sl in by_dist.items():
        sl = sorted(sl, key=lambda x: -x["count"])[:2]
        for s in sl:
            plan.append((dist, s["deal_ymd"]))

    for dist, ym in plan:
        base = {"source": C.MOLIT, "filter": {"_lawd_name": dist, "_deal_ymd": ym}}
        d_ko = dist.split()[-1] if " " in dist else dist
        # count
        v, _ = C.recompute({**base, "op": "count"})
        add_table(C.MOLIT, f"{dist}-{ym}", {**base, "op": "count"},
                  f"MOLIT 아파트 매매 실거래가 상세 자료에서 {dist} {MONTH_KO(ym)}의 아파트 매매 거래 건수는 몇 건인가?",
                  f"{v:,}건", "number", ["table_filtering", "counting"],
                  "exact_numbers", {"gold_numbers": [str(v)]}, molit_loc({**base, "op": "count"}))
        # avg price
        p = {**base, "op": "avg", "field": "dealAmount_manwon"}
        v, _ = C.recompute(p)
        add_table(C.MOLIT, f"{dist}-{ym}", p,
                  f"MOLIT 실거래 상세에서 {dist} {MONTH_KO(ym)} 아파트 매매 거래금액의 평균은 약 몇 만원인가? (정수 만원)",
                  f"{v:,}만원", "number", ["table_filtering", "numeric_aggregation"],
                  "exact_numbers", {"gold_numbers": [str(v)]}, molit_loc(p))
        # max price
        p = {**base, "op": "max", "field": "dealAmount_manwon"}
        v, _ = C.recompute(p)
        add_table(C.MOLIT, f"{dist}-{ym}", p,
                  f"MOLIT 실거래 상세에서 {dist} {MONTH_KO(ym)} 아파트 매매 최고 거래금액은 몇 만원인가?",
                  f"{v:,}만원", "number", ["table_filtering", "numeric_aggregation"],
                  "exact_numbers", {"gold_numbers": [str(v)]}, molit_loc(p))
        # argmax apt name
        p = {**base, "op": "argmax", "field": "dealAmount_manwon", "return_field": "aptNm"}
        v, _ = C.recompute(p)
        add_table(C.MOLIT, f"{dist}-{ym}", p,
                  f"MOLIT 실거래 상세에서 {dist} {MONTH_KO(ym)} 최고 거래금액을 기록한 아파트의 이름(aptNm)은?",
                  f"{v}", "text", ["table_filtering", "argmax"],
                  "exact_match", {"gold_terms": [v]}, molit_loc(p))
        # 84㎡-band count
        p = {**base, "op": "count", "filter": {**base["filter"], "excluUseAr_m2": {"min": 84, "max": 85}}}
        v, _ = C.recompute(p)
        if v and v > 0:
            add_table(C.MOLIT, f"{dist}-{ym}-84", p,
                      f"MOLIT 실거래 상세에서 {dist} {MONTH_KO(ym)} 전용면적 84㎡대(84㎡ 이상 85㎡ 미만) 매매 거래 건수는?",
                      f"{v:,}건", "number", ["table_filtering", "counting"],
                      "exact_numbers", {"gold_numbers": [str(v)]}, molit_loc(p))


# ----------------------------------------------------------------- HUG table
def gen_hug_table():
    idx = json.loads((C.ROOT / "workspace_local" / "audit" / "index_hug.json").read_text(encoding="utf-8"))
    # pick region-year slices with healthy counts
    sl = sorted(idx["region_year_slices"], key=lambda x: -x["count"])[:8]
    for s in sl:
        region, year = s["region"], s["year"]
        base = {"source": C.HUG, "filter": {"_query_area_name": region, "_query_year": year}}
        p = {**base, "op": "count"}
        v, _ = C.recompute(p)
        add_table(C.HUG, f"{region}-{year}", p,
                  f"HUG 분양이력정보에서 {year}년 {region}의 분양 사업장(분양보증 발급) 건수는 몇 건인가?",
                  f"{v:,}건", "number", ["table_filtering", "counting"],
                  "exact_numbers", {"gold_numbers": [str(v)]},
                  f"HUG 분양이력정보 / predicate: {C.predicate_human(p)}")
        p = {**base, "op": "sum", "field": "TOT_HOCO"}
        v, _ = C.recompute(p)
        add_table(C.HUG, f"{region}-{year}", p,
                  f"HUG 분양이력정보에서 {year}년 {region} 분양 사업장의 총세대수(TOT_HOCO) 합계는?",
                  f"{v:,}세대", "number", ["table_filtering", "numeric_aggregation"],
                  "exact_numbers", {"gold_numbers": [str(v)]},
                  f"HUG 분양이력정보 / predicate: {C.predicate_human(p)}")


# ----------------------------------------------------------------- format robustness
def gen_format_robustness():
    FMT_DIR.mkdir(parents=True, exist_ok=True)
    # small clean slices (5-60 bounded rows) for 4-format rendering — scan 종로구/동구 months
    cand = [("서울특별시 종로구", ym) for ym in
            ["202501", "202502", "202503", "202504", "202505", "202506",
             "202507", "202508", "202509", "202510", "202511", "202512"]]
    cand += [("대전광역시 동구", ym) for ym in ["202504", "202508", "202509"]]
    targets, used = [], 0
    for dist, ym in cand:
        if used >= 6:
            break
        n = len(C.select({"source": C.MOLIT, "filter": {"_lawd_name": dist, "_deal_ymd": ym}}))
        if 5 <= n <= 60:
            targets.append((dist, ym)); used += 1
    for dist, ym in targets:
        pred = {"source": C.MOLIT, "filter": {"_lawd_name": dist, "_deal_ymd": ym}, "op": "count"}
        rows = C.select(pred)
        if not (5 <= len(rows) <= 60):
            continue
        ids = [r["_row_id"] for r in rows]
        norm = [{"row_id": r["_row_id"], "aptNm": r["aptNm"], "excluUseAr": r["excluUseAr"],
                 "floor": r["floor"], "dealAmount_manwon": r["dealAmount"].replace(",", "")} for r in rows]
        base = f"{dist.replace(' ', '')}_{ym}"
        (FMT_DIR / f"{base}.txt").write_text(
            "\n".join(f"{r['row_id']} {r['aptNm']} {r['excluUseAr']}㎡ {r['floor']}층 {r['dealAmount_manwon']}만원"
                      for r in norm), encoding="utf-8")
        (FMT_DIR / f"{base}.md").write_text(
            "| row_id | aptNm | excluUseAr | floor | dealAmount_manwon |\n|---|---|---|---|---|\n" +
            "\n".join(f"| {r['row_id']} | {r['aptNm']} | {r['excluUseAr']} | {r['floor']} | {r['dealAmount_manwon']} |"
                      for r in norm), encoding="utf-8")
        (FMT_DIR / f"{base}.csv").write_text(
            "row_id,aptNm,excluUseAr,floor,dealAmount_manwon\n" +
            "\n".join(f"{r['row_id']},{r['aptNm']},{r['excluUseAr']},{r['floor']},{r['dealAmount_manwon']}"
                      for r in norm), encoding="utf-8")
        (FMT_DIR / f"{base}.json").write_text(json.dumps(norm, ensure_ascii=False), encoding="utf-8")

        cnt_pred = {"source": C.MOLIT, "filter": {"_lawd_name": dist, "_deal_ymd": ym}, "op": "count"}
        cnt, _ = C.recompute(cnt_pred)
        for fmt, ext in [("plain_text", "txt"), ("markdown", "md"), ("csv", "csv"), ("json", "json")]:
            it = {
                "split": "dev", "task_type": "format_robustness",
                "question": f"다음 MOLIT 실거래 표(동일 데이터)를 {fmt} 형식으로 제공했을 때, {dist} {MONTH_KO(ym)} "
                            f"아파트 매매 거래 '행(레코드) 수'는 몇 개인가?",
                "answer": f"{cnt}", "answer_type": "number",
                "source_ids": [C.MOLIT], "required_capabilities": ["format_robustness", "counting"],
                "evidence": [{"source_id": C.MOLIT,
                              "locator": f"format_variants/{base}.{ext} ({fmt}) / predicate: {C.predicate_human(cnt_pred)}"}],
                "evaluation": {"metric": "exact_numbers", "gold_numbers": [str(cnt)]},
                "row_ids": rid_sample(ids), "gold_predicate": cnt_pred,
                "copyright_note": "동일 슬라이스의 4개 직렬화 형식에 대한 동일 질의(형식 강건성). 행은 내부 format_variants에만 저장.",
            }
            emit(it, cnt is not None and len(rows) == cnt)


# ----------------------------------------------------------------- answerability (empty slice)
def gen_answerability():
    # districts/regions deliberately NOT in the sampled data -> count == 0 -> unanswerable
    molit_absent = [("부산광역시 해운대구", "202503"), ("세종특별자치시", "202504"),
                    ("경기도 성남시 분당구", "202505"), ("인천광역시 연수구", "202506"),
                    ("광주광역시 서구", "202507"), ("대구광역시 수성구", "202508"),
                    ("울산광역시 남구", "202503"), ("경기도 수원시 영통구", "202509"),
                    ("강원특별자치도 춘천시", "202506"), ("전북특별자치도 전주시 완산구", "202504"),
                    ("제주특별자치도 제주시", "202507"), ("충청남도 천안시 서북구", "202505"),
                    ("경상남도 창원시 성산구", "202508"), ("서울특별시 마포구", "202510")]
    for dist, ym in molit_absent:
        pred = {"source": C.MOLIT, "filter": {"_lawd_name": dist, "_deal_ymd": ym}, "op": "count"}
        v, _ = C.recompute(pred)
        it = {
            "split": "dev", "task_type": "answerability_detection",
            "question": f"제공된 MOLIT 아파트 매매 실거래가 상세(현재 표본)만으로 {dist} {MONTH_KO(ym)}의 "
                        f"평균 거래금액을 확정할 수 있는가?",
            "answer": f"확정할 수 없음(unanswerable). 현재 표본에는 {dist} {MONTH_KO(ym)} 거래 데이터가 없음(0건).",
            "answer_type": "boolean_with_reason",
            "source_ids": [C.MOLIT], "required_capabilities": ["answerability_detection", "coverage_check"],
            "evidence": [{"source_id": C.MOLIT, "locator": f"표본 부재: {C.predicate_human(pred)} = 0"}],
            "evaluation": {"metric": "boolean_and_reason", "gold_numbers": ["0"], "gold_terms": ["확정할 수 없", "없"]},
            "gold_predicate": pred,
            "copyright_note": "negative control. 표본 부재(0건)를 결정론으로 검증.",
        }
        emit(it, v == 0)
    # HUG region/year not sampled
    hug_absent = [("세종특별자치시", "2024"), ("서울특별시", "2022"), ("경기도", "2021"),
                  ("부산광역시", "2026"), ("대전광역시", "2022"), ("인천광역시", "2020")]
    for region, year in hug_absent:
        pred = {"source": C.HUG, "filter": {"_query_area_name": region, "_query_year": year}, "op": "count"}
        v, _ = C.recompute(pred)
        it = {
            "split": "dev", "task_type": "answerability_detection",
            "question": f"제공된 HUG 분양이력정보(현재 표본)만으로 {year}년 {region}의 분양 사업장 총세대수 합을 확정할 수 있는가?",
            "answer": f"확정할 수 없음(unanswerable). 현재 표본에는 {year}년 {region} 분양이력 데이터가 없음(0건).",
            "answer_type": "boolean_with_reason",
            "source_ids": [C.HUG], "required_capabilities": ["answerability_detection", "coverage_check"],
            "evidence": [{"source_id": C.HUG, "locator": f"표본 부재: {C.predicate_human(pred)} = 0"}],
            "evaluation": {"metric": "boolean_and_reason", "gold_numbers": ["0"], "gold_terms": ["확정할 수 없", "없"]},
            "gold_predicate": pred,
            "copyright_note": "negative control. 표본 부재(0건)를 결정론으로 검증.",
        }
        emit(it, v == 0)


# ----------------------------------------------------------------- cross-source (LH district -> MOLIT)
def gen_cross_source_det():
    # The LH announcement (대전대동2 1블록) 공급위치 = 대전광역시 동구; MOLIT has 대전광역시 동구 rows.
    # A valid cross-source QA: read the announcement to resolve the district, then aggregate MOLIT.
    p1 = next((p for p in C.lh_pages() if p["page_no"] == 1), None)
    if not p1 or "동구" not in p1["text"]:
        return
    pid = p1["page_id"]
    dist = "대전광역시 동구"

    def cs(question, pred, gold_terms, extra_caps=()):
        v, ids = C.recompute(pred)
        if v is None or (pred["op"] == "count" and v == 0):
            emit({}, False); return
        unit = "건" if pred["op"] == "count" else ("만원" if "dealAmount" in pred.get("field", "") else "세대")
        it = {
            "split": "dev", "task_type": "cross_source_aggregation",
            "question": question, "answer": f"{v:,}{unit}", "answer_type": "number",
            "source_ids": [C.LH, pred["source"]],
            "required_capabilities": ["cross_source_aggregation", "multi_hop_reasoning", *extra_caps],
            "evidence": [{"source_id": C.LH, "locator": f"{p1['locator']} 공급위치/공급대상"},
                         {"source_id": pred["source"], "locator": f"predicate: {C.predicate_human(pred)}"}],
            "evaluation": {"metric": "exact_numbers", "gold_numbers": [str(v)], "gold_terms": gold_terms},
            "page_ids": [pid], "row_ids": rid_sample(ids), "gold_predicate": pred,
            "copyright_note": "공고 사실(공급위치/대상) + 공공데이터 집계 결합. 공개물은 locator+predicate+단답만.",
        }
        emit(it, True)

    # (1) LH district -> MOLIT 동구 monthly count/avg/max
    for ym in ["202502", "202503", "202504", "202506", "202508", "202510"]:
        base = {"source": C.MOLIT, "filter": {"_lawd_name": dist, "_deal_ymd": ym}}
        cs(f"「대전대동2 1블록 공공분양 입주자모집공고」(p.1)의 공급위치가 속한 시·군·구의 MOLIT 실거래에서 "
           f"{MONTH_KO(ym)} 아파트 매매 거래 건수는?", {**base, "op": "count"}, ["동구"], ["table_filtering"])
        cs(f"위 공고의 공급위치가 속한 시·군·구의 MOLIT 실거래에서 {MONTH_KO(ym)} 평균 거래금액은?",
           {**base, "op": "avg", "field": "dealAmount_manwon"}, ["동구"], ["numeric_aggregation"])
        cs(f"위 공고의 공급위치가 속한 시·군·구의 MOLIT 실거래에서 {MONTH_KO(ym)} 최고 거래금액은?",
           {**base, "op": "max", "field": "dealAmount_manwon"}, ["동구"], ["numeric_aggregation"])
    # (2) LH 전용면적 84㎡ 대상 -> MOLIT 동구 84㎡대 집계
    for ym in ["202503", "202507"]:
        base = {"source": C.MOLIT, "filter": {"_lawd_name": dist, "_deal_ymd": ym, "excluUseAr_m2": {"min": 84, "max": 85}}}
        cs(f"위 공고의 공급대상에 포함된 전용면적 84㎡ 주택과 관련하여, 같은 시·군·구의 MOLIT 실거래 중 "
           f"전용면적 84㎡대(84~85㎡) {MONTH_KO(ym)} 거래 건수는?", {**base, "op": "count"}, ["동구", "84"], ["table_filtering"])
        cs(f"위 공고의 전용면적 84㎡ 주택과 관련하여, 같은 시·군·구 MOLIT 84㎡대 {MONTH_KO(ym)} 평균 거래금액은?",
           {**base, "op": "avg", "field": "dealAmount_manwon"}, ["동구", "84"], ["numeric_aggregation"])
    # (3) LH 광역시(대전) -> HUG 대전 분양현황
    for year in ["2023", "2024", "2025"]:
        base = {"source": C.HUG, "filter": {"_query_area_name": "대전광역시", "_query_year": year}}
        cs(f"위 공고의 공급위치가 속한 광역시에 대하여, HUG 분양이력정보에서 {year}년 분양 사업장 건수는?",
           {**base, "op": "count"}, ["대전"], ["table_filtering"])
        cs(f"위 공고의 공급위치가 속한 광역시에 대하여, HUG 분양이력정보 {year}년 분양 사업장 총세대수 합은?",
           {**base, "op": "sum", "field": "TOT_HOCO"}, ["대전"], ["numeric_aggregation"])


# ----------------------------------------------------------------- LH retrieval (deterministic cloze)
def gen_lh_retrieval_det(target: int = 8):
    """Short-cloze LH retrieval from value_unique_in_doc facts on pages 1-6, skipping facts already
    used by agents (dedup by value_text). Stems kept short (<=22 chars) to avoid long excerpts."""
    agent_path = C.ROOT / "workspace_local" / "audit" / "qa_v03_agent_raw.json"
    used = set()
    if agent_path.exists():
        for row in json.loads(agent_path.read_text(encoding="utf-8")):
            for t in row["item"].get("evaluation", {}).get("gold_terms", []):
                used.add(t)
    pages = {p["page_no"]: p for p in C.lh_pages()}
    pid_by_no = {p["page_no"]: p["page_id"] for p in C.lh_pages()}
    from collections import Counter as _C
    vt = _C(f["value_text"] for f in C.lh_facts())
    n = 0
    for f in C.lh_facts():
        if n >= target:
            break
        if f["page_no"] > 6 or vt[f["value_text"]] != 1:
            continue
        val = f["value_text"]
        if val in used or len(val) < 2:
            continue
        snip = f["local_snippet"]
        i = snip.find(val)
        if i < 0:
            continue
        pre = snip[max(0, i - 18):i]
        if " " in pre:
            pre = pre[pre.index(" ") + 1:]
        post = snip[i + len(val):i + len(val) + 8]
        if " " in post:
            post = post[:post.rindex(" ")]
        stem = f"{pre}____{post}".strip()
        if not (4 <= len(stem) <= 30):
            continue
        pid = pid_by_no[f["page_no"]]
        used.add(val)
        n += 1
        it = {
            "split": "dev", "task_type": "long_context_retrieval",
            "question": f"「대전대동2 1블록 공공분양 입주자모집공고」(p.{f['page_no']})에서 다음 빈칸에 들어갈 값은? — \"{stem}\"",
            "answer": val, "answer_type": "span",
            "source_ids": [C.LH], "required_capabilities": ["long_context_retrieval", "announcement_reading"],
            "evidence": [{"source_id": C.LH, "locator": f"{f['locator']} (p.{f['page_no']})"}],
            "evaluation": {"metric": "contains_all", "gold_terms": [val]},
            "page_ids": [pid],
            "copyright_note": "공고 단답 + 짧은 cloze 스템(공공기관 입주자모집공고). 원문 전체는 내부 전용.",
        }
        emit(it, val.replace(" ", "") in pages[f["page_no"]]["text"].replace(" ", ""))


def main() -> int:
    gen_molit_table()
    gen_hug_table()
    gen_format_robustness()
    gen_answerability()
    gen_cross_source_det()
    gen_lh_retrieval_det()

    ok = [i for i in items if i["_ok"]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for it in ok:
            out = {k: v for k, v in it.items() if not k.startswith("_")}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
    fam = Counter(i["task_type"] for i in ok)
    print(f"=== DET v0.3: emitted {len(ok)}/{len(items)} ===")
    for k, v in sorted(fam.items()):
        print(f"   {k}: {v}")
    dropped = [i for i in items if not i["_ok"]]
    if dropped:
        print(f"   dropped {len(dropped)} (recompute None / mismatch)")
    print(f"   -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
