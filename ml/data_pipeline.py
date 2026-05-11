from __future__ import annotations  # 파이썬이 조금 오래된 버전이어도 최신 타입 표기법(X | Y 같은 것)을 쓸 수 있게 해줘요

import argparse  # 터미널에서 "--input 폴더" 같은 명령어 옵션을 읽어오는 도구예요
import hashlib  # 어떤 글자를 넣으면 항상 같은 짧은 암호 코드를 만들어주는 기계예요 (경기 이름표 만들 때 사용해요)
import json  # 딕셔너리 같은 파이썬 데이터를 파일에 저장하거나 불러올 때 쓰는 도구예요
from pathlib import Path  # 파일 경로를 폴더/파일 이름처럼 편하게 다루게 해주는 도구예요
from typing import Any  # "어떤 종류의 값이든 다 받겠다"고 표시할 때 쓰는 기호예요

import numpy as np  # 평균, 중앙값, 표준편차 같은 수학 계산을 빠르게 해주는 도구예요
import pandas as pd  # 엑셀처럼 가로줄·세로줄로 이루어진 표(DataFrame)를 다루는 도구예요
from sklearn.model_selection import GroupShuffleSplit  # 같은 경기 데이터가 훈련용과 시험용에 동시에 들어가지 않도록 안전하게 나눠주는 도구예요

from ml.agent_roles import (  # 요원 역할과 이름을 정리해둔 파일에서 필요한 것들을 가져와요
    AGENT_ROLE_MAP,  # 요원 이름 → 역할군(타격대/척후대 등) 을 연결해둔 사전이에요 (27개 요원)
    ATK_ADV_MAP,  # 어떤 맵이 공격 팀에게 얼마나 유리한지 숫자로 저장해둔 사전이에요
    MAP_ORDER,  # 공식 맵 이름들을 순서대로 늘어놓은 목록이에요 (맵을 숫자로 바꿀 때 기준이 돼요)
    get_role,  # 요원 이름을 넣으면 그 요원의 역할군(예: Duelist)을 알려주는 함수예요
    normalize_agent,  # 요원 이름의 대소문자나 별명을 통일된 표준 이름으로 바꿔주는 함수예요
    normalize_event,  # 대회 이름을 통일된 형식으로 바꿔주는 함수예요
    normalize_map,  # 맵 이름을 표준 이름으로 바꿔주는 함수예요 (모르는 맵이면 None을 반환해요)
    normalize_player,  # 선수 이름을 통일된 형식으로 바꿔주는 함수예요
    normalize_team,  # 팀 이름을 통일된 형식으로 바꿔주는 함수예요
)

Row = dict[str, Any]  # 경기 1건을 담는 딕셔너리의 별명이에요 (파서가 돌려주는 데이터 형태예요)

SOURCE_WEIGHT: dict[str, float] = {  # 데이터 출처별로 얼마나 믿을 수 있는지 점수를 매겨둔 사전이에요
    "kaggle_challengers":    1.8,  # Challengers 리그 데이터 — 가장 믿을 수 있어요 (1.8점)
    "kaggle_vct":            1.0,  # VCT 공식 대회 데이터 — 기본 점수예요 (1.0점)
    "kaggle_qualidea":       1.0,  # Qualidea가 모은 데이터 — 기본 점수예요 (1.0점)
    "kaggle_ediashtarevin":  0.9,  # Ediashtarevin이 모은 데이터 — 가장 낮은 점수예요 (0.9점)
    "kaggle_piyush2025":     1.0,  # piyush86kumar VCT 2025 전 대회 데이터 — 기본 점수예요 (1.0점)
    "kaggle_piyush2024":     1.2,  # piyush86kumar VCT Champions 2024 국제 대회 데이터 — VCT 공식 수준이에요 (1.2점)
    "vlrgg_direct_detail":   1.1,  # VLR.gg 상세 페이지에서 검증된 map-level 경기 — 초기 opt-in 가중치예요
}

FEATURE_COLS_P1 = [  # AI가 예측할 때 참고하는 숫자 정보 중 "요원 역할군 기반" 17가지 항목 이름이에요
    "a_duelist", "a_initiator", "a_controller", "a_sentinel",  # 팀A에 각 역할군이 몇 명인지예요 (4개)
    "b_duelist", "b_initiator", "b_controller", "b_sentinel",  # 팀B에 각 역할군이 몇 명인지예요 (4개)
    "diff_duelist", "diff_initiator", "diff_controller", "diff_sentinel",  # 팀A 수 - 팀B 수 차이예요 (4개)
    "map_encoded", "atk_side_advantage", "is_attacker_a",  # 맵 번호, 공격 유리도, 팀A가 공격 측인지 여부예요
    "a_double_initiator", "b_double_initiator",  # 팀에 척후대가 2명 이상이면 1이에요
]

FEATURE_COLS_P2 = [  # AI가 예측할 때 참고하는 숫자 정보 중 "선수 개인 스탯 기반" 27가지 항목 이름이에요
    "a_avg_acs", "b_avg_acs", "a_avg_kd", "b_avg_kd",  # 팀별 평균 전투점수(ACS)와 킬/데스 비율이에요
    "a_avg_kast", "b_avg_kast", "a_avg_adr", "b_avg_adr",  # 팀별 평균 생존기여율(KAST)과 라운드당 피해량(ADR)이에요
    "a_avg_hs", "b_avg_hs",  # 팀별 평균 헤드샷 비율이에요
    "a_fk_fd_ratio", "b_fk_fd_ratio",  # 팀이 얼마나 먼저 적을 잡는지(선제킬 ÷ 선제사) 비율이에요
    "a_avg_assists", "b_avg_assists",  # 팀별 평균 어시스트 수 — 팀워크를 보여주는 숫자예요
    "a_kast_std", "b_kast_std",  # 팀원들 사이에서 KAST가 얼마나 고른지 나타내는 숫자예요 (작을수록 균형 잡혀요)
    "a_avg_agent_map_wr", "b_avg_agent_map_wr",  # 팀의 각 요원이 이 맵에서 얼마나 자주 이겼는지 평균이에요
    "a_avg_agent_pick_rate", "b_avg_agent_pick_rate",  # 팀의 각 요원이 이 맵에서 얼마나 자주 선택됐는지 비율이에요
    "a_avg_agent_exp", "b_avg_agent_exp",  # 팀 선수들이 자기 요원을 얼마나 많이 플레이해봤는지 경험 횟수 평균이에요
    "diff_avg_acs",   # 팀A ACS에서 팀B ACS를 뺀 값이에요 (양수면 팀A가 더 활약이 많음)
    "diff_avg_kd",    # 팀A K/D에서 팀B K/D를 뺀 값이에요 (양수면 팀A가 더 많이 잡고 덜 죽음)
    "diff_avg_kast",  # 팀A KAST에서 팀B KAST를 뺀 값이에요 (양수면 팀A 팀원들이 더 많이 기여함)
    "diff_avg_adr",   # 팀A ADR에서 팀B ADR을 뺀 값이에요 (양수면 팀A가 라운드당 더 많은 피해를 줌)
    "diff_avg_hs",    # 팀A 헤드샷 비율에서 팀B 헤드샷 비율을 뺀 값이에요 (양수면 팀A가 더 정확함)
]

FEATURE_COLS_P3 = [  # 맵별 요원 승률 기반 피처 (train 집계 기반, 데이터 누수 없음)
    "a_map_wr_mean", "b_map_wr_mean",  # 팀별 5요원의 이 맵에서의 역사적 평균 승률이에요
    "diff_map_wr",  # a_map_wr_mean - b_map_wr_mean 차이예요
]

FEATURE_COLS_P4 = [  # 팀 최근 폼 기반 피처 (train 집계 기반, 데이터 누수 없음)
    "a_team_wr",         # 팀A의 훈련 기간 전체 승률이에요
    "b_team_wr",         # 팀B의 훈련 기간 전체 승률이에요
    "a_team_recent_wr",  # 팀A의 훈련 기간 내 최근 10경기 승률이에요
    "b_team_recent_wr",  # 팀B의 훈련 기간 내 최근 10경기 승률이에요
    "a_win_streak",      # 팀A의 연승(양수) / 연패(음수) 수예요
    "b_win_streak",      # 팀B의 연승(양수) / 연패(음수) 수예요
    "a_h2h_wr",          # 팀A의 팀B 상대 역대 승률이에요 (데이터 없으면 0.5)
    "b_h2h_wr",          # 팀B의 팀A 상대 역대 승률이에요 (데이터 없으면 0.5)
    "diff_h2h_wr",       # a_h2h_wr - b_h2h_wr 차이예요 (augment_swap에서 자동 부호 반전)
    "diff_team_wr",      # a_team_wr - b_team_wr 차이예요 (augment_swap에서 자동 부호 반전)
]

FEATURE_COLS = FEATURE_COLS_P1 + FEATURE_COLS_P2 + FEATURE_COLS_P3 + FEATURE_COLS_P4

FEATURE_COLS_P5 = [
    "region_encoded",  # 토너먼트 지역 (0=Unknown,1=Americas,2=EMEA,3=Pacific,4=Global)
    "event_tier",      # 대회 등급 (0=Unknown,1=Challengers,2=Regional,3=International)
]

FEATURE_COLS_P6 = [
    "season_q",   # 시즌 분기 (0=Unknown,1=2024-H1,2=2024-H2,3=2025-H1,4=2025-H2,5=2026-H1)
    "patch_era",  # 패치 시대 (0=Unknown,1=Pre-8.0,2=8.x,3=9.x,4=10.x,5=11+)
]

EXPERIMENTAL_FEATURE_COLS = FEATURE_COLS_P5 + FEATURE_COLS_P6

# Laplace 스무딩 강도: 극단값(0/1) 방지를 위해 α=5 prior 경기수 적용
_FORM_SMOOTH_K: float = 5.0
_FORM_SMOOTH_PRIOR: float = 0.5


# ── 컨텍스트 피처 헬퍼 ────────────────────────────────────────────────────────

def _infer_region(event: str, source: str) -> int:
    ev = event.lower()
    if "emea" in ev:
        return 2
    if any(k in ev for k in ("americas", "north america", " na ", "kickoff")):
        return 1
    if any(k in ev for k in ("pacific", "apac", "asia")):
        return 3
    if any(k in ev for k in ("champions", "masters", "world")):
        return 4
    if source == "kaggle_challengers":
        return 1
    return 0


def _infer_event_tier(event: str, source: str) -> int:
    ev = event.lower()
    if source == "kaggle_challengers" or "challengers" in ev:
        return 1
    if any(k in ev for k in ("champions", "masters")):
        return 3
    if any(k in ev for k in ("vct", "stage", "kickoff")):
        return 2
    return 0


_SEASON_Q_BOUNDS = [
    ("2026-01", "2026-12", 5),
    ("2025-07", "2025-12", 4),
    ("2025-01", "2025-06", 3),
    ("2024-07", "2024-12", 2),
    ("2024-01", "2024-06", 1),
]


def _date_to_season_q(date_str: str) -> int:
    s = str(date_str).strip()[:7]
    if not s or len(s) < 7 or s[4] != "-":
        return 0
    for lo, hi, q in _SEASON_Q_BOUNDS:
        if lo <= s <= hi:
            return q
    return 0


_PATCH_ERA_MAP: dict[int, int] = {0: 0, 1: 2, 2: 3, 3: 4, 4: 5, 5: 5}


def _add_context_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["region_encoded"] = df.apply(
        lambda r: _infer_region(str(r.get("event", "")), str(r.get("source", ""))), axis=1
    )
    df["event_tier"] = df.apply(
        lambda r: _infer_event_tier(str(r.get("event", "")), str(r.get("source", ""))), axis=1
    )
    date_col = df["date"] if "date" in df.columns else pd.Series([""] * len(df))
    df["season_q"] = date_col.apply(_date_to_season_q)
    df["patch_era"] = df["season_q"].map(_PATCH_ERA_MAP).fillna(0).astype(int)
    return df


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _sha1(s: str, length: int) -> str:  # 문자열을 넣으면 항상 같은 짧은 암호 코드를 돌려주는 함수예요 (앞 length 글자만 써요)
    return hashlib.sha1(s.encode("utf-8", errors="replace")).hexdigest()[:length]  # 글자를 UTF-8로 바꾼 뒤 SHA-1 암호화 후 앞 length자만 잘라요


def make_match_key(source: str, filepath: str, match_id: str, map_name: str) -> str:  # 경기 하나를 콕 집어 부르는 16글자 고유 이름표를 만들어요
    return _sha1(f"{source}|{filepath}|{match_id}|{map_name}", 16)  # 출처·파일·경기번호·맵을 합쳐서 암호화한 16글자 이름표를 돌려줘요


def make_dedup_key(  # 같은 경기가 여러 파일에 중복될 때 하나만 남기려고 찍는 24글자 고유 도장을 만들어요
    date: str, event: str, map_name: str,  # 경기 날짜, 대회 이름, 맵 이름이에요
    team_a: str, team_b: str,  # 팀A 이름, 팀B 이름이에요
    agents_a: list[str], agents_b: list[str],  # 팀A 요원 목록, 팀B 요원 목록이에요
    score_a: int, score_b: int,  # 팀A 점수, 팀B 점수예요
) -> str:
    canonical = "|".join([  # 모든 정보를 파이프(|) 기호로 연결해서 하나의 긴 문자열로 만들어요
        str(date).strip(),  # 날짜 앞뒤 빈칸 제거해요
        event.lower().strip(),  # 대회 이름을 소문자로 바꾸고 빈칸 제거해요
        map_name.lower(),  # 맵 이름을 소문자로 바꿔요
        team_a.lower(),  # 팀A 이름을 소문자로 바꿔요
        team_b.lower(),  # 팀B 이름을 소문자로 바꿔요
        ",".join(sorted(a.lower() for a in agents_a)),  # 팀A 요원을 가나다순으로 정렬하고 쉼표로 연결해요
        ",".join(sorted(a.lower() for a in agents_b)),  # 팀B 요원을 가나다순으로 정렬하고 쉼표로 연결해요
        str(score_a),  # 팀A 점수를 문자열로 바꿔요
        str(score_b),  # 팀B 점수를 문자열로 바꿔요
    ])
    return _sha1(canonical, 24)  # 긴 문자열을 암호화해서 24글자 도장을 만들어 돌려줘요


