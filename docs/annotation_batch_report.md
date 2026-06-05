# Annotation Batch Report — v0.2 Seed

- 배치: `v0.2` (KR-Housing-LongRAG-Bench)
- 작업일: 2026-06-04
- 산출물: `data/qa_v0.2_candidates.jsonl` (70개), `workspace_local/{raw,processed,audit}/`, 본 리포트
- 파이프라인: Explore → Plan → Acquire → Extract → Annotate → Verify → Report (동적 워크플로우)

> 핵심 원칙 준수: 공개 릴리즈 파일에는 원문 PDF/HWP/CSV, 긴 OCR/발췌, 스크린샷을 넣지 않았다.
> 원문은 전부 `workspace_local/`(릴리즈 제외, `.gitignore`)에만 저장했고, 공개물은 URL·source_id·evidence
> locator·단답·결정론 스크립트만 포함한다.

---

## 1. 처리한 Source 목록

### 1.1 승인 + 취득 완료 (7개)

| source_id | 유형 | 라이선스 근거 | 취득물 | 추출 |
|---|---|---|---|---|
| `law-housing-supply-rule` (주택공급에 관한 규칙) | 법령 | 저작권법 §7 비보호 | 본문 HTML 602KB (lsInfoR.do, efYd=20150608) | 조문 63, 별표참조 32, 수치사실 334, 99,992자 |
| `law-public-housing-special-act-rule` (공공주택 특별법 시행규칙) | 법령 | §7 비보호 | 252KB (efYd=20180928) | 조문 50, 별표참조 38, 수치 39 |
| `law-private-rental-housing-special-act` (민간임대주택에 관한 특별법) | 법령 | §7 비보호 | 176KB (efYd=20151229) | 조문 67, 별표참조 0, 수치 41 |
| `kogl-license-guide` (공공누리 유형안내) | 정책 | 공식 라이선스 정책 | HTML 136KB | 유형 0~4 + AI 조건 표 |
| `public-data-portal-use-policy` (공공데이터포털 이용정책) | 정책 | 공식 정책 | HTML 168KB | 제3자권리 처리 원칙 |
| `hug-sale-history` (주택도시보증공사 분양이력정보) | 공공데이터 | 이용허락범위 제한 없음 | **메타데이터만** 155KB | 포맷=XML, 무료, 키워드 필드 |
| `molit-apt-official-price-2025` (국토교통부 주택 공시가격) | 공공데이터 | 이용허락범위 제한 없음 | **메타데이터만** 160KB | CSV, 15,580,435건, UTF-8 |

- 모든 취득물은 SHA-256·URL·파일명·크기·다운로드일을 `workspace_local/audit/{source_id}.json`에 기록.
- 법령 본문 취득 경로(재현 가능): `https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq={lsiSeq}&chrClsCd=010202&efYd={efYd}`
  (DRF Open API는 OC 키+IP 등록이 필요해 사용 불가 → 공개 본문 엔드포인트로 대체. efYd 자동 발견.)

### 1.2 이번 배치 미처리(연기) — manifest_only 유지 (2개)

| source_id | 사유 |
|---|---|
| `lh-sale-announcements` | LH 동적 청약포털의 PDF/HWP 첨부. 폼/세션 게이트로 결정론적 취득 불가. |
| `lh-third-new-town-pre-announcements` | 동일(동적 포털). 원문 재배포 리스크도 있어 보류. |

### 1.3 제외 클래스 (변경 없음 — `data/excluded_sources.jsonl`)

민간 은행 상품설명서, 민간 보험약관, 민간 건설사 공고 PDF, 도면/조감도/브로슈어, 개인 신청·민원 문서.
모두 `excluded` 또는 `excluded_pending_permission` 유지.

---

## 2. 승인 / 제외 집계

- 매니페스트 등재 source: **9** (법령 3 · 공공데이터 2 · 정책 2 · LH공고 2)
- 이번 배치 취득·추출: **7** / 미처리(연기): **2**(LH)
- 제외 클래스(별도 레지스트리): **6**
- 신규 외부 source 추가: **0** (라이선스 불명확 source를 공개 QA에 끌어들이지 않음 → 중단 조건 회피)

---

## 3. 다운로드 / 추출 성공 여부

- 다운로드: **7/7 성공** (법령 3 전문, 정책 2, 공공데이터 메타 2). audit JSON 7개 생성.
- 추출: **7/7 성공**. `workspace_local/processed/*/extraction_report.json` 7개 생성.
  - 법령: `document_pages.jsonl`(조문) · `tables.jsonl`(in-text 열거 + 별표 참조) · `chunks.jsonl` · `numeric_facts.jsonl`.
  - locator 보존: `법령명 [시행 YYYY.M.D.] lsiSeq=... / 제N조(제목)` + 항/호.

