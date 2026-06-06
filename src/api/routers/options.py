"""GET /options, /agents, /maps, /players, /years — 입력 위젯 데이터."""
from __future__ import annotations

from fastapi import APIRouter

from app.predict import MAP_LABELS
from ml.agent_roles import AGENT_ROLE_MAP
from web.backend.deps import to_http
from web.backend.services import prediction as svc

router = APIRouter()


def _role(agent: str) -> str:
    return AGENT_ROLE_MAP.get(agent, "").lower()


def _agents(o: dict) -> list[dict]:
    return [{"name": a, "role": _role(a)} for a in o["agents"]]


def _maps(o: dict) -> list[dict]:
    return [{"name": m, "ko": MAP_LABELS.get(m, m)} for m in o["maps"]]


@router.get("/options")
def options() -> dict:
    try:
        o = svc.options_bundle()
    except (FileNotFoundError, OSError) as exc:
        raise to_http(exc if isinstance(exc, FileNotFoundError) else FileNotFoundError())
    return {
        "maps": _maps(o),
        "agents": _agents(o),
        "players": o["players"],
        "featured_players": o.get("featured_players", []),
        "years": o["years"],
    }


@router.get("/agents")
def agents() -> list[dict]:
    try:
        return _agents(svc.options_bundle())
    except (FileNotFoundError, OSError):
        raise to_http(FileNotFoundError())


@router.get("/maps")
def maps() -> list[dict]:
    try:
        return _maps(svc.options_bundle())
    except (FileNotFoundError, OSError):
        raise to_http(FileNotFoundError())


@router.get("/players")
def players(limit: int = 300) -> dict:
    try:
        o = svc.options_bundle()
    except (FileNotFoundError, OSError):
        raise to_http(FileNotFoundError())
    return {"players": o["players"][:limit], "total": len(o["players"])}


@router.get("/years")
def years() -> dict:
    try:
        o = svc.options_bundle()
    except (FileNotFoundError, OSError):
        raise to_http(FileNotFoundError())
    ys = o["years"]
    return {"years": ys, "default": ys[-1] if ys else None}
