"""
VLR.gg 수집 데이터 전처리

data/raw/vlrgg/match/details.csv + compositions.csv
  → data/processed/vlrgg_matches.csv  (matches.csv 동일 포맷)

Usage:
    python -m ml.vlrgg.preprocess
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

DETAILS_CSV   = Path("data/raw/vlrgg/match/details.csv")
COMPS_CSV     = Path("data/raw/vlrgg/match/compositions.csv")
OUTPUT_CSV    = Path("data/processed/vlrgg_matches.csv")

FIELDNAMES = [
    "match_key", "dedup_key", "source", "source_priority",
    "date", "date_raw", "date_quality",
    "event", "map", "team_a", "team_b",
    "score_a", "score_b", "label",
    "agents_a", "agents_b", "provenance",
]

# API 응답에서 나오는 요원 이름 정규화 (compositions.csv도 같은 방식 적용)
_AGENT_ALIAS: dict[str, str] = {
    "kayo": "KAY/O", "kay/o": "KAY/O",
    "iso": "ISO",
}

def _norm_agent(name: str) -> str:
    key = name.strip().lower()
    return _AGENT_ALIAS.get(key, name.strip())

def _sha1(s: str, length: int) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:length]

def _is_iso_date(s: str) -> bool:
    return bool(re.match(r"\d{4}-\d{2}-\d{2}", s or ""))


def _load_compositions() -> dict[tuple[str, str], list[tuple[str, list[str]]]]:
    """(match_id, game_id) → [(team_name, sorted_agents), ...]"""
    comps: dict[tuple[str, str], list[tuple[str, list[str]]]] = {}
    with COMPS_CSV.open(newline="") as f:
        for row in csv.DictReader(f):
            key = (row["match_id"], row["game_id"])
            agents = sorted(_norm_agent(a) for a in row["agents"].split("|") if a.strip())
            comps.setdefault(key, []).append((row["team"], agents))
    return comps


def _match_team(player_agents: list[str],
                comp_list: list[tuple[str, list[str]]]) -> str:
    """에이전트 세트로 팀명 역방향 조회. 완전 일치 → 교집합 크기 순."""
    for team_name, comp_agents in comp_list:
        if player_agents == comp_agents:
            return team_name
    # 완전 일치 실패 시 교집합 최대 팀 선택
    best = max(comp_list, key=lambda x: len(set(x[1]) & set(player_agents)), default=None)
    return best[0] if best else ""


def main() -> None:
    print(f"compositions 로딩: {COMPS_CSV}")
    comps = _load_compositions()
    print(f"  {len(comps):,} 개 (match_id, game_id) 키")

    rows: list[dict] = []
    skipped_no_score = 0
    skipped_no_players = 0
    skipped_draw = 0

    print(f"details 파싱: {DETAILS_CSV}")
    with DETAILS_CSV.open(newline="") as f:
        for detail in csv.DictReader(f):
            match_id = detail["match_id"]
            event    = detail.get("event", "") or ""
            date_raw = detail.get("date", "") or ""
            date     = date_raw if _is_iso_date(date_raw) else ""
            date_quality = "iso" if date else "missing"

            try:
                maps_data = json.loads(detail.get("maps_json") or "[]")
            except json.JSONDecodeError:
                continue

            for game_idx, m in enumerate(maps_data):
                if not isinstance(m, dict):
                    continue

                game_id  = f"{match_id}-{game_idx + 1}"
                map_name = (m.get("map_name") or m.get("map") or "").strip()
                score    = m.get("score") or {}
                players  = m.get("players") or {}

                if not isinstance(score, dict):
                    skipped_no_score += 1
                    continue

                score_t1 = score.get("team1") or 0
                score_t2 = score.get("team2") or 0

                try:
                    score_t1 = int(score_t1)
                    score_t2 = int(score_t2)
                except (TypeError, ValueError):
                    skipped_no_score += 1
                    continue

                if score_t1 == 0 and score_t2 == 0:
                    skipped_no_score += 1
                    continue

                if score_t1 == score_t2:
                    skipped_draw += 1
                    continue

                if not isinstance(players, dict):
                    skipped_no_players += 1
                    continue

                t1_raw = players.get("team1") or []
                t2_raw = players.get("team2") or []

                if not t1_raw or not t2_raw:
                    skipped_no_players += 1
                    continue

                t1_agents = sorted(_norm_agent(p.get("agent", "")) for p in t1_raw if p.get("agent"))
                t2_agents = sorted(_norm_agent(p.get("agent", "")) for p in t2_raw if p.get("agent"))

                if len(t1_agents) < 3 or len(t2_agents) < 3:
                    skipped_no_players += 1
                    continue

                # 팀명 역조회
                comp_key  = (match_id, game_id)
                comp_list = comps.get(comp_key, [])
                team_a = _match_team(t1_agents, comp_list)
                team_b = _match_team(t2_agents, comp_list)

                label = 1 if score_t1 > score_t2 else 0

                agents_a = "|".join(t1_agents)
                agents_b = "|".join(t2_agents)

                match_key = _sha1(f"vlrgg|{match_id}|{game_id}", 16)
                dedup_key = _sha1(
                    f"{date}|{event}|{map_name}|{team_a}|{agents_a}|{team_b}|{agents_b}|{score_t1}:{score_t2}",
                    24,
                )

                rows.append({
                    "match_key":      match_key,
                    "dedup_key":      dedup_key,
                    "source":         "vlrgg_api_detail",
                    "source_priority": 2,
                    "date":           date,
                    "date_raw":       date_raw,
                    "date_quality":   date_quality,
                    "event":          event,
                    "map":            map_name,
                    "team_a":         team_a,
                    "team_b":         team_b,
                    "score_a":        score_t1,
                    "score_b":        score_t2,
                    "label":          label,
                    "agents_a":       agents_a,
                    "agents_b":       agents_b,
                    "provenance":     f"vlrgg/{match_id}/{game_id}",
                })

    print(f"  파싱 완료: {len(rows):,}행 (스킵 — 점수없음:{skipped_no_score}, 무승부:{skipped_draw}, 선수없음:{skipped_no_players})")

    # dedup_key 기준 중복 제거
    seen: set[str] = set()
    deduped = []
    for r in rows:
        if r["dedup_key"] not in seen:
            seen.add(r["dedup_key"])
            deduped.append(r)

    dup_removed = len(rows) - len(deduped)
    print(f"  중복 제거: {dup_removed:,}건 → 최종 {len(deduped):,}행")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(deduped)

    print(f"\n저장 완료: {OUTPUT_CSV}")

    # 간단한 통계
    label_1 = sum(1 for r in deduped if r["label"] == 1)
    label_0 = len(deduped) - label_1
    maps_count: dict[str, int] = {}
    for r in deduped:
        maps_count[r["map"]] = maps_count.get(r["map"], 0) + 1
    top_maps = sorted(maps_count.items(), key=lambda x: -x[1])[:5]

    print(f"\n  label 1(승): {label_1:,}  label 0(패): {label_0:,}")
    print(f"  Top 5 맵: {top_maps}")


if __name__ == "__main__":
    main()
