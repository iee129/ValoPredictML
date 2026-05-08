"""ml/train_model.py — RF + XGBoost + LightGBM 학습 + Optuna HPO + 앙상블 저장."""
from __future__ import annotations  # 파이썬이 오래된 버전이어도 최신 방식으로 타입을 적을 수 있게 해줌

import argparse  # 터미널에서 '--input 폴더명' 처럼 옵션을 받아오는 도구
import json  # 결과를 메모장(JSON 파일)에 저장할 때 쓰는 도구
from datetime import datetime  # 모델을 저장한 날짜·시각을 기록하기 위해 쓰는 도구
from pathlib import Path  # 파일 경로를 다루기 편하게 해주는 도구 (예: "폴더/파일" 구조 탐색)

import joblib  # 학습이 끝난 모델을 파일로 저장하거나 불러올 때 쓰는 도구
import lightgbm as lgb  # LightGBM 선생님 모델을 만들고 쓰는 도구
import numpy as np  # 숫자 배열을 빠르게 계산할 때 쓰는 도구 (예: 평균 내기)
import optuna  # 어떤 설정값이 가장 좋은지 자동으로 수백 번 실험해서 찾아주는 도구
import pandas as pd  # 표(데이터프레임) 형태로 데이터를 다루는 도구
import xgboost as xgb  # XGBoost 선생님 모델을 만들고 쓰는 도구
from sklearn.ensemble import RandomForestClassifier  # Random Forest(랜덤 포레스트) 선생님 모델
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score  # 모델 성적표를 매기는 세 가지 채점 함수
from scipy.optimize import minimize  # 앙상블 가중치 val-AUC 최적화에 사용
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold  # 같은 경기 데이터가 훈련용과 시험용에 동시에 들어가지 않도록 조심해서 나누는 방법

from ml.data_pipeline import FEATURE_COLS_P1, FEATURE_COLS_P2, FEATURE_COLS_P3, FEATURE_COLS_P4  # 전처리 단계에서 만들어 둔 피처(특징) 컬럼 목록 가져오기

optuna.logging.set_verbosity(optuna.logging.WARNING)  # Optuna가 실험할 때마다 너무 많은 로그를 출력하지 않도록 경고 수준만 보이게 설정

FEATURE_COLS: list[str] = FEATURE_COLS_P1 + FEATURE_COLS_P2 + FEATURE_COLS_P3 + FEATURE_COLS_P4  # 네 단계에서 만든 특징 목록을 합침 (총 59개)

_YEAR_WEIGHTS: dict[int, float] = {2025: 2.0, 2024: 1.8, 2023: 1.4, 2022: 1.2}
_CLOSE_MATCH_BOOST: float = 1.5  # 박빙 경기(스코어 차 ≤3)에 부여하는 추가 가중치


def _compute_sample_weights(df_train: pd.DataFrame) -> np.ndarray:
    """연도 가중치 + 박빙 경기 부스트를 결합한 샘플 가중치를 반환한다."""
    def _year(row: pd.Series) -> int:
        date_str = str(row.get("date", ""))
        if date_str and len(date_str) >= 4 and date_str[:4].isdigit():
            return int(date_str[:4])
        event = str(row.get("event", ""))
        for yr in (2025, 2024, 2023, 2022):
            if str(yr) in event:
                return yr
        return 2021

    years = df_train.apply(_year, axis=1)
    weights = years.map(_YEAR_WEIGHTS).fillna(1.0)
    if "score_a" in df_train.columns and "score_b" in df_train.columns:
        score_diff = (df_train["score_a"] - df_train["score_b"]).abs()
        weights = weights * score_diff.apply(lambda d: _CLOSE_MATCH_BOOST if d <= 3 else 1.0)
    return weights.to_numpy(dtype=float)


# ── 데이터 로드 ────────────────────────────────────────────────────────────────

