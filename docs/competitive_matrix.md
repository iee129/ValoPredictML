# GitHub 경쟁 프로젝트 매트릭스

조사일: 2026-05-11
범위: GitHub 공개 repository 검색, 로컬 clone, 정적 분석
분석 방식: README, manifest, notebook, source, license 확인. 외부 repository 코드는 실행하지 않음

---

## 1. Evidence Summary

| 단계 | 결과 |
|---|---:|
| GitHub repository search HTML에서 추출한 distinct candidate | 94 |
| 로컬 clone 완료 | 60 |
| eligibility 필터 통과 | 57 |
| primary 분석 cap | 50 |
| empty clone | 2 |
| 분석 가능했지만 primary cap 밖 extra | 7 |
| 분석 근거 부족으로 제외 | 1 |

`gh auth status`에서 GitHub token invalid가 확인되어 authenticated search는 사용하지 않았다. Unauthenticated REST search는 rate limit에 도달했으므로, 최종 discovery는 GitHub repository search HTML 첫 페이지 링크를 사용했다. 따라서 이 문서는 GitHub 전체 총량을 주장하지 않고, 2026-05-11 기준으로 clone 및 정적 확인이 가능했던 후보군을 비교한다.

---

## 2. Reading Guide

| 표기 | 의미 |
|---|---|
| VLR/VCT | VLR.gg, VCT, pro match data, 또는 관련 scraper/API 근거 |
| 검증 | README/source에서 train/test split, cross-validation, 또는 metric 보고가 확인됨 |
| 누수 | leakage, chronological, temporal split, TimeSeriesSplit 등 시간/누수 방지 언급이 확인됨 |
| 박빙 | close-match를 별도 evaluation metric으로 분리한 근거 |
| 추천 | 추천/교체/counterfactual 성격의 keyword 또는 workflow 근거 |

정적 스캐너는 넓은 후보를 빠르게 분류하기 위한 도구다. UI/배포와 추천성 표기는 README/source keyword에 의존하므로, 최종 차별성 판단은 [`competitive_analysis.md`](competitive_analysis.md)의 대표 사례 해석을 우선한다.

---

## 3. Differentiation Scorecard

| 축 | ValoPredicML 현재 근거 | Primary 50개 관찰 |
|---|---|---|
| VLR/VCT 데이터 | 수집/검증 산출물과 UI 근거 패널은 있음. 학습 피처 계약 통합은 별도 단계 | 27/50이 VLR/VCT 또는 VLR.gg scraper/API 성격 |
| 활성 피처 계약 | `ml/data_pipeline.py` P1~P4 57개와 Streamlit feature builder가 같은 계약 사용 | 동일한 57-feature 계약을 문서화한 사례는 확인 안 됨 |
| 검증 | 현재 local report snapshot에 AUC/Acc/F1, close-match subset 포함 | 31/50에서 metric 또는 split 확인, 19/50은 미문서화 |
| 누수 방지 | `GroupKFold` + `match_key`의 `_swap` 제거 guard | 정적 스캐너 3개, 수동 확인 포함 최소 4개가 temporal/leakage를 언급. swap 증강쌍 guard는 확인 안 됨 |
| 박빙 평가 | margin 1~4 close-match subset 평가 구현 | 0/50. 한 프로젝트는 close-game feature/heuristic만 확인 |
| 사용자 insight | Streamlit Insight Pack, 유리/위험 요인, 추천 교체 Top 3 source 존재 | 추천/counterfactual keyword는 14/50이나, 예측 + UI + agent replacement를 ValoPredicML처럼 결합한 사례는 확인 안 됨 |

결론적으로 ValoPredicML의 방어 가능한 포지션은 "VLR/VCT 데이터를 쓴다"가 아니라 "경기 전 조합 예측, source-backed feature contract, match-level leakage guard, close-match evaluation, 그리고 사용자-facing replacement insight를 한 로컬 도구로 묶는다"이다.

---

## 4. Primary 50 Matrix

