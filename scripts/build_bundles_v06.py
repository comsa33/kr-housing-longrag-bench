#!/usr/bin/env python3
"""v0.6 multi-provider long-context bundles (internal). Resolves the v0.4/v0.5 LH-only bundle limit.

Builds, over ALL 41 announcements across 10 providers (providers_v05):
  - <ann>__early_<tier>  : announcement first -> its early pages sit 'early'   (long_context_retrieval)
  - <ann>__late_<tier>   : distractors first, announcement tail last -> 'late'  (long_distance_retrieval)
  - mix_multiprovider_<tier> : interleaved lead pages from MANY providers + law/row distractors
                               (multi position; cross_source / cross_document / comparison context)
Tiers: 32k/64k/128k/256k/512k. Bundle TEXT stays internal under workspace_local/processed/bundles-v06/.
The manifest records metadata only (bundle_id, tier, template, providers, announcement_ids, source_mix,
token_estimate, component_positions) — no document text.
"""
from __future__ import annotations

import json
from collections import Counter

import tiktoken

import qa_common as V2
import qa_v03_common as C
import providers_v05 as P

ENC = tiktoken.get_encoding("cl100k_base")
BUNDLES = C.ROOT / "workspace_local" / "processed" / "bundles-v06"
LEAD = 6
TIERS = {"32k": 32000, "64k": 64000, "128k": 128000, "256k": 256000, "512k": 512000}
EARLY_TIERS = ["32k", "64k"]
LATE_TIERS = ["128k", "256k"]


def toks(s: str) -> int:
    return len(ENC.encode(s))


def band(frac: float) -> str:
    return "early" if frac < 0.34 else ("middle" if frac < 0.67 else "late")


def ann_components(ann_id: str, max_page=None) -> list:
    out = []
    for p in sorted(P.pages(ann_id), key=lambda x: x["page_no"]):
        if max_page and p["page_no"] > max_page:
            continue
        t = f"[공고 {P.provider_of(ann_id)} {p['page_id']} (p.{p['page_no']})]\n{p['text']}\n"
        out.append({"type": "lh_page", "id": p["page_id"], "ann": ann_id, "text": t, "tokens": toks(t)})
    return out


def law_components() -> list:
    out = []
    for sid in P.Q.STATUTES if hasattr(P, "Q") else ("law-housing-supply-rule", "law-public-housing-special-act-rule", "law-private-rental-housing-special-act"):
        for r in V2.load_jsonl(C.PROC / sid / "document_pages.jsonl"):
            if r.get("unit_type") != "article":
                continue
            t = f"[법령 {sid} {r['article_label']}({r.get('title','')})]\n{r['text']}\n"
            out.append({"type": "law_article", "id": f"{sid}::{r['article_label']}", "ann": None, "text": t, "tokens": toks(t)})
    return out


def row_block_components() -> list:
    out, buf = [], []

    def flush(kind, lines):
        if not lines:
            return
        t = f"[{kind} rows]\n" + "\n".join(lines) + "\n"
        out.append({"type": f"{kind.lower()}_rows", "id": f"{kind.lower()}_block_{len(out)}", "ann": None, "text": t, "tokens": toks(t)})

    for r in C.molit_rows():
        buf.append(f"{r['_row_id']} | {r['_lawd_name']} {r['umdNm']} | {r['aptNm']} | {r['excluUseAr']}㎡ {r['dealAmount']}만원 | {r['_deal_ymd']}")
        if len(buf) >= 60:
            flush("MOLIT", buf); buf = []
    flush("MOLIT", buf)
    return out


def hug_block_component() -> dict:
    """The complete HUG (주택도시보증공사) sale-history table as ONE guaranteed component.

    `cross_source_aggregation` questions aggregate over this table (count / avg TOT_HOCO by 지역·연도), so the
    bundle must embed it COMPLETELY (a partial/padding-truncated copy would change the count). Included
    verbatim and in full in the multi-provider mix bundle, never as a paddable distractor.
    """
    rows = sorted(C.hug_rows(), key=lambda r: (r.get("_query_area_name", ""), r.get("_query_year", ""), r.get("_row_id", "")))
    lines = [
        "===== [참고자료] HUG 분양이력 자료 (주택도시보증공사, 분양보증 발급 사업장) =====",
        f"총 {len(rows)}개 사업장. 각 행 = 분양 사업장 1건. ‘분양 사업장 건수’는 해당 지역·연도 행의 개수이고, "
        "‘평균 총세대수(TOT_HOCO)’는 그 행들의 총세대수 평균입니다.",
        "지역 | 연도 | 사업장명 | 총세대수(TOT_HOCO) | 일반분양세대(GNRL_SILT_HOCO)",
    ]
    for r in rows:
        lines.append(" | ".join([
            r.get("_query_area_name", ""), r.get("_query_year", ""),
            r.get("BSU_NM", ""), str(r.get("TOT_HOCO", "")), str(r.get("GNRL_SILT_HOCO", "")),
        ]))
    lines.append("===== [참고자료 끝] =====")
    text = "\n".join(lines) + "\n"
    return {"type": "hug_sale_history_rows", "id": "hug_sale_history_block", "ann": None,
            "text": text, "tokens": toks(text)}