def load_splits(input_dir: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:  # 훈련·검증·시험용으로 미리 나눠 둔 세 파일을 읽어오는 함수
    base = Path(input_dir)  # 데이터가 들어있는 폴더 경로를 다루기 쉬운 객체로 바꿈
    df_train = pd.read_csv(base / "train.csv", low_memory=False)  # 모델을 가르칠 훈련 데이터 읽기 (학교 수업 자료 같은 것)
    df_val   = pd.read_csv(base / "val.csv",   low_memory=False)  # 중간 점검용 검증 데이터 읽기 (쪽지 시험 같은 것)
    df_test  = pd.read_csv(base / "test.csv",  low_memory=False)  # 최종 실력 확인용 시험 데이터 읽기 (기말고사 같은 것)
    for name, df in [("train", df_train), ("val", df_val), ("test", df_test)]:  # 세 파일 모두 필요한 특징 열이 다 있는지 확인
        missing = [c for c in FEATURE_COLS if c not in df.columns]  # 있어야 할 특징 중에서 빠진 것들을 골라냄
        if missing:  # 빠진 특징이 하나라도 있으면 어떤 파일에서 무엇이 없는지 알려주며 멈춤
            raise ValueError(f"{name}.csv에 피처 컬럼 누락: {missing}")  # 예를 들어 "train.csv에 'avg_kills' 컬럼이 없어요!" 하고 알려줌
    return df_train, df_val, df_test  # 세 데이터 묶음을 한 번에 돌려줌


# ── 모델 학습 ─────────────────────────────────────────────────────────────────

def train_rf(
    X_train: pd.DataFrame,  # 선생님께 보여줄 훈련 데이터의 특징 표
    y_train: pd.Series,  # 각 경기의 정답(1=팀A 승, 0=팀B 승) 목록
    params: dict | None = None,  # 모델 설정값을 직접 넣고 싶을 때 사용 (없으면 기본값 사용)
    sample_weight: np.ndarray | None = None,  # 경기별 학습 가중치 (최신 경기에 더 높은 값)
) -> RandomForestClassifier:  # 학습을 마친 랜덤 포레스트 선생님 모델을 돌려줌
    default = dict(  # 랜덤 포레스트의 기본 설정값들 (마치 선생님의 기본 교수법)
        n_estimators=300,  # 결정 트리(나무) 300그루를 심어서 다수결로 답을 결정함 — 나무가 많을수록 안정적
        max_features="sqrt",  # 각 나무가 특징을 고를 때 전체 개수의 제곱근만큼만 봄 — 나무들이 서로 다른 시각을 갖게 해서 실력을 높여줌
        oob_score=True,  # 학습에 쓰이지 않은 데이터로 자체 점검 점수를 계산함 (공짜 미니 시험)
        n_jobs=-1,  # 컴퓨터의 모든 CPU 코어를 동시에 써서 학습 속도를 빠르게 함
        random_state=42,  # 같은 숫자(42)를 넣으면 언제 실행해도 똑같은 결과가 나오게 고정
    )
    if params:  # 외부에서 다른 설정값을 넣어줬다면 기본값 위에 덮어씀
        default.update(params)  # 예를 들어 Optuna가 찾은 더 좋은 설정으로 교체
    model = RandomForestClassifier(**default)  # 설정값을 가지고 랜덤 포레스트 선생님을 만듦
    model.fit(X_train, y_train, sample_weight=sample_weight)  # 훈련 데이터를 보여주며 선생님을 가르침
    print(f"[RF] OOB Score: {model.oob_score_:.4f}")  # 자체 점검 점수를 화면에 출력 (1에 가까울수록 좋음)
    return model  # 학습이 끝난 랜덤 포레스트 선생님을 돌려줌


def train_xgb(
    X_train: pd.DataFrame,  # 선생님께 보여줄 훈련 데이터의 특징 표
    y_train: pd.Series,  # 각 경기의 정답 목록
    X_val: pd.DataFrame,  # 중간 점검에 쓸 검증 데이터의 특징 표 (실력이 더 오르는지 확인하기 위해)
    y_val: pd.Series,  # 검증 데이터의 정답 목록
    params: dict | None = None,  # 모델 설정값을 직접 넣고 싶을 때 사용 (없으면 기본값 사용)
    sample_weight: np.ndarray | None = None,  # 경기별 학습 가중치
) -> xgb.XGBClassifier:  # 학습을 마친 XGBoost 선생님 모델을 돌려줌
    default = dict(  # XGBoost의 기본 설정값들
        n_estimators=500,  # 최대 500라운드까지 조금씩 실력을 키워나감 (실제로는 일찍 멈출 수도 있음)
        max_depth=4,  # 각 나무가 질문을 최대 4단계 깊이까지 할 수 있음 (5→4로 줄여 과적합 방지)
        learning_rate=0.05,  # 한 번에 조금씩(5%) 배우는 학습률 — 느리지만 실수를 줄여줌
        subsample=0.8,  # 매 라운드마다 훈련 데이터의 80%만 무작위로 골라 씀 — 다양한 관점을 배우게 함
        colsample_bytree=0.7,  # 매 라운드마다 특징의 70%만 무작위로 골라 씀 (0.8→0.7 강화)
        reg_alpha=0.1,  # 불필요한 특징의 영향을 줄여주는 L1 벌점 (작은 값들을 0으로 만드는 효과)
        reg_lambda=2.0,  # 특징의 영향력이 너무 커지지 않게 눌러주는 L2 벌점 (1.0→2.0 강화)
        min_child_weight=7,  # 나무 가지 하나에 최소 7개 이상의 데이터가 있어야 함 (5→7로 올려 과적합 방지)
        gamma=0.1,  # 가지를 새로 만들 때 최소 이 만큼 나아져야 허락함 — 의미 없는 가지를 차단
        objective="binary:logistic",  # 이기거나(1) 지거나(0), 둘 중 하나를 맞히는 문제로 설정
        eval_metric="logloss",  # 중간 점검 때 예측이 얼마나 확신에 찼는지로 점수를 매김
        early_stopping_rounds=50,  # 50라운드 동안 점수가 안 오르면 더 하지 않고 멈춤 (시간 낭비 방지)
        tree_method="hist",  # 데이터를 구간으로 나눠서 빠르게 학습하는 방식
        random_state=42,  # 결과를 재현할 수 있도록 랜덤 시드 고정
        n_jobs=-1,  # 모든 CPU 코어를 동시에 써서 빠르게 학습
    )
    if params:  # 외부에서 다른 설정값을 넣어줬다면 기본값 위에 덮어씀
        default.update(params)  # Optuna가 찾아준 더 좋은 설정으로 교체
    model = xgb.XGBClassifier(**default)  # 설정값을 가지고 XGBoost 선생님을 만듦
    model.fit(X_train, y_train, sample_weight=sample_weight, eval_set=[(X_val, y_val)], verbose=100)  # 훈련하면서 100라운드마다 검증 세트로 중간 점검
    val_acc = accuracy_score(y_val, model.predict(X_val))  # 검증 데이터에서 몇 문제를 맞혔는지 정확도 계산
    print(f"[XGBoost] Val Accuracy: {val_acc:.4f}, Best iter: {model.best_iteration}")  # 검증 정확도와 몇 라운드에서 가장 좋았는지 출력
    return model  # 학습이 끝난 XGBoost 선생님을 돌려줌


def train_lgbm(
    X_train: pd.DataFrame,  # 선생님께 보여줄 훈련 데이터의 특징 표
    y_train: pd.Series,  # 각 경기의 정답 목록
    X_val: pd.DataFrame,  # 중간 점검에 쓸 검증 데이터의 특징 표
    y_val: pd.Series,  # 검증 데이터의 정답 목록
    params: dict | None = None,  # 모델 설정값을 직접 넣고 싶을 때 사용 (없으면 기본값 사용)
    sample_weight: np.ndarray | None = None,  # 경기별 학습 가중치
) -> lgb.LGBMClassifier:  # 학습을 마친 LightGBM 선생님 모델을 돌려줌
    default = dict(  # LightGBM의 기본 설정값들
        n_estimators=500,  # 최대 500라운드까지 조금씩 실력을 키워나감
        num_leaves=25,  # 나무의 잎사귀(끝 가지) 수를 25개로 제한 (31→25, 과적합 방지)
        max_depth=-1,  # 나무 깊이는 제한 없음 (-1) — 대신 잎사귀 수(num_leaves)로 복잡도를 조절
        learning_rate=0.05,  # 한 번에 조금씩(5%) 배우는 학습률
        subsample=0.8,  # 매 라운드마다 훈련 데이터의 80%만 무작위로 골라 씀
        subsample_freq=1,  # 위 80% 샘플링을 매 라운드마다 적용
        colsample_bytree=0.7,  # 매 라운드마다 특징의 70%만 무작위로 골라 씀 (0.8→0.7 강화)
        reg_alpha=0.1,  # 불필요한 특징을 줄여주는 L1 벌점
        reg_lambda=2.0,  # 특징 영향력을 눌러주는 L2 벌점 (1.0→2.0 강화)
        min_child_samples=30,  # 잎사귀 하나에 최소 30개의 데이터가 있어야 만들 수 있음 (20→30, 과적합 방지)
        objective="binary",  # 이기거나(1) 지거나(0), 둘 중 하나를 맞히는 문제로 설정
        metric="binary_logloss",  # 중간 점검 때 예측이 얼마나 확신에 찼는지로 점수를 매김
        random_state=42,  # 결과를 재현할 수 있도록 랜덤 시드 고정
        n_jobs=-1,  # 모든 CPU 코어를 동시에 써서 빠르게 학습
        verbose=-1,  # LightGBM 내부 로그를 완전히 끔 (콘솔이 지저분해지는 것 방지)
    )
    if params:  # 외부에서 다른 설정값을 넣어줬다면 기본값 위에 덮어씀
        default.update(params)  # Optuna가 찾아준 더 좋은 설정으로 교체
    model = lgb.LGBMClassifier(**default)  # 설정값을 가지고 LightGBM 선생님을 만듦
    model.fit(
        X_train, y_train,
        sample_weight=sample_weight,
        eval_set=[(X_val, y_val)],  # 검증 데이터로 중간 점검하며 학습
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(100)],  # 50라운드 동안 점수가 안 오르면 멈추고, 100라운드마다 진행 상황 출력
    )
    val_acc = accuracy_score(y_val, model.predict(X_val))  # 검증 데이터에서 몇 문제를 맞혔는지 정확도 계산
    print(f"[LightGBM] Val Accuracy: {val_acc:.4f}, Best iter: {model.best_iteration_}")  # 검증 정확도와 최적 라운드 출력
    return model  # 학습이 끝난 LightGBM 선생님을 돌려줌


