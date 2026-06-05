#!/usr/bin/env python3
"""Extract per-page text records from the internally stored LH announcement PDF."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "workspace_local" / "raw" / "lh-sale-announcements"
PROC_DIR = ROOT / "workspace_local" / "processed" / "lh-sale-announcements"
PDF_NAME = "lh_daedong2_b1_public_sale_announcement_20251017.pdf"
TEXT_NAME = "lh_daedong2_b1_public_sale_announcement_20251017_pdf.txt"


def normalize_page_text(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def extract_numeric_facts(page_id: str, page_no: int, text: str) -> list[dict]:
    facts: list[dict] = []
    for idx, match in enumerate(re.finditer(r"\d[\d,]*(?:\.\d+)?\s*(?:세대|원|만원|㎡|%|일|회|개월|년)", text), 1):
        snippet_start = max(0, match.start() - 80)
        snippet_end = min(len(text), match.end() + 80)
        snippet = re.sub(r"\s+", " ", text[snippet_start:snippet_end]).strip()
        facts.append({
            "fact_id": f"{page_id}-num-{idx:03d}",
            "page_no": page_no,
            "value_text": match.group(0).strip(),
            "locator": f"{PDF_NAME}#page={page_no}",
            "local_snippet": snippet,
        })
    return facts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default=str(RAW_DIR / PDF_NAME))
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"Missing PDF: {pdf_path}")
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    txt_path = PROC_DIR / TEXT_NAME
    subprocess.run(["pdftotext", "-layout", str(pdf_path), str(txt_path)], check=True)
    raw_text = txt_path.read_text(encoding="utf-8", errors="replace")
    pages = [normalize_page_text(page) for page in raw_text.split("\f")]
    pages = [page for page in pages if page.strip()]

    page_rows = []
    numeric_rows = []
    for page_no, text in enumerate(pages, 1):
        page_id = f"lh-daedong2-b1-public-sale-20251017-p{page_no:03d}"
        row = {
            "source_id": "lh-sale-announcements",
            "announcement_id": "lh-daedong2-b1-public-sale-20251017",
            "page_id": page_id,
            "page_no": page_no,
            "locator": f"{PDF_NAME}#page={page_no}",
            "char_count": len(text),
            "text": text,
        }
        page_rows.append(row)
        numeric_rows.extend(extract_numeric_facts(page_id, page_no, text))

    pages_path = PROC_DIR / "document_pages.jsonl"
    with pages_path.open("w", encoding="utf-8") as f:
        for row in page_rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    numeric_path = PROC_DIR / "numeric_facts.jsonl"
    with numeric_path.open("w", encoding="utf-8") as f:
        for row in numeric_rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    report = {
        "source_id": "lh-sale-announcements",
        "announcement_id": "lh-daedong2-b1-public-sale-20251017",
        "input_pdf": f"workspace_local/raw/lh-sale-announcements/{pdf_path.name}",
        "text_file": f"workspace_local/processed/lh-sale-announcements/{txt_path.name}",
        "document_pages_file": "workspace_local/processed/lh-sale-announcements/document_pages.jsonl",
        "numeric_facts_file": "workspace_local/processed/lh-sale-announcements/numeric_facts.jsonl",
        "page_count": len(page_rows),
        "char_count": sum(row["char_count"] for row in page_rows),
        "numeric_fact_count": len(numeric_rows),
        "extraction_tool": "pdftotext -layout",
    }
    report_path = PROC_DIR / "extraction_report_v0.3.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: extracted {len(page_rows)} pages, {report['char_count']} chars, {len(numeric_rows)} numeric facts")
    print(f"pages: {pages_path}")
    print(f"numeric: {numeric_path}")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
