from __future__ import annotations  # 오래된 파이썬에서도 새로운 방식으로 변수 종류를 표현할 수 있게 해주는 설정

import pandas as pd  # 표(엑셀처럼 생긴 것)를 만들고 다루는 도구
import streamlit as st  # 화면에 버튼·글자·차트를 그려주는 도구

from ml.agent_roles import AGENT_ROLE_MAP, MAP_ORDER, get_role  # 요원 이름, 맵 목록, "이 요원은 어떤 역할이야?" 함수를 가져옴

_AGENTS = sorted(AGENT_ROLE_MAP.keys())  # 선택 박스에 보여줄 요원 이름들을 가나다(알파벳) 순서로 정렬한 목록


def render() -> None:  # 예측 화면 전체를 화면에 그려주는 함수
    st.title("예측 — 상세 분석 + 교체 실험")  # 페이지 맨 위에 크게 제목을 보여줌

    try:
        from app.model_loader import load_models  # 모델을 불러오는 도구 가져오기 (필요할 때만 꺼냄)
        models = load_models()  # 저장해둔 AI 모델 파일 3개를 컴퓨터 기억장치에 올림 (한 번 올리면 다음엔 빠르게 재사용)
    except (FileNotFoundError, RuntimeError, ValueError) as e:  # 모델 파일이나 metadata 계약이 맞지 않으면 아래처럼 처리
        st.error(str(e))  # 빨간 경고 박스에 "파일을 찾을 수 없어요" 메시지를 보여줌
        st.stop()  # 여기서 멈추고 아래 코드는 실행하지 않음

    from app.player_lookup import get_player_names, get_player_stats  # 선수 이름 목록과 선수 기록을 가져오는 함수 꺼내기
    player_names = get_player_names()  # 등록된 선수 이름들을 한 번에 불러옴

    st.markdown("### 팀 구성 입력")  # "팀 구성 입력"이라는 중간 제목을 화면에 표시
    col_map, col_side = st.columns([2, 1])  # 화면을 왼쪽(넓게)과 오른쪽(좁게) 두 칸으로 나눔
    with col_map:  # 왼쪽 칸에 아래 내용을 넣음
        map_name = st.selectbox("맵", MAP_ORDER, key="pred_map")  # 공식 맵 목록 중 하나를 고르는 드롭다운 메뉴
    with col_side:  # 오른쪽 칸에 아래 내용을 넣음
        attacker_side = st.radio("선공 팀 (1~12라운드 공격)", ["Team A", "Team B"], key="pred_atk")  # 팀A와 팀B 중 먼저 공격하는 팀을 동그라미 버튼으로 고름
    is_attacker_a = attacker_side == "Team A"  # 팀A가 공격 팀으로 선택됐으면 True, 아니면 False로 기억해둠

    def _team_inputs(prefix: str, label: str) -> tuple[list[str], list[str]]:  # 한 팀의 선수 5명과 요원 5개를 고르는 칸들을 그려주는 내부 함수
        st.subheader(label)  # "Team A" 또는 "Team B" 같은 팀 이름을 화면에 조금 큰 글씨로 표시
        ps, ag = [], []  # 선수 이름들과 요원 이름들을 담을 빈 바구니(리스트) 두 개
        cols = st.columns(5)  # 선수 5명을 나란히 보여줄 5칸짜리 줄을 만듦
        for i, col in enumerate(cols):  # 각 칸(슬롯)을 1번부터 5번까지 돌면서
            with col:  # 해당 칸 안에 위젯을 넣음
                ps.append(st.selectbox(f"선수 {i+1}", [""] + player_names, key=f"{prefix}_p{i}"))  # 선수를 고르는 드롭다운(빈 칸 포함)을 만들고 선택 결과를 목록에 추가
                ag.append(st.selectbox(f"요원 {i+1}", _AGENTS, key=f"{prefix}_a{i}"))  # 요원을 고르는 드롭다운을 만들고 선택 결과를 목록에 추가
        return ps, ag  # 선수 이름 목록과 요원 이름 목록을 함께 돌려줌

    col_a, col_b = st.columns(2)  # 화면을 왼쪽(팀A)과 오른쪽(팀B)으로 똑같이 반씩 나눔
    with col_a:  # 왼쪽 칸에 팀A 입력 위젯들을 넣음
        players_a, agents_a = _team_inputs("pr_a", "Team A")  # 팀A의 선수 5명과 요원 5개를 고르는 칸들을 그림
    with col_b:  # 오른쪽 칸에 팀B 입력 위젯들을 넣음
        players_b, agents_b = _team_inputs("pr_b", "Team B")  # 팀B의 선수 5명과 요원 5개를 고르는 칸들을 그림

    if not st.button("예측 실행", type="primary", key="pred_run", use_container_width=True):  # 파란색 넓은 버튼 — 누르지 않으면 아래 내용은 실행되지 않음
        return  # 버튼을 아직 안 눌렀으니 여기서 멈추고 예측 결과는 보여주지 않음

    from app.feature_builder import PlayerInput, build_features, feature_source_status  # 선수·요원 정보를 숫자로 바꾸는 도구 꺼내기 (버튼 누를 때만 꺼냄)
    from app.insights import (
        describe_feature_changes,
        enrich_top_factors,
        load_vlr_evidence,
        split_factor_insights,
    )
    from app.model_loader import compute_shap, predict  # AI가 예측하고 이유를 설명하는 함수 꺼내기

    team_a = [PlayerInput(player=players_a[i], agent=agents_a[i]) for i in range(5)]  # 팀A의 선수·요원 5쌍을 깔끔한 묶음으로 포장
    team_b = [PlayerInput(player=players_b[i], agent=agents_b[i]) for i in range(5)]  # 팀B의 선수·요원 5쌍을 깔끔한 묶음으로 포장

    try:
        features = build_features(team_a, team_b, map_name, is_attacker_a)  # 두 팀 정보를 AI가 읽을 수 있는 숫자 43개로 변환
        source_status = feature_source_status(team_a, team_b, map_name)
        win_prob = predict(models, features)  # 3개의 AI 모델이 의견을 합쳐서 팀A의 승리 확률을 계산
    except Exception as e:  # 숫자 변환이나 예측 도중 문제가 생기면
        st.error(f"예측 오류: {e}")  # 빨간 경고 박스에 어떤 문제인지 보여줌
        return  # 여기서 멈추고 아래 코드는 실행하지 않음

    st.markdown("---")  # 입력 칸과 결과 사이에 가로 줄을 그어 구분
    st.markdown("### 예측 결과")  # "예측 결과"라는 중간 제목을 화면에 표시
    c1, c2 = st.columns(2)  # 팀A와 팀B 승률을 나란히 보여줄 두 칸을 만듦
    c1.metric("Team A 승률", f"{win_prob*100:.1f}%")  # 팀A의 승리 확률을 퍼센트로 예쁜 카드에 표시 (예: 63.2%)
    c2.metric("Team B 승률", f"{(1-win_prob)*100:.1f}%")  # 팀B의 승리 확률(100%에서 팀A 확률을 뺀 값)을 예쁜 카드에 표시
    st.progress(win_prob)  # 팀A의 승률만큼 막대가 채워지는 진행 바를 화면에 그림

    st.markdown("---")  # 가로 줄로 섹션 구분
    st.markdown("### 선수 기여도 (KAST)")  # "선수 기여도" 중간 제목 표시

    def _kast_table(players: list[str], agents: list[str]) -> tuple[list[dict], float]:  # 선수들의 KAST(경기 기여 점수) 표와 평균을 만들어 돌려주는 내부 함수
        rows, vals = [], []  # 표의 각 행과 KAST 점수를 모을 빈 바구니 두 개
        for p, a in zip(players, agents):  # 선수와 요원을 짝지어서 한 명씩 처리
            kast = get_player_stats(p).get("avg_kast", 0.70)  # 해당 선수의 평균 KAST를 가져옴 (기록이 없으면 기본값 70%로 사용)
            vals.append(kast)  # 나중에 평균을 계산하기 위해 KAST 값을 모아둠
            rows.append({"선수": p or "(미선택)", "요원": a, "KAST": f"{kast*100:.1f}%"})  # 선수 이름(선택 안 했으면 "(미선택)")·요원·KAST를 한 줄로 정리
        return rows, sum(vals) / len(vals)  # 표의 모든 행과 선수들의 KAST 평균값을 함께 돌려줌

    rows_a, avg_a = _kast_table(players_a, agents_a)  # 팀A 선수들의 KAST 표와 평균 계산
    rows_b, avg_b = _kast_table(players_b, agents_b)  # 팀B 선수들의 KAST 표와 평균 계산

    col_ka, col_kb = st.columns(2)  # 팀A와 팀B KAST 정보를 나란히 보여줄 두 칸을 만듦
    with col_ka:  # 왼쪽 칸에 팀A 정보를 넣음
        st.metric("Team A 평균 KAST", f"{avg_a*100:.1f}%")  # 팀A 선수들의 평균 KAST를 예쁜 숫자 카드로 표시
        st.dataframe(pd.DataFrame(rows_a), use_container_width=True, hide_index=True)  # 팀A 선수별 KAST를 엑셀처럼 생긴 표로 보여줌 (왼쪽 번호 숨김)
    with col_kb:  # 오른쪽 칸에 팀B 정보를 넣음
        st.metric("Team B 평균 KAST", f"{avg_b*100:.1f}%")  # 팀B 선수들의 평균 KAST를 예쁜 숫자 카드로 표시
        st.dataframe(pd.DataFrame(rows_b), use_container_width=True, hide_index=True)  # 팀B 선수별 KAST를 엑셀처럼 생긴 표로 보여줌 (왼쪽 번호 숨김)

    shap_dict: dict[str, float] = {}
    top_factors: list[dict] = []
    shap_error: str | None = None
    try:
        shap_dict = compute_shap(models, features)  # 어떤 요소가 예측에 얼마나 영향을 줬는지 점수판(SHAP 값)을 계산
        top10 = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:10]  # 영향이 큰 순서대로 상위 10개 요소를 골라냄
        top_factors = enrich_top_factors([{"feature": k, "value": float(v)} for k, v in top10], features)
    except Exception as e:  # SHAP 점수 계산이 안 될 경우 (조용히 처리)
        shap_error = str(e)

    replacement_rows: list[dict] = []
    with st.spinner("최적 요원 탐색 중..."):  # 계산이 좀 걸리니까 "로딩 중..." 빙글빙글 애니메이션을 보여주는 동안
        for i in range(5):  # 팀A의 선수 칸 5개를 하나씩 살펴봄
            best_agent, best_prob = agents_a[i], win_prob  # 일단 지금 선택한 요원을 "최선"으로 시작
            best_features = features
            current_role = get_role(agents_a[i])  # 이 칸의 요원이 어떤 역할군인지 확인 (예: 타격대)
            candidates = [a for a in _AGENTS if a != agents_a[i] and get_role(a) == current_role]  # 같은 역할군이면서 지금 요원과 다른 후보 요원 목록을 만듦
            for candidate in candidates:  # 후보 요원을 하나씩 바꿔보면서 승률을 계산
                new_team_a = list(team_a)  # 팀A 목록을 복사해서 실험용 새 목록을 만듦 (원본은 안 건드림)
                new_team_a[i] = PlayerInput(player=players_a[i], agent=candidate)  # i번 칸의 요원만 후보 요원으로 교체
                try:
                    candidate_features = build_features(new_team_a, team_b, map_name, is_attacker_a)
                    p = predict(models, candidate_features)  # 교체 후의 승률을 예측
                    if p > best_prob:  # 교체했을 때 승률이 더 높으면
                        best_prob, best_agent, best_features = p, candidate, candidate_features  # 이 요원을 새로운 "최선"으로 업데이트
                except Exception:  # 예측이 실패하면 그냥 넘어감
                    continue  # 다음 후보 요원으로 넘어감
            reasons = describe_feature_changes(features, best_features, shap_dict, limit=3)
            replacement_rows.append({  # 이 슬롯의 추천 결과를 한 줄로 정리
                "슬롯": i + 1,  # 슬롯 번호 (1번부터 5번까지)
                "현재 요원": agents_a[i],  # 지금 선택된 요원 이름
                "추천 요원": best_agent,  # 바꾸면 가장 이길 확률이 높아지는 요원 이름
                "현재 승률": f"{win_prob*100:.1f}%",  # 지금 팀 구성으로 예측한 팀A 승률
                "추천 시 승률": f"{best_prob*100:.1f}%",  # 추천 요원으로 바꿨을 때 예상되는 팀A 승률
                "변화": f"{(best_prob - win_prob)*100:+.1f}%p",  # 바꾸기 전과 후의 승률 차이 (플러스/마이너스 표시 포함)
                "변동 원인": " / ".join(reasons) if reasons else "동일 역할군 내 개선 후보 없음",
                "_delta": best_prob - win_prob,
            })

    favorable, risks = split_factor_insights(top_factors, limit=3)
    top_replacements = sorted(replacement_rows, key=lambda row: row["_delta"], reverse=True)[:3]

    st.markdown("---")
    st.markdown("### Insight Pack")
    m1, m2 = st.columns(2)
    m1.metric("Team A 승률", f"{win_prob*100:.1f}%")
    m2.metric("Team B 승률", f"{(1-win_prob)*100:.1f}%")

    fav_col, risk_col = st.columns(2)
    with fav_col:
        st.markdown("**주요 유리 요인**")
        if favorable:
            for item in favorable:
                st.write(f"- {item}")
        elif shap_error:
            st.caption("SHAP 분석 사용 불가: 유리 요인을 계산하지 못했습니다.")
        else:
            st.caption("강한 유리 요인이 감지되지 않았습니다.")
    with risk_col:
        st.markdown("**주요 위험 요인**")
        if risks:
            for item in risks:
                st.write(f"- {item}")
        elif shap_error:
            st.caption("SHAP 분석 사용 불가: 위험 요인을 계산하지 못했습니다.")
        else:
            st.caption("강한 위험 요인이 감지되지 않았습니다.")

    st.markdown("**추천 교체 Top 3**")
    replacement_display = [
        {k: v for k, v in row.items() if not k.startswith("_")}
        for row in top_replacements
    ]
    st.dataframe(pd.DataFrame(replacement_display), use_container_width=True, hide_index=True)

    agent_map_status = source_status["agent_map_stats"]
    if agent_map_status["neutral_used"]:
        missing_preview = ", ".join(agent_map_status["missing"][:5])
        suffix = f" 누락 예: {missing_preview}" if missing_preview else ""
        st.warning(
            f"요원-맵 통계 {agent_map_status['matched']}/{agent_map_status['total']}개를 사용했습니다. "
            f"나머지는 중립값 50%를 사용했습니다.{suffix}"
        )
    else:
        st.caption(f"요원-맵 통계는 {agent_map_status['path']}에서 10/10개 조합을 사용했습니다.")
    st.caption(source_status["team_form"]["message"])

    vlr_evidence = load_vlr_evidence()
    with st.expander("VLR 근거", expanded=False):
        st.caption("아래 수치는 현재 예측 모델에 직접 반영됐다는 뜻이 아니라, 수집 산출물 기반 근거 패널입니다.")
        if vlr_evidence:
            rows = vlr_evidence["rows"]
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("수집 row 수", f"{vlr_evidence['total_rows']:,}")
            v2.metric("요원/맵 표본", f"{int(rows.get('vlrgg_agent_map_stats', 0)):,}")
            v3.metric("팀 맵 표본", f"{int(rows.get('vlrgg_team_map_stats', 0)):,}")
            v4.metric("Pipeline-ready", f"{vlr_evidence['pipeline_matches']:,}")
            st.caption(
                f"리포트: {vlr_evidence['summary_path']} | "
                f"생성 시각: {vlr_evidence['generated_at'] or 'unknown'}"
            )
        else:
            st.info("아직 수집 리포트 없음")

    st.markdown("---")  # 가로 줄로 섹션 구분
    st.markdown("### 예측 근거 (SHAP 기여도)")  # "예측 근거" 중간 제목 표시
    st.caption("양수: Team A에 유리, 음수: Team B에 유리")  # 점수가 플러스면 팀A에 좋고, 마이너스면 팀B에 좋다는 안내
    if shap_error:
        st.caption("SHAP 분석 사용 불가")  # "지금은 분석을 보여줄 수 없어요"라고 작은 글씨로 안내
    elif top_factors:
        chart_df = pd.DataFrame(
            [{"피처": f["label"], "기여도": f["value"]} for f in top_factors]
        ).set_index("피처")
        st.bar_chart(chart_df)  # 상위 10개 요소의 영향 크기를 막대 그래프로 보여줌
        st.dataframe(
            pd.DataFrame([
                {
                    "피처": f["label"],
                    "현재 값": f["feature_value_display"],
                    "기여도": f"{f['value']:+.5f}",
                    "해석": f["description"],
                }
                for f in top_factors
            ]),
            use_container_width=True,
            hide_index=True,
        )

    try:
        from app.db import get_engine, init_db, save_prediction

        engine = get_engine()
        init_db(engine)
        save_prediction(
            engine,
            map_name=map_name,
            team_a_players=players_a,
            team_a_agents=agents_a,
            team_b_players=players_b,
            team_b_agents=agents_b,
            win_probability=float(win_prob),
            top_factors=top_factors,
        )
        st.caption("예측 이력이 저장되었습니다.")
    except Exception as e:
        st.caption(f"예측 이력 저장 실패: {e}")

    st.markdown("---")  # 가로 줄로 섹션 구분
    st.markdown("### 슬롯별 최선 요원 추천 (Team A)")  # "요원 추천" 중간 제목 표시
    st.caption("각 슬롯에서 같은 역할군 내 교체 시 승률이 가장 높아지는 요원을 자동으로 찾습니다.")  # 어떤 요원으로 바꾸면 이길 확률이 올라가는지 자동으로 찾아준다는 설명
    st.dataframe(
        pd.DataFrame([{k: v for k, v in row.items() if not k.startswith("_")} for row in replacement_rows]),
        use_container_width=True,
        hide_index=True,
    )  # 슬롯별 요원 추천 결과를 화면 전체 너비의 표로 보여줌 (왼쪽 번호 숨김)
