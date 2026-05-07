from __future__ import annotations  # 파이썬 버전이 낮아도 최신 방식으로 타입을 쓸 수 있게 해주는 설정

import json  # 요원+맵 조합 통계 파일(JSON)을 읽기 위한 도구
from dataclasses import dataclass  # 선수 이름과 선택한 요원을 묶어두는 간단한 데이터 보관함을 쉽게 만드는 도구
from pathlib import Path  # 파일 경로를 다루는 도구

import numpy as np  # 평균, 표준편차, 최댓값 같은 수학 계산을 빠르게 해주는 도구
import pandas as pd  # AI 모델에 넣을 숫자 표(DataFrame)를 만들기 위한 도구

from ml.agent_roles import AGENT_ROLE_MAP, ATK_ADV_MAP, MAP_ORDER  # 요원→역할군 사전, 맵별 공격 유리값, 맵 이름 목록

_AGENT_MAP_STATS_PATH = Path("data/processed/agent_map_stats.json")  # 요원과 맵을 조합했을 때의 승률·픽률·경험치 데이터가 담긴 파일 경로

_FEATURE_ORDER = [  # AI 모델이 입력받는 숫자 정보(피처) 43개의 순서 (훈련할 때 쓴 순서와 반드시 같아야 해요)
    "a_duelist", "a_initiator", "a_controller", "a_sentinel",  # 팀A에 타격대·척후대·전략가·감시자가 각각 몇 명인지
    "b_duelist", "b_initiator", "b_controller", "b_sentinel",  # 팀B에 타격대·척후대·전략가·감시자가 각각 몇 명인지
    "diff_duelist", "diff_initiator", "diff_controller", "diff_sentinel",  # 팀A에서 팀B를 뺀 각 역할군 인원 차이 (양수면 팀A가 더 많음)
    "has_controller_a", "has_controller_b",  # 팀A·팀B에 전략가(연막 요원)가 한 명이라도 있는지 (있으면 1, 없으면 0)
    "is_double_duelist_a", "is_double_duelist_b",  # 팀A·팀B에 타격대가 2명 이상인지 (맞으면 1, 아니면 0)
    "map_encoded", "atk_side_advantage", "is_attacker_a",  # 맵의 번호, 해당 맵에서 공격 팀이 얼마나 유리한지, 팀A가 공격 측인지
    "a_avg_acs", "b_avg_acs", "a_avg_kd", "b_avg_kd",  # 팀A·팀B의 평균 ACS(활약 점수)·K/D(킬-데스 비율)
    "a_avg_kast", "b_avg_kast", "a_avg_adr", "b_avg_adr",  # 팀A·팀B의 평균 KAST(기여 라운드 비율)·ADR(라운드당 피해량)
    "a_avg_hs", "b_avg_hs", "a_max_clutch", "b_max_clutch",  # 팀A·팀B의 평균 헤드샷 비율·팀 내 최고 클러치(역전) 비율
    "a_fk_fd_ratio", "b_fk_fd_ratio",  # 팀A·팀B의 퍼스트 킬 ÷ 퍼스트 데스 비율 (높을수록 선제권이 강함)
    "a_avg_assists", "b_avg_assists",  # 팀A·팀B의 평균 어시스트 수 (팀워크 지표)
    "a_kast_std", "b_kast_std",  # 팀A·팀B 내 선수들의 KAST 들쑥날쑥 정도 (낮을수록 팀 전체가 고르게 잘함)
    "a_avg_agent_map_wr", "b_avg_agent_map_wr",  # 팀A·팀B가 선택한 요원들이 이 맵에서 평균적으로 이겨온 비율
    "a_avg_agent_pick_rate", "b_avg_agent_pick_rate",  # 팀A·팀B가 선택한 요원들이 이 맵에서 얼마나 자주 선택됐는지
    "a_avg_agent_exp", "b_avg_agent_exp",  # 팀A·팀B 선수들이 해당 요원을 얼마나 많이 플레이해봤는지 경험치 평균
]

_combo: dict | None = None  # 요원+맵 조합 통계를 한 번만 읽어두는 보관함 (None이면 아직 읽지 않은 상태)


