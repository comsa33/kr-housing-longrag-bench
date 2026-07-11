#!/usr/bin/env python3
"""v0.5 WP2/WP3: deterministic table cell-grid extraction from announcement PDFs (PyMuPDF).

For each acquired LH-v04 announcement PDF, detect tables with fitz.find_tables() and emit a structured
cell grid so QA can target real announcement tables (eligibility matrices, supply-type tables, schedules,
unit price/area tables) — not just plain-text snippets.

Outputs per announcement (INTERNAL, under workspace_local/processed/lh-sale-announcements-v04/<ann>/):
  tables.jsonl       : one row per detected table (table_id, page_id, page_no, n_rows, n_cols, bbox, confidence)
  table_cells.jsonl  : one row per cell (table_id, page_id, row_index, col_index, row_header, col_header,
                       cell_text, normalized_value, unit, bbox, source_format, confidence)
Merged index: workspace_local/audit/index_cells_v05.json

page_id is aligned to the existing document_pages.jsonl: if the PDF page count matches the extracted
page count we map directly; otherwise we map each PDF page to the document page with the best text
overlap and skip cells whose page cannot be aligned (so cited page_ids always resolve).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import fitz  # PyMuPDF

import qa_v04_common as Q

PROC = Q.V04_DIR
AUDIT = Q.AUDIT
RAW = Q.ROOT / "workspace_local" / "raw" / "lh-sale-announcements-v04"
MERGED = AUDIT / "index_cells_v05.json"

UNIT_RE = re.compile(r"(만원|천원|원|세대|㎡|％|%|평|개월|년|월|일|회|호|층|배|점|명|가구|동)")
NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def normalize_value(cell_text: str):
    """Return (normalized_value: float|None, unit: str|None) from a cell's text."""
    t = (cell_text or "").replace("\n", " ")
    m = NUM_RE.search(t)
    val = None
    if m:
        try:
            val = float(m.group(0).replace(",", ""))
            if val == int(val):
                val = int(val)
        except ValueError:
            val = None
    u = UNIT_RE.search(t)
    unit = u.group(1) if u else None
    return val, unit


def align_pages(doc, ann_id: str):
    """Map fitz page index -> document_pages page_id. Returns dict pno0 -> page_id (or None)."""
    pages = Q.ann_pages(ann_id)
    by_no = {p["page_no"]: p for p in pages}
    out = {}
    if doc.page_count == len(pages):
        for i in range(doc.page_count):
            out[i] = Q.page_id_for(ann_id, i + 1)
        return out
    # fallback: content overlap matching
    def toks(s):
        return set(re.findall(r"[0-9A-Za-z가-힣]{2,}", s or ""))
    doc_tok = {p["page_no"]: toks(p["text"]) for p in pages}
    for i in range(doc.page_count):
        ftxt = toks(doc[i].get_text())
        best, best_no = 0.0, None
        for no, dt in doc_tok.items():
            if not dt:
                continue
            inter = len(ftxt & dt)
            score = inter / max(len(dt), 1)
            if score > best:
                best, best_no = score, no
        out[i] = Q.page_id_for(ann_id, best_no) if (best_no and best >= 0.5) else None
    return out


def extract_announcement(ann_id: str) -> dict:
    raw_dir = RAW / ann_id
    pdfs = sorted(raw_dir.glob("*.pdf"))
    if not pdfs:
        return {"announcement_id": ann_id, "tables": 0, "cells": 0, "skipped_pages": 0, "error": "no pdf"}
    doc = fitz.open(pdfs[0])
    page_map = align_pages(doc, ann_id)
    tables_rows, cell_rows = [], []
    skipped = 0
    for pno in range(doc.page_count):
        page_id = page_map.get(pno)
        if not page_id:
            skipped += 1
            continue
        page = doc[pno]
        try:
            found = page.find_tables()
        except Exception:
            continue
        for ti, tab in enumerate(found.tables, 1):
            try:
                grid = tab.extract()
            except Exception:
                continue
            if not grid or len(grid) < 2 or len(grid[0]) < 2:
                continue
            table_id = f"{page_id}-t{ti:02d}"
            n_rows, n_cols = len(grid), max(len(r) for r in grid)
            nonempty = sum(1 for r in grid for c in r if norm_ws(c))
            conf_table = round(nonempty / max(n_rows * n_cols, 1), 3)
            col_headers = [norm_ws(grid[0][j]) if j < len(grid[0]) else "" for j in range(n_cols)]
            tables_rows.append({
                "table_id": table_id, "page_id": page_id, "page_no": int(page_id.split("-p")[-1]),
                "n_rows": n_rows, "n_cols": n_cols, "col_headers": col_headers,
                "bbox": [round(x, 1) for x in tab.bbox], "source_format": "pdf",
                "confidence": conf_table,
            })
            for ri, row in enumerate(grid):
                row_header = norm_ws(row[0]) if row else ""
                for ci in range(n_cols):
                    raw = row[ci] if ci < len(row) else ""
                    ctext = norm_ws(raw)
                    if not ctext:
                        continue
                    val, unit = normalize_value(ctext)
                    # cell confidence: full if short clean cell, lower if very long (merged/noisy)
                    cconf = 1.0 if len(ctext) <= 40 else (0.6 if len(ctext) <= 120 else 0.3)
                    cell_rows.append({
                        "table_id": table_id, "page_id": page_id,
                        "row_index": ri, "col_index": ci,
                        "row_header": row_header, "col_header": col_headers[ci] if ci < len(col_headers) else "",
                        "cell_text": ctext,
                        "normalized_value": val, "unit": unit,
                        "bbox": None, "source_format": "pdf",
                        "confidence": round(min(conf_table + 0.0, cconf), 3),
                    })
    proc_dir = PROC / ann_id
    proc_dir.mkdir(parents=True, exist_ok=True)
    with (proc_dir / "tables.jsonl").open("w", encoding="utf-8") as f:
        for r in tables_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (proc_dir / "table_cells.jsonl").open("w", encoding="utf-8") as f:
        for r in cell_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"announcement_id": ann_id, "pdf": pdfs[0].name, "pages": doc.page_count,
            "tables": len(tables_rows), "cells": len(cell_rows), "skipped_pages": skipped}


def main() -> int:
    reports = []
    for ann_id in Q.announcement_ids():
        rep = extract_announcement(ann_id)
        reports.append(rep)
        print(f"  {ann_id[:46]:46s} tables={rep.get('tables',0):4d} cells={rep.get('cells',0):5d} "
              f"skipped_pages={rep.get('skipped_pages',0)}")
    idx = {
        "source_id": Q.LH_V04,
        "announcement_count": len(reports),
        "total_tables": sum(r.get("tables", 0) for r in reports),
        "total_cells": sum(r.get("cells", 0) for r in reports),
        "announcements_with_tables": sum(1 for r in reports if r.get("tables", 0) > 0),
        "reports": reports,
    }
    MERGED.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"=== CELLS v0.5: {idx['total_tables']} tables, {idx['total_cells']} cells across "
          f"{idx['announcements_with_tables']}/{len(reports)} announcements -> {MERGED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
