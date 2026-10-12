# 사전 명시: dev 1,534문항 전수 사람 검수 (초안)

- 작성일: 2026-10-12. 작성: kr-housing 리뷰어2. 프로토콜: `final2_engexpert.md` §24 실행용(A–G).
- 상태: 주석자 4명 결정, 검수 시트 생성 완료(2026-10-12, G절). 라벨 수집 전이다.
- 스크립트: `scripts/v097/export_dev_review.py`. 근거 텍스트가 필요하므로 저자의 내부 작업본(internal review material, not released)에서 실행한다. 공개 파일은 v0.9.6(8ced8fe)에서 읽는다.
- 규칙: 아래 G절 항목은 라벨 수집 전에 고정하고, 라벨을 본 뒤 바꾸지 않는다. 바꿀 일이 생기면 바꾸기 전에 날짜를 적은 개정 절을 이 문서에 추가하고, 원래 규칙의 결과도 함께 보고한다.

## A. 범위

- 대상: 평가 대상 dev **1,534문항** = `data/qa_v0.6_dev.jsonl` 1,608 − cross_document_legal_reasoning 67 − `data/v0.9.3/eval_exclusions.txt`의 dev 7. dry-run에서 1,534를 확인했다.
- 포함: 122 bundle 제외 문항, 탐지기 플래그 54, 2차 라운드 100문항(이전 라벨과의 일관성 점검용) 모두.
- 제외: legal 67, 이미 평가에서 뺀 7.
- 참고 열 `stage`: 1 = BM25·FC 열과 pooled 표의 dev 분모 964(번들 있음, `bundle_exclusions.txt`에 없음), 2 = 나머지 570(번들 없음 448 + 122). 배정과 무관한 정보 열이다.
- 단위: 문항. 각 문항을 비저자 주석자 **정확히 2인**이 독립으로 라벨한다.

## B. 배정

- 가족 교차 섞기: 가족별로 묶어 `random.Random(20261012)`로 가족 안을 섞는다. 그 뒤 가족 크기에 비례해 교차 배열한다(키 = (가족 내 순위 + 난수) / 가족 크기).
- 블록: 50문항씩 끊어 **31블록**을 만든다(마지막 블록 34).
- 쌍 목록 P: n명의 모든 2인 조합을 고정 순서(사전식 AB, AC, …)로 둔다. 블록 k(0부터)는 P[k mod |P|]에 간다.
- dry-run 배정 수:

| n | 쌍 수 | 주석자별 문항 | 쌍별 공유 문항 |
|---:|---:|---|---|
| 2 | 1 | A 1,534, B 1,534 | AB 1,534 |
| 3 | 3 | A 1,034, B 1,034, C 1,000 | AB 534, AC 500, BC 500 |
| 4 | 6 | A 784, B 784, C 750, D 750 | AB 284, 나머지 쌍 각 250 |

  모든 n에서 문항 1,534개가 정확히 2인에게 배정됨을 확인했다. 31블록이 쌍 수로 나누어떨어지지 않아 분량 차이가 블록 하나(34~50문항) 생긴다.
- 블록별 가족 분포: 큰 가족(long_context 474, table_numeric 485, aggregation 180, answerability 90, multi-doc 82, format 60, eligibility 56)은 31블록 모두에 들어간다. 작은 가족(long_distance 35, region 27, provider 25, schedule 20)은 19–25블록에 들어간다.
- 배정표 `assignment.csv`(qa_id, block, annotator_a, annotator_b, stage, family, route)는 라벨 수집 전에 고정하고, 라벨과 함께 공개한다. 주석자 문자(A, B, …)와 실제 사람의 대응은 공개하지 않는다.

## C. 검수 시트

- 파일: 주석자마다 `dev_review_<문자>_INTERNAL.csv`(UTF-8 BOM). 근거가 셀 한도(30,000자)를 넘는 문항은 셀에서 자르고 전체를 `evidence/<qa_id>.txt`로 함께 준다(dry-run 123문항, 대부분 일치 행이 많은 집계·실거래 문항).
- 보이는 열: no, block, qa_id, family, route(script / cloze_regenerated / template_reworded), question, original_question(현재 문구와 다를 때만), gold(복수 정답은 ` ‖ `로 전부; v0.9.2 gold_fixes 반영), locators, evidence.
- 근거 텍스트(저자의 내부 작업본; internal review material, not released):
  - 인용 페이지 전문
  - 술어 문항: 공고 페이지 + 술어(조건·연산·재계산 값·행 수) + **일치 행 전부**. 집계 필드는 재계산에 실제 쓰는 값을 표시한다(파생 필드 `dealAmount_manwon` 포함).
  - 표 셀 문항: 머리글 행·열을 포함한 표 전체 블록. 정답 셀은 ★로 표시한다.
  - 비교 문항: 두 페이지
  - 답변 불가 문항: 인용 페이지와 locator(없다고 주장하는 사실)