### 3.1 추출 실패 / 한계 (정직 기록)

| 항목 | 원인 | 대체 방법 |
|---|---|---|
| 별표(別表) 표 내용 | 본문 HTML에 텍스트 미임베드, HWPX/PDF 첨부로 분리 | `flDownload.do?flSeq=...` locator를 `tables.jsonl`에 보존. 다음 배치에서 HWPX(zip+XML) 파싱. |
| HUG 분양이력 실데이터(행) | data.go.kr serviceKey(IP 등록) 미보유 | 메타/스키마 라벨만 사용. 키 발급 후 행 기반 QA. |
| MOLIT 공시가격 실데이터 | 약 15.58M행 포털 다운로드(세션/이용신청) 게이트 | 메타데이터 사실만 사용. 다음 배치 시·군·구 샘플링. |
| LH 공고 PDF/HWP | 동적 포털 + 재배포 리스크 | 미사용. 포털 메타/필드 단위 QA 또는 명시적 허가 후 진행. |

---

## 4. QA Task Family별 개수 (총 70개, MECE)

| task_type | 개수 | 생성 방식 |
|---|---|---|
| `table_numeric_reasoning` | 17 | 결정론(수치 cloze·호 카운트·조문 간 비교) |
| `retrieval` | 12 | 결정론 6(조문 제명) + agent 6(자연어 단일사실) |
| `cross_document_legal_reasoning` | 10 | agent(법령 2종 결합, 다중 근거) |
| `answerability_detection` | 9 | 결정론 4 + agent 5 (negative control, 부재 검증) |
| `format_robustness` | 8 | 결정론(동일 표 → text/markdown/csv/json 4형식) |
| `cross_source_aggregation` | 7 | 결정론 2 + agent 5 (법령+메타/HUG+MOLIT/KOGL+정책) |
| `long_distance_retrieval` | 7 | agent(뒷부분 조문, evidence_position=late) |

- 생성 출처: 결정론 **37** + agent **33** (agent 1개는 검증 게이트로 드롭).
- 메트릭 분포: `exact_numbers` 23 · `contains_all` 21 · `term_recall` 10 · `boolean_and_reason` 9 · `term_overlap` 5 · `exact_match` 2.
- 다중 source(≥2) QA: **18개** (cross-document / cross-source).
- source 활용도: supply 36 · public-rule 22 · private-act 18 · hug 5 · molit 4 · kogl 2 · portal 1.

각 QA는 필수 필드 전부 포함: `qa_id, task_type, question, answer, answer_type, source_ids,
required_capabilities, evidence(locator), evaluation(metric), copyright_note`.
공개 파일 기준 최대 답변 길이 105자, gold_term 최대 34자(긴 원문 문장 금지 준수).

---

## 5. 검증 완료 / 미완료

### 5.1 다층 검증 (모두 통과)

1. **결정론 생성-시 검증** (37개): 답을 추출 데이터에서 직접 산출/대조하여 통과한 항목만 방출
   (`scripts/build_qa_candidates.py`). 예: answerability negative control 3건은 용어가 실제로 번들에 존재해
   자동 드롭(거짓 unanswerable 차단).
2. **적대적 reviewer pass** (agent 33개): Workflow의 family별 reviewer agent가 `supported`(근거 뒷받침)·
   `unambiguous`(유일 정답) 판정. 34/34 통과.
3. **Grounding 게이트** (`scripts/assemble_qa.py`): 모든 gold_term/gold_number가 인용 source 원문에 verbatim
   존재해야 채택. agent 1건 드롭(`1000` vs 원문 "1천만원" 불일치) — 게이트 정상 작동.
4. **독립 재검증** (`scripts/verify_qa.py`): 빌드 파이프라인을 신뢰하지 않고 공개 파일을 원문과 재대조.
   → **70/70 verified, 0 failed** (`workspace_local/audit/verification_report.json`).
5. **수기 스팟체크** (별도 reviewer pass): 핵심 수치/법령 답 8건 + answerability 부재 전제 8건을 추출 원문에
   직접 grep하여 정답·문맥·부재를 확인 → 전부 PASS.
6. **데이터셋 validator**: `python3 scripts/validate_dataset.py` →
   `OK: 9 sources, 12 QA seed items, 6 blueprints, 70 QA v0.2 candidates`.
   (validator를 v0.2 파일 검사 + 필수 필드/ locator/metric 강제 검사로 확장.)
