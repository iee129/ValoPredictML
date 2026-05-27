import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import joblib
import pandas as pd
import streamlit as st

from config import ARTIFACTS_DIR
from src.predict_v9 import predict_one_v9
from src.taxonomy import AGENT_ROLES, MAP_LIST

AGENTS = sorted(AGENT_ROLES.keys())
_DIRECT_INPUT = "(직접 입력...)"


@st.cache_resource
def load_known_players():
    state = joblib.load(ARTIFACTS_DIR / "prior_state_v7.joblib")
    return sorted(k for k in state["player_hist"].keys() if isinstance(k, str) and k.strip())


KNOWN_PLAYERS = load_known_players()
PLAYER_OPTIONS = KNOWN_PLAYERS + [_DIRECT_INPUT]

st.set_page_config(page_title="VCT 승률 예측", layout="wide")
st.title("VCT 발로란트 매치 승률 예측")

map_name = st.selectbox("맵", MAP_LIST)

st.markdown("---")
col_a, col_b = st.columns(2)


def player_inputs(col, side_label, key_prefix):
    with col:
        st.subheader(side_label)
        players = []
        for i in range(5):
            c1, c2 = st.columns([2, 2])
            with c1:
                sel = st.selectbox(
                    f"선수 {i + 1}",
                    PLAYER_OPTIONS,
                    key=f"{key_prefix}_sel_{i}",
                )
                if sel == _DIRECT_INPUT:
                    player = st.text_input(
                        f"이름 직접 입력 ({i + 1})",
                        key=f"{key_prefix}_custom_{i}",
                    )
                else:
                    player = sel
            with c2:
                agent = st.selectbox(f"요원 {i + 1}", AGENTS, key=f"{key_prefix}_agent_{i}")
            players.append({"player": player, "agent": agent})
        return players


team_a = player_inputs(col_a, "팀 A", "a")
team_b = player_inputs(col_b, "팀 B", "b")

if st.button("예측하기", type="primary"):
    empty_a = [i + 1 for i, p in enumerate(team_a) if not p["player"].strip()]
    empty_b = [i + 1 for i, p in enumerate(team_b) if not p["player"].strip()]

    if empty_a or empty_b:
        if empty_a:
            st.warning(f"팀 A {empty_a}번 선수 이름을 입력하세요.")
        if empty_b:
            st.warning(f"팀 B {empty_b}번 선수 이름을 입력하세요.")
    else:
        input_dict = {
            "map": map_name,
            "team_a": [{"player": p["player"].strip(), "agent": p["agent"]} for p in team_a],
            "team_b": [{"player": p["player"].strip(), "agent": p["agent"]} for p in team_b],
        }
        try:
            r = predict_one_v9(input_dict)

            p_a = r["p_ensemble"]
            p_b = 1.0 - p_a

            st.markdown("---")
            st.subheader("예측 결과")

            if p_a > 0.5:
                winner_text = "팀 A 우세"
            elif p_b > 0.5:
                winner_text = "팀 B 우세"
            else:
                winner_text = "동률"
            st.markdown(f"### {winner_text}")

            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.metric("팀 A 승률", f"{p_a * 100:.1f}%")
                st.progress(p_a)
            with res_col2:
                st.metric("팀 B 승률", f"{p_b * 100:.1f}%")
                st.progress(p_b)

            st.markdown("**모델별 P(팀 A 승)**")
            w = r["weights"]
            df = pd.DataFrame(
                {
                    "모델": [
                        "LightGBM",
                        "XGBoost",
                        "SVM",
                        "RF",
                        f"앙상블 ({w['lgbm']:.2f}/{w['xgb']:.2f}/{w['svm']:.2f}/{w['rf']:.2f})",
                    ],
                    "P(팀 A 승)": [
                        f"{r['p_lgbm'] * 100:.1f}%",
                        f"{r['p_xgb'] * 100:.1f}%",
                        f"{r['p_svm'] * 100:.1f}%",
                        f"{r['p_rf'] * 100:.1f}%",
                        f"{p_a * 100:.1f}%",
                    ],
                }
            )
            st.table(df)

            cold_a = r.get("cold_team_a", [])
            cold_b = r.get("cold_team_b", [])
            if cold_a or cold_b:
                lines = ["학습 데이터에 없는 선수 — 팀 평균 prior로 대체됨"]
                if cold_a:
                    lines.append(f"팀 A: {', '.join(cold_a)}")
                if cold_b:
                    lines.append(f"팀 B: {', '.join(cold_b)}")
                st.warning("\n".join(lines))

            if not r.get("map_recognized", True):
                st.warning(f"'{map_name}' 맵 미인식 — map_is_* 피처 모두 0 처리.")

        except Exception as e:
            st.error(f"예측 오류: {e}")