- 라벨 열:
  - verdict ∈ {no_error, error, unsure}
  - verdict = error이면 type ∈ {dual_row, header_parse, multiple_schedules, wrong_gold, scope, unspecified, other}
  - memo(자유, 비공개)
  - 자연스러움은 수집하지 않는다.
- 오류 정의(안내문에 적음): test 검토의 q1–q3 중 하나라도 no에 해당하면 error다.
  - q1: 질문이 한 가지로 읽히지 않는다(원문에 맞는 답이 둘 이상).
  - q2: 근거가 gold를 뒷받침하지 않는다.
  - q3: gold가 틀렸거나 빠진 것이 있다.
- 시트 머리와 `README_INTERNAL.txt`: "internal review material; source text not for redistribution". 시트는 git 저장소 밖에 쓴다. 공개는 라벨과 배정표만 한다.
- 생성 뒤 검사(오류가 하나라도 있으면 `--write`가 멈춘다):
  - 문항 수 1,534
  - 빈 근거
  - 술어 문항의 집계 필드 null(2차 라운드 "실거래 열 공란" 재발 방지)
  - 표 셀 문항의 표나 정답 셀 누락
  - 재계산 실패
- dry-run 검사 결과: **오류 0**(빈 근거 0, null 0, 표·정답 셀 누락 0, 재계산 실패 0).
  - 경고("gold 문자열이 근거에 없음") 200건은 정보용이다. 대부분 정답이 원문 문자열이 아닌 구조다: multi-doc 82, 답변 불가 56, region 27, provider 25(정답이 "지역 / 지역", "확정할 수 없음" 형태).
  - 나머지 10건은 cloze 재생성 문항(long_context 8, long_distance 2)이다. 이 10건은 검수 때 근거를 주의해서 보도록 저자 메모에 남긴다.
- 안내: 독립 작업, AI 도구 금지, 기한(사용자 지정), 질문은 저자에게 문항 ID로만.

## D. 조정과 결과 처리

- 조정 대상: 주석자 1인 이상이 error로 표시한 문항과, 주석자가 unsure + "시트 문제" 메모를 단 문항. 그 밖의 unsure는 오류가 아니며 조정 대상이 아니다(두 사람 모두 unsure인 문항 수만 보고).
- 조정 결과(문항마다 하나, `score_dev_review.py`가 다른 조합이면 멈춘다; 2026-10-12 engexpert 결정):
  - final_error = yes: 최종 type과 함께 조치 action ∈ {gold_accept_any(복수 정답 목록), gold_replaced(gold 교체), locator_fixed(근거 locator만 수정, 질문·gold 불변), excluded(질문 결함: 평가 제외, 릴리스 유지)} 중 하나가 반드시 있어야 한다. "오류지만 고칠 것 없음"이라는 상태는 두지 않는다.
  - final_error = no: 이유 reason ∈ {annotator_misread, sheet_defect, other}를 적는다.
- 조정 규칙(라벨 전 고정):
  - (i) 두 주석자가 같은 type으로 error라고 한 문항을 no_error로 뒤집으려면 근거를 메모한다.
  - (ii) 시트 결함(열 누락 등)으로 생긴 error 표시나 "시트 문제" unsure는 final_error = no, reason = `sheet_defect`로 적고 따로 센다. 오류에 넣지 않는다.
- 처리(test와 같음):
  - 질문은 바꾸지 않는다.
  - gold를 넓히거나(gold_accept_any) 바꿔서(gold_replaced) 고칠 수 있으면 고친다.
  - 근거 위치만 틀렸으면 locator를 고친다(locator_fixed).
  - 질문 자체가 결함이면 평가에서 빼고 릴리스에는 남긴다(excluded).
  - 122 bundle 제외와는 독립이다(두 플래그가 함께 있을 수 있다).
