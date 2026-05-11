from __future__ import annotations  # 오래된 파이썬에서도 새로운 방식으로 변수 종류를 표현할 수 있게 해주는 설정

import json  # eval_summary.json(모델 성능 기록)과 baseline_comparison.json(비교 결과)을 읽기 위한 기본 도구
from pathlib import Path  # 파일 경로를 문자열 대신 더 편리하게 다룰 수 있게 해주는 도구

import pandas as pd  # 모델별 성능을 엑셀처럼 생긴 표로 만들기 위한 도구
import streamlit as st  # 화면에 제목·숫자 카드·차트·표를 그려주는 도구

_EVAL_PATH = Path("reports/eval_summary.json")  # AI 모델 평가 결과가 저장된 파일의 경로
_BASELINE_PATH = Path("reports/baseline_comparison.json")  # 기존 단순 예측(베이스라인)과 비교한 결과가 저장된 파일의 경로
_FALLBACK = {"auc": 0.9355, "accuracy": 0.854, "f1": 0.851}  # 평가 파일이 없을 때 대신 쓸 기준 성능값 (CLAUDE.md에 기록된 검증값)


def render() -> None:  # 소개 화면 전체를 화면에 그려주는 함수
    st.title("소개 — ValoPredictML")  # 페이지 맨 위에 크게 제목을 보여줌

    st.markdown(  # 프로젝트 소개와 사용 방법을 화면에 글로 보여줌
        """
        **ValoPredictML**은 발로란트 5v5 팀 구성 기반 승률 예측 도구입니다.

        RandomForest + XGBoost + LightGBM 앙상블 모델이 요원 역할 조합, 맵, 선수 통계를 분석해
        팀 A의 승리 확률을 제공합니다.

        **사용 방법**: 예측 탭에서 맵과 양 팀의 요원을 선택한 뒤 예측 실행 버튼을 누르세요.
        """
    )

    st.markdown("---")  # 소개 글과 모델 성능 섹션 사이에 가로 줄을 그어 구분
    st.markdown("### 모델 성능")  # "모델 성능"이라는 중간 제목을 화면에 표시

    if _EVAL_PATH.exists():  # 평가 결과 파일이 있으면 실제 측정값을 사용
        with open(_EVAL_PATH, encoding="utf-8") as f:  # 한글이 깨지지 않도록 UTF-8 방식으로 파일을 열어서
            eval_data = json.load(f)  # 파이썬이 읽을 수 있는 사전 형태로 변환
        ens_raw = eval_data.get("test", {}).get("ensemble", {})  # 앙상블(3개 모델 합산) 테스트 결과를 꺼냄
        ens = {
            "auc": ens_raw.get("roc_auc", _FALLBACK["auc"]),
            "accuracy": ens_raw.get("accuracy", _FALLBACK["accuracy"]),
            "f1": ens_raw.get("f1", _FALLBACK["f1"]),
        }
        st.caption("출처: reports/eval_summary.json")  # 어디서 가져온 수치인지 작은 글씨로 안내
    else:  # 평가 파일이 없으면 미리 저장해둔 기준값을 대신 사용
        eval_data = {}  # 파일이 없으니 빈 사전으로 시작
        ens = _FALLBACK  # CLAUDE.md에 기록된 검증값을 기준값으로 사용
        st.caption("출처: CLAUDE.md 기준 검증값 (eval_summary.json 없음)")  # 대체 수치임을 작은 글씨로 안내

    c1, c2, c3 = st.columns(3)  # 3개의 성능 지표를 나란히 보여줄 세 칸을 만듦
    c1.metric("AUC", f"{ens.get('auc', 0):.4f}")  # AUC(모델이 얼마나 잘 구분하는지 점수, 1에 가까울수록 좋음)를 예쁜 숫자 카드로 표시
    c2.metric("Accuracy", f"{ens.get('accuracy', 0):.4f}")  # Accuracy(100번 예측하면 몇 번 맞히는지 비율)를 예쁜 숫자 카드로 표시
    c3.metric("F1", f"{ens.get('f1', 0):.4f}")  # F1(정밀도와 재현율을 합친 종합 점수)을 예쁜 숫자 카드로 표시

    model_rows = []  # 모델별 성능 비교 표의 행(가로 줄)들을 모을 빈 바구니
    for model_name, metrics in eval_data.get("test", {}).items():  # 각 모델(RF·XGBoost·LightGBM)의 성능 데이터를 하나씩 꺼냄
        if model_name == "ensemble":
            continue
        model_rows.append({  # 이 모델의 성능 지표를 한 줄로 정리
            "모델": model_name,  # 모델 이름 (예: rf, xgboost, lgbm)
            "AUC (KFold)": f"{eval_data.get(model_name, {}).get('roc_auc_mean', 0):.4f}",  # 여러 번 나눠서 검증한 평균 AUC 점수
            "AUC (Test)": f"{metrics.get('roc_auc', 0):.4f}",  # 최종 테스트 데이터로 측정한 AUC 점수
            "Accuracy": f"{metrics.get('accuracy', 0):.4f}",  # 테스트 데이터에서 맞힌 비율
            "F1": f"{metrics.get('f1', 0):.4f}",  # 테스트 데이터에서의 F1 종합 점수
        })
    if model_rows:  # 모델 데이터가 하나라도 있으면 비교 표를 보여줌
        st.markdown("### 모델별 성능 비교")  # "모델별 성능 비교"라는 중간 제목을 표시
        st.dataframe(pd.DataFrame(model_rows), use_container_width=True)  # 모델별 성능을 화면 전체 너비의 엑셀 표로 보여줌

    feat_imp = eval_data.get("feature_importance", {})  # 어떤 특징(피처)이 예측에 얼마나 중요한지 수치를 꺼냄
    if feat_imp:  # 피처 중요도 데이터가 있을 때만 차트를 그려줌
        st.markdown("### Feature Importance (상위 20개)")  # "피처 중요도 상위 20개"라는 중간 제목을 표시
        fi_df = (
            pd.DataFrame(list(feat_imp.items()), columns=["피처", "중요도"])  # 피처 이름과 중요도를 표(DataFrame)로 만듦
            .sort_values("중요도", ascending=False)  # 중요도가 높은 순서대로 정렬
            .head(20)  # 상위 20개만 남김
            .reset_index(drop=True)  # 줄 번호를 0부터 새로 매김 (기존 번호는 버림)
        )
        st.bar_chart(fi_df.set_index("피처")["중요도"])  # 피처 이름을 가로축으로 하는 막대 그래프를 화면에 그림

    if _BASELINE_PATH.exists():  # 베이스라인 비교 파일이 있으면 비교 섹션을 추가로 보여줌
        st.markdown("---")  # 가로 줄로 섹션 구분
        with open(_BASELINE_PATH, encoding="utf-8") as f:  # 한글이 깨지지 않도록 UTF-8 방식으로 파일을 열어서
            bl = json.load(f)  # 파이썬이 읽을 수 있는 사전 형태로 변환
        st.markdown("### 베이스라인 비교")  # "베이스라인 비교"라는 중간 제목을 표시
        b1, b2, b3 = st.columns(3)  # 3개의 비교 지표를 나란히 보여줄 세 칸을 만듦
        b1.metric("앙상블 Accuracy", f"{bl.get('ensemble_test_acc', 0):.4f}")  # 우리 AI 모델의 정확도를 예쁜 숫자 카드로 표시
        b2.metric("다수 클래스 Accuracy", f"{bl.get('majority_acc', 0):.4f}")  # 단순 예측(베이스라인)의 정확도를 예쁜 숫자 카드로 표시
        b3.metric("개선폭", f"+{bl.get('improvement_over_majority_pct', 0):.2f}%p")  # 베이스라인보다 얼마나 더 좋아졌는지를 예쁜 숫자 카드로 표시
