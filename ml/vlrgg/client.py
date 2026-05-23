from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


class VLRGGRateLimitError(RuntimeError):
    def __init__(self, message, *, url, status_code=None, retry_after=None, requests_made=1):
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.retry_after = retry_after
        self.requests_made = requests_made


def parse_retry_after_seconds(value, *, now=None):
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


def _is_limit_like_response(status_code, headers, body=""):
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


def raise_for_limit_like_response(*, url, status_code, headers, body="", requests_made=1):
    if not _is_limit_like_response(status_code, headers, body):
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

logger = logging.getLogger(__name__)

DEFAULT_API_BASE_URL = "http://127.0.0.1:3001"
DEFAULT_API_VERSION = "v2"

# 지원 region 목록 (v2 기준)
REGIONS = ("na", "eu", "ap", "la", "la-s", "la-n", "oce", "mn", "gc", "br", "kr", "cn", "jp", "col")
TIMESPANS = ("30", "60", "90", "all")
PLAYER_TIMESPANS = ("30d", "60d", "90d", "all")


class VLRGGClient:
    """axsddlr/vlrggapi (https://github.com/axsddlr/vlrggapi) 클라이언트.

    rate_limit_per_second=1.0, 세션당 ≤5,000 요청 권장.

    사용 예시::

        client = VLRGGClient(cache_dir="data/raw/vlrgg/api_cache")
        stats = client.fetch_stats("na", "30")   # 선수 통계
        events = client.fetch_events("completed") # 이벤트 목록
        rankings = client.fetch_rankings("na")    # 랭킹

    """

    def __init__(
        self,
        rate_limit_per_second: float = 1.0,
        cache_dir: str | None = None,
        base_url: str | None = None,
        cache_only: bool = False,
        api_version: str = DEFAULT_API_VERSION,
    ) -> None:
        self._min_interval = 1.0 / max(rate_limit_per_second, 1e-6)
        self._last_request_time: float = 0.0
        self._cache_dir: Path | None = Path(cache_dir) if cache_dir else None
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = (base_url or os.getenv("VLRGG_API_BASE_URL") or DEFAULT_API_BASE_URL).rstrip("/")
        self.api_version = api_version.strip("/")
        self.cache_only = cache_only
        self.last_cache_hit = False
        self.request_count = 0
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": "ValoPredicML/1.0 (academic research; non-commercial)"}
        )

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        wait = self._min_interval - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_time = time.monotonic()

    def _cache_path(self, key: str) -> Path | None:
        if self._cache_dir is None:
            return None
        safe = re.sub(r"[^\w\-]", "_", key)
        return self._cache_dir / f"{safe}.json"

    def _load_cache(self, key: str) -> dict | None:
        path = self._cache_path(key)
        if path and path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def _save_cache(self, key: str, data: dict) -> None:
        path = self._cache_path(key)
        if path:
            tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
            try:
                tmp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                os.replace(tmp_path, path)
            except Exception as exc:
                logger.warning("캐시 저장 실패 (%s): %s", key, exc)
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    @staticmethod
    def cache_key(path: str, params: dict | None = None) -> str:
        if not params:
            return path
        return path + "?" + urlencode(sorted(params.items()))

    @staticmethod
    def extract_data(raw: Any) -> Any:
        """Return the useful V2 payload while keeping older cache shapes usable."""
        if not isinstance(raw, dict):
            return raw
        data = raw.get("data", raw)
        if isinstance(data, dict) and set(data.keys()) == {"segments"}:
            return data.get("segments")
        return data

    @staticmethod
    def extract_segments(raw: Any) -> list[dict] | None:
        """Return a v2 segment list while keeping older unversioned cache support."""
        if raw is None:
            return None
        data = VLRGGClient.extract_data(raw)
        if isinstance(data, dict):
            segments = data.get("segments", data.get("results", data.get("matches")))
            return segments if isinstance(segments, list) else None
        return data if isinstance(data, list) else None

    def _versioned_path(self, path: str) -> str:
        if not self.api_version or path.startswith(f"/{self.api_version}/"):
            return path
        return f"/{self.api_version}{path if path.startswith('/') else '/' + path}"

    def _unversioned_path(self, path: str) -> str:
        prefix = f"/{self.api_version}/"
        if self.api_version and path.startswith(prefix):
            return "/" + path[len(prefix):]
        return path

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        request_path = self._versioned_path(path)
        cache_key = self.cache_key(request_path, params)
        self.last_cache_hit = False
        cache_keys = [cache_key]
        legacy_key = self.cache_key(self._unversioned_path(request_path), params)
        if legacy_key != cache_key:
            cache_keys.append(legacy_key)
        for candidate in cache_keys:
            cached = self._load_cache(candidate)
            if cached is not None:
                self.last_cache_hit = True
                return cached
        if self.cache_only:
            return None

        self._throttle()
        url = f"{self.base_url}{request_path}"
        try:
            resp = self._session.get(url, params=params, timeout=15)
            self.request_count += 1
            raise_for_limit_like_response(
                url=resp.url,
                status_code=resp.status_code,
                headers=resp.headers,
                body=resp.text,
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            self._save_cache(cache_key, data)
            return data
        except VLRGGRateLimitError:
            raise
        except requests.exceptions.HTTPError as exc:
            logger.warning("HTTP 오류 [%s]: %s", url, exc)
        except requests.exceptions.ConnectionError as exc:
            logger.warning("연결 실패 [%s]: %s", url, exc)
        except requests.exceptions.Timeout:
            logger.warning("요청 타임아웃 [%s]", url)
        except Exception as exc:
            logger.warning("예기치 않은 오류 [%s]: %s", url, exc)
        return None

    # ------ Public API ------

    def fetch_stats(self, region: str, timespan: str = "30") -> list[dict] | None:
        """지역별 선수 통계를 가져옵니다.

        Args:
            region: 'na', 'eu', 'ap', 'la', 'kr' 등
            timespan: '30', '60', '90', 'all'

        Returns:
            선수 통계 리스트. 컬럼: player, org, agents, rounds_played,
            rating, average_combat_score, kill_deaths, headshot_percentage 등
        """
        raw = self._get("/stats", {"region": region, "timespan": timespan})
        return self.extract_segments(raw)

    def fetch_events(self, q: str = "completed", page: int = 1) -> list[dict] | None:
        """이벤트 목록을 가져옵니다.

        Args:
            q: 'completed' 또는 'upcoming'
            page: 페이지 번호 (completed에만 적용)

        Returns:
            이벤트 리스트. 컬럼: title, status, prize, dates, region, url_path
            url_path 예시: 'https://www.vlr.gg/event/2857/challengers-2026-...'
        """
        raw = self._get("/events", {"q": q, "page": page})
        return self.extract_segments(raw)

    def fetch_rankings(self, region: str) -> list[dict] | None:
        """지역별 팀 랭킹을 가져옵니다."""
        raw = self._get("/rankings", {"region": region})
        return self.extract_segments(raw)

    def fetch_health(self) -> dict | None:
        """API와 원천 VLR.gg 상태를 확인합니다."""
        return self._get("/health")

    def fetch_match(
        self,
        q: str,
        num_pages: int = 1,
        from_page: int | None = None,
        to_page: int | None = None,
    ) -> list[dict] | None:
        """매치 목록을 가져옵니다.

        Args:
            q: 'upcoming' 또는 'completed' 등 검색 쿼리
            num_pages: 스크래핑 페이지 수 (기본 1)
            from_page: 시작 페이지 (옵션)
            to_page: 종료 페이지 (옵션)
        """
        params: dict[str, Any] = {"q": q, "num_pages": num_pages}
        if from_page is not None:
            params["from_page"] = from_page
        if to_page is not None:
            params["to_page"] = to_page
        raw = self._get("/match", params)
        return self.extract_segments(raw)

    def fetch_match_details(self, match_id: str | int) -> dict | None:
        """매치 상세를 가져옵니다."""
        raw = self._get("/match/details", {"match_id": match_id})
        data = self.extract_data(raw)
        if isinstance(data, dict):
            segments = data.get("segments")
            if isinstance(segments, list):
                return segments[0] if segments and isinstance(segments[0], dict) else None
        return data if isinstance(data, dict) else None

    def fetch_news(self) -> list[dict] | None:
        """최신 발로란트 뉴스를 가져옵니다."""
        raw = self._get("/news")
        return self.extract_segments(raw)

    def fetch_event_detail(self, event_id: str | int) -> dict | None:
        """이벤트 상세를 가져옵니다."""
        raw = self._get(f"/event/{event_id}")
        data = self.extract_data(raw)
        if isinstance(data, dict) and isinstance(data.get("segments"), dict):
            return data["segments"]
        return data if isinstance(data, dict) else None

    def fetch_event_matches(self, event_id: str | int) -> list[dict] | None:
        """이벤트별 매치 목록을 가져옵니다."""
        raw = self._get("/events/matches", {"event_id": event_id})
        data = self.extract_data(raw)
        if isinstance(data, dict) and isinstance(data.get("matches"), list):
            return data["matches"]
        return self.extract_segments(raw)

    def fetch_search(self, q: str) -> dict | None:
        """검색 결과를 가져옵니다. 최대 수집 계획에서는 기본 사용하지 않습니다."""
        raw = self._get("/search", {"q": q})
        data = self.extract_data(raw)
        if isinstance(data, dict) and isinstance(data.get("segments"), dict):
            return data["segments"]
        return data if isinstance(data, dict) else None

    def fetch_player(self, player_id: str | int, timespan: str = "all") -> dict | None:
        """선수 프로필을 가져옵니다."""
        raw = self._get("/player", {"id": player_id, "timespan": timespan})
        data = self.extract_data(raw)
        return data if isinstance(data, dict) else None

    def fetch_player_matches(self, player_id: str | int, page: int = 1) -> list[dict] | None:
        """선수별 매치 목록을 가져옵니다."""
        raw = self._get("/player/matches", {"id": player_id, "page": page})
        data = self.extract_data(raw)
        if isinstance(data, dict) and isinstance(data.get("matches"), list):
            return data["matches"]
        return self.extract_segments(raw)

    def fetch_team(self, team_id: str | int) -> dict | None:
        """팀 프로필을 가져옵니다."""
        raw = self._get("/team", {"id": team_id})
        data = self.extract_data(raw)
        return data if isinstance(data, dict) else None

    def fetch_team_matches(self, team_id: str | int, page: int = 1) -> list[dict] | None:
        """팀별 매치 목록을 가져옵니다."""
        raw = self._get("/team/matches", {"id": team_id, "page": page})
        data = self.extract_data(raw)
        if isinstance(data, dict) and isinstance(data.get("matches"), list):
            return data["matches"]
        return self.extract_segments(raw)

    def fetch_team_transactions(self, team_id: str | int) -> list[dict] | None:
        """팀 로스터 트랜잭션을 가져옵니다."""
        raw = self._get("/team/transactions", {"id": team_id})
        data = self.extract_data(raw)
        if isinstance(data, dict) and isinstance(data.get("transactions"), list):
            return data["transactions"]
        return self.extract_segments(raw)

    @staticmethod
    def extract_match_id(url_path: str) -> str | None:
        """매치 URL에서 match_id를 추출합니다.

        예: '/314642/g2-esports-vs-...' 또는
        'https://www.vlr.gg/314642/g2-esports-vs-...' → '314642'
        """
        m = re.search(r"(?:vlr\.gg)?/(\d+)(?:/|$)", str(url_path or ""))
        return m.group(1) if m else None

    @staticmethod
    def extract_event_id(url_path: str) -> str | None:
        """이벤트 URL에서 event_id를 추출합니다.

        예: 'https://www.vlr.gg/event/2857/challengers-...' → '2857'
        """
        m = re.search(r"/event/(\d+)/", url_path)
        return m.group(1) if m else None
