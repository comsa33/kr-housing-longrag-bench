#!/usr/bin/env python3
"""Check whether the benchmark is ready for a public release.

This is intentionally stricter than validate_dataset.py. It can pass for a
future v0.4-public package and should fail/warn for v0.3-dev.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_FIELD_NAMES = {
    "raw_text",
    "raw_content",
    "document_text",
    "pdf_text",
    "hwp_text",
    "full_context",
}


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)


def warn(msg: str, warnings: list[str]) -> None:
    warnings.append(msg)


def scan_for_raw_fields(obj: object, where: str, failures: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in RAW_FIELD_NAMES:
                fail(f"{where}: forbidden raw field {key}", failures)
            scan_for_raw_fields(value, f"{where}.{key}", failures)
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            scan_for_raw_fields(value, f"{where}[{idx}]", failures)


def secret_values() -> list[str]:
    vals = []
    for p in [ROOT / "workspace_local/secrets/data_go_kr.key", ROOT / "workspace_local/secrets/hug_api.key"]:
        if p.exists():
            vals.append(p.read_text(encoding="utf-8").strip())
    return [v for v in vals if len(v) >= 20]


def check_secret_leakage(failures: list[str]) -> None:
    secrets = secret_values()
    if not secrets:
        return
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if ".git" in p.parts or "__pycache__" in p.parts:
            continue
        if "workspace_local" in p.parts and "secrets" in p.parts:
            continue
        text = p.read_bytes().decode("utf-8", errors="ignore")
        for secret in secrets:
            if secret and secret in text:
                fail(f"secret leaked into {p.relative_to(ROOT)}", failures)


def check_public_files_for_raw_terms(failures: list[str]) -> None:
    for rel in ["README.md", "DATASET_CARD.md", "data", "docs", "prompts", "scripts"]:
        p = ROOT / rel
        paths = [p] if p.is_file() else list(p.rglob("*"))
        for file in paths:
            if not file.is_file() or "__pycache__" in file.parts:
                continue
            if file.name == "check_public_release_readiness.py":
                continue
            text = file.read_bytes().decode("utf-8", errors="ignore")
            # Mentions in docs/scripts are allowed; actual object fields are checked through JSON.
            if re.search(r"BEGIN FULL CONTEXT|\\bPDF_TEXT_START\\b|\\bRAW_CORPUS_START\\b", text):
                fail(f"raw corpus marker in public file {file.relative_to(ROOT)}", failures)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa", default="data/qa_v0.5_candidates.jsonl")
    parser.add_argument("--min-qa", type=int, default=700)
    parser.add_argument("--min-announcements", type=int, default=8)
    parser.add_argument("--max-announcement-share", type=float, default=0.20)
    # provider/region diversity criteria — auto-applied only when QA rows carry a `provider` field (v0.5+)
    parser.add_argument("--min-providers", type=int, default=5)
    parser.add_argument("--max-provider-share", type=float, default=0.60)
    parser.add_argument("--min-sido", type=int, default=8)
    parser.add_argument("--allow-dev", action="store_true", help="Report failures but exit 0 with dev/seed status.")
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []

    qa_path = ROOT / args.qa
    rows = load_jsonl(qa_path)
    if not rows:
        fail(f"missing or empty QA file: {args.qa}", failures)
    if len(rows) < args.min_qa:
        fail(f"QA count {len(rows)} < required {args.min_qa}", failures)

    source_rows = load_jsonl(ROOT / "data/source_manifest.jsonl")
    source_ids = {row["source_id"] for row in source_rows}
    bundle_manifest_paths = [
        ROOT / "workspace_local/processed/bundles-v04/manifest.jsonl",
        ROOT / "workspace_local/processed/bundles/manifest.jsonl",
    ]
    bundle_rows = []
    for path in bundle_manifest_paths:
        bundle_rows.extend(load_jsonl(path))
    bundle_ids = {row.get("bundle_id") for row in bundle_rows}

    # Families excluded from the "non-table" dominance denominator (and numerator).
    TABLE_FAMILIES = {"table_numeric_reasoning", "format_robustness", "answerability_detection"}

    question_counts = Counter()
    family_counts = Counter()
    announcement_counts = Counter()          # distinctness: every announcement cited anywhere
    nontable_ann_counts = Counter()          # dominance: each announcement counted once per non-table row
    nontable_rows = 0
    public_context_rows = 0

    for idx, row in enumerate(rows, 1):
        where = f"{args.qa}:{idx}:{row.get('qa_id', '<no_id>')}"
        scan_for_raw_fields(row, where, failures)
        question_counts[row.get("question", "")] += 1
        fam = row.get("task_type", "")
        family_counts[fam] += 1
        for sid in row.get("source_ids", []):
            if sid not in source_ids:
                fail(f"{where}: unknown source_id {sid}", failures)
        bid = row.get("bundle_id")
        if bid:
            public_context_rows += 1
            if bid not in bundle_ids:
                fail(f"{where}: unknown bundle_id {bid}", failures)
        # collect the announcements cited by this row (dedup across announcement_ids + page_ids)
        row_anns = set(row.get("announcement_ids", []) or [])
        for pid in row.get("page_ids", []) or []:
            m = re.match(r"(.+)-p\d{3}$", pid)
            if m:
                row_anns.add(m.group(1))
        for a in row_anns:
            announcement_counts[a] += 1
        # Dominance is "share of NON-table QA contributed by one announcement": count consistently
        # within non-table families only, and at most once per row (no announcement_ids/page_ids
        # double-counting).
        if fam not in TABLE_FAMILIES:
            nontable_rows += 1
            for a in row_anns:
                nontable_ann_counts[a] += 1
        answer = str(row.get("answer", ""))
        if len(answer) > 120:
            fail(f"{where}: answer too long for public QA ({len(answer)} chars)", failures)
        for term in row.get("evaluation", {}).get("gold_terms", []) or []:
            if len(str(term)) > 40:
                fail(f"{where}: gold_term too long ({len(str(term))} chars)", failures)

    dupes = [q for q, n in question_counts.items() if q and n > 1]
    if dupes:
        fail(f"duplicate questions: {len(dupes)}", failures)

    if public_context_rows == 0:
        fail("no QA rows reference context bundles", failures)

    distinct_ann = len(announcement_counts)
    if distinct_ann < args.min_announcements:
        fail(f"distinct announcement count {distinct_ann} < required {args.min_announcements}", failures)
    if nontable_ann_counts:
        top_aid, top_count = nontable_ann_counts.most_common(1)[0]
        share = top_count / max(nontable_rows, 1)
        if share > args.max_announcement_share:
            fail(f"top announcement dominance {top_aid} share={share:.2%} of {nontable_rows} non-table QA "
                 f"> {args.max_announcement_share:.0%}", failures)
    else:
        warn("no announcement_ids/page_ids detected; dominance check weak", warnings)

    # provider / region diversity + split leakage + near-duplicate — applied only for v0.5+ rows.
    # Count only REAL announcement providers (exclude tabular public-data and comparison meta-buckets)
    # so the metric isn't inflated by MOLIT/HUG or '복수(비교)' rows.
    def _is_ann_provider(p: str) -> bool:
        return bool(p) and ("공공데이터" not in p) and (not p.startswith("복수"))

    any_provider = any(r.get("provider") for r in rows)
    provider_counts = Counter(r["provider"] for r in rows if _is_ann_provider(r.get("provider", "")))
    sido_set = {r.get("region_sido") for r in rows
                if _is_ann_provider(r.get("provider", "")) and r.get("region_sido") and r["region_sido"] != "복수"}
    htype_set = {r.get("housing_type") for r in rows if r.get("housing_type") and r.get("housing_type") != "복수"}
    n_providers = len(provider_counts)
    near_dups = 0
    if any_provider:
        ann_total = sum(provider_counts.values())
        if n_providers < args.min_providers:
            fail(f"announcement-provider diversity {n_providers} < required {args.min_providers}", failures)
        top_p, top_pc = provider_counts.most_common(1)[0]
        if top_pc / max(ann_total, 1) > args.max_provider_share:
            fail(f"provider dominance {top_p} share={top_pc/ann_total:.1%} of announcement QA > {args.max_provider_share:.0%}", failures)
        if len(sido_set) < args.min_sido:
            fail(f"announcement 시·도 coverage {len(sido_set)} < required {args.min_sido}", failures)
        # split leakage: no announcement in >1 evaluation split
        eval_splits = {"test_public", "test_hidden", "ood_provider", "ood_region", "ood_year"}
        ann_splits: dict = {}
        for r in rows:
            anns = set(r.get("announcement_ids", []) or [])
            for pid in r.get("page_ids", []) or []:
                m = re.match(r"(.+)-p\d{3}$", pid)
                if m:
                    anns.add(m.group(1))
            for a in anns:
                ann_splits.setdefault(a, set()).add(r.get("split"))
        leaks = [a for a, s in ann_splits.items() if len({x for x in s if x in eval_splits}) > 1]
        if leaks:
            fail(f"split leakage: {len(leaks)} announcements in >1 eval split", failures)
        # near-duplicate questions within a family (token Jaccard >= 0.92) — reported as warning
        by_fam: dict = {}
        for r in rows:
            by_fam.setdefault(r.get("task_type", ""), []).append(set(re.findall(r"[0-9A-Za-z가-힣]+", r.get("question", ""))))
        for fam, toks in by_fam.items():
            for i in range(len(toks)):
                for j in range(i + 1, len(toks)):
                    a, b = toks[i], toks[j]
                    if not a or not b:
                        continue
                    jac = len(a & b) / len(a | b)
                    if jac >= 0.92:
                        near_dups += 1
                        break
        if near_dups:
            warn(f"near-duplicate question pairs (Jaccard>=0.92): ~{near_dups} (parametric table QA expected)", warnings)

    check_secret_leakage(failures)
    check_public_files_for_raw_terms(failures)

    print("== public release readiness ==")
    print(f"qa_file: {args.qa}")
    print(f"qa_count: {len(rows)}")
    print(f"families: {dict(sorted(family_counts.items()))}")
    print(f"distinct_announcements: {distinct_ann}")
    if provider_counts:
        print(f"providers: {n_providers} {dict(provider_counts)}")
        print(f"시도: {len(sido_set)}  housing_types: {len(htype_set)}")
        print(f"splits: {dict(Counter(r.get('split','') for r in rows))}")
    print(f"bundle_count: {len(bundle_ids)}")
    print(f"warnings: {len(warnings)}")
    for msg in warnings:
        print(f"WARN: {msg}")
    print(f"failures: {len(failures)}")
    for msg in failures:
        print(f"FAIL: {msg}")

    if failures and args.allow_dev:
        print("STATUS: dev/seed only, not public-ready")
        return 0
    if failures:
        print("STATUS: not public-ready")
        return 1
    print("STATUS: public-ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
