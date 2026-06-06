"""PostgreSQL-backed prediction history store."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    desc,
    func,
    insert,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

from api.schemas import PredictRequest

logger = logging.getLogger(__name__)

metadata = MetaData()

prediction_history = Table(
    "prediction_history",
    metadata,
    Column("id", Text, primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False, index=True),
    Column("map", Text, nullable=False, index=True),
    Column("cutoff_year", Integer, nullable=False, index=True),
    Column("predicted_winner", Text, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("team_a_name", Text, nullable=False),
    Column("team_b_name", Text, nullable=False),
    Column("team_a_win_probability", Float, nullable=False),
    Column("team_b_win_probability", Float, nullable=False),
    Column("request_json", JSONB, nullable=False),
    Column("response_json", JSONB, nullable=False),
)


class HistoryUnavailable(RuntimeError):
    """Raised when the history database is not configured or reachable."""


def _normalize_database_url(raw: str) -> str:
    if raw.startswith("postgres://"):
        return f"postgresql+psycopg2://{raw.removeprefix('postgres://')}"
    if raw.startswith("postgresql://"):
        return f"postgresql+psycopg2://{raw.removeprefix('postgresql://')}"
    return raw


@lru_cache(maxsize=1)
def database_url() -> str | None:
    raw = os.getenv("VALO_DATABASE_URL") or os.getenv("DATABASE_URL")
    return _normalize_database_url(raw.strip()) if raw and raw.strip() else None


@lru_cache(maxsize=1)
def engine() -> Engine | None:
    url = database_url()
    if not url:
        return None
    return create_engine(url, pool_pre_ping=True, future=True)


def _require_engine() -> Engine:
    eng = engine()
    if eng is None:
        raise HistoryUnavailable(
            "PostgreSQL 연결값이 없습니다. VALO_DATABASE_URL 또는 DATABASE_URL을 설정하세요."
        )
    return eng


def init_store() -> bool:
    """Create the history table when PostgreSQL is configured."""
    eng = engine()
    if eng is None:
        logger.info("prediction history skipped: database URL is not configured")
        return False
    try:
        metadata.create_all(eng)
    except Exception as exc:
        logger.warning("prediction history table init skipped: %s", exc)
        return False
    return True


def save_prediction(req: PredictRequest, response: dict[str, Any]) -> dict[str, Any] | None:
    """Persist a successful custom prediction. Prediction requests must not fail on DB issues."""
    eng = engine()
    if eng is None:
        return None

    now = datetime.now(timezone.utc)
    history_id = str(uuid4())
    response_with_history = {
        **response,
        "history_id": history_id,
        "created_at": now.isoformat(),
    }
    team_a = response.get("team_a") or {}
    team_b = response.get("team_b") or {}

    row = {
        "id": history_id,
        "created_at": now,
        "map": str(response.get("map") or req.map),
        "cutoff_year": int(response.get("cutoff_year") or req.cutoff_year),
        "predicted_winner": str(response.get("predicted_winner") or ""),
        "confidence": float(response.get("confidence") or 0.0),
        "team_a_name": str(team_a.get("name") or "팀 A"),
        "team_b_name": str(team_b.get("name") or "팀 B"),
        "team_a_win_probability": float(team_a.get("win_probability") or 0.0),
        "team_b_win_probability": float(team_b.get("win_probability") or 0.0),
        "request_json": req.model_dump(mode="json"),
        "response_json": response_with_history,
    }

    try:
        with eng.begin() as conn:
            conn.execute(insert(prediction_history).values(row))
    except Exception as exc:
        logger.warning("prediction history save skipped: %s", exc)
        return None

    return {"history_id": history_id, "created_at": now.isoformat()}


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _slots(request_json: dict[str, Any], side: str, key: str) -> list[str]:
    slots = request_json.get(side) or []
    return [str(slot.get(key) or "") for slot in slots if isinstance(slot, dict)]


def _summary(row: dict[str, Any]) -> dict[str, Any]:
    request_json = row.get("request_json") or {}
    return {
        "id": row["id"],
        "created_at": _iso(row["created_at"]),
        "map": row["map"],
        "cutoff_year": row["cutoff_year"],
        "predicted_winner": row["predicted_winner"],
        "confidence": row["confidence"],
        "team_a_name": row["team_a_name"],
        "team_b_name": row["team_b_name"],
        "team_a_win_probability": row["team_a_win_probability"],
        "team_b_win_probability": row["team_b_win_probability"],
        "team_a_players": _slots(request_json, "team_a", "player"),
        "team_b_players": _slots(request_json, "team_b", "player"),
        "team_a_agents": _slots(request_json, "team_a", "agent"),
        "team_b_agents": _slots(request_json, "team_b", "agent"),
    }


def list_predictions(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    eng = _require_engine()
    safe_limit = min(max(int(limit), 1), 200)
    safe_offset = max(int(offset), 0)
    cols = [
        prediction_history.c.id,
        prediction_history.c.created_at,
        prediction_history.c.map,
        prediction_history.c.cutoff_year,
        prediction_history.c.predicted_winner,
        prediction_history.c.confidence,
        prediction_history.c.team_a_name,
        prediction_history.c.team_b_name,
        prediction_history.c.team_a_win_probability,
        prediction_history.c.team_b_win_probability,
        prediction_history.c.request_json,
    ]
    try:
        with eng.connect() as conn:
            total = conn.scalar(select(func.count()).select_from(prediction_history)) or 0
            rows = conn.execute(
                select(*cols)
                .order_by(desc(prediction_history.c.created_at))
                .limit(safe_limit)
                .offset(safe_offset)
            ).mappings()
            items = [_summary(dict(row)) for row in rows]
    except Exception as exc:
        raise HistoryUnavailable(f"PostgreSQL 히스토리를 읽지 못했습니다: {exc}") from exc
    return {"items": items, "total": int(total), "limit": safe_limit, "offset": safe_offset}


def get_prediction(history_id: str) -> dict[str, Any] | None:
    eng = _require_engine()
    try:
        with eng.connect() as conn:
            row = conn.execute(
                select(prediction_history).where(prediction_history.c.id == history_id)
            ).mappings().one_or_none()
    except Exception as exc:
        raise HistoryUnavailable(f"PostgreSQL 히스토리를 읽지 못했습니다: {exc}") from exc
    if row is None:
        return None

    data = dict(row)
    result = dict(data.get("response_json") or {})
    result["history_id"] = data["id"]
    result["created_at"] = _iso(data["created_at"])
    return {
        "item": _summary(data),
        "request": data.get("request_json") or {},
        "result": result,
    }