def _load_combo() -> dict:  # 요원+맵 조합 통계 파일을 읽거나, 이미 읽었으면 보관함에서 바로 꺼내주는 내부 함수
    global _combo  # 함수 밖의 _combo 변수를 이 함수 안에서 바꿀 수 있게 선언
    if _combo is not None:  # 이미 읽어둔 데이터가 있으면 파일을 다시 읽지 않고 바로 돌려줌
        return _combo  # 보관함에 있는 사전 반환
    if _AGENT_MAP_STATS_PATH.exists():  # 파일이 있으면 읽어서 파이썬 사전으로 변환
        with open(_AGENT_MAP_STATS_PATH, encoding="utf-8") as f:  # 한글이 깨지지 않도록 UTF-8 방식으로 열기
            _combo = json.load(f)  # JSON 파일을 파이썬 사전으로 읽기
    else:
        _combo = {"wr": {}, "pr": {}, "exp": {}}  # 파일이 없으면 모든 값이 비어있는 빈 사전으로 시작 (조회 시 기본값이 사용됨)
    return _combo  # 읽어온 또는 빈 사전 반환


@dataclass  # 이 데코레이터를 붙이면 __init__ 같은 기본 메서드를 자동으로 만들어줘요
class PlayerInput:  # 선수 이름과 그 선수가 고른 요원을 함께 담아두는 간단한 데이터 보관함
    player: str  # 선수 이름 (통계 파일에서 찾을 때 열쇠로 사용)
    agent: str  # 선수가 고른 요원 이름


def _count_roles(agents: list[str]) -> dict[str, int]:  # 요원 목록을 받아서 각 역할군이 몇 명인지 세어주는 내부 함수
    c = {"Duelist": 0, "Initiator": 0, "Controller": 0, "Sentinel": 0}  # 4개 역할군 카운터를 모두 0으로 시작
    for a in agents:  # 요원 목록에서 하나씩 꺼내면서
        role = AGENT_ROLE_MAP.get(a)  # 해당 요원이 어떤 역할군인지 사전에서 찾기
        if role and role in c:  # 알려진 역할군이면 해당 카운터를 1 올리기
            c[role] += 1  # 역할군 카운터 1 증가
    return c  # 역할군별 인원수가 담긴 사전 반환


