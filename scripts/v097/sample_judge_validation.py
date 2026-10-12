"""Stratified random sample of reported test_public predictions for a second judge-validation round.

Released files only (dataset v0.9.6): results/predictions_v0.9.5/, data/qa_v0.6_test_public.jsonl,
data/v0.9.3/eval_exclusions.txt. No API calls.

Strata: model (8) x setting (CB, BM25, dense, FC, k=50, open-region, oracle) -> 50 cells
(8 models x 4 settings + 6 full-window models x 3 aggregation settings). Within a cell the items are drawn
uniformly at random; the primary judge label is NOT used for balancing (the first sample was balanced on the
then-primary judge, which reviewers criticised). Non-literal gold answers are kept.

Each cell uses the reported run only, with later files overriding earlier ones per qa_id in the order below
(e.g. closed-book = original run, then the gpt-5.5 empty-answer retry, then the leak-fixed re-run).

Usage (from the dataset repository root):
  python3 <path>/sample_judge_validation.py                    # dry run: cell counts only
  python3 <path>/sample_judge_validation.py --exclude-human80  # drop (qa_id, model, setting) in the first 80
  python3 <path>/sample_judge_validation.py --write OUT_DIR     # write sample.csv, annotator.csv, key.csv
Options: --per-cell N (default 4), --seed S (default 20261012),
  --aux-string-mismatch: add an auxiliary stratum of 2 predictions per model, drawn at random from that
  model's reported predictions in which no gold answer string occurs in the prediction (string comparison
  only, no judge verdict). Gold answer strings: the released `answer`, or the v0.9.2 accepted alternatives
  (data/v0.9.2/gold_fixes.json: accept_any lists, replace values). Normalisation of both sides: Unicode NFKC,
  lower case, all whitespace removed; "occurs" = substring. Rows already in the main sample are excluded
  (drawn after the main sample with the same random stream). Reported separately.
The cell population (pool) is printed for post-stratified weighting: weight of a cell = pool / per-cell sample.
"""
import argparse
import csv
import json
import random
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
P = ROOT / "results" / "predictions_v0.9.5"
V2, V3, V4 = "v0.9.2/", "v0.9.3/", "v0.9.4/"

