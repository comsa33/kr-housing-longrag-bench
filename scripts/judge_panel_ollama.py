#!/usr/bin/env python3
"""Independent-judge cross-check via Ollama Cloud (paper Appendix: judge panel).

The primary LLM-judge (``scripts/llm_judge.py``, gpt-4.1-mini via OpenAI Batch) is itself
one of the evaluated baselines. To rule out a judge self-preference confound, this script
re-scores the same predictions with a non-OpenAI judge model served on Ollama Cloud, using
the *identical* judge prompt as the primary judge. Unlike the original ad-hoc panel run,
every verdict is written to disk (flushed per item, ``--resume``-safe) so the cross-check
is fully reproducible and archived.

Two input modes feed the same judge call:
  * agreement/kappa validation --- items = the n=80 human-labeled sample; compare the judge
    verdict to the human label with ``scripts/kappa_panel.py``.
  * capability-ladder re-score --- items = the 81 cross-source-aggregation predictions of an
    evaluated model; aggregate with ``scripts/score_judge.py``-style counting.

Usage:
    python3 scripts/judge_panel_ollama.py --judge-model gemma4:31b \
        --input workspace_local/audit/baselines/panel_items_<model>.jsonl \
        --out   workspace_local/audit/baselines/panel_<judge>_<model>.judged.jsonl [--resume]

Input JSONL lines: {"qa_id":..., "question":..., "gold":..., "prediction":...}
Output JSONL lines: {"qa_id":..., "judge_correct": bool, "raw": "<model text>"}

Auth: OLLAMA_API_KEY env, else workspace_local/secrets/ollama_api.key.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOUD_URL = "https://ollama.com/api/chat"

# Identical judge instruction + prompt template as scripts/llm_judge.py (do not diverge:
# a fair cross-check requires the panel judges to see exactly what the primary judge saw).
JUDGE_INSTR = (
    "당신은 한국어 QA 채점자입니다. [질문]에 대한 [정답]과 [모델답변]을 비교하세요.\n"
    "모델답변이 정답과 의미상 동일하거나 정답의 핵심 사실을 올바르게 담고 있으면 정답입니다. "
    "표현·형식·어순·부연설명 차이는 무시하고 핵심 사실의 일치만 보세요. "
    "모델이 '자료로 확정 불가' 등으로 답을 거부했는데 정답이 실제 값이면 오답입니다.\n"
    "판정을 'YES'(정답) 또는 'NO'(오답) 한 단어로만 출력하세요."
)


def judge_prompt(q: str, gold: str, pred: str) -> str:
    return f"{JUDGE_INSTR}\n\n[질문] {q}\n[정답] {gold}\n[모델답변] {pred or '(빈 답)'}\n\n판정:"


def api_key() -> str:
    k = os.environ.get("OLLAMA_API_KEY", "").strip()
    if k:
        return k
    f = ROOT / "workspace_local" / "secrets" / "ollama_api.key"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    raise SystemExit("Set OLLAMA_API_KEY or provide workspace_local/secrets/ollama_api.key")


def call(model: str, prompt: str, key: str, think: bool, num_predict: int, timeout: int) -> dict:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": think,
        "options": {"temperature": 0, "num_predict": num_predict},
    }).encode("utf-8")
    req = urllib.request.Request(
        CLOUD_URL, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def verdict_text(resp: dict) -> str:
    """Prefer the final content; some reasoning judges emit the verdict only in `thinking`."""
    m = resp.get("message", {}) or {}
    txt = (m.get("content") or "").strip()
    if not txt:
        txt = (m.get("thinking") or "").strip()
    return txt


def parse_yes(txt: str) -> bool:
    """Same rule as scripts/llm_judge.py fetch(): a YES anywhere in the (upper) text.
    For reasoning fallbacks we take the LAST explicit YES/NO token to reflect the conclusion."""
    up = txt.upper()
    last = None
    for tok in ("YES", "NO"):
        i = up.rfind(tok)
        if i >= 0 and (last is None or i > last[1]):
            last = (tok, i)
    if last is not None:
        return last[0] == "YES"
    return "YES" in up


def judge_one(model: str, q: str, gold: str, pred: str, key: str, timeout: int) -> tuple[bool, str]:
    prompt = judge_prompt(q, gold, pred)
    # Pass 1: think off, short — works for non-reasoning judges (gemma, mistral) and any
    # reasoning judge that honors think:false.
    resp = call(model, prompt, key, think=False, num_predict=16, timeout=timeout)
    txt = verdict_text(resp)
    if txt:
        return parse_yes(txt), txt
    # Pass 2: reasoning judge ignored think:false and exhausted num_predict on the trace;
    # let it think, then read the verdict out of the (longer) trace/content.
    resp = call(model, prompt, key, think=True, num_predict=2048, timeout=timeout * 3)
    txt = verdict_text(resp)
    return parse_yes(txt), txt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge-model", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--sleep", type=float, default=0.15)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    key = api_key()
    inp = Path(args.input) if Path(args.input).is_absolute() else ROOT / args.input
    out = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    items = [json.loads(l) for l in inp.open(encoding="utf-8") if l.strip()]
    if args.limit:
        items = items[: args.limit]

    done: set[str] = set()
    if args.resume and out.exists():
        for l in out.open(encoding="utf-8"):
            try:
                done.add(json.loads(l)["qa_id"])
            except Exception:
                pass
    todo = [it for it in items if it["qa_id"] not in done]
    print(f"[panel] judge={args.judge_model} input={inp.name} items={len(items)} "
          f"done={len(done)} todo={len(todo)} -> {out.name}")

    n_ok = 0
    with out.open("a", encoding="utf-8") as fout:
        for i, it in enumerate(todo, 1):
            qid = it["qa_id"]
            for attempt in range(3):
                try:
                    ok, raw = judge_one(args.judge_model, it.get("question", ""),
                                        str(it.get("gold", "")), str(it.get("prediction", "")),
                                        key, args.timeout)
                    break
                except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
                    if attempt == 2:
                        print(f"  [skip] {qid}: {e}")
                        ok, raw = None, f"__error__: {e}"
                    else:
                        time.sleep(2 * (attempt + 1))
            if ok is None:
                continue  # leave unwritten so --resume retries
            fout.write(json.dumps({"qa_id": qid, "judge_correct": ok, "raw": raw[:200]}, ensure_ascii=False) + "\n")
            fout.flush()
            n_ok += int(ok)
            if i % 20 == 0:
                print(f"  {i}/{len(todo)} judged ({n_ok} YES so far)")
            time.sleep(args.sleep)
    print(f"[panel] wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
