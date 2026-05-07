"""ml/evaluate_model.py — GroupKFold(5) 교차검증 + SHAP 피처 중요도 + 리포트."""
from __future__ import annotations  # 파이썬이 오래된 버전이어도 최신 방식으로 타입을 적을 수 있게 해줌

import argparse  # 터미널에서 '--input 폴더명' 처럼 옵션을 받아오는 도구
import copy  # 모델 객체를 안전하게 복사할 때 쓰는 도구 (원본을 건드리지 않고 복사본으로 실험하기 위해)
import json  # 평가 결과를 메모장(JSON 파일)에 저장할 때 쓰는 도구
from pathlib import Path  # 파일 경로를 다루기 편하게 해주는 도구

import joblib  # 저장된 선생님 모델 파일(.joblib)을 불러올 때 쓰는 도구
import lightgbm as lgb  # LightGBM 선생님 모델 종류 확인과 콜백 설정에 사용
import numpy as np  # 숫자 배열 계산(평균, 절댓값 등)에 쓰는 도구
import pandas as pd  # 표(데이터프레임) 형태로 데이터를 다루는 도구
import shap  # 어떤 특징(피처)이 예측에 얼마나 영향을 줬는지 점수로 알려주는 도구
import xgboost as xgb  # XGBoost 선생님 모델 종류 확인과 검증 세트 설정에 사용
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score  # 모델 성적표를 매기는 세 가지 채점 함수
from sklearn.model_selection import GroupKFold  # 같은 경기 데이터가 훈련용과 시험용에 동시에 들어가지 않도록 조심해서 나누는 방법

from ml.data_pipeline import FEATURE_COLS_P1, FEATURE_COLS_P2, FEATURE_COLS_P3  # 전처리 단계에서 만들어 둔 특징 컬럼 목록 가져오기
from ml.train_model import ensemble_predict_proba  # 세 선생님의 예측 확률을 평균 내는 앙상블 함수 가져오기

FEATURE_COLS: list[str] = FEATURE_COLS_P1 + FEATURE_COLS_P2 + FEATURE_COLS_P3  # 세 단계에서 만든 특징 목록을 합침


# ── 모델 로드 ─────────────────────────────────────────────────────────────────

def load_models(models_dir: str) -> dict:  # 저장된 세 선생님 모델 파일을 읽어서 이름표를 달아 묶음으로 돌려주는 함수
    base = Path(models_dir)  # 모델 파일이 담긴 폴더 경로를 다루기 쉬운 객체로 바꿈
    return {
        "rf":   joblib.load(base / "rf_model.joblib"),  # 랜덤 포레스트 선생님 파일 불러오기
        "xgb":  joblib.load(base / "xgboost_model.joblib"),  # XGBoost 선생님 파일 불러오기
        "lgbm": joblib.load(base / "lgbm_model.joblib"),  # LightGBM 선생님 파일 불러오기
    }


# ── GroupKFold 교차검증 ────────────────────────────────────────────────────────