def _pct_to_float(val: Any) -> float:  # "88%" 같은 퍼센트 문자열을 0.88처럼 소수로 바꿔주는 함수예요
    """'88%' → 0.88  |  0.88 → 0.88  |  NaN → NaN"""
    if not isinstance(val, str) and pd.isna(val):  # 문자열이 아닌데 빈 값(NaN)이면
        return float("nan")  # 빈 값 그대로 돌려줘요
    s = str(val).strip().rstrip("%")  # 앞뒤 빈칸을 없애고 % 기호도 떼어내요
    try:
        v = float(s)  # 숫자로 바꿔봐요
        return v / 100.0 if v > 1.5 else v  # 1.5보다 크면 퍼센트 표기라서 100으로 나눠요, 아니면 그대로 써요
    except (ValueError, TypeError):  # 숫자로 못 바꾸면
        return float("nan")  # 빈 값(NaN)을 돌려줘요


def _safe_float(val: Any, default: float = float("nan")) -> float:  # 어떤 값이든 소수로 바꾸는 함수예요, 실패하면 기본값을 돌려줘요
    try:
        return float(val)  # 소수로 바꿔봐요
    except (ValueError, TypeError):  # 못 바꾸면 (예: 글자, None)
        return default  # 미리 정해둔 기본값을 돌려줘요 (기본값은 빈 값(NaN)이에요)


def _read_csv(path: Path) -> pd.DataFrame | None:  # CSV 파일을 열어서 엑셀 표(DataFrame)로 돌려줘요, 실패하면 None이에요
    for enc in ("utf-8", "latin-1"):  # utf-8로 먼저 시도하고 안 되면 latin-1로 시도해요
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)  # 파일을 읽어서 표로 돌려줘요 (low_memory=False는 경고 방지용이에요)
        except Exception:  # 읽기에 실패하면 다음 방법을 시도해요
            pass
    return None  # 모든 방법이 실패하면 None을 돌려줘요


def _clean_agents(raw: list[Any]) -> list[str]:  # 요원 목록에서 숫자·빈값·모르는 요원을 제거하고 올바른 이름만 남겨요
    result = []  # 올바른 요원 이름을 모을 빈 리스트예요
    for a in raw:  # 요원 목록을 하나씩 확인해요
        if not isinstance(a, str):  # 문자열이 아니면
            try:
                float(a)  # 숫자로 바뀌면 잘못된 데이터예요
                continue  # 숫자면 건너뛰어요 (데이터가 오염된 거예요)
            except (ValueError, TypeError):  # 숫자로도 못 바꾸면 일단 계속 처리해요
                pass
        norm = normalize_agent(str(a))  # 요원 이름을 표준 이름으로 바꿔봐요
        if norm:  # 표준 이름으로 바꿀 수 있으면 (알려진 요원이면)
            result.append(norm)  # 결과 리스트에 추가해요
    return result  # 정제된 요원 이름 리스트를 돌려줘요


# ── 파서 A: ryanluong ─────────────────────────────────────────────────────────

def _parse_ryanluong_matches(matches_dir: Path, source: str, weight: float) -> list[Row]:  # ryanluong이 만든 overview.csv와 maps_scores.csv 두 파일을 읽어서 경기 목록을 만드는 함수예요
    ov = _read_csv(matches_dir / "overview.csv")  # 선수별 스탯이 담긴 파일을 표로 읽어요
    sc = _read_csv(matches_dir / "maps_scores.csv")  # 경기 점수가 담긴 파일을 표로 읽어요
    if ov is None or sc is None:  # 두 파일 중 하나라도 없으면
        return []  # 빈 목록을 돌려줘요

    if "Side" in ov.columns:  # "Side"(공격/수비 사이드) 열이 있으면
        ov = ov[ov["Side"] == "both"].copy()  # "both"(합산) 줄만 남겨요 — 공격/수비가 따로 적힌 중복 줄을 제거해요

    ov = ov.rename(columns={  # 열 이름을 우리가 쓰는 표준 이름으로 바꿔요
        "Average Combat Score": "acs",  # 평균 전투 점수
        "Kills": "kills",  # 킬 수
        "Deaths": "deaths",  # 데스 수
        "Assists": "assists",  # 어시스트 수
        "Kill, Assist, Trade, Survive %": "kast_raw",  # 생존기여율(퍼센트 문자열)
        "Average Damage Per Round": "adr",  # 라운드당 평균 피해량
        "Headshot %": "hs_raw",  # 헤드샷 비율(퍼센트 문자열)
        "First Kills": "fk",  # 선제킬 수
        "First Deaths": "fd",  # 선제사 수
    })

    rows: list[Row] = []  # 파싱한 경기들을 담을 빈 리스트예요
    for (match_name, map_raw), grp in ov.groupby(["Match Name", "Map"]):  # 경기 이름과 맵 이름이 같은 줄끼리 묶어서 하나씩 처리해요
        map_norm = normalize_map(str(map_raw))  # 맵 이름을 표준 이름으로 바꿔요 (모르는 맵이면 None)
        if map_norm is None:  # 모르는 맵이면 건너뛰어요
            continue

        sc_match = sc[(sc["Match Name"] == match_name) & (sc["Map"] == map_raw)]  # 같은 경기·맵의 점수 줄을 찾아요
        if sc_match.empty:  # 점수 정보가 없으면 건너뛰어요
            continue
        sr = sc_match.iloc[0]  # 첫 번째 점수 줄을 가져와요

        raw_a = str(sr.get("Team A", "")).strip()  # 팀A 이름을 꺼내고 앞뒤 빈칸을 없애요
        raw_b = str(sr.get("Team B", "")).strip()  # 팀B 이름을 꺼내고 앞뒤 빈칸을 없애요
        try:
            score_a = int(sr.get("Team A Score", 0))  # 팀A 점수를 정수로 바꿔요
            score_b = int(sr.get("Team B Score", 0))  # 팀B 점수를 정수로 바꿔요
        except (ValueError, TypeError):  # 점수를 숫자로 못 바꾸면 건너뛰어요
            continue
        if score_a == score_b:  # 무승부(동점)면 누가 이겼는지 모르니까 건너뛰어요
            continue

        team_a = normalize_team(raw_a)  # 팀A 이름을 표준 형식으로 바꿔요
        team_b = normalize_team(raw_b)  # 팀B 이름을 표준 형식으로 바꿔요
        label = 1 if score_a > score_b else 0  # 팀A 점수가 높으면 1(팀A 승), 낮으면 0(팀B 승)이에요

        try:
            atk_a = int(sr.get("Team A Attacker Score", 0))  # 팀A가 공격할 때 딴 점수예요
            def_a = int(sr.get("Team A Defender Score", 0))  # 팀A가 수비할 때 딴 점수예요
        except (ValueError, TypeError):  # 못 읽으면 None으로 놔둬요
            atk_a, def_a = None, None

        def _find_players(raw_team: str) -> pd.DataFrame | None:  # 팀 이름으로 그 팀 선수들의 줄을 찾아주는 함수예요
            for t in grp["Team"].unique():  # 이 경기에 있는 모든 팀 이름을 하나씩 확인해요
                if normalize_team(str(t)).lower() == normalize_team(raw_team).lower():  # 표준화 후 대소문자 구분 없이 비교해요
                    return grp[grp["Team"] == t]  # 일치하는 팀의 선수 줄들을 돌려줘요
            return None  # 일치하는 팀이 없으면 None을 돌려줘요

        df_a = _find_players(raw_a)  # 팀A 선수들 줄을 찾아요
        df_b = _find_players(raw_b)  # 팀B 선수들 줄을 찾아요
        if df_a is None or df_b is None:  # 어느 팀이든 선수를 못 찾으면 건너뛰어요
            continue

        def _build(df: pd.DataFrame) -> list[dict]:  # 선수 줄들에서 필요한 스탯을 꺼내 딕셔너리 리스트로 만들어요
            ps = []  # 선수 스탯 딕셔너리를 담을 빈 리스트예요
            for _, r in df.iterrows():  # 각 선수 줄을 하나씩 처리해요
                kills = _safe_float(r.get("kills", 0))  # 킬 수를 소수로 바꿔요 (실패하면 0)
                deaths = _safe_float(r.get("deaths", 1))  # 데스 수를 소수로 바꿔요 (실패하면 1 — 0으로 나누는 것 방지)
                ps.append({  # 선수 스탯 딕셔너리를 만들어 리스트에 추가해요
                    "player": normalize_player(str(r.get("Player", ""))),  # 선수 이름을 표준 형식으로 바꿔요
                    "agent": normalize_agent(str(r.get("Agents", ""))),  # 요원 이름을 표준 형식으로 바꿔요
                    "acs": _safe_float(r.get("acs")),  # 평균 전투 점수예요 (못 읽으면 빈 값)
                    "kd": kills / max(deaths, 1),  # 킬 ÷ 데스 비율이에요 (데스가 0이면 1로 나눠요)
                    "kast": _pct_to_float(r.get("kast_raw")),  # 생존기여율 퍼센트를 소수로 바꿔요
                    "adr": _safe_float(r.get("adr")),  # 라운드당 평균 피해량이에요 (못 읽으면 빈 값)
                    "fk": _safe_float(r.get("fk", 0)),  # 선제킬 수예요 (못 읽으면 0)
                    "fd": _safe_float(r.get("fd", 0)),  # 선제사 수예요 (못 읽으면 0)
                    "assists": _safe_float(r.get("assists", 0)),  # 어시스트 수예요 (못 읽으면 0)
                    "hs": _pct_to_float(r.get("hs_raw")),  # 헤드샷 비율 퍼센트를 소수로 바꿔요
                    "clutch": float("nan"),  # ryanluong 데이터는 클러치 정보가 없어서 빈 값이에요
                })
            return ps  # 선수 스탯 딕셔너리 리스트를 돌려줘요

        players_a = _build(df_a)  # 팀A 선수 스탯 리스트를 만들어요
        players_b = _build(df_b)  # 팀B 선수 스탯 리스트를 만들어요
        agents_a = _clean_agents([p["agent"] for p in players_a])  # 팀A 요원 목록에서 오류 있는 것을 걸러내요
        agents_b = _clean_agents([p["agent"] for p in players_b])  # 팀B 요원 목록에서 오류 있는 것을 걸러내요
        if len(agents_a) != 5 or len(agents_b) != 5:  # 어느 팀이든 요원이 정확히 5명이 아니면 건너뛰어요
            continue

        tournament = normalize_event(str(grp["Tournament"].iloc[0]) if "Tournament" in grp.columns else "")  # 대회 이름을 표준 형식으로 바꿔요 (열이 없으면 빈 문자열)
        rows.append({  # 경기 정보를 딕셔너리로 만들어 목록에 추가해요
            "source": source,  # 데이터 출처 이름이에요 (kaggle_vct 또는 kaggle_challengers)
            "weight": weight,  # 이 데이터 출처의 신뢰도 점수예요
            "match_key": make_match_key(source, str(matches_dir), str(match_name), map_norm),  # 이 경기만의 고유 이름표(16글자)예요
            "dedup_key": make_dedup_key("", tournament, map_norm, team_a, team_b, agents_a, agents_b, score_a, score_b),  # 중복 경기를 찾는 고유 도장(24글자)이에요 (날짜 정보 없음)
            "date": "",  # ryanluong 데이터는 날짜 정보가 없어요
            "event": tournament,  # 표준화된 대회 이름이에요
            "map": map_norm,  # 표준화된 맵 이름이에요
            "team_a": team_a,  # 표준화된 팀A 이름이에요
            "team_b": team_b,  # 표준화된 팀B 이름이에요
            "players_a": players_a,  # 팀A 선수 스탯 리스트예요
            "players_b": players_b,  # 팀B 선수 스탯 리스트예요
            "score_a": score_a,  # 팀A 최종 점수예요
            "score_b": score_b,  # 팀B 최종 점수예요
            "atk_a": atk_a,  # 팀A가 공격할 때 딴 점수예요 (없으면 None)
            "def_a": def_a,  # 팀A가 수비할 때 딴 점수예요 (없으면 None)
            "label": label,  # 승패 정답이에요 (1 = 팀A 승, 0 = 팀B 승)
        })
    return rows  # 이 폴더에서 파싱한 모든 경기 목록을 돌려줘요