# ── Optuna HPO ────────────────────────────────────────────────────────────────

def _xgb_objective(
    trial: optuna.Trial,  # Optuna가 건네주는 "이번 실험 번호표" — 이 번호표로 설정값을 제안 받음
    X: pd.DataFrame,  # 실험에 쓸 특징 표 (훈련 전체 데이터)
    y: pd.Series,  # 각 경기의 정답 목록
    df: pd.DataFrame,  # match_key 열이 있는 전체 데이터프레임 (경기 단위로 나누기 위해 필요)
    n_splits: int = 5,  # 데이터를 몇 조각으로 나눌지 (기본 5조각)
) -> float:  # 이번 실험에서 얻은 평균 AUC 점수를 돌려줌 (Optuna가 이 숫자를 높이려고 노력함)
    params = dict(  # Optuna가 이번 실험에서 제안한 설정값 조합 (마치 레시피를 조금씩 바꿔가며 맛을 테스트하는 것)
        max_depth=trial.suggest_int("max_depth", 3, 10),  # 나무 깊이를 3~10 사이에서 골라봄
        min_child_weight=trial.suggest_int("min_child_weight", 1, 10),  # 최소 자식 데이터 수를 1~10 사이에서 골라봄
        gamma=trial.suggest_float("gamma", 0.0, 1.0),  # 가지 만들기 최소 이득을 0.0~1.0 사이에서 골라봄
        learning_rate=trial.suggest_float("learning_rate", 0.01, 0.3, log=True),  # 학습률을 0.01~0.3 사이에서 골라봄 (작은 값도 충분히 탐색하도록 로그 스케일 사용)
        n_estimators=trial.suggest_int("n_estimators", 200, 2000),  # 라운드 수를 200~2000 사이에서 골라봄
        subsample=trial.suggest_float("subsample", 0.5, 1.0),  # 훈련 데이터 사용 비율을 50~100% 사이에서 골라봄
        colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),  # 특징 사용 비율을 50~100% 사이에서 골라봄
        reg_alpha=trial.suggest_float("reg_alpha", 0.0, 1.0),  # L1 벌점을 0.0~1.0 사이에서 골라봄
        reg_lambda=trial.suggest_float("reg_lambda", 0.1, 10.0, log=True),  # L2 벌점을 0.1~10.0 사이에서 골라봄 (로그 스케일)
        objective="binary:logistic",  # 이기거나 지거나 예측하는 문제 고정
        eval_metric="logloss",  # 중간 점검 기준 고정
        early_stopping_rounds=30,  # HPO 실험 중에는 30라운드 개선 없으면 빨리 멈춤 (실험 속도 향상)
        tree_method="hist",  # 빠른 히스토그램 방식 고정
        random_state=42,  # 실험 간 공정한 비교를 위해 시드 고정
        n_jobs=-1,  # 모든 CPU 코어 사용
    )
    gkf = GroupKFold(n_splits=n_splits)  # 같은 경기 데이터가 훈련용과 시험용에 동시에 들어가지 않도록 조심해서 나누는 방법으로 5조각 생성
    groups = df["match_key"].str.replace(r"_swap$", "", regex=True)  # 팀A·B를 뒤집어 만든 복사본이 다른 조각에 들어가는 것을 막기 위해 '_swap' 꼬리말 제거
    auc_scores = []  # 각 조각에서 받은 AUC 점수를 모아둘 빈 리스트
    for step, (tr_idx, vl_idx) in enumerate(gkf.split(X, y, groups=groups)):  # 5개 조각을 차례로 돌면서 학습·평가 반복
        X_tr, X_vl = X.iloc[tr_idx], X.iloc[vl_idx]  # 이번 조각에서 훈련용과 검증용 특징 표를 분리
        y_tr, y_vl = y.iloc[tr_idx], y.iloc[vl_idx]  # 이번 조각에서 훈련용과 검증용 정답을 분리
        model = xgb.XGBClassifier(**params, verbosity=0)  # 이번 실험 설정으로 XGBoost 모델 생성 (로그 없이)
        model.fit(X_tr, y_tr, eval_set=[(X_vl, y_vl)], verbose=False)  # 훈련하면서 검증 세트로 조기 종료 감시
        auc = roc_auc_score(y_vl, model.predict_proba(X_vl)[:, 1])  # 이번 조각에서 모델이 승리팀을 맞힐 확률을 0~1로 나타낸 AUC 점수 계산
        auc_scores.append(auc)  # 이번 조각 점수를 목록에 추가
        trial.report(auc, step=step)  # Optuna에게 "이번 조각 결과는 이래요"라고 보고
        if trial.should_prune():  # Optuna가 "이 실험은 가망 없어, 그만해"라고 하면
            raise optuna.exceptions.TrialPruned()  # 이번 실험을 중간에 포기하고 다음 실험으로 넘어감
    return float(np.mean(auc_scores))  # 5개 조각의 AUC 평균을 이번 실험의 최종 점수로 Optuna에 돌려줌