def kfold_evaluate(
    models: dict,  # 평가할 모델들이 담긴 묶음 {"rf": ..., "xgb": ..., "lgbm": ...}
    df_train: pd.DataFrame,  # 교차검증에 쓸 훈련 데이터프레임 (최종 시험 데이터는 절대 사용 안 함)
    feature_cols: list[str],  # 모델에 넣어줄 특징 컬럼 이름 목록
    n_splits: int = 5,  # 데이터를 몇 조각으로 나눌지 (기본 5조각)
) -> dict:  # 각 모델과 앙상블의 조각별 평균·표준편차 성적을 담은 묶음을 돌려줌
    """train.csv에서 GroupKFold(5), groups=match_key.
    각 모델 + 앙상블의 fold별 Accuracy/F1/AUC → mean/std 반환.
    test.csv는 절대 사용하지 않음.
    """
    X = df_train[feature_cols]  # 훈련 데이터에서 특징 표만 꺼냄
    y = df_train["label"]  # 훈련 데이터에서 정답(0=팀B 승, 1=팀A 승)만 꺼냄
    gkf = GroupKFold(n_splits=n_splits)  # 같은 경기 데이터가 훈련용과 시험용에 동시에 들어가지 않도록 조심해서 5조각으로 나누는 분할기 생성
    # _swap suffix 제거: augment된 twin row가 다른 fold에 들어가는 leakage 방지
    groups = df_train["match_key"].str.replace(r"_swap$", "", regex=True)  # 팀A·B를 뒤집어 만든 복사본이 다른 조각에 함께 들어가지 않도록 '_swap' 꼬리말 제거

    fold_scores: dict[str, list[dict]] = {name: [] for name in list(models.keys()) + ["ensemble"]}  # 각 모델·앙상블의 조각별 점수를 담아둘 빈 리스트 묶음 초기화

    for fold, (tr_idx, vl_idx) in enumerate(gkf.split(X, y, groups=groups), 1):  # 조각 번호를 1부터 시작해 차례로 꺼냄
        X_tr, X_vl = X.iloc[tr_idx], X.iloc[vl_idx]  # 이번 조각에서 훈련용과 검증용 특징 표를 나눔
        y_tr, y_vl = y.iloc[tr_idx], y.iloc[vl_idx]  # 이번 조각에서 훈련용과 검증용 정답을 나눔
        fold_models: dict = {}  # 이번 조각에서 새로 가르친 모델들을 담아둘 묶음
        for name, model in models.items():  # 각 선생님 모델을 하나씩 꺼내 이번 조각으로 다시 가르침
            m = copy.deepcopy(model)  # 원본 선생님 모델을 건드리지 않도록 완전히 복사본을 만들어 사용
            if isinstance(m, xgb.XGBClassifier):  # XGBoost 선생님이면 검증 세트로 조기 종료를 감시하며 학습
                m.fit(X_tr, y_tr, eval_set=[(X_vl, y_vl)], verbose=False)  # 검증 점수가 안 오르면 일찍 멈추게 하고, 로그 출력은 끔
            elif isinstance(m, lgb.LGBMClassifier):  # LightGBM 선생님이면 콜백으로 조기 종료 설정
                m.fit(
                    X_tr, y_tr,
                    eval_set=[(X_vl, y_vl)],  # 검증 데이터로 조기 종료 감시
                    callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],  # 50조각 개선 없으면 멈추고, 로그 출력 완전히 끔
                )
            else:
                m.fit(X_tr, y_tr)  # 랜덤 포레스트 같은 나머지 모델은 그냥 학습
            fold_models[name] = m  # 이번 조각에서 학습 완료된 모델을 이름표 달아 저장
            pred = m.predict(X_vl)  # 검증 데이터의 승패를 예측
            prob = m.predict_proba(X_vl)[:, 1]  # 팀A가 이길 확률을 0~1 숫자로 출력
            fold_scores[name].append(dict(  # 이번 조각의 성적 세 가지를 목록에 추가
                accuracy=float(accuracy_score(y_vl, pred)),  # 정확도: 맞힌 비율
                f1=float(f1_score(y_vl, pred, average="macro")),  # F1 점수: 이기는 팀과 지는 팀 모두 공평하게 평가한 점수
                roc_auc=float(roc_auc_score(y_vl, prob)),  # AUC: 모델이 승리팀을 맞힐 확률을 0~1로 나타낸 점수 (1에 가까울수록 훌륭)
            ))
        ens_prob = ensemble_predict_proba(fold_models, X_vl)  # 이번 조각에서 세 선생님의 예측 확률을 평균 낸 앙상블 결과
        ens_pred = (ens_prob >= 0.5).astype(int)  # 앙상블 확률이 50% 이상이면 팀A 승리(1), 미만이면 팀B 승리(0)
        fold_scores["ensemble"].append(dict(  # 앙상블의 이번 조각 성적을 목록에 추가
            accuracy=float(accuracy_score(y_vl, ens_pred)),  # 앙상블 정확도
            f1=float(f1_score(y_vl, ens_pred, average="macro")),  # 앙상블 F1 점수
            roc_auc=float(roc_auc_score(y_vl, ens_prob)),  # 앙상블 AUC 점수
        ))
        print(f"Fold {fold}/{n_splits} | "  # 몇 번째 조각이 끝났는지 진행 상황 출력
              + " | ".join(f"{n}: Acc={fold_scores[n][-1]['accuracy']:.4f}"
                           for n in list(models.keys()) + ["ensemble"]))  # 각 모델·앙상블의 이번 조각 정확도를 나란히 출력

    results: dict[str, dict] = {}  # 전체 조각의 평균·표준편차를 담아둘 최종 결과 묶음
    for name, scores in fold_scores.items():  # 각 모델·앙상블의 조각별 점수 묶음을 하나씩 꺼냄
        for metric in ("accuracy", "f1", "roc_auc"):  # 정확도, F1, AUC 세 가지 지표를 차례로 처리
            vals = [s[metric] for s in scores]  # 모든 조각에서의 해당 지표 값을 리스트로 모음
            results.setdefault(name, {})[f"{metric}_mean"] = float(np.mean(vals))  # 조각들의 평균 계산 (평균 성적)
            results.setdefault(name, {})[f"{metric}_std"]  = float(np.std(vals))  # 조각들의 표준편차 계산 (성적이 얼마나 고른지)
    print("\n[K-Fold 결과]")  # 전체 교차검증 결과 요약 제목 출력
    for name, m in results.items():  # 각 모델·앙상블의 종합 결과를 차례로 출력
        print(f"  {name:10s} Acc={m['accuracy_mean']:.4f}±{m['accuracy_std']:.4f}  "
              f"AUC={m['roc_auc_mean']:.4f}±{m['roc_auc_std']:.4f}")  # 평균±표준편차 형식으로 출력 (예: 0.8540±0.0032)
    return results  # 전체 조각의 평균·표준편차가 담긴 결과 묶음을 돌려줌


