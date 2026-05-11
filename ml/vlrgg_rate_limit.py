from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


class VLRGGRateLimitError(RuntimeError):
    """Raised when VLR.gg or the local proxy asks the collector to slow down."""

    def __init__(
        self,
        message: str,
        *,
        url: str,
        status_code: int | None = None,
        retry_after: str | None = None,
        requests_made: int = 1,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.retry_after = retry_after
        self.requests_made = requests_made


def parse_retry_after_seconds(value: str | None, *, now: datetime | None = None) -> float | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return max(0.0, float(text))
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    baseline = now or datetime.now(timezone.utc)
    return max(0.0, (parsed - baseline).total_seconds())


def is_limit_like_response(status_code: int, headers: Any, body: str = "") -> bool:
    retry_after = ""
    try:
        retry_after = headers.get("Retry-After", "")
    except AttributeError:
        retry_after = ""
    if status_code == 429 or retry_after:
        return True
    if status_code not in {403, 503}:
        return False
    text = body[:2000].lower()
    return any(token in text for token in ("rate limit", "too many requests", "captcha", "cloudflare"))


def raise_for_limit_like_response(
    *,
    url: str,
    status_code: int,
    headers: Any,
    body: str = "",
    requests_made: int = 1,
) -> None:
    if not is_limit_like_response(status_code, headers, body):
        return
    retry_after = None
    try:
        retry_after = headers.get("Retry-After")
    except AttributeError:
        retry_after = None
    raise VLRGGRateLimitError(
        f"rate-limit response from {url}: status={status_code} retry_after={retry_after or '-'}",
        url=url,
        status_code=status_code,
        retry_after=retry_after,
        requests_made=requests_made,
    )
