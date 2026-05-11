# ValoPredicML 경쟁 프로젝트 분석

조사일: 2026-05-11
범위: GitHub 공개 repository 검색 및 로컬 clone 기반 정적 분석
분석 대상: 검색 후보 94개 중 clone 60개, eligibility 필터 후 primary 50개
실행 원칙: 외부 repository 코드는 실행하지 않고 README, manifest, notebook, source, license만 확인

---

## 1. 결론 요약

이번 조사는 기존 8개 프로젝트 스냅샷을 50개 GitHub 경쟁/인접 프로젝트로 확장했다. 결과적으로 ValoPredicML의 차별성은 "Valorant 데이터를 쓴다" 또는 "ML로 승률을 예측한다"가 아니다. 이 두 영역은 이미 다수 프로젝트가 시도했다.

현재 코드와 로컬 리포트 기준으로 방어 가능한 차별점은 다음이다.

| 축 | ValoPredicML 현재 상태 | 50개 GitHub 조사 결과 |
|---|---|---|
| 경기 전 팀 구성 기반 예측 | 구현됨. 양 팀 요원, 맵, 선수 통계, 요원-맵 통계, 팀 폼을 입력 피처로 사용 | 일부 match predictor가 있지만 라운드 화면, VLR scraping, 단일 notebook, rank/earnings 예측으로 흩어짐 |
| 피처 계약 | active feature 57개. `FEATURE_COLS_P1~P4`와 Streamlit feature builder가 같은 계약을 사용 | 단일 프로젝트에서 역할군 + 선수 폼 + 요원-맵 + 팀 폼을 함께 갖춘 사례는 확인하지 못함 |
| 누수 방지 | `GroupKFold`와 `match_key`의 `_swap` 제거로 경기 단위/증강쌍 누수 방지 | 일부 프로젝트가 temporal split/leakage를 언급하지만, swap 증강쌍 누수 방지까지 명시한 사례는 확인하지 못함 |
| 박빙 경기 평가 | margin 1~4 close-match subset 평가가 구현됨 | 별도 close-match evaluation metric을 문서화한 프로젝트는 확인하지 못함. 한 프로젝트는 close-game feature/heuristic만 보유 |
| UI/사용자 가치 | Streamlit 예측 화면, Insight Pack, 추천 교체 Top 3, VLR 근거 패널이 source tree에 존재 | UI는 일부 있으나, 승률 + 원인 + 교체 실험을 한 화면에서 묶은 사례는 확인하지 못함 |
| VLR/VCT 데이터 | 수집/검증 산출물은 연구 검증 및 UI 근거 패널 용도. 학습 피처 계약 변경은 별도 단계 | 50개 중 상당수가 VLR/VCT scraping/API를 사용. 이 자체는 더 이상 유일한 차별점이 아님 |

핵심 메시지:

> ValoPredicML은 단순 "Valorant 승률 예측기"가 아니라, 경기 전 요원 조합을 중심으로 선수/맵/팀 맥락을 결합하고, 경기 단위 누수 방지와 박빙 subset 평가를 갖춘 로컬 Streamlit 분석 도구다.

---

## 2. 조사 방법

### 2.1 검색 키워드

영어 키워드:

`valorant prediction`, `valorant predict`, `valorant winrate`, `valorant win rate`, `valorant match prediction`, `valorant match predictor`, `valorant machine learning`, `valorant analytics`, `valorant esports prediction`, `vct match predictor`, `vlrgg`, `valorant scraper`, `topic:valorant prediction`, `topic:valorant machine-learning`

한국어 키워드:

`발로란트 예측`, `발로란트 승률`, `발로란트 승률 예측`, `발로란트 경기 예측`, `발로란트 매치 예측`, `발로란트 머신러닝`, `발로란트 분석`

### 2.2 GitHub API 제약

`gh auth status`는 `github.com` 토큰 invalid 상태를 보고했다. 따라서 authenticated `gh search`는 사용하지 않았다.

GitHub REST repository search는 unauthenticated 상태에서 사용했으나, 첫 negative-query 배치가 0건으로 반환됐고 단순 probe에서 rate limit에 도달했다. 이후 discovery는 GitHub repository search HTML의 첫 페이지 링크를 사용했다. 이 방식은 정밀한 total count 산출에는 약하므로, 문서에는 "검색 후보 수"와 "clone/analyze 수"를 중심으로 기록한다.

### 2.3 필터 규칙

포함:

- Valorant, VCT, VLR.gg, Tracker.gg 관련 prediction, analytics, ML, dashboard, scraper/API repository
- README/source/notebook/manifest 중 하나 이상으로 분석 가능한 repository
- 기존 scout 후보 6개를 강제 spot-check: `jasonlow2307/valo-prediction`, `unnamed-catalyst/VCT-Match-Predictor`, `ianjure/valorant-match-prediction`, `neilsorkin19/ValLoadoutToWin`, `MitsuSDK/ML_Valorant`, `axsddlr/vlrggapi`