# ── test 최종 평가 ────────────────────────────────────────────────────────────

def test_evaluate(
    models: dict,  # 평가할 선생님 모델들이 담긴 묶음
    df_test: pd.DataFrame,  # 최종 실력 확인에 쓸 시험 데이터프레임 (기말고사 같은 것)
    feature_cols: list[str],  # 모델에 넣어줄 특징 컬럼 이름 목록
) -> dict:  # 각 모델·앙상블의 시험 성적을 담은 묶음을 돌려줌
    """test.csv 1회 최종 평가. K-Fold 중 절대 사용 안 함."""
    X = df_test[feature_cols]  # 시험 데이터에서 특징 표만 꺼냄
    y = df_test["label"]  # 시험 데이터에서 정답만 꺼냄
    results: dict[str, dict] = {}  # 각 모델의 시험 성적을 담아둘 빈 묶음
    for name, model in models.items():  # 각 선생님 모델을 하나씩 꺼내 시험 평가 수행
        pred = model.predict(X)  # 시험 데이터의 승패를 예측
        prob = model.predict_proba(X)[:, 1]  # 팀A가 이길 확률을 0~1 숫자로 출력
        results[name] = dict(  # 이 선생님의 시험 성적표 작성
            accuracy=float(accuracy_score(y, pred)),  # 정확도: 맞힌 비율
            f1=float(f1_score(y, pred, average="macro")),  # F1 점수: 이기는 팀과 지는 팀 모두 공평하게 평가한 점수
            roc_auc=float(roc_auc_score(y, prob)),  # AUC: 모델이 승리팀을 맞힐 확률을 0~1로 나타낸 점수 (1에 가까울수록 훌륭)
        )
    ens_prob = ensemble_predict_proba(models, X)  # 세 선생님의 예측 확률을 평균 낸 앙상블 최종 확률
    ens_pred = (ens_prob >= 0.5).astype(int)  # 앙상블 확률이 50% 이상이면 팀A 승리(1), 미만이면 팀B 승리(0)
    results["ensemble"] = dict(  # 앙상블의 시험 성적표 작성
        accuracy=float(accuracy_score(y, ens_pred)),  # 앙상블 정확도
        f1=float(f1_score(y, ens_pred, average="macro")),  # 앙상블 F1 점수
        roc_auc=float(roc_auc_score(y, ens_prob)),  # 앙상블 AUC 점수
    )
    print("\n[Test 결과]")  # 시험 결과 요약 제목 출력
    for name, m in results.items():  # 각 모델·앙상블의 시험 성적을 차례로 출력
        print(f"  {name:10s} Acc={m['accuracy']:.4f}  F1={m['f1']:.4f}  AUC={m['roc_auc']:.4f}")  # 이름, 정확도, F1, AUC를 나란히 출력
    return results  # 시험 성적 묶음을 돌려줌


# ── 박빙(접전) 경기 서브셋 평가 ──────────────────────────────────────────────────

