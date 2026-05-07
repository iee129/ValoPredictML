# ValoPredictML — Python 파일 안내

> 이 문서는 프로젝트에 있는 모든 Python 파일의 위치와 역할을 정리합니다.

---

## 실행 순서 (처음부터 끝까지)

```
1단계  dataload.py              데이터를 인터넷에서 다운로드
2단계  ml/data_pipeline.py      다운로드한 데이터를 모델이 배울 수 있는 형태로 정리
3단계  ml/train_model.py        세 가지 AI 모델을 학습
4단계  ml/evaluate_model.py     모델이 얼마나 잘 맞추는지 측정
5단계  ml/validate_metrics.py   목표 성능 기준을 통과했는지 검증
6단계  streamlit run app/streamlit_app.py   웹 UI 실행
```

---

## 파일별 상세 설명

### 최상위 (프로젝트 루트)

| 경로 | 역할 |
|------|------|
| `dataload.py` | Kaggle에서 발로란트 경기 데이터 7개 묶음을 자동으로 다운로드해서 `data/raw/kaggle/` 폴더에 저장합니다. |

**실행 방법**
```bash
python dataload.py
```

---

### `ml/` 폴더 — 머신러닝 파이프라인

#### `ml/agent_roles.py`
- **역할**: 프로젝트 전체가 함께 쓰는 "공용 사전" 파일
- **하는 일**:
  - 27개 발로란트 요원의 역할군(타격대·척후대·전략가·감시자)을 기록
  - 맵 이름 목록과 인코딩 번호를 관리
  - 오타나 소문자로 입력된 요원·맵·팀 이름을 정규 표기로 변환
- **다른 파일들이 이 파일을 `from ml.agent_roles import ...` 형태로 불러서 사용**

#### `ml/data_pipeline.py`
- **역할**: 원시 CSV 데이터를 AI가 배울 수 있는 숫자 표로 변환하는 가장 큰 처리 파이프라인
- **하는 일** (7단계):
  1. **파서 실행** — 3개 소스(ryanluong VCT, Challengers, qualidea, ediashtarevin)의 CSV를 읽어 경기 목록 생성
  2. **품질 게이트** — 선수 5명 미만, 알 수 없는 요원·맵, 무승부 등 불량 데이터 제거
  3. **Phase 1 피처** — 역할군 인원 수·차이·맵 인코딩 등 19개 기본 피처 생성
  4. **분할** — 경기(match_key) 단위로 train 70% / val 15% / test 15% 분리
  5. **Phase 2 통계** — train 데이터만 보고 선수별·요원별 평균 스탯 집계 (데이터 누수 방지)
  6. **Phase 2 피처 추가** — 평균 ACS·KD·KAST·ADR 등 24개 스탯 피처 추가 + train 2배 증강
  7. **저장** — `data/processed/`에 CSV 파일들과 JSON 캐시 저장
- **출력**: `train.csv`, `val.csv`, `test.csv`, `features_base.csv`, `player_stats.json`, `agent_map_stats.json`

**실행 방법**
```bash
python -m ml.data_pipeline --input data/raw/kaggle --output data/processed --reports reports
```

#### `ml/train_model.py`
- **역할**: 세 가지 AI 모델을 학습하고 저장
- **하는 일**:
  - **RandomForest** — 수많은 결정 나무로 다수결 예측
  - **XGBoost** — 점진적으로 오차를 줄이는 부스팅 모델, Optuna로 최적 파라미터 자동 탐색
  - **LightGBM** — XGBoost보다 빠른 부스팅 모델, 마찬가지로 Optuna HPO 적용
  - 세 모델의 예측을 평균 내는 **앙상블** 구성
- **출력**: `models/rf.joblib`, `models/xgb.joblib`, `models/lgbm.joblib`
- **실제 성능**: Ensemble AUC = 0.935, Accuracy = 0.854, F1 = 0.851

**실행 방법**
```bash
python -m ml.train_model --input data/processed --output models --reports reports
```

#### `ml/evaluate_model.py`
- **역할**: 학습된 모델이 얼마나 정확한지 측정
- **하는 일**:
  - GroupKFold(5) 교차검증 — 같은 경기가 train/test에 동시에 들어가지 않도록 5번 나눠서 검증
  - 테스트셋 AUC·Accuracy·F1 계산
  - SHAP으로 어떤 피처가 예측에 가장 큰 영향을 주는지 분석
  - 결과를 `reports/eval_summary.json`에 저장
- **출력**: `reports/eval_summary.json`, `reports/shap_values.csv`

**실행 방법**
```bash
python -m ml.evaluate_model --input data/processed --models models --reports reports
```