def _lgbm_objective(
    trial: optuna.Trial,  # Optuna가 건네주는 "이번 실험 번호표"
    X: pd.DataFrame,  # 실험에 쓸 특징 표
    y: pd.Series,  # 각 경기의 정답 목록
    df: pd.DataFrame,  # match_key 열이 있는 전체 데이터프레임
    n_splits: int = 5,  # 데이터를 몇 조각으로 나눌지 (기본 5조각)
) -> float:  # 이번 실험에서 얻은 평균 AUC 점수를 돌려줌
    params = dict(  # Optuna가 이번 실험에서 제안한 LightGBM 설정값 조합
        num_leaves=trial.suggest_int("num_leaves", 15, 127),  # 잎사귀 수를 15~127 사이에서 골라봄
        min_child_samples=trial.suggest_int("min_child_samples", 10, 100),  # 잎 최소 데이터 수를 10~100 사이에서 골라봄
        learning_rate=trial.suggest_float("learning_rate", 0.01, 0.3, log=True),  # 학습률을 0.01~0.3 사이에서 골라봄 (로그 스케일)
        n_estimators=trial.suggest_int("n_estimators", 200, 2000),  # 라운드 수를 200~2000 사이에서 골라봄
        subsample=trial.suggest_float("subsample", 0.5, 1.0),  # 훈련 데이터 사용 비율을 50~100% 사이에서 골라봄
        subsample_freq=1,  # 샘플링을 매 라운드 적용 (고정)
        colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),  # 특징 사용 비율을 50~100% 사이에서 골라봄
        reg_alpha=trial.suggest_float("reg_alpha", 0.0, 1.0),  # L1 벌점을 0.0~1.0 사이에서 골라봄
        reg_lambda=trial.suggest_float("reg_lambda", 0.0, 10.0),  # L2 벌점을 0.0~10.0 사이에서 골라봄
        min_split_gain=trial.suggest_float("min_split_gain", 0.0, 1.0),  # 가지 만들기 최소 이득을 0.0~1.0 사이에서 골라봄
        max_bin=63,  # 데이터를 구간으로 쪼갤 때 최대 63구간만 씀 — 속도를 빠르게 하기 위해 HPO 중에만 이 값으로 제한
        objective="binary",  # 이기거나 지거나 예측하는 문제 고정
        metric="binary_logloss",  # 중간 점검 기준 고정
        random_state=42,  # 실험 간 공정한 비교를 위해 시드 고정
        n_jobs=-1,  # 모든 CPU 코어 사용
        verbose=-1,  # LightGBM 내부 로그 완전히 끔
    )
    gkf = GroupKFold(n_splits=n_splits)  # 같은 경기 데이터가 훈련용과 시험용에 동시에 들어가지 않도록 조심해서 나누는 방법으로 5조각 생성
    groups = df["match_key"].str.replace(r"_swap$", "", regex=True)  # 팀A·B를 뒤집어 만든 복사본이 다른 조각에 들어가는 것을 막기 위해 '_swap' 꼬리말 제거
    auc_scores = []  # 각 조각에서 받은 AUC 점수를 모아둘 빈 리스트
    for step, (tr_idx, vl_idx) in enumerate(gkf.split(X, y, groups=groups)):  # 5개 조각을 차례로 돌면서 학습·평가 반복
        X_tr, X_vl = X.iloc[tr_idx], X.iloc[vl_idx]  # 이번 조각에서 훈련용과 검증용 특징 표를 분리
        y_tr, y_vl = y.iloc[tr_idx], y.iloc[vl_idx]  # 이번 조각에서 훈련용과 검증용 정답을 분리
        model = lgb.LGBMClassifier(**params)  # 이번 실험 설정으로 LightGBM 모델 생성
        model.fit(
            X_tr, y_tr,
            eval_set=[(X_vl, y_vl)],  # 검증 데이터로 조기 종료 감시
            callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(0)],  # 30라운드 개선 없으면 멈추고, 로그는 완전히 끔
        )
        auc = roc_auc_score(y_vl, model.predict_proba(X_vl)[:, 1])  # 이번 조각에서 모델이 승리팀을 맞힐 확률을 0~1로 나타낸 AUC 점수 계산
        auc_scores.append(auc)  # 이번 조각 점수를 목록에 추가
        trial.report(auc, step=step)  # Optuna에게 중간 결과 보고
        if trial.should_prune():  # Optuna가 이 실험을 포기하라고 하면
            raise optuna.exceptions.TrialPruned()  # 이번 실험을 중단하고 다음 실험으로 넘어감
    return float(np.mean(auc_scores))  # 5개 조각의 AUC 평균을 이번 실험의 최종 점수로 Optuna에 돌려줌


