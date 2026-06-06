"""POST /predict — 커스텀 5v5 예측."""
from __future__ import annotations

from fastapi import APIRouter

from inference.predict import predict_custom_lineup
from api.deps import to_http
from api.schemas import PredictRequest, PredictResponse
from api.serializers import serialize_prediction
from api.services import history as history_service

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
    response = serialize_prediction(result)
    history_meta = history_service.save_prediction(req, response)
    if history_meta:
        response.update(history_meta)
    return response
