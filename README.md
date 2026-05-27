# ValoPredictML

Valorant 5v5 팀 조합(선수 5명 + 요원 5명)을 입력받아 승리 확률과 예측 근거를 출력하는 Streamlit 로컬 분석 도구.

## 현재 상태

| 단계 | 상태 |
|------|------|
| 데이터 수집 | ✅ 완료 — Kaggle 5개 데이터셋 (`data/raw/kaggle/`, git 제외) |
| VLR.gg 수집 | 🔄 수집 중 — `ml/vlrgg/` |
| 도메인 상수 | ✅ 완료 — `ml/valorant.py` |
| 베이스라인 모델 | ✅ 완료 — `ml/baseline/` Kaggle-only previous-year 178피처, train+val 학습 (Test AUC 0.6562, trusted) |
| 앙상블 모델 (advanced) | ✅ 완료 — `ml/advanced/` Kaggle-only 125피처 RF + XGBoost + LightGBM soft voting (Test AUC 0.7664) |
| Streamlit UI | ✅ 완료 — `app/main.py`, 커스텀 5v5 + Kaggle test replay + 모델 근거 |
| PostgreSQL 저장 | 🚫 범위 외 |

## 실행 환경

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 데이터 다운로드

Kaggle API 키가 필요해요. 최초 1회만 설정하면 됩니다.

1. [kaggle.com](https://www.kaggle.com) → 계정 설정 → API → **Create New Token**
2. 다운로드된 `kaggle.json`을 아래 경로에 저장

```
# macOS / Linux
~/.kaggle/kaggle.json

# Windows
C:\Users\<사용자명>\.kaggle\kaggle.json
```

3. 데이터 다운로드 실행

```bash
python dataload.py
```

이미 다운로드된 폴더는 자동으로 건너뜁니다.

## 문서

| 문서 | 내용 |
|------|------|
| [docs/overview.md](docs/overview.md) | 프로젝트 정의, 아키텍처, 로드맵, 차별점 |
| [docs/datasets.md](docs/datasets.md) | 데이터셋 상세 — 내용, 관련성, 파이프라인 역할 |
| [docs/competitive_analysis.md](docs/competitive_analysis.md) | 유사 프로젝트 비교 분석 |

## 기술 스택

| 계층 | 기술 |
|------|------|
| 언어 | Python 3.14 |
| 데이터 처리 | pandas, NumPy |
| ML | scikit-learn, XGBoost, LightGBM, SHAP |
| UI | Streamlit |
| DB | SQLite 기본값 + SQLAlchemy |

## 로컬 실행

```bash
# 데이터 다운로드
python dataload.py

# ML 파이프라인
python -m ml.baseline.preprocess
python -m ml.baseline.train
python -m ml.baseline.evaluate
python -m ml.baseline.validate

python -m ml.baseline.preprocess --feature-contract advanced
python -m ml.advanced.ensemble --input data/processed/adv_kaggle_only --output models/advanced --reports reports/adv_kaggle_only
python -m ml.advanced.evaluate --input data/processed/adv_kaggle_only --models models/advanced --reports reports/adv_kaggle_only
python -m ml.advanced.validate --reports reports/adv_kaggle_only --models models/advanced

# Streamlit UI
python -m streamlit run app/main.py
```