DISTRACTORS: list = []


def assemble(bundle_id, tier, template, ordered_parts, target, no_pad=False):
    parts = [dict(c) for c in ordered_parts]
    cur = sum(c["tokens"] for c in parts)
    di = 0
    guard = 0
    while not no_pad and cur < target and guard < 200000 and DISTRACTORS:
        if di >= len(DISTRACTORS):
            di = 0
        c = DISTRACTORS[di]; di += 1; guard += 1
        parts.append(dict(c)); cur += c["tokens"]
    text_parts, comps = [], []
    char_off, tok_off = 0, 0
    for c in parts:
        t = c["text"]
        frac = (tok_off + c["tokens"] / 2) / max(cur, 1)
        comp = {"type": c["type"], "id": c["id"], "position_band": band(frac)}
        if c.get("ann"):
            comp["ann"] = c["ann"]
        comps.append(comp)
        text_parts.append(t)
        char_off += len(t); tok_off += c["tokens"]
    (BUNDLES / f"{bundle_id}.txt").write_text("".join(text_parts), encoding="utf-8")
    anns = sorted({c["ann"] for c in parts if c.get("ann")})
    providers = sorted({P.provider_of(a) for a in anns})
    src_mix = Counter(P.source_of(a) for a in anns)
    return {"bundle_id": bundle_id, "context_tier": tier, "template": template,
            "providers": providers, "announcement_ids": anns, "source_mix": dict(src_mix),
            "token_estimate": cur, "n_components": len(comps),
            "component_positions": comps}


def build():
    global DISTRACTORS
    BUNDLES.mkdir(parents=True, exist_ok=True)
    laws = law_components()
    rows = row_block_components()
    DISTRACTORS = laws + rows
    manifest = []
    anns = list(P.announcement_ids())

    for ann_id in anns:
        comps = ann_components(ann_id)
        if not comps:
            continue
        for tier in EARLY_TIERS:
            target = TIERS[tier]
            lead, cur = [], 0
            for c in comps:
                if cur + c["tokens"] > target * 0.9:
                    break
                lead.append(c); cur += c["tokens"]
            manifest.append(assemble(f"{ann_id}__early_{tier}", tier, "announcement_focus_early", lead, target))
        for tier in LATE_TIERS:
            target = TIERS[tier]
            ann_cap = target * 0.40
            lead, atok = [], 0
            for c in reversed(comps):  # tail pages (long_distance cites later pages)
                if atok + c["tokens"] > ann_cap:
                    break
                lead.insert(0, c); atok += c["tokens"]
            pre, cur, di = [], 0, 0
            while cur < target - atok - 2000 and di < len(DISTRACTORS):
                pre.append(DISTRACTORS[di]); cur += DISTRACTORS[di]["tokens"]; di += 1
            parts = pre + lead
            manifest.append(assemble(f"{ann_id}__late_{tier}", tier, "announcement_focus_late", parts, sum(c["tokens"] for c in parts), no_pad=True))

    # multi-provider mix bundles: interleave lead pages from all providers (round-robin by provider)
    by_prov = {}
    for a in anns:
        by_prov.setdefault(P.source_of(a), []).append(a)
    interleaved = []
    i = 0
    while True:
        added = False
        for src in sorted(by_prov):
            if i < len(by_prov[src]):
                interleaved.extend(ann_components(by_prov[src][i], max_page=LEAD))
                added = True
        if not added:
            break
        i += 1
    # The HUG sale-history table is embedded COMPLETE and guaranteed (not as a paddable distractor) in the
    # 512k multi-provider mix — this is the bundle that every cross_source_aggregation item references, and
    # its gold is computed from these rows. (Prompt-level injection in fix_fc_hug_bundle_v09.py is now
    # redundant for bundles rebuilt from this script.)
    hug = hug_block_component()
    manifest.append(assemble("mix_multiprovider_512k", "512k", "multiprovider_announcement_heavy", [hug] + interleaved, TIERS["512k"]))
    manifest.append(assemble("mix_multiprovider_256k", "256k", "multiprovider_law_heavy", laws + interleaved, TIERS["256k"]))
    manifest.append(assemble("mix_multiprovider_32k", "32k", "multiprovider_compact", interleaved[:14], TIERS["32k"]))

    with (BUNDLES / "manifest.jsonl").open("w", encoding="utf-8") as f:
        for m in manifest:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    tiers = Counter(m["context_tier"] for m in manifest)
    pages_band = {}
    for m in manifest:
        for c in m["component_positions"]:
            if c["type"] == "lh_page":
                pages_band.setdefault(c["id"], set()).add(c["position_band"])
    print(f"=== BUNDLES v0.6: {len(manifest)} bundles ; tiers {dict(tiers)} ===")
    print(f"  LH-pages covered: {len(pages_band)} ; early {sum(1 for v in pages_band.values() if 'early' in v)} ; late {sum(1 for v in pages_band.values() if 'late' in v)}")
    print(f"  multi-provider mix bundles: providers per mix = {[len(m['providers']) for m in manifest if m['bundle_id'].startswith('mix_')]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
