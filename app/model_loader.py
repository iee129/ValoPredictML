from __future__ import annotations  # 파이썬 버전이 낮아도 최신 방식으로 타입을 쓸 수 있게 해주는 설정

import json
from pathlib import Path  # 파일 경로를 다루는 도구 (예: "models 폴더에 rf_model.joblib 파일이 있나?" 확인 가능)

import pandas as pd  # AI 모델에 넣을 숫자 표(DataFrame)를 다루기 위한 도구
import streamlit as st  # 화면을 만드는 도구이면서, 같은 결과를 기억해두는 메모 스티커 기능도 제공

from ml.data_pipeline import FEATURE_COLS
from ml.train_model import normalize_ensemble_weights

_MODELS_DIR = Path("models")  # 학습이 끝난 AI 모델 파일들이 저장된 폴더 이름
_MODEL_FILES = {
    "rf": "rf_model.joblib",
    "xgb": "xgboost_model.joblib",
    "lgbm": "lgbm_model.joblib",
}


def _load_metadata() -> dict:
    metadata_path = _MODELS_DIR / "model_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(
            "models/model_metadata.json 없음\n"
            "먼저 실행: python -m ml.train_model --input data/processed --output models --reports reports"
        )
    with metadata_path.open(encoding="utf-8") as f:
        metadata = json.load(f)

    feature_cols = metadata.get("feature_cols")
    if feature_cols != FEATURE_COLS:
        raise RuntimeError(
            "모델 metadata feature contract가 현재 P1-P4 57개 피처와 다릅니다. "
            f"metadata feature_count={metadata.get('feature_count')}, current={len(FEATURE_COLS)}. "
            "data_pipeline -> train_model -> evaluate_model 순서로 산출물을 재생성하세요."
        )
    if metadata.get("feature_count") != len(FEATURE_COLS):
        raise RuntimeError(
            f"metadata feature_count 불일치: {metadata.get('feature_count')} != {len(FEATURE_COLS)}"
        )
    metadata["ensemble_weights"] = normalize_ensemble_weights(metadata.get("ensemble_weights"))
    return metadata


def _validate_model_shapes(models: dict, feature_count: int) -> None:
    bad: dict[str, int] = {}
    for name, model in models.items():
        n_features = getattr(model, "n_features_in_", None)
        if n_features is not None and int(n_features) != feature_count:
            bad[name] = int(n_features)
    if bad:
        raise RuntimeError(
            f"모델 파일 feature 수가 metadata와 다릅니다: {bad}, metadata={feature_count}. "
            "models/ 산출물을 재학습으로 맞춰야 합니다."
        )


def _validate_feature_frame(features: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    cols = list(features.columns)
    if cols == feature_cols:
        return features
    missing = [col for col in feature_cols if col not in features.columns]
    extra = [col for col in features.columns if col not in feature_cols]
    if missing or extra:
        raise ValueError(f"예측 피처 불일치: missing={missing}, extra={extra}")
    return features[feature_cols]


@st.cache_resource  # 이 함수의 결과를 기억해뒀다가, 같은 요청이 오면 다시 계산하지 않고 바로 돌려주는 메모 스티커 (모델 파일을 매번 다시 읽지 않아도 돼요)
def load_models() -> dict:  # 저장된 AI 모델 3개(RF·XGBoost·LightGBM)를 파일에서 읽어서 묶음으로 돌려주는 함수
    import joblib  # 파이썬 객체를 파일로 저장하거나 파일에서 읽어오는 도구 (처음 호출할 때만 불러와요)

    metadata = _load_metadata()
    models: dict = {}  # 읽어온 모델들을 담아둘 빈 서랍
    missing = [fname for fname in _MODEL_FILES.values() if not (_MODELS_DIR / fname).exists()]  # 파일이 없는 모델 이름만 골라서 목록으로 만들기
    if missing:  # 모델 파일이 하나라도 없으면 무슨 파일이 없는지 알려주고 멈춤
        raise FileNotFoundError(
            f"모델 파일 없음: {missing}\n"
            "먼저 실행: python -m ml.train_model --input data/processed --output models --reports reports"
        )  # 어떤 명령어를 실행해야 모델 파일이 생기는지 안내해 주는 에러 메시지
    for key, filename in _MODEL_FILES.items():  # 필요한 모델 파일 이름을 하나씩 꺼내며 반복
        models[key] = joblib.load(_MODELS_DIR / filename)  # 파일에서 모델을 읽어서 rf/xgb/lgbm 이름으로 서랍에 넣기
    _validate_model_shapes(models, metadata["feature_count"])
    models["__metadata__"] = metadata
    models["__feature_cols__"] = metadata["feature_cols"]
    models["__ensemble_weights__"] = metadata["ensemble_weights"]
    return models  # 3개 모델이 담긴 서랍 반환


def predict(models: dict, features: pd.DataFrame) -> float:  # 3개 AI 모델이 각자 예측한 확률을 평균 내어 최종 승률을 계산하는 함수
    feature_cols = models.get("__feature_cols__", FEATURE_COLS)
    weights = models.get("__ensemble_weights__", normalize_ensemble_weights(None))
    features = _validate_feature_frame(features, feature_cols)
    rf_p = float(models["rf"].predict_proba(features)[0, 1])  # RF(랜덤 포레스트) 모델이 예측한 팀A 승리 확률
    xgb_p = float(models["xgb"].predict_proba(features)[0, 1])  # XGBoost 모델이 예측한 팀A 승리 확률
    lgbm_p = float(models["lgbm"].predict_proba(features)[0, 1])  # LightGBM 모델이 예측한 팀A 승리 확률
    return weights["rf"] * rf_p + weights["xgb"] * xgb_p + weights["lgbm"] * lgbm_p  # metadata 기준 가중 앙상블 확률 반환


def compute_shap(models: dict, features: pd.DataFrame) -> dict[str, float]:  # 어떤 숫자 정보(피처)가 승률 예측에 얼마나 영향을 미쳤는지 계산하는 함수
    import shap  # AI 모델의 예측 이유를 설명해주는 도구 (처음 호출할 때만 불러와요)
    features = _validate_feature_frame(features, models.get("__feature_cols__", FEATURE_COLS))
    explainer = shap.TreeExplainer(models["rf"])  # 나무 구조 AI 모델 전용 설명 도우미를 RF 모델로 만들기
    shap_vals = explainer.shap_values(features)  # 각 숫자 정보가 예측에 얼마나 기여했는지 점수 계산
    if isinstance(shap_vals, list):  # 승/패 두 가지 결과를 각각 계산했을 때는 리스트 형태로 나올 수 있어요
        vals = shap_vals[1][0]  # 승리(1번 결과)에 대한 첫 번째 경기의 기여도 점수만 꺼냄
    else:
        vals = shap_vals[0, :, 1] if shap_vals.ndim == 3 else shap_vals[0]  # 3차원이면 승리 축의 값, 2차원이면 첫 경기의 값을 사용
    return dict(zip(features.columns, map(float, vals)))  # 숫자 정보 이름과 기여도 점수를 짝지어서 {"정보이름": 기여도점수} 형태로 반환
