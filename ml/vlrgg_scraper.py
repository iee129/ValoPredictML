"""VLR.gg 직접 스크래퍼 — akhilnarang/vlrgg-scraper 포팅 (동기식).

Redis·Firebase 없이 httpx + BeautifulSoup만으로 동작하는 경량 버전.
출처: https://github.com/akhilnarang/vlrgg-scraper (MIT License)
"""
from __future__ import annotations

import re
import time
import logging
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ml.vlrgg_rate_limit import VLRGGRateLimitError, raise_for_limit_like_response

logger = logging.getLogger(__name__)

_BASE = "https://www.vlr.gg"
_HEADERS = {
    "User-Agent": "ValoPredicML/1.0 (academic research; non-commercial)",
    "Accept-Language": "en-US,en;q=0.9",
}
_TIMEOUT = 20.0
ROBOTS_URL = "https://www.vlr.gg/robots.txt"
DISALLOWED_PATH_PREFIXES = ("/search/auto", "/rr")
DIRECT_HTML_ALLOWED_PATH_PREFIXES = (
    "/matches/results",
    "/event/stats/",
    "/event/agents/",
    "/team/",
    "/team/stats/",
    "/team/transactions/",
)


def assert_vlrgg_path_allowed(
    path_or_url: str,
    *,
    allowed_prefixes: tuple[str, ...] | None = None,
) -> None:
    """Reject paths disallowed by the current VLR.gg robots policy used here."""
    parsed = urlparse(path_or_url)
    path = parsed.path if parsed.scheme else path_or_url
    for prefix in DISALLOWED_PATH_PREFIXES:
        if path.startswith(prefix):
            raise ValueError(f"direct VLR.gg fetch blocked for disallowed path: {path}")
    if allowed_prefixes and not any(path.startswith(prefix) for prefix in allowed_prefixes):
        raise ValueError(f"direct VLR.gg fetch outside collector allowlist: {path}")


def _get(
    url: str,
    delay: float = 1.0,
    *,
    allowed_prefixes: tuple[str, ...] | None = None,
) -> BeautifulSoup | None:
    """rate-limit 적용 동기 GET → BeautifulSoup."""
    assert_vlrgg_path_allowed(url, allowed_prefixes=allowed_prefixes)
    time.sleep(delay)
    try:
        with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as c:
            r = c.get(url)
            raise_for_limit_like_response(
                url=str(r.url),
                status_code=r.status_code,
                headers=r.headers,
                body=r.text,
            )
            r.raise_for_status()
            return BeautifulSoup(r.content, "lxml")
    except VLRGGRateLimitError:
        raise
    except Exception as exc:
        logger.warning("fetch 실패 [%s]: %s", url, exc)
        return None


def _squash_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _node_text(el, sep: str = " ") -> str:
    return _squash_text(el.get_text(sep, strip=True)) if el else ""


def _first_int_text(text: str) -> int | None:
    match = re.search(r"-?\d+", str(text or "").replace(",", ""))
    return int(match.group(0)) if match else None


def _extract_path_id(href: str, prefix: str) -> str | None:
    match = re.search(rf"/{re.escape(prefix)}/(\d+)(?:/|$)", str(href or ""))
    return match.group(1) if match else None


def _extract_country_code(el) -> str:
    if not el:
        return ""
    flag = el.find("i", class_=lambda cls: cls and "flag" in str(cls))
    classes = flag.get("class", []) if flag else []
    for cls in classes:
        if isinstance(cls, str) and cls.startswith("mod-"):
            return cls.removeprefix("mod-").upper()
    return ""


def _member_type_for_roster_item(item) -> str:
    for label in item.find_all_previous("div", class_="wf-label"):
        text = _node_text(label).lower()
        if "staff" in text:
            return "staff"
        if "player" in text:
            return "player"
    return "player"


def _parse_roster_items(soup: BeautifulSoup) -> list[dict]:
    rows: list[dict] = []
    for item in soup.select(".team-roster-item"):
        link = item.find("a", href=lambda href: bool(href and "/player/" in href))
        href = str(link.get("href", "") if link else "")
        player_id = _extract_path_id(href, "player")
        player = _node_text(item.select_one(".team-roster-item-name-alias")) or _node_text(link)
        real_name = _node_text(item.select_one(".team-roster-item-name-real"))
        role = _node_text(item.select_one(".team-roster-item-name-role"))
        if not player and not real_name:
            continue
        rows.append({
            "member_type": _member_type_for_roster_item(item),
            "player_id": player_id or "",
            "player": player,
            "real_name": real_name,
            "role": role,
            "status": "active",
            "url_path": href,
        })
    return rows


