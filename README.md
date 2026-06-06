# ValoPredictML

Valorant 5v5 팀 조합(선수 5명 + 요원 5명)을 입력받아 승리 확률과 예측 근거를 출력하는 웹 분석 도구 (FastAPI + Next.js).

## 현재 상태

| 단계 | 상태 |
|------|------|
| 데이터 수집 | ✅ 완료 — Kaggle 5개 데이터셋 (`data/raw/kaggle/`, git 제외) |
| VLR.gg 수집 | ✅ 완료 — 통합 인제스트(`src/data/ingest.py`)와 시간순 피처 생성(`src/features/chrono_preprocess.py --include-vlrgg`)에 포함 |
| 도메인 상수 | ✅ 완료 — `src/domain/valorant.py` |
| 베이스라인 모델 | ✅ 완료 — 중간발표 PDF 기준 reference baseline(421피처 LR+DT soft voting, 랜덤 80/20 split, Test AUC 0.5943, trusted) |
| 앙상블 모델 (advanced) | ✅ 완료 — `src/ml/advanced/` 시간순 split 179피처 RF + XGBoost + LightGBM soft voting (91,458개 맵 단위 승패 샘플, Test AUC 0.7010, trusted) |
| 웹 UI | ✅ 완료 — `web/`(Next.js) + `src/api/`(FastAPI), 커스텀 5v5 + test replay + 모델 근거 |
| PostgreSQL 저장 | 선택 구현 — `VALO_DATABASE_URL` 설정 시 `/history` 활성, 미설정 시 예측 기능은 정상 |

## 실행 환경

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .            # src-layout 패키지 editable 등록 (from domain..., uvicorn api.main:app)
```

## 실행용 산출물

모델 파일, 전처리 데이터, 평가 리포트는 용량 때문에 GitHub에 포함하지 않습니다. 웹 시연까지 실행하려면 아래 파일을 내려받아 저장소 루트에서 압축을 풀어 주세요.

- 다운로드: [runtime.zip](https://drive.google.com/file/d/1G1IeQNduWs8KqgSvQ8pb2My6Cj2kFLGD/view?usp=sharing)
- SHA256: `831e8df0edb67f3d86de58ecc5689a166c7b5ca50cbb4b2282ed269ce41b6ad3`

```bash
unzip runtime.zip
```

압축 해제 후 생성되는 주요 경로:

- `models/advanced/ensemble.joblib`
- `models/advanced/meta.json`
- `data/processed/matches.csv`
- `data/processed/players.csv`
- `data/processed/advanced/test.csv`
- `reports/advanced/*.json`
- `reports/insights/*.json`

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
python -m data.dataload
```

이미 다운로드된 폴더는 자동으로 건너뜁니다.

## 문서

| 문서 | 내용 |
|------|------|
| [docs/01_overview/01_project_summary.md](docs/01_overview/01_project_summary.md) | 프로젝트 정의, 목표, 입력 계약 |
| [docs/07_data/README.md](docs/07_data/README.md) | 데이터셋 상세 — 내용, 관련성, 파이프라인 역할 |
| [docs/competitive_analysis.md](docs/competitive_analysis.md) | 유사 프로젝트 비교 분석 |

## 기술 스택

| 계층 | 기술 |
|------|------|
| 언어 | Python 3.14 |
| 데이터 처리 | pandas, NumPy |
| ML | scikit-learn, XGBoost, LightGBM |
| 백엔드 | FastAPI, uvicorn |
| 프런트 | Next.js 16, React 19, TypeScript, Tailwind v4 |
| DB | PostgreSQL 선택 기능(SQLAlchemy Core, 미설정 시 `/history`만 503) |

## 로컬 실행

```bash
# 데이터 다운로드
python -m data.dataload

# ML 파이프라인
# Baseline은 중간발표 PDF 기준 reference artifact로 고정
python -m ml.baseline.reference
python -m ml.baseline.validate

python -m features.chrono_preprocess --include-vlrgg
python -m ml.advanced.ensemble
python -m ml.advanced.evaluate
python -m ml.advanced.validate

# 웹 스택 (백엔드 + 프런트)
uvicorn api.main:app --reload --port 8000   # FastAPI 백엔드
cd web && npm install && npm run dev         # Next.js 프런트 (http://localhost:3000)
```
