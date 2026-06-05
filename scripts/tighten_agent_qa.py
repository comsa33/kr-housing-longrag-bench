#!/usr/bin/env python3
"""Tighten over-long agent answers / gold_terms to honor the 'no long original sentences in public QA'
policy (principle #7). Operates on internal staging workspace_local/audit/qa_agent_raw.json in place
(backup kept). Shortened gold_terms remain verbatim substrings of the source so grounding still holds;
shortened answers stay factually complete but drop near-verbatim statutory restatement.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from qa_common import ROOT, norm, full_text

RAW = ROOT / "workspace_local" / "audit" / "qa_agent_raw.json"

# concise, fact-only answer rewrites keyed by a stable question substring
ANSWER_FIX = {
    "민간임대주택의 임차인 자격·선정방법 등 공급에 관한 사항을 누가 정하도록":
        "공급에 관한 사항은 임대사업자가 정하고 「주택법」 제4장은 적용하지 않음(특별법 제42조). 주택공급규칙 제1조는 「주택법」 제38조 등에 근거함.",
    "증액 한도 범위는 얼마이며":
        "임대료 증액: 연 5퍼센트 범위(특별법 제44조제2항). 청약금: 주택가격의 10퍼센트, 계약금: 20퍼센트(주택공급규칙 제26조제2항).",
    "임대주택의 입주자로 선정된 자가 언제까지 거주할 수 있다고 규정하는가":
        "주택공급규칙 제29조제4항: 임대기간 만료시까지 거주 가능. 민간임대주택특별법 제43조제1항: 그 기간은 '임대의무기간'.",
    "어떤 법률들을 적용한다고 규정하는가":
        "특별법 제3조: 「주택법」·「건축법」·「주택임대차보호법」 적용. 주택공급규칙 제2조: '공급'은 「주택법」 제38조 대상 주택·복리시설의 분양 또는 임대.",
    "주택의 공급방법을 어떤 세 가지로 구분하는가":
        "주택공급규칙 제10조제1항: 일반공급·특별공급·단체공급. 민간임대주택특별법 제42조제1항: 임대사업자가 정함.",
}

# explicit shorter verbatim gold_term substitutions (each must remain a substring of the source)
GOLD_FIX = {
    "입주자저축을 해약한 날부터 1년 이내에 입주자저축을 다시 납입하는 경우": "1년 이내에 입주자저축을 다시 납입",
    "「주택법」(이하 “법”이라 한다) 제38조의 적용대상이 되는 주택 및 복리시설을 분양 또는 임대하는 것":
        "제38조의 적용대상이 되는 주택 및 복리시설",
}


def main() -> int:
    rows = json.loads(RAW.read_text(encoding="utf-8"))
    shutil.copy(RAW, RAW.with_suffix(".json.bak"))
    n_ans = n_gold = 0
    for row in rows:
        it = row["item"]
        q = it.get("question", "")
        for key, newans in ANSWER_FIX.items():
            if key in q and len(it["answer"]) > 100:
                it["answer"] = newans
                n_ans += 1
                break
        gts = it.get("evaluation", {}).get("gold_terms", [])
        for i, t in enumerate(gts):
            if t in GOLD_FIX:
                repl = GOLD_FIX[t]
                # safety: confirm replacement is verbatim in a cited source
                cited = [e["source_id"] for e in it.get("evidence", [])] or it.get("source_ids", [])
                if any(norm(repl) in norm(full_text(s)) for s in cited):
                    gts[i] = repl
                    n_gold += 1
    RAW.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"tightened {n_ans} answers, {n_gold} gold_terms (backup: {RAW.with_suffix('.json.bak').name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