def close_match_evaluate(
    models: dict,
    df_test: pd.DataFrame,
    feature_cols: list[str],
    margin: int = 2,
) -> dict:
    """박빙(접전) 경기만 추려서 모델 성능을 평가한다.

    |score_a - score_b| <= margin 인 경기만 평가.
    margin=2 → 13-11, 13-12, OT(14-12, 15-13 등) 포함.
    박빙 경기는 예측이 어려우므로 전체 test보다 AUC가 낮게 나오는 것이 정상이다.
    """
    if "score_a" not in df_test.columns or "score_b" not in df_test.columns:
        print("[WARNING] score_a/score_b 컬럼 없음 — 박빙 평가 건너뜀")
        return {}

    mask = (df_test["score_a"] - df_test["score_b"]).abs() <= margin
    df_close = df_test[mask].copy()
    subset_size = len(df_close)

    if subset_size == 0:
        print(f"[WARNING] margin={margin} 박빙 경기 0건 — 박빙 평가 건너뜀")
        return {}

    total = len(df_test)
    print(f"\n[Close Match] margin={margin} | 서브셋 {subset_size}건 ({subset_size/total*100:.1f}% of test)")

    X = df_close[feature_cols]
    y = df_close["label"]
    results: dict = {"subset_size": subset_size}

    for name, model in models.items():
        pred = model.predict(X)
        prob = model.predict_proba(X)[:, 1]
        results[name] = dict(
            accuracy=float(accuracy_score(y, pred)),
            f1=float(f1_score(y, pred, average="macro")),
            roc_auc=float(roc_auc_score(y, prob)),
        )

    ens_prob = ensemble_predict_proba(models, X)
    ens_pred = (ens_prob >= 0.5).astype(int)
    results["ensemble"] = dict(
        accuracy=float(accuracy_score(y, ens_pred)),
        f1=float(f1_score(y, ens_pred, average="macro")),
        roc_auc=float(roc_auc_score(y, ens_prob)),
    )

    print("\n[박빙 경기 평가 결과]")
    for name, m in results.items():
        if name == "subset_size":
            continue
        print(f"  {name:10s} Acc={m['accuracy']:.4f}  F1={m['f1']:.4f}  AUC={m['roc_auc']:.4f}")

    return results


# ── SHAP 피처 중요도 ───────────────────────────────────────────────────────────

def compute_shap(
    model,  # SHAP 값을 계산할 트리 계열 선생님 모델 (랜덤 포레스트·XGBoost·LightGBM 중 하나)
    X: pd.DataFrame,  # SHAP 계산에 쓸 특징 데이터프레임
    model_name: str,  # 결과에 붙일 모델 이름 (예: "rf", "xgb", "lgbm")
    sample_size: int = 2000,  # 계산 속도를 위해 최대 몇 개의 경기만 쓸지 (기본 2000개)
) -> pd.Series:  # 특징별 평균 SHAP 점수가 높은 순으로 정렬된 목록을 돌려줌
    """TreeExplainer로 mean |SHAP| per feature 계산. sample_size로 속도 제한."""
    if len(X) > sample_size:  # 경기 수가 sample_size보다 많으면 무작위로 그만큼만 골라 씀 (시간 단축)
        X = X.sample(n=sample_size, random_state=42)  # 시드 42를 써서 항상 같은 경기를 고르도록 고정
    explainer = shap.TreeExplainer(model)  # 나무 계열 모델 전용 SHAP 계산기 생성 — 각 특징이 예측에 얼마나 기여했는지 분석하는 도구
    shap_vals = explainer.shap_values(X)  # 각 경기·특징에 대해 SHAP 기여도 점수 행렬 계산
    if isinstance(shap_vals, list):  # 이진 분류 랜덤 포레스트는 [팀B 기여도, 팀A 기여도] 두 개의 행렬 리스트를 돌려줌
        shap_vals = shap_vals[1]  # 팀A 승리(클래스1) 쪽의 기여도 행렬만 선택
    elif isinstance(shap_vals, np.ndarray) and shap_vals.ndim == 3:
        # newer SHAP: (n_samples, n_features, n_classes) — pick positive class
        shap_vals = shap_vals[:, :, 1]  # 3차원 배열이면 팀A 승리 축만 뽑음 (최신 SHAP 버전 대응)
    mean_abs = np.abs(shap_vals).mean(axis=0)  # 각 특징의 기여도 절댓값 평균 — 양수·음수 방향 관계없이 "얼마나 중요한가"만 측정
    return pd.Series(mean_abs, index=X.columns, name=f"{model_name}_shap").sort_values(ascending=False)  # 특징 이름을 붙여 중요한 순서대로 정렬한 목록 돌려줌


# ── 리포트 저장 ───────────────────────────────────────────────────────────────

