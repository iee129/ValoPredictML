from __future__ import annotations  # 오래된 파이썬에서도 새로운 방식으로 변수 종류를 표현할 수 있게 해주는 설정

import json  # agent_map_stats.json 파일(요원별 통계가 담긴 파일)을 읽기 위한 기본 도구
from collections import Counter, defaultdict  # Counter: 목록에서 각 항목이 몇 번 나왔는지 세어주는 도구 / defaultdict: 없는 키도 자동으로 빈 바구니를 만들어주는 딕셔너리
from pathlib import Path  # 파일 경로를 문자열 대신 더 편리하게 다룰 수 있게 해주는 도구

import pandas as pd  # 경기 데이터를 읽고 인기 조합을 세기 위한 표 도구
import streamlit as st  # 화면에 버튼·표·차트를 그려주는 도구

from ml.agent_roles import AGENT_ROLE_MAP, MAP_ORDER, get_role  # 요원→역할 매핑, 맵 목록, "이 요원은 어떤 역할이야?" 함수를 가져옴

ROLE_DESC = {  # 각 역할군을 한국어로 설명해놓은 사전
    "Duelist": "타격대 — 높은 개인 전투력으로 적진을 돌파합니다.",  # Duelist(타격대): 혼자서도 싸움을 잘하는 공격형 요원
    "Initiator": "척후대 — 정보 수집·적 견제로 팀 진입을 지원합니다.",  # Initiator(척후대): 팀이 안전하게 들어갈 수 있도록 앞에서 길을 여는 요원
    "Controller": "전략가 — 스모크·장벽으로 전장을 통제합니다.",  # Controller(전략가): 연기나 장벽으로 전투 지역을 유리하게 바꾸는 요원
    "Sentinel": "감시자 — 사이드 수비·치유·감시로 팀을 안정시킵니다.",  # Sentinel(감시자): 옆을 지키고 팀원을 도와주는 수비형 요원
}

_ROLE_ORDER = ["Duelist", "Initiator", "Controller", "Sentinel"]  # 역할군을 화면에 보여줄 순서 목록
_STATS_PATH = Path("data/processed/agent_map_stats.json")  # 요원·맵 조합의 승률이 담긴 JSON 파일이 있는 경로
_MATCHES_PATH = Path("data/processed/matches_clean.csv")  # 정제된 경기 기록이 담긴 CSV 파일이 있는 경로


@st.cache_data  # 이 함수의 결과를 저장해뒀다가 다음에 다시 물어보면 파일을 다시 읽지 않고 저장해둔 값을 바로 돌려줌
def _load_agent_map_stats() -> dict:  # 요원·맵 조합 통계가 담긴 JSON 파일을 읽어서 돌려주는 함수
    if not _STATS_PATH.exists():  # 파일이 없으면 (데이터 처리를 아직 안 했을 때)
        return {}  # 빈 사전을 돌려줘서 오류 없이 넘어감
    with _STATS_PATH.open() as f:  # JSON 파일을 열어서
        return json.load(f)  # 파이썬이 읽을 수 있는 사전 형태로 변환해서 돌려줌


@st.cache_data  # 이 함수의 결과도 저장해뒀다가 재사용함 (같은 맵이면 다시 계산하지 않음)
def _load_top_combos(map_name: str, top_n: int = 5) -> list[dict]:  # 선택한 맵에서 자주 이긴 팀 구성 Top N개를 돌려주는 함수
    df = pd.read_csv(_MATCHES_PATH, usecols=["map", "agents_a", "agents_b", "label"])  # 경기 기록에서 필요한 4개 열만 읽어옴 (다 읽으면 느려서)
    subset = df[df["map"] == map_name]  # 선택한 맵의 경기들만 골라냄
    win_mask = subset["label"] == 1  # 팀A가 이긴 경기들을 표시하는 마스크 (label이 1이면 팀A 승리)
    combos = pd.concat([subset.loc[win_mask, "agents_a"], subset.loc[~win_mask, "agents_b"]])  # 이긴 팀의 요원 조합만 모음 (팀A가 이기면 agents_a, 팀B가 이기면 agents_b)
    return [  # 많이 등장한 순서로 Top N개의 조합을 사전 목록으로 돌려줌
        {"조합": combo.replace("|", " · "), "등장 횟수": cnt}  # 파이프(|)로 구분된 요원 이름을 점(·)으로 바꿔 읽기 좋게 만듦
        for combo, cnt in Counter(combos).most_common(top_n)  # 목록 안에서 각 항목이 몇 번 나왔는지 세고 많은 순서로 Top N개 꺼냄
    ]