제외:

- empty clone
- cheat/aimbot/wallhack 계열
- awesome list/API catalog처럼 자체 분석/모델/수집 구현이 없는 목록성 repository
- Valorant 관련성이 약하거나 분석 가능한 source/docs가 부족한 repository

---

## 3. ValoPredicML 현재 기준선

이 절은 현재 source tree와 로컬 generated report snapshot을 분리해 읽어야 한다. Generated report는 재생성 시 바뀔 수 있으므로, 구현 상태의 source-of-truth는 코드다.

| 항목 | 현재 근거 |
|---|---|
| 활성 피처 계약 | `ml/data_pipeline.py`의 `FEATURE_COLS_P1~P4` 57개, `app/feature_builder.py`가 `FEATURE_COLS`를 사용 |
| 데이터 규모 snapshot | `reports/preprocess_summary.json`: clean 66,711행, active feature 57개 |
| 최종 test snapshot | `reports/eval_summary.json`: ensemble AUC 0.9336, Acc 0.8543, F1 0.8513 |
| 박빙 snapshot | margin=2 subset 1,962건, ensemble AUC 0.7372 |
| 누수 방지 | `ml/evaluate_model.py`가 `GroupKFold` groups를 `match_key`에서 `_swap` 제거 후 구성 |
| 로컬 앱 | `app/streamlit_app.py`, `app/views/predict.py`, `app/views/research_validation.py` 등 Streamlit source 존재 |
| Insight Pack | `app/views/predict.py`에 승률, 유리/위험 요인, 추천 교체 Top 3, VLR 근거 패널 존재 |

현재 문서화에서 피해야 할 표현:

- "VLR/VCT 23시즌이 학습 피처에 통합됐다"는 현재 구현 주장으로 쓰면 안 된다.
- "FastAPI/Next.js/PostgreSQL/Vercel 배포 완료"는 현재 실행 기준이 아니다.
- "추천 시스템이 완성 제품 수준으로 검증됐다"는 현재 근거보다 강하다. 지금은 source-backed Streamlit replacement experiment로 표현한다.

---

## 4. 경쟁 프로젝트 지형

50개 primary set은 크게 5개 부류로 나뉜다.

| 부류 | 대표 프로젝트 | 관찰 |
|---|---|---|
| 실시간/라운드 화면 예측 | `jasonlow2307/valo-prediction`, `neilsorkin19/ValLoadoutToWin` | 라운드 중 이미지/상태 기반. ValoPredicML의 경기 전 팀 구성 예측과 목표가 다름 |
| VCT/VLR match predictor | `unnamed-catalyst/VCT-Match-Predictor`, `Jonathan-Data/VCT-Match-Predictor`, `MociW/valorant-match-outcome-prediction`, `harker-tech/Valorant-Machine-Learning` | VLR/VCT data와 ML 모델 사용. 일부는 cross-validation/temporal split을 언급 |
| Scraper/API | `axsddlr/vlrggapi`, `aritropaul/vlr.gg-scraper`, `wyndollin/vlr.gg-scraper`, `FlynV/vlr-map-veto-scraper` | 데이터 수집 도구 성격. 예측/검증/사용자 insight는 별도 |
| Composition/winrate analysis | `manuellrds/Valorant-WinRateComps`, `piravelha/valorant_agent_comp_winrate`, `khfong26/Valorant-Agent-Analysis` | 요원/조합 분석은 있으나 누수 방지, close-match metric, 예측 UI까지 결합되지는 않음 |
| Dashboard/analytics | `Aesenaliev/ValorantAnalytics`, `d4nilloval-dotcom/ValorantAnalytics`, `Ominousx/valorant-comp-dashboard`, `Haxodrat/valesportsmodel` | 시각화/조회 가치가 있으나 모델 검증과 counterfactual 설명은 제한적 |

중요한 변화:

- VLR/VCT scraping은 더 이상 희소하지 않다. GitHub에는 VLR.gg scraper/API와 VCT match predictor가 다수 있다.
- "accuracy reported"는 흔하지만, 검증 설계가 재현 가능하거나 누수 방지를 명시한 프로젝트는 소수다.
- close-match를 독립 metric으로 분리한 사례는 이번 50개 조사에서 확인하지 못했다.
- agent replacement/counterfactual recommendation을 예측 UI에 직접 묶은 사례도 확인하지 못했다. 일부 프로젝트는 loadout/agent/winrate 분석에 가깝다.

---

## 5. 주요 프로젝트 비교

전체 50개 표는 [`competitive_matrix.md`](competitive_matrix.md)에 둔다. 여기서는 차별성 판단에 영향을 주는 대표 사례만 요약한다.