def parse_vct_dir(base_dir: Path) -> list[Row]:  # VCT·Challengers 데이터셋 폴더를 돌아다니며 모든 경기를 파싱해요
    rows: list[Row] = []  # 파싱 결과를 담을 빈 리스트예요
    base = Path(base_dir)  # 문자열 경로를 Path 객체로 바꿔요

    vct_root = base / "vct_2021_2023"  # VCT 2021~2023 데이터 폴더 경로예요
    if vct_root.exists():  # 그 폴더가 실제로 있으면
        for yr in sorted(vct_root.iterdir()):  # 연도 폴더를 알파벳 순서대로 하나씩 확인해요
            if yr.is_dir() and yr.name != "all_ids":  # 실제 폴더이고 all_ids를 제외한 모든 연도 파싱
                md = yr / "matches"  # 그 연도의 matches 폴더 경로예요
                if md.exists():  # matches 폴더가 있으면 파싱해요
                    rows.extend(_parse_ryanluong_matches(md, "kaggle_vct", 1.0))  # VCT 데이터를 파싱해서 목록에 추가해요

    ch_root = base / "ryanluong1__valorant-challengers-league-data"  # Challengers 리그 데이터 폴더 경로예요
    if ch_root.exists():  # 그 폴더가 실제로 있으면
        for sub in sorted(ch_root.iterdir()):  # 하위 폴더를 알파벳 순서대로 하나씩 확인해요
            if sub.is_dir():  # 실제 폴더인 경우만 처리해요
                md = sub / "matches"  # 그 폴더 안의 matches 폴더 경로예요
                if md.exists():  # matches 폴더가 있으면 파싱해요
                    rows.extend(_parse_ryanluong_matches(md, "kaggle_challengers", 1.8))  # Challengers 데이터를 파싱해서 목록에 추가해요

    return rows  # VCT + Challengers 전체 파싱 결과를 돌려줘요


# ── 파서 B: 단일 CSV ──────────────────────────────────────────────────────────

def _parse_qualidea(csv_path: Path) -> list[Row]:  # qualidea가 만든 단일 CSV 파일을 읽어서 경기 목록을 만드는 함수예요
    df = _read_csv(csv_path)  # CSV 파일을 표로 읽어요
    if df is None:  # 읽기에 실패하면
        return []  # 빈 목록을 돌려줘요

    # 요원 열에 숫자가 들어간 오염된 줄을 제거해요
    numeric_mask = pd.to_numeric(df["agent"], errors="coerce").notna()  # 요원 이름이 숫자로 바뀌는 줄을 오염 줄로 표시해요
    df = df[~numeric_mask].copy()  # 오염된 줄을 제거하고 깨끗한 복사본을 만들어요

    rows: list[Row] = []  # 파싱한 경기들을 담을 빈 리스트예요
    for (match_dt, map_raw, t1_raw, t2_raw), grp in df.groupby(  # 날짜·맵·팀1·팀2가 같은 줄끼리 묶어서 하나씩 처리해요
        ["match-datetime", "map", "team1", "team2"]
    ):
        map_norm = normalize_map(str(map_raw))  # 맵 이름을 표준 이름으로 바꿔요
        if map_norm is None:  # 모르는 맵이면 건너뛰어요
            continue

        unique_pt = grp["player-team"].dropna().unique()  # 이 경기에서 선수들이 속한 팀 이름 종류를 추려요 (빈 값 제외)
        if len(unique_pt) != 2:  # 팀이 정확히 2종류가 아니면 건너뛰어요
            continue

        # player-team 값이 team1/team2 이름과 같을 수도, 약간 다를 수도 있어요
        grp1 = grp[grp["player-team"] == unique_pt[0]]  # 첫 번째 팀에 속한 선수 줄들이에요
        grp2 = grp[grp["player-team"] == unique_pt[1]]  # 두 번째 팀에 속한 선수 줄들이에요
        if len(grp1) != 5 or len(grp2) != 5:  # 어느 팀이든 선수가 5명이 아니면 건너뛰어요
            continue

        try:
            s1 = int(grp["team1-score"].iloc[0])  # team1 점수를 정수로 바꿔요
            s2 = int(grp["team2-score"].iloc[0])  # team2 점수를 정수로 바꿔요
        except (ValueError, TypeError, KeyError):  # 못 바꾸거나 열이 없으면 건너뛰어요
            continue
        if s1 == s2:  # 무승부면 건너뛰어요
            continue

        # player-team[0]이 team1과 같은지 확인해서 팀A를 결정해요
        pt0_norm = normalize_team(str(unique_pt[0]))  # 첫 번째 player-team 값을 표준 형식으로 바꿔요
        t1_norm = normalize_team(str(t1_raw))  # team1 이름을 표준 형식으로 바꿔요
        if pt0_norm.lower() == t1_norm.lower():  # player-team[0]이 team1과 같으면
            team_a = t1_norm  # team1이 팀A예요
            team_b = normalize_team(str(t2_raw))  # team2가 팀B예요
            score_a, score_b = s1, s2  # 각 팀 점수를 그대로 대응해요
            label = 1 if s1 > s2 else 0  # team1(팀A) 점수가 높으면 팀A 승이에요
            df_a, df_b = grp1, grp2  # grp1이 팀A, grp2가 팀B예요
        else:  # player-team[0]이 team2에 해당하는 경우예요
            team_a = normalize_team(str(t2_raw))  # team2가 팀A예요
            team_b = t1_norm  # team1이 팀B예요
            score_a, score_b = s2, s1  # 점수를 뒤집어서 대응해요
            label = 1 if s2 > s1 else 0  # team2(팀A) 점수가 높으면 팀A 승이에요
            df_a, df_b = grp2, grp1  # grp2가 팀A, grp1이 팀B예요

        def _build_q(team_df: pd.DataFrame) -> list[dict]:  # qualidea 형식 선수 줄들에서 스탯 딕셔너리 리스트를 만드는 함수예요
            ps = []  # 선수 스탯을 담을 빈 리스트예요
            for _, r in team_df.iterrows():  # 각 선수 줄을 하나씩 처리해요
                ps.append({  # 선수 스탯 딕셔너리를 만들어 리스트에 추가해요
                    "player": normalize_player(str(r.get("player-name", ""))),  # 선수 이름을 표준 형식으로 바꿔요
                    "agent": normalize_agent(str(r.get("agent", ""))),  # 요원 이름을 표준 형식으로 바꿔요
                    "acs": _safe_float(r.get("acs")),  # 평균 전투 점수예요
                    "kd": _safe_float(r.get("k", 0)) / max(_safe_float(r.get("d", 1)), 1),  # 킬("k") ÷ 데스("d") 비율이에요 (데스 0 방지)
                    "kast": _pct_to_float(r.get("kast")),  # 생존기여율 퍼센트를 소수로 바꿔요
                    "adr": _safe_float(r.get("adr")),  # 라운드당 평균 피해량이에요
                    "fk": _safe_float(r.get("fk", 0)),  # 선제킬 수예요
                    "fd": _safe_float(r.get("fd", 0)),  # 선제사 수예요
                    "assists": _safe_float(r.get("a", 0)),  # 어시스트 수예요 ("a" 열에 저장돼 있어요)
                    "hs": _pct_to_float(r.get("hs")),  # 헤드샷 비율 퍼센트를 소수로 바꿔요
                    "clutch": float("nan"),  # qualidea 데이터는 클러치 정보가 없어서 빈 값이에요
                })
            return ps  # 선수 스탯 딕셔너리 리스트를 돌려줘요

        players_a = _build_q(df_a)  # 팀A 선수 스탯 리스트를 만들어요
        players_b = _build_q(df_b)  # 팀B 선수 스탯 리스트를 만들어요
        agents_a = _clean_agents([p["agent"] for p in players_a])  # 팀A 요원 목록에서 오류 있는 것을 걸러내요
        agents_b = _clean_agents([p["agent"] for p in players_b])  # 팀B 요원 목록에서 오류 있는 것을 걸러내요
        if len(agents_a) != 5 or len(agents_b) != 5:  # 어느 팀이든 요원이 5명이 아니면 건너뛰어요
            continue

        date_str = str(match_dt)  # 경기 날짜·시간을 문자열로 바꿔요
        rows.append({  # 경기 정보를 딕셔너리로 만들어 목록에 추가해요
            "source": "kaggle_qualidea",  # 데이터 출처 이름이에요
            "weight": 1.0,  # qualidea 데이터의 신뢰도 점수예요 (기본값)
            "match_key": make_match_key("kaggle_qualidea", str(csv_path), f"{match_dt}|{t1_raw}|{t2_raw}", map_norm),  # 날짜·팀 조합으로 만든 고유 이름표예요
            "dedup_key": make_dedup_key(date_str, "", map_norm, team_a, team_b, agents_a, agents_b, score_a, score_b),  # 대회 이름 없이 날짜·팀 기반으로 만든 고유 도장이에요
            "date": date_str,  # 경기 날짜·시간 문자열이에요
            "event": "",  # qualidea 데이터는 대회 이름이 없어요
            "map": map_norm,  # 표준화된 맵 이름이에요
            "team_a": team_a,  # 표준화된 팀A 이름이에요
            "team_b": team_b,  # 표준화된 팀B 이름이에요
            "players_a": players_a,  # 팀A 선수 스탯 리스트예요
            "players_b": players_b,  # 팀B 선수 스탯 리스트예요
            "score_a": score_a,  # 팀A 최종 점수예요
            "score_b": score_b,  # 팀B 최종 점수예요
            "atk_a": None,  # qualidea 데이터는 공격/수비별 점수가 없어요
            "def_a": None,  # qualidea 데이터는 공격/수비별 점수가 없어요
            "label": label,  # 승패 정답이에요 (1 = 팀A 승, 0 = 팀B 승)
        })
    return rows  # 이 파일에서 파싱한 모든 경기 목록을 돌려줘요


def _parse_ediashtarevin(csv_path: Path) -> list[Row]:  # ediashtarevin이 만든 선수 스탯 CSV를 읽어서 경기 목록을 만드는 함수예요
    df = _read_csv(csv_path)  # CSV 파일을 표로 읽어요
    if df is None:  # 읽기에 실패하면
        return []  # 빈 목록을 돌려줘요

    rows: list[Row] = []  # 파싱한 경기들을 담을 빈 리스트예요
    for (match_id, game_id), grp in df.groupby(["match_id", "game_id"]):  # 경기 번호와 게임 번호가 같은 줄끼리 묶어서 처리해요
        winners = grp[grp["win_lose"] == "team win"]  # "team win"이라고 적힌 줄 = 이긴 팀 선수들이에요
        losers = grp[grp["win_lose"] == "opponent win"]  # "opponent win"이라고 적힌 줄 = 진 팀 선수들이에요
        if len(winners) != 5 or len(losers) != 5:  # 이긴 팀·진 팀 모두 5명씩 아니면 건너뛰어요
            continue

        map_norm = normalize_map(str(grp["map"].iloc[0]))  # 맵 이름을 표준 이름으로 바꿔요
        if map_norm is None:  # 모르는 맵이면 건너뛰어요
            continue

        team_a = normalize_team(str(winners["team"].iloc[0]))  # 이긴 팀을 팀A로 정하고 이름을 표준 형식으로 바꿔요
        team_b = normalize_team(str(losers["team"].iloc[0]))  # 진 팀을 팀B로 정하고 이름을 표준 형식으로 바꿔요

        try:
            score_a = int(winners["score_team"].iloc[0])  # 팀A(이긴 팀) 점수를 정수로 바꿔요
            score_b = int(losers["score_team"].iloc[0])  # 팀B(진 팀) 점수를 정수로 바꿔요
        except (ValueError, TypeError):  # 점수를 못 바꾸면 임시 점수를 써요
            score_a, score_b = 13, 0  # 발로란트 맵 최고 점수인 13을 임시로 써요
        if score_a == score_b:  # 무승부면 건너뛰어요
            continue

        def _build_e(team_df: pd.DataFrame) -> list[dict]:  # ediashtarevin 형식 선수 줄들에서 스탯 딕셔너리 리스트를 만드는 함수예요
            ps = []  # 선수 스탯을 담을 빈 리스트예요
            for _, r in team_df.iterrows():  # 각 선수 줄을 하나씩 처리해요
                ps.append({  # 선수 스탯 딕셔너리를 만들어 리스트에 추가해요
                    "player": normalize_player(str(r.get("player", ""))),  # 선수 이름을 표준 형식으로 바꿔요
                    "agent": normalize_agent(str(r.get("agent", ""))),  # 요원 이름을 표준 형식으로 바꿔요
                    "acs": _safe_float(r.get("acs")),  # 평균 전투 점수예요
                    "kd": _safe_float(r.get("kill", 0)) / max(_safe_float(r.get("death", 1)), 1),  # 킬("kill") ÷ 데스("death") 비율이에요 (데스 0 방지)
                    "kast": _pct_to_float(r.get("kast%")),  # "kast%" 열의 퍼센트를 소수로 바꿔요
                    "adr": _safe_float(r.get("adr")),  # 라운드당 평균 피해량이에요
                    "fk": _safe_float(r.get("fk", 0)),  # 선제킬 수예요
                    "fd": _safe_float(r.get("fd", 0)),  # 선제사 수예요
                    "assists": _safe_float(r.get("assist", 0)),  # 어시스트 수예요 ("assist" 열에 저장돼 있어요)
                    "hs": _pct_to_float(r.get("hs%")),  # "hs%" 열의 헤드샷 비율 퍼센트를 소수로 바꿔요
                    "clutch": float("nan"),  # ediashtarevin 데이터는 클러치 정보가 없어서 빈 값이에요
                })
            return ps  # 선수 스탯 딕셔너리 리스트를 돌려줘요

        players_a = _build_e(winners)  # 팀A(이긴 팀) 선수 스탯 리스트를 만들어요
        players_b = _build_e(losers)  # 팀B(진 팀) 선수 스탯 리스트를 만들어요
        agents_a = _clean_agents([p["agent"] for p in players_a])  # 팀A 요원 목록에서 오류 있는 것을 걸러내요
        agents_b = _clean_agents([p["agent"] for p in players_b])  # 팀B 요원 목록에서 오류 있는 것을 걸러내요
        if len(agents_a) != 5 or len(agents_b) != 5:  # 어느 팀이든 요원이 5명이 아니면 건너뛰어요
            continue

        rows.append({  # 경기 정보를 딕셔너리로 만들어 목록에 추가해요
            "source": "kaggle_ediashtarevin",  # 데이터 출처 이름이에요
            "weight": 0.9,  # ediashtarevin 데이터의 신뢰도 점수예요 (가장 낮아요)
            "match_key": make_match_key("kaggle_ediashtarevin", str(csv_path), f"{match_id}|{game_id}", map_norm),  # 경기번호·게임번호·맵으로 만든 고유 이름표예요
            "dedup_key": make_dedup_key("", "", map_norm, team_a, team_b, agents_a, agents_b, score_a, score_b),  # 날짜·대회 이름 없이 팀·요원 기반으로 만든 고유 도장이에요
            "date": "",  # ediashtarevin 데이터는 날짜 정보가 없어요
            "event": "",  # ediashtarevin 데이터는 대회 이름이 없어요
            "map": map_norm,  # 표준화된 맵 이름이에요
            "team_a": team_a,  # 표준화된 팀A 이름이에요 (이긴 팀)
            "team_b": team_b,  # 표준화된 팀B 이름이에요 (진 팀)
            "players_a": players_a,  # 팀A 선수 스탯 리스트예요
            "players_b": players_b,  # 팀B 선수 스탯 리스트예요
            "score_a": score_a,  # 팀A(이긴 팀) 최종 점수예요
            "score_b": score_b,  # 팀B(진 팀) 최종 점수예요
            "atk_a": None,  # ediashtarevin 데이터는 공격/수비별 점수가 없어요
            "def_a": None,  # ediashtarevin 데이터는 공격/수비별 점수가 없어요
            "label": 1,  # 팀A는 항상 이긴 팀("team win")이라서 정답이 항상 1이에요
        })
    return rows  # 이 파일에서 파싱한 모든 경기 목록을 돌려줘요