def _parse_rating_summary(soup: BeautifulSoup) -> dict:
    card = soup.select_one(".wf-card.mod-rating") or soup
    active_core = card.select_one(".team-core-block.mod-active") or card
    core_label = _node_text(card.select_one(".wf-ps-select-menu-value"))
    core_numeric_id = str(active_core.get("data-core-id", "") or "")
    rank_el = active_core.select_one(".team-rating-info-section.mod-rank .rank-num")
    region_el = active_core.select_one(".team-rating-info-section.mod-rank .rating-txt")
    rating_el = active_core.select_one(".team-rating-info-section.mod-rating .rating-num")
    record_el = active_core.select_one(".team-rating-info-section.mod-streak .rating-num")
    return {
        "core_id": core_label,
        "core_numeric_id": core_numeric_id,
        "rank": _first_int_text(_node_text(rank_el)),
        "region": _node_text(region_el),
        "current_rating": _first_int_text(_node_text(rating_el)),
        "record": _node_text(record_el),
    }


def _rating_history_href(soup: BeautifulSoup, point_id: str) -> tuple[str, str]:
    if not point_id:
        return "", ""
    marker = soup.select_one(f'[data-pt-id="{point_id}"][onclick]')
    onclick = str(marker.get("onclick", "") if marker else "")
    match = re.search(r"href=['\"]([^'\"]+)['\"]", onclick)
    href = match.group(1) if match else ""
    match_id = _extract_path_id(href, "") if href else None
    if match_id is None and href:
        id_match = re.search(r"/(\d+)(?:/|$)", href)
        match_id = id_match.group(1) if id_match else None
    return href, match_id or ""


def _parse_rating_result(text: str) -> tuple[str, int | None, int | None, int | None]:
    normalized = (
        str(text or "")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\xa0", " ")
    )
    result_match = re.search(r"\b(Win|Loss|Draw)\b\s*([+-]\d+)?", normalized, flags=re.I)
    result = result_match.group(1).title() if result_match else ""
    delta = int(result_match.group(2)) if result_match and result_match.group(2) else None
    rating_after = opponent_rating = None
    rating_match = re.search(r"-\s*(\d+|Unrated)\s+vs\.?\s+(\d+|Unrated)", normalized, flags=re.I)
    if rating_match:
        rating_after = int(rating_match.group(1)) if rating_match.group(1).isdigit() else None
        opponent_rating = int(rating_match.group(2)) if rating_match.group(2).isdigit() else None
    return result, delta, rating_after, opponent_rating


def _parse_rating_history(soup: BeautifulSoup) -> list[dict]:
    active_core = soup.select_one(".team-core-block.mod-active")
    tips = active_core.select(".tip[data-pt-id]") if active_core else []
    if not tips:
        tips = soup.select(".tip[data-pt-id]")
    rows: list[dict] = []
    for sequence, tip in enumerate(tips, start=1):
        children = tip.find_all("div", recursive=False)
        date = _node_text(children[0]) if children else ""
        title = _node_text(tip.select_one(".tip-title"))
        opponent = re.sub(r"^vs\.?\s*", "", title, flags=re.I).strip()
        event = _node_text(children[2]) if len(children) > 2 else ""
        result_text = _node_text(tip.select_one(".result"))
        result, rating_delta, rating_after, opponent_rating = _parse_rating_result(result_text)
        href, match_id = _rating_history_href(soup, str(tip.get("data-pt-id", "") or ""))
        rows.append({
            "sequence": sequence,
            "date": date,
            "opponent": opponent,
            "event": event,
            "result": result,
            "rating_delta": rating_delta,
            "rating_after": rating_after,
            "opponent_rating": opponent_rating,
            "raw_text": _node_text(tip),
            "match_id": match_id,
            "url_path": href,
        })
    return rows


def _parse_score_pair(result_el) -> tuple[int | None, int | None]:
    if not result_el:
        return None, None
    scores = [_first_int_text(_node_text(span)) for span in result_el.find_all("span", recursive=False)]
    scores = [score for score in scores if score is not None]
    return (scores[0], scores[1]) if len(scores) >= 2 else (None, None)


