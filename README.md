# ValoPredictML

Valorant 5v5 팀 조합(선수 5명 + 요원 5명)을 입력받아 승리 확률과 예측 근거를 출력하는 Streamlit 로컬 분석 도구.

## 현재 상태

| 단계 | 상태 |
|------|------|
| 데이터 수집 | ✅ 완료 — Kaggle 7개 데이터셋, 2.3GB (`data/raw/kaggle/`, git 제외) |
| 데이터 전처리 | 🔜 다음 단계 — `ml/data_pipeline.py` 구현 예정 |
| 모델 학습 | ⬜ 미구현 — RF / XGBoost / LightGBM |
| Streamlit UI | ⬜ 미구현 |
| PostgreSQL 저장 | ⬜ 미구현 (후보) |

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
| [docs/preprocessing.md](docs/preprocessing.md) | 데이터 전처리 전략 — 파서, 정규화, 품질 게이트, 분할, 39개 피처 정의 |
| [docs/ui_design.md](docs/ui_design.md) | Streamlit 5개 화면 설계 |
| [docs/datasets.md](docs/datasets.md) | 7개 데이터셋 상세 — 내용, 관련성, 파이프라인 역할 |
| [docs/valorant.md](docs/valorant.md) | 발로란트 게임 규칙 및 요원 역할 가이드 |
| [docs/TODO.md](docs/TODO.md) | 전체 작업 TODO 리스트 — 완료·진행중·미구현 단계별 정리 |

## 기술 스택

| 계층 | 기술 |
|------|------|
| 언어 | Python 3.14 |
| 데이터 처리 | pandas, NumPy |
| ML (예정) | scikit-learn, XGBoost, LightGBM, SHAP |
| UI (예정) | Streamlit |
| DB (후보) | PostgreSQL + SQLAlchemy |