def optimize_model(
    model_type: str,  # 최적화할 모델 종류: "xgb"(XGBoost) 또는 "lgbm"(LightGBM)
    X_train: pd.DataFrame,  # 훈련 데이터의 특징 표
    y_train: pd.Series,  # 훈련 데이터의 정답 목록
    df_train: pd.DataFrame,  # match_key 열이 있는 훈련 데이터프레임 (경기 단위 나누기용)
    n_trials: int = 100,  # 몇 번이나 다른 설정으로 실험해볼지 (기본 100번)
    timeout: int = 3600,  # 최대 몇 초까지 실험할지 (기본 1시간)
) -> dict:  # 가장 좋은 성적을 낸 설정값 묶음을 돌려줌
    print(f"\n[Optuna] {model_type.upper()} 최적화 시작 (trials={n_trials})")  # 어떤 모델을 몇 번 실험할지 화면에 알림
    study = optuna.create_study(  # Optuna 최적화 세션(스터디)을 새로 만듦 — 마치 레시피 테스트 기록장
        study_name=f"valorant_{model_type}_v1",  # 이 스터디의 이름 (나중에 결과를 찾아볼 때 식별자)
        direction="maximize",  # AUC가 높을수록 좋으니 최대화하는 방향으로 실험
        sampler=optuna.samplers.TPESampler(seed=42, n_startup_trials=20),  # 처음 20번은 무작위로 실험하고, 그 후부터는 좋은 결과를 보고 영리하게 다음 설정을 골라주는 알고리즘 사용
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=3),  # 중간 성적이 평균에 못 미치는 실험을 일찍 포기하게 해서 시간을 아끼는 장치
    )
    if model_type == "xgb":  # XGBoost를 최적화하는 경우
        fn = lambda t: _xgb_objective(t, X_train, y_train, df_train)  # XGBoost 실험 함수에 데이터를 미리 묶어 둠
    elif model_type == "lgbm":  # LightGBM을 최적화하는 경우
        fn = lambda t: _lgbm_objective(t, X_train, y_train, df_train)  # LightGBM 실험 함수에 데이터를 미리 묶어 둠
    else:
        raise ValueError(f"지원하지 않는 모델: {model_type}")  # "xgb"도 "lgbm"도 아니면 "그런 모델은 없어요!"라고 알려줌
    study.optimize(fn, n_trials=n_trials, timeout=timeout, gc_after_trial=True)  # 설정한 횟수·시간만큼 실험 반복 (매 실험 후 메모리를 청소해 컴퓨터가 느려지지 않게 함)
    print(f"[Optuna] {model_type.upper()} 최적 AUC: {study.best_value:.4f}")  # 가장 좋은 실험에서 얻은 AUC 점수 출력
    return study.best_params  # 가장 좋은 성적을 낸 설정값 묶음을 돌려줌


# ── 앙상블 + 평가 ──────────────────────────────────────────────────────────────

