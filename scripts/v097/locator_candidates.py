#!/usr/bin/env python3
"""New evidence pages for the dev items adjudicated as locator_fixed (prespec_dev_review_2026-10-12.md D, rule of
2026-10-12). No API calls.

Rule: the new locator is the only page of the same announcement that contains the gold value, present in every
bundle tier, confirmed by the author.
- Gold value of the defective page: aggregation items take the predicate's _query_area_name; comparison items split
  the gold on " / " and take the part in the same position as the page (the region after "=" when present).
  Province names also match their short form.
- A page contains the value when the value occurs with a location marker in the 40 characters before it (or
  "일원" within 25 characters after it) and no
  non-location context (model house, application or contract place, residence, transport, inquiry) in that window
  or the 30 characters after it. Whitespace inside the value is ignored.
- A cited page is defective when it has no such line.
- Bundle check: the item's bundle and every bundle (any tier) that holds the old page.
Status per defective page: propose (one candidate, in every bundle), author_select (several candidates),
bundle_flag (one candidate, missing from a bundle: keep it as locator, flag the item for bundle exclusion),
readjudicate (no candidate).

Usage (from file-search-map-reduce-agent/):
  python3 -I kr-housing-longrag-bench-paper/shared/scripts/peerreview_check/locator_candidates.py \
      kr-housing-longrag-bench kr-housing-longrag-bench-v096 ADJUDICATION_CSV OUT_DIR
Writes OUT_DIR/locator_candidates.csv, OUT_DIR/confirm_locators.csv, OUT_DIR/adjudication_filled_v2.csv.
"""
import csv
import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

WORK, DATA, ADJ, OUT = map(Path, sys.argv[1:5])
W = WORK / "workspace_local"
pages = {}
for f in glob.glob(str(W / "processed/*/*/document_pages.jsonl")):
    for l in open(f):
        p = json.loads(l)
        pages[p["page_id"]] = p["text"]
qa = {json.loads(l)["qa_id"]: json.loads(l) for l in open(DATA / "data/qa_v0.6_dev.jsonl")}
bundles = {}
for l in open(W / "processed/bundles-v06/manifest.jsonl"):
    b = json.loads(l)
    bundles[b["bundle_id"]] = {c["id"] for c in b["component_positions"] if c["type"] == "lh_page"}
bexcl = {l.strip() for l in open(DATA / "data/v0.9.3/bundle_exclusions.txt") if l.strip() and l[0] != "#"}

ann = lambda pid: re.sub(r"-p\d+$", "", pid)
norm = lambda s: re.sub(r"\s+", "", s)
KEY = re.compile(r"공급\s*위\s*치|위\s+치|위치\s*[:：]|소\s*재\s*지|건설\s*위치|사업\s*위치|일\s*원|대\s*상\s*지|주\s*소")
POST = re.compile(r"^[^\n]{0,25}일\s*원")  # "... 일원" (site area) right after the value
EXCL = re.compile(r"계약\s*체결\s*장소|견본\s*주택|모델\s*하우스|홍보관|접수|계약\s*장소|사업장\s*소재지|관할|거주|재학|네비게이션|검색|하차|버스|지하철|구청|문의")
SHORT = {"서울특별시": "서울", "대전광역시": "대전", "광주광역시": "광주", "경기도": "경기"}


def hits(page_id, alts, before=40, after=30):
    """Occurrences of the gold value with a location marker in the 40 characters before it and no non-location
    context within that window or the 30 characters after it (lines are ignored because some extracted pages
    are one long line)."""
    t = pages.get(page_id, "")
    out = []
    for a in alts:
        for m in re.finditer(r"\s*".join(map(re.escape, a)), t):
            pre = t[max(0, m.start() - before): m.start()]
            win = pre + m.group(0) + t[m.end(): m.end() + after]
            post = t[m.end(): m.end() + after]
            if (KEY.search(pre) or POST.search(post)) and not EXCL.search(win):
                out.append((m.start(), m.end()))
    return out


def value_lines(page_id, alts):
    return hits(page_id, alts)


def context(page_id, alts, n=100):
    h = hits(page_id, alts)
    if not h:
        return ""
    t = pages[page_id]
    s, e = h[0]
    return re.sub(r"\s+", " ", t[max(0, s - n): e + n])