def parse_single_csv(base_dir: Path) -> list[Row]:  # qualidea·ediashtarevin CSV 파일들을 찾아 파싱하고 목록을 돌려주는 함수예요
    base = Path(base_dir)  # 문자열 경로를 Path 객체로 바꿔요
    rows: list[Row] = []  # 파싱 결과를 담을 빈 리스트예요

    q = base / "qualidea1217__valorant-pro-matches-since-april-2021" / "data-since-april-2021.csv"  # qualidea CSV 파일 경로예요
    if q.exists():  # 파일이 실제로 있으면
        rows.extend(_parse_qualidea(q))  # qualidea 파싱 결과를 목록에 추가해요

    e = base / "ediashtarevin__vct-champions-2023-stats" / "player_stats.csv"  # ediashtarevin CSV 파일 경로예요
    if e.exists():  # 파일이 실제로 있으면
        rows.extend(_parse_ediashtarevin(e))  # ediashtarevin 파싱 결과를 목록에 추가해요

    return rows  # 전체 파싱 결과를 돌려줘요


# ── 파서 C: piyush86kumar VCT 2025 ───────────────────────────────────────────

def _parse_piyush2025(event_folder: Path, source: str, weight: float) -> list[Row]:
    stats_path = event_folder / "detailed_matches_player_stats.csv"
    maps_path = event_folder / "detailed_matches_maps.csv"
    df_stats = _read_csv(stats_path)
    df_maps = _read_csv(maps_path)
    if df_stats is None or df_maps is None:
        return []

    df_stats = df_stats[df_stats["stat_type"] == "map"].copy()

    # (match_id, map_name) → (score_team1, score_team2) — "12 - 14" 형식 파싱
    map_scores: dict[tuple, tuple[int, int]] = {}
    for _, r in df_maps.iterrows():
        parts = str(r.get("score", "")).split("-")
        if len(parts) == 2:
            try:
                map_scores[(r["match_id"], r["map_name"])] = (int(parts[0].strip()), int(parts[1].strip()))
            except (ValueError, TypeError):
                pass

    rows: list[Row] = []
    for (match_id, map_name), grp in df_stats.groupby(["match_id", "map_name"]):
        map_norm = normalize_map(str(map_name))
        if map_norm is None:
            continue

        team1_raw = str(grp["team1"].iloc[0]).strip()
        team2_raw = str(grp["team2"].iloc[0]).strip()
        df_t1 = grp[grp["player_team"] == team1_raw]
        df_t2 = grp[grp["player_team"] == team2_raw]
        if len(df_t1) != 5 or len(df_t2) != 5:
            continue

        team1_norm = normalize_team(team1_raw)
        team2_norm = normalize_team(team2_raw)
        winner_raw = str(grp["map_winner"].iloc[0]).strip()
        winner_norm = normalize_team(winner_raw)
        if winner_norm.lower() == team1_norm.lower():
            label = 1
        elif winner_norm.lower() == team2_norm.lower():
            label = 0
        else:
            continue

        s1, s2 = map_scores.get((match_id, map_name), (13 if label == 1 else 0, 0 if label == 1 else 13))

        def _build_p(team_df: pd.DataFrame) -> list[dict]:
            ps = []
            for _, r in team_df.iterrows():
                kills = _safe_float(r.get("k", 0))
                deaths = _safe_float(r.get("d", 1))
                ps.append({
                    "player": normalize_player(str(r.get("player_name", ""))),
                    "agent": normalize_agent(str(r.get("agent", ""))),
                    "acs": _safe_float(r.get("acs")),
                    "kd": kills / max(deaths, 1),
                    "kast": _pct_to_float(r.get("kast")),
                    "adr": _safe_float(r.get("adr")),
                    "fk": _safe_float(r.get("fk", 0)),
                    "fd": _safe_float(r.get("fd", 0)),
                    "assists": _safe_float(r.get("a", 0)),
                    "hs": _pct_to_float(r.get("hs_percent")),
                    "clutch": float("nan"),
                })
            return ps

        players_a = _build_p(df_t1)
        players_b = _build_p(df_t2)
        agents_a = _clean_agents([p["agent"] for p in players_a])
        agents_b = _clean_agents([p["agent"] for p in players_b])
        if len(agents_a) != 5 or len(agents_b) != 5:
            continue

        date_str = str(grp["match_date"].iloc[0]) if "match_date" in grp.columns else ""
        event_norm = normalize_event(str(grp["event_name"].iloc[0])) if "event_name" in grp.columns else ""

        rows.append({
            "source": source,
            "weight": weight,
            "match_key": make_match_key(source, str(event_folder), str(match_id), map_norm),
            "dedup_key": make_dedup_key(date_str, event_norm, map_norm, team1_norm, team2_norm, agents_a, agents_b, s1, s2),
            "date": date_str,
            "event": event_norm,
            "map": map_norm,
            "team_a": team1_norm,
            "team_b": team2_norm,
            "players_a": players_a,
            "players_b": players_b,
            "score_a": s1,
            "score_b": s2,
            "atk_a": None,
            "def_a": None,
            "label": label,
        })
    return rows


_PIYUSH_EVENT_DIRS = [  # _csvs 서브폴더 구조를 가진 piyush 이벤트 폴더 목록이에요
    "piyush86kumar__valorant-champions-tour-2024-all-events",
    "piyush86kumar__valorant-champions-tour-2025-paris",
    "piyush86kumar__valorant-kickoff-2025-all-regions",
    "piyush86kumar__valorant-masters-bangkok-2025",
    "piyush86kumar__valorant-masters-toronto-2025",
    "piyush86kumar__valorant-stage-1-2025-all-regions",
    "piyush86kumar__valorant-stage-2-2025-all-regions",
    "piyush86kumar__valorant-vct-2025-all-events",
]


def parse_piyush_events_dir(base_dir: Path) -> list[Row]:
    base = Path(base_dir)
    rows: list[Row] = []

    # _csvs 서브폴더 구조의 이벤트 폴더들을 처리해요
    for dirname in _PIYUSH_EVENT_DIRS:
        root = base / dirname
        if not root.exists():
            continue
        for event_folder in sorted(root.iterdir()):
            if event_folder.is_dir() and event_folder.name.endswith("_csvs"):
                rows.extend(_parse_piyush2025(event_folder, "kaggle_piyush2025", 1.0))

    # piyush86kumar__valorant-champions-2024: 플랫 CSV 구조 (서브폴더 없음)
    flat_dir = base / "piyush86kumar__valorant-champions-2024"
    if flat_dir.exists():
        rows.extend(_parse_piyush2025(flat_dir, "kaggle_piyush2024", 1.2))

    return rows


def _parse_vlrgg_players_json(raw: Any) -> list[dict]:
    try:
        values = json.loads(str(raw)) if not isinstance(raw, list) else raw
    except json.JSONDecodeError:
        return []
    if not isinstance(values, list):
        return []
    players: list[dict] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        kills = _safe_float(item.get("kills", 0), 0.0)
        deaths = _safe_float(item.get("deaths", 0), 0.0)
        kd = _safe_float(item.get("kd"), float("nan"))
        if pd.isna(kd):
            kd = kills / max(deaths, 1.0)
        players.append({
            "player": normalize_player(str(item.get("player", ""))),
            "agent": normalize_agent(str(item.get("agent", ""))),
            "acs": _safe_float(item.get("acs")),
            "kd": kd,
            "kast": _pct_to_float(item.get("kast")),
            "adr": _safe_float(item.get("adr")),
            "fk": _safe_float(item.get("fk", item.get("fb", 0)), 0.0),
            "fd": _safe_float(item.get("fd", 0), 0.0),
            "assists": _safe_float(item.get("assists", 0), 0.0),
            "hs": _pct_to_float(item.get("hs", item.get("hs_pct"))),
            "clutch": _safe_float(item.get("clutch"), float("nan")),
        })
    return players


def parse_vlrgg_pipeline_matches(path: Path) -> list[Row]:
    path = Path(path)
    if not path.exists():
        return []
    df = _read_csv(path)
    if df is None or df.empty:
        return []

    rows: list[Row] = []
    for _, r in df.iterrows():
        map_norm = normalize_map(str(r.get("map", "")))
        if map_norm is None:
            continue
        team_a = normalize_team(str(r.get("team_a", "")))
        team_b = normalize_team(str(r.get("team_b", "")))
        players_a = _parse_vlrgg_players_json(r.get("players_a_json", "[]"))
        players_b = _parse_vlrgg_players_json(r.get("players_b_json", "[]"))
        agents_a = _clean_agents([p.get("agent") for p in players_a])
        agents_b = _clean_agents([p.get("agent") for p in players_b])
        if len(players_a) != 5 or len(players_b) != 5 or len(agents_a) != 5 or len(agents_b) != 5:
            continue
        score_a = int(_safe_float(r.get("score_a"), 0.0))
        score_b = int(_safe_float(r.get("score_b"), 0.0))
        if score_a == score_b:
            continue
        label = int(_safe_float(r.get("label"), 1 if score_a > score_b else 0))
        if label not in (0, 1):
            continue
        source = str(r.get("source", "vlrgg_direct_detail") or "vlrgg_direct_detail")
        weight = float(SOURCE_WEIGHT.get(source, 1.1))
        date_str = str(r.get("date", "") or "")
        event_norm = normalize_event(str(r.get("event", "") or ""))
        match_id = str(r.get("match_id", "") or "")
        game_id = str(r.get("game_id", "") or "")
        source_url = str(r.get("source_url", "") or path)
        rows.append({
            "source": source,
            "weight": weight,
            "match_key": str(r.get("match_key", "") or make_match_key(source, source_url, f"{match_id}|{game_id}", map_norm)),
            "dedup_key": str(r.get("dedup_key", "") or make_dedup_key(date_str, event_norm, map_norm, team_a, team_b, agents_a, agents_b, score_a, score_b)),
            "date": date_str,
            "event": event_norm,
            "map": map_norm,
            "team_a": team_a,
            "team_b": team_b,
            "players_a": players_a,
            "players_b": players_b,
            "score_a": score_a,
            "score_b": score_b,
            "atk_a": int(_safe_float(r.get("atk_a"), 0.0)) if not pd.isna(_safe_float(r.get("atk_a"), float("nan"))) else None,
            "def_a": int(_safe_float(r.get("def_a"), 0.0)) if not pd.isna(_safe_float(r.get("def_a"), float("nan"))) else None,
            "label": label,
        })
    return rows


# ── 품질 게이트 ───────────────────────────────────────────────────────────────

