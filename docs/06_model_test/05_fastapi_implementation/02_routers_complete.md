> ⚠️ **범위 외**: FastAPI 미사용. 본 프로젝트는 Streamlit 로컬 도구이며 API 엔드포인트 테스트는 적용되지 않는다. 본문은 참고용으로 보존된다.

# 02. 라우터 완전 구현 코드

## 1. predict.py 라우터

```python
# backend/routers/predict.py
"""POST /predict — 팀 조합 승률 예측."""

import logging
from fastapi import APIRouter, HTTPException

from schemas.predict import PredictRequest, PredictResponse
from services.prediction_service import PredictionService

logger = logging.getLogger(__name__)
router = APIRouter()

# 싱글톤 서비스 인스턴스 (모듈 로드 시 1회 생성)
_service: PredictionService | None = None


def get_service() -> PredictionService:
    global _service
    if _service is None:
        _service = PredictionService()
    return _service


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="팀 조합 승률 예측",
    description="팀 A와 팀 B의 요원 조합을 입력받아 팀 A의 승리 확률을 반환합니다.",
    responses={
        200: {"description": "예측 성공"},
        422: {"description": "입력 검증 실패 (잘못된 맵, 팀 인원, 중복 요원)"},
        500: {"description": "예측 서비스 내부 오류"},
        503: {"description": "모델 초기화 중"},
    },
)
async def predict_win_rate(request: PredictRequest):
    svc = get_service()

    if not svc.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="서비스 초기화 중입니다. 잠시 후 다시 시도하세요.",
        )

    try:
        result = svc.predict(
            map_name=request.map,
            team_a=request.team_a,
            team_b=request.team_b,
        )
        logger.info(
            f"예측 완료: map={request.map} "
            f"win_prob={result['win_probability']:.3f} "
            f"confidence={result['confidence']}"
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FileNotFoundError as e:
        logger.error(f"모델 파일 없음: {e}")
        raise HTTPException(status_code=500, detail=f"모델 파일을 찾을 수 없습니다: {e}")
    except Exception as e:
        logger.error(f"예측 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"예측 오류: {str(e)}")
```

---

## 2. agents.py 라우터

```python
# backend/routers/agents.py
"""GET /agents — 요원 목록 반환."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from data.agent_data import AGENTS, ROLES

router = APIRouter()


@router.get(
    "/agents",
    summary="요원 목록 조회",
    description="발로란트 전체 요원 목록과 역할군 메타데이터를 반환합니다.",
)
async def get_agents():
    data = {
        "agents": [
            {
                "name": name,
                "role": info["role"],
                "role_kr": ROLES[info["role"]]["name_kr"],
            }
            for name, info in AGENTS.items()
        ],
        "roles": {
            role: {
                "name_kr": data["name_kr"],
                "description": data["description"],
                "count": sum(1 for a in AGENTS.values() if a["role"] == role),
            }
            for role, data in ROLES.items()
        },
        "total": len(AGENTS),
    }

    response = JSONResponse(content=data)
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response
```

---

## 3. maps.py 라우터

```python
# backend/routers/maps.py
"""GET /maps — 맵 목록 반환."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from data.map_data import MAPS

router = APIRouter()


@router.get(
    "/maps",
    summary="맵 목록 조회",
    description="발로란트 현재 경쟁 맵 풀 목록을 반환합니다.",
)
async def get_maps():
    data = {
        "maps": [
            {
                "name": name,
                "name_kr": info["name_kr"],
                "region": info["region"],
                "callouts": info["callouts"],
            }
            for name, info in MAPS.items()
        ],
        "total": len(MAPS),
    }

    response = JSONResponse(content=data)
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response
```

---

## 4. history.py 라우터