adj = list(csv.DictReader(open(ADJ, encoding="utf-8-sig")))
rows = []
for x in adj:
    if x["action"].strip() != "locator_fixed":
        continue
    q = qa[x["qa_id"]]
    pids = q["page_ids"]
    if q.get("gold_predicate"):
        vals = [q["gold_predicate"]["filter"].get("_query_area_name")] * len(pids)
    else:
        vals = [p.strip().split("=")[-1].strip() for p in q["answer"].split("/")]
    found = False
    for i, pid in enumerate(pids):
        v = vals[i] if i < len(vals) else vals[-1]
        alts = [v] + ([SHORT[v]] if v in SHORT else [])
        if value_lines(pid, alts):
            continue
        found = True
        cands = sorted(p for p in pages if ann(p) == ann(pid) and value_lines(p, alts))
        holders = sorted(b for b, s in bundles.items() if pid in s)
        inb = {c: (c in bundles.get(q["bundle_id"], set()) and all(c in bundles[b] for b in holders)) for c in cands}
        if not cands:
            status = "readjudicate"
        elif len(cands) > 1:
            status = "author_select"
        elif inb[cands[0]]:
            status = "propose"
        else:
            status = "bundle_flag"
        rows.append({
            "qa_id": x["qa_id"], "family": q["task_type"], "old_locator": pid, "gold_value": v,
            "n_candidates": len(cands), "candidates": " | ".join(cands),
            "candidates_in_every_bundle": " | ".join(f"{c.split('-p')[-1]}:{'yes' if inb[c] else 'no'}" for c in cands),
            "proposed_locator": cands[0] if len(cands) == 1 else "", "unique": len(cands) == 1,
            "in_bundle_all_tiers": (inb[cands[0]] if len(cands) == 1 else ""), "bundles_holding_old_page": len(holders),
            "item_bundle": q["bundle_id"], "in_current_122": x["qa_id"] in bexcl, "status": status,
            "context": context(cands[0], alts) if len(cands) == 1 else "",
        })
    if not found:
        rows.append({"qa_id": x["qa_id"], "family": q["task_type"], "old_locator": "", "gold_value": "",
                     "n_candidates": 0, "candidates": "", "candidates_in_every_bundle": "", "proposed_locator": "",
                     "unique": "", "in_bundle_all_tiers": "", "bundles_holding_old_page": "", "item_bundle": q["bundle_id"],
                     "in_current_122": x["qa_id"] in bexcl, "status": "no_defective_page_found", "context": ""})

OUT.mkdir(parents=True, exist_ok=True)
with open(OUT / "locator_candidates.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

# confirm sheet: one row per defective page and candidate
with open(OUT / "confirm_locators.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["qa_id", "status", "old_locator", "gold_value", "candidate_page", "in_every_bundle", "context_±100",
                "author_choice (y = use this page)", "author_note"])
    for r in rows:
        for c in (r["candidates"].split(" | ") if r["candidates"] else [""]):
            alts = [r["gold_value"]] + ([SHORT[r["gold_value"]]] if r["gold_value"] in SHORT else [])
            ok = dict(z.split(":") for z in r["candidates_in_every_bundle"].split(" | ")) if r["candidates_in_every_bundle"] else {}
            w.writerow([r["qa_id"], r["status"], r["old_locator"], r["gold_value"], c, ok.get(c.split("-p")[-1], ""),
                        context(c, alts) if c else "", "", ""])

# adjudication v2: fill new_locator only where every defective page of the item has status propose or bundle_flag
by_q = {}
for r in rows:
    by_q.setdefault(r["qa_id"], []).append(r)
for x in adj:
    if x["action"].strip() != "locator_fixed":
        continue
    rs = by_q[x["qa_id"]]
    if all(r["status"] in ("propose", "bundle_flag") for r in rs):
        x["new_locator"] = " ; ".join(f"{r['old_locator']} -> {r['proposed_locator']}" for r in rs)
        if any(r["status"] == "bundle_flag" for r in rs):
            x["note"] = (x["note"] + " || locator rule: new page missing from a bundle tier; flag for bundle exclusion "
                         "(independent of the 122)").strip(" |")
    else:
        why = "; ".join(f"{r['old_locator'].split('-p')[-1] if r['old_locator'] else '?'}: {r['status']}"
                        + (f" among {r['n_candidates']}" if r["status"] == "author_select" else "") for r in rs)
        x["note"] = (x["note"] + f" || locator rule: {why}"
                     + (f" (author-selected among {max(r['n_candidates'] for r in rs)})" if any(r['status'] == 'author_select' for r in rs) else "")).strip(" |")
fields = list(adj[0])
with open(OUT / "adjudication_filled_v2.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(adj)

items = {r["qa_id"] for r in rows}
st_item = {q: ("propose" if all(r["status"] == "propose" for r in by_q[q]) else
               "bundle_flag" if all(r["status"] in ("propose", "bundle_flag") for r in by_q[q]) else
               "readjudicate" if any(r["status"] in ("readjudicate", "no_defective_page_found") for r in by_q[q]) else
               "author_select") for q in items}
print(f"items {len(items)}, defective pages {sum(1 for r in rows if r['old_locator'])}")
print("pages by status:", dict(Counter(r["status"] for r in rows)))
print("items by status:", dict(Counter(st_item.values())))
print("by announcement:", dict(Counter((ann(r["old_locator"])[:45] if r["old_locator"] else "-", r["status"]) for r in rows)))
new_flag = {q for q in items if st_item[q] == "bundle_flag"}
print("cross-table items x {in current 122, newly flagged for bundle exclusion}:",
      dict(Counter((q in bexcl, q in new_flag) for q in items)))
print(f"filled new_locator in v2: {sum(1 for q in items if st_item[q] in ('propose', 'bundle_flag'))}")
