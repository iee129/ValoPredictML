# 05. 실행 · CORS · 환경변수

## 1. 의존성 설치

```bash
source .venv/bin/activate
pip install "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0"
# 또는 requirements.txt에 두 줄 추가 후 pip install -r requirements.txt
```

나머지 ML 의존성(`joblib`, `pandas`, `scikit-learn`, `xgboost`, `lightgbm` 등)은 이미 설치돼 있다.

---

## 2. 실행

저장소 루트에서:

```bash
# 개발 (자동 리로드)
uvicorn valo_web_backend.main:app --reload --port 8000

# 또는
python -m valo_web_backend.main      # main.py 하단에 uvicorn.run(...) 둔 경우
```

확인:
```bash
curl http://localhost:8000/health
# {"status":"ok","model_loaded":true,"n_features":125,"contract":"advanced"}
```

Swagger UI: `http://localhost:8000/docs` — FastAPI가 Pydantic 스키마로 자동 생성. 시연 중 백엔드 단독 데모에도 유용.

> **실행 전 산출물 확인**: `models/advanced/ensemble.joblib`, `data/processed/{matches,players}.csv`, `data/processed/adv_kaggle_only/test.csv`가 없으면 `/predict`·`/replay`가 503/FileNotFound. 생성 절차 → [../04_integration/02_demo_runbook.md](../04_integration/02_demo_runbook.md).

---

## 3. CORS

프론트(`:3000`)와 백엔드(`:8000`)는 출처가 다르므로 CORS 필수.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        # 배포 시: "https://<your-frontend-domain>",
    ],
    allow_credentials=False,     # 쿠키/인증 없음
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

인증이 없으므로 `allow_credentials`는 False면 충분하다. 와일드카드 `allow_origins=["*"]`는 시연 한정으로만(자격증명 없으니 허용 가능).

---

## 4. 환경변수

| 변수 | 위치 | 기본값 | 용도 |
|------|------|--------|------|
| `NEXT_PUBLIC_API_URL` | 프론트(`.env.local`) | `http://localhost:8000` | API 베이스 URL |
| `VALO_MODELS_DIR` | 백엔드(선택) | `models/advanced` | 모델 경로 오버라이드 |
| `VALO_PROCESSED_DIR` | 백엔드(선택) | `data/processed` | 데이터 경로 오버라이드 |
| `VALO_REPORTS_DIR` | 백엔드(선택) | `reports/adv_kaggle_only` | 리포트 경로 오버라이드 |

`app/predict.py`의 기본 경로(`DEFAULT_MODELS_DIR` 등)는 저장소 루트 상대. 백엔드를 루트에서 실행하면 추가 설정 없이 동작한다. 경로를 바꿔야 하면 위 변수를 읽어 `predict_custom_lineup(..., models_dir=..., processed_dir=..., reports_dir=...)`에 전달.

비밀키는 `.env`로만 관리하고 커밋 금지(본 시연 API는 비밀키 불필요).

---

## 5. 시연 안정화 팁

| 이슈 | 대응 |
|------|------|
| 첫 `/predict` 지연(콜드스타트) | `lifespan` startup에서 더미 라인업 1회 예측으로 캐시 워밍 |
| 데이터 무거움 | 시연 1순위 경로로 **replay** 사용(콜드스타트 없음) |
| 산출물 부재 | `/health`로 사전 점검, 503 시 런북 안내 노출 |
| 포트 충돌 | `--port` 변경 + 프론트 `NEXT_PUBLIC_API_URL` 동기화 |

---

## 6. 관련 문서

- 앱 구조 → [01_app_structure.md](01_app_structure.md)
- 시연 런북 → [../04_integration/02_demo_runbook.md](../04_integration/02_demo_runbook.md)
