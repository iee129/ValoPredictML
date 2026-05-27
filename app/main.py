from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.predict import (  # noqa: E402
    agent_label,
    available_options,
    feature_label,
    global_feature_importance,
    load_model,
    load_reports,
    map_label,
    predict_custom_lineup,
    predict_replay_match,
    verdict_label,
)


APP_TITLE = "발로란트 5v5 승률 예측 시뮬레이터"


st.set_page_config(page_title=APP_TITLE, layout="wide")


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --vp-bg: #07080c;
            --vp-bg-2: #0d1017;
            --vp-panel: #11151f;
            --vp-panel-2: #171c27;
            --vp-ink: #f5f7fb;
            --vp-muted: #9ba3b3;
            --vp-line: rgba(255, 255, 255, 0.1);
            --vp-red: #ff4655;
            --vp-red-dark: #b91f2e;
            --vp-red-soft: rgba(255, 70, 85, 0.16);
            --vp-ice: #f5f7fb;
            --vp-green: #30d08c;
            --vp-green-soft: rgba(48, 208, 140, 0.14);
            --vp-gold: #ffd166;
        }

        .stApp {
            background:
                linear-gradient(135deg, rgba(255, 70, 85, 0.12) 0%, rgba(255, 70, 85, 0) 26%),
                linear-gradient(180deg, #10131b 0%, var(--vp-bg) 44%, #050609 100%);
            color: var(--vp-ink);
        }

        header[data-testid="stHeader"] {
            background: rgba(7, 8, 12, 0.7);
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }

        .block-container {
            max-width: 1200px;
            padding-top: 1.35rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3, p, label {
            letter-spacing: 0;
        }

        h1, h2, h3, label,
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricValue"] {
            color: var(--vp-ink);
        }

        .vp-header {
            background:
                linear-gradient(116deg, rgba(255, 70, 85, 0.2), rgba(255, 70, 85, 0.02) 32%),
                linear-gradient(180deg, #191f2c, #0f131c);
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-left: 5px solid var(--vp-red);
            border-radius: 8px;
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.32);
            margin-bottom: 1.05rem;
            overflow: hidden;
            padding: 1.35rem 1.45rem 1.18rem;
            position: relative;
        }

        .vp-header::after {
            background: var(--vp-red);
            content: "";
            height: 3px;
            left: 1.45rem;
            position: absolute;
            right: 1.45rem;
            top: 0;
        }

        .vp-kicker {
            color: var(--vp-red);
            font-size: 0.76rem;
            font-weight: 900;
            margin-bottom: 0.42rem;
            text-transform: uppercase;
        }

        .vp-title {
            color: var(--vp-ink);
            font-size: 2.2rem;
            font-weight: 900;
            line-height: 1.1;
            margin: 0;
        }

        .vp-subtitle {
            color: #c8ceda;
            margin: 0.38rem 0 0;
            font-size: 0.98rem;
        }

        .vp-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.95rem;
        }

        .vp-chip {
            align-items: center;
            background: rgba(255, 70, 85, 0.1);
            border: 1px solid rgba(255, 70, 85, 0.24);
            border-radius: 6px;
            color: #fff0f2;
            display: inline-flex;
            font-size: 0.78rem;
            font-weight: 850;
            line-height: 1;
            padding: 0.46rem 0.64rem;
        }

        .vp-section {
            margin: 1rem 0 0.65rem;
        }

        .vp-section-title {
            color: var(--vp-ink);
            font-size: 1rem;
            font-weight: 900;
            margin: 0;
            padding-left: 0.62rem;
            position: relative;
        }

        .vp-section-title::before {
            background: var(--vp-red);
            content: "";
            height: 1.05rem;
            left: 0;
            position: absolute;
            top: 0.08rem;
            width: 3px;
        }

        .vp-section-meta {
            color: var(--vp-muted);
            font-size: 0.82rem;
            margin: 0.15rem 0 0;
        }

        .vp-team-heading {
            background: linear-gradient(90deg, rgba(255, 70, 85, 0.16), rgba(255, 70, 85, 0));
            border-bottom: 1px solid rgba(255, 70, 85, 0.24);
            color: var(--vp-ink);
            font-size: 0.95rem;
            font-weight: 900;
            margin: 0.95rem 0 0.7rem;
            padding: 0.5rem 0.65rem;
            text-transform: uppercase;
        }

        .vp-result-card {
            background:
                linear-gradient(135deg, rgba(255, 70, 85, 0.13), rgba(255, 255, 255, 0.02) 32%),
                linear-gradient(180deg, #141a25, #0d1119);
            border: 1px solid rgba(255, 255, 255, 0.11);
            border-left: 5px solid var(--vp-red);
            border-radius: 8px;
            box-shadow: 0 22px 54px rgba(0, 0, 0, 0.34);
            margin: 1.05rem 0;
            padding: 1.2rem 1.25rem;
        }

        .vp-result-top {
            align-items: flex-start;
            display: flex;
            gap: 1rem;
            justify-content: space-between;
        }

        .vp-eyebrow {
            color: var(--vp-red);
            font-size: 0.76rem;
            font-weight: 900;
            text-transform: uppercase;
        }

        .vp-winner {
            color: var(--vp-ink);
            font-size: 1.8rem;
            font-weight: 900;
            line-height: 1.15;
            margin-top: 0.15rem;
            overflow-wrap: anywhere;
        }

        .vp-confidence {
            background: rgba(255, 70, 85, 0.11);
            border: 1px solid rgba(255, 70, 85, 0.28);
            border-radius: 8px;
            min-width: 150px;
            padding: 0.7rem 0.85rem;
            text-align: right;
        }

        .vp-confidence strong {
            color: var(--vp-ink);
            display: block;
            font-size: 1.25rem;
            margin-top: 0.12rem;
        }

        .vp-prob-row {
            display: grid;
            gap: 0.55rem;
            grid-template-columns: minmax(120px, 1fr) minmax(160px, 2.2fr) 72px;
            margin-top: 0.85rem;
        }

        .vp-prob-label {
            color: #dce1ea;
            font-weight: 900;
            overflow-wrap: anywhere;
        }

        .vp-prob-value {
            color: var(--vp-ink);
            font-variant-numeric: tabular-nums;
            font-weight: 900;
            text-align: right;
        }

        .vp-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 999px;
            height: 0.72rem;
            overflow: hidden;
            margin-top: 0.32rem;
        }

        .vp-fill {
            background: linear-gradient(90deg, var(--vp-red-dark), var(--vp-red));
            border-radius: 999px;
            height: 100%;
        }

        .vp-fill.alt {
            background: linear-gradient(90deg, #d6dae3, #ffffff);
        }

        .vp-outcome {
            background: var(--vp-green-soft);
            border: 1px solid rgba(48, 208, 140, 0.28);
            border-radius: 8px;
            color: #d7ffec;
            font-weight: 900;
            margin: 0.75rem 0 0.3rem;
            padding: 0.8rem 0.95rem;
        }

        .vp-outcome.miss {
            background: rgba(255, 70, 85, 0.14);
            border-color: rgba(255, 70, 85, 0.34);
            color: #ffe4e8;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.055), rgba(255, 255, 255, 0.025));
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-radius: 8px;
            padding: 0.85rem 0.95rem;
        }

        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: var(--vp-ink);
        }

        div[data-testid="stMetric"] label {
            color: var(--vp-muted);
            font-weight: 800;
        }

        div[data-testid="stForm"] {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.055), rgba(255, 255, 255, 0.025));
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-radius: 8px;
            padding: 1rem;
        }

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {
            background: #0d1119;
            border-color: rgba(255, 255, 255, 0.13);
            color: var(--vp-ink);
        }

        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div,
        div[data-baseweb="input"] input {
            color: var(--vp-ink);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            overflow: hidden;
        }

        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            background: rgba(255, 255, 255, 0.035);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            gap: 0.25rem;
            padding: 0.25rem;
        }

        div[data-testid="stTabs"] [data-baseweb="tab"] {
            border-radius: 6px;
            color: var(--vp-muted);
            font-weight: 850;
        }

        div[data-testid="stTabs"] [aria-selected="true"] {
            background: var(--vp-red);
            color: #ffffff;
        }

        div.stButton > button,
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 8px;
            font-weight: 900;
            text-transform: uppercase;
        }

        @media (max-width: 760px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .vp-result-top,
            .vp-prob-row {
                display: block;
            }

            .vp-confidence {
                margin-top: 0.75rem;
                text-align: left;
            }

            .vp-prob-value {
                margin-top: 0.25rem;
                text-align: left;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _safe(value: object) -> str:
    return escape(str(value), quote=True)


def _chip_row(labels: list[str]) -> str:
    return "".join(f'<span class="vp-chip">{_safe(label)}</span>' for label in labels)


def _page_header() -> None:
    st.markdown(
        f"""
        <div class="vp-header">
            <div class="vp-kicker">Match Control</div>
            <h1 class="vp-title">{_safe(APP_TITLE)}</h1>
            <p class="vp-subtitle">Tactical win probability console</p>
            <div class="vp-chip-row">
                {_chip_row(["Advanced", "125F", "Replay", "Prior Stats"])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section(title: str, meta: str | None = None) -> None:
    meta_html = f'<p class="vp-section-meta">{_safe(meta)}</p>' if meta else ""
    st.markdown(
        f"""
        <div class="vp-section">
            <p class="vp-section-title">{_safe(title)}</p>
            {meta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _options() -> dict:
    return available_options()


@st.cache_resource(show_spinner=False)
def _model_meta() -> dict:
    _, meta = load_model()
    return meta


@st.cache_data(show_spinner=False)
def _reports() -> dict:
    return load_reports()


@st.cache_data(show_spinner=False)
def _global_importance() -> list[dict]:
    return global_feature_importance()


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _verdict_short(verdict: str | None) -> str:
    if not verdict:
        return "-"
    verdict_text = str(verdict)
    if verdict_text.startswith("PASS"):
        return "통과"
    if verdict_text.upper() == "FAIL":
        return "실패"
    return verdict_label(verdict_text)


def _probability_row(label: str, value: float, *, alt: bool = False) -> str:
    width = max(0.0, min(float(value) * 100, 100.0))
    alt_class = " alt" if alt else ""
    return f"""
        <div class="vp-prob-row">
            <div class="vp-prob-label">{_safe(label)}</div>
            <div class="vp-track"><div class="vp-fill{alt_class}" style="width: {width:.1f}%"></div></div>
            <div class="vp-prob-value">{_pct(float(value))}</div>
        </div>
    """


def _lineup_inputs(team_label: str, players: list[str], agents: list[str], offset: int) -> list[dict[str, str]]:
    st.markdown(f'<div class="vp-team-heading">{_safe(team_label)}</div>', unsafe_allow_html=True)
    slots: list[dict[str, str]] = []
    for idx in range(5):
        c1, c2 = st.columns([1.25, 1])
        player_index = min(offset + idx, max(len(players) - 1, 0))
        with c1:
            player = st.selectbox(
                f"{team_label} 선수 {idx + 1}",
                players,
                index=player_index,
                key=f"{team_label}_player_{idx}",
            )
        with c2:
            agent = st.selectbox(
                f"{team_label} 요원 {idx + 1}",
                agents,
                index=(offset + idx) % max(len(agents), 1),
                format_func=agent_label,
                key=f"{team_label}_agent_{idx}",
            )
        slots.append({"player": player, "agent": agent})
    return slots


def _top_feature_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=["영향 피처", "현재 값", "중요도", "기여도"])
    frame = frame.rename(
        columns={
            "feature": "영향 피처",
            "value": "현재 값",
            "importance": "중요도",
            "contribution": "기여도",
        }
    )
    frame["영향 피처"] = frame["영향 피처"].map(feature_label)
    return frame[["영향 피처", "현재 값", "중요도", "기여도"]]


def _render_prediction(result) -> None:
    winner = result.team_a if result.predicted_label else result.team_b
    st.markdown(
        f"""
        <div class="vp-result-card">
            <div class="vp-result-top">
                <div>
                    <div class="vp-eyebrow">예측 승자</div>
                    <div class="vp-winner">{_safe(winner)}</div>
                </div>
                <div class="vp-confidence">
                    <span class="vp-eyebrow">확신도</span>
                    <strong>{_pct(result.confidence)}</strong>
                </div>
            </div>
            {_probability_row(result.team_a, result.team_a_win_probability)}
            {_probability_row(result.team_b, result.team_b_win_probability, alt=True)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.2, 1])
    with left:
        _section("승률 영향 피처")
        st.dataframe(_top_feature_frame(result.top_features), width="stretch", hide_index=True)
    with right:
        _section("역할군 구성")
        st.dataframe(pd.DataFrame(result.role_counts).T, width="stretch")


def _custom_tab(options: dict) -> None:
    players = options["players"]
    agents = options["agents"]
    if len(players) < 10:
        st.error("data/processed/players.csv에서 선택 가능한 선수가 10명보다 적습니다.")
        return

    result_area = st.container()
    _section("라인업 입력")
    with st.form("custom_lineup_form"):
        top_left, top_right = st.columns([1, 1])
        with top_left:
            map_name = st.selectbox("맵", options["maps"], format_func=map_label)
        with top_right:
            years = options["years"] or [2026]
            cutoff_year = st.selectbox("기준 연도", years, index=len(years) - 1)

        col_a, col_b = st.columns(2)
        with col_a:
            team_a_slots = _lineup_inputs("A팀", players, agents, 0)
        with col_b:
            team_b_slots = _lineup_inputs("B팀", players, agents, 5)

        submitted = st.form_submit_button(
            "예측하기",
            type="primary",
            icon=":material/play_arrow:",
            width="stretch",
        )

    if submitted:
        with result_area:
            with st.spinner("이전 연도 선수 기록과 맵-요원 기록을 계산하는 중입니다. 첫 실행은 조금 걸릴 수 있습니다."):
                try:
                    st.session_state["custom_prediction_result"] = predict_custom_lineup(
                        map_name=map_name,
                        cutoff_year=int(cutoff_year),
                        team_a_slots=team_a_slots,
                        team_b_slots=team_b_slots,
                    )
                    st.session_state["custom_prediction_error"] = None
                except ValueError as exc:
                    st.session_state["custom_prediction_result"] = None
                    st.session_state["custom_prediction_error"] = str(exc)

    with result_area:
        error = st.session_state.get("custom_prediction_error")
        result = st.session_state.get("custom_prediction_result")
        if error:
            st.error(error)
        elif result:
            _render_prediction(result)


def _replay_tab(options: dict) -> None:
    replay_matches = options["replay_matches"]
    labels = {row["label"]: row["match_key"] for row in replay_matches}
    _section("테스트 경기")
    selected = st.selectbox("테스트 경기", list(labels))
    result = predict_replay_match(labels[selected])

    predicted_winner = result.team_a if result.predicted_label else result.team_b
    actual_winner = result.team_a if result.actual_label else result.team_b
    outcome = "적중" if result.predicted_label == result.actual_label else "불일치"
    outcome_class = "" if result.predicted_label == result.actual_label else " miss"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("판정", outcome)
    c2.metric("실제 승자", actual_winner)
    c3.metric("맵", map_label(result.map_name))
    c4.metric("경기 키", result.match_key or "-")
    st.markdown(
        f'<div class="vp-outcome{outcome_class}">예측 승자: {_safe(predicted_winner)} / 실제 승자: {_safe(actual_winner)}</div>',
        unsafe_allow_html=True,
    )
    _render_prediction(result)


def _model_tab() -> None:
    meta = _model_meta()
    reports = _reports()
    metrics = reports.get("metrics", {})
    validation = reports.get("validation", {})

    _section("모델 상태")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("피처 수", meta.get("n_features", "-"))
    c2.metric("테스트 AUC", f"{metrics.get('test_auc', 0.0):.4f}")
    c3.metric("테스트 정확도", f"{metrics.get('test_acc', 0.0):.4f}")
    c4.metric("검증", _verdict_short(validation.get("final_verdict")))

    left, right = st.columns([1, 1])
    with left:
        importance = pd.DataFrame(_global_importance())
        if not importance.empty:
            importance["feature"] = importance["feature"].map(feature_label)
            importance = importance.rename(columns={"feature": "피처", "importance": "중요도"})
        _section("전체 모델 피처 중요도")
        st.dataframe(importance, width="stretch", hide_index=True)
    with right:
        rows = [
            {
                "검증 항목": key,
                "value": value if isinstance(value, str) else json.dumps(value, ensure_ascii=False),
            }
            for key, value in validation.items()
            if key not in {"passed_checks", "failed_checks"}
        ]
        for row in rows:
            if row["검증 항목"] == "final_verdict":
                row["value"] = verdict_label(row["value"])
        validation_frame = pd.DataFrame(rows).rename(columns={"value": "값"})
        _section("검증 요약")
        st.dataframe(validation_frame, width="stretch", hide_index=True)


def main() -> None:
    _inject_css()
    _page_header()
    options = _options()
    custom, replay, model = st.tabs(["커스텀 5v5", "경기 다시보기", "모델 근거"])
    with custom:
        _custom_tab(options)
    with replay:
        _replay_tab(options)
    with model:
        _model_tab()


if __name__ == "__main__":
    main()