- locator_fixed의 새 근거 쪽(2026-10-12 고정, 벤치마크 전문가 §29; 산출 전에 기록함):
  - 규칙: "locator set by rule: the only page of the same announcement that contains the gold value; present in every bundle tier; author-confirmed".
  - gold 값: 문항의 gold 중 결함 페이지에 해당하는 값이다. 집계 문항은 술어의 `_query_area_name`, 비교 문항은 gold를 " / "로 나눈 해당 순번 값(`기관=지역` 형식이면 지역)이다. 시·도는 약칭(서울, 대전, 광주, 경기)도 허용한다.
  - "contains"(최종 구현): 같은 공고의 쪽에서 gold 값이 나오는 자리 앞 40자 안에 위치 표지(공급위치, 위 치, 위치:, 소재지, 건설·사업위치, 일원, 대상지, 주소)가 있거나 뒤 25자 안에 "일원"이 있고, 그 창(앞 40자 + 값 + 뒤 30자)에 비위치 맥락(계약체결 장소, 견본주택, 접수, 거주, 재학, 교통, 구청, 문의 등)이 없는 쪽이다. 값 안의 공백은 무시한다.
  - 기록(투명성): 규칙 문장(위 따옴표)은 산출 전에 적었다. 세부 판정 방식은 같은 날 이 30문항을 계산하면서 세 번 고쳤다. (1) 처음에는 줄 단위였으나, 일부 추출 쪽이 한 줄로 이어져 있어 앞뒤 창 방식으로 바꿨다. (2) 값 뒤의 "일원"을 표지로 넣었다. (3) "계약체결 장소"를 비위치 맥락에 넣었다. 고칠 때마다 원문을 보고 판정이 틀린 사례를 확인했다(2025 신창·하남 p.1의 "위 치 광주 광산구"를 놓친 일; 항동 p.2 "서울특별시 구로구 연동로 245 일원"을 놓친 일; 신탄진 p.36 계약 장소 주소를 공급위치로 잡은 일). 최종 판정은 저자 확인(`confirm_locators.csv`)으로 정한다.
  - 번들 포함: 그 문항의 번들과, 옛 근거 쪽을 담은 모든 tier 번들에 새 쪽이 있는가.
  - 처리:
    - (a) 후보 1개이고 모든 tier에 있음 → new_locator로 채운다.
    - (b) 후보가 여럿 → 후보 목록을 남기고 저자가 고른다(note "author-selected among n"). excluded로 돌리지 않는다.
    - (c) 같은 공고에 있지만 번들에 없음 → 그 쪽을 locator로 두고 bundle 제외 플래그를 단다(122와 독립).
    - (d) 공고 어디에도 없음 → 재조정 대상.
  - 모든 행은 저자가 `confirm_locators.csv`(qa_id, 새 쪽, gold 앞뒤 약 100자)로 일괄 확인한다.
  - 스크립트: `scripts/v097/locator_candidates.py`. 입력은 내부 작업본의 추출 페이지와 번들 manifest(not released)이고, 모델 호출은 없다.
- 기록:
  - `errata_v0.9.7.csv`: v0.9.3 errata와 같은 열 — qa_id, split, task_type, errata_type, v0.9.7_status, old_answer, new_answer_or_accepted, source=human_review_v0.9.7, note. 상태 값은 gold_accept_any, gold_replaced, locator_fixed(새 locator는 note에), excluded_from_evaluation 넷뿐이다. errata_type은 v0.9.2 명칭(dual_row_gold, ill_posed_header_parse, multiple_schedules, wrong_gold, scope_mismatch, unspecified_type, other)으로 적는다.
  - `eval_exclusions` 갱신
  - `results/human_review_v0.9.7/`: annotator_labels.jsonl(qa_id, annotator, block, verdict, type), adjudication.jsonl(qa_id, n_flag, final_error, final_type, action, reason), assignment.csv, seed, 스크립트
- 재판정: gold가 바뀐 문항(gold_accept_any, gold_replaced)의 dev 예측만 두 판정자로 다시 판정한다(OpenAI 4모델 × CB/BM25/FC 해당 설정). 생성 호출은 0이고, 판정 호출 수는 수정 문항 × 모델 × 설정이다. pooled 표, dev 표, recall 분모(964 등)를 갱신한다.

## E. 보고

- dev 오류율 = 최종 오류 / 1,534, Wilson 95%. "1인 이상 플래그 / 2인 모두 / 최종" 세 수를 test Table S4 형식으로 낸다.
- 쌍별 raw 일치율, Cohen κ, PABAK를 test Table S3 형식으로 낸다.
- 가족별 오류율 표(Wilson)와 생성 경로 요약 한 줄(script / cloze_regenerated / template_reworded 각각의 오류율과 Wilson; test의 14.0%·2.4%와 같은 단위). 표 메모: "route is nearly determined by family in dev". 유형별 수와 조치별 수(test Table S5 형식), 조정 후 오류가 아닌 문항의 reason별 수(sheet_defect 포함).
- 탐지기 교차표: 54 플래그 중 확정 오류(precision), 확정 오류 중 플래그(recall). 전수 검토 뒤 "unverified" 라벨은 지운다.
- 2차 라운드 100문항: 이전 라벨과 새 라벨의 일치율.
- test 8.4%와 나란히 둔다.
- 2차 라운드 표본 추정치 7.0%는 S2에 "superseded by the full review"로 남긴다.
- 원고에서는 "complete human validation"을 주장하지 않는다(legal 67 미검수, 비전문가 주석자, 저자 조정).

