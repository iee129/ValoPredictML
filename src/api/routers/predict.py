"""POST /predict — 커스텀 5v5 예측."""
from __future__ import annotations

from fastapi import APIRouter

from app.predict import predict_custom_lineup
from web.backend.deps import to_http
from web.backend.schemas import PredictRequest, PredictResponse
from web.backend.serializers import serialize_prediction

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
def post_predict(req: PredictRequest) -> dict:
    try:
        result = predict_custom_lineup(
            map_name=req.map,
            cutoff_year=req.cutoff_year,
            team_a_slots=[s.model_dump() for s in req.team_a],
            team_b_slots=[s.model_dump() for s in req.team_b],
        )
    except (ValueError, FileNotFoundError) as exc:
        raise to_http(exc)
    return serialize_prediction(result)
