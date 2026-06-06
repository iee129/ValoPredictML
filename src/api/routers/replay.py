"""GET /replay/matches, GET /replay/{match_key} — 경기 다시보기."""
from __future__ import annotations

from fastapi import APIRouter

from inference.predict import predict_replay_match
from api.deps import to_http
from api.schemas import PredictResponse
from api.serializers import serialize_prediction
from api.services import prediction as svc

router = APIRouter()


@router.get("/replay/matches")
def replay_matches(q: str = "", limit: int = 200) -> dict:
    """전체 테스트셋에서 q(팀/맵/날짜/키)로 검색. items=상위 limit, total=전체 일치 수."""
    try:
        items, total = svc.replay_query(q, limit)
    except (FileNotFoundError, OSError) as exc:
        raise to_http(exc if isinstance(exc, FileNotFoundError) else FileNotFoundError())
    return {"items": items, "total": total}


@router.get("/replay/{match_key}", response_model=PredictResponse)
def replay_one(match_key: str) -> dict:
    try:
        result = predict_replay_match(match_key)
    except (ValueError, FileNotFoundError) as exc:
        raise to_http(exc)
    return serialize_prediction(result)