| Repo | 목표 | 데이터 | 모델/방식 | 검증 | UI/배포 | 갱신 | License |
|---|---|---|---|---|---|---|---|
| [jasonlow2307/valo-prediction](https://github.com/jasonlow2307/valo-prediction) | round/event analytics | CSV/dataset | RandomForest, NeuralNetwork, scraper/API | train/test split, metric reported | React/Next/Web, Discord/bot, CLI/notebook | 2024-12-27 | not found |
| [unnamed-catalyst/VCT-Match-Predictor](https://github.com/unnamed-catalyst/VCT-Match-Predictor) | match win/loss | web scraping, CSV/dataset | RandomForest, XGBoost, SVM, scraper/API | train/test split, metric reported | React/Next/Web, Discord/bot, CLI/notebook, packaged app | 2025-05-19 | LICENSE |
| [ianjure/valorant-match-prediction](https://github.com/ianjure/valorant-match-prediction) | round/event analytics | Kaggle, Riot/API, CSV/dataset | unclear/no model | metric reported | React/Next/Web, Discord/bot, CLI/notebook | 2024-08-27 | not found |
| [neilsorkin19/ValLoadoutToWin](https://github.com/neilsorkin19/ValLoadoutToWin) | round/event analytics | CSV/dataset | NeuralNetwork | metric reported | React/Next/Web, Discord/bot, CLI/notebook | 2022-05-15 | not found |
| [MitsuSDK/ML_Valorant](https://github.com/MitsuSDK/ML_Valorant) | analytics/dashboard | CSV/dataset | RandomForest, LogisticRegression, Regression | cross-validation, train/test split, metric reported, leakage/time control mentioned | React/Next/Web, Discord/bot | 2026-03-24 | not found |
| [axsddlr/vlrggapi](https://github.com/axsddlr/vlrggapi) | data/API collection | VLR.gg, web scraping | NeuralNetwork, scraper/API | not documented | Flask/FastAPI, React/Next/Web, Discord/bot, CLI/notebook | 2026-05-08 | LICENSE |
| [Juniorffonseca/valorant-predictor](https://github.com/Juniorffonseca/valorant-predictor) | round/event analytics | VLR.gg, CSV/dataset | NeuralNetwork, BERT/embedding, scraper/API | metric reported | React/Next/Web, Discord/bot | 2023-07-27 | LICENSE |
| [lucaspellegrinelli/valorant-agent-embeddings](https://github.com/lucaspellegrinelli/valorant-agent-embeddings) | data/API collection | VLR.gg, web scraping, CSV/dataset | NeuralNetwork, BERT/embedding, scraper/API | train/test split, metric reported | React/Next/Web | 2022-10-15 | not found |
| [DEF4LT-303/Valorant-Pro-Match-Analysis](https://github.com/DEF4LT-303/Valorant-Pro-Match-Analysis) | analytics/dashboard | Kaggle, CSV/dataset | RandomForest, LogisticRegression, DecisionTree, Regression | train/test split, metric reported | React/Next/Web, Discord/bot, CLI/notebook | 2023-05-07 | not found |
| [kleinaitis/valorant-match-predictor](https://github.com/kleinaitis/valorant-match-predictor) | data/API collection | Tracker.gg, web scraping, CSV/dataset | LogisticRegression, Regression, scraper/API | train/test split, metric reported | React/Next/Web, Discord/bot, CLI/notebook, packaged app | 2023-09-10 | not found |
| [chechna9/valorant_win_prediction_UI](https://github.com/chechna9/valorant_win_prediction_UI) | analytics/dashboard | Kaggle, CSV/dataset | scraper/API | not documented | Flask/FastAPI, React/Next/Web, Discord/bot, CLI/notebook | 2023-09-10 | not found |
| [chechna9/valorant_win_prediction_server](https://github.com/chechna9/valorant_win_prediction_server) | data/API collection | CSV/dataset | LogisticRegression, Regression, scraper/API | cross-validation | Flask/FastAPI | 2023-06-05 | not found |
| [Parham635/ValorantPrediction](https://github.com/Parham635/ValorantPrediction) | data/API collection | Riot/API | scraper/API | not documented | Discord/bot | 2024-03-02 | LICENSE |
| [Acrylus/ValorantRankPrediction](https://github.com/Acrylus/ValorantRankPrediction) | round/event analytics | CSV/dataset | Regression | train/test split, metric reported | React/Next/Web | 2024-03-18 | not found |
| [ghpanda/ValorantMatchPredictor](https://github.com/ghpanda/ValorantMatchPredictor) | data/API collection | VLR.gg, web scraping | NeuralNetwork, scraper/API | metric reported | Flask/FastAPI, React/Next/Web, Discord/bot, packaged app | 2025-09-23 | not found |
| [Jonathan-Data/VCT-Match-Predictor](https://github.com/Jonathan-Data/VCT-Match-Predictor) | analytics/dashboard | VLR.gg, Kaggle, web scraping, CSV/dataset | RandomForest, XGBoost, LogisticRegression, NeuralNetwork, SVM, Regression, heuristic/dashboard, scraper/API | cross-validation, train/test split, metric reported, leakage/time control mentioned | Flask/FastAPI, React/Next/Web, Discord/bot, PowerBI/dashboard, CLI/notebook, packaged app | 2026-05-08 | not found |
| [jonathanwang9316/VCT-Match-Predictor](https://github.com/jonathanwang9316/VCT-Match-Predictor) | match win/loss | unclear | unclear/no model | not documented | none/unclear | 2025-06-05 | LICENSE |
| [terrdv/VCT-Match-Predictor](https://github.com/terrdv/VCT-Match-Predictor) | data/API collection | web scraping, CSV/dataset | RandomForest, LogisticRegression, NeuralNetwork, Regression, scraper/API | train/test split, metric reported | Flask/FastAPI, React/Next/Web, Discord/bot, CLI/notebook | 2026-02-10 | not found |
| [donacianojesus/VCTMatchPredictor](https://github.com/donacianojesus/VCTMatchPredictor) | analytics/dashboard | VLR.gg, web scraping, CSV/dataset | RandomForest, NeuralNetwork, heuristic/dashboard, scraper/API | metric reported | Flask/FastAPI, React/Next/Web, Discord/bot, PowerBI/dashboard, CLI/notebook, packaged app | 2025-10-30 | not found |
| [EthanSB-dev/VCT2026_Match_Predictor](https://github.com/EthanSB-dev/VCT2026_Match_Predictor) | round/event analytics | Kaggle, CSV/dataset | NeuralNetwork | not documented | Discord/bot | 2026-04-30 | not found |
| [AndyWarrior123/Valorant-Esports-Prediction-using-Machine-Learning](https://github.com/AndyWarrior123/Valorant-Esports-Prediction-using-Machine-Learning) | rank/rating | VLR.gg, Riot/API, web scraping, CSV/dataset | RandomForest, XGBoost, LogisticRegression, NeuralNetwork, SVM, Regression, scraper/API | train/test split, metric reported | React/Next/Web, Discord/bot, CLI/notebook | 2023-11-29 | not found |
| [chnabi/VCT-Americas-24-ML-Predictions](https://github.com/chnabi/VCT-Americas-24-ML-Predictions) | round/event analytics | VLR.gg, web scraping, CSV/dataset | RandomForest, SVM, scraper/API | metric reported | React/Next/Web, Discord/bot, CLI/notebook | 2024-09-06 | not found |
| [wyndollin/Valorant-pro-match-predictor](https://github.com/wyndollin/Valorant-pro-match-predictor) | unclear | Riot/API, CSV/dataset | RandomForest, LogisticRegression, DecisionTree, Regression | cross-validation, train/test split, metric reported | React/Next/Web, CLI/notebook | 2025-06-21 | not found |
| [skittles9823/ValorantPredictionsBot](https://github.com/skittles9823/ValorantPredictionsBot) | data/API collection | unclear | scraper/API | not documented | Discord/bot, CLI/notebook | 2022-09-02 | LICENSE |
| [Dr-Zero69/Valorant-Win-Rate-Prediction](https://github.com/Dr-Zero69/Valorant-Win-Rate-Prediction) | data/API collection | web scraping, CSV/dataset | LogisticRegression, Regression, scraper/API | cross-validation, train/test split, metric reported, leakage/time control mentioned | React/Next/Web, Discord/bot, CLI/notebook | 2025-08-20 | not found |
| [absolutePi/valorant_winrate_prediction](https://github.com/absolutePi/valorant_winrate_prediction) | rank/rating | VLR.gg, web scraping, CSV/dataset | LogisticRegression, Regression, scraper/API | train/test split, metric reported | React/Next/Web, Discord/bot, packaged app | 2024-07-09 | not found |
| [manuellrds/Valorant-WinRateComps](https://github.com/manuellrds/Valorant-WinRateComps) | round/event analytics | unclear | BERT/embedding | not documented | React/Next/Web | 2025-05-21 | not found |
| [marcowong3/valorant-esports-winrate-analysis](https://github.com/marcowong3/valorant-esports-winrate-analysis) | analytics/dashboard | Kaggle, CSV/dataset | RandomForest, XGBoost, NeuralNetwork, Regression, heuristic/dashboard | train/test split, metric reported | React/Next/Web, PowerBI/dashboard | 2023-08-15 | not found |
| [piravelha/valorant_agent_comp_winrate](https://github.com/piravelha/valorant_agent_comp_winrate) | round/event analytics | unclear | NeuralNetwork | not documented | none/unclear | 2023-12-07 | not found |
| [MociW/valorant-match-outcome-prediction](https://github.com/MociW/valorant-match-outcome-prediction) | match win/loss | VLR.gg, Riot/API, web scraping, CSV/dataset | XGBoost, LightGBM, LogisticRegression, SVM, Regression, scraper/API | cross-validation, train/test split, metric reported | React/Next/Web, Discord/bot, CLI/notebook | 2025-09-07 | not found |
| [harker-tech/Valorant-Machine-Learning](https://github.com/harker-tech/Valorant-Machine-Learning) | match win/loss | web scraping, CSV/dataset | RandomForest, XGBoost, LightGBM, LogisticRegression, NeuralNetwork, SVM, Regression, heuristic/dashboard, scraper/API | cross-validation, train/test split, metric reported, leakage/time control mentioned | React/Next/Web, Discord/bot, PowerBI/dashboard | 2025-06-16 | LICENSE |
| [Nazacodes/Valorant-Machine-Learning](https://github.com/Nazacodes/Valorant-Machine-Learning) | rank/rating | CSV/dataset | unclear/no model | not documented | React/Next/Web, Discord/bot, CLI/notebook | 2024-03-04 | not found |
| [Nsujatno/valorant-machine-learning](https://github.com/Nsujatno/valorant-machine-learning) | round/event analytics | CSV/dataset | RandomForest, LogisticRegression, Regression | train/test split, metric reported | none/unclear | 2025-11-02 | not found |
| [KamiiJisoo/Valorant-Predictor](https://github.com/KamiiJisoo/Valorant-Predictor) | match win/loss | VLR.gg, web scraping, CSV/dataset | LogisticRegression, Regression | train/test split | React/Next/Web | 2025-02-24 | not found |
| [axs-14/valorant-predictor](https://github.com/axs-14/valorant-predictor) | analytics/dashboard | Kaggle, CSV/dataset | RandomForest, LogisticRegression, Regression, heuristic/dashboard | cross-validation, metric reported, leakage/time control mentioned | Discord/bot, PowerBI/dashboard, CLI/notebook | 2026-03-30 | not found |
| [gupta-v/valorant-performance-predictor](https://github.com/gupta-v/valorant-performance-predictor) | analytics/dashboard | CSV/dataset | Regression, scraper/API | cross-validation, train/test split, metric reported | Streamlit, Discord/bot, CLI/notebook | 2024-12-21 | LICENSE |
| [Aesenaliev/ValorantAnalytics](https://github.com/Aesenaliev/ValorantAnalytics) | analytics/dashboard | unclear | heuristic/dashboard | not documented | PowerBI/dashboard | 2024-07-03 | not found |
| [d4nilloval-dotcom/ValorantAnalytics](https://github.com/d4nilloval-dotcom/ValorantAnalytics) | analytics/dashboard | Riot/API, web scraping, CSV/dataset | heuristic/dashboard, scraper/API | metric reported, leakage/time control mentioned | React/Next/Web, Discord/bot, PowerBI/dashboard, CLI/notebook, packaged app | 2026-04-05 | not found |
| [jlirms/valorant-analytics](https://github.com/jlirms/valorant-analytics) | analytics/dashboard | CSV/dataset | XGBoost, NeuralNetwork, BERT/embedding, scraper/API | cross-validation, train/test split, metric reported | React/Next/Web, Discord/bot, CLI/notebook | 2022-03-01 | LICENSE |
| [varvind830/ValorantAnalytics](https://github.com/varvind830/ValorantAnalytics) | analytics/dashboard | unclear | unclear/no model | not documented | none/unclear | 2024-04-04 | not found |
| [khfong26/Valorant-Agent-Analysis](https://github.com/khfong26/Valorant-Agent-Analysis) | analytics/dashboard | VLR.gg, web scraping, CSV/dataset | scraper/API | not documented | React/Next/Web, Discord/bot, CLI/notebook | 2025-08-19 | not found |
| [guardiantria33/Valorant_META_Analysis](https://github.com/guardiantria33/Valorant_META_Analysis) | analytics/dashboard | Kaggle, Riot/API, CSV/dataset | BERT/embedding, scraper/API | not documented | React/Next/Web | 2023-12-11 | not found |
| [sanskarkosare/Valorant-VCT-VISION-Project](https://github.com/sanskarkosare/Valorant-VCT-VISION-Project) | data/API collection | VLR.gg, web scraping | XGBoost, scraper/API | not documented | Streamlit, React/Next/Web, packaged app | 2026-04-05 | not found |
| [Haxodrat/valesportsmodel](https://github.com/Haxodrat/valesportsmodel) | analytics/dashboard | VLR.gg, web scraping, CSV/dataset | LightGBM, NeuralNetwork, BERT/embedding, heuristic/dashboard, scraper/API | train/test split, metric reported | Flask/FastAPI, React/Next/Web, Discord/bot, PowerBI/dashboard, CLI/notebook | 2026-04-08 | not found |
| [lcemerald11/valSportAI](https://github.com/lcemerald11/valSportAI) | rank/rating | VLR.gg, web scraping | scraper/API | not documented | React/Next/Web | 2025-10-29 | not found |
| [Ominousx/valorant-comp-dashboard](https://github.com/Ominousx/valorant-comp-dashboard) | analytics/dashboard | CSV/dataset | heuristic/dashboard, scraper/API | not documented | Streamlit, React/Next/Web, Discord/bot, PowerBI/dashboard, CLI/notebook | 2026-04-30 | not found |
| [aritropaul/vlr.gg-scraper](https://github.com/aritropaul/vlr.gg-scraper) | data/API collection | VLR.gg, web scraping | scraper/API | not documented | Flask/FastAPI, React/Next/Web, Discord/bot | 2021-07-06 | not found |
| [wyndollin/vlr.gg-scraper](https://github.com/wyndollin/vlr.gg-scraper) | data/API collection | VLR.gg, web scraping, CSV/dataset | scraper/API | not documented | React/Next/Web, Discord/bot, CLI/notebook | 2025-07-20 | not found |
| [FlynV/vlr-map-veto-scraper](https://github.com/FlynV/vlr-map-veto-scraper) | data/API collection | VLR.gg, web scraping, CSV/dataset | scraper/API | not documented | React/Next/Web, CLI/notebook | 2023-06-20 | LICENSE |
| [MateusVega/vlrgg-stats-scraper](https://github.com/MateusVega/vlrgg-stats-scraper) | analytics/dashboard | VLR.gg, web scraping | scraper/API | metric reported | React/Next/Web, Discord/bot, CLI/notebook | 2026-01-03 | LICENSE |

---

## 5. Extra And Excluded Repositories

이 표는 clone까지는 되었지만 primary 50 cap 밖에 있거나, 분석 근거가 부족해 제외한 repository다.

| Repo | 처리 | Eligible | 관찰 목표 |
|---|---|---:|---|
| [KhalilSayah/ValorantPrediction](https://github.com/KhalilSayah/ValorantPrediction) | empty clone | false | unclear |
| [rydohaines/Valorant-Match-Prediction](https://github.com/rydohaines/Valorant-Match-Prediction) | empty clone | false | unclear |
| [liulalemx/vlrgg-api](https://github.com/liulalemx/vlrgg-api) | eligible extra beyond primary cap | true | data/API collection |
| [QaysBadri/Valorant-Web-Scraper](https://github.com/QaysBadri/Valorant-Web-Scraper) | eligible extra beyond primary cap | true | data/API collection |
| [Dilka30003/tracker.gg-Valorant-Scraper](https://github.com/Dilka30003/tracker.gg-Valorant-Scraper) | eligible extra beyond primary cap | true | data/API collection |
| [J0BS013/Valorant-Tracker-Web-Scraper](https://github.com/J0BS013/Valorant-Tracker-Web-Scraper) | eligible extra beyond primary cap | true | data/API collection |
| [techchrism/valorant-log-endpoint-scraper](https://github.com/techchrism/valorant-log-endpoint-scraper) | eligible extra beyond primary cap | true | data/API collection |
| [deep-codr/valorant-tracker-app](https://github.com/deep-codr/valorant-tracker-app) | eligible extra beyond primary cap | true | data/API collection |
| [McDaived/Valinfo](https://github.com/McDaived/Valinfo) | eligible extra beyond primary cap | true | data/API collection |
| [Belloto-souza/Valorant-match-tracker](https://github.com/Belloto-souza/Valorant-match-tracker) | insufficient Valorant prediction/analytics evidence | false | rank/rating |

---

## 6. Method Limits

- Search breadth is practical rather than exhaustive: GitHub HTML search first-page results were used after REST rate limiting.
- Third-party code was not executed, so runtime claims from competitor repositories are treated as self-reported unless source structure directly supported them.
- Static keyword classification can over-detect UI/deployment and recommendation signals when a README mentions related terms. Differentiation claims therefore rely on repeated evidence across README/source/notebook, not one keyword hit.
- Reported performance across repositories is not ranked because targets, splits, seasons, and datasets differ.