```python
# backend/routers/history.py
"""GET /history — 예측 기록 조회 (페이지네이션 + 맵 필터)."""

import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models.prediction import Prediction
from schemas.history import HistoryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="예측 기록 조회",
    description="저장된 예측 기록을 최신순으로 반환합니다. 맵 필터링 및 페이지네이션을 지원합니다.",
)
async def get_history(
    limit: int = Query(
        default=20, ge=1, le=100,
        description="반환할 최대 건수 (1~100)"
    ),
    offset: int = Query(
        default=0, ge=0,
        description="건너뛸 레코드 수"
    ),
    map: str | None = Query(
        default=None,
        description="맵 이름으로 필터링 (선택)"
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Prediction).order_by(Prediction.id.desc())

    if map is not None:
        query = query.filter(Prediction.map == map)

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    logger.info(f"기록 조회: total={total}, limit={limit}, offset={offset}, map={map}")

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": item.id,
                "created_at": item.created_at.isoformat(),
                "map": item.map,
                "team_a_agents": item.team_a_agents,
                "team_b_agents": item.team_b_agents,
                "win_probability": item.win_probability,
                "confidence": item.confidence,
            }
            for item in items
        ],
    }
```

---

## 5. health.py 라우터

```python
# backend/routers/health.py
"""GET /health — 서버 상태 확인."""

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from database import engine

logger = logging.getLogger(__name__)
router = APIRouter()

_start_time = time.time()


@router.get(
    "/health",
    summary="서버 상태 확인",
    description="서버 상태, 모델 로드 여부, DB 연결을 확인합니다.",
)
async def health_check():
    # 모델 상태 확인
    model_loaded = False
    model_version = None
    trained_at = None
    try:
        from services.prediction_service import PredictionService
        svc = PredictionService()
        model_loaded = svc.is_loaded()
        if model_loaded:
            model_version = svc.get_version()
            trained_at = svc.get_trained_at()
    except Exception as e:
        logger.warning(f"모델 상태 확인 실패: {e}")

    # DB 연결 확인
    db_connected = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_connected = True
    except Exception as e:
        logger.error(f"DB 연결 실패: {e}")

    # 전체 상태 결정
    if model_loaded and db_connected:
        status = "ok"
    elif db_connected:
        status = "degraded"
    else:
        status = "error"

    body = {
        "status": status,
        "model_loaded": model_loaded,
        "model_version": model_version,
        "trained_at": trained_at,
        "db_connected": db_connected,
        "uptime_seconds": int(time.time() - _start_time),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    http_status = 503 if status == "error" else 200
    return JSONResponse(content=body, status_code=http_status)
```

---

## 6. ORM 모델 (models/prediction.py)

```python
# backend/models/prediction.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ARRAY
from sqlalchemy.sql import func
from database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at      = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    map             = Column(String(50), nullable=False, index=True)
    team_a_agents   = Column(ARRAY(String), nullable=False)
    team_b_agents   = Column(ARRAY(String), nullable=False)
    win_probability = Column(Float, nullable=False)
    confidence      = Column(String(10), nullable=False)

    def __repr__(self):
        return (
            f"<Prediction id={self.id} map={self.map} "
            f"win_prob={self.win_probability:.3f}>"
        )
```

---

## 7. 예측 결과 DB 저장 — predict 라우터 확장

예측 후 결과를 자동으로 DB에 저장하는 완전 구현:

```python
# backend/routers/predict.py (DB 저장 포함 버전)
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.prediction import Prediction
from schemas.predict import PredictRequest, PredictResponse
from services.prediction_service import PredictionService

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
async def predict_win_rate(
    request: PredictRequest,
    db: Session = Depends(get_db),
):
    svc = PredictionService()

    if not svc.is_loaded():
        raise HTTPException(status_code=503, detail="서비스 초기화 중입니다.")

    try:
        result = svc.predict(
            map_name=request.map,
            team_a=request.team_a,
            team_b=request.team_b,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예측 오류: {str(e)}")

    # DB 저장
    record = Prediction(
        map=request.map,
        team_a_agents=request.team_a,
        team_b_agents=request.team_b,
        win_probability=result["win_probability"],
        confidence=result["confidence"],
    )
    db.add(record)
    db.commit()

    return result
```
