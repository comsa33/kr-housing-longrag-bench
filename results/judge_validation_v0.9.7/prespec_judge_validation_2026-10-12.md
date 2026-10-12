# 사전 명시: 판정자 검증 2차 표본 (초안)

- 작성일: 2026-10-12. 작성: kr-housing 리뷰어2. 설계 근거: `final2_engexpert.md` §23 "추가 3", "추가 4".
- 상태: **초안.** 사용자 승인 전이다. 승인 전에는 표본 파일을 만들지 않는다(`--write` 미실행).
- 스크립트: `scripts/v097/sample_judge_validation.py`. 실행 위치는 데이터셋 레포 루트(v0.9.6, 8ced8fe)다.
- 규칙: 이 문서는 표본을 뽑기 전에 고정한다. 라벨이나 결과를 본 뒤 표본, 셀, seed, 보고 단위를 바꾸지 않는다. 바꿀 일이 생기면 바꾸기 전에 이 문서에 날짜를 적은 개정 절을 추가하고, 원래 결과도 함께 보고한다.

## 1. 목적

주 판정자(claude-sonnet-5-5)와 보조 판정자(gpt-4.1-mini)가 **보고된 test_public 예측 전반**에서 사람 판정과 얼마나 일치하는지 추정한다. 1차 검증 표본(80건)에는 세 가지 한계가 있었다.
- OpenAI 4개 모델만 포함했다.
- 76건이 retrieval 예측이었다.
- 당시 주 판정자(gpt-4.1-mini)의 YES/NO로 균형을 맞췄다.

또 공개 파일 대조 결과, 80건 중 test 문항은 6건뿐이었다(dev 74, legal 8 포함). 2차 표본은 이 한계를 보완한다.

## 2. 모집단과 셀

- 문항: test_public 중 평가 대상 342문항(legal 가족과 `data/v0.9.3/eval_exclusions.txt`의 5건 제외).
- 예측: `results/predictions_v0.9.5/`의 **보고된 실행만** 쓴다. 재실행 파일은 qa_id별로 덮어쓴다. 셀별 파일 순서는 스크립트의 `CB`/`BM25`/`DENSE`/`FC`/`K50`/`OPENREGION`/`ORACLE` 표에 고정되어 있다.
  - CB: 원래 실행 → gpt-5.5 빈 답 재시도 → 누출 수정 재실행. glm-5.2는 reasoning on 실행.
  - FC: 512k는 fixed 재실행으로 덮어쓴다.
  - minimax-m3 k=50은 보고된 reasoning-on 실행이다.
- 셀 50개:
  - 8모델 × {CB, BM25, dense, FC}: 셀 모집단 342 / 339 / 339 / 98(gpt-5.4 두 모델은 77)
  - 6개 full-window 모델 × {dense k=50, open-region, oracle}: 셀 모집단 81
- 판정 라벨: 예측 파일의 `judge_label`(주)과 `judge_label_secondary`(보조). 공개된 판정과 같다.

## 3. 추출 규칙

- 셀마다 4건을 무작위로 뽑는다(`random.Random(20261012)`, 셀 순서는 설정 → 모델 순서로 고정). 합계 50 × 4 = 200건이다.
- **판정 라벨로 균형을 맞추지 않는다.** 셀당 최소 NO 규칙도 두지 않는다.
- 비문자열 정답을 따로 거르지 않는다.
- 보조 층(선택, `--aux-string-mismatch`): 모델마다 2건, 합계 16건. 본 표본을 뽑은 뒤 같은 난수열로 이어서 뽑는다. 본 표본과 겹치는 (qa_id, model, setting)은 후보에서 미리 빼므로 다시 뽑을 일이 없다. 후보는 그 모델의 보고된 test 예측 중 **금 답 문자열이 예측에 들어 있지 않은 쌍**이다(selected by string mismatch between gold and prediction, independent of any judge verdict). 판정 라벨은 선택에 쓰지 않는다.
  - 금 답 문자열: 공개 `answer`를 쓴다. v0.9.2에서 복수 정답이 된 23문항은 `data/v0.9.2/gold_fixes.json`의 `accept_any` 목록, 교체된 1문항(0568)은 `replace` 값을 쓴다. 복수 정답은 **어느 것도** 들어 있지 않을 때 불일치로 본다.
  - 정규화(양쪽 같음): Unicode NFKC → 소문자 → 모든 공백 제거. 그 밖의 정규화(쉼표, 단위, 괄호)는 하지 않는다. 형식 차이도 불일치로 잡히게 하려는 것이다.
  - 포함: 정규화한 금 답이 정규화한 예측의 부분 문자열이면 "들어 있다"로 본다.
  - 본 표본은 보조 층 사용 여부와 무관하게 동일하다(확인함).
