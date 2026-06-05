#!/usr/bin/env python3
"""Materialize internal multi-announcement long-context bundles for v0.4 (32k..512k tokens).

Bundle families guarantee that every announcement's evidence pages are available at the band each
QA family needs:
  - <ann>_early_<tier>  : the announcement is placed first  -> its early pages sit in the 'early' band
                          (long_context_retrieval)
  - <ann>_late_<tier>   : distractors fill ~62% first, then the announcement -> its pages sit 'late'
                          (long_distance_retrieval)
  - mix_announce_512k   : announcement-heavy; all announcements' lead pages + light law/row padding
  - mix_law_256k        : law-heavy; statutes first then all announcements' lead pages (cross_document_legal)
  - mix_table_128k      : table-heavy; MOLIT/HUG row blocks then announcement lead pages (cross_source context)
The three mix bundles contain every announcement's lead pages, so cross-document / multi-document QA
that cite any lead page + a statute resolve to evidence_position='multi'.

Bundle text lives ONLY under workspace_local/processed/bundles-v04/ (internal, gitignored). The public
manifest records each component's char/token offset + position band so QA can map a page to its position.
Token counts use tiktoken cl100k_base.
"""
from __future__ import annotations

import json

import tiktoken

import qa_common as V2
import qa_v03_common as C
import qa_v04_common as Q

ENC = tiktoken.get_encoding("cl100k_base")
BUNDLES = Q.BUNDLES_V04
LEAD_PAGES = 8  # how many lead pages of each announcement go into mix bundles

TIERS = {"32k": 32000, "64k": 64000, "128k": 128000, "256k": 256000, "512k": 512000}
# which focused bundles to build (announcement placed early or late) and at which tiers
EARLY_TIERS = ["32k", "128k"]
LATE_TIERS = ["64k", "256k"]
PRE_FRAC_LATE = 0.62


def toks(s: str) -> int:
    return len(ENC.encode(s))


def band(frac: float) -> str:
    return "early" if frac < 0.34 else ("middle" if frac < 0.67 else "late")


# ---- component factories -----------------------------------------------------
def ann_components(ann_id: str, max_page: int | None = None) -> list:
    out = []
    for p in sorted(Q.ann_pages(ann_id), key=lambda x: x["page_no"]):
        if max_page and p["page_no"] > max_page:
            continue
        t = f"[LH공고 {ann_id} (p.{p['page_no']})]\n{p['text']}\n"
        out.append({"type": "lh_page", "id": p["page_id"], "text": t, "tokens": toks(t)})
    return out


def law_components() -> list:
    out = []
    for sid in Q.STATUTES:
        for r in V2.load_jsonl(C.PROC / sid / "document_pages.jsonl"):
            if r.get("unit_type") != "article":
                continue
            t = f"[법령 {sid} {r['article_label']}({r.get('title','')})]\n{r['text']}\n"
            out.append({"type": "law_article", "id": f"{sid}::{r['article_label']}", "text": t, "tokens": toks(t)})
    return out


def row_block_components() -> list:
    out, buf = [], []

    def flush(kind, lines):
        if not lines:
            return
        t = f"[{kind} rows]\n" + "\n".join(lines) + "\n"
        out.append({"type": f"{kind.lower()}_rows", "id": f"{kind.lower()}_block_{len(out)}", "text": t, "tokens": toks(t)})

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


# ---- bundle assembly ---------------------------------------------------------
def assemble(bundle_id, tier, template, ordered_parts, target):
    """ordered_parts: list of component dicts already in final order; pad with distractors to target."""
    parts = [dict(c) for c in ordered_parts]
    cur = sum(c["tokens"] for c in parts)
    di = 0
    guard = 0
    while cur < target and guard < 200000:
        if di >= len(DISTRACTORS):
            di = 0
        if not DISTRACTORS:
            break
        c = DISTRACTORS[di]; di += 1; guard += 1
        parts.append(dict(c)); cur += c["tokens"]

    text_parts, components = [], []
    char_off, tok_off = 0, 0
    for c in parts:
        t = c["text"]
        frac = (tok_off + c["tokens"] / 2) / max(cur, 1)
        components.append({"type": c["type"], "id": c["id"],
                           "char_start": char_off, "char_end": char_off + len(t),
                           "token_start": tok_off, "tokens": c["tokens"], "position_band": band(frac)})
        text_parts.append(t)
        char_off += len(t); tok_off += c["tokens"]
    full = "".join(text_parts)
    (BUNDLES / f"{bundle_id}.txt").write_text(full, encoding="utf-8")
    lh_pages_in = [c["id"] for c in components if c["type"] == "lh_page"]
    lh_bands = sorted({c["position_band"] for c in components if c["type"] == "lh_page"})
    return {
        "bundle_id": bundle_id, "context_tier": tier, "template": template,
        "target_tokens": target, "est_tokens": cur, "char_len": len(full),
        "n_components": len(components), "lh_pages_included": lh_pages_in, "lh_position_bands": lh_bands,
        "file": f"workspace_local/processed/bundles-v04/{bundle_id}.txt", "components": components,
    }