_ENSEMBLE_WEIGHTS = {"rf": 0.50, "xgb": 0.25, "lgbm": 0.25}  # RF가 박빙 경기에서 더 강해 비중을 높임


def _optimize_ensemble_weights(
    rf_val: np.ndarray,
    xgb_val: np.ndarray,
    lgbm_val: np.ndarray,
    y_val: pd.Series,
) -> dict[str, float]:
    """validation AUC 기반으로 최적 앙상블 가중치를 scipy.optimize로 탐색한다."""
    def neg_auc(w: np.ndarray) -> float:
        w_abs = np.abs(w)
        w_norm = w_abs / (w_abs.sum() + 1e-12)
        probs = w_norm[0] * rf_val + w_norm[1] * xgb_val + w_norm[2] * lgbm_val
        return -roc_auc_score(y_val, probs)

    x0 = np.array([0.50, 0.25, 0.25])
    bounds = [(0.15, 0.80), (0.05, 0.50), (0.05, 0.50)]
    result = minimize(neg_auc, x0, method="L-BFGS-B", bounds=bounds)
    w = np.abs(result.x)
    w = w / w.sum()
    return {"rf": float(w[0]), "xgb": float(w[1]), "lgbm": float(w[2])}


def calibrate_models(models: dict, X_val: pd.DataFrame, y_val: pd.Series) -> dict:
    """val set으로 각 기본 모델에 isotonic 확률 보정을 적용하고 보정된 모델 dict를 반환한다."""
    calibrated: dict = {}
    for name, model in models.items():
        cal = CalibratedClassifierCV(model, cv="prefit", method="isotonic")
        cal.fit(X_val, y_val)
        calibrated[name] = cal
    return calibrated


def train_oof_stack(
    df_trainval: pd.DataFrame,
    X_trainval: pd.DataFrame,
    y_trainval: pd.Series,
    best_params: dict,
) -> LogisticRegression:
    """train+val 데이터로 OOF 예측을 생성하고 LogisticRegression 메타 학습기를 반환한다."""
    groups = df_trainval["match_key"].str.replace(r"_swap$", "", regex=True)
    gkf = GroupKFold(n_splits=5)
    oof_rf   = np.zeros(len(df_trainval))
    oof_xgb  = np.zeros(len(df_trainval))
    oof_lgbm = np.zeros(len(df_trainval))

    for tr_idx, vl_idx in gkf.split(X_trainval, y_trainval, groups=groups):
        X_tr, X_vl = X_trainval.iloc[tr_idx], X_trainval.iloc[vl_idx]
        y_tr = y_trainval.iloc[tr_idx]
        df_tr = df_trainval.iloc[tr_idx]

        sw = _compute_sample_weights(df_tr)
        fold_rf = train_rf(X_tr, y_tr, sample_weight=sw)
        fold_xgb = train_xgb(
            X_tr, y_tr, X_vl, y_trainval.iloc[vl_idx],
            best_params.get("xgb") or None, sample_weight=sw,
        )
        fold_lgbm = train_lgbm(
            X_tr, y_tr, X_vl, y_trainval.iloc[vl_idx],
            best_params.get("lgbm") or None, sample_weight=sw,
        )
        oof_rf[vl_idx]   = fold_rf.predict_proba(X_vl)[:, 1]
        oof_xgb[vl_idx]  = fold_xgb.predict_proba(X_vl)[:, 1]
        oof_lgbm[vl_idx] = fold_lgbm.predict_proba(X_vl)[:, 1]

    oof_stack = np.column_stack([oof_rf, oof_xgb, oof_lgbm])
    meta = LogisticRegression(C=1.0, max_iter=1000)
    meta.fit(oof_stack, y_trainval)
    return meta


def ensemble_predict_proba(
    models: dict, X: pd.DataFrame, meta_learner: LogisticRegression | None = None
) -> np.ndarray:
    rf_p   = models["rf"].predict_proba(X)[:, 1]
    xgb_p  = models["xgb"].predict_proba(X)[:, 1]
    lgbm_p = models["lgbm"].predict_proba(X)[:, 1]
    if meta_learner is not None:
        stack = np.column_stack([rf_p, xgb_p, lgbm_p])
        return meta_learner.predict_proba(stack)[:, 1]
    return _ENSEMBLE_WEIGHTS["rf"] * rf_p + _ENSEMBLE_WEIGHTS["xgb"] * xgb_p + _ENSEMBLE_WEIGHTS["lgbm"] * lgbm_p