- 주석자 파일은 `sample_id` 순서를 따로 섞고(`seed + 1`), 모델·설정·판정 라벨을 숨긴다(`annotator.csv`). 대응은 `key.csv`에 둔다.

## 4. 제외

- `--exclude-human80`: 1차 80건과 같은 (qa_id, model, setting)을 뺀다. 1차의 `rag`는 BM25로 대응시킨다.
- dry-run 기준으로 빠지는 것은 **2건**(gpt-5.4-mini BM25 1, gpt-5.4-mini FC 1)이다. 해당 셀의 모집단은 338, 76이 된다.

## 5. 라벨 절차

1. 비저자 주석자 2인이 `annotator.csv`로 각자 독립 라벨을 단다(correct / incorrect / unsure). AI 도구는 쓰지 않는다. 기준은 1차와 같다: gold 답과 근거에 비추어 예측이 정답인가.
   - 최종 답 규칙: 답변이 최종 답 하나를 분명히 제시하면 그 답으로 판정한다(다른 값을 함께 언급해도 무관). 여러 값을 늘어놓고 하나로 정하지 않으면 incorrect다. 최종 답을 제시했는지 자체를 판단할 수 없을 때만 unsure와 메모를 쓴다. 판정자 지시문(`scripts/llm_judge.py`)은 바꾸지 않는다.
2. 두 사람의 라벨이 같으면 그 라벨을 기준 라벨로 쓴다. 다르거나 한쪽이라도 unsure이면 저자가 조정한다. 저자는 조정 때만 모델·설정을 볼 수 있다.
3. 주석자 간 일치율과 Cohen κ(조정 전)를 보고한다.
4. 보상과 기간은 사용자 결정이다. 정해지는 대로 이 절에 적는다.

## 6. 보고 단위

- **전체(본 표본 200):** 주·보조 판정 각각 기준 라벨과의 일치율(Wilson 95%)과 Cohen κ를 낸다. 두 가지 값을 함께 낸다.
  - (a) 표본 그대로
  - (b) 사후층화: **셀(50) 단위**, 각 표본의 가중치 = 셀 모집단 n / 셀 표본 수 4. 한 설정 안에서는 모델별 모집단이 같으므로 설정(7) 가중과 같다(collapses to setting weights except for the two 77-item FC cells of gpt-5.4-mini and gpt-5.4-nano). 1차 80건 겹침으로 2셀의 모집단은 338, 76이다. 셀 모집단 합은 10,358이다(CB 2,736, BM25 2,711, dense 2,712, FC 741, k=50·open-region·oracle 각 486).
- **설정별(7, n = 24–32)·모델별(8, n = 16–28):** 일치율과 Wilson 구간만 낸다. κ는 내지 않는다.
- **가족별:** aggregation(본 표본 104)과 long_context_retrieval(56)만 따로 내고, 나머지(40)는 "other"로 합친다.
- **패널:** 네 패널 판정은 Anthropic 예측에만 있다. Anthropic 두 모델 × 7설정 × 4 = **56건**에서 여섯 판정(주, 보조, 패널 4) 각각의 기준 라벨 일치율을 따로 낸다.
- **보조 층(16, 사용 시):** 본 표본과 섞지 않고, 사후층화에도 넣지 않고 따로 보고한다. 주·보조 판정과 기준 라벨의 일치율(n = 16, Wilson)만 낸다.
- **오답 쪽:** 거의 전부 YES인 셀이 있다. dry-run 표본에서 4건이 모두 주 판정 YES인 셀은 15개다. 이런 셀은 판정자의 false negative에 대한 정보가 거의 없다. 판정자의 NO 쪽은 표본 전체의 주 판정 NO 84건으로 평가하고, 셀별 추정은 그 셀의 자연 비율에서의 일치율로 해석한다.
- 표본 목록(qa_id, model, setting, stratum), seed, 스크립트, 사람 라벨을 데이터셋 다음 릴리즈에 넣는다. 1차 80건과 겹쳐 뺀 2건도 적는다.

## 7. dry-run 수치 (2026-10-12, `--exclude-human80 --aux-string-mismatch`)

- 본 표본: 200건, 서로 다른 문항 139, 주 판정 YES 116 / NO 84.
- 설정별: CB 32, BM25 32, dense 32, FC 32, k=50 24, open-region 24, oracle 24.
- 가족별: aggregation 104, long_context 56, table_numeric 17, long_distance 11, answerability 8, schedule 2, eligibility 2.
- gold metric별: exact_numbers 104, contains_all 88, boolean_and_reason 8.
- 보조 층 후보(문자열 불일치 쌍, 본 표본 제외): 모델당 598–858, 합계 6,003. 가족별 후보는 aggregation 2,648, long_context 1,396, table_numeric 897, answerability 443, long_distance 274, eligibility 221, schedule 94, multi-doc 30.
- 보조 층 표본 16건: 설정 CB 7, BM25 4, dense 4, open-region 1. 가족 aggregation 7, long_distance 3, long_context 2, table_numeric 2, schedule 1, answerability 1.
- 참고(선택에 쓰지 않음): 후보 중 주 판정 YES는 1,250/6,003(21%)이고, 표본 16건 중 YES는 2건이다.