def quality_gate(rows: list[Row], reports_dir: Path) -> tuple[list[Row], pd.DataFrame]:  # 불량 데이터를 걸러내는 검문소예요 — 통과한 경기와 탈락한 경기 목록을 함께 돌려줘요
    clean: list[Row] = []  # 검문소를 통과한 경기들을 담을 빈 리스트예요
    rejected: list[dict] = []  # 탈락한 경기 정보를 담을 빈 리스트예요

    for r in rows:  # 모든 경기를 하나씩 검사해요
        agents_a = [p["agent"] for p in r["players_a"] if p.get("agent")]  # 팀A에서 요원 이름이 있는 선수만 모아요
        agents_b = [p["agent"] for p in r["players_b"] if p.get("agent")]  # 팀B에서 요원 이름이 있는 선수만 모아요
        reason = None  # 탈락 이유를 None으로 시작해요 (이유가 없으면 통과예요)

        if len(r["players_a"]) != 5 or len(r["players_b"]) != 5:  # 어느 팀이든 선수가 5명이 아니면 탈락이에요
            reason = "WRONG_AGENT_COUNT"
        elif not all(a in AGENT_ROLE_MAP for a in agents_a) or not all(a in AGENT_ROLE_MAP for a in agents_b):  # 알 수 없는 요원이 있으면 탈락이에요
            reason = "UNKNOWN_AGENT"
        elif r["map"] not in MAP_ORDER:  # 우리가 모르는 맵이면 탈락이에요
            reason = "UNKNOWN_MAP"
        elif r["label"] not in (0, 1):  # 승패 정답이 0이나 1이 아니면 탈락이에요
            reason = "INVALID_LABEL"
        elif any(  # 어느 선수든 전투점수(ACS)나 킬/데스 비율(K/D)이 빈 값이면 탈락이에요
            pd.isna(p.get("acs", float("nan"))) or pd.isna(p.get("kd", float("nan")))
            for p in r["players_a"] + r["players_b"]
        ):
            reason = "MISSING_STATS"
        elif r.get("weight", 0) <= 0:  # 신뢰도 점수가 0 이하면 탈락이에요
            reason = "INVALID_WEIGHT"
        elif r["score_a"] == r["score_b"]:  # 무승부면 누가 이겼는지 모르니까 탈락이에요
            reason = "DRAW"
        elif len(set(agents_a)) != 5 or len(set(agents_b)) != 5:  # 한 팀 안에 같은 요원이 중복으로 있으면 탈락이에요
            reason = "DUPLICATE_AGENT_IN_TEAM"

        if reason:  # 탈락 이유가 생겼으면
            rejected.append({  # 탈락한 경기의 기본 정보를 기록해요
                "source": r["source"],  # 데이터 출처 이름이에요
                "match_key": r["match_key"],  # 경기 고유 이름표예요
                "map": r["map"],  # 맵 이름이에요
                "team_a": r["team_a"],  # 팀A 이름이에요
                "team_b": r["team_b"],  # 팀B 이름이에요
                "label": r["label"],  # 승패 정답이에요
                "reject_reason": reason,  # 탈락 이유 코드예요
            })
        else:  # 탈락 이유가 없으면 통과예요
            clean.append(r)

    # 같은 경기가 여러 출처에 있으면 신뢰도 점수가 높은 것만 남겨요 (dedup_key 기준)
    dedup_map: dict[str, Row] = {}  # 고유 도장(dedup_key) → 경기 데이터를 연결하는 사전이에요
    for r in clean:  # 통과한 경기를 하나씩 확인해요
        dk = r["dedup_key"]  # 현재 경기의 고유 도장이에요
        if dk not in dedup_map:  # 이 도장이 처음 나오면
            dedup_map[dk] = r  # 그대로 저장해요
        elif r["weight"] > dedup_map[dk]["weight"]:  # 이미 저장된 것보다 신뢰도 점수가 높으면
            rejected.append({  # 기존에 저장된 것을 탈락 처리해요 (점수가 낮으니까요)
                "source": dedup_map[dk]["source"],
                "match_key": dedup_map[dk]["match_key"],
                "map": dedup_map[dk]["map"],
                "team_a": dedup_map[dk]["team_a"],
                "team_b": dedup_map[dk]["team_b"],
                "label": dedup_map[dk]["label"],
                "reject_reason": "DEDUP_LOW_WEIGHT",  # 중복 경기 중 신뢰도가 낮아서 탈락이에요
            })
            dedup_map[dk] = r  # 더 신뢰도 높은 것으로 교체해요
        else:  # 현재 경기가 이미 저장된 것보다 신뢰도 점수가 같거나 낮으면
            rejected.append({  # 현재 경기를 탈락 처리해요
                "source": r["source"],
                "match_key": r["match_key"],
                "map": r["map"],
                "team_a": r["team_a"],
                "team_b": r["team_b"],
                "label": r["label"],
                "reject_reason": "DEDUP_LOW_WEIGHT",  # 중복 경기 중 신뢰도가 낮아서 탈락이에요
            })

    return list(dedup_map.values()), pd.DataFrame(rejected) if rejected else pd.DataFrame()  # 통과한 경기 목록과 탈락한 경기 표를 함께 돌려줘요


# ── 피처 엔지니어링 ───────────────────────────────────────────────────────────

def _count_roles(agents: list[str]) -> dict[str, int]:  # 요원 목록을 받아서 역할군별로 몇 명인지 세어 사전으로 돌려주는 함수예요
    c = {"Duelist": 0, "Initiator": 0, "Controller": 0, "Sentinel": 0}  # 역할군별 카운트를 0으로 시작해요
    for a in agents:  # 요원 하나씩 확인해요
        role = get_role(a)  # 요원 이름으로 역할군을 찾아요
        if role and role in c:  # 알려진 역할군이면 카운트를 하나 올려요
            c[role] += 1
    return c  # 역할군별 카운트 사전을 돌려줘요


def build_features_phase1(rows: list[Row]) -> pd.DataFrame:  # 경기 목록에서 요원 역할군 기반 AI 참고 숫자 19가지를 만들어 표로 돌려주는 함수예요
    records = []  # AI 참고 숫자(피처) 딕셔너리를 담을 빈 리스트예요
    for r in rows:  # 각 경기를 하나씩 처리해요
        agents_a = [p["agent"] for p in r["players_a"]]  # 팀A 요원 이름 목록을 꺼내요
        agents_b = [p["agent"] for p in r["players_b"]]  # 팀B 요원 이름 목록을 꺼내요
        rc_a = _count_roles(agents_a)  # 팀A의 역할군별 요원 수를 세요
        rc_b = _count_roles(agents_b)  # 팀B의 역할군별 요원 수를 세요
        ad = ATK_ADV_MAP.get(r["map"], 0.0)  # 이 맵에서 공격 팀이 얼마나 유리한지 점수를 가져와요 (없으면 0.0)
        is_atk_a = int(  # 팀A가 공격 측이면 1, 수비 측이면 0이에요 (공격 점수 정보가 있을 때만 판단해요)
            r.get("atk_a") is not None
            and r.get("def_a") is not None
            and r.get("atk_a", 0) >= r.get("def_a", 0)
        )
        records.append({  # 이 경기의 AI 참고 숫자 딕셔너리를 만들어 리스트에 추가해요
            "source": r["source"],  # 데이터 출처 이름이에요
            "weight": r["weight"],  # 신뢰도 점수예요
            "match_key": r["match_key"],  # 경기 고유 이름표예요
            "dedup_key": r["dedup_key"],  # 중복 제거 고유 도장이에요
            "date": r["date"],  # 경기 날짜예요
            "event": r["event"],  # 대회 이름이에요
            "map": r["map"],  # 맵 이름이에요
            "team_a": r["team_a"],  # 팀A 이름이에요
            "team_b": r["team_b"],  # 팀B 이름이에요
            "score_a": r["score_a"],  # 팀A 점수예요
            "score_b": r["score_b"],  # 팀B 점수예요
            "agents_a": "|".join(agents_a),  # 팀A 요원 목록을 파이프(|)로 연결한 문자열로 저장해요
            "agents_b": "|".join(agents_b),  # 팀B 요원 목록을 파이프(|)로 연결한 문자열로 저장해요
            # 역할군 인원 수 (8개)
            "a_duelist": rc_a["Duelist"],  # 팀A 타격대(Duelist) 수예요
            "a_initiator": rc_a["Initiator"],  # 팀A 척후대(Initiator) 수예요
            "a_controller": rc_a["Controller"],  # 팀A 전략가(Controller) 수예요
            "a_sentinel": rc_a["Sentinel"],  # 팀A 감시자(Sentinel) 수예요
            "b_duelist": rc_b["Duelist"],  # 팀B 타격대(Duelist) 수예요
            "b_initiator": rc_b["Initiator"],  # 팀B 척후대(Initiator) 수예요
            "b_controller": rc_b["Controller"],  # 팀B 전략가(Controller) 수예요
            "b_sentinel": rc_b["Sentinel"],  # 팀B 감시자(Sentinel) 수예요
            # 역할군 인원 차이 (4개)
            "diff_duelist": rc_a["Duelist"] - rc_b["Duelist"],  # 팀A 타격대 수 - 팀B 타격대 수예요
            "diff_initiator": rc_a["Initiator"] - rc_b["Initiator"],  # 팀A 척후대 수 - 팀B 척후대 수예요
            "diff_controller": rc_a["Controller"] - rc_b["Controller"],  # 팀A 전략가 수 - 팀B 전략가 수예요
            "diff_sentinel": rc_a["Sentinel"] - rc_b["Sentinel"],  # 팀A 감시자 수 - 팀B 감시자 수예요
            # 시너지 피처 (2개)
            "a_double_initiator": int(rc_a["Initiator"] >= 2),  # 팀A에 척후대가 2명 이상이면 1이에요
            "b_double_initiator": int(rc_b["Initiator"] >= 2),  # 팀B에 척후대가 2명 이상이면 1이에요
            # 맵 관련 (3개)
            "map_encoded": MAP_ORDER.index(r["map"]) if r["map"] in MAP_ORDER else -1,  # 맵 이름을 순서 번호로 바꿔요 (목록에 없으면 -1)
            "atk_side_advantage": ad,  # 이 맵에서 공격 팀 유리도 점수예요
            "is_attacker_a": is_atk_a,  # 팀A가 공격 측이면 1, 아니면 0이에요
            "label": r["label"],  # 승패 정답이에요 (1 = 팀A 승, 0 = 팀B 승)
        })
    return pd.DataFrame(records)  # AI 참고 숫자 딕셔너리 리스트를 엑셀 표(DataFrame)로 바꿔서 돌려줘요


def _build_player_stat_lookup(df_train: pd.DataFrame, rows_map: dict[str, Row]) -> dict[str, dict[str, float]]:  # 훈련 경기들만 보고 선수별 평균 스탯 사전을 만드는 함수예요 (시험 데이터 정보가 새어들어가지 않도록 훈련 데이터만 써요)
    player_data: dict[str, list[dict]] = {}  # 선수 이름 → 그 선수의 모든 경기 스탯 리스트를 연결하는 사전이에요
    for mk in df_train["match_key"].unique():  # 훈련 세트에 있는 모든 고유 경기 이름표를 하나씩 확인해요
        r = rows_map.get(mk)  # 경기 이름표로 원본 경기 데이터를 찾아요
        if r is None:  # 못 찾으면 건너뛰어요
            continue
        for p in r["players_a"] + r["players_b"]:  # 양 팀 선수를 모두 순회해요
            name = p.get("player", "")  # 선수 이름을 꺼내요
            if not name:  # 이름이 없으면 건너뛰어요
                continue
            player_data.setdefault(name, []).append(p)  # 선수 이름 키에 이 경기 스탯을 추가해요

    result: dict[str, dict[str, float]] = {}  # 선수 이름 → 집계 스탯 사전을 담을 빈 결과 사전이에요
    for name, stats in player_data.items():  # 선수별로 모은 스탯 목록을 하나씩 처리해요
        def _avg(key: str) -> float:  # 특정 스탯의 빈 값(NaN) 제외 평균을 계산하는 내부 함수예요
            vals = [s[key] for s in stats if not pd.isna(s.get(key, float("nan")))]  # 빈 값 제외한 스탯 값 목록이에요
            return float(np.mean(vals)) if vals else float("nan")  # 유효한 값이 있으면 평균, 없으면 빈 값이에요

        clutch_vals = [s["clutch"] for s in stats if not pd.isna(s.get("clutch", float("nan")))]  # 빈 값 제외한 클러치 수 목록이에요
        result[name] = {  # 선수별 집계 스탯 사전을 만들어요
            "avg_acs": _avg("acs"),  # 평균 전투점수(ACS)예요
            "avg_kd": _avg("kd"),  # 평균 킬/데스 비율이에요
            "avg_kast": _avg("kast"),  # 평균 생존기여율(KAST)이에요
            "avg_adr": _avg("adr"),  # 평균 라운드당 피해량(ADR)이에요
            "avg_hs": _avg("hs"),  # 평균 헤드샷 비율이에요
            "max_clutch": float(np.max(clutch_vals)) if clutch_vals else float("nan"),  # 클러치 최대 기록이에요 (데이터 없으면 빈 값)
            "avg_fk": _avg("fk"),  # 평균 선제킬 수예요
            "avg_fd": _avg("fd"),  # 평균 선제사 수예요
            "avg_assists": _avg("assists"),  # 평균 어시스트 수예요
        }
    return result  # 선수 이름 → 집계 스탯 사전을 돌려줘요


