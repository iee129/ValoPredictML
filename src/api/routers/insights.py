"""GET /agent-map-fit (N), POST /comp-match (K)."""
from __future__ import annotations

from fastapi import APIRouter, Query

from api.deps import to_http
from api.schemas import AgentMapFitResponse, CompMatchRequest, CompMatchResponse
from api.services import insights as ins

router = APIRouter()


@router.get("/agent-map-fit", response_model=AgentMapFitResponse)
def agent_map_fit(map: str = Query(..., description="맵 이름(예: Ascent)")) -> dict:
    try:
        return ins.agent_map_fit(map)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        raise to_http(exc if isinstance(exc, (FileNotFoundError, ValueError)) else ValueError(str(exc)))


@router.post("/comp-match", response_model=CompMatchResponse)
def comp_match(req: CompMatchRequest) -> dict:
    try:
        return ins.comp_match(req.map, list(req.agents))
    except (FileNotFoundError, ValueError) as exc:
        raise to_http(exc)
