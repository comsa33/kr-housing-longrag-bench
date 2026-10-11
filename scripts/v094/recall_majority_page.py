"""BM25 gold-page recall@5 under the majority-page rule (v0.9.4), with the earlier any-overlap rule for comparison.

Each retrieved passage is located in its bundle and assigned to the one page that holds most of its characters;
a gold page counts as retrieved when a passage assigned to it is in the top five. An item with two gold pages
scores half for each page retrieved. The any-overlap rule (used for the dev figure in v0.9.3) counted a passage
for every page it overlaps, so a passage crossing an SH page boundary counted for both pages.

Scope: legal family, the 5 v0.9.2 test exclusions and the 7 confirmed dev errors dropped; the 122 dev items whose
512k bundle lacks at least one gold page are reported separately. Build machine: needs the bundle text and the
stored BM25 prompt files under workspace_local/ (not redistributed). No API calls.

Usage (from the repository root): python3 scripts/v094/recall_majority_page.py
"""
import ast
import collections
import csv
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(os.environ.get("KRH_WORKSPACE", ROOT / "workspace_local"))
BASEL = WORK / "audit" / "baselines"
BUNDLES = WORK / "processed" / "bundles-v06"
LEGAL = "cross_document_legal_reasoning"
PAGE = re.compile(r"\[[^\]\n]*?\s([^\s\]]+-p\d{3}) \(p\.\d+\)\]")          # page markers in the bundle (Hangul ids too)
HDR = re.compile(r"(?:^|\n\n)\[((?:[A-Za-z0-9][A-Za-z0-9-]*)-p\d{3}) \(p\.\d+\)\]\n")  # passage headers in prompts
PROMPTS = (("rag_bm25_dev_fixed_prompts.jsonl", "dev"), ("rag_bm25_tp386_fixed_prompts.jsonl", "test"))


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def ids(p):
    return {l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")}


def main():
    G = {}
    for sp in ("dev", "test_public"):
        for r in load(ROOT / "data" / f"qa_v0.6_{sp}.jsonl"):
            G[r["qa_id"]] = r
    excl = set(json.load(open(ROOT / "data" / "v0.9.2" / "gold_fixes.json"))["exclude_from_evaluation"])
    err7 = {r["qa_id"] for r in csv.DictReader(open(ROOT / "data" / "errata_v0.9.3.csv", encoding="utf-8"))
            if r["split"] == "dev" and r["v0.9.3_status"] == "excluded_from_evaluation"}
    l122 = ids(ROOT / "data" / "v0.9.3" / "bundle_exclusions.txt")
    assert len(err7) == 7 and len(l122) == 122
    cache = {}

    def bundle(bid):
        if bid not in cache:
            t = open(BUNDLES / f"{bid}.txt", encoding="utf-8").read()
            ms = list(PAGE.finditer(t))
            cache[bid] = (t, [(m.group(1), m.end(), ms[i + 1].start() if i + 1 < len(ms) else len(t)) for i, m in enumerate(ms)])
        return cache[bid]

    out = collections.defaultdict(list)
    for fn, sp in PROMPTS:
        for r in load(BASEL / fn):
            q = r["qa_id"]
            g = G.get(q)
            if not g or g["task_type"] == LEGAL or q in excl or q in err7:
                continue
            gold = set(r.get("gold_page_ids") or [])
            if not gold:
                continue
            t, spans = bundle(r["bundle_id"])
            body = r["prompt"].split("(질문과 관련된 상위 페이지만 제공)\n", 1)[1].rsplit("\n\n[질문]", 1)[0]
            hs = list(HDR.finditer(body))
            anyp, maj = set(), set()
            for i, m in enumerate(hs):
                txt = body[m.end(): hs[i + 1].start() if i + 1 < len(hs) else len(body)]
                off = t.find(txt)
                if off < 0:
                    continue
                ov = []
                for pid, a2, b in spans:
                    if a2 < off + len(txt) and off < b:
                        n = len(t[max(off, a2): min(off + len(txt), b)].strip())
                        ov.append((n, pid))
                        anyp.add(pid)
                if ov:
                    maj.add(max(ov)[1])
            grp = "test" if sp == "test" else ("dev122" if q in l122 else "dev")
            sh = any(x.startswith("sh-") for x in gold)
            out[grp].append((len(anyp & gold) / len(gold), len(maj & gold) / len(gold), len(gold), sh))
    mean = lambda v, i: 100 * sum(z[i] for z in v) / len(v)
    print("| set | n | any-overlap | majority-page |")
    print("|---|---|---|---|")
    for k in ("test", "dev", "dev122"):
        v = out[k]
        print(f"| {k} | {len(v)} | {mean(v, 0):.2f} | {mean(v, 1):.2f} |")
    v = out["dev"] + out["test"]
    print(f"| pooled (dev + test) | {len(v)} | {mean(v, 0):.2f} | {mean(v, 1):.2f} |")
    for lab, sel in (("dev SH", lambda z: z[3]), ("dev non-SH", lambda z: not z[3]), ("dev two gold pages", lambda z: z[2] == 2)):
        s = [z for z in out["dev"] if sel(z)]
        print(f"| {lab} | {len(s)} | {mean(s, 0):.1f} | {mean(s, 1):.1f} |")


if __name__ == "__main__":
    main()