def _build_agent_combo_lookup(df_train: pd.DataFrame, rows_map: dict[str, Row]) -> dict:  # 훈련 경기들만 보고 요원·맵 조합별 승률·픽률·경험치를 계산하는 함수예요 (시험 데이터 정보가 새어들어가지 않도록 훈련 데이터만 써요)
    agent_map: dict[tuple, dict] = {}  # (요원, 맵) → {이긴 횟수, 총 횟수} 사전이에요
    agent_exp: dict[tuple, int] = {}  # (선수, 요원) → 그 요원을 플레이한 횟수 사전이에요
    map_totals: dict[str, int] = {}  # 맵 이름 → 총 경기 수 사전이에요

    for mk in df_train["match_key"].unique():  # 훈련 세트의 모든 고유 경기 이름표를 하나씩 확인해요
        r = rows_map.get(mk)  # 경기 이름표로 원본 경기 데이터를 찾아요
        if r is None:  # 못 찾으면 건너뛰어요
            continue
        map_n = r["map"]  # 이 경기의 맵 이름이에요
        map_totals[map_n] = map_totals.get(map_n, 0) + 1  # 이 맵에서 경기가 하나 더 치러진 거예요
        for side_players, won in [(r["players_a"], r["label"] == 1), (r["players_b"], r["label"] == 0)]:  # 팀A(팀A 승이면 won=True)·팀B(팀B 승이면 won=True) 순서로 처리해요
            for p in side_players:  # 팀의 각 선수를 확인해요
                ag, pl = p.get("agent", ""), p.get("player", "")  # 요원 이름과 선수 이름을 꺼내요
                if not ag:  # 요원 이름이 없으면 건너뛰어요
                    continue
                key = (ag, map_n)  # (요원, 맵) 쌍을 사전 키로 써요
                s = agent_map.setdefault(key, {"wins": 0, "total": 0})  # 처음 나온 조합이면 0으로 초기화해요
                s["total"] += 1  # 이 요원·맵 조합이 등장한 횟수를 하나 올려요
                if won:  # 이 팀이 이긴 경기면
                    s["wins"] += 1  # 이긴 횟수도 하나 올려요
                if pl:  # 선수 이름이 있으면
                    agent_exp[(pl, ag)] = agent_exp.get((pl, ag), 0) + 1  # 이 선수가 이 요원을 플레이한 횟수를 하나 올려요

    wr: dict[tuple, float] = {}  # (요원, 맵) → 승률 사전이에요
    pr: dict[tuple, float] = {}  # (요원, 맵) → 픽률 사전이에요
    for (ag, map_n), s in agent_map.items():  # 요원·맵 조합별 집계 결과를 하나씩 처리해요
        wr[(ag, map_n)] = s["wins"] / s["total"] if s["total"] else 0.5  # 승률 = 이긴 횟수 ÷ 총 횟수 (데이터 없으면 50%)
        pr[(ag, map_n)] = s["total"] / max(map_totals.get(map_n, 1), 1)  # 픽률 = 이 요원이 이 맵에서 등장한 횟수 ÷ 이 맵 총 경기 수

    return {"wr": wr, "pr": pr, "exp": agent_exp}  # 승률·픽률·경험치 세 사전을 하나로 묶어서 돌려줘요


def _add_map_agent_features(df: pd.DataFrame, combo_lookup: dict) -> pd.DataFrame:
    """train 집계 기반 combo_lookup을 써서 팀별 맵 평균 승률 피처 3개를 추가한다."""
    wr_lookup = combo_lookup["wr"]
    a_means: list[float] = []
    b_means: list[float] = []
    for _, row in df.iterrows():
        map_n = row["map"]
        agents_a = [a for a in str(row.get("agents_a", "")).split("|") if a]
        agents_b = [a for a in str(row.get("agents_b", "")).split("|") if a]
        a_wrs = [wr_lookup.get((ag, map_n), 0.5) for ag in agents_a]
        b_wrs = [wr_lookup.get((ag, map_n), 0.5) for ag in agents_b]
        a_means.append(float(np.mean(a_wrs)) if a_wrs else 0.5)
        b_means.append(float(np.mean(b_wrs)) if b_wrs else 0.5)
    out = df.copy()
    out["a_map_wr_mean"] = a_means
    out["b_map_wr_mean"] = b_means
    out["diff_map_wr"] = out["a_map_wr_mean"] - out["b_map_wr_mean"]
    return out


def _add_phase2_features(  # 요원 역할군 숫자(Phase 1) 표에 선수 개인 스탯 기반 숫자(Phase 2)를 추가해서 돌려주는 함수예요
    df: pd.DataFrame,  # Phase 1 AI 참고 숫자가 담긴 엑셀 표예요
    rows_map: dict[str, Row],  # 경기 이름표 → 원본 경기 데이터를 연결하는 사전이에요 (선수 정보를 다시 꺼낼 때 써요)
    player_lookup: dict[str, dict[str, float]],  # 선수 이름 → 집계 스탯 사전이에요 (훈련 데이터 기반)
    combo_lookup: dict,  # 요원·맵 조합 승률·픽률·경험치 사전이에요 (훈련 데이터 기반)
    medians: dict[str, float],  # 스탯이 빈 값일 때 대신 쓸 중앙값 사전이에요
) -> pd.DataFrame:
    records = []  # Phase 2 AI 참고 숫자를 담을 빈 리스트예요
    for _, row in df.iterrows():  # Phase 1 표의 각 줄(경기)을 하나씩 처리해요
        r = rows_map.get(row["match_key"])  # 경기 이름표로 원본 경기 데이터를 찾아요
        map_n = row["map"]  # 현재 경기의 맵 이름이에요
        pa = r["players_a"] if r else []  # 원본 데이터가 있으면 팀A 선수 리스트, 없으면 빈 리스트예요
        pb = r["players_b"] if r else []  # 원본 데이터가 있으면 팀B 선수 리스트, 없으면 빈 리스트예요

        def _stat(players: list[dict], key: str, agg: str, side: str) -> float:  # 선수 목록에서 특정 스탯의 평균(mean) 또는 최대값(max)을 계산하는 내부 함수예요
            vals = [  # 각 선수의 해당 스탯을 집계 사전에서 찾아 목록을 만들어요
                player_lookup.get(p.get("player", ""), {}).get(key, float("nan"))
                for p in players
            ]
            valid = [v for v in vals if not pd.isna(v)]  # 빈 값(NaN)을 제외한 유효한 값 목록이에요
            if valid:  # 유효한 값이 있으면
                return float(np.max(valid)) if agg == "max" else float(np.mean(valid))  # max이면 최대값, 아니면 평균을 돌려줘요
            return medians.get(f"{side}_{key}", 0.0)  # 유효한 값이 없으면 미리 정해둔 중앙값을 대신 써요

        def _synergy(players: list[dict], side: str) -> dict:  # 팀 전체의 협동 관련 숫자(선제킬/사 비율·어시스트·KAST 균형도)를 계산하는 내부 함수예요
            fk = sum(p.get("fk", 0) or 0 for p in players)  # 팀 전체 선제킬 수를 더해요
            fd = sum(p.get("fd", 0) or 0 for p in players)  # 팀 전체 선제사 수를 더해요
            assists = [p.get("assists", 0) or 0 for p in players]  # 각 선수 어시스트 수를 모아요
            kast_vals = [  # 각 선수의 집계 KAST 값을 집계 사전에서 찾아 목록을 만들어요
                player_lookup.get(p.get("player", ""), {}).get("avg_kast", float("nan"))
                for p in players
            ]
            kast_valid = [v for v in kast_vals if not pd.isna(v)]  # 빈 값 제외한 유효 KAST 목록이에요
            return {  # 팀 협동 관련 숫자 사전을 돌려줘요
                f"{side}_fk_fd_ratio": fk / max(fd, 1e-9),  # 선제킬 ÷ 선제사 비율이에요 (선제사가 0일 때 나누기 오류를 막으려고 1e-9를 써요)
                f"{side}_avg_assists": float(np.mean(assists)) if assists else 0.0,  # 팀 평균 어시스트 수예요
                f"{side}_kast_std": float(np.std(kast_valid)) if len(kast_valid) > 1 else 0.0,  # 팀원들 KAST의 표준편차예요 (1명 이하면 0)
            }

        def _combo(players: list[dict], side: str) -> dict:  # 각 선수의 요원·맵 조합 승률·픽률·경험치를 찾아서 팀 평균을 계산하는 내부 함수예요
            wrs, prs, exps = [], [], []  # 승률·픽률·경험치 값을 담을 빈 리스트들이에요
            for p in players:  # 각 선수를 확인해요
                ag, pl = p.get("agent", ""), p.get("player", "")  # 요원 이름과 선수 이름을 꺼내요
                wrs.append(combo_lookup["wr"].get((ag, map_n), 0.5))  # 이 요원이 이 맵에서 가진 승률이에요 (데이터 없으면 50%)
                prs.append(combo_lookup["pr"].get((ag, map_n), 0.0))  # 이 요원이 이 맵에서 선택된 비율이에요 (데이터 없으면 0)
                exps.append(combo_lookup["exp"].get((pl, ag), 0))  # 이 선수가 이 요원을 몇 번 플레이했는지예요 (데이터 없으면 0)
            return {  # 팀 평균 요원·맵 조합 숫자 사전을 돌려줘요
                f"{side}_avg_agent_map_wr": float(np.mean(wrs)) if wrs else 0.5,  # 팀 평균 요원·맵 승률이에요
                f"{side}_avg_agent_pick_rate": float(np.mean(prs)) if prs else 0.0,  # 팀 평균 요원·맵 픽률이에요
                f"{side}_avg_agent_exp": float(np.mean(exps)) if exps else 0.0,  # 팀 평균 선수·요원 경험 횟수예요
            }

        rec: dict[str, float] = {}  # 현재 경기의 Phase 2 숫자를 담을 빈 사전이에요
        for side, players in [("a", pa), ("b", pb)]:  # 팀A("a")와 팀B("b")를 차례로 처리해요
            for key, agg in [("avg_acs","mean"),("avg_kd","mean"),("avg_kast","mean"),  # 각 스탯과 집계 방법(평균 또는 최대) 쌍을 처리해요
                              ("avg_adr","mean"),("avg_hs","mean")]:
                rec[f"{side}_{key}"] = _stat(players, key, agg, side)  # 스탯 집계 숫자를 계산해서 저장해요
            rec.update(_synergy(players, side))  # 팀 협동 관련 숫자를 추가해요
            rec.update(_combo(players, side))  # 요원·맵 조합 숫자를 추가해요

        for key in ("avg_acs", "avg_kd", "avg_kast", "avg_adr", "avg_hs"):  # 비교할 스탯 이름 목록이에요
            rec[f"diff_{key}"] = rec.get(f"a_{key}", 0.0) - rec.get(f"b_{key}", 0.0)  # 팀A 스탯에서 팀B 스탯을 빼요 (augment_swap이 나중에 diff_* 부호를 자동으로 반전해줘요)
        records.append(rec)  # 현재 경기의 Phase 2 숫자 사전을 리스트에 추가해요

    phase2 = pd.DataFrame(records, index=df.index)  # Phase 2 숫자 리스트를 표로 바꿔요 (Phase 1 표와 줄 번호를 맞춰요)
    return pd.concat([df, phase2], axis=1)  # Phase 1 표와 Phase 2 표를 옆으로 붙여서 함께 돌려줘요


# ── 분할 + 증강 ───────────────────────────────────────────────────────────────

def _build_team_form_lookup(df_train: pd.DataFrame) -> dict:
    """훈련 경기만 보고 팀별 폼 통계를 계산한다. 데이터 누수 없음.

    df_train에는 team_a, team_b, label, date 컬럼이 포함되어 있어야 한다.
    미등장 팀 기본값: team_wr=0.5, team_recent_wr=0.5, team_streak=0, h2h_wr=0.5
    date 빈값은 '0000-01-01'로 처리해 정렬에서 oldest 취급한다.

    LOO(Leave-One-Out) 지원을 위해 team_wins / team_total / h2h_wins / h2h_total
    원시 카운트도 함께 반환한다. _add_team_form_features(is_train=True) 시 활용.
    """
    team_matches: dict[str, list[tuple[str, int]]] = {}  # team → [(date, win)]
    h2h: dict[tuple, list[int]] = {}  # (ta, tb) → [win_a, ...]

    for _, row in df_train.drop_duplicates("match_key").iterrows():
        ta = str(row.get("team_a", "") or "").strip()
        tb = str(row.get("team_b", "") or "").strip()
        if not ta or not tb:
            continue
        label = int(row.get("label", 0))
        date_str = str(row.get("date", "") or "").strip() or "0000-01-01"
        won_a = label == 1

        team_matches.setdefault(ta, []).append((date_str, 1 if won_a else 0))
        team_matches.setdefault(tb, []).append((date_str, 0 if won_a else 1))
        h2h.setdefault((ta, tb), []).append(1 if won_a else 0)
        h2h.setdefault((tb, ta), []).append(0 if won_a else 1)

    team_wr: dict[str, float] = {}
    team_recent_wr: dict[str, float] = {}
    team_streak: dict[str, int] = {}
    team_wins_count: dict[str, int] = {}
    team_total_count: dict[str, int] = {}

    for team, results in team_matches.items():
        results.sort(key=lambda x: x[0])
        wins = [w for _, w in results]
        W, T = sum(wins), len(wins)
        team_wins_count[team] = W
        team_total_count[team] = T
        # Laplace 스무딩: 경기 수 적을 때 극단값(0/1) 방지
        team_wr[team] = (W + _FORM_SMOOTH_K * _FORM_SMOOTH_PRIOR) / (T + _FORM_SMOOTH_K)
        recent = wins[-10:] if len(wins) >= 10 else wins
        rW, rT = sum(recent), len(recent)
        team_recent_wr[team] = (rW + _FORM_SMOOTH_K * _FORM_SMOOTH_PRIOR) / (rT + _FORM_SMOOTH_K) if rT else 0.5
        streak = 0
        for w in reversed(wins):
            if streak == 0:
                streak = 1 if w else -1
            elif (w == 1 and streak > 0) or (w == 0 and streak < 0):
                streak += 1 if w else -1
            else:
                break
        team_streak[team] = streak

    h2h_wr: dict[tuple, float] = {
        k: (sum(v) + _FORM_SMOOTH_K * _FORM_SMOOTH_PRIOR) / (len(v) + _FORM_SMOOTH_K)
        for k, v in h2h.items() if v
    }
    h2h_wins_count: dict[tuple, int] = {k: sum(v) for k, v in h2h.items()}
    h2h_total_count: dict[tuple, int] = {k: len(v) for k, v in h2h.items()}

    return {
        "team_wr": team_wr,
        "team_recent_wr": team_recent_wr,
        "team_streak": team_streak,
        "h2h_wr": h2h_wr,
        "team_wins": team_wins_count,
        "team_total": team_total_count,
        "h2h_wins": h2h_wins_count,
        "h2h_total": h2h_total_count,
    }


