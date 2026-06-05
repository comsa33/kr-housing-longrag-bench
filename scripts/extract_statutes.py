#!/usr/bin/env python3
"""Extract structured units from acquired statute HTML (National Law Information Center).

Outputs (internal only, under workspace_local/processed/{source_id}/):
  - document_pages.jsonl : one record per article (조) / addenda block, with locator + full text
  - chunks.jsonl         : retrieval chunks (article-level) with stable chunk_id + locator
  - tables.jsonl         : (a) in-text enumerations (각 호) normalized as tables,
                           (b) 별표(別表) references with flSeq download locators (content NOT extracted)
  - numeric_facts.jsonl  : regex-mined numeric provisions (value/unit/article) for deterministic QA + verify
  - extraction_report.json : tool versions, counts, failures, confidence notes

Structure of lsInfoR.do body (observed):
  - <div class="lawcon">  : one per article; text begins "제N조(제목) ..." with 항(①②③) / 호(1.2.3.) lines
  - preceding <a id="J{n}:0"> anchors carry the article ordinal
  - 별표 attachments are separate HWPX/PDF files referenced via flDownload.do?flSeq=...&bylClsCd=...
    (their tabular content is NOT inline; extraction deferred to a later batch).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "workspace_local" / "raw"
PROC = ROOT / "workspace_local" / "processed"

STATUTES = {
    "law-housing-supply-rule": {"title": "주택공급에 관한 규칙", "efYd": "20150608", "lsiSeq": 171762},
    "law-public-housing-special-act-rule": {"title": "공공주택 특별법 시행규칙", "efYd": "20180928", "lsiSeq": 204719},
    "law-private-rental-housing-special-act": {"title": "민간임대주택에 관한 특별법", "efYd": "20151229", "lsiSeq": 174472},
}

ART_RE = re.compile(r"^제(\d+)조(?:의(\d+))?\s*(?:\(([^)]*)\))?")
# numeric provision patterns -> (regex, unit_kind)
NUM_PATTERNS = [
    (re.compile(r"(\d[\d,]*)\s*제곱미터"), "area_m2"),
    (re.compile(r"(\d[\d,]*)\s*퍼센트"), "percent"),
    (re.compile(r"100분의\s*(\d[\d,]*)"), "percent"),
    (re.compile(r"(\d[\d,]*)\s*일(?![\w가-힣])"), "days"),
    (re.compile(r"(\d[\d,]*)\s*개월"), "months"),
    (re.compile(r"(\d[\d,]*)\s*년(?![\w가-힣])"), "years"),
    (re.compile(r"(\d[\d,]*)\s*세대"), "households"),
    (re.compile(r"(\d[\d,]*)\s*세(?![\w가-힣대])"), "age_years"),
    (re.compile(r"(\d[\d,]*)\s*배(?![\w가-힣])"), "multiplier"),
    (re.compile(r"(\d[\d,]*)\s*만\s*원"), "won_10k"),
    (re.compile(r"(\d[\d,]*)\s*원(?![\w가-힣])"), "won"),
]


def article_no_str(num: str, sub: str | None) -> str:
    return f"제{num}조" + (f"의{sub}" if sub else "")


def clean(txt: str) -> str:
    txt = txt.replace("\xa0", " ")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


def mine_numbers(article_label: str, text: str) -> list[dict]:
    facts = []
    for rx, kind in NUM_PATTERNS:
        for m in rx.finditer(text):
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            facts.append({
                "article": article_label,
                "unit_kind": kind,
                "value_raw": m.group(1).replace(",", ""),
                "match": m.group(0),
                "context": clean(text[start:end]),
            })
    return facts


def extract_one(source_id: str, meta: dict) -> dict:
    src_dir = RAW / source_id
    html_files = sorted(src_dir.glob("*lsInfoR*.html"))
    if not html_files:
        return {"source_id": source_id, "ok": False, "error": "no lsInfoR html in raw"}
    html_path = html_files[0]
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")

    out_dir = PROC / source_id
    out_dir.mkdir(parents=True, exist_ok=True)

    pages, chunks, tables, numeric_facts = [], [], [], []
    seen_articles = set()
    locator_base = f"{meta['title']} [시행 {meta['efYd'][:4]}.{int(meta['efYd'][4:6])}.{int(meta['efYd'][6:8])}.] lsiSeq={meta['lsiSeq']}"

    for idx, lc in enumerate(soup.select("div.lawcon")):
        text = clean(lc.get_text("\n", strip=True))
        if not text:
            continue
        m = ART_RE.match(text)
        if m:
            label = article_no_str(m.group(1), m.group(2))
            title = m.group(3) or ""
            unit_type = "article"
        else:
            # addenda / non-article content block
            label = f"block_{idx}"
            title = ""
            unit_type = "block"
        if label in seen_articles:
            label = f"{label}#{idx}"
        seen_articles.add(label)

        # count 항(①-⑮) and 호(1. 2. ...) markers for structural locators
        hang = re.findall(r"[①-⑮]", text)
        ho = re.findall(r"(?m)^\s*(\d+)\.\s", text)
        byeolpyo_refs = sorted(set(re.findall(r"별표\s*\d*(?:의\d+)?", text)))

        locator = f"{locator_base} / {label}" + (f"({title})" if title else "")
        rec = {
            "source_id": source_id,
            "unit_type": unit_type,
            "article_label": label,
            "title": title,
            "char_len": len(text),
            "n_hang": len(hang),
            "n_ho": len(ho),
            "byeolpyo_refs": byeolpyo_refs,
            "locator": locator,
            "anchor_index": idx,
            "text": text,  # internal-only; never released
        }
        pages.append(rec)

        chunks.append({
            "chunk_id": f"{source_id}::{label}",
            "source_id": source_id,
            "locator": locator,
            "char_len": len(text),
            "text": text,
        })

        if unit_type == "article":
            numeric_facts.extend(mine_numbers(label, text))

            # in-text enumeration (각 호) -> normalized table for table/format-robustness tasks
            ho_rows = []
            for hm in re.finditer(r"(?m)^\s*(\d+)\.\s*(.+?)(?=\n\s*\d+\.\s|\Z)", text, re.S):
                cell = clean(hm.group(2))
                if 0 < len(cell) <= 400:
                    ho_rows.append({"호": int(hm.group(1)), "내용": cell})
            if len(ho_rows) >= 3:
                tables.append({
                    "table_id": f"{source_id}::{label}::호목록",
                    "source_id": source_id,
                    "kind": "in_text_enumeration",
                    "locator": locator + " 각 호",
                    "columns": ["호", "내용"],
                    "n_rows": len(ho_rows),
                    "rows": ho_rows,
                })

    # 별표 references (content in separate HWPX/PDF; record locator only)
    byl_refs = {}
    for a in soup.find_all("a", href=True):
        h = a["href"]
        m = re.search(r"flDownload\.do\?[^\"']*flSeq=(\d+)[^\"']*bylClsCd=(\d+)", h)
        if m:
            ext = (re.search(r"flExt=(\w+)", h) or [None, None])[1]
            byl_refs[m.group(1)] = {"flSeq": m.group(1), "bylClsCd": m.group(2), "flExt": ext}
    for fl in byl_refs.values():
        tables.append({
            "table_id": f"{source_id}::byeolpyo::flSeq{fl['flSeq']}",
            "source_id": source_id,
            "kind": "byeolpyo_attachment_reference",
            "locator": f"{locator_base} / 별표·서식 첨부 flSeq={fl['flSeq']} bylClsCd={fl['bylClsCd']} ext={fl['flExt']}",
            "download_url": f"https://www.law.go.kr/LSW/flDownload.do?flSeq={fl['flSeq']}&bylClsCd={fl['bylClsCd']}",
            "content_extracted": False,
            "note": "별표/서식은 HWPX/PDF 첨부. 표 내용 추출은 다음 batch로 연기(HWPX XML 파싱 필요).",
        })

    def dump(name, rows):
        with (out_dir / name).open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dump("document_pages.jsonl", pages)
    dump("chunks.jsonl", chunks)
    dump("tables.jsonl", tables)
    dump("numeric_facts.jsonl", numeric_facts)

    n_articles = sum(1 for p in pages if p["unit_type"] == "article")
    report = {
        "source_id": source_id,
        "title": meta["title"],
        "source_html": html_path.name,
        "tooling": {"python": sys.version.split()[0], "parser": "beautifulsoup4+lxml"},
        "counts": {
            "blocks_total": len(pages),
            "articles": n_articles,
            "chunks": len(chunks),
            "in_text_tables": sum(1 for t in tables if t["kind"] == "in_text_enumeration"),
            "byeolpyo_references": sum(1 for t in tables if t["kind"] == "byeolpyo_attachment_reference"),
            "numeric_facts": len(numeric_facts),
            "total_chars": sum(p["char_len"] for p in pages),
        },
        "failures": [
            {"item": "별표(別表) tabular content",
             "reason": "별표는 본문 HTML에 텍스트로 임베드되지 않고 HWPX/PDF 첨부로 분리됨.",
             "fallback": "flSeq download locator를 tables.jsonl에 보존. 다음 batch에서 HWPX(zip+XML) 파싱으로 셀 추출 예정."}
        ],
        "confidence": "high for article text & locators (clean HTML, no OCR); numeric_facts are regex-mined candidates "
                      "and are re-verified per-QA against the cited article text.",
    }
    (out_dir / "extraction_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"source_id": source_id, "ok": True, **report["counts"]}


def main() -> int:
    results = [extract_one(sid, meta) for sid, meta in STATUTES.items()]
    print("=== EXTRACTION SUMMARY ===")
    for r in results:
        if r.get("ok"):
            print(f"  OK   {r['source_id']:42s} arts={r['articles']:>3} chunks={r['chunks']:>3} "
                  f"in_text_tables={r['in_text_tables']:>2} byl_refs={r['byeolpyo_references']:>2} "
                  f"num_facts={r['numeric_facts']:>4} chars={r['total_chars']:>7}")
        else:
            print(f"  FAIL {r['source_id']}: {r.get('error')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
