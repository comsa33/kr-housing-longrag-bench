#!/usr/bin/env python3
"""Materialize internal long-context bundles (32k/64k/128k/256k tokens) for RAG-vs-full-context experiments.

Each bundle concatenates licensed internal text: LH announcement pages (target evidence) + statute
articles + serialized HUG/MOLIT rows (distractors). The LH announcement is placed at a controlled band
(early/middle/late) per tier so QA can reference a real `evidence_position`. Bundle text lives ONLY under
workspace_local/processed/bundles/ (internal); manifest.jsonl records each component's char range,
token offset, and position band so QA can map an evidence page/article to its position.

Token counts use tiktoken cl100k_base.
"""
from __future__ import annotations

import json
from pathlib import Path

import tiktoken

import qa_v03_common as C
import qa_common as V2

ENC = tiktoken.get_encoding("cl100k_base")
BUNDLES = C.ROOT / "workspace_local" / "processed" / "bundles"

TIERS = [("bundle_lh_hug_law_32k", "32k", 32000, "early"),
         ("bundle_lh_hug_law_64k", "64k", 64000, "middle"),
         ("bundle_lh_hug_law_128k", "128k", 128000, "late"),
         ("bundle_lh_hug_law_256k", "256k", 256000, "late")]
PRE_FRAC = {"early": 0.0, "middle": 0.40, "late": 0.62}


def toks(s: str) -> int:
    return len(ENC.encode(s))


def band(frac: float) -> str:
    return "early" if frac < 0.34 else ("middle" if frac < 0.67 else "late")


def lh_components() -> list[dict]:
    out = []
    for p in sorted(C.lh_pages(), key=lambda x: x["page_no"]):
        t = f"[LH공고 {p['page_id']} (p.{p['page_no']})]\n{p['text']}\n"
        out.append({"type": "lh_page", "id": p["page_id"], "text": t, "tokens": toks(t)})
    return out


def law_components() -> list[dict]:
    out = []
    for sid in ("law-housing-supply-rule", "law-public-housing-special-act-rule",
                "law-private-rental-housing-special-act"):
        for r in V2.load_jsonl(C.PROC / sid / "document_pages.jsonl"):
            if r.get("unit_type") != "article":
                continue
            t = f"[법령 {sid} {r['article_label']}({r['title']})]\n{r['text']}\n"
            out.append({"type": "law_article", "id": f"{sid}::{r['article_label']}",
                        "text": t, "tokens": toks(t)})
    return out


def row_block_components() -> list[dict]:
    """Serialize HUG + MOLIT rows into ~2k-token distractor blocks."""
    out = []
    lines, src = [], "molit"
    def flush(kind, lines):
        if not lines:
            return
        t = f"[{kind} rows]\n" + "\n".join(lines) + "\n"
        out.append({"type": f"{kind}_rows", "id": f"{kind}_block_{len(out)}", "text": t, "tokens": toks(t)})
    buf = []
    for r in C.molit_rows():
        buf.append(f"{r['_row_id']} | {r['_lawd_name']} {r['umdNm']} | {r['aptNm']} | "
                   f"{r['excluUseAr']}㎡ {r['floor']}층 {r['buildYear']}년 | {r['dealAmount']}만원 | {r['_deal_ymd']}")
        if len(buf) >= 60:
            flush("MOLIT", buf); buf = []
    flush("MOLIT", buf); buf = []
    for r in C.hug_rows():
        buf.append(f"{r['_row_id']} | {r.get('AREA_DTL_DCD_NM')} | {r.get('BSU_NM')} | "
                   f"TOT_HOCO={r.get('TOT_HOCO')} GNRL={r.get('GNRL_SILT_HOCO')} | "
                   f"공고승인일={r.get('COLL_ANNO_APVL_DT')} 분양개시일={r.get('SILT_OPEN_DT')}")
        if len(buf) >= 60:
            flush("HUG", buf); buf = []
    flush("HUG", buf)
    return out


def build():
    BUNDLES.mkdir(parents=True, exist_ok=True)
    lh = lh_components()
    distractors = law_components() + row_block_components()
    manifest = []

    for bundle_id, tier, target, lh_pos in TIERS:
        parts, cur_tok = [], 0
        di = 0

        def add(comp):
            nonlocal cur_tok
            parts.append(dict(comp))
            cur_tok += comp["tokens"]

        # 1) pre-distractor block to push LH to its band
        pre_target = PRE_FRAC[lh_pos] * target
        while cur_tok < pre_target and di < len(distractors):
            add(distractors[di]); di += 1
        # 2) LH announcement pages (as many as fit, leaving room for tail distractors)
        lh_budget = target * 0.92
        for comp in lh:
            if cur_tok + comp["tokens"] > lh_budget:
                break
            add(comp)
        # 3) fill remaining to target with distractors (cycling if needed)
        guard = 0
        while cur_tok < target and guard < 100000:
            if di >= len(distractors):
                di = 0  # cycle distractors for very large tiers
            if distractors:
                add(distractors[di]); di += 1
            guard += 1
            if not distractors:
                break

        # assemble text + char/token offsets
        text_parts, components = [], []
        char_off, tok_off = 0, 0
        for comp in parts:
            t = comp["text"]
            frac = (tok_off + comp["tokens"] / 2) / max(cur_tok, 1)
            components.append({"type": comp["type"], "id": comp["id"],
                               "char_start": char_off, "char_end": char_off + len(t),
                               "token_start": tok_off, "tokens": comp["tokens"],
                               "position_band": band(frac)})
            text_parts.append(t)
            char_off += len(t); tok_off += comp["tokens"]
        full = "".join(text_parts)
        (BUNDLES / f"{bundle_id}.txt").write_text(full, encoding="utf-8")

        lh_pages_in = [c["id"] for c in components if c["type"] == "lh_page"]
        lh_bands = sorted({c["position_band"] for c in components if c["type"] == "lh_page"})
        manifest.append({
            "bundle_id": bundle_id, "context_tier": tier, "target_tokens": target,
            "est_tokens": cur_tok, "char_len": len(full), "n_components": len(components),
            "lh_pages_included": lh_pages_in, "lh_position_bands": lh_bands,
            "file": f"workspace_local/processed/bundles/{bundle_id}.txt",
            "components": components,
        })
        print(f"  {bundle_id}: est_tokens={cur_tok} chars={len(full)} lh_pages={len(lh_pages_in)} "
              f"lh_bands={lh_bands}")

    with (BUNDLES / "manifest.jsonl").open("w", encoding="utf-8") as f:
        for m in manifest:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"  wrote manifest.jsonl ({len(manifest)} bundles)")


if __name__ == "__main__":
    build()
