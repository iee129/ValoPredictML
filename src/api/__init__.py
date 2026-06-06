"""ValoPredictML FastAPI 백엔드.

app/predict.py(advanced 179피처 앙상블) + reports/insights/*.json 을 서빙한다.
모델 로직은 재구현하지 않고 app.predict 를 그대로 호출한다.
저장소 루트에서 실행: `uvicorn web.backend.main:app --reload --port 8000`
"""