def _add_team_form_features(
    df: pd.DataFrame, form_lookup: dict, is_train: bool = False
) -> pd.DataFrame:
    """팀별 폼 피처 9개를 추가한다. augment_swap() 호출 전에 사용해야 한다.

    team_a/team_b 컬럼을 직접 참조하므로 rows_map 불필요.
    미등장 팀: wr=0.5, recent_wr=0.5, streak=0, h2h=0.5

    is_train=True 시 LOO(Leave-One-Out)로 자기참조 누수를 제거한다.
    team_wr / h2h_wr에만 LOO 적용; recent_wr·streak은 집계 특성상 그대로 사용.
    """
    tw = form_lookup["team_wr"]
    rw = form_lookup["team_recent_wr"]
    ts = form_lookup["team_streak"]
    h2h = form_lookup["h2h_wr"]
    tw_wins = form_lookup.get("team_wins", {})
    tw_total = form_lookup.get("team_total", {})
    h2h_wins = form_lookup.get("h2h_wins", {})
    h2h_total = form_lookup.get("h2h_total", {})

    a_wr, b_wr, a_rwr, b_rwr, a_str, b_str, a_h2h, b_h2h = ([] for _ in range(8))

    for _, row in df.iterrows():
        ta = str(row.get("team_a", "") or "").strip()
        tb = str(row.get("team_b", "") or "").strip()
        label = int(row.get("label", 0))
        won_a = label == 1

        if is_train:
            # LOO + Laplace 스무딩: 현재 경기 결과를 제외하되 극단값(0/1) 방지
            _prior = _FORM_SMOOTH_K * _FORM_SMOOTH_PRIOR
            W_a, T_a = tw_wins.get(ta, 0), tw_total.get(ta, 0)
            loo_a = (W_a - (1 if won_a else 0) + _prior) / max(T_a - 1 + _FORM_SMOOTH_K, _FORM_SMOOTH_K)
            W_b, T_b = tw_wins.get(tb, 0), tw_total.get(tb, 0)
            loo_b = (W_b - (0 if won_a else 1) + _prior) / max(T_b - 1 + _FORM_SMOOTH_K, _FORM_SMOOTH_K)
            W_ab, T_ab = h2h_wins.get((ta, tb), 0), h2h_total.get((ta, tb), 0)
            loo_h2h_a = (W_ab - (1 if won_a else 0) + _prior) / max(T_ab - 1 + _FORM_SMOOTH_K, _FORM_SMOOTH_K)
            W_ba, T_ba = h2h_wins.get((tb, ta), 0), h2h_total.get((tb, ta), 0)
            loo_h2h_b = (W_ba - (0 if won_a else 1) + _prior) / max(T_ba - 1 + _FORM_SMOOTH_K, _FORM_SMOOTH_K)
            a_wr.append(loo_a)
            b_wr.append(loo_b)
            a_h2h.append(loo_h2h_a)
            b_h2h.append(loo_h2h_b)
        else:
            a_wr.append(tw.get(ta, 0.5))
            b_wr.append(tw.get(tb, 0.5))
            a_h2h.append(h2h.get((ta, tb), 0.5))
            b_h2h.append(h2h.get((tb, ta), 0.5))

        a_rwr.append(rw.get(ta, 0.5))
        b_rwr.append(rw.get(tb, 0.5))
        a_str.append(float(ts.get(ta, 0)))
        b_str.append(float(ts.get(tb, 0)))

    out = df.copy()
    out["a_team_wr"] = a_wr
    out["b_team_wr"] = b_wr
    out["a_team_recent_wr"] = a_rwr
    out["b_team_recent_wr"] = b_rwr
    out["a_win_streak"] = a_str
    out["b_win_streak"] = b_str
    out["a_h2h_wr"] = a_h2h
    out["b_h2h_wr"] = b_h2h
    out["diff_h2h_wr"] = out["a_h2h_wr"] - out["b_h2h_wr"]
    out["diff_team_wr"] = out["a_team_wr"] - out["b_team_wr"]
    return out


def augment_swap(df: pd.DataFrame) -> pd.DataFrame:  # 팀A와 팀B를 통째로 바꿔서 데이터를 두 배로 늘리는 함수예요 — 원본과 뒤집은 버전을 합쳐서 돌려줘요
    """A↔B 스왑 증강: prefix(a_/b_) + suffix(_a/_b) 피처 모두 교환, diff 부호 반전."""
    swap = df.copy()  # 원본 표를 복사해서 팀 교환에 쓸 복사본을 만들어요

    # 1단계: "a_"로 시작하는 열과 "b_"로 시작하는 열의 이름을 서로 바꿔요
    a_pre = [c for c in df.columns if c.startswith("a_")]  # "a_"로 시작하는 열 이름 목록이에요 (팀A 숫자들)
    b_pre = [c for c in df.columns if c.startswith("b_")]  # "b_"로 시작하는 열 이름 목록이에요 (팀B 숫자들)
    rename: dict[str, str] = {}  # 바꿀 열 이름을 정리하는 사전이에요
    for c in a_pre:  # 팀A 열을 팀B 열 이름으로 바꿔요
        rename[c] = "b_" + c[2:]  # 예: "a_duelist" → "b_duelist"
    for c in b_pre:  # 팀B 열을 팀A 열 이름으로 바꿔요
        rename[c] = "a_" + c[2:]  # 예: "b_duelist" → "a_duelist"
    swap = swap.rename(columns=rename)  # 열 이름 교환을 실제로 적용해요

    # 2단계: "_a"로 끝나는 열과 "_b"로 끝나는 열도 서로 바꿔요 (1단계에서 못 처리한 것만)
    processed = set(a_pre) | set(b_pre)  # 1단계에서 이미 처리한 열 이름을 기억해둬요
    rename2: dict[str, str] = {}  # 2단계용 열 이름 교환 사전이에요
    for c in df.columns:  # 모든 열을 확인해요
        if c in processed:  # 이미 처리한 열이면 건너뛰어요
            continue
        if c.endswith("_a"):  # "_a"로 끝나는 열이면
            pair = c[:-2] + "_b"  # 대응하는 "_b" 열 이름을 만들어요
            if pair in df.columns:  # 대응 열이 실제로 있으면 교환 등록해요
                rename2[c] = pair
        elif c.endswith("_b"):  # "_b"로 끝나는 열이면
            pair = c[:-2] + "_a"  # 대응하는 "_a" 열 이름을 만들어요
            if pair in df.columns:  # 대응 열이 실제로 있으면 교환 등록해요
                rename2[c] = pair
    swap = swap.rename(columns=rename2)  # 2단계 열 이름 교환을 실제로 적용해요

    # 3단계: "diff_"로 시작하는 차이 숫자들은 부호를 반대로 뒤집어요
    for c in [c for c in swap.columns if c.startswith("diff_")]:  # "diff_"로 시작하는 열 목록이에요
        swap[c] = -swap[c]  # 팀A-팀B 차이였던 것이 팀B-팀A 차이가 되니까 부호를 뒤집어요

    # 4단계: is_attacker_a는 "_b" 짝이 없으니 팀 교환 시 직접 반전해요
    if "is_attacker_a" in swap.columns:  # is_attacker_a 열이 있으면
        swap["is_attacker_a"] = 1 - swap["is_attacker_a"]  # 0→1, 1→0으로 바꿔요 (공격 팀도 바뀌니까요)

    # 5단계: 승패 정답(label)도 반전해요
    swap["label"] = 1 - df["label"].values  # 팀A 승(1)→팀B 승(0), 팀B 승(0)→팀A 승(1)으로 뒤집어요

    # 6단계: 교환된 줄임을 표시해요
    swap["match_key"] = df["match_key"].astype(str) + "_swap"  # 교환된 줄의 경기 이름표에 "_swap"을 붙여서 원본과 구분해요
    swap["swap_flag"] = 1  # 교환된 줄임을 알리는 표시예요 (1 = 교환 줄)

    original = df.copy()  # 원본을 복사해요
    original["swap_flag"] = 0  # 원본 줄임을 알리는 표시예요 (0 = 원본 줄)
    return pd.concat([original, swap], ignore_index=True)  # 원본 + 교환된 줄을 위아래로 붙여서 돌려줘요


def split_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:  # 같은 경기 데이터가 훈련용과 시험용에 동시에 들어가지 않도록 안전하게 70/15/15로 나눠주는 함수예요
    """match_key 그룹 단위 70/15/15 분할 (증강 없음 — run()에서 Phase 2 이후 적용)."""
    idx = np.arange(len(df))  # 0부터 시작하는 줄 번호 배열을 만들어요
    groups = df["match_key"].values  # 경기 이름표 배열이에요 (같은 경기끼리 같은 그룹으로 처리해요)

    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=42)  # 1차 나누기: 70% 훈련용 / 30% 나머지 (random_state=42는 항상 같은 결과가 나오게 하는 씨앗 번호예요)
    train_idx, temp_idx = next(gss1.split(idx, groups=groups))  # 1차 나누기 결과로 훈련 줄 번호와 나머지 줄 번호를 얻어요

    temp_groups = groups[temp_idx]  # 나머지 30%의 경기 이름표 배열이에요
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=42)  # 2차 나누기: 나머지 30%를 절반씩 — 결과적으로 검증용 15% / 테스트용 15%가 돼요
    val_rel, test_rel = next(gss2.split(temp_idx, groups=temp_groups))  # 2차 나누기 결과로 검증 줄 번호와 테스트 줄 번호를 얻어요 (나머지 30% 안에서의 상대 번호예요)
    val_idx = temp_idx[val_rel]  # 전체 표 기준 검증용 줄 번호로 변환해요
    test_idx = temp_idx[test_rel]  # 전체 표 기준 테스트용 줄 번호로 변환해요

    return df.iloc[train_idx].copy(), df.iloc[val_idx].copy(), df.iloc[test_idx].copy()  # 훈련/검증/테스트 표 복사본을 돌려줘요