DISTRACTORS: list = []


def build():
    global DISTRACTORS
    BUNDLES.mkdir(parents=True, exist_ok=True)
    laws = law_components()
    rows = row_block_components()
    DISTRACTORS = laws + rows
    manifest = []
    anns = list(Q.announcement_ids())

    # 1) per-announcement early-focused + late-focused bundles
    for ann_id in anns:
        comps = ann_components(ann_id)
        for tier in EARLY_TIERS:
            target = TIERS[tier]
            # announcement first (its early pages -> early band), capped to ~90% so tail distractors exist
            lead = []
            budget = target * 0.9
            cur = 0
            for c in comps:
                if cur + c["tokens"] > budget:
                    break
                lead.append(c); cur += c["tokens"]
            manifest.append(assemble(f"{ann_id}__early_{tier}", tier, "announcement_focus_early", lead, target))
        for tier in LATE_TIERS:
            target = TIERS[tier]
            # Place the announcement at the very END so all its pages (esp. later doc pages) land 'late'.
            # Cap announcement to <=40% of the tier, pad the front with distractors to fill the rest.
            ann_cap = target * 0.40
            # take the TAIL pages of the announcement (long_distance cites later doc pages), in order
            lead, atok = [], 0
            for c in reversed(comps):
                if atok + c["tokens"] > ann_cap:
                    break
                lead.insert(0, c); atok += c["tokens"]
            pre, cur, di = [], 0, 0
            front_budget = target - atok - 2000
            while cur < front_budget and di < len(DISTRACTORS):
                pre.append(DISTRACTORS[di]); cur += DISTRACTORS[di]["tokens"]; di += 1
            # pass target=current sum so assemble does NOT pad after the announcement (keeps it at the tail)
            parts = pre + lead
            manifest.append(assemble(f"{ann_id}__late_{tier}", tier, "announcement_focus_late",
                                     parts, sum(c["tokens"] for c in parts)))

    # 2) mix bundles containing every announcement's lead pages (for multi / cross-document / cross-source)
    lead_all = []
    for ann_id in anns:
        lead_all.extend(ann_components(ann_id, max_page=LEAD_PAGES))

    # announcement-heavy 512k: all lead pages first, light padding
    manifest.append(assemble("mix_announce_512k", "512k", "announcement_heavy", lead_all, TIERS["512k"]))
    # law-heavy 256k: statutes first, then all lead pages
    manifest.append(assemble("mix_law_256k", "256k", "law_heavy", laws + lead_all, TIERS["256k"]))
    # table-heavy 128k: row blocks first, then all lead pages (those that fit)
    manifest.append(assemble("mix_table_128k", "128k", "table_heavy", rows[:40] + lead_all, TIERS["128k"]))

    with (BUNDLES / "manifest.jsonl").open("w", encoding="utf-8") as f:
        for m in manifest:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    from collections import Counter
    tiers = Counter(m["context_tier"] for m in manifest)
    print(f"=== BUNDLES v0.4: {len(manifest)} bundles ===")
    print("  by tier:", dict(tiers))
    # coverage report: which (page_id, band) demands can be served
    pos = Q.page_bundle_positions_v04.__wrapped__() if hasattr(Q.page_bundle_positions_v04, "__wrapped__") else None
    bands_per_page = {}
    for m in manifest:
        for c in m["components"]:
            if c["type"] == "lh_page":
                bands_per_page.setdefault(c["id"], set()).add(c["position_band"])
    pages_with_early = sum(1 for v in bands_per_page.values() if "early" in v)
    pages_with_late = sum(1 for v in bands_per_page.values() if "late" in v)
    print(f"  LH pages covered: {len(bands_per_page)} ; with early band: {pages_with_early} ; with late band: {pages_with_late}")
    print(f"  -> {BUNDLES / 'manifest.jsonl'}")


if __name__ == "__main__":
    build()
