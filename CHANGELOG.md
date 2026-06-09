# Changelog

## v0.8 — human-review repair build (1,997 QA)

Supersedes the v0.6 dataset build. The v0.7 release falsely described the data as "v0.6 unchanged"; v0.8
is the first build where the QA content was substantively repaired through an LLM-assisted human-review
pass (gpt-5.4 grounding triage + cross-model verification + source-grounded fixes).

### Changed
- **Positional-cloze eliminated.** All ~686 templated `"X 다음/앞에 제시된 값은?"` / `[위치 탐침]` questions
  (34% of the dataset — a string-matching probe, not document understanding) were regenerated into natural,
  source-grounded questions (679 regenerated; Claude generate → gpt-5.4 cross-model verify) or removed.
  `question_style` is now 100% `real_user`/`professional_analyst` (was 92.2%); cloze-phrased ≈ 0% (was 7.8%).
- **Location mislabels fixed (source-grounded):** 항동(sh-196920) 서울특별시→구로구 (15 answers + 51
  region_sigungu); jpdc-ildo 제주특별자치도→제주시; 발산8단지 region_sigungu →서울특별시 강서구. region_sigungu
  normalized to the full `서울특별시 구로구` form. (Verified ih-cheonwon / bmc-youth as correctly 시·도-level
  city-wide programs — NOT changed.)
- **Confirmed wrong answers fixed:** table 0910 평균 전용면적 29.58→24.10 (gold cited the wrong row).

### Removed (14 unrepairable / confirmed-broken items; 2,011 → 1,997)
- correction_notice_reasoning 0901/0902 (gold falsely claimed `정정 공고` from an unrelated `정정` string),
  ungrounded table item 1035, malformed schedule items 1148/1157/1160, and 8 cloze items whose regeneration
  did not pass cross-model verification.

### Known limitations (carried to v0.9)
- ~20 `cross_document_legal_reasoning` gold answers are concise, grounded paraphrases of the cited statute
  article that omit secondary qualifiers (e.g. `1세대 1주택`, `시·도지사 승인 예외`); grounded but not exhaustive.
- `region_sigungu == region_sido` remains on ~270 items for announcements whose true 시·군·구 was not resolved
  (a v0.9 metadata sweep); the 항동/jpdc/발산 cases were fixed.
- Human review of v0.8 was LLM-assisted (gpt-5.4 + Claude cross-model), not a full human pass.

### Tooling
- Provider-agnostic triage/verification runner (`run_triage_v08.py`), regeneration + integration pipeline,
  and gates all green: `validate_dataset.py`, `verify_qa.py` (1,997/1,997), `check_public_release_readiness.py`
  (public-ready), `check_question_realism_v06.py` (0 failures).

## v0.7 — research preview (over v0.6 build, 2,011 QA)
Added a provider-agnostic baseline runner, full-context / RAG smoke diagnostics, retrieval diagnostics, and
a repository scope policy on top of the (then-unchanged) v0.6 dataset build. Zenodo DOI 10.5281/zenodo.20570856.

## v0.6.x — source-expansion + quality / realism build (2,011 QA)
Multi-provider source expansion, realism phrasing pass, near-duplicate clustering, materialized
long-context bundles, and public release splits. Archived as v0.6.3 (DOI 10.5281/zenodo.20563604).