def evaluate_split(
    models: dict,  # 성적을 매길 모델들이 담긴 묶음
    X: pd.DataFrame,  # 성적을 볼 데이터의 특징 표 (검증 또는 시험 데이터)
    y: pd.Series,  # 정답 목록
    split_name: str,  # 어떤 데이터인지 이름 (화면 출력에 쓰임, 예: "Val", "Test")
) -> dict:  # 각 모델과 앙상블의 성적표(정확도·F1·AUC)를 담은 묶음을 돌려줌
    results: dict[str, dict] = {}  # 모델별 성적을 담아둘 빈 묶음
    for name, model in models.items():  # 각 선생님 모델을 하나씩 꺼내 성적 계산
        pred = model.predict(X)  # 선생님이 각 경기의 승패를 예측
        prob = model.predict_proba(X)[:, 1]  # 선생님이 팀A가 이길 확률을 숫자로 출력
        results[name] = dict(  # 이 선생님의 성적표 작성
            accuracy=float(accuracy_score(y, pred)),  # 정확도: 100문제 중 몇 문제나 맞혔는지 비율
            f1=float(f1_score(y, pred, average="macro")),  # F1 점수: 이기는 팀과 지는 팀 모두 공평하게 평가한 점수
            roc_auc=float(roc_auc_score(y, prob)),  # AUC: 모델이 승리팀을 맞힐 확률을 0~1로 나타낸 점수 (1에 가까울수록 훌륭)
        )
    ens_prob = ensemble_predict_proba(models, X)  # 세 선생님의 예측 확률을 평균 낸 앙상블 최종 확률
    ens_pred = (ens_prob >= 0.5).astype(int)  # 앙상블 확률이 50% 이상이면 팀A 승리(1), 미만이면 팀B 승리(0)로 예측
    results["ensemble"] = dict(  # 앙상블의 성적표 작성
        accuracy=float(accuracy_score(y, ens_pred)),  # 앙상블 정확도
        f1=float(f1_score(y, ens_pred, average="macro")),  # 앙상블 F1 점수
        roc_auc=float(roc_auc_score(y, ens_prob)),  # 앙상블 AUC 점수
    )
    print(f"\n[{split_name}]")  # 어떤 데이터셋 성적인지 제목 출력
    for name, m in results.items():  # 모든 모델과 앙상블의 성적을 차례로 출력
        print(f"  {name:10s} Acc={m['accuracy']:.4f} F1={m['f1']:.4f} AUC={m['roc_auc']:.4f}")  # 이름, 정확도, F1, AUC를 나란히 출력
    return results  # 전체 성적표 묶음을 돌려줌


# ── 저장 ──────────────────────────────────────────────────────────────────────

def save_models(
    models: dict,
    best_params: dict,
    metrics: dict,
    train_samples: int,
    output_dir: str,
    calibrated_models: dict | None = None,
    meta_learner: LogisticRegression | None = None,
) -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    name_map = {"rf": "rf_model", "xgb": "xgboost_model", "lgbm": "lgbm_model"}
    for key, fname in name_map.items():
        joblib.dump(models[key], Path(output_dir) / f"{fname}.joblib")
    if calibrated_models:
        for key in ("rf", "xgb", "lgbm"):
            joblib.dump(calibrated_models[key], Path(output_dir) / f"{key}_calibrated.joblib")
    if meta_learner is not None:
        joblib.dump(meta_learner, Path(output_dir) / "meta_learner.joblib")
    metadata = dict(  # 모델 학습 정보를 정리한 메모장 내용
        trained_at=datetime.now().isoformat(),  # 이 모델을 저장한 날짜와 시각
        feature_cols=FEATURE_COLS,  # 학습에 사용한 특징 목록 (나중에 예측할 때 같은 특징을 넣어야 함)
        feature_count=len(FEATURE_COLS),  # 특징의 개수 (54개)
        train_samples=train_samples,  # 훈련에 쓰인 경기 수
        val_metrics=metrics.get("val", {}),  # 검증 데이터에서의 성적표
        test_metrics=metrics.get("test", {}),  # 시험 데이터에서의 성적표
        best_params=best_params,  # Optuna가 찾아낸 가장 좋은 설정값 기록
        ensemble_weights=dict(_ENSEMBLE_WEIGHTS),  # 앙상블 가중치 스냅샷 (최적화 후 갱신된 값)
    )
    with open(Path(output_dir) / "model_metadata.json", "w", encoding="utf-8") as f:  # 메모장 파일을 쓰기 모드로 열기
        json.dump(metadata, f, indent=2, ensure_ascii=False)  # 들여쓰기 2칸, 한글이 깨지지 않게 그대로 저장
    print(f"\n[INFO] 모델 저장 완료 → {output_dir}/")  # 저장이 끝났다고 화면에 알림