def render() -> None:  # 가이드 화면 전체를 화면에 그려주는 함수
    st.title("가이드 — 역할군 + 맵별 메타")  # 페이지 맨 위에 크게 제목을 보여줌

    st.markdown("### 역할군 소개")  # "역할군 소개"라는 중간 제목을 표시
    roles_to_agents: dict[str, list[str]] = defaultdict(list)  # 역할군 이름 → 그 역할군에 속한 요원 목록을 담는 사전 (없는 역할군은 자동으로 빈 목록으로 시작)
    for agent, role in AGENT_ROLE_MAP.items():  # 모든 요원과 그 역할군을 하나씩 꺼내면서
        roles_to_agents[role].append(agent)  # 역할군 바구니에 요원 이름을 하나씩 넣음

    for role in _ROLE_ORDER:  # 역할군을 정해진 순서대로 하나씩 화면에 보여줌
        agents = sorted(roles_to_agents.get(role, []))  # 해당 역할군의 요원들을 가나다(알파벳) 순으로 정렬
        with st.expander(f"**{role}** — {ROLE_DESC.get(role, '')}"):  # 역할군 이름과 설명을 제목으로 한 접었다 펼쳤다 할 수 있는 박스
            st.write(", ".join(agents))  # 해당 역할군의 요원들을 쉼표로 구분해서 한 줄에 표시

    st.markdown("---")  # 역할군 소개와 다음 섹션 사이에 가로 줄을 그어 구분
    st.markdown("### 맵별 강세 요원")  # "맵별 강세 요원"이라는 중간 제목을 표시
    selected_map = st.selectbox("맵 선택", MAP_ORDER, key="guide_map")  # 공식 맵 목록에서 분석할 맵을 고르는 드롭다운 메뉴

    stats = _load_agent_map_stats()  # 저장된 요원·맵 조합 통계를 가져옴
    map_wr: dict[str, float] = {}  # 선택한 맵에서 각 요원의 승률을 담을 빈 사전
    for key, val in stats.get("wr", {}).items():  # "요원이름|맵이름" 형식의 승률 데이터를 하나씩 꺼냄
        parts = key.split("|", 1)  # 파이프(|)를 기준으로 요원 이름과 맵 이름으로 나눔
        if len(parts) == 2 and parts[1] == selected_map:  # 선택한 맵의 데이터인 경우에만
            map_wr[parts[0]] = val  # 요원 이름 → 승률로 사전에 추가

    if map_wr:  # 해당 맵의 요원 승률 데이터가 있을 때만 아래를 실행
        cols = st.columns(len(_ROLE_ORDER))  # 역할군 4개를 나란히 보여줄 4칸을 만듦
        for col, role in zip(cols, _ROLE_ORDER):  # 각 칸과 역할군을 짝지어서 하나씩 처리
            top3 = sorted(  # 해당 역할군에서 승률이 높은 순서로 Top 3 요원을 골라냄
                [(a, v) for a, v in map_wr.items() if get_role(a) == role],  # 이 역할군에 속하는 요원들만 필터링
                key=lambda x: x[1],  # 승률(두 번째 값)을 기준으로 정렬
                reverse=True,  # 높은 승률이 앞으로 오도록 내림차순 정렬
            )[:3]  # 상위 3개만 선택
            with col:  # 해당 역할군 칸 안에 내용을 넣음
                st.markdown(f"**{role}**")  # 역할군 이름을 굵은 글씨로 표시
                for agent, wr_val in top3:  # Top 3 요원을 하나씩 꺼내서
                    st.write(f"{agent}: {wr_val*100:.1f}%")  # 요원 이름과 승률을 소수점 첫째 자리 퍼센트로 보여줌
    else:  # 해당 맵의 데이터가 없을 때
        st.caption("해당 맵의 데이터가 없습니다.")  # 작은 글씨로 "데이터가 없어요"라고 안내

    st.markdown("---")  # 강세 요원 섹션과 다음 섹션 사이에 가로 줄을 그어 구분
    st.markdown("### 맵별 인기 승리 조합 Top 5")  # "인기 승리 조합" 중간 제목을 표시
    combos = _load_top_combos(selected_map)  # 선택한 맵에서 가장 많이 이긴 요원 조합 Top 5를 가져옴
    if combos:  # 조합 데이터가 있으면 표로 보여줌
        st.dataframe(pd.DataFrame(combos), use_container_width=True, hide_index=True)  # 인기 승리 조합을 화면 전체 너비의 엑셀 표로 보여줌 (왼쪽 번호 숨김)
    else:  # 조합 데이터가 없으면
        st.caption("해당 맵의 조합 데이터가 없습니다.")  # 작은 글씨로 "데이터가 없어요"라고 안내
