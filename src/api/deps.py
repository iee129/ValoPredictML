"""inference.predict 예외 → HTTP 매핑. docs/08_web/02_backend_fastapi/01_app_structure.md §4."""
from __future__ import annotations

from fastapi import HTTPException


def to_http(exc: Exception) -> HTTPException:
    """ValueError → 422(입력 오류), FileNotFoundError → 503(산출물 부재)."""
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(
            status_code=503,
            detail="모델/데이터 산출물이 없습니다. docs/08_web/04_integration/02_demo_runbook.md §1 참조.",
        )
    return HTTPException(status_code=500, detail=str(exc))