def build_features(
    team_a: list[PlayerInput],  # 팀A의 5명 — 각각 선수 이름과 요원 이름이 담겨 있어요
    team_b: list[PlayerInput],  # 팀B의 5명 — 각각 선수 이름과 요원 이름이 담겨 있어요
    map_name: str,  # 경기가 진행될 맵 이름 (공식 맵 목록에 있는 이름이어야 해요)
    is_attacker_a: bool,  # 팀A가 공격 팀이면 True, 수비 팀이면 False
    player_stats: dict | None = None,  # 선수 통계를 직접 넣고 싶을 때 사용 (없으면 자동으로 파일에서 조회)
) -> pd.DataFrame:  # AI 모델에 바로 넣을 수 있는 숫자 43개가 담긴 1행짜리 표(DataFrame) 반환
    from app.player_lookup import get_player_stats as _get_stats  # 선수 통계 조회 함수를 여기서 불러옴 (서로 불러오는 문제를 피하기 위해 나중에 가져와요)

    combo = _load_combo()  # 요원+맵 조합 통계 사전 가져오기 (이미 읽었으면 보관함에서 바로 꺼냄)

    agents_a = [p.agent for p in team_a]  # 팀A 5명이 고른 요원 이름만 뽑아서 리스트로 만들기
    agents_b = [p.agent for p in team_b]  # 팀B 5명이 고른 요원 이름만 뽑아서 리스트로 만들기
    rc_a = _count_roles(agents_a)  # 팀A의 역할군별 인원수 계산
    rc_b = _count_roles(agents_b)  # 팀B의 역할군별 인원수 계산

    map_encoded = MAP_ORDER.index(map_name) if map_name in MAP_ORDER else -1  # 맵 이름을 순서 번호로 바꾸기 (AI는 이름보다 숫자를 좋아해요; 모르는 맵은 -1)
    atk_adv = ATK_ADV_MAP.get(map_name, 0.0)  # 이 맵에서 공격 팀이 얼마나 유리한지 값 가져오기 (없으면 0.0 = 유불리 없음)

    def _pstats(pi: PlayerInput) -> dict:  # 선수 한 명의 통계를 가져오는 도우미 함수
        if player_stats and pi.player in player_stats:  # 직접 넣어준 통계 사전에 이 선수가 있으면 그걸 먼저 사용
            return player_stats[pi.player]  # 직접 제공된 통계 반환
        return _get_stats(pi.player)  # 없으면 파일이나 캐시에서 찾아오기

    def _team_stats(team: list[PlayerInput], side: str, map_n: str) -> dict:  # 팀 전체의 평균 통계를 계산해주는 도우미 함수
        stats_list = [_pstats(pi) for pi in team]  # 팀 내 5명 선수의 통계를 각각 가져와서 리스트로 모으기

        avg_acs = float(np.mean([s["avg_acs"] for s in stats_list]))  # 팀 전체 ACS(활약 점수) 평균 계산
        avg_kd = float(np.mean([s["avg_kd"] for s in stats_list]))  # 팀 전체 K/D(킬÷데스) 평균 계산
        avg_kast = float(np.mean([s["avg_kast"] for s in stats_list]))  # 팀 전체 KAST(기여 라운드 비율) 평균 계산
        avg_adr = float(np.mean([s["avg_adr"] for s in stats_list]))  # 팀 전체 ADR(라운드당 피해량) 평균 계산
        avg_hs = float(np.mean([s["avg_hs"] for s in stats_list]))  # 팀 전체 헤드샷 비율 평균 계산
        max_clutch = float(np.max([s["max_clutch"] for s in stats_list]))  # 팀 내 클러치(역전) 비율이 가장 높은 선수의 값 (한 명이라도 클러치 잘하면 팀에 이득)

        avg_fk = float(np.mean([s["avg_fk"] for s in stats_list]))  # 팀 전체 퍼스트 킬 수 평균 계산
        avg_fd = float(np.mean([s["avg_fd"] for s in stats_list]))  # 팀 전체 퍼스트 데스 수 평균 계산
        fk_fd_ratio = avg_fk / max(avg_fd, 1e-9)  # 퍼스트 킬 ÷ 퍼스트 데스 비율 계산 (0으로 나누는 사고를 막기 위해 아주 작은 수 1e-9를 사용)

        avg_assists = float(np.mean([s["avg_assists"] for s in stats_list]))  # 팀 전체 어시스트 수 평균 계산
        kast_vals = [s["avg_kast"] for s in stats_list]  # 선수별 KAST 값을 모아서 들쑥날쑥 정도를 구하기 위한 준비
        kast_std = float(np.std(kast_vals)) if len(kast_vals) > 1 else 0.0  # KAST 표준편차 계산 (값이 고를수록 0에 가까워요; 선수가 1명이면 0)

        wrs, prs, exps = [], [], []  # 요원+맵 승률, 픽률, 선수 경험치 값을 모을 빈 바구니 3개
        for pi in team:  # 팀 내 선수-요원 쌍을 하나씩 꺼내면서
            key = f"{pi.agent}|{map_n}"  # "제트|어센트" 같은 형식으로 요원+맵 조합 열쇠 만들기
            wrs.append(combo["wr"].get(key, 0.5))  # 이 요원이 이 맵에서 이긴 비율 (데이터 없으면 50%로 가정)
            prs.append(combo["pr"].get(key, 0.0))  # 이 요원이 이 맵에서 선택된 비율 (데이터 없으면 0%)
            exp_key = f"{pi.player}|{pi.agent}"  # "TenZ|제트" 같은 형식으로 선수+요원 경험치 열쇠 만들기
            exps.append(float(combo["exp"].get(exp_key, 0)))  # 이 선수의 이 요원 경험치 (데이터 없으면 0)

        return {  # "a_" 또는 "b_" 접두사를 붙인 팀 통계 사전 반환
            f"{side}_avg_acs": avg_acs,  # 팀 평균 ACS
            f"{side}_avg_kd": avg_kd,  # 팀 평균 K/D
            f"{side}_avg_kast": avg_kast,  # 팀 평균 KAST
            f"{side}_avg_adr": avg_adr,  # 팀 평균 ADR
            f"{side}_avg_hs": avg_hs,  # 팀 평균 헤드샷 비율
            f"{side}_max_clutch": max_clutch,  # 팀 내 최고 클러치 비율
            f"{side}_fk_fd_ratio": fk_fd_ratio,  # 팀 FK/FD 비율
            f"{side}_avg_assists": avg_assists,  # 팀 평균 어시스트 수
            f"{side}_kast_std": kast_std,  # 팀 KAST 들쑥날쑥 정도
            f"{side}_avg_agent_map_wr": float(np.mean(wrs)),  # 팀이 고른 요원들의 이 맵 평균 승률
            f"{side}_avg_agent_pick_rate": float(np.mean(prs)),  # 팀이 고른 요원들의 이 맵 평균 픽률
            f"{side}_avg_agent_exp": float(np.mean(exps)),  # 팀 선수들의 해당 요원 경험치 평균
        }

    rec: dict = {  # 역할군 인원수·맵 정보·공격 측 여부 등 팀 구성 관련 숫자들을 담는 사전
        "a_duelist": rc_a["Duelist"],  # 팀A 타격대(Duelist) 수
        "a_initiator": rc_a["Initiator"],  # 팀A 척후대(Initiator) 수
        "a_controller": rc_a["Controller"],  # 팀A 전략가(Controller) 수
        "a_sentinel": rc_a["Sentinel"],  # 팀A 감시자(Sentinel) 수
        "b_duelist": rc_b["Duelist"],  # 팀B 타격대(Duelist) 수
        "b_initiator": rc_b["Initiator"],  # 팀B 척후대(Initiator) 수
        "b_controller": rc_b["Controller"],  # 팀B 전략가(Controller) 수
        "b_sentinel": rc_b["Sentinel"],  # 팀B 감시자(Sentinel) 수
        "diff_duelist": rc_a["Duelist"] - rc_b["Duelist"],  # 팀A 타격대 수 - 팀B 타격대 수 (양수면 팀A가 더 많음)
        "diff_initiator": rc_a["Initiator"] - rc_b["Initiator"],  # 팀A 척후대 수 - 팀B 척후대 수
        "diff_controller": rc_a["Controller"] - rc_b["Controller"],  # 팀A 전략가 수 - 팀B 전략가 수
        "diff_sentinel": rc_a["Sentinel"] - rc_b["Sentinel"],  # 팀A 감시자 수 - 팀B 감시자 수
        "has_controller_a": int(rc_a["Controller"] > 0),  # 팀A에 전략가(연막 담당)가 1명이라도 있으면 1, 없으면 0
        "has_controller_b": int(rc_b["Controller"] > 0),  # 팀B에 전략가(연막 담당)가 1명이라도 있으면 1, 없으면 0
        "is_double_duelist_a": int(rc_a["Duelist"] >= 2),  # 팀A에 타격대가 2명 이상이면 1 (더블 타격대 구성), 아니면 0
        "is_double_duelist_b": int(rc_b["Duelist"] >= 2),  # 팀B에 타격대가 2명 이상이면 1 (더블 타격대 구성), 아니면 0
        "map_encoded": map_encoded,  # 맵 이름을 순서 번호로 변환한 값 (모르는 맵이면 -1)
        "atk_side_advantage": atk_adv,  # 이 맵에서 공격 팀이 얼마나 유리한지 나타내는 값 (양수면 공격 유리)
        "is_attacker_a": int(is_attacker_a),  # 팀A가 공격 팀이면 1, 수비 팀이면 0
    }
    rec.update(_team_stats(team_a, "a", map_name))  # 팀A의 선수 통계 숫자들을 위 사전에 추가
    rec.update(_team_stats(team_b, "b", map_name))  # 팀B의 선수 통계 숫자들을 위 사전에 추가

    df = pd.DataFrame([rec])  # 사전을 1행짜리 숫자 표(DataFrame)로 변환
    return df[_FEATURE_ORDER]  # AI 모델이 훈련할 때 사용한 순서와 똑같이 컬럼을 정렬해서 반환