def _parse_team_matches(soup: BeautifulSoup, team_name: str) -> list[dict]:
    rows: list[dict] = []
    page_team = _squash_text(team_name).lower()
    for card in soup.select("a.wf-card.m-item"):
        classes = set(card.get("class", []))
        if "m-item-games-item" in classes:
            continue
        href = str(card.get("href", "") or "")
        match = re.search(r"/(\d+)(?:/|$)", href)
        event_el = card.select_one(".m-item-event")
        event = _node_text(event_el.select_one(".text-of")) if event_el else ""
        event_text = _node_text(event_el)
        round_info = _squash_text(event_text.replace(event, "", 1).strip(" -\u00b7")) if event else event_text
        date = _node_text(card.select_one(".m-item-date"))
        teams = [_node_text(el) for el in card.select(".m-item-team-name") if _node_text(el)]
        result_el = card.select_one(".m-item-result")
        score_a, score_b = _parse_score_pair(result_el)
        status_classes = set(result_el.get("class", []) if result_el else [])
        status = "upcoming"
        if "mod-win" in status_classes:
            status = "win"
        elif "mod-loss" in status_classes:
            status = "loss"
        elif score_a is not None and score_b is not None:
            status = "completed"
        team_idx = 0
        if len(teams) >= 2 and page_team:
            normalized = [team.lower() for team in teams]
            if normalized[1] == page_team or page_team in normalized[1]:
                team_idx = 1
        opponent = ""
        score_for = score_against = None
        if len(teams) >= 2:
            opponent = teams[1 - team_idx]
            if team_idx == 0:
                score_for, score_against = score_a, score_b
            else:
                score_for, score_against = score_b, score_a
        rows.append({
            "match_id": match.group(1) if match else "",
            "event": event,
            "date": date,
            "round_info": round_info,
            "opponent": opponent,
            "score_for": score_for,
            "score_against": score_against,
            "status": status,
            "url_path": href,
            "raw_text": _node_text(card),
        })
    return rows


def _parse_event_placements(soup: BeautifulSoup) -> list[dict]:
    rows: list[dict] = []
    for item in soup.select("a.team-event-item"):
        href = str(item.get("href", "") or "")
        rows.append({
            "event_id": _extract_path_id(href, "event") or "",
            "event": _node_text(item.select_one(".text-of")) or _node_text(item),
            "series_results": [
                _node_text(span).replace("\u2013", "-").replace("\u2014", "-")
                for span in item.select(".team-event-item-series span")
                if _node_text(span)
            ],
            "year": _first_int_text(_node_text(item)),
            "url_path": href,
            "raw_text": _node_text(item),
        })
    return rows


def _parse_total_winnings(soup: BeautifulSoup) -> str:
    label = soup.find(string=lambda text: bool(text and "Total Winnings" in text))
    if not label:
        return ""
    node = label.find_parent()
    for _ in range(4):
        if not node:
            break
        spans = node.find_all("span")
        for span in spans:
            text = _node_text(span)
            if text and text != "Total Winnings":
                return text
        node = node.find_parent()
    return ""


def scrape_team_profile(team_id: int | str, delay: float = 1.0) -> dict:
    """Scrape public team profile facts from /team/{team_id}.

    This parser intentionally stays on the profile page and returns normalized
    public facts for downstream CSV materialization.
    """
    team_id_str = str(team_id)
    url = f"{_BASE}/team/{team_id_str}"
    soup = _get(url, delay=delay, allowed_prefixes=DIRECT_HTML_ALLOWED_PATH_PREFIXES)
    if soup is None:
        return {}

    name = _node_text(soup.select_one(".team-header-desc h1.wf-title")) or _node_text(soup.select_one("h1.wf-title"))
    tag = _node_text(soup.select_one(".team-header-tag"))
    country_el = soup.select_one(".team-header-country")
    country = _node_text(country_el)
    rating = _parse_rating_summary(soup)
    roster = _parse_roster_items(soup)
    rating_history = _parse_rating_history(soup)
    recent_matches = _parse_team_matches(soup, name)
    event_placements = _parse_event_placements(soup)

    logger.info(
        "team %s profile: roster=%d rating_history=%d matches=%d placements=%d",
        team_id_str,
        len(roster),
        len(rating_history),
        len(recent_matches),
        len(event_placements),
    )
    return {
        "team_id": team_id_str,
        "team": name,
        "tag": tag,
        "country": country,
        "country_code": _extract_country_code(country_el),
        "region": rating.get("region"),
        "rank": rating.get("rank"),
        "current_rating": rating.get("current_rating"),
        "record": rating.get("record"),
        "core_id": rating.get("core_id"),
        "core_numeric_id": rating.get("core_numeric_id"),
        "roster": roster,
        "rating_history": rating_history,
        "recent_matches": recent_matches,
        "event_placements": event_placements,
        "total_winnings": _parse_total_winnings(soup),
        "url_path": f"/team/{team_id_str}",
    }


