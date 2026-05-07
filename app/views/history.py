from __future__ import annotations  # 오래된 파이썬에서도 새로운 방식으로 변수 종류를 표현할 수 있게 해주는 설정

import pandas as pd  # 예측 기록 목록을 엑셀처럼 생긴 표로 만들기 위한 도구
import streamlit as st  # 화면에 버튼·글자·표를 그려주는 도구


def render() -> None:  # 예측 이력 화면 전체를 화면에 그려주는 함수
    st.title("기록 — 예측 이력")  # 페이지 맨 위에 크게 제목을 보여줌

    try:
        from app.db import get_engine, get_predictions, init_db  # 데이터베이스 연결·조회 도구를 꺼냄 (필요할 때만 꺼냄)
        engine = get_engine()  # 설정에 맞는 데이터베이스 창구를 열어옴 (SQLite 또는 PostgreSQL)
        init_db(engine)  # 기록을 저장할 표(테이블)가 없으면 새로 만듦 (이미 있으면 아무것도 안 함)
    except Exception as e:  # 데이터베이스 연결에 실패하면
        st.error(f"DB 연결 실패: {e}")  # 빨간 경고 박스에 어떤 문제인지 보여줌
        return  # 여기서 멈추고 아래 코드는 실행하지 않음

    col_map, col_limit = st.columns([2, 1])  # 화면을 왼쪽(넓게)과 오른쪽(좁게) 두 칸으로 나눔
    with col_map:  # 왼쪽 넓은 칸에 아래 내용을 넣음
        map_filter = st.text_input("맵 필터 (빈칸=전체)", key="hist_map")  # 특정 맵 이름을 입력하면 그 맵의 기록만 보여주는 검색 칸
    with col_limit:  # 오른쪽 좁은 칸에 아래 내용을 넣음
        limit = st.number_input("최대 건수", min_value=10, max_value=200, value=50, step=10, key="hist_limit")  # 기록을 최대 몇 개까지 볼지 10~200 사이로 고르는 숫자 입력 칸

    try:
        records = get_predictions(engine, limit=int(limit))  # 데이터베이스에서 최근 기록을 최대 limit개만큼 가져옴 (최신 순서)
    except Exception as e:  # 기록을 가져오는 데 실패하면
        st.error(f"조회 실패: {e}")  # 빨간 경고 박스에 어떤 문제인지 보여줌
        return  # 여기서 멈추고 아래 코드는 실행하지 않음

    if map_filter:  # 맵 이름을 검색 칸에 입력한 경우에만 걸러냄
        records = [r for r in records if map_filter.lower() in r["map"].lower()]  # 대소문자 구분 없이 입력한 맵 이름이 포함된 기록만 남김

    if not records:  # 걸러낸 후 기록이 하나도 없으면
        st.info("저장된 기록이 없습니다.")  # 파란 안내 박스에 "기록이 없어요"라고 보여줌
        return  # 여기서 멈추고 아래 코드는 실행하지 않음

    rows = []  # 표에 보여줄 행(가로 줄)들을 모을 빈 바구니
    for r in records:  # 각 예측 기록을 하나씩 꺼내서 표의 한 줄로 변환
        rows.append({  # 화면에 보여줄 항목명과 값을 한 묶음으로 정리
            "ID": r["id"],  # 이 예측 기록의 고유 번호
            "시각": r["created_at"],  # 예측이 저장된 날짜와 시간
            "맵": r["map"],  # 어떤 맵에서의 경기인지
            "Team A 선수": ", ".join(r["team_a_players"]),  # 팀A 선수 이름들을 쉼표로 이어붙인 문자열
            "Team A 요원": ", ".join(r["team_a_agents"]),  # 팀A 요원 이름들을 쉼표로 이어붙인 문자열
            "Team B 선수": ", ".join(r["team_b_players"]),  # 팀B 선수 이름들을 쉼표로 이어붙인 문자열
            "Team B 요원": ", ".join(r["team_b_agents"]),  # 팀B 요원 이름들을 쉼표로 이어붙인 문자열
            "Team A 승률": f"{r['win_probability']*100:.1f}%",  # 팀A가 이길 확률을 소수점 첫째 자리 퍼센트로 변환 (예: 63.2%)
        })

    df = pd.DataFrame(rows)  # 행 묶음 목록을 엑셀처럼 생긴 표(DataFrame)로 만듦
    st.dataframe(df, use_container_width=True)  # 예측 이력 표를 화면 전체 너비로 보여줌

    selected_id = st.number_input("상세 보기 ID (0=없음)", min_value=0, value=0, step=1, key="hist_sel")  # 자세히 보고 싶은 기록의 번호를 입력하는 칸 (0이면 아무것도 안 보여줌)
    if selected_id:  # 0이 아닌 번호를 입력했을 때만 아래를 실행
        matched = [r for r in records if r["id"] == selected_id]  # 입력한 번호와 일치하는 기록을 찾음
        if matched:  # 일치하는 기록이 있으면 상세 정보를 보여줌
            r = matched[0]  # 찾은 기록 중 첫 번째를 꺼냄
            st.markdown(f"**맵**: {r['map']} | **Team A 승률**: {r['win_probability']*100:.1f}%")  # 맵 이름과 팀A 승률을 굵은 글씨로 한 줄에 표시
            c1, c2 = st.columns(2)  # 팀A와 팀B 정보를 나란히 보여줄 두 칸을 만듦
            c1.markdown("**Team A**")  # 왼쪽 칸 위에 "Team A"를 굵은 글씨로 표시
            for p, a in zip(r["team_a_players"], r["team_a_agents"]):  # 팀A 선수와 요원을 짝지어 하나씩 꺼냄
                c1.write(f"{p or '(미입력)'} — {a}")  # 선수 이름(없으면 "(미입력)")과 요원 이름을 한 줄에 보여줌
            c2.markdown("**Team B**")  # 오른쪽 칸 위에 "Team B"를 굵은 글씨로 표시
            for p, a in zip(r["team_b_players"], r["team_b_agents"]):  # 팀B 선수와 요원을 짝지어 하나씩 꺼냄
                c2.write(f"{p or '(미입력)'} — {a}")  # 선수 이름(없으면 "(미입력)")과 요원 이름을 한 줄에 보여줌