| 프로젝트 | 성격 | 강점 | ValoPredicML 대비 차이 |
|---|---|---|---|
| [jasonlow2307/valo-prediction](https://github.com/jasonlow2307/valo-prediction) | 실시간 screenshot 기반 라운드/매치 win-rate | Random Forest, CNN/NN artifact, live visualization, README 기준 95% accuracy 주장 | 경기 중 화면 상태 예측. 경기 전 요원 조합 입력, match-key GroupKFold, close-match subset 평가와는 목표가 다름 |
| [unnamed-catalyst/VCT-Match-Predictor](https://github.com/unnamed-catalyst/VCT-Match-Predictor) | VCT match predictor | VLR scraping, RF/XGBoost/SVM, train/test metric | Americas Stage 1 2025 중심. 추천 UI와 close-match metric은 확인 안 됨 |
| [MitsuSDK/ML_Valorant](https://github.com/MitsuSDK/ML_Valorant) | ML/analytics | README에서 chronological split, no leakage를 명시 | 누수 방지 의식은 강점. 다만 ValoPredicML의 swap-pair GroupKFold와 Insight Pack은 별도 차별점 |
| [Jonathan-Data/VCT-Match-Predictor](https://github.com/Jonathan-Data/VCT-Match-Predictor) | VCT dashboard + model | VLR/Kaggle, 여러 모델, temporal evaluation 코드 | 가장 가까운 경쟁군 중 하나. 단, close-match 분리 평가와 교체 추천 UI는 확인 안 됨 |
| [MociW/valorant-match-outcome-prediction](https://github.com/MociW/valorant-match-outcome-prediction) | match outcome ML | XGBoost/LightGBM/SVM 등 모델 폭이 넓음 | 모델 후보는 강하지만, 사용자-facing insight/replacement workflow는 확인 안 됨 |
| [harker-tech/Valorant-Machine-Learning](https://github.com/harker-tech/Valorant-Machine-Learning) | match prediction + dashboard/API 성격 | temporal split/leakage 방지와 close-game feature를 언급 | close-game feature는 있으나 ValoPredicML처럼 close-match subset 평가 metric으로 분리한 증거는 없음 |
| [axsddlr/vlrggapi](https://github.com/axsddlr/vlrggapi) | VLR.gg 비공식 API/scraper | VLR.gg 데이터 접근성 | 경쟁 모델이 아니라 source expansion 후보. ValoPredicML의 차별성 증거에는 데이터 수집 기반으로만 기여 |
| [neilsorkin19/ValLoadoutToWin](https://github.com/neilsorkin19/ValLoadoutToWin) | loadout/round win probability | round-level loadout modeling | agent replacement recommendation과 유사한 문제의식이 있지만, Valorant 팀 조합/맵/선수 폼 기반 pre-match 앱은 아님 |

---

## 6. 정량 요약

Primary 50개 기준 정적 분석 결과:

| 항목 | 관찰 |
|---|---:|
| VLR/VCT 관련 repository | 27/50 |
| validation metric 또는 split 확인 | 31/50 |
| validation 미문서화 | 19/50 |
| leakage/temporal control 명시 | 정적 스캐너 3개, 수동 확인 포함 최소 4개 |
| close-match 별도 evaluation metric | 0/50 |
| ValoPredicML과 같은 swap-pair GroupKFold guard | 0/50 |
| 예측 + UI + 교체 실험을 한 화면에 결합 | 0/50 확인 |

해석:

- ValoPredicML은 VLR/VCT 데이터 사용 자체로는 독점적이지 않다.
- 경쟁력은 데이터 수집보다 "검증 가능한 모델 계약 + 누수 방지 + 박빙 평가 + 사용자-facing insight"의 결합에서 나온다.
- 따라서 발표/README/논문 문구는 "유일한 Valorant 예측기"가 아니라 "조합-중심 pre-match 예측과 close-match/누수 검증을 결합한 도구"로 좁혀야 한다.

---

## 7. 포지셔닝 문구

권장 문구:

> ValoPredicML은 Valorant 프로 경기의 팀 구성 선택 단계에서 사용할 수 있는 로컬 Streamlit 승률 분석 도구다. 57개 활성 피처는 요원 역할, 선수 폼, 요원-맵 통계, 팀 폼을 결합하며, 평가 단계에서는 경기 단위 GroupKFold와 swap 증강쌍 누수 방지를 적용한다. GitHub 50개 경쟁/인접 프로젝트 조사에서 VLR/VCT scraping과 일반 match prediction은 흔했지만, 별도 close-match 평가와 agent replacement insight를 함께 제공하는 사례는 확인하지 못했다.

피해야 할 문구:

- "VLR.gg를 사용하므로 유일하다"
- "경쟁 프로젝트에는 ML이 없다"
- "추천 시스템 완성"
- "모든 경쟁 프로젝트보다 성능이 높다"

성능 비교 주의:

경쟁 프로젝트는 예측 target, split, 데이터 기간, 재현성이 서로 다르다. 따라서 reported accuracy를 단순 순위화하지 않는다. ValoPredicML의 AUC/Acc는 내부 snapshot으로 제시하고, 경쟁 프로젝트 성능은 "보고 여부와 검증 설계" 중심으로 비교한다.
