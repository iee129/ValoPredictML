# 04. 로드맵, 팀 구성, 용어 사전

마지막 업데이트: 2026-05-27

## 1. 단계별 로드맵

```
Phase 0 ✅  환경 설정 (venv, Kaggle 인증)
Phase 1 ✅  데이터 수집 (Kaggle 3개 활성 데이터셋)
Phase 2 ✅  데이터 전처리 (src/features/preprocess.py)
Phase 3 ✅  피처 엔지니어링 (슬롯 기반 421피처, LEAK-SAFE 시간순 누적 평균)
Phase 4 ✅  Baseline 모델 학습·평가 (LR + DT Soft Voting, 랜덤 80/20, Test AUC=0.5943)
Phase 5a →  심화 모델 학습 (RF + XGBoost + LightGBM 시간순 split)       — 5/29~5/31
Phase 5b →  VLR.gg 통합 + 심화 모델 재학습                              — 6/2~6/3
Phase 5c →  10개 사용자 차별점 모듈 + 웹 스택 통합 (src/api + web)      — 5/29~6/7
Phase 6  →  통합 테스트 + 시연 영상 + 기말 발표                          — 6/7~6/9
```

### 단계별 완료 기준

| Phase | 완료 기준 |
|-------|-----------|
| Phase 0 | `.venv` 활성화, `python -m data.dataload` 정상 실행 |
| Phase 1 | `data/raw/kaggle/`에 활성 데이터셋 3종 다운로드 완료 |
| Phase 2 | ✅ `data/processed/matches.csv` 생성, 품질 검사 통과 |
| Phase 3 | ✅ 421피처 생성, `train.csv / test.csv` 랜덤 80/20 분할 |
| Phase 4 | ✅ Baseline Test AUC=0.5943 (LR + DT Soft Voting, 랜덤 80/20) |
| Phase 5a | RF/XGB/LGBM 세 모델 (고정 파라미터) 학습 완료, `models/advanced/{rf,xgb,lgbm}.joblib` |
| Phase 5b | VLR.gg 통합 데이터로 시간순 심화 모델 재학습, `models/advanced/` |
| Phase 5c | 10개 차별점 모듈 + 웹 스택 통합 (FastAPI `src/api` + Next.js `web`) 정상 동작, 단위 테스트 10개 통과 |
| Phase 6  | 통합 테스트 통과, 시연 영상 3개 (정상/박빙/out-of-pool), 발표 자료 완성 |

### 1.1 일별 일정 (2026-05-28 ~ 2026-06-09)

전체 구현 계획 원본: `.omc/plans/user_facing_differentiators_plan.md` — 채택된 차별점 10개의 파일·알고리즘·acceptance 명세 포함.

| 날짜 | 작업 |
|------|------|
| 5/28 (목) | 중간 발표 |
| 5/29 (금) | 차별점 I (카운터 픽 경고) + G (위험 알림) 모듈 구현 |
| 5/30 (토) | 차별점 N (요원-맵 적합도) + K (맵별 이상 구성) + J (Ult Cycle Balance) |
| 5/31 (일) | Phase 5a — 심화 모델 학습 (RF + XGBoost + LightGBM 시간순 split) |
| 6/01 (월) | 차별점 B (박빙 검증, Brier+ECE) + C (자연어 설명 골격) |
| 6/02 (화) | VLR.gg 스크래핑 완료 확인 + 통합 데이터 정합성 검증 |
| 6/03 (수) | 차별점 D (선수 Agent Pool) + Phase 5b VLR.gg 통합 모델 재학습 |
| 6/04 (목) | 차별점 E (사이드별 ATK/DEF 패널) |
| 6/05 (금) | 차별점 A (What-if 시뮬레이션) |
| 6/06 (토) | 차별점 C (자연어 설명) feature_importances 기반 근거 + 한국어 도메인 비유 완성 |
| 6/07 (일) | Phase 5c 통합 — 웹 스택(`src/api` + `web`) 단일 진입점 + 통합 테스트 + 시연 영상 1차 |
| 6/08 (월) | 최종 리허설 + 발표 자료 보강 + 백업 시연 영상 |
| 6/09 (화) | 기말 발표 |

---

## 2. 팀 구성 및 역할

| 팀원 | 역할 | 담당 영역 |
|------|------|-----------|
| 이연주 | 프로젝트 리드 | 전체 구조 설계, Git/GitHub 버전 관리, 문서화 |
| 이예인 | ML 엔지니어 | 모델 학습 전략, RF / XGBoost / LightGBM 비교, 성능 평가 |
| 장정아 | 데이터 엔지니어 | CSV 데이터 정합성 검증, 전처리 파이프라인 |

---

## 3. 용어 사전

### 3.1 발로란트 게임 용어