def scrape_recent_results(page: int = 1, delay: float = 1.0) -> list[dict]:
    """Scrape the public results listing only.

    This intentionally collects match-card metadata, not detailed match pages.
    It is the direct-HTML fallback for small research coverage checks.
    """
    url = f"{_BASE}/matches/results?page={page}"
    soup = _get(url, delay=delay, allowed_prefixes=DIRECT_HTML_ALLOWED_PATH_PREFIXES)
    if soup is None:
        return []

    rows: list[dict] = []
    for card in soup.find_all("a", class_="match-item"):
        href = card.get("href", "")
        match_id = None
        m = re.search(r"/(\d+)/", href)
        if m:
            match_id = m.group(1)

        teams = card.find_all("div", class_="match-item-vs-team-name")
        scores = card.find_all("div", class_="match-item-vs-team-score")
        event_el = card.find("div", class_="match-item-event")
        time_el = card.find("div", class_="match-item-time")
        status_el = card.find("div", class_="match-item-eta")

        rows.append({
            "match_id": match_id,
            "team_a": teams[0].get_text(strip=True) if len(teams) > 0 else "",
            "team_b": teams[1].get_text(strip=True) if len(teams) > 1 else "",
            "score_a": _parse_score(scores[0]) if len(scores) > 0 else None,
            "score_b": _parse_score(scores[1]) if len(scores) > 1 else None,
            "event": event_el.get_text(" ", strip=True) if event_el else "",
            "date": time_el.get_text(" ", strip=True) if time_el else "",
            "status": status_el.get_text(" ", strip=True) if status_el else "",
            "url_path": href,
        })

    logger.info("recent results page %d: %d matches collected", page, len(rows))
    return rows


def scrape_standings(year: int) -> list[dict]:
    """VCT 연도별 팀 스탠딩을 스크래핑합니다.

    URL: https://www.vlr.gg/vct-{year}/standings

    Returns:
        [{"region": "EMEA", "rank": 1, "team": "...", "team_id": 123,
          "points": 500, "country": "DE"}, ...]
    """
    soup = _get(f"{_BASE}/vct-{year}/standings", allowed_prefixes=(f"/vct-{year}/standings",))
    if soup is None:
        return []

    rows: list[dict] = []
    for group in soup.find_all("div", class_="eg-standing-group"):
        region_el = group.find("div", class_="wf-label")
        region = region_el.get_text(strip=True) if region_el else "Unknown"
        table = group.find("table")
        if not table:
            continue
        rank = 1
        for row in table.find_all("tr")[1:]:
            team_td = row.find("td", class_="eg-standing-group-team")
            if not team_td:
                continue
            a = team_td.find("a")
            if not a:
                continue
            href = a.get("href", "")
            m = re.search(r"/team/(\d+)/", href)
            team_id = int(m.group(1)) if m else None
            name_div = a.find("div", class_="text-of")
            if name_div:
                divs = name_div.find_all("div", recursive=False)
                name = divs[0].get_text(strip=True) if divs else ""
                country = divs[1].get_text(strip=True) if len(divs) > 1 else ""
            else:
                name, country = "", ""
            pts_tds = row.find_all("td")
            points_str = pts_tds[1].get_text(strip=True).split()[0] if len(pts_tds) > 1 else "0"
            try:
                points = int(points_str)
            except ValueError:
                points = 0
            rows.append({
                "year": year,
                "region": region,
                "rank": rank,
                "team": name,
                "team_id": team_id,
                "points": points,
                "country": country,
            })
            rank += 1

    if not rows:
        logger.warning("standings %d: 0팀 — JS 렌더링 페이지이거나 URL 형식이 다를 수 있음", year)
    else:
        logger.info("standings %d: %d팀 수집", year, len(rows))
    return rows


