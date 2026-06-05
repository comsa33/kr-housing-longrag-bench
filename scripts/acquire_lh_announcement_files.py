#!/usr/bin/env python3
"""Acquire an official LH apartment announcement PDF/HWP for internal v0.3 work.

This script downloads only the official "입주자모집공고문" attachments from a
public LH announcement page. Raw source files remain under workspace_local/,
which is gitignored. Public benchmark release should provide source URLs,
file IDs, locators, and QA labels rather than bundling these raw files.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from email.message import Message
from pathlib import Path
from urllib.parse import unquote

import requests


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "workspace_local" / "raw" / "lh-sale-announcements"
PROC_DIR = ROOT / "workspace_local" / "processed" / "lh-sale-announcements"
AUDIT_DIR = ROOT / "workspace_local" / "audit"

SOURCE_ID = "lh-sale-announcements"
ANNOUNCEMENT_ID = "lh-daedong2-b1-public-sale-20251017"
PAGE_URL = (
    "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancInfo.do"
    "?aisTpCd=05&ccrCnntSysDsCd=02&mi=1027&panId=0000060998&uppAisTpCd=05"
)
FILES = [
    {
        "file_id": "63915772",
        "kind": "announcement_pdf",
        "filename": "lh_daedong2_b1_public_sale_announcement_20251017.pdf",
        "expected_prefix_hex": "25504446",
    },
    {
        "file_id": "63915773",
        "kind": "announcement_hwp",
        "filename": "lh_daedong2_b1_public_sale_announcement_20251017.hwp",
        "expected_prefix_hex": "d0cf11e0",
    },
]


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def decode_content_disposition(value: str) -> str:
    """Best-effort decode for servers that send UTF-8 bytes as latin-1 header text."""
    if not value:
        return ""
    msg = Message()
    msg["content-disposition"] = value
    filename = msg.get_filename() or ""
    if not filename:
        m = re.search(r'filename\*?=(?:"([^"]+)"|([^;]+))', value)
        filename = (m.group(1) or m.group(2)).strip() if m else value
    filename = unquote(filename.strip("\"'"))
    try:
        filename = filename.encode("latin-1").decode("utf-8")
    except UnicodeError:
        pass
    return filename


def strip_tags(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_attachment_labels(page_text: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    pattern = re.compile(r"<a[^>]+href=\"javascript:fileDownLoad\('([^']+)'\);\"[^>]*>(.*?)</a>", re.S)
    for file_id, label_html in pattern.findall(page_text):
        labels[file_id] = strip_tags(label_html)
    return labels


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (KR-Housing-LongRAG-Bench dataset builder; research use)",
        "Referer": "https://apply.lh.or.kr/",
    })

    page_response = session.get(PAGE_URL, timeout=60)
    page_response.raise_for_status()
    page_bytes = page_response.content
    page_path = RAW_DIR / f"{ANNOUNCEMENT_ID}.html"
    page_path.write_bytes(page_bytes)
    page_text = page_response.text
    labels = extract_attachment_labels(page_text)
    visible_text = strip_tags(page_text)
    visible_text_path = PROC_DIR / f"{ANNOUNCEMENT_ID}_page_visible_text.txt"
    visible_text_path.write_text(visible_text, encoding="utf-8")

    downloaded_files = []
    for item in FILES:
        url = f"https://apply.lh.or.kr/lhapply/lhFile.do?fileid={item['file_id']}"
        response = session.get(url, timeout=120)
        response.raise_for_status()
        data = response.content
        prefix = data[:4].hex()
        expected = item["expected_prefix_hex"]
        if not prefix.startswith(expected):
            raise RuntimeError(
                f"{item['file_id']} returned unexpected prefix {prefix}; expected {expected}"
            )
        path = RAW_DIR / item["filename"]
        path.write_bytes(data)
        downloaded_files.append({
            "file_id": item["file_id"],
            "kind": item["kind"],
            "filename": f"workspace_local/raw/lh-sale-announcements/{item['filename']}",
            "official_label": labels.get(item["file_id"], ""),
            "download_url_without_session": url,
            "content_disposition_filename": decode_content_disposition(
                response.headers.get("Content-Disposition", "")
            ),
            "content_type": response.headers.get("Content-Type", ""),
            "sha256": sha256_bytes(data),
            "bytes": len(data),
        })

    audit = {
        "source_id": SOURCE_ID,
        "batch": "v0.3",
        "announcement_id": ANNOUNCEMENT_ID,
        "provider": "한국토지주택공사",
        "title": "대전대동2 1블록 공공분양 입주자모집공고",
        "official_page_url": PAGE_URL,
        "page_file": f"workspace_local/raw/lh-sale-announcements/{page_path.name}",
        "page_sha256": sha256_bytes(page_bytes),
        "processed_visible_text_file": (
            f"workspace_local/processed/lh-sale-announcements/{visible_text_path.name}"
        ),
        "downloaded_files": downloaded_files,
        "license_observation": {
            "status": "public_official_announcement_internal_use",
            "basis": "Official LH public announcement page; keep raw files internal and release URL/locators only.",
        },
        "release_decision": "do_not_redistribute_raw_pdf_hwp_release_url_locators_and_qa_only",
        "notes": "Only official 모집공고문 PDF/HWP were downloaded; pamphlet/forms/floor-plan assets were not acquired.",
    }
    audit_path = AUDIT_DIR / f"{ANNOUNCEMENT_ID}.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: acquired {len(downloaded_files)} LH announcement files")
    for f in downloaded_files:
        print(f"  {f['kind']}: {f['filename']} ({f['bytes']} bytes)")
    print(f"audit: {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