def save_reports(
    kfold_metrics: dict,  # kfold_evaluate()가 돌려준 교차검증 평균·표준편차 성적 묶음
    test_metrics: dict,  # test_evaluate()가 돌려준 시험 성적 묶음
    shap_series: dict[str, pd.Series],  # 모델별 SHAP 중요도 목록 묶음
    reports_dir: str,  # 리포트 파일을 저장할 폴더 경로
    close_metrics: dict | None = None,  # close_match_evaluate()가 돌려준 박빙 경기 성적 (없으면 None)
) -> None:  # 파일만 저장하고 아무것도 돌려주지 않음
    Path(reports_dir).mkdir(parents=True, exist_ok=True)  # 리포트 폴더가 없으면 새로 만듦

    # eval_summary.json: kfold + test + close_match 통합
    summary: dict = {}  # 교차검증 결과와 시험 결과를 하나로 합칠 묶음
    for name in kfold_metrics:  # 교차검증 결과를 summary에 복사
        summary[name] = {**kfold_metrics[name]}  # 각 모델의 교차검증 성적을 그대로 복사
    summary["test"] = test_metrics  # 시험 결과를 별도 항목으로 추가
    if close_metrics:
        summary["close_match"] = close_metrics  # 박빙 경기 평가 결과를 별도 항목으로 추가
    # ensemble의 kfold mean/std도 최상위에 노출 (AC-6 요구사항)
    for key in ("accuracy_mean", "f1_mean", "roc_auc_mean"):  # 앙상블 교차검증 평균 성적을 최상위에 노출
        summary["ensemble"][key] = kfold_metrics["ensemble"][key]  # 앙상블 교차검증 평균 성적 반영

    with open(Path(reports_dir) / "eval_summary.json", "w", encoding="utf-8") as f:  # eval_summary.json 파일을 쓰기 모드로 열기
        json.dump(summary, f, indent=2, ensure_ascii=False)  # 들여쓰기 2칸, 한글이 깨지지 않게 그대로 저장

    # shap_importance.csv: feature × 모델별 shap (43행)
    shap_df = pd.DataFrame({"feature": FEATURE_COLS})  # 43개 특징 이름을 첫 번째 열로 하는 표 생성
    for model_name, series in shap_series.items():  # 각 모델의 SHAP 점수 목록을 열로 추가
        col = f"{model_name}_shap"  # 열 이름: "{모델명}_shap" 형식 (예: "rf_shap")
        shap_df[col] = shap_df["feature"].map(series).fillna(0.0)  # 특징 이름으로 SHAP 점수를 매핑, 없는 특징은 0점으로 채움
    shap_df.to_csv(Path(reports_dir) / "shap_importance.csv", index=False)  # 행 번호(인덱스) 제외하고 CSV 파일로 저장

    print(f"\n[INFO] 리포트 저장 완료 → {reports_dir}/")  # 저장이 끝났다고 화면에 알림


