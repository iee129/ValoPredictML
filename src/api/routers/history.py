"""GET /history — PostgreSQL prediction history."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import HistoryDetailResponse, HistoryListResponse
from api.services import history as svc
from api.services.history import HistoryUnavailable

router = APIRouter()


@router.get("/history", response_model=HistoryListResponse)
def history_list(limit: int = 50, offset: int = 0) -> dict:
    try:
        return svc.list_predictions(limit=limit, offset=offset)
    except HistoryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/history/{history_id}", response_model=HistoryDetailResponse)
def history_detail(history_id: str) -> dict:
    try:
        item = svc.get_prediction(history_id)
    except HistoryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="히스토리 항목을 찾지 못했습니다.")
    return item