| 용어 | 설명 |
|------|------|
| **요원 (Agent)** | 플레이어가 선택하는 캐릭터. 현재 29종 (2026-03 기준, Miks·Veto·Tejo·Waylay 포함) |
| **픽창** | 경기 시작 전 요원 선택 단계. 이 프로젝트의 예측 시점 |
| **라인업** | 선수 5명 + 각 선수의 요원 픽 전체. 핵심 입력 단위 |
| **역할군 (Role)** | 요원의 플레이 스타일 분류: 타격대/척후대/전략가/감시자 |
| **타격대 (Duelist)** | 공격적 진입, 킬 창출. Jett, Reyna, Neon 등 |
| **척후대 (Initiator)** | 정보 수집, 섬광, 팀 진입 보조. Sova, Breach, Fade 등 |
| **전략가 (Controller)** | 스모크로 시야 차단, 지역 통제. Viper, Omen, Astra 등 |
| **감시자 (Sentinel)** | 수비, 사이드 잠금, 힐. Killjoy, Cypher, Sage 등 |
| **VCT** | Valorant Champions Tour. Riot Games 공식 프로 대회 |
| **ACS** | Average Combat Score. 라운드당 평균 전투 점수 |
| **KAST** | Kill/Assist/Survive/Trade. 라운드 기여 지표 (%) |
| **ADR** | Average Damage per Round. 라운드당 평균 피해량 |
| **FK / FD** | First Kill / First Death. 첫 교전 주도권 지표 |
| **맵 (Map)** | 경기 진행 무대. Ascent, Bind, Haven, Icebox 등 13개 (Corrode·Drift 포함) |

### 3.2 머신러닝 용어

| 용어 | 설명 |
|------|------|
| **K-Fold** | K겹 교차검증. 데이터를 K개로 나눠 순차적으로 검증 (본 프로젝트: K=5) |
| **GroupShuffleSplit** | match_key 단위로 같은 경기가 train/test에 겹치지 않게 분할하는 scikit-learn 분할기 |
| **앙상블** | RF + XGBoost + LightGBM 세 모델 예측 확률을 평균 내어 최종 승률 산출 |
| **Early Stopping** | 검증 성능이 일정 라운드 이상 개선되지 않으면 학습 조기 종료 |
| **dedup_key** | 24자 SHA-1 hex — 날짜/이벤트/맵/팀/요원셋/점수로 만든 경기 중복 제거 키 |
| **match_key** | 16자 SHA-1 hex — 소스+파일+경기 단위 grouping 키. train/val/test 분할 단위 |
| **소스 가중치** | 중복 경기 선택 시 신뢰도 높은 소스 우선. ryanluong challengers=1.8, vct/qualidea=1.0 (~~piyush=1.5 제거됨~~) |
| **시간 가중치** | 구식 메타 데이터 영향 줄이기. 2021~2022=0.6, 2023=0.8, 2024+=1.2 |
| **데이터 분리** | match_key 단위 분할 + GroupKFold(baseline) + 금지 피처 26개 정규식 차단 + 이전 연도만 prior 집계 + 리그평균 smoothing으로 데이터가 섞이지 않게 함 |
| **XGBoost** | eXtreme Gradient Boosting. 구조화 데이터 분류에 강한 Gradient Boosting 모델 |
| **LightGBM** | Light Gradient Boosting Machine. XGBoost 대비 빠른 학습, 메모리 효율적 |
| **Random Forest** | 여러 결정 트리의 독립 학습 후 다수결 예측 — 안정적인 baseline |
| **SHAP** | 피처별 예측 기여도를 수치로 설명하는 해석 가능성 도구 |
| **ROC-AUC** | Receiver Operating Characteristic - Area Under Curve. 이진 분류 종합 성능 |
| **F1-Score** | Precision과 Recall의 조화 평균. 클래스 불균형 시 유용 |

### 3.3 파이프라인 용어

| 용어 | 설명 |
|------|------|
| **품질 검사** | 팀당 요원 5명, 유효 요원/맵, 유효 레이블 등 조건 미충족 시 행 제외 |
| **ryanluong 파서** | vct_2021_2023 + challengers 소스 파서. overview.csv + maps_scores.csv 조인 필요 |
| **qualidea 파서** | data-since-april-2021.csv 단일 파일 파서. 조인 불필요 |
| ~~**piyush 파서**~~ | ~~2024/2025 VCT 이벤트 폴더 파서. 조인 불필요~~ (제거됨 — ryanluong vct_2024/vct_2025와 중복) |
| **atk_side_advantage** | 맵별 공격 사이드 전역 승률 (ryanluong challengers 집계) |
| **Team_Agent_Experience** | 선수가 특정 요원을 과거에 플레이한 경험 횟수 |
| ~~**Streamlit**~~ | ~~Python 전용 로컬 웹 UI 프레임워크~~ (폐기됨 — 웹 스택 FastAPI + Next.js로 전환) |
| **FastAPI** | Python 비동기 웹 프레임워크. 모델 서빙 백엔드(`src/api`) |
| **Next.js** | React 기반 풀스택 프레임워크. 시연 프런트엔드(`web`) |
| **SQLAlchemy** | Python ORM (Object-Relational Mapping). PostgreSQL `prediction_history` 테이블 연결 (구현됨, 선택적) |
| **joblib** | Python 모델 직렬화/역직렬화 라이브러리 |
| **환경변수** | `.env` 파일에 저장되는 시크릿 및 설정값 (Kaggle API Key 등) |

---

## 4. 관련 문서

| 문서 | 내용 |
|------|------|
| [01_project_summary.md](01_project_summary.md) | 프로젝트 소개 및 핵심 아이디어 |
| [02_tech_stack.md](02_tech_stack.md) | 기술 스택 상세 |
| [../03_architecture/06_ml_pipeline_architecture.md](../03_architecture/06_ml_pipeline_architecture.md) | ML 파이프라인 아키텍처 |