def _extract_agents(rows: list) -> list[str]:
    out = []
    for row in rows:
        td = row.find("td", class_="mod-agents")
        if not td:
            continue
        img = td.find("img", src=lambda s: s and "/agents/" in s if s else False)
        if img:
            m = re.search(r"/agents/(\w+)\.png", img.get("src", ""))
            if m:
                out.append(m.group(1))
    return out


def _parse_score(el) -> int | None:
    try:
        return int(el.get_text(strip=True))
    except (ValueError, AttributeError):
        return None


def _parse_side_stat(td) -> tuple[str, str, str]:
    """stats-sq span에서 (overall, t_side, ct_side) 텍스트를 추출합니다."""
    sq = td.find("span", class_="stats-sq")
    if not sq:
        return "", "", ""
    both = sq.find("span", class_="mod-both")
    t_side = sq.find("span", class_="mod-t")
    ct_side = sq.find("span", class_="mod-ct")
    def _text(el) -> str:
        return el.get_text(strip=True).replace("%", "") if el else ""
    return _text(both), _text(t_side), _text(ct_side)


def _to_num(s: str) -> int | float | None:
    s = s.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def _cell_text(cell) -> str:
    return cell.get_text(" ", strip=True) if cell else ""


def _agent_from_img(img) -> str:
    if not img:
        return ""
    for attr in ("alt", "title"):
        text = str(img.get(attr, "") or "").strip()
        if text:
            text = re.sub(r"^image:\s*", "", text, flags=re.I).strip()
            if text:
                return text
    src = str(img.get("src", "") or "")
    m = re.search(r"/agents/([A-Za-z0-9_-]+)\.png", src)
    return m.group(1) if m else ""


def _agents_from_cell(cell) -> list[str]:
    agents: list[str] = []
    for img in cell.find_all("img", src=lambda s: s and "/agents/" in s if s else False):
        agent = _agent_from_img(img)
        if agent and agent not in agents:
            agents.append(agent)
    return agents


def _player_team_from_cell(cell) -> tuple[str, str]:
    text = _cell_text(cell)
    player_link = cell.find("a", href=lambda href: href and "/player/" in href)
    team_link = cell.find("a", href=lambda href: href and "/team/" in href)
    player = _cell_text(player_link) if player_link else ""
    team = _cell_text(team_link) if team_link else ""
    if player and not team:
        rest = text.replace(player, "", 1).strip()
        team = rest.split()[0] if rest else ""
    if not player:
        parts = text.split()
        if len(parts) > 1:
            player = " ".join(parts[:-1])
            team = team or parts[-1]
        else:
            player = text
    return player, team


def _data_rows(table) -> list:
    body = table.find("tbody")
    return body.find_all("tr") if body else table.find_all("tr")[1:]


def scrape_event_player_stats(event_id: int | str, delay: float = 1.0) -> list[dict]:
    """Scrape static event player stats from the public event stats table."""
    url = f"{_BASE}/event/stats/{event_id}/?series_id=all"
    soup = _get(url, delay=delay, allowed_prefixes=("/event/stats/",))
    if soup is None:
        return []

    rows: list[dict] = []
    for table in soup.find_all("table"):
        header_text = " ".join(_cell_text(cell) for cell in table.find_all(["th", "td"])[:24])
        if "ACS" not in header_text or "K:D" not in header_text:
            continue
        for tr in _data_rows(table):
            cells = tr.find_all("td")
            if len(cells) < 14:
                continue
            player, team = _player_team_from_cell(cells[0])
            if not player:
                continue
            agents = _agents_from_cell(cells[1]) or [""]
            base = {
                "player": player,
                "team": team,
                "map_key": "",
                "rounds_played": _to_num(_cell_text(cells[2])),
                "rating": _to_num(_cell_text(cells[3])),
                "average_combat_score": _to_num(_cell_text(cells[4])),
                "kill_deaths": _to_num(_cell_text(cells[5])),
                "average_damage_per_round": _to_num(_cell_text(cells[7])),
                "kills_per_round": _to_num(_cell_text(cells[8])),
                "assists_per_round": _to_num(_cell_text(cells[9])),
                "first_kills_per_round": _to_num(_cell_text(cells[10])),
                "first_deaths_per_round": _to_num(_cell_text(cells[11])),
                "headshot_percentage": _cell_text(cells[12]),
                "clutch_success_percentage": _cell_text(cells[13]),
            }
            for agent in agents:
                rows.append({**base, "agent": agent})

    logger.info("event %s: %d player stat rows collected", event_id, len(rows))
    return rows


