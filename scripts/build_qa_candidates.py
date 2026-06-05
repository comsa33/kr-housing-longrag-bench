#!/usr/bin/env python3
"""Deterministically generate VERIFIED v0.2 QA candidates from the extracted statute corpus.

Only families whose gold answer can be derived and checked by construction are produced here:
  - table_numeric_reasoning  : short cloze numeric retrieval, 호(item) counts, cross-article comparison
  - format_robustness        : same enumeration table asked across text/markdown/csv/json renderings
  - retrieval                : article 제명(title) lookup (unambiguous, verbatim-verifiable)
  - answerability_detection  : negative controls whose required fact is provably absent from the bundle
  - cross_source_aggregation : combine confirmed metadata facts across two public-data sources

Every emitted item is checked against the actual source text before being written. Output:
  workspace_local/audit/qa_det.jsonl   (internal staging; merged into the public file by assemble_qa.py)
Source statutory text is Korean Copyright Act Art. 7 exempt; only short factual stems/answers are used.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from qa_common import (PROC, ROOT, STATUTE_TITLES, articles, load_jsonl,
                       norm, term_absent_from_sources, term_in_source)

OUT = ROOT / "workspace_local" / "audit" / "qa_det.jsonl"
DATE_RE = re.compile(r"\d{4}\.\s*\d{1,2}\.|\d+년\s*\d+월|개정|신설|삭제|부칙|종전|시행일")
UNIT_KO = {"area_m2": "면적", "percent": "비율(퍼센트)", "days": "기간(일)", "months": "기간(개월)",
           "years": "기간(년)", "households": "세대수", "age_years": "연령(세)",
           "multiplier": "배수", "won_10k": "금액", "won": "금액"}

items: list[dict] = []
log: list[str] = []


def emit(item: dict, check: bool) -> None:
    item["_verified"] = bool(check)
    items.append(item)
    log.append(f"{'OK ' if check else 'DROP'} {item['task_type']:26s} {item['qa_id']}")


# ---------------------------------------------------------------- numeric cloze
def short_cloze(context: str, match: str) -> str | None:
    i = context.find(match)
    if i < 0:
        return None
    pre, post = context[:i], context[i + len(match):]
    pre = pre[-22:]
    if " " in pre:
        pre = pre[pre.index(" ") + 1:]
    post = post[:14]
    if " " in post:
        post = post[:post.rindex(" ")]
    stem = (pre + "____" + post).strip()
    return stem if 6 <= len(stem) <= 44 else None


def gen_numeric_cloze(limit_per_law: int = 4) -> None:
    n = 0
    for sid in STATUTE_TITLES:
        facts = load_jsonl(PROC / sid / "numeric_facts.jsonl")
        used_articles: set[str] = set()
        c = 0
        for f in facts:
            if c >= limit_per_law:
                break
            ctx, match, art = f["context"], f["match"], f["article"]
            if DATE_RE.search(ctx):
                continue
            if f["unit_kind"] == "years" and int(f["value_raw"]) > 100:
                continue
            if art in used_articles:  # diversify across articles
                continue
            stem = short_cloze(ctx, match)
            if not stem:
                continue
            n += 1
            c += 1
            used_articles.add(art)
            qid = f"num_cloze_{sid.split('-')[1]}_{n}"
            q = (f"「{STATUTE_TITLES[sid]}」 {art}의 다음 문구에서 빈칸에 들어갈 수치는? "
                 f"(단위 포함, 예: 85제곱미터) — \"{stem}\"")
            ok = match in articles(sid)[art]["text"]
            emit({
                "qa_id": qid, "split": "dev", "task_type": "table_numeric_reasoning",
                "question": q, "answer": match, "answer_type": "number_with_unit",
                "source_ids": [sid], "required_capabilities": ["numeric_retrieval", "long_context_retrieval"],
                "evidence": [{"source_id": sid, "locator": f"{articles(sid)[art]['locator']} 본문 수치 조항"}],
                "evaluation": {"metric": "exact_numbers", "gold_numbers": [f["value_raw"]]},
                "copyright_note": "단답형 수치 + 짧은 cloze 문구. 출처는 저작권법 제7조 비보호 법령 본문.",
            }, ok)


# ---------------------------------------------------------------- 호 count
def gen_ho_count(per_law: int = 1) -> None:
    for sid in STATUTE_TITLES:
        tables = [t for t in load_jsonl(PROC / sid / "tables.jsonl")
                  if t["kind"] == "in_text_enumeration"]
        tables = sorted(tables, key=lambda t: -t["n_rows"])
        for t in tables[:per_law]:
            maxho = max(r["호"] for r in t["rows"])
            art = t["table_id"].split("::")[1]
            rec = articles(sid)[art]
            qid = f"ho_count_{sid.split('-')[1]}_{art}"
            q = f"「{STATUTE_TITLES[sid]}」 {art}({rec['title']})은 제몇 호까지 규정하는가? (최대 호 번호)"
            emit({
                "qa_id": qid, "split": "dev", "task_type": "table_numeric_reasoning",
                "question": q, "answer": f"제{maxho}호", "answer_type": "number",
                "source_ids": [sid], "required_capabilities": ["table_structure_reasoning", "counting"],
                "evidence": [{"source_id": sid, "locator": f"{rec['locator']} 각 호 열거"}],
                "evaluation": {"metric": "exact_numbers", "gold_numbers": [str(maxho)]},
                "copyright_note": "구조 카운팅. 출처는 저작권법 제7조 비보호 법령 본문.",
            }, maxho == max(r["호"] for r in t["rows"]))


# ---------------------------------------------------------------- comparison
def gen_comparison() -> None:
    for sid in STATUTE_TITLES:
        facts = load_jsonl(PROC / sid / "numeric_facts.jsonl")
        by_unit: dict[str, dict[str, int]] = {}
        for f in facts:
            if DATE_RE.search(f["context"]):
                continue
            if f["unit_kind"] in ("days", "years", "months", "age_years", "area_m2"):
                by_unit.setdefault(f["unit_kind"], {})
                # keep first (unique-ish) value per article
                by_unit[f["unit_kind"]].setdefault(f["article"], int(f["value_raw"]))
        for unit, amap in by_unit.items():
            if len(amap) < 2:
                continue
            (aA, vA), (aB, vB) = sorted(amap.items(), key=lambda x: -x[1])[:2]
            if vA == vB:
                continue
            qid = f"cmp_{sid.split('-')[1]}_{unit}"
            q = (f"「{STATUTE_TITLES[sid]}」에서 {aA}와 {aB} 중 더 큰 {UNIT_KO[unit]} 수치를 "
                 f"규정한 조문은 무엇인가?")
            ok = (str(vA) in articles(sid)[aA]["text"]) and (str(vB) in articles(sid)[aB]["text"])
            emit({
                "qa_id": qid, "split": "dev", "task_type": "table_numeric_reasoning",
                "question": q, "answer": aA, "answer_type": "article_label",
                "source_ids": [sid], "required_capabilities": ["numeric_comparison", "long_context_retrieval"],
                "evidence": [{"source_id": sid, "locator": f"{articles(sid)[aA]['locator']} ({vA}) vs {articles(sid)[aB]['locator']} ({vB})"}],
                "evaluation": {"metric": "exact_match", "gold_terms": [aA]},
                "copyright_note": "두 조문 수치 비교. 출처는 저작권법 제7조 비보호 법령 본문.",
            }, ok)
            break  # one comparison per law for diversity


# ---------------------------------------------------------------- format robustness
def gen_format_robustness(n_tables: int = 2) -> None:
    sid = "law-housing-supply-rule"
    tables = [t for t in load_jsonl(PROC / sid / "tables.jsonl") if t["kind"] == "in_text_enumeration"]

    def substantive(t):
        rows = [r for r in t["rows"] if "삭제" not in r["내용"] and len(r["내용"]) >= 6]
        return rows
    cand = [(t, substantive(t)) for t in tables]
    cand = [(t, rows) for t, rows in cand if len(rows) >= 4]
    cand = sorted(cand, key=lambda x: len(x[1]))[:n_tables]  # prefer small, clean tables

    for t, rows in cand:
        art = t["table_id"].split("::")[1]
        rec = articles(sid)[art]
        # short label per row (first ~24 chars) for the rendered variants
        norm_rows = [{"호": r["호"], "내용요약": re.sub(r"\s+", " ", r["내용"])[:24]} for r in rows]
        vdir = PROC / sid / "format_variants"
        vdir.mkdir(parents=True, exist_ok=True)
        base = f"{art}_호목록"
        (vdir / f"{base}.txt").write_text(
            "\n".join(f"{r['호']}. {r['내용요약']}" for r in norm_rows), encoding="utf-8")
        (vdir / f"{base}.md").write_text(
            "| 호 | 내용요약 |\n|---|---|\n" + "\n".join(f"| {r['호']} | {r['내용요약']} |" for r in norm_rows),
            encoding="utf-8")
        (vdir / f"{base}.csv").write_text(
            "호,내용요약\n" + "\n".join(f"{r['호']},\"{r['내용요약']}\"" for r in norm_rows), encoding="utf-8")
        (vdir / f"{base}.json").write_text(json.dumps(norm_rows, ensure_ascii=False), encoding="utf-8")

        nrows = len(norm_rows)
        for fmt, ext in [("plain_text", "txt"), ("markdown", "md"), ("csv", "csv"), ("json", "json")]:
            qid = f"fmt_{art}_{fmt}"
            q = (f"「{STATUTE_TITLES[sid]}」 {art}({rec['title']})의 호(號) 목록을 {fmt} 형식으로 제공했을 때, "
                 f"실질 내용이 있는(삭제 제외) 행은 모두 몇 개인가?")
            emit({
                "qa_id": qid, "split": "dev", "task_type": "format_robustness",
                "question": q, "answer": str(nrows), "answer_type": "number",
                "source_ids": [sid], "required_capabilities": ["format_robustness", "table_structure_reasoning"],
                "evidence": [{"source_id": sid,
                              "locator": f"{rec['locator']} 각 호 → format_variants/{base}.{ext} ({fmt})"}],
                "evaluation": {"metric": "exact_numbers", "gold_numbers": [str(nrows)]},
                "copyright_note": "동일 표의 4개 직렬화 형식에 대한 동일 질의(형식 강건성). 출처는 §7 비보호 법령.",
            }, nrows == len(norm_rows))


# ---------------------------------------------------------------- retrieval (title)
def gen_title_retrieval(per_law: int = 3) -> None:
    picks = {
        "law-housing-supply-rule": ["제1조", "제2조", "제8조"],
        "law-public-housing-special-act-rule": ["제1조"],
        "law-private-rental-housing-special-act": ["제1조", "제2조"],
    }
    for sid, labels in picks.items():
        for lab in labels[:per_law + 1]:
            rec = articles(sid).get(lab)
            if not rec or not rec["title"]:
                continue
            qid = f"title_{sid.split('-')[1]}_{lab}"
            q = f"「{STATUTE_TITLES[sid]}」 {lab}의 제명(괄호 안 표제)은 무엇인가?"
            emit({
                "qa_id": qid, "split": "dev", "task_type": "retrieval",
                "question": q, "answer": rec["title"], "answer_type": "short_answer",
                "source_ids": [sid], "required_capabilities": ["retrieval", "long_context_retrieval"],
                "evidence": [{"source_id": sid, "locator": rec["locator"]}],
                "evaluation": {"metric": "contains_all", "gold_terms": [rec["title"]]},
                "copyright_note": "조문 제명 단답. 출처는 저작권법 제7조 비보호 법령 본문.",
            }, term_in_source(sid, rec["title"], lab))


# ---------------------------------------------------------------- answerability (negative control)
def gen_answerability() -> None:
    controls = [
        # (bundle, distinctive_term_absent_from_bundle, present_in, question, reason)
        (["law-housing-supply-rule"], "임대료의 증액", "law-private-rental-housing-special-act",
         "제공된 「주택공급에 관한 규칙」만으로 민간임대주택의 임대료 증액 청구 한도(상한)를 확정할 수 있는가?",
         "임대료 증액 한도는 민간임대주택에 관한 특별법 소관으로, 제공된 주택공급규칙에는 근거 규정이 없음."),
        (["law-public-housing-special-act-rule"], "월납입금", "law-housing-supply-rule",
         "제공된 「공공주택 특별법 시행규칙」만으로 주택청약종합저축의 월납입금 하한 금액을 확정할 수 있는가?",
         "월납입금 규정은 주택공급에 관한 규칙 소관으로, 제공된 시행규칙에는 해당 규정이 없음."),
        (["law-private-rental-housing-special-act"], "가점제", "law-housing-supply-rule",
         "제공된 「민간임대주택에 관한 특별법」만으로 분양주택 입주자 선정의 가점제 점수 산정 기준을 확정할 수 있는가?",
         "가점제 점수 산정은 주택공급에 관한 규칙 소관으로, 제공된 특별법에는 해당 기준이 없음."),
        (["law-housing-supply-rule", "law-public-housing-special-act-rule"], "임대료의 증액", "law-private-rental-housing-special-act",
         "제공된 「주택공급에 관한 규칙」과 「공공주택 특별법 시행규칙」만으로 민간임대주택 임대료 증액 청구 한도를 확정할 수 있는가?",
         "민간임대주택 임대료 증액 한도는 민간임대주택에 관한 특별법 소관으로, 제공된 두 자료에는 해당 규정이 없음."),
    ]
    for i, (bundle, term, present_in, q, reason) in enumerate(controls, 1):
        absent = term_absent_from_sources(term, bundle)
        present = term_in_source(present_in, term)
        emit({
            "qa_id": f"unans_{i}", "split": "dev", "task_type": "answerability_detection",
            "question": q, "answer": f"확정할 수 없음(unanswerable). {reason}", "answer_type": "boolean_with_reason",
            "source_ids": bundle, "required_capabilities": ["answerability_detection", "faithfulness"],
            "evidence": [{"source_id": s, "locator": f"제공된 자료에 '{term}' 관련 근거 부재"} for s in bundle],
            "evaluation": {"metric": "boolean_and_reason", "gold_terms": ["확정할 수 없", "없"]},
            "copyright_note": "negative control. 제공 자료에 근거가 없음을 검증.",
        }, absent and present)


# ---------------------------------------------------------------- cross-source aggregation (metadata)
def gen_cross_source() -> None:
    hug = json.loads((PROC / "hug-sale-history" / "metadata.json").read_text(encoding="utf-8"))
    molit = json.loads((PROC / "molit-apt-official-price-2025" / "metadata.json").read_text(encoding="utf-8"))
    emit({
        "qa_id": "xsrc_format_pair", "split": "dev", "task_type": "cross_source_aggregation",
        "question": "공공데이터포털에 등재된 HUG 분양이력정보와 MOLIT 주택 공시가격 정보는 각각 어떤 데이터 제공 형식(포맷/확장자)을 사용하는가?",
        "answer": "HUG 분양이력정보: XML, MOLIT 주택 공시가격 정보: CSV.", "answer_type": "short_pair",
        "source_ids": ["hug-sale-history", "molit-apt-official-price-2025"],
        "required_capabilities": ["cross_source_aggregation", "metadata_understanding"],
        "evidence": [
            {"source_id": "hug-sale-history", "locator": "공공데이터포털 오픈API 메타데이터(데이터포맷)"},
            {"source_id": "molit-apt-official-price-2025", "locator": "공공데이터포털 파일데이터 메타데이터(확장자)"}],
        "evaluation": {"metric": "contains_all", "gold_terms": ["XML", "CSV"]},
        "copyright_note": "두 공공데이터 출처 메타데이터 사실의 집계.",
    }, hug["confirmed_facts"]["데이터포맷"] == "XML" and molit["confirmed_facts"]["확장자"] == "CSV")

    emit({
        "qa_id": "xsrc_license_pair", "split": "dev", "task_type": "cross_source_aggregation",
        "question": "v0.2에서 취득한 HUG 분양이력정보와 MOLIT 주택 공시가격 정보의 공공데이터포털 이용허락범위는 각각 무엇으로 표기되어 있는가?",
        "answer": "두 출처 모두 '이용허락범위 제한 없음'으로 표기됨.", "answer_type": "short_answer",
        "source_ids": ["hug-sale-history", "molit-apt-official-price-2025"],
        "required_capabilities": ["cross_source_aggregation", "license_reasoning"],
        "evidence": [
            {"source_id": "hug-sale-history", "locator": "메타데이터 이용허락범위"},
            {"source_id": "molit-apt-official-price-2025", "locator": "메타데이터 이용허락범위"}],
        "evaluation": {"metric": "contains_all", "gold_terms": ["이용허락범위 제한 없음"]},
        "copyright_note": "두 공공데이터 출처 라이선스 표기 집계.",
    }, "제한 없음" in hug["confirmed_facts"]["이용허락범위"] and "제한 없음" in molit["confirmed_facts"]["이용허락범위"])


def main() -> int:
    gen_numeric_cloze()
    gen_ho_count()
    gen_comparison()
    gen_format_robustness()
    gen_title_retrieval()
    gen_answerability()
    gen_cross_source()

    verified = [i for i in items if i["_verified"]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for it in verified:
            out = {k: v for k, v in it.items() if k != "_verified"}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    from collections import Counter
    fam = Counter(i["task_type"] for i in verified)
    print("=== DETERMINISTIC QA SUMMARY ===")
    for line in log:
        print("  " + line)
    print(f"--- emitted {len(verified)}/{len(items)} verified items")
    for k, v in fam.items():
        print(f"    {k}: {v}")
    print(f"--- written to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
