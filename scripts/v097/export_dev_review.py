#!/usr/bin/env python3
"""Export review sheets for the full human review of the evaluated dev items (final2_engexpert.md §24, A-G).

A. Scope: qa_v0.6_dev minus cross_document_legal_reasoning (67) minus the 7 dev items of
   data/v0.9.3/eval_exclusions.txt = 1,534. The 122 bundle-excluded items, the 54 detector flags and the 100
   items of review round 2 are all included. Column `stage`: 1 = the 964 items of the BM25/full-context
   columns (bundle present, not in bundle_exclusions.txt), 2 = the other 570; it is information only.
B. Assignment: items grouped by family, shuffled within family (seed), then interleaved across families in
   proportion to family size, so every block mixes the families; blocks of 50 (the last one 34; 31 blocks).
   P = all 2-annotator combinations in fixed order (n=2: 1 pair, 3: 3, 4: 6). Block k goes to P[k mod |P|].
   Every item gets exactly two annotators. The assignment table (qa_id, block, annotator_a, annotator_b) is
   fixed before labelling.
C. Sheet: one row per item. Shown: qa_id, family, route (script / cloze_regenerated / template_reworded),
   question (current; the original wording when it differs), gold (all accepted answers), locators, and the
   evidence text from the local processed corpus: cited pages in full; predicate items: the predicate and every
   matching row; table-cell items: the table block with its header rows and the target cell marked ★. Evidence
   longer than one spreadsheet cell (30,000 characters) is cut in the cell and written in full to
   evidence/<qa_id>.txt. Label columns: verdict (no_error / error / unsure), type (dual_row / header_parse /
   multiple_schedules / wrong_gold / scope / unspecified / other; only when verdict = error), memo.
   Naturalness is not collected. The sheets are internal review material (source text not for
   redistribution): write them outside every git repository.
   Checks after building (an error stops --write): 1,534 items; empty evidence; a predicate item showing a null
   value in the aggregated field (the round-2 dealAmount_manwon gap); a table item without its target cell or
   table; recompute failures. Warning only: gold string not found in the evidence (non-predicate items).

Usage (REPO = the dataset working copy that has workspace_local/):
  python3 -I export_dev_review.py REPO --annotators 4               # dry run
  python3 -I export_dev_review.py REPO --annotators 4 --write OUT_DIR
Options: --block-size 50, --seed 20261012, --data-root (released files; default REPO).
"""
import argparse
import csv
import glob
import itertools
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("repo")
ap.add_argument("--annotators", type=int, required=True)
ap.add_argument("--block-size", type=int, default=50)
ap.add_argument("--seed", type=int, default=20261012)
ap.add_argument("--data-root")
ap.add_argument("--write", metavar="OUT_DIR")
a = ap.parse_args()

REPO = Path(a.repo).resolve()
DATA = Path(a.data_root).resolve() if a.data_root else REPO
sys.path.insert(0, str(REPO / "scripts"))
import qa_v03_common as q3  # noqa: E402

P = REPO / "workspace_local" / "processed"
T = REPO / "workspace_local" / "audit" / "triage_compare"
CELL_MAX = 30000


def ids(path):
    return {l.strip() for l in open(path) if l.strip() and not l.startswith("#")}


# ---- A. scope
qa = [json.loads(l) for l in open(DATA / "data/qa_v0.6_dev.jsonl") if l.strip()]
excl = ids(DATA / "data/v0.9.3/eval_exclusions.txt")
bexcl = ids(DATA / "data/v0.9.3/bundle_exclusions.txt")
legal = [q for q in qa if q["task_type"] == "cross_document_legal_reasoning"]
scope = sorted((q for q in qa if q["task_type"] != "cross_document_legal_reasoning" and q["qa_id"] not in excl),
               key=lambda q: q["qa_id"])
stage = {q["qa_id"]: ("1" if q.get("bundle_id") and q["qa_id"] not in bexcl else "2") for q in scope}
cloze_ids = {x["qa_id"] for f in ("regen_verify_targets.json", "regen_verify_targets_68.json")
             for x in json.load(open(T / f))}
fixes = json.load(open(DATA / "data/v0.9.2/gold_fixes.json"))


def route(q):
    if q["qa_id"] in cloze_ids:
        return "cloze_regenerated"
    if q.get("original_question") and q["original_question"] != q["question"]:
        return "template_reworded"
    return "script"


def golds(q):
    if q["qa_id"] in fixes["accept_any"]:
        return list(fixes["accept_any"][q["qa_id"]])
    return [fixes["replace"].get(q["qa_id"], q["answer"])]


# ---- B. assignment
names = [chr(ord("A") + i) for i in range(a.annotators)]
pairs = list(itertools.combinations(names, 2))
rng = random.Random(a.seed)
by_fam = defaultdict(list)
for q in scope:
    by_fam[q["task_type"]].append(q)
keyed = []
for fam in sorted(by_fam):
    items = by_fam[fam][:]
    rng.shuffle(items)
    n = len(items)
    keyed += [((i + rng.random()) / n, fam, q) for i, q in enumerate(items)]