def _map_name_from_agent_row(text: str) -> str:
    text = text.strip()
    m = re.match(r"^[A-Z]\s+(.+)$", text)
    return m.group(1).strip() if m else text


def _agent_metric(text: str) -> dict[str, int | float | str | None]:
    clean = text.strip()
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", clean)
    count_match = re.search(r"\d+(?:\.\d+)?", clean)
    use_rate = float(pct_match.group(1)) if pct_match else None
    use_count = None
    if count_match and (not pct_match or count_match.group(0) != pct_match.group(1)):
        parsed = _to_num(count_match.group(0))
        use_count = int(parsed) if isinstance(parsed, int) or (isinstance(parsed, float) and parsed.is_integer()) else parsed
    return {"raw_value": clean, "use_count": use_count, "use_rate": use_rate}


def scrape_event_agent_usage(event_id: int | str, delay: float = 1.0) -> list[dict]:
    """Scrape static event agent pick-rate rows from the public agent table."""
    url = f"{_BASE}/event/agents/{event_id}/?series_id=all"
    soup = _get(url, delay=delay, allowed_prefixes=("/event/agents/",))
    if soup is None:
        return []

    rows: list[dict] = []
    for table in soup.find_all("table"):
        header_row = table.find("thead").find("tr") if table.find("thead") else table.find("tr")
        if not header_row:
            continue
        header_cells = header_row.find_all(["th", "td"])
        agent_columns = [
            (idx, _agent_from_img(cell.find("img")))
            for idx, cell in enumerate(header_cells)
        ]
        agent_columns = [(idx, agent) for idx, agent in agent_columns if agent]
        if not agent_columns:
            continue
        for tr in _data_rows(table):
            cells = tr.find_all("td")
            if len(cells) < 5:
                continue
            map_name = _map_name_from_agent_row(_cell_text(cells[0]))
            if not map_name:
                continue
            map_count = _to_num(_cell_text(cells[1])) if len(cells) > 1 else None
            atk_win = _cell_text(cells[2]) if len(cells) > 2 else ""
            def_win = _cell_text(cells[3]) if len(cells) > 3 else ""
            for idx, agent in agent_columns:
                if idx >= len(cells):
                    continue
                metric_text = _cell_text(cells[idx])
                if not metric_text:
                    continue
                metric = _agent_metric(metric_text)
                rows.append({
                    "map": map_name,
                    "agent": agent,
                    "use_count": metric["use_count"],
                    "use_rate": metric["use_rate"],
                    "rounds_played": map_count,
                    "win_rate": None,
                    "raw_metric": {
                        **metric,
                        "map_count": map_count,
                        "atk_win": atk_win,
                        "def_win": def_win,
                    },
                })

    logger.info("event %s: %d agent usage rows collected", event_id, len(rows))
    return rows


def _int_span(el) -> int:
    try:
        return int(el.get_text(strip=True)) if el else 0
    except ValueError:
        return 0


def _extract_team_sides(game_div) -> dict:
    """게임 div에서 팀별 선공/후공 및 ATK/DEF 라운드 수를 추출합니다."""
    team_divs = [
        t for t in game_div.find_all("div", class_="team")
        if t.find("div", class_="team-name")
        and t.find("div", class_="team-name").get_text(strip=True)
    ]

    sides: dict = {}
    first_atk = ""
    for t in team_divs[:2]:
        is_right = "mod-right" in (t.get("class") or [])
        key = "b" if is_right else "a"
        name = t.find("div", class_="team-name").get_text(strip=True)
        if not is_right:
            first_atk = name
        sides[f"atk_rounds_{key}"] = _int_span(t.find("span", class_="mod-t"))
        sides[f"def_rounds_{key}"] = _int_span(t.find("span", class_="mod-ct"))
        sides[f"ot_rounds_{key}"] = _int_span(t.find("span", class_="mod-ot"))
    sides["first_atk"] = first_atk
    return sides