CB = {
    "gpt-4.1-mini": [V2 + "gpt-4.1-mini_cb", V3 + "cbfix_gpt-4.1-mini_test_public"],
    "gpt-5.4-mini": [V2 + "gpt-5.4-mini_cb", V3 + "cbfix_gpt-5.4-mini_test_public"],
    "gpt-5.4-nano": [V2 + "gpt-5.4-nano_cb", V3 + "cbfix_gpt-5.4-nano_test_public"],
    "gpt-5.5": [V2 + "gpt-5.5_cb", V3 + "g55retry_cb_test_public", V3 + "cbfix_gpt-5.5_test_public"],
    "minimax-m3": [V2 + "cb_minimax-m3-cloud_tp", V3 + "cbfix_minimax-m3_test_public"],
    "glm-5.2": [V3 + "thinkon_cb_glm-5.2"],
    "claude-sonnet-5-5": [V3 + "cb_claude-sonnet-5-5"],
    "claude-haiku-5-5": [V3 + "cb_claude-haiku-5-5"],
}
BM25 = {
    "gpt-4.1-mini": [V2 + "gpt-4.1-mini_rag"], "gpt-5.4-mini": [V2 + "gpt-5.4-mini_rag"],
    "gpt-5.4-nano": [V2 + "gpt-5.4-nano_rag"], "gpt-5.5": [V2 + "gpt-5.5_rag"],
    "minimax-m3": [V2 + "rag_minimax-m3-cloud_tp"], "glm-5.2": [V3 + "thinkon_bm25_glm-5.2"],
    "claude-sonnet-5-5": [V3 + "bm25_claude-sonnet-5-5"], "claude-haiku-5-5": [V3 + "bm25_claude-haiku-5-5"],
}
DENSE = {m: [V2 + f"jf386_{m}_dense"] for m in ["gpt-4.1-mini", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.5", "minimax-m3"]}
DENSE.update({"glm-5.2": [V3 + "thinkon_dense_glm-5.2"], "claude-sonnet-5-5": [V3 + "dense_claude-sonnet-5-5"],
              "claude-haiku-5-5": [V3 + "dense_claude-haiku-5-5"]})
FC = {  # full-context sample (98 items; 77 for the two 272k-window models)
    "gpt-4.1-mini": [V2 + "gpt-4.1-mini_fc", V2 + "fc_gpt-4.1-mini_test_public_fixed512k"],
    "gpt-5.4-mini": [V2 + "gpt-5.4-mini_fc"], "gpt-5.4-nano": [V2 + "gpt-5.4-nano_fc"],
    "gpt-5.5": [V2 + "g55fc", V2 + "fc_gpt-5.5_test_public_fixed512k"],
    "minimax-m3": [V2 + "fc_minimax-m3-cloud_tp", V2 + "fc_minimax-m3-cloud_tp_fixed"],
    "glm-5.2": [V2 + "fc_glm-5.2-cloud_tp", V2 + "fc_glm-5.2-cloud_tp_fixed"],
    "claude-sonnet-5-5": [V3 + "fc_claude-sonnet-5-5"], "claude-haiku-5-5": [V3 + "fc_claude-haiku-5-5"],
}
FULL = ["gpt-5.5", "glm-5.2", "minimax-m3", "claude-sonnet-5-5", "claude-haiku-5-5", "gpt-4.1-mini"]
K50 = {m: [V4 + f"k50dense_{m}"] for m in FULL}
OPENREGION = {m: [V3 + f"openregion_agg81_{m}"] for m in FULL}
ORACLE = {m: [V3 + f"oracle_agg81_{m}"] for m in FULL}
SETTINGS = {"cb": CB, "bm25": BM25, "dense": DENSE, "fc": FC, "k50": K50, "open-region": OPENREGION, "oracle": ORACLE}
FC_ITEMS_FROM = V3 + "fc_claude-sonnet-5-5"  # defines the 98-item full-context sample


report_aux = []
aux_families = Counter()


FIXES = None


def gold_strings(q, qa):
    """Gold answers as scored since v0.9.2: accept-any alternatives, the replaced value, or the released answer."""
    global FIXES
    if FIXES is None:
        FIXES = json.load(open(ROOT / "data" / "v0.9.2" / "gold_fixes.json", encoding="utf-8"))
    if q in FIXES["accept_any"]:
        return list(FIXES["accept_any"][q])
    if q in FIXES["replace"]:
        return [FIXES["replace"][q]]
    return [qa[q]["answer"]]


def snorm(s):
    return "".join(unicodedata.normalize("NFKC", str(s)).lower().split())


def load(name):
    with open(P / f"{name}.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cell", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20261012)
    ap.add_argument("--exclude-human80", action="store_true")
    ap.add_argument("--write", metavar="OUT_DIR")
    ap.add_argument("--aux-string-mismatch", action="store_true")
    a = ap.parse_args()

    qa = {}
    with open(ROOT / "data" / "qa_v0.6_test_public.jsonl", encoding="utf-8") as f:
        for l in f:
            r = json.loads(l)
            qa[r["qa_id"]] = r
    excl = {l.strip() for l in open(ROOT / "data" / "v0.9.3" / "eval_exclusions.txt") if l.strip() and l[0] != "#"}
    scope = {q for q, r in qa.items() if r["task_type"] != "cross_document_legal_reasoning" and q not in excl}
    fc_items = {r["qa_id"] for r in load(FC_ITEMS_FROM)}
    agg = {json.loads(l)["qa_id"] for l in open(ROOT / "results" / "item_sets" / "agg81.jsonl")}

    h80 = set()
    if a.exclude_human80:
        for r in load("human80/human80"):
            q, m, s = r["qa_id"].split("__")
            h80.add((q, m, {"rag": "bm25"}.get(s, s)))

    rng = random.Random(a.seed)
    rows, report, allpred = [], [], []
    for setting, by_model in SETTINGS.items():
        for model, files in by_model.items():
            pred = {}
            for fn in files:
                for r in load(fn):
                    if r.get("split", "test_public") == "test_public":
                        pred[r["qa_id"]] = r
            items = scope & set(pred)
            if setting == "fc":
                items &= fc_items
            if setting in ("k50", "open-region", "oracle"):
                items &= agg
            pool = sorted(q for q in items if (q, model, setting) not in h80)
            allpred += [(model, setting, q, pred[q]) for q in pool]
            dropped = len(items) - len(pool)
            pick = rng.sample(pool, min(a.per_cell, len(pool)))
            yes_pool = sum(bool(pred[q]["judge_label"]) for q in pool)
            yes_pick = sum(bool(pred[q]["judge_label"]) for q in pick)
            report.append((model, setting, len(items), dropped, len(pick), yes_pool, yes_pick))
            for q in pick:
                rows.append(make_row(q, model, setting, pred[q], qa, "main"))

    aux = []
    if a.aux_string_mismatch:
        golds = lambda q: gold_strings(q, qa)
        taken = {(r["qa_id"], r["model"], r["setting"]) for r in rows}
        for model in CB:
            cand = sorted((s, q) for m, s, q, r in allpred if m == model and (q, m, s) not in taken
                          and not any(snorm(g) in snorm(r["prediction"]) for g in golds(q)))
            pick = rng.sample(cand, min(2, len(cand)))
            for s, q in pick:
                r = next(r for m, s2, q2, r in allpred if m == model and s2 == s and q2 == q)
                aux.append(make_row(q, model, s, r, qa, "aux_string_mismatch"))
            yes = sum(bool(r["judge_label"]) for m, s, q, r in allpred if m == model and (s, q) in set(cand))
            report_aux.append((model, len(cand), len(pick), yes))
        aux_families.update(qa[q]["task_type"] for m, s, q, r in allpred
                            if (q, m, s) not in taken and not any(snorm(g) in snorm(r["prediction"]) for g in golds(q)))

    report_rows(a, report, rows, aux)
    if a.write:
        write(a, rows + aux)


def make_row(q, model, setting, r, qa, stratum):
    x = qa[q]
    ev = x.get("evaluation") or {}
    return {
        "stratum": stratum, "qa_id": q, "model": model, "setting": setting, "task_type": x["task_type"],
        "question": x["question"], "gold_answer": " ‖ ".join(gold_strings(q, qa)),
        "gold_alternatives": len(gold_strings(q, qa)),
        "gold_terms": json.dumps(ev.get("gold_terms") or ev.get("gold_numbers") or [], ensure_ascii=False),
        "metric": ev.get("metric", ""), "prediction": r["prediction"],
        "judge_label": r["judge_label"], "judge_label_secondary": r.get("judge_label_secondary"),
    }


def report_rows(a, report, rows, aux):
    print(f"seed {a.seed}, per cell {a.per_cell}, exclude_human80={a.exclude_human80}")
    print("| model | setting | pool | dropped (human80) | sampled | primary YES in pool | primary YES in sample |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for m, s, n, d, k, yp, ys in report:
        print(f"| {m} | {s} | {n} | {d} | {k} | {yp}/{n - d} | {ys}/{k} |")
    print(f"\ncells {len(report)}, sampled {len(rows)}, distinct items {len({r['qa_id'] for r in rows})}, "
          f"primary YES {sum(bool(r['judge_label']) for r in rows)}")
    print("by setting:", dict(Counter(r["setting"] for r in rows)))
    print("by task family:", dict(Counter(r["task_type"] for r in rows)))
    lit = sum(1 for r in rows if r["metric"] in ("exact_numbers", "contains_all"))
    print(f"metric types: {dict(Counter(r['metric'] for r in rows))} (string-scorable {lit})")
    print("\npost-stratification: cell weight = cell pool / sampled (the pool column above); "
          "it equals the setting weight except for the two 77-item FC cells")
    pop = Counter()
    for m, s, n, d, k, yp, ys in report:
        pop[s] += n - d
    print("  setting population:", dict(pop), "total", sum(pop.values()))
    if aux:
        print("\naux_string_mismatch stratum (judge labels for reference only; not used in selection):")
        print("| model | candidates | sampled | primary YES among candidates |")
        print("|---|---:|---:|---:|")
        for m, n, k, y in report_aux:
            print(f"| {m} | {n} | {k} | {y}/{n} |")
        print(f"candidates by family: {dict(aux_families)}")
        print(f"sampled: {len(aux)}; by setting {dict(Counter(r['setting'] for r in aux))}; "
              f"by family {dict(Counter(r['task_type'] for r in aux))}; "
              f"primary YES {sum(bool(r['judge_label']) for r in aux)}/{len(aux)}")


def write(a, rows):
    out = Path(a.write)
    out.mkdir(parents=True, exist_ok=True)
    order = list(range(len(rows)))
    random.Random(a.seed + 1).shuffle(order)
    human = {"label_annotator_a": "", "note_a": "", "label_annotator_b": "", "note_b": "", "label_adjudicated": ""}
    full = [dict(sample_id=f"s{i:03d}", **rows[j], **human) for i, j in enumerate(order)]
    with open(out / "sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(full[0]))
        w.writeheader()
        w.writerows(full)
    # annotator file: no model, setting, stratum or judge label; each annotator fills a copy independently
    with open(out / "annotator.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "question", "gold_answer", "prediction", "label", "memo"])
        w.writeheader()
        for r in full:
            w.writerow({"sample_id": r["sample_id"], "question": r["question"], "gold_answer": r["gold_answer"],
                        "prediction": r["prediction"], "label": "", "memo": ""})
    with open(out / "key.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "stratum", "qa_id", "model", "setting"], extrasaction="ignore")
        w.writeheader()
        w.writerows(full)
    print(f"wrote {out}/sample.csv, annotator.csv, key.csv")


if __name__ == "__main__":
    main()
