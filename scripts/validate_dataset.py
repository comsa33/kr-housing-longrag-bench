#!/usr/bin/env python3
"""Validate KR-Housing-LongRAG-Bench seed files.

The validator intentionally avoids downloading source documents. It checks that
annotations reference known sources and do not include raw corpus fields.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW_FIELD_NAMES = {
    "raw_text",
    "raw_content",
    "document_text",
    "pdf_text",
    "hwp_text",
    "full_context",
}

# Scraped JS/HTML residue that must never reach public files (e.g. list-page onclick handlers leaking
# into a question's display title). The grounding verifier cannot catch these surface-quality artifacts.
FORBIDDEN_SURFACE = ("getDetailView", "return false", "onclick", "javascript:",
                     "serviceKey", "MY 신청현황", "서비스키 복사하기")
PUBLIC_SCAN_PATHS = ("data", "docs", "README.md", "DATASET_CARD.md")


def assert_no_surface_artifacts() -> None:
    hits: list[str] = []
    for rel in PUBLIC_SCAN_PATHS:
        p = ROOT / rel
        files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file()]
        for f in files:
            if "__pycache__" in f.parts:
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for tok in FORBIDDEN_SURFACE:
                if tok in text:
                    hits.append(f"{f.relative_to(ROOT)}: forbidden surface artifact {tok!r}")
    if hits:
        for h in hits[:30]:
            print(h, file=sys.stderr)
        raise SystemExit(f"{len(hits)} surface-artifact violation(s) in public files")


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            rows.append(row)
    return rows


def assert_unique(rows: list[dict], key: str, path: Path) -> None:
    seen: set[str] = set()
    for idx, row in enumerate(rows, 1):
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise SystemExit(f"{path}:{idx}: missing string key {key!r}")
        if value in seen:
            raise SystemExit(f"{path}:{idx}: duplicate {key}: {value}")
        seen.add(value)


def assert_no_raw_fields(obj: object, path: Path, context: str = "$") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in RAW_FIELD_NAMES:
                raise SystemExit(f"{path}:{context}: forbidden raw corpus field {key!r}")
            assert_no_raw_fields(value, path, f"{context}.{key}")
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            assert_no_raw_fields(value, path, f"{context}[{idx}]")


QA_REQUIRED = (
    "qa_id", "split", "task_type", "question", "answer", "answer_type",
    "source_ids", "required_capabilities", "evidence", "evaluation", "copyright_note",
)


def check_qa_rows(rows: list[dict], source_ids: set[str], path: Path, require_fields: bool = False) -> None:
    for row in rows:
        if require_fields:
            for field in QA_REQUIRED:
                if field not in row:
                    raise SystemExit(f"{path}:{row.get('qa_id')}: missing required field {field!r}")
            for ev in row.get("evidence", []):
                if "locator" not in ev or not ev.get("locator"):
                    raise SystemExit(f"{path}:{row.get('qa_id')}: evidence missing locator")
            if "metric" not in row.get("evaluation", {}):
                raise SystemExit(f"{path}:{row.get('qa_id')}: evaluation missing metric")
        for source_id in row.get("source_ids", []):
            if source_id not in source_ids:
                raise SystemExit(f"{path}:{row['qa_id']}: unknown source_id {source_id!r}")
        for evidence in row.get("evidence", []):
            evidence_source_id = evidence.get("source_id")
            if evidence_source_id not in source_ids:
                raise SystemExit(f"{path}:{row['qa_id']}: unknown evidence source_id {evidence_source_id!r}")


def main() -> int:
    source_rows = load_jsonl(DATA / "source_manifest.jsonl")
    excluded_rows = load_jsonl(DATA / "excluded_sources.jsonl")
    qa_rows = load_jsonl(DATA / "qa_seed.jsonl")
    blueprint_rows = load_jsonl(DATA / "task_blueprints.jsonl")

    assert_unique(source_rows, "source_id", DATA / "source_manifest.jsonl")
    assert_unique(excluded_rows, "source_id", DATA / "excluded_sources.jsonl")
    assert_unique(qa_rows, "qa_id", DATA / "qa_seed.jsonl")
    assert_unique(blueprint_rows, "blueprint_id", DATA / "task_blueprints.jsonl")

    source_ids = {row["source_id"] for row in source_rows}
    source_ids.update(row["source_id"] for row in excluded_rows)

    paths_rows = [
        (DATA / "source_manifest.jsonl", source_rows),
        (DATA / "excluded_sources.jsonl", excluded_rows),
        (DATA / "qa_seed.jsonl", qa_rows),
        (DATA / "task_blueprints.jsonl", blueprint_rows),
    ]

    # Optional candidate files (v0.2, v0.3): validated with stricter field requirements.
    v02_path = DATA / "qa_v0.2_candidates.jsonl"
    v02_rows = load_jsonl(v02_path) if v02_path.exists() else []
    if v02_rows:
        assert_unique(v02_rows, "qa_id", v02_path)
        paths_rows.append((v02_path, v02_rows))

    v03_path = DATA / "qa_v0.3_candidates.jsonl"
    v03_rows = load_jsonl(v03_path) if v03_path.exists() else []
    if v03_rows:
        assert_unique(v03_rows, "qa_id", v03_path)
        paths_rows.append((v03_path, v03_rows))

    v04_path = DATA / "qa_v0.4_candidates.jsonl"
    v04_rows = load_jsonl(v04_path) if v04_path.exists() else []
    if v04_rows:
        assert_unique(v04_rows, "qa_id", v04_path)
        paths_rows.append((v04_path, v04_rows))

    v05_path = DATA / "qa_v0.5_candidates.jsonl"
    v05_rows = load_jsonl(v05_path) if v05_path.exists() else []
    if v05_rows:
        assert_unique(v05_rows, "qa_id", v05_path)
        paths_rows.append((v05_path, v05_rows))

    for path, rows in paths_rows:
        for row in rows:
            assert_no_raw_fields(row, path)

    check_qa_rows(qa_rows, source_ids, DATA / "qa_seed.jsonl")
    if v02_rows:
        check_qa_rows(v02_rows, source_ids, v02_path, require_fields=True)
    if v03_rows:
        check_qa_rows(v03_rows, source_ids, v03_path, require_fields=True)
    if v04_rows:
        check_qa_rows(v04_rows, source_ids, v04_path, require_fields=True)
    if v05_rows:
        check_qa_rows(v05_rows, source_ids, v05_path, require_fields=True)

    for row in blueprint_rows:
        for source_id in row.get("bundle_sources", []):
            if source_id not in source_ids:
                raise SystemExit(f"{row['blueprint_id']}: unknown bundle source_id {source_id!r}")

    assert_no_surface_artifacts()

    extra = f", {len(v02_rows)} QA v0.2 candidates" if v02_rows else ""
    extra += f", {len(v03_rows)} QA v0.3 candidates" if v03_rows else ""
    extra += f", {len(v04_rows)} QA v0.4 candidates" if v04_rows else ""
    extra += f", {len(v05_rows)} QA v0.5 candidates" if v05_rows else ""
    print(f"OK: {len(source_rows)} sources, {len(qa_rows)} QA seed items, "
          f"{len(blueprint_rows)} blueprints{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