def _extract_player_stats(rows: list) -> list[dict]:
    """선수 tr 행에서 ATK/DEF 스플릿 통계를 포함한 선수 데이터를 추출합니다."""
    players = []
    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 14:
            continue
        player = tds[0].get_text(strip=True)
        img = tds[1].find("img", src=lambda s: s and "/agents/" in s if s else False)
        agent = ""
        if img:
            m = re.search(r"/agents/(\w+)\.png", img.get("src", ""))
            agent = m.group(1) if m else ""
        rat_all, _, _ = _parse_side_stat(tds[2])
        acs_all, _, _ = _parse_side_stat(tds[3])
        k_all, k_atk, k_def = _parse_side_stat(tds[4])
        d_all, d_atk, d_def = _parse_side_stat(tds[5])
        a_all, _, _ = _parse_side_stat(tds[6])
        kast_all, _, _ = _parse_side_stat(tds[8])
        adr_all, _, _ = _parse_side_stat(tds[9])
        hs_all, _, _ = _parse_side_stat(tds[10])
        fb_all, _, _ = _parse_side_stat(tds[11])
        fd_all, _, _ = _parse_side_stat(tds[12])
        players.append({
            "player": player,
            "agent": agent,
            "rating": _to_num(rat_all),
            "acs": _to_num(acs_all),
            "kills": _to_num(k_all),
            "deaths": _to_num(d_all),
            "assists": _to_num(a_all),
            "kast": _to_num(kast_all),
            "adr": _to_num(adr_all),
            "hs_pct": _to_num(hs_all),
            "fb": _to_num(fb_all),
            "fd": _to_num(fd_all),
            "atk_kills": _to_num(k_atk),
            "def_kills": _to_num(k_def),
            "atk_deaths": _to_num(d_atk),
            "def_deaths": _to_num(d_def),
        })
    return players


def scrape_match_detail(match_id: int | str) -> list[dict]:
    """매치 상세 페이지에서 게임별 데이터를 스크래핑합니다.

    URL: https://www.vlr.gg/{match_id}

    Returns:
        [{"match_id": "...", "game_id": "...", "map": "Pearl",
          "team_a": "...", "team_b": "...",
          "first_atk": "team_a_name",
          "atk_rounds_a": 7, "def_rounds_a": 5, "ot_rounds_a": 2,
          "atk_rounds_b": 7, "def_rounds_b": 5, "ot_rounds_b": 0,
          "agents_a": ["astra", ...], "agents_b": ["cypher", ...],
          "players_a": [...], "players_b": [...]}, ...]
        game_id="all" 합산 섹션은 제외됩니다.
    """
    soup = _get(f"{_BASE}/{match_id}", allowed_prefixes=(f"/{match_id}",))
    if soup is None:
        return []

    team_els = soup.find_all("div", class_="match-header-link-name")
    team_a = team_els[0].get_text(strip=True) if len(team_els) > 0 else ""
    team_b = team_els[1].get_text(strip=True) if len(team_els) > 1 else ""

    results: list[dict] = []
    for game in soup.find_all("div", class_="vm-stats-game", attrs={"data-game-id": True}):
        game_id = game.get("data-game-id", "")
        if game_id == "all":
            continue

        map_el = game.find("div", class_="map")
        raw_map = map_el.get_text(strip=True) if map_el else ""
        m_map = re.match(r"([A-Z][a-z]+)", raw_map)
        map_name = m_map.group(1) if m_map else raw_map

        rows = game.find_all("tr")
        if len(rows) < 12:
            logger.warning("match %s game %s: 행 수 %d < 12 (중도포기 경기 가능성) — 스킵", match_id, game_id, len(rows))
            continue

        sides = _extract_team_sides(game)
        agents_a = _extract_agents(rows[1:6])
        agents_b = _extract_agents(rows[7:12])
        players_a = _extract_player_stats(rows[1:6])
        players_b = _extract_player_stats(rows[7:12])

        results.append({
            "match_id": str(match_id),
            "game_id": game_id,
            "map": map_name,
            "team_a": team_a,
            "team_b": team_b,
            **sides,
            "agents_a": agents_a,
            "agents_b": agents_b,
            "players_a": players_a,
            "players_b": players_b,
        })

    logger.info("match %s: %d 게임 수집", match_id, len(results))
    return results