# ── 메인 ──────────────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> None:  # 터미널에서 받은 옵션들을 보고 전체 평가 과정을 순서대로 실행하는 함수
    print("[Evaluate] 모델 로드 중...")  # 평가 시작 단계를 화면에 알림
    models = load_models(args.models)  # 지정된 폴더에서 세 선생님 모델 파일 불러오기

    base = Path(args.input)  # 전처리 데이터가 있는 폴더 경로를 다루기 쉬운 객체로 바꿈
    df_train = pd.read_csv(base / "train.csv", low_memory=False)  # 교차검증에 쓸 훈련 데이터 읽기 (메모리를 절약하며 읽음)
    df_test  = pd.read_csv(base / "test.csv",  low_memory=False)  # 최종 시험에 쓸 데이터 읽기

    print("\n[Evaluate] GroupKFold(5) 교차검증 중...")  # 교차검증 시작을 화면에 알림
    kfold_metrics = kfold_evaluate(models, df_train, FEATURE_COLS)  # 훈련 데이터를 5조각으로 나눠 교차검증 실행

    # K-Fold deepcopy가 원본을 변경하지 않지만, 명시적으로 reload하여 저장된 artifact와 일치시킴
    print("\n[Evaluate] Test 최종 평가 중 (저장 모델 재로드)...")  # 시험 평가 시작을 화면에 알림
    models = load_models(args.models)  # 저장된 원본 선생님 모델을 다시 불러와 시험 평가에 씀 (교차검증 중 변형된 복사본이 아닌 원본 사용)
    test_metrics = test_evaluate(models, df_test, FEATURE_COLS)  # 시험 데이터로 딱 한 번만 최종 성적 확인

    # 박빙(접전) 경기 서브셋 평가
    print(f"\n[Evaluate] 박빙(접전) 경기 평가 중 (margin={args.close_margin})...")
    close_metrics = close_match_evaluate(models, df_test, FEATURE_COLS, margin=args.close_margin)

    # SHAP 실패 시 메트릭 손실 방지 — 선저장
    Path(args.reports).mkdir(parents=True, exist_ok=True)  # 리포트 폴더가 없으면 새로 만듦
    _summary: dict = {name: {**kfold_metrics[name]} for name in kfold_metrics}  # 교차검증 결과를 임시 묶음에 복사
    _summary["test"] = test_metrics  # 시험 결과를 임시 묶음에 추가
    if close_metrics:
        _summary["close_match"] = close_metrics  # 박빙 평가 결과 선저장
    for key in ("accuracy_mean", "f1_mean", "roc_auc_mean"):  # 앙상블 교차검증 평균 성적 최상위 노출
        _summary["ensemble"][key] = kfold_metrics["ensemble"][key]  # 앙상블 교차검증 평균 성적 반영
    with open(Path(args.reports) / "eval_summary.json", "w", encoding="utf-8") as f:  # SHAP 계산 전에 먼저 성적 파일을 저장 (SHAP 계산이 실패해도 성적은 보존됨)
        json.dump(_summary, f, indent=2, ensure_ascii=False)  # 들여쓰기 2칸, 한글이 깨지지 않게 저장
    print("[INFO] eval_summary.json 선저장 완료")  # 먼저 저장 완료를 화면에 알림

    print("\n[Evaluate] SHAP 피처 중요도 계산 중...")  # SHAP 계산 시작을 화면에 알림
    X_train = df_train[FEATURE_COLS]  # SHAP 계산에 쓸 훈련 데이터 특징 표 꺼내기
    shap_series: dict[str, pd.Series] = {}  # 모델별 SHAP 점수 목록을 담아둘 빈 묶음
    for name, model in models.items():  # 각 선생님 모델에 대해 SHAP 계산 실행
        print(f"  SHAP: {name}...")  # 지금 어떤 선생님의 SHAP를 계산 중인지 출력
        shap_series[name] = compute_shap(model, X_train, name, sample_size=args.shap_samples)  # 지정된 샘플 수로 SHAP 기여도 점수 계산

    save_reports(kfold_metrics, test_metrics, shap_series, args.reports, close_metrics)  # 교차검증·시험·SHAP·박빙 결과를 파일로 저장
    print("\n[INFO] 완료 ✅")  # 모든 평가 과정이 끝났다고 화면에 알림


def main() -> None:  # 터미널에서 이 파일을 실행할 때 가장 먼저 호출되는 함수
    parser = argparse.ArgumentParser(description="ValoPredictML 모델 평가")  # 터미널 옵션 안내 설명 파서 생성
    parser.add_argument("--input",        required=True, help="data/processed/ 디렉토리")  # 전처리 데이터 폴더 경로 (반드시 넣어야 함)
    parser.add_argument("--models",       required=True, help="models/ 디렉토리")  # 모델 파일 폴더 경로 (반드시 넣어야 함)
    parser.add_argument("--reports",      required=True, help="reports/ 디렉토리")  # 리포트 저장 폴더 경로 (반드시 넣어야 함)
    parser.add_argument("--shap-samples", type=int, default=2000, dest="shap_samples",
                        help="SHAP 계산 샘플 수 (기본 2000)")  # SHAP 계산에 쓸 최대 경기 수 (선택, 기본 2000)
    parser.add_argument("--close-margin", type=int, default=2, dest="close_margin",
                        help="|score_a - score_b| <= N 인 박빙 경기 기준 (기본 2)")  # 박빙 경기 판정 임계값
    args = parser.parse_args()  # 터미널에서 입력한 옵션들을 읽어서 변수에 담음
    run(args)  # 읽어온 옵션으로 전체 평가 파이프라인 실행


if __name__ == "__main__":  # 이 파일을 직접 실행할 때만 아래 코드가 동작함 (다른 파일에서 불러쓸 때는 동작 안 함)
    main()  # 터미널 옵션 읽기 → 전체 평가 실행
