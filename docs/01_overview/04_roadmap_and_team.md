# 04. 로드맵, 팀 구성, 용어 사전

마지막 업데이트: 2026-05-04

## 1. 단계별 로드맵

```
Phase 0 ✅  환경 설정 (venv, Kaggle 인증)
Phase 1 ✅  데이터 수집 (Kaggle 7개 데이터셋, 2.3GB)
Phase 2 →   데이터 전처리 (ml/agent_roles.py, ml/data_pipeline.py)
Phase 3 →   피처 엔지니어링 (역할군·선수스탯·시너지·요원조합 피처 43개)
Phase 4     모델 학습 및 평가 (RF, XGBoost, LightGBM)
Phase 5     Streamlit UI 구현
Phase 6     검증 및 발표 정리
```

### 단계별 완료 기준

| Phase | 완료 기준 |
|-------|-----------|
| Phase 0 | `.venv` 활성화, `python dataload.py` 정상 실행 |
| Phase 1 | `data/raw/kaggle/`에 7개 데이터셋, 2.3GB 다운로드 완료 |
| Phase 2 | `data/processed/matches_clean.csv` 생성, 품질 게이트 통과, `reports/preprocess_summary.json` 생성 |
| Phase 3 | 43개 피처 생성, `data/processed/features_base.csv` 확인, `train.csv / val.csv / test.csv` 생성 |
| Phase 4 | RF/XGBoost/LightGBM Accuracy·ROC-AUC·F1 비교표 생성, K-Fold(K=5) 교차 검증 완료 |
| Phase 5 | 입력→예측→설명 흐름 Streamlit에서 동작 |
| Phase 6 | 발표 자료에 데이터/피처/모델/평가/한계 포함 |

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
| **요원 (Agent)** | 플레이어가 선택하는 캐릭터. 현재 27종 |
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
| **맵 (Map)** | 경기 진행 무대. Ascent, Bind, Haven, Icebox 등 12개 |

### 3.2 머신러닝 용어

| 용어 | 설명 |
|------|------|
| **K-Fold** | K겹 교차검증. 데이터를 K개로 나눠 순차적으로 검증 (본 프로젝트: K=5) |
| **GroupShuffleSplit** | match_key 단위로 경기 누수 없이 분할하는 scikit-learn 분할기 |
| **앙상블** | RF + XGBoost + LightGBM 세 모델 예측 확률을 평균 내어 최종 승률 산출 |
| **Early Stopping** | 검증 성능이 일정 라운드 이상 개선되지 않으면 학습 조기 종료 |
| **dedup_key** | 24자 SHA-1 hex — 날짜/이벤트/맵/팀/요원셋/점수로 만든 경기 중복 제거 키 |
| **match_key** | 16자 SHA-1 hex — 소스+파일+경기 단위 grouping 키. train/val/test 분할 단위 |
| **소스 가중치** | 중복 경기 선택 시 신뢰도 높은 소스 우선. ryanluong challengers=1.8, piyush=1.5 |
| **시간 가중치** | 구식 메타 데이터 영향 줄이기. 2021~2022=0.6, 2023=0.8, 2024+=1.2 |
| **A/B Swap 증강** | 팀 A/B를 뒤집은 행을 train에 추가 — 위치 편향 방지 |
| **XGBoost** | eXtreme Gradient Boosting. 구조화 데이터 분류에 강한 Gradient Boosting 모델 |
| **LightGBM** | Light Gradient Boosting Machine. XGBoost 대비 빠른 학습, 메모리 효율적 |
| **Random Forest** | 여러 결정 트리의 독립 학습 후 다수결 예측 — 안정적인 baseline |
| **SHAP** | 피처별 예측 기여도를 수치로 설명하는 해석 가능성 도구 |
| **ROC-AUC** | Receiver Operating Characteristic - Area Under Curve. 이진 분류 종합 성능 |
| **F1-Score** | Precision과 Recall의 조화 평균. 클래스 불균형 시 유용 |

### 3.3 파이프라인 용어

| 용어 | 설명 |
|------|------|
| **품질 게이트** | 팀당 요원 5명, 유효 요원/맵, 유효 레이블 등 조건 미충족 시 행 제외 |
| **ryanluong 파서** | vct_2021_2023 + challengers 소스 파서. overview.csv + maps_scores.csv 조인 필요 |
| **qualidea 파서** | data-since-april-2021.csv 단일 파일 파서. 조인 불필요 |
| **piyush 파서** | 2024/2025 VCT 이벤트 폴더 파서. 조인 불필요 |
| **atk_side_advantage** | 맵별 공격 사이드 전역 승률 (ryanluong challengers 집계) |
| **Team_Agent_Experience** | 선수가 특정 요원을 과거에 플레이한 경험 횟수 |
| **Streamlit** | Python 전용 로컬 웹 UI 프레임워크 |
| **SQLAlchemy** | Python ORM (Object-Relational Mapping). PostgreSQL 연결 후보 |
| **joblib** | Python 모델 직렬화/역직렬화 라이브러리 |
| **환경변수** | `.env` 파일에 저장되는 시크릿 및 설정값 (Kaggle API Key 등) |

---

## 4. 관련 문서

| 문서 | 내용 |
|------|------|
| [01_project_summary.md](01_project_summary.md) | 프로젝트 소개 및 핵심 아이디어 |
| [02_tech_stack.md](02_tech_stack.md) | 기술 스택 상세 |
| [../03_architecture/06_ml_pipeline_architecture.md](../03_architecture/06_ml_pipeline_architecture.md) | ML 파이프라인 아키텍처 |