def scrape_team_stats(team_id: int | str) -> list[dict]:
    """팀 맵별 통계를 스크래핑합니다.

    URL: https://www.vlr.gg/team/stats/{team_id}

    Returns:
        [{"team_id": ..., "map": "Bind", "games": 34,
          "win_rate": 56, "wins": 19, "losses": 15,
          "atk_first": 16, "def_first": 18,
          "atk_rwin_pct": ..., "atk_rw": ..., "atk_rl": ...,
          "def_rwin_pct": ..., "def_rw": ..., "def_rl": ...}, ...]
    """
    soup = _get(f"{_BASE}/team/stats/{team_id}", allowed_prefixes=("/team/stats/",))
    if soup is None:
        return []

    table = soup.find("table", class_="mod-team-maps")
    if not table:
        logger.warning("team %s: mod-team-maps 테이블 없음 — JS 렌더링 가능성", team_id)
        return []

    def _cell(td) -> str:
        first = td.find("div", class_="mod-first") if td else None
        return first.get_text(strip=True) if first else (td.get_text(strip=True) if td else "")

    rows: list[dict] = []
    for tr in table.find("tbody").find_all("tr") if table.find("tbody") else []:
        map_td = tr.find("td", class_="mod-supercell")
        if not map_td:
            continue
        map_div = map_td.find("div", class_="mod-highlight")
        if not map_div:
            continue
        raw = map_div.get_text(strip=True)
        m_map = re.match(r"([A-Za-z]+)\s*\((\d+)\)", raw)
        if not m_map:
            continue
        map_name, games = m_map.group(1), int(m_map.group(2))

        cells = tr.find_all("td", class_="mod-supercell")
        def _val(idx: int) -> str:
            return _cell(cells[idx]) if idx < len(cells) else ""

        rows.append({
            "team_id": team_id,
            "map": map_name,
            "games": games,
            "win_rate": _to_num(_val(2).replace("%", "")),
            "wins": _to_num(_val(3)),
            "losses": _to_num(_val(4)),
            "atk_first": _to_num(_val(5)),
            "def_first": _to_num(_val(6)),
            "atk_rwin_pct": _to_num(_val(7).replace("%", "")),
            "atk_rw": _to_num(_val(8)),
            "atk_rl": _to_num(_val(9)),
            "def_rwin_pct": _to_num(_val(10).replace("%", "")),
            "def_rw": _to_num(_val(11)),
            "def_rl": _to_num(_val(12)),
        })

    logger.info("team %s: %d맵 통계 수집", team_id, len(rows))
    return rows


def scrape_event_matches(event_id: int | str, page: int = 1) -> list[dict]:
    """이벤트별 매치 목록을 스크래핑합니다.

    URL: https://www.vlr.gg/event/matches/{event_id}/?series_id=all&page={page}

    Returns:
        [{"match_id": "...", "team_a": "...", "team_b": "...",
          "score_a": 2, "score_b": 0, "date": "...", "event_id": ...}, ...]
    """
    url = f"{_BASE}/event/matches/{event_id}/?series_id=all&page={page}"
    soup = _get(url, allowed_prefixes=("/event/matches/",))
    if soup is None:
        return []

    rows: list[dict] = []
    for card in soup.find_all("a", class_="match-item"):
        href = card.get("href", "")
        m = re.search(r"/(\d+)/", href)
        match_id = m.group(1) if m else None

        teams = card.find_all("div", class_="match-item-vs-team-name")
        scores = card.find_all("div", class_="match-item-vs-team-score")

        team_a = teams[0].get_text(strip=True) if len(teams) > 0 else ""
        team_b = teams[1].get_text(strip=True) if len(teams) > 1 else ""

        score_a = _parse_score(scores[0]) if scores else None
        score_b = _parse_score(scores[1]) if len(scores) > 1 else None

        date_el = card.find("div", class_="match-item-time")
        date = date_el.get_text(strip=True) if date_el else ""

        rows.append({
            "event_id": event_id,
            "match_id": match_id,
            "team_a": team_a,
            "team_b": team_b,
            "score_a": score_a,
            "score_b": score_b,
            "date": date,
        })

    logger.info("event %s page %d: %d매치 수집", event_id, page, len(rows))
    return rows