#### `ml/validate_metrics.py`
- **역할**: 모델 성능이 목표 기준을 충족하는지 검증하는 품질 게이트
- **하는 일**:
  - AUC ≥ 0.90, Accuracy ≥ 0.80, F1 ≥ 0.80 기준 통과 여부 확인
  - 베이스라인(단순 다수결) 대비 개선폭 측정
  - 과적합 여부 확인 (train/val/test 점수 비교)
  - SHAP 분석 결과 요약
- **출력**: 터미널 출력 + `reports/baseline_comparison.json`

**실행 방법**
```bash
python -m ml.validate_metrics --input data/processed --reports reports
```

---

### `app/` 폴더 — Streamlit 웹 UI

#### `app/streamlit_app.py`
- **역할**: 앱의 시작점. 사이드바 메뉴와 4개 페이지 연결
- **하는 일**:
  - 페이지 제목·아이콘·레이아웃 설정
  - 사이드바에 "소개 / 예측 / 기록 / 가이드" 메뉴 생성
  - 선택한 메뉴에 해당하는 뷰 모듈의 `render()` 함수 호출

**실행 방법**
```bash
streamlit run app/streamlit_app.py
```

#### `app/model_loader.py`
- **역할**: 세 모델 파일을 메모리에 불러오고 예측·SHAP 계산을 담당
- **하는 일**:
  - `@st.cache_resource`로 모델을 한 번만 로드해서 재사용
  - 세 모델 예측값을 평균 내어 팀A 승률 반환
  - RF 모델 기반 SHAP 값 계산

#### `app/player_lookup.py`
- **역할**: 선수 이름을 입력하면 해당 선수의 평균 스탯을 반환
- **하는 일**:
  - `data/processed/player_stats.json` 캐시를 읽어 선수별 ACS·KD·KAST 등 조회
  - 파일이 없으면 기본값(avg_kast=0.70 등) 사용
  - 선수 이름 목록 제공 (예측 화면 드롭다운용)

#### `app/feature_builder.py`
- **역할**: UI에서 입력한 팀 구성을 AI 모델이 이해할 수 있는 숫자 43개로 변환
- **하는 일**:
  - `PlayerInput` 데이터 클래스로 선수·요원 정보 수신
  - 역할군 카운트·맵 인코딩·선수 스탯 조회·요원·맵 승률 조합
  - `FEATURE_ORDER`에 정의된 순서대로 1행 DataFrame 반환 (훈련 때 순서와 반드시 일치)

#### `app/db.py`
- **역할**: 예측 결과를 데이터베이스에 저장하고 조회
- **하는 일**:
  - SQLAlchemy ORM으로 `Prediction` 테이블 정의
  - 환경 변수 `DATABASE_URL`로 SQLite(기본) 또는 PostgreSQL 연결
  - 예측 결과 저장(`save_prediction`) / 이력 조회(`get_predictions`)

---

### `app/views/` 폴더 — 화면별 뷰 모듈

각 파일은 `render()` 함수 하나를 갖고 있으며, `streamlit_app.py`가 선택된 메뉴에 따라 호출합니다.

| 경로 | 탭 이름 | 역할 |
|------|---------|------|
| `app/views/intro.py` | 소개 | 프로젝트 설명 + AUC·Accuracy·F1 지표 카드 + 피처 중요도 막대 차트 + 베이스라인 비교 |
| `app/views/predict.py` | 예측 | 팀 구성 입력 → 승률 예측 → KAST 기여도 테이블 → SHAP 막대 차트 → 슬롯별 최선 요원 추천 |
| `app/views/history.py` | 기록 | DB에서 과거 예측 이력 조회, 맵 이름 필터, ID로 상세 보기 |
| `app/views/guide.py` | 가이드 | 역할군(타격대/척후대/전략가/감시자) 소개 + 맵별 강세 요원 승률 + 인기 승리 조합 Top 5 |

---

## 파일 구조 한눈에 보기

```
ValoPredicML/
│
├── dataload.py                  ← 1단계: 데이터 다운로드
│
├── ml/
│   ├── agent_roles.py           ← 공용 유틸 (요원·맵 정규화)
│   ├── data_pipeline.py         ← 2단계: 전처리 파이프라인
│   ├── train_model.py           ← 3단계: 모델 학습
│   ├── evaluate_model.py        ← 4단계: 성능 평가
│   └── validate_metrics.py      ← 5단계: 품질 검증
│
└── app/
    ├── streamlit_app.py         ← 6단계: UI 진입점
    ├── model_loader.py          ← 모델 로드 & 예측
    ├── player_lookup.py         ← 선수 스탯 조회
    ├── feature_builder.py       ← 피처 변환 (UI → 모델 입력)
    ├── db.py                    ← 예측 기록 저장·조회
    └── views/
        ├── intro.py             ← 소개 탭
        ├── predict.py           ← 예측 탭
        ├── history.py           ← 기록 탭
        └── guide.py             ← 가이드 탭
```