7. **금지 필드/유출 스캔**: `raw_text|raw_content|document_text|pdf_text|hwp_text|full_context` 부재 확인,
   `data/` 하위에 원문 아티팩트(html/hwpx/pdf/csv) 없음 확인.

### 5.2 미완료

- 별표 표 기반 수치 QA(가점제·과태료 등): 별표 미파싱으로 **이번 배치 미생성**. (다음 배치)
- HUG/MOLIT 실데이터 기반 table/numeric QA: 실데이터 미취득으로 **미생성**. (다음 배치)

---

## 6. 남은 라이선스 / 컴플라이언스 리스크

- **공개 QA 기준 리스크: 없음.** 모든 정답은 (a) 저작권법 §7 비보호 법령 본문, 또는 (b) `이용허락범위 제한 없음`
  공공데이터 메타데이터 사실, 또는 (c) 공식 라이선스 정책 사실에 근거. 원문 재배포 없음(locator+단답만).
- HUG/MOLIT **실데이터 미배포** — 메타데이터 사실만 사용하므로 안전. 향후 실데이터 도입 시 포털·제공기관 약관
  재확인 필요.
- 별표 HWPX는 **다운로드하지 않고 locator만 보존** — 콘텐츠 추출 시 §7 비보호이나 형식 변환·재배포 정책을
  재확인할 것.
- LH 공고 PDF/HWP는 사용하지 않음(동적 포털 + 재배포 리스크).
- 개인정보: 처리한 7개 source(법령·정책·공공데이터 메타) 모두 개인정보 미포함 — 중단 조건 미발동.

---

## 7. 다음 배치 추천

1. **별표 파싱**: HWPX(zip+XML) 파서로 주택공급규칙 별표(가점제 점수표 등)·민간임대주택법 시행령 과태료 별표를
   셀 단위 추출 → 진짜 표 기반 numeric/format-robustness QA 확대.
2. **HUG Open API 키 발급** → 분양이력 실제 행으로 table filtering·numeric aggregation·cross-source(법령+표) QA.
3. **MOLIT CSV 샘플링**(시·군·구/단지 단위 부분 취득) → large-table aggregation. (전체 15.58M행은 비현실적.)
4. **법령 확충**: 주택법, 공공주택 특별법(본법), 주택임대차보호법, 각 시행령 추가 → cross-document 깊이·체인 확대.
5. **버전 민감도**: 현행(최신 efYd) 버전 병행 수록 + 버전 ablation(고정 lsiSeq vs 현행).
6. **Context tier 머터리얼라이즈**: 라이선스 안전 공공 문서를 distractor로 사용해 32K~512K 번들 구성
   (evidence 위치 early/middle/late 통제) — full-context vs RAG 비교 실험용.
7. **LH 공고**: 포털 메타/필드 단위 QA(원문 PDF 미배포) 또는 명시적 재배포 허가 확보 후 본문 도입.

---

## 8. 산출 파일 인덱스

### 공개(릴리즈 가능)
- `data/qa_v0.2_candidates.jsonl` — 70 QA (locator+단답)
- `data/source_manifest.jsonl` — `v0.2_acquisition` 상태 필드 추가
- `scripts/acquire_sources.py`, `extract_statutes.py`, `extract_metadata_pages.py`,
  `build_evidence_index.py`, `build_qa_candidates.py`, `assemble_qa.py`, `verify_qa.py`,
  `tighten_agent_qa.py`, `update_manifest_status.py`, `qa_common.py`, `validate_dataset.py`(확장)

### 내부 전용 (`workspace_local/`, 릴리즈 제외)
- `raw/{source_id}/…` — 원문 HTML(법령 본문/정책/메타)
- `processed/{source_id}/` — document_pages·tables·chunks·numeric_facts·extraction_report·format_variants
- `audit/{source_id}.json` — SHA-256/URL/크기/날짜/라이선스 관찰
- `audit/qa_det.jsonl`, `qa_agent_raw.json`, `qa_dropped.json`, `qa_v0.2_provenance.jsonl`,
  `verification_report.json`, `index_*.json`

---

## 9. 완료 기준 점검

- [x] `workspace_local/audit/*.json` 생성 (7 source + 검증/계보 로그)
- [x] `workspace_local/processed/*/extraction_report.json` 생성 (7)
- [x] `data/qa_v0.2_candidates.jsonl` 50개 이상 — **70개**
- [x] `docs/annotation_batch_report.md` 생성 (본 문서)
- [x] validator 통과 (`OK: … 70 QA v0.2 candidates`) + 독립 검증 70/70