order = [q for _, _, q in sorted(keyed, key=lambda t: (t[0], t[1]))]
assign, blocks = {}, []
for k in range(0, len(order), a.block_size):
    blk = order[k:k + a.block_size]
    b = len(blocks)
    pair = pairs[b % len(pairs)]
    blocks.append((f"B{b + 1:02d}", len(blk), pair))
    for q in blk:
        assign[q["qa_id"]] = (f"B{b + 1:02d}", pair)

# ---- C. evidence
pages, cells = {}, defaultdict(list)
for f in glob.glob(str(P / "*/*/document_pages.jsonl")):
    for l in open(f):
        r = json.loads(l)
        pages[r["page_id"]] = r
for f in glob.glob(str(P / "*/*/table_cells.jsonl")):
    for l in open(f):
        r = json.loads(l)
        cells[r["table_id"]].append(r)


def norm(s):
    return re.sub(r"\s+", "", s or "")


def table_block(table_id, target_cells):
    cs = cells.get(table_id, [])
    if not cs:
        return None
    tgt = {tuple(map(int, m.groups())) for cid in target_cells for m in [re.search(r"#r(\d+)c(\d+)$", cid)] if m}
    nr = max(c["row_index"] for c in cs) + 1
    nc = max(c["col_index"] for c in cs) + 1
    grid = [["" for _ in range(nc)] for _ in range(nr)]
    for c in cs:
        grid[c["row_index"]][c["col_index"]] = (c["cell_text"] or "")[:120]
    return {"kind": "table", "label": f"표 {table_id.split('-')[-1]} (p.{table_id.split('-p')[-1].split('-')[0]})",
            "grid": grid, "targets": tgt}


def page_block(pid, why=""):
    r = pages.get(pid)
    if not r:
        return None
    return {"kind": "text", "label": f"공고 원문 · {pid} (p.{r.get('page_no')})" + (f" · {why}" if why else ""),
            "text": r["text"]}


FIELD_KO = {"_query_area_name": "시·도", "_query_year": "분양연도", "AREA_DCD_NM": "시·도",
            "AREA_DTL_DCD_NM": "시·군·구", "BIZ_DIVN_NM": "사업구분", "_lawd_name": "시·군·구", "_deal_ymd": "거래연월"}
OP_KO = {"count": "건수", "avg": "평균", "sum": "합계", "min": "최솟값", "max": "최댓값", "median": "중앙값",
         "argmax": "최댓값인 행", "argmin": "최솟값인 행"}


def agg_block(pred):
    try:
        val, rid = q3.recompute(pred)
    except Exception as ex:
        return {"kind": "pred", "error": str(ex), "pred": pred}
    rows = q3.select(pred)
    hug = pred["source"] == q3.HUG
    keep = (["AREA_DTL_DCD_NM", "BSU_NM", "BIZ_DIVN_NM", "GNRL_SILT_HOCO", "SILT_OPEN_DT", "COLL_ANNO_APVL_DT",
             "_query_year", "_query_area_name"] if hug else
            ["_lawd_name", "_deal_ymd", "umdNm", "aptNm", "excluUseAr", "floor", "dealAmount"])
    shown = [{k: r.get(k) for k in keep if k in r} for r in rows]
    if pred.get("field"):  # the value the recompute uses, derived fields included
        for s, r in zip(shown, rows):
            s[pred["field"]] = q3._num(pred["source"], r, pred["field"])
    filt = [f"{FIELD_KO.get(k, k)} = {v}" for k, v in pred.get("filter", {}).items()]
    return {"kind": "pred", "label": f"집계 조건 ({'HUG 분양이력' if hug else '국토부 실거래'})", "filters": filt,
            "op": OP_KO.get(pred["op"], pred["op"]), "field": pred.get("field"), "value": val,
            "n_rows": len(rid), "rows": shown}


def flat(b):
    if b["kind"] == "text":
        return f"[{b['label']}]\n{b['text']}"
    if b["kind"] == "table":
        rows = [" | ".join(("★" + c + "★") if (r, j) in b["targets"] else c for j, c in enumerate(row))
                for r, row in enumerate(b["grid"]) if any(row)]
        return f"[{b['label']}] (★ = 정답 셀; 첫 행·첫 열은 머리글)\n" + "\n".join(rows)
    if b.get("error"):
        return f"[집계 조건] 재계산 실패: {b['error']}\n{json.dumps(b['pred'], ensure_ascii=False)}"
    head = (f"[{b['label']}] 조건: {', '.join(b['filters'])} / 연산: {b['op']}" + (f" ({b['field']})" if b["field"] else "")
            + f" / 재계산 값: {b['value']} / 해당 행 {b['n_rows']}개 (아래에 전부)")
    return "\n".join([head] + [json.dumps(r, ensure_ascii=False) for r in b["rows"]])