## F. 원고에서 바뀔 자리

`final2_engexpert.md` §24 F를 따른다: 초록, §1 53행, §3.2 145–147행, §7 Item verification, S2 345–372행과 tab:corrections, 데이터시트 47–50행과 verification status, Declarations Annotators, Data availability errata 목록, S3 분모.

## G. 라벨 수집 전에 고정하는 것

범위(A), 배정표와 seed(B), 시트 양식과 오류 정의(C), 조정 규칙과 처리 규칙(D), 보고 표 형식(E), 재판정 범위(D). 고정 시점에 다음 해시를 이 절에 적는다: 스크립트, `assignment.csv`, 주석자 안내문.
- 주석자 안내문 `INSTRUCTIONS_ko.md`(이 디렉터리) sha256: `bbd2963000ce552571c6ecad7820f5b98c033ec8cac7a541c0cc5275a23b3d4e`(2026-10-12 고정).
- 시트 생성(2026-10-12, 주석자 4명 결정 뒤):
  - 명령: `python3 -I scripts/v097/export_dev_review.py <internal working copy> --data-root <dataset v0.9.6> --annotators 4 --write <internal output directory>`
  - 공개 파일은 v0.9.6(8ced8fe, 깨끗한 작업 트리)에서, 근거 텍스트는 저자의 내부 작업본(HEAD be275d4)에서 읽었다. 검수 시트는 원문을 담고 있어 공개하지 않는다(internal review material, not released).
  - 스크립트 sha256(`scripts/v097/export_dev_review.py`와 같은 파일): `b22bc6f71170f1711221f6a482b295dcc445f05e9d5013c42baddaaff896d002`
  - `assignment.csv` sha256: `24acf1bd700294039c1b9ea4883d1c7f2b63dbfbfb83b6a049ab5ce29ff750ef`. 이 디렉터리의 `assignment.csv`가 그 파일이다.
  - 생성 뒤 검사: 1,534문항, 각 문항 정확히 2인(annotator_a ≠ annotator_b, 중복 0), 빈 근거 0, 표·정답 셀 누락 0, 집계 필드 null 0, 재계산 실패 0. 경고("gold 문자열이 근거에 없음") 200은 C절 설명과 같다.
  - 주석자별 문항: A 784, B 784, C 750, D 750. 쌍별 공유: AB 284, AC·AD·BC·BD·CD 각 250.
  - 셀 한도를 넘는 근거 123문항은 `evidence/`에 있다. 주석자 폴더에는 본인 문항분만 넣었다(A 59, B 67, C 56, D 64; 합 246 = 123 × 2).
  - 전달 묶음: `annotator_<X>/`(본인 시트, 본인 `evidence/`, `INSTRUCTIONS_ko.md` 사본, `README_INTERNAL.txt`)와 같은 내용의 `annotator_<X>.zip`. 각 폴더의 시트 문항 집합이 `assignment.csv`와 일치함을 확인했다.
  - 시트 sha256: A `a801774522c680687541ea5018a13c9b47598c8a906d7ad0df6600e21a234b78`, B `47f390cef40ffef345e98bba01b0f681c9b8813ca18204fd40055f8686724c8b`, C `977333c25409bc4df8598d4f35e4fe1d17799656ef1f0d18fc428c773b79c1d9`, D `bc13de206d9c24e7a7fe78bf061484461e1ada718a6bfdcbb333d3889dd6a964`
  - 주석자 문자(A–D)와 실제 사람의 대응은 저자만 알고, 공개하지 않는다.

## 미결

1. (결정) 주석자 4명(2026-10-12). 시트를 만들었다(G절). 보상과 기한은 사용자 결정으로 남아 있다.
2. (해결) 주석자 안내문을 작성했다(G절 해시). 시트 결함으로 보이는 행은 unsure + memo "시트 문제"로 받아 D(ii)의 sheet_defect로 센다.
3. (결정) 분량 차이: n = 3, 4에서 31블록이 쌍 수로 나누어떨어지지 않아 주석자 간 최대 34문항 차이가 생긴다. 현 블록 규칙을 유지하고 이 차이를 허용한다.
