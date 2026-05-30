"""GET /replay/matches, GET /replay/{match_key} — 경기 다시보기."""
from __future__ import annotations

from fastapi import APIRouter

from app.predict import predict_replay_match
from valo_web_backend.deps import to_http
from valo_web_backend.schemas import PredictResponse
from valo_web_backend.serializers import serialize_prediction
from valo_web_backend.services import prediction as svc

router = APIRouter()


@router.get("/replay/matches")
def replay_matches(limit: int = 200) -> dict:
    try:
        items = list(svc.replay_list(limit))
    except (FileNotFoundError, OSError) as exc:
        raise to_http(exc if isinstance(exc, FileNotFoundError) else FileNotFoundError())
    return {"items": items, "total": len(items)}


@router.get("/replay/{match_key}", response_model=PredictResponse)
def replay_one(match_key: str) -> dict:
    try:
        result = predict_replay_match(match_key)
    except (ValueError, FileNotFoundError) as exc:
        raise to_http(exc)
    return serialize_prediction(result)
