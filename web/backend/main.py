"""FastAPI 앱 진입점.

실행(저장소 루트):
    uvicorn web.backend.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web.backend.routers import insights, model, options, predict, replay
from web.backend.services.prediction import warmup


@asynccontextmanager
async def lifespan(app: FastAPI):
    warmup()   # 모델 로드 + 옵션 캐시 워밍(실패해도 서버는 뜬다)
    yield


app = FastAPI(title="ValoPredictML API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(model.router)      # /health, /model
app.include_router(options.router)    # /options, /agents, /maps, /players, /years
app.include_router(predict.router)    # /predict
app.include_router(replay.router)     # /replay/*
app.include_router(insights.router)   # /agent-map-fit, /comp-match


@app.get("/")
def root() -> dict:
    return {"service": "ValoPredictML API", "docs": "/docs", "health": "/health"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web.backend.main:app", host="0.0.0.0", port=8000, reload=False)