## 8. 미결 사항 (사용자 결정 전)

1. **보조 층의 정보량.** 문자열 불일치 쌍의 대부분(약 79%)은 주 판정이 NO인 오답이다. 그래서 무작위 16건 중 판정과 문자열이 갈리는 경우(주 판정 YES)는 기대값 약 3건이고, dry-run에서는 2건이다. 이 층은 "문자열은 틀렸다고 하는데 판정이 맞다고 한 경우"보다 "문자열 불일치 예측 전반에서 판정자의 정확도"를 잰다. 앞의 경우를 두텁게 보려면 판정 라벨을 써야 하는데, 이는 결정 (1)에 막혀 있다. 이 한계를 보고 때 그대로 적는다.
2. 주석자, 보상, 기간.
3. (해결됨, 추가 4) 사후층화는 셀 단위로 한다.

## 9. 생성 기록

- 생성일: 2026-10-12. 사용자가 투고 전 실행을 결정했고, 지도교수 세션의 지시로 `--write`를 실행했다.
- 명령(데이터셋 레포 루트, v0.9.6 HEAD 8ced8fe, 작업 트리 깨끗함): `python3 scripts/v097/sample_judge_validation.py --exclude-human80 --aux-string-mismatch --write <output directory>`
- 스크립트 sha256: `a2f90508565753abe7a192c55d75ed4c314b259771c2c6d1d5fa45dd266960d0`
- dry-run 뒤 스크립트에서 바뀐 것은 **출력 형식뿐**이고, 추출 규칙과 난수열은 그대로다. 출력된 표본은 §7의 dry-run 수치와 같다.
  - `gold_answer`를 v0.9.2 이후 채점에 쓰인 금 답(복수 정답 23문항은 ` ‖ `로 이은 목록, 0568은 교체 값)으로 표시한다.
  - `annotator.csv`의 열을 바꿨다.
  - `key.csv`에 stratum 열을 추가했다.

| 파일 | 레코드 | 열 | sha256 |
|---|---:|---|---|
| `sample.csv` | 216 (main 200 + aux_string_mismatch 16) | sample_id, stratum, qa_id, model, setting, task_type, question, gold_answer, gold_alternatives, gold_terms, metric, prediction, judge_label, judge_label_secondary, label_annotator_a, note_a, label_annotator_b, note_b, label_adjudicated | `887e127020f9a1a2dbb334c4b7591d4337c2709ff0c3798486135bdd2dcae303` |
| `annotator.csv` (UTF-8 BOM) | 216 | sample_id, question, gold_answer, prediction, label, memo | `2b61d7fcdf6949370cbda514736dc007659467047fdef471582ca72f9c22abc1` |
| `key.csv` | 216 | sample_id, stratum, qa_id, model, setting | `ef9d8b094bc32a7ff2b51375806afce45a4370fb9b4812d24d9ace9fd92c3b1b` |

- 레코드 수는 CSV 파서 기준이다. 예측에 줄바꿈이 있어 `wc -l`로는 415줄이 나온다.
- 점검 결과:
  - 세 파일의 sample_id 순서가 같다.
  - (qa_id, model, setting) 중복은 0이다.
  - 빈 예측은 0이다.
  - 예측 문자열에 모델·개발사 이름(claude, anthropic, gpt, openai, minimax, glm, sonnet, haiku)이 나오는 행은 0이다.
  - 복수 정답 표시 행은 12개다.
- 주석자에게는 `annotator.csv`와 `INSTRUCTIONS_ko.md`만 준다. `sample.csv`와 `key.csv`에는 모델, 설정, 판정이 있으므로 라벨 수집이 끝날 때까지 주석자에게 주지 않는다.
- 주석자 안내문의 판정 기준은 판정자 지시문(`scripts/llm_judge.py:31–34`: 핵심 사실 일치, 표현·형식 차이 무시, 실제 값이 있는데 답을 거부하면 오답)에 맞췄다. 여러 값을 늘어놓은 답은 §5의 최종 답 규칙을 따른다(engexpert 결정, 2026-10-12).
- 주석자 안내문 `INSTRUCTIONS_ko.md`(최종 답 규칙 반영본) sha256: `70c648c95f1084cc6d019706df03298aa0e85a3f860abaec018a3cc5daec0f66`. 라벨 수집 전 고정이다.