def build(q):
    fam, bl = q["task_type"], []
    if q.get("gold_predicate"):
        bl += [page_block(pid, "공고에서 조건 찾기") for pid in q.get("page_ids") or []]
        bl.append(agg_block(q["gold_predicate"]))
    elif q.get("table_ids"):
        bl += [table_block(t, q.get("cell_ids") or []) for t in q["table_ids"]]
        bl += [page_block(pid) for pid in q.get("page_ids") or []]
    else:
        bl += [page_block(pid) for pid in q.get("page_ids") or []]
    return [b for b in bl if b]


def check(q, bl, ev):
    err, warn = [], []
    if not ev.strip():
        err.append("empty evidence")
    for b in bl:
        if b["kind"] == "pred":
            if b.get("error"):
                err.append("recompute failed")
            elif b["field"] and any(r.get(b["field"]) is None for r in b["rows"]):
                err.append("null aggregated field")
        if b["kind"] == "table" and q.get("cell_ids") and "★" not in flat(b):
            err.append("target cell not shown")
    if q.get("table_ids") and not q.get("gold_predicate") and not any(b["kind"] == "table" for b in bl):
        err.append("table missing")
    if not q.get("gold_predicate") and not any(norm(g) and norm(g) in norm(ev) for g in golds(q)):
        warn.append("gold string not in evidence")
    return err, warn


rows, errs, warns, long_ev = [], defaultdict(list), defaultdict(list), {}
for q in order:
    bl = build(q)
    ev = "\n\n".join(flat(b) for b in bl)
    e, w = check(q, bl, ev)
    for x in e:
        errs[x].append(q["qa_id"])
    for x in w:
        warns[x].append(q["qa_id"])
    if len(ev) > CELL_MAX:
        long_ev[q["qa_id"]] = ev
        ev = ev[:CELL_MAX] + f"\n... (셀 길이 제한으로 잘림. 전체는 evidence/{q['qa_id']}.txt)"
    blk, pair = assign[q["qa_id"]]
    rows.append({
        "block": blk, "annotator_a": pair[0], "annotator_b": pair[1], "stage": stage[q["qa_id"]],
        "qa_id": q["qa_id"], "family": q["task_type"], "route": route(q), "question": q["question"],
        "original_question": q["original_question"] if route(q) != "script" and q.get("original_question") != q["question"] else "",
        "gold": " ‖ ".join(golds(q)), "locators": " / ".join(e["locator"] for e in q.get("evidence", [])),
        "evidence": ev,
    })

# ---- report
print(f"dev {len(qa)} - legal {len(legal)} - excluded {len(excl & {q['qa_id'] for q in qa})} = scope {len(scope)}"
      f" (stage 1 {sum(v == '1' for v in stage.values())}, stage 2 {sum(v == '2' for v in stage.values())})")
print(f"blocks {len(blocks)} (sizes {Counter(k for _, k, _ in blocks)}), pairs {len(pairs)}: {pairs}")
load, share = Counter(), Counter()
for _, k, pair in blocks:
    share[pair] += k
    for p in pair:
        load[p] += k
print("items per annotator:", dict(load), "| items per pair:", {''.join(p): v for p, v in share.items()})
print("check: every item has exactly two annotators:", all(len(set(assign[q['qa_id']][1])) == 2 for q in scope),
      "| items assigned:", len(assign))
print("route:", dict(Counter(r["route"] for r in rows)))
fams = sorted(by_fam)
mix = [len({assign[q["qa_id"]][0] for q in by_fam[f]}) for f in fams]
print("families (n, blocks containing it):", {f: (len(by_fam[f]), m) for f, m in zip(fams, mix)})
print("sheet check errors:", {k: (len(v), v[:5]) for k, v in errs.items()} or "none")
print("sheet check warnings:", {k: (len(v), v[:5]) for k, v in warns.items()} or "none")
L = sorted(len(r["evidence"]) for r in rows)
print(f"evidence chars: median {L[len(L) // 2]}, max {L[-1]}; over one cell (side file): {len(long_ev)}")

if a.write:
    if errs or len(rows) != 1534:
        sys.exit("sheet check failed; nothing written")
    out = Path(a.write)
    (out / "evidence").mkdir(parents=True, exist_ok=True)
    for qid, ev in long_ev.items():
        (out / "evidence" / f"{qid}.txt").write_text(ev, encoding="utf-8")
    show = ["no", "block", "qa_id", "family", "route", "question", "original_question", "gold", "locators", "evidence"]
    lab = {"verdict": "", "type": "", "memo": ""}
    for nm in names:
        mine = [r for r in rows if nm in (r["annotator_a"], r["annotator_b"])]
        with open(out / f"dev_review_{nm}_INTERNAL.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=show + list(lab))
            w.writeheader()
            for i, r in enumerate(mine, 1):
                w.writerow({**{k: r[k] for k in show if k != "no"}, "no": i, **lab})
    with open(out / "assignment.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["qa_id", "block", "annotator_a", "annotator_b", "stage", "family", "route"])
        w.writeheader()
        w.writerows({k: r[k] for k in w.fieldnames} for r in sorted(rows, key=lambda r: r["qa_id"]))
    (out / "README_INTERNAL.txt").write_text(
        "Internal review material; source text not for redistribution. Release only the labels and assignment.csv.\n",
        encoding="utf-8")
    print(f"wrote {out}")