# ── 진입점 ────────────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> None:  # 전처리 파이프라인 7단계를 순서대로 실행하는 메인 함수예요
    input_dir = Path(args.input)  # 터미널에서 받은 입력 폴더 경로를 Path 객체로 만들어요
    output_dir = Path(args.output)  # 터미널에서 받은 출력 폴더 경로를 Path 객체로 만들어요
    reports_dir = Path(args.reports)  # 터미널에서 받은 리포트 폴더 경로를 Path 객체로 만들어요
    output_dir.mkdir(parents=True, exist_ok=True)  # 출력 폴더가 없으면 새로 만들어요 (이미 있으면 그냥 두어요)
    reports_dir.mkdir(parents=True, exist_ok=True)  # 리포트 폴더가 없으면 새로 만들어요 (이미 있으면 그냥 두어요)

    print("[1/7] 파서 실행...")  # 1단계 시작을 알려요
    rows_vct = parse_vct_dir(input_dir)  # VCT·Challengers 데이터를 파싱해서 경기 목록을 만들어요
    rows_single = parse_single_csv(input_dir)  # qualidea·ediashtarevin 데이터를 파싱해서 경기 목록을 만들어요
    rows_piyush = parse_piyush_events_dir(input_dir)  # piyush 이벤트 데이터를 파싱해서 경기 목록을 만들어요
    include_vlrgg = bool(getattr(args, "include_vlrgg_detail", False))
    vlrgg_path = Path(getattr(args, "vlrgg_pipeline_matches", "data/processed/vlrgg_pipeline_matches.csv"))
    rows_vlrgg = parse_vlrgg_pipeline_matches(vlrgg_path) if include_vlrgg else []
    all_rows = rows_vct + rows_single + rows_piyush + rows_vlrgg  # 세 목록과 opt-in VLR 상세 행을 하나로 합쳐요

    src_raw = {  # 출처별로 원시 경기가 몇 건인지 세어두는 사전이에요
        "kaggle_vct": sum(1 for r in rows_vct if r["source"] == "kaggle_vct"),  # VCT 출처 경기 수예요
        "kaggle_challengers": sum(1 for r in rows_vct if r["source"] == "kaggle_challengers"),  # Challengers 출처 경기 수예요
        "kaggle_qualidea": sum(1 for r in rows_single if r["source"] == "kaggle_qualidea"),  # qualidea 출처 경기 수예요
        "kaggle_ediashtarevin": sum(1 for r in rows_single if r["source"] == "kaggle_ediashtarevin"),  # ediashtarevin 출처 경기 수예요
        "kaggle_piyush2025": sum(1 for r in rows_piyush if r["source"] == "kaggle_piyush2025"),  # piyush 2025 출처 경기 수예요
        "kaggle_piyush2024": sum(1 for r in rows_piyush if r["source"] == "kaggle_piyush2024"),  # piyush 2024 출처 경기 수예요
        "vlrgg_direct_detail": len(rows_vlrgg),
    }
    print(f"  A(vct+ch): {len(rows_vct)}  B(single): {len(rows_single)}  C(piyush): {len(rows_piyush)}  VLR:{len(rows_vlrgg)}")  # 출처 그룹별 경기 수를 화면에 보여줘요

    print("[2/7] 품질 게이트 + dedup...")  # 2단계 시작을 알려요 — 불량 데이터 걸러내기 + 중복 제거예요
    clean_rows, rejected_df = quality_gate(all_rows, reports_dir)  # 검문소를 통과한 경기와 탈락한 경기를 나눠요
    print(f"  통과: {len(clean_rows)}  리젝트: {len(rejected_df)}")  # 통과·탈락 경기 수를 화면에 보여줘요

    flat = [  # 통과한 경기들을 CSV에 저장하기 좋은 납작한 딕셔너리 형태로 바꿔요
        {
            "source": r["source"], "weight": r["weight"],  # 출처 이름·신뢰도 점수예요
            "match_key": r["match_key"], "dedup_key": r["dedup_key"],  # 고유 이름표·중복 제거 도장이에요
            "date": r["date"], "event": r["event"], "map": r["map"],  # 날짜·대회 이름·맵이에요
            "team_a": r["team_a"], "team_b": r["team_b"],  # 팀 이름들이에요
            "score_a": r["score_a"], "score_b": r["score_b"],  # 점수들이에요
            "agents_a": "|".join(p["agent"] for p in r["players_a"]),  # 팀A 요원 목록을 파이프(|)로 연결해요
            "agents_b": "|".join(p["agent"] for p in r["players_b"]),  # 팀B 요원 목록을 파이프(|)로 연결해요
            "label": r["label"],  # 승패 정답이에요
        }
        for r in clean_rows  # 통과한 모든 경기에 대해 변환해요
    ]
    df_clean = pd.DataFrame(flat)  # 납작한 딕셔너리 목록을 엑셀 표(DataFrame)로 바꿔요
    df_clean.to_csv(output_dir / "matches_clean.csv", index=False)  # 통과한 경기 목록을 CSV 파일로 저장해요
    if not rejected_df.empty:  # 탈락한 경기가 있으면
        rejected_df.to_csv(reports_dir / "rejected_matches.csv", index=False)  # 탈락 내역을 reports 폴더에 저장해요
    print(f"  matches_clean.csv: {len(df_clean)}행")  # 저장된 경기 수를 화면에 보여줘요

    print("[3/7] Phase 1 피처 생성...")  # 3단계 시작을 알려요 — 요원 역할군 기반 AI 참고 숫자 만들기예요
    df_feat = build_features_phase1(clean_rows)  # 통과한 경기들로 Phase 1 AI 참고 숫자 표를 만들어요
    df_feat = _add_context_features(df_feat)  # P5/P6: 지역·등급·시즌·패치 피처 추가
    rows_map = {r["match_key"]: r for r in clean_rows}  # 경기 이름표 → 원본 데이터 사전을 만들어요 (Phase 2에서 선수 정보를 다시 꺼낼 때 써요)

    print("[4/7] 데이터 분할 (70/15/15)...")  # 4단계 시작을 알려요 — 훈련/검증/테스트 세트로 나누기예요
    augment_train = not getattr(args, "no_augment_train", False)  # "--no-augment-train" 옵션이 없으면 팀 교환 증강을 써요
    df_train, df_val, df_test = split_features(df_feat)  # 경기 이름표 그룹 단위로 70/15/15 비율로 나눠요
    print(f"  split(pre-aug): train:{len(df_train)}  val:{len(df_val)}  test:{len(df_test)}")  # 증강 전 각 세트 경기 수를 화면에 보여줘요

    print("[5/7] Phase 2 집계 (train 전용)...")  # 5단계 시작을 알려요 — 훈련 세트만 보고 선수·요원 통계를 만들어요
    player_lookup = _build_player_stat_lookup(df_train, rows_map)  # 훈련 세트 기반 선수별 집계 스탯 사전을 만들어요
    combo_lookup = _build_agent_combo_lookup(df_train, rows_map)  # 훈련 세트 기반 요원·맵 조합 통계 사전을 만들어요

    # Streamlit UI가 나중에 쓸 수 있도록 통계 캐시를 JSON 파일로 저장해요
    def _nan_to_none(v: float) -> float | None:  # 빈 값(NaN)을 JSON에서 쓸 수 있는 None으로 바꾸는 내부 함수예요
        return None if isinstance(v, float) and np.isnan(v) else v  # float NaN이면 None, 아니면 그대로 둬요

    player_stats_cache = {  # 선수별 집계 스탯을 JSON 저장용으로 변환해요
        name: {k: _nan_to_none(v) for k, v in stats.items()}  # 각 스탯의 빈 값을 None으로 바꿔요
        for name, stats in player_lookup.items()  # 모든 선수에 대해 변환해요
    }
    with open(output_dir / "player_stats.json", "w", encoding="utf-8") as f:  # player_stats.json 파일을 열어요
        json.dump(player_stats_cache, f, ensure_ascii=False)  # 선수 통계를 UTF-8 JSON으로 저장해요

    agent_map_cache = {  # 요원·맵 조합 통계를 JSON 저장용으로 변환해요
        "wr": {f"{ag}|{mp}": float(v) for (ag, mp), v in combo_lookup["wr"].items()},  # 승률: "요원|맵" → 소수예요
        "pr": {f"{ag}|{mp}": float(v) for (ag, mp), v in combo_lookup["pr"].items()},  # 픽률: "요원|맵" → 소수예요
        "exp": {f"{pl}|{ag}": int(v) for (pl, ag), v in combo_lookup["exp"].items()},  # 경험치: "선수|요원" → 정수예요
    }
    with open(output_dir / "agent_map_stats.json", "w", encoding="utf-8") as f:  # agent_map_stats.json 파일을 열어요
        json.dump(agent_map_cache, f, ensure_ascii=False)  # 요원·맵 통계를 UTF-8 JSON으로 저장해요

    all_acs = [  # 전체 경기에서 빈 값이 아닌 ACS 값만 모아요 (대체값 계산에 써요)
        p["acs"] for r in clean_rows
        for p in r["players_a"] + r["players_b"]
        if not pd.isna(p.get("acs", float("nan")))
    ]
    med_acs = float(np.median(all_acs)) if all_acs else 200.0  # ACS 중앙값을 구해요 (데이터가 없으면 200으로 대신 써요)
    medians = {  # Phase 2 AI 참고 숫자에서 빈 값이 있을 때 대신 쓸 기본값 사전이에요
        "a_avg_acs": med_acs, "b_avg_acs": med_acs,  # ACS 빈 값 대체값이에요
        "a_avg_kd": 1.0, "b_avg_kd": 1.0,  # K/D 빈 값 대체값이에요 (1.0 = 킬과 데스가 같은 수준)
        "a_avg_kast": 0.7, "b_avg_kast": 0.7,  # KAST 빈 값 대체값이에요 (0.7 = 프로 평균 수준)
        "a_avg_adr": 130.0, "b_avg_adr": 130.0,  # ADR 빈 값 대체값이에요 (130 = 프로 평균 수준)
        "a_avg_hs": 0.2, "b_avg_hs": 0.2,  # 헤드샷 비율 빈 값 대체값이에요 (20% = 프로 평균)
    }

    print("[6/7] Phase 2 피처 추가 → train 증강...")  # 6단계 시작을 알려요 — 선수 스탯 숫자 추가 + 훈련 데이터 두 배 늘리기예요
    df_train = _add_phase2_features(df_train, rows_map, player_lookup, combo_lookup, medians)  # 훈련 세트에 Phase 2 숫자를 추가해요
    df_val = _add_phase2_features(df_val, rows_map, player_lookup, combo_lookup, medians)  # 검증 세트에 Phase 2 숫자를 추가해요
    df_test = _add_phase2_features(df_test, rows_map, player_lookup, combo_lookup, medians)  # 테스트 세트에 Phase 2 숫자를 추가해요

    # 맵별 요원 승률 피처 추가 (train 집계 기반, 데이터 누수 없음)
    df_train = _add_map_agent_features(df_train, combo_lookup)
    df_val = _add_map_agent_features(df_val, combo_lookup)
    df_test = _add_map_agent_features(df_test, combo_lookup)

    # 팀 최근 폼 피처 추가 (train 집계 기반, augment_swap 전에 호출해야 함)
    form_lookup = _build_team_form_lookup(df_train)
    df_train = _add_team_form_features(df_train, form_lookup, is_train=True)
    df_val = _add_team_form_features(df_val, form_lookup)
    df_test = _add_team_form_features(df_test, form_lookup)

    # Phase 2 + P3 + P4 숫자가 모두 채워진 후에 팀 교환 증강을 해요
    if augment_train:  # 팀 교환 증강 옵션이 켜져 있으면
        df_train = augment_swap(df_train)  # 팀A↔팀B를 뒤집어서 훈련 데이터를 두 배로 늘려요

    df_all = _add_phase2_features(df_feat, rows_map, player_lookup, combo_lookup, medians)  # 분할 전 전체 표에도 Phase 2 숫자를 추가해요
    df_all = _add_map_agent_features(df_all, combo_lookup)  # 전체 표에도 맵 승률 피처 추가
    df_all = _add_team_form_features(df_all, form_lookup)  # 전체 표에도 팀 폼 피처 추가
    feat_cols = ["match_key", "dedup_key"] + FEATURE_COLS + EXPERIMENTAL_FEATURE_COLS + ["label"]  # features_base.csv에 저장할 열 순서를 정해요
    avail = [c for c in feat_cols if c in df_all.columns]  # 실제로 있는 열만 추려요
    df_all[avail].to_csv(output_dir / "features_base.csv", index=False)  # 전체 AI 참고 숫자 표를 features_base.csv로 저장해요

    print("[7/7] 저장...")  # 7단계 시작을 알려요 — 훈련/검증/테스트 파일 저장이에요
    df_train.to_csv(output_dir / "train.csv", index=False)  # 훈련 세트를 train.csv로 저장해요
    df_val.to_csv(output_dir / "val.csv", index=False)  # 검증 세트를 val.csv로 저장해요
    df_test.to_csv(output_dir / "test.csv", index=False)  # 테스트 세트를 test.csv로 저장해요

    manifest = {  # 세트 분할 결과를 기록하는 사전이에요
        "train_rows": len(df_train),  # 훈련 세트 줄 수예요 (팀 교환 증강 포함)
        "val_rows": len(df_val),  # 검증 세트 줄 수예요
        "test_rows": len(df_test),  # 테스트 세트 줄 수예요
        "train_label_mean": float(df_train["label"].mean()),  # 훈련 세트에서 팀A가 이긴 비율이에요 (0.5에 가까울수록 균형 잡혀 있어요)
        "val_label_mean": float(df_val["label"].mean()),  # 검증 세트에서 팀A가 이긴 비율이에요
        "test_label_mean": float(df_test["label"].mean()),  # 테스트 세트에서 팀A가 이긴 비율이에요
        "seed": 42,  # 나누기에 쓴 씨앗 번호예요 (같은 숫자를 쓰면 항상 같은 결과가 나와요)
        "augmented": augment_train,  # 팀 교환 증강을 했는지 여부예요 (True/False)
    }
    with open(output_dir / "split_manifest.json", "w") as f:  # split_manifest.json 파일을 열어요
        json.dump(manifest, f, indent=2)  # 분할 결과를 보기 좋게 들여쓰기 2칸으로 저장해요

    src_clean = {src: sum(1 for r in clean_rows if r["source"] == src) for src in SOURCE_WEIGHT}  # 출처별로 검문소를 통과한 경기 수를 세요
    summary = {  # 전처리 파이프라인 전체 결과를 요약하는 사전이에요
        "total_raw": len(all_rows),  # 파싱한 원시 경기 총 수예요 (검문소 전)
        "total_clean": len(clean_rows),  # 검문소를 통과한 경기 수예요
        "total_rejected": len(rejected_df),  # 검문소에서 탈락한 경기 수예요
        "source_raw": src_raw,  # 출처별 원시 경기 수 사전이에요
        "source_clean": src_clean,  # 출처별 통과 경기 수 사전이에요
        "split": manifest,  # 세트 분할 결과 사전이에요
        "active_feature_count": len(FEATURE_COLS),  # 학습/평가/UI에서 쓰는 P1-P4 피처 개수예요
        "experimental_feature_count": len(EXPERIMENTAL_FEATURE_COLS),  # ablation 전 후보 피처 개수예요
        "feature_count": len(avail) - 1,  # 레이블 제외 저장 열 개수예요 (경기 이름표·중복 도장 포함)
        "vlrgg_detail_included": include_vlrgg,
        "vlrgg_pipeline_matches_path": str(vlrgg_path),
    }
    with open(reports_dir / "preprocess_summary.json", "w") as f:  # preprocess_summary.json 파일을 열어요
        json.dump(summary, f, indent=2, ensure_ascii=False)  # 전처리 요약을 보기 좋게 UTF-8 JSON으로 저장해요

    print(f"\n완료: clean={len(clean_rows)}  train={len(df_train)}/val={len(df_val)}/test={len(df_test)}")  # 최종 결과를 화면에 보여줘요
    print(f"  features_base.csv: {len(avail) - 1}개 피처 + label")  # AI 참고 숫자 개수를 화면에 보여줘요


if __name__ == "__main__":  # 이 파일을 직접 실행할 때만 아래 코드가 동작해요 (다른 파일에서 import하면 실행 안 해요)
    parser = argparse.ArgumentParser(description="ValoPredictML 전처리 파이프라인")  # 터미널 옵션을 읽는 도구를 만들어요
    parser.add_argument("--input", required=True)  # 입력 데이터 폴더 경로는 반드시 입력해야 해요
    parser.add_argument("--output", required=True)  # 출력 데이터 폴더 경로는 반드시 입력해야 해요
    parser.add_argument("--reports", required=True)  # 리포트 저장 폴더 경로는 반드시 입력해야 해요
    parser.add_argument("--no-augment-train", action="store_true")  # 이 옵션을 붙이면 팀 교환 증강을 하지 않아요
    parser.add_argument("--include-vlrgg-detail", action="store_true")  # 검증된 VLR.gg 상세 경기 행을 opt-in으로 포함해요
    parser.add_argument("--vlrgg-pipeline-matches", default="data/processed/vlrgg_pipeline_matches.csv")  # VLR.gg 정규화 경기 CSV 경로예요
    run(parser.parse_args())  # 터미널 옵션을 읽어서 run() 함수를 실행해요
