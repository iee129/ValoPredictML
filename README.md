# ValoPredictML

Valorant 5v5 팀 조합(선수 5명 + 요원 5명)을 입력받아 승리 확률과 예측 근거를 출력하는 Streamlit 로컬 분석 도구.

## 현재 상태

| 단계 | 상태 |
|------|------|
| 데이터 수집 | ✅ 완료 — Kaggle 3개 데이터셋 (`data/raw/kaggle/`, git 제외) |
| VLR.gg 수집 | 🔄 부분 구현 — `ml/vlrgg/` |
| 도메인 상수 | ⏳ 미구현 — `ml/valorant.py` |
| 베이스라인 모델 | ⏳ 미구현 — `ml/baseline/` |
| 앙상블 모델 (advanced) | ⏳ 미구현 — `ml/advanced/` (RF + XGBoost + LightGBM) |
| Streamlit UI | ⏳ 미구현 — `app/main.py` |
| PostgreSQL 저장 | 🚫 범위 외 |

## 실행 환경

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

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

# ML 파이프라인 (구현 예정)
python -m ml.baseline.preprocess --input data/raw --output data/processed/baseline
python -m ml.advanced.ensemble --input data/processed/advanced --output models/advanced

# Streamlit UI (구현 예정)
streamlit run app/main.py
```