# ── 메인 ──────────────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> None:  # 터미널에서 받은 옵션들을 보고 전체 학습 과정을 순서대로 실행하는 함수
    df_train, df_val, df_test = load_splits(args.input)  # 전처리된 훈련·검증·시험 데이터를 불러옴
    X_train = df_train[FEATURE_COLS]  # 훈련 데이터에서 특징 표만 꺼냄
    y_train = df_train["label"]  # 훈련 데이터에서 정답(승패)만 꺼냄
    X_val   = df_val[FEATURE_COLS]  # 검증 데이터에서 특징 표만 꺼냄
    y_val   = df_val["label"]  # 검증 데이터에서 정답만 꺼냄
    X_test  = df_test[FEATURE_COLS]  # 시험 데이터에서 특징 표만 꺼냄
    y_test  = df_test["label"]  # 시험 데이터에서 정답만 꺼냄

    best_params: dict = {"xgb": {}, "lgbm": {}}  # 최적 설정값 초기화 (Optuna를 안 쓰면 빈 묶음으로 남음)
    if args.optimize:  # 터미널에서 --optimize를 붙이면 Optuna 자동 설정 탐색 실행
        best_params["xgb"]  = optimize_model("xgb",  X_train, y_train, df_train, args.n_trials)  # XGBoost 설정을 수백 번 실험해서 가장 좋은 것 찾기
        best_params["lgbm"] = optimize_model("lgbm", X_train, y_train, df_train, args.n_trials)  # LightGBM 설정을 수백 번 실험해서 가장 좋은 것 찾기

    sample_weights = _compute_sample_weights(df_train)

    print("\n[Train] RF 학습 중...")  # 랜덤 포레스트 학습 시작 알림
    rf_model = train_rf(X_train, y_train, sample_weight=sample_weights)

    print("\n[Train] XGBoost 학습 중...")  # XGBoost 학습 시작 알림
    xgb_model = train_xgb(X_train, y_train, X_val, y_val, best_params["xgb"] if args.optimize else None, sample_weight=sample_weights)

    print("\n[Train] LightGBM 학습 중...")  # LightGBM 학습 시작 알림
    lgbm_model = train_lgbm(X_train, y_train, X_val, y_val, best_params["lgbm"] if args.optimize else None, sample_weight=sample_weights)

    models = {"rf": rf_model, "xgb": xgb_model, "lgbm": lgbm_model}  # 세 선생님 모델을 이름표를 달아 한 묶음으로 모음

    print("\n[Ensemble] validation AUC 기반 가중치 최적화 중...")
    rf_val_p   = rf_model.predict_proba(X_val)[:, 1]
    xgb_val_p  = xgb_model.predict_proba(X_val)[:, 1]
    lgbm_val_p = lgbm_model.predict_proba(X_val)[:, 1]
    opt_weights = _optimize_ensemble_weights(rf_val_p, xgb_val_p, lgbm_val_p, y_val)
    _ENSEMBLE_WEIGHTS.update(opt_weights)
    print(f"[Ensemble] 최적 가중치: RF={opt_weights['rf']:.3f}, XGB={opt_weights['xgb']:.3f}, LGBM={opt_weights['lgbm']:.3f}")
    Path(args.output).mkdir(parents=True, exist_ok=True)
    with open(Path(args.output) / "ensemble_weights.json", "w", encoding="utf-8") as _f:
        json.dump(opt_weights, _f, indent=2)

    print("\n[Calibration] val set으로 확률 보정 중...")
    calibrated_models = calibrate_models(models, X_val, y_val)
    print("[Calibration] 완료")

    print("\n[OOF Stack] train+val OOF 스태킹 메타 학습기 훈련 중...")
    df_trainval = pd.concat([df_train, df_val], ignore_index=True)
    X_trainval  = df_trainval[FEATURE_COLS]
    y_trainval  = df_trainval["label"]
    meta_learner = train_oof_stack(df_trainval, X_trainval, y_trainval, best_params)
    print("[OOF Stack] 완료")

    val_metrics  = evaluate_split(calibrated_models, X_val,  y_val,  "Val")
    test_metrics = evaluate_split(calibrated_models, X_test, y_test, "Test")

    save_models(
        models=models,
        best_params=best_params,
        metrics={"val": val_metrics, "test": test_metrics},
        train_samples=len(df_train),
        output_dir=args.output,
        calibrated_models=calibrated_models,
        meta_learner=meta_learner,
    )

    Path(args.reports).mkdir(parents=True, exist_ok=True)  # 리포트 저장 폴더가 없으면 새로 만듦
    summary = dict(  # 학습 전체 결과를 정리한 요약 메모장 내용
        trained_at=datetime.now().isoformat(),  # 학습이 끝난 날짜·시각
        train_samples=len(df_train),  # 훈련에 쓰인 경기 수
        val_samples=len(df_val),  # 검증에 쓰인 경기 수
        test_samples=len(df_test),  # 시험에 쓰인 경기 수
        val_metrics=val_metrics,  # 검증 성적표
        test_metrics=test_metrics,  # 시험 성적표
        best_params=best_params,  # Optuna 최적 설정값
    )
    with open(Path(args.reports) / "train_summary.json", "w", encoding="utf-8") as f:  # 요약 파일을 쓰기 모드로 열기
        json.dump(summary, f, indent=2, ensure_ascii=False)  # 들여쓰기 2칸, 한글이 깨지지 않게 그대로 저장
    print("\n[INFO] 완료 ✅")  # 모든 학습 과정이 끝났다고 화면에 알림


def main() -> None:  # 터미널에서 이 파일을 실행할 때 가장 먼저 호출되는 함수
    parser = argparse.ArgumentParser(description="ValoPredictML 모델 학습")  # 터미널 옵션 안내 설명 파서 생성
    parser.add_argument("--input",    required=True,  help="data/processed/ 디렉토리")  # 전처리 데이터 폴더 경로 (반드시 넣어야 함)
    parser.add_argument("--output",   required=True,  help="models/ 디렉토리")  # 모델 저장 폴더 경로 (반드시 넣어야 함)
    parser.add_argument("--reports",  required=True,  help="reports/ 디렉토리")  # 리포트 저장 폴더 경로 (반드시 넣어야 함)
    parser.add_argument("--optimize", action="store_true", help="Optuna HPO 실행")  # 이 옵션을 붙이면 Optuna로 자동 설정 탐색을 함 (선택)
    parser.add_argument("--n-trials", type=int, default=100, dest="n_trials",
                        help="Optuna trial 수 (기본 100)")  # Optuna 실험 횟수 (선택, 기본 100번)
    args = parser.parse_args()  # 터미널에서 입력한 옵션들을 읽어서 변수에 담음
    run(args)  # 읽어온 옵션으로 전체 학습 파이프라인 실행


if __name__ == "__main__":  # 이 파일을 직접 실행할 때만 아래 코드가 동작함 (다른 파일에서 불러쓸 때는 동작 안 함)
    main()  # 터미널 옵션 읽기 → 전체 학습 실행
