"""ml/validate_metrics.py — 성과 지표 검증 + ML 개념 분석 스크립트.

US-1.1  baseline_comparison.json  — random/majority baseline 대비 ensemble 개선폭
US-1.2  generalization_check.json — K-Fold vs Test gap (과적합 탐지)
US-1.3  roc_curve.png             — 4모델 ROC Curve + random diagonal (--roc-curve)
US-1.4  metric_analysis.json      — F1 vs Accuracy, imbalance_ratio
US-2.3  shap_analysis.json        — SHAP RF-XGB Spearman r, 도메인 해석 (--shap-analysis)
"""
from __future__ import annotations  # 파이썬이 오래된 버전이어도 최신 방식으로 타입을 적을 수 있게 해줌

import argparse  # 터미널에서 '--input 폴더명' 처럼 옵션을 받아오는 도구
import json  # 분석 결과를 메모장(JSON 파일)에 저장할 때 쓰는 도구
from pathlib import Path  # 파일 경로를 다루기 편하게 해주는 도구

import numpy as np  # ROC 커브를 그릴 때 세 선생님의 확률을 평균 내기 위해 쓰는 도구
import pandas as pd  # SHAP 표와 시험 데이터를 데이터프레임으로 다루는 도구
from scipy.stats import spearmanr  # 두 선생님의 SHAP 중요도 순서가 얼마나 비슷한지 점수로 계산하는 도구
from sklearn.metrics import roc_curve, auc  # ROC 커브의 좌표를 계산하고 곡선 아래 면적(AUC)을 구하는 함수

from ml.data_pipeline import FEATURE_COLS_P1, FEATURE_COLS_P2  # 전처리 단계에서 만들어 둔 특징 컬럼 목록 가져오기

FEATURE_COLS: list[str] = FEATURE_COLS_P1 + FEATURE_COLS_P2  # 1단계와 2단계에서 만든 특징 목록을 합쳐서 하나의 큰 목록으로 만듦 (총 43개)

_DOMAIN_MAP: dict[str, str] = {  # 특징 이름의 키워드 → 발로란트 게임 맥락 설명 매핑표 (SHAP 분석 결과를 사람이 이해하기 쉽게 해설하기 위해)
    "avg_assists":   "어시스트(assists)는 팀 플레이 기여도 지표 → 높을수록 협력 전투력 강함",  # 어시스트 특징 설명
    "fk_fd_ratio":   "선빵/선죽 비율(FK/FD ratio) → 선제 교전 우위; 높을수록 라운드 이니셔티브 확보",  # 선제 킬/데스 비율 특징 설명
    "avg_agent_exp": "요원 숙련도(agent experience) → 해당 요원 플레이 경험; 높을수록 역할 완성도 높음",  # 요원 경험치 특징 설명
    "avg_kills":     "평균 킬 수 → 팀 전투력 직접 지표",  # 평균 킬 특징 설명
    "avg_deaths":    "평균 데스 수 → 낮을수록 생존력·팀 자원 보전 우수",  # 평균 데스 특징 설명
    "avg_acs":       "ACS(Average Combat Score) → 라운드당 종합 전투 기여도 지표",  # ACS 특징 설명
    "initiator":     "Initiator(척후대)는 정보전·진입 지원 핵심 → 승리 기여도 높음",  # 척후대 역할 특징 설명
    "controller":    "Controller(전략가)는 스모크/장벽으로 구역 통제 → 팀 안정성 제공",  # 전략가 역할 특징 설명
    "duelist":       "Duelist(타격대)는 킬 생성 역할 → 공격 조합의 핵심",  # 타격대 역할 특징 설명
    "sentinel":      "Sentinel(감시자)는 수비·정찰 → 방어 안정성 기여",  # 감시자 역할 특징 설명
    "map":           "맵에 따라 역할 메타가 달라짐 → map_encoded가 역할 조합 해석에 필수",  # 맵 특징 설명
}

# eval_summary.json / shap_importance.csv 탐색 후보
_FALLBACK_REPORTS = Path("/tmp/valo_reports")  # 지정한 폴더에 파일이 없을 때 대신 찾아볼 임시 폴더
_FALLBACK_MODELS = [Path("/tmp/valo_models_opt"), Path("/tmp/valo_models"), Path("models")]  # 모델 폴더를 자동으로 찾을 때 차례로 시도할 후보 경로 목록


def _load_json(reports_dir: Path, filename: str) -> dict:  # 리포트 폴더에서 JSON 파일을 읽는 함수 (파일이 없으면 대안 폴더도 찾아봄)
    candidates = [reports_dir / filename, _FALLBACK_REPORTS / filename]  # 주 경로와 대안 경로를 순서대로 시도
    for i, p in enumerate(candidates):  # 후보 경로를 하나씩 꺼내 파일이 있는지 확인
        if p.exists():  # 파일이 있으면 읽기
            if i > 0:  # 대안 경로를 사용하는 경우 "이 폴더에 없어서 다른 곳에서 찾았어요"라고 경고
                print(f"[WARN] {filename}: {reports_dir}에 없음, fallback 사용 → {p}")  # 대안 경로 사용 경고 출력
            with open(p, encoding="utf-8") as f:  # UTF-8 인코딩으로 파일 열기 (한글이 깨지지 않게)
                return json.load(f)  # JSON 파일을 파이썬 딕셔너리로 변환해 돌려줌
    raise FileNotFoundError(
        f"{filename} 없음. 탐색 위치: {[str(c) for c in candidates]}"
    )  # 모든 후보에서 파일을 못 찾으면 "여기 여기 다 찾아봤는데 없어요!"라고 알려주며 멈춤


def _load_shap_csv(reports_dir: Path) -> pd.DataFrame:  # SHAP 중요도 CSV 파일을 읽는 함수 (파일이 없으면 대안 폴더도 찾아봄)
    candidates = [reports_dir / "shap_importance.csv", _FALLBACK_REPORTS / "shap_importance.csv"]  # 주 경로와 대안 경로를 순서대로 시도
    for i, p in enumerate(candidates):  # 후보 경로를 하나씩 꺼내 파일이 있는지 확인
        if p.exists():  # 파일이 있으면 읽기
            if i > 0:  # 대안 경로를 사용하는 경우 경고 출력
                print(f"[WARN] shap_importance.csv: {reports_dir}에 없음, fallback 사용 → {p}")  # 대안 경로 사용 경고 출력
            return pd.read_csv(p)  # SHAP 중요도 CSV를 데이터프레임으로 읽어 돌려줌
    raise FileNotFoundError(f"shap_importance.csv 없음. 탐색: {candidates}")  # 모든 후보에서 파일을 못 찾으면 예외 발생


def _find_models_dir(models_hint: str | None) -> Path:  # 모델 파일들이 있는 폴더를 옵션 또는 자동 탐색으로 찾아주는 함수
    if models_hint:  # 터미널에서 --models 옵션으로 경로를 알려줬다면 그 경로 우선 사용
        p = Path(models_hint)  # 알려준 경로를 다루기 쉬운 객체로 바꿈
        if p.exists():  # 그 경로가 실제로 있으면 바로 돌려줌
            return p  # 유효한 모델 폴더 경로 돌려줌
    for p in _FALLBACK_MODELS:  # --models 옵션이 없거나 경로가 없으면 후보 경로를 차례로 탐색
        if p.exists() and (p / "rf_model.joblib").exists():  # 폴더도 있고 랜덤 포레스트 모델 파일도 있으면 올바른 폴더로 판단
            return p  # 유효한 모델 폴더 경로 돌려줌
    raise FileNotFoundError("모델 디렉토리를 찾을 수 없습니다. --models 옵션으로 지정하세요.")  # 어디에도 모델이 없으면 "직접 알려주세요!"라고 하며 멈춤


# ── US-1.1 Baseline 비교 ──────────────────────────────────────────────────────

def baseline_compare(df_test: pd.DataFrame, eval_summary: dict, reports_dir: Path) -> dict:  # 무작위 예측·다수 클래스 예측 대비 앙상블이 얼마나 더 잘 맞히는지 비교하는 함수
    majority_label = int(df_test["label"].mode()[0])  # 시험 데이터에서 가장 많이 등장하는 정답 레이블 (다수 클래스)
    majority_acc = float((df_test["label"] == majority_label).mean())  # 항상 다수 클래스만 찍을 때의 정확도 — 예를 들어 팀A가 항상 이기면 항상 팀A 승리라고 예측하는 것
    random_acc = 0.5  # 동전 던지기처럼 무작위로 예측할 때의 기대 정확도 (이진 분류는 50%)

    ensemble_test_acc = eval_summary["test"]["ensemble"]["accuracy"]  # 앙상블 선생님들이 시험에서 받은 정확도
    improvement = ensemble_test_acc - majority_acc  # 앙상블이 항상 다수 클래스만 찍는 것보다 얼마나 더 잘 맞히는지 차이

    result = {  # 비교 결과를 담은 묶음
        "random_acc": random_acc,  # 동전 던지기 수준의 정확도 (0.5)
        "majority_acc": majority_acc,  # 항상 많은 쪽 팀이 이긴다고 찍는 수준의 정확도
        "majority_label": majority_label,  # 더 자주 이기는 쪽 팀의 레이블 값
        "ensemble_test_acc": ensemble_test_acc,  # 앙상블이 실제로 받은 시험 정확도
        "improvement_over_majority": improvement,  # 다수 클래스 찍기 대비 개선된 정확도 (소수점 형태)
        "improvement_over_majority_pct": round(improvement * 100, 2),  # 개선폭을 퍼센트로 표현 (예: 29.13)
    }
    with open(reports_dir / "baseline_comparison.json", "w", encoding="utf-8") as f:  # 비교 결과 파일을 쓰기 모드로 열기
        json.dump(result, f, indent=2, ensure_ascii=False)  # 들여쓰기 2칸, 한글이 깨지지 않게 그대로 저장

    print(f"[Baseline] random={random_acc:.4f}  majority={majority_acc:.4f}  "
          f"ensemble={ensemble_test_acc:.4f}")  # 세 가지 기준 정확도를 나란히 출력
    print(f"  → Ensemble은 다수 클래스 기준 대비 +{improvement * 100:.1f}%p")  # 앙상블이 얼마나 더 잘하는지 강조 출력
    return result  # 비교 결과 묶음을 돌려줌


# ── US-1.2 K-Fold vs Test 일관성 ─────────────────────────────────────────────

def generalization_check(eval_summary: dict, reports_dir: Path) -> dict:  # 교차검증 성적과 시험 성적의 차이가 크면 "외운 것 아니냐"고 경고하는 함수
    kfold_acc = eval_summary["ensemble"]["accuracy_mean"]  # 교차검증에서 앙상블이 받은 평균 정확도
    test_acc = eval_summary["test"]["ensemble"]["accuracy"]  # 최종 시험에서 앙상블이 받은 정확도
    gap = abs(kfold_acc - test_acc)  # 교차검증과 시험 정확도의 차이 (절댓값)
    overfitting_flag = gap >= 0.03  # 차이가 3% 이상이면 "혹시 훈련 데이터를 외운 거 아닐까?" 경고 깃발 세움

    result = {  # 일관성 검사 결과를 담은 묶음
        "kfold_acc_mean": kfold_acc,  # 교차검증 평균 정확도
        "test_acc": test_acc,  # 시험 정확도
        "gap": gap,  # 교차검증과 시험 정확도의 차이
        "overfitting_flag": overfitting_flag,  # 과적합(외우기) 가능성 여부 (True=위험, False=안전)
        "verdict": "PASS — 과적합 없음" if not overfitting_flag else f"WARN — gap={gap:.4f} ≥ 0.03",  # 결론: 안전하거나 경고
    }
    with open(reports_dir / "generalization_check.json", "w", encoding="utf-8") as f:  # 일관성 검사 결과 파일을 쓰기 모드로 열기
        json.dump(result, f, indent=2, ensure_ascii=False)  # 들여쓰기 2칸, 한글이 깨지지 않게 저장

    status = "PASS (과적합 없음)" if not overfitting_flag else "WARN (과적합 가능성)"  # 화면 출력용 상태 문자열
    print(f"[Generalization] K-Fold Acc={kfold_acc:.4f}  Test Acc={test_acc:.4f}  "
          f"gap={gap:.4f} → {status}")  # 교차검증·시험 정확도와 차이, 최종 결론 출력
    return result  # 일관성 검사 결과 묶음을 돌려줌


# ── US-1.3 ROC Curve 시각화 ───────────────────────────────────────────────────

def roc_curve_plot(models_dir: Path, df_test: pd.DataFrame, reports_dir: Path) -> None:  # 세 선생님과 앙상블의 ROC 커브를 그림 파일로 저장하는 함수
    try:
        import matplotlib  # 그래프를 그리는 도구 (설치 안 돼있으면 그냥 건너뜀)
        matplotlib.use("Agg")  # 화면(모니터)이 없는 서버 환경에서도 파일로 저장할 수 있도록 백엔드 설정
        import matplotlib.pyplot as plt  # 실제 그래프를 그리는 함수 모음
    except ImportError:  # matplotlib가 설치 안 된 경우 건너뜀
        print("[ROC] matplotlib 미설치 — roc_curve.png 스킵")  # 건너뛴다고 화면에 알림
        return  # 이 함수를 여기서 끝냄

    import joblib  # 모델 파일을 불러오기 위해 여기서 가져옴 (필요할 때만 불러오는 방식)
    models = {  # 세 선생님 모델 파일을 읽어서 이름표를 달아 묶음으로 구성
        "RF":       joblib.load(models_dir / "rf_model.joblib"),  # 랜덤 포레스트 선생님 불러오기
        "XGBoost":  joblib.load(models_dir / "xgboost_model.joblib"),  # XGBoost 선생님 불러오기
        "LightGBM": joblib.load(models_dir / "lgbm_model.joblib"),  # LightGBM 선생님 불러오기
    }
    X = df_test[FEATURE_COLS]  # 시험 데이터에서 특징 표만 꺼냄
    y = df_test["label"]  # 시험 데이터에서 정답만 꺼냄

    fig, ax = plt.subplots(figsize=(8, 6))  # 가로 8인치·세로 6인치 크기의 그래프 틀 생성
    probs: dict[str, np.ndarray] = {}  # 앙상블 계산을 위해 각 선생님의 예측 확률을 담아둘 빈 묶음
    for name, model in models.items():  # 각 선생님 모델의 ROC 커브를 차례로 그림
        prob = model.predict_proba(X)[:, 1]  # 팀A가 이길 확률을 0~1 숫자로 출력
        probs[name] = prob  # 앙상블 계산을 위해 이 확률을 저장해둠
        fpr, tpr, _ = roc_curve(y, prob)  # ROC 커브의 x축(틀린 양성 비율)·y축(맞힌 양성 비율) 좌표 계산
        auc_val = auc(fpr, tpr)  # ROC 커브 아래 면적(AUC) 계산 — 1에 가까울수록 훌륭한 모델
        ax.plot(fpr, tpr, label=f"{name} (AUC={auc_val:.3f})")  # 이 선생님의 ROC 커브를 AUC 점수와 함께 범례에 추가

    ens_prob = np.mean(list(probs.values()), axis=0)  # 세 선생님의 예측 확률을 평균 내서 앙상블 확률 계산
    fpr, tpr, _ = roc_curve(y, ens_prob)  # 앙상블 ROC 커브 좌표 계산
    auc_val = auc(fpr, tpr)  # 앙상블 AUC 계산
    ax.plot(fpr, tpr, label=f"Ensemble (AUC={auc_val:.3f})", linewidth=2.5, linestyle="--")  # 앙상블 ROC 커브를 굵은 점선으로 눈에 띄게 강조

    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Random (AUC=0.500)")  # 동전 던지기 수준(대각선)을 비교 기준선으로 추가
    ax.set_xlabel("False Positive Rate")  # x축 레이블: 실제로 진 팀을 이겼다고 잘못 예측한 비율
    ax.set_ylabel("True Positive Rate")  # y축 레이블: 실제로 이긴 팀을 맞게 예측한 비율
    ax.set_title("ROC Curves — Valorant Win Prediction")  # 그래프 제목 설정
    ax.legend(loc="lower right")  # 범례를 오른쪽 아래에 배치
    ax.grid(True, alpha=0.3)  # 30% 투명도의 격자선 추가 (읽기 편하게)
    fig.tight_layout()  # 여백을 자동으로 조정해서 잘리는 부분 없게 함
    fig.savefig(reports_dir / "roc_curve.png", dpi=150)  # 150dpi 해상도로 PNG 파일 저장 (선명한 그림)
    plt.close(fig)  # 그래프 객체를 닫아서 메모리를 해방함 (안 닫으면 메모리 낭비)
    print(f"[ROC] roc_curve.png 저장 완료")  # 그림 저장이 끝났다고 화면에 알림


# ── US-1.4 F1 vs Accuracy 분리 분석 ──────────────────────────────────────────

def metric_analysis(df_test: pd.DataFrame, eval_summary: dict, reports_dir: Path) -> dict:  # 정확도와 F1 점수의 차이를 분석하고 팀A·팀B 경기 수가 얼마나 고른지 확인하는 함수
    test_acc = eval_summary["test"]["ensemble"]["accuracy"]  # 앙상블의 시험 정확도
    test_f1 = eval_summary["test"]["ensemble"]["f1"]  # 앙상블의 시험 F1 점수
    diff = test_acc - test_f1  # 정확도 - F1 차이 (차이가 크면 팀A·팀B 경기 수가 많이 치우쳐 있다는 신호)

    counts = df_test["label"].value_counts()  # 시험 데이터에서 팀A 승리(1)와 팀B 승리(0)가 각각 몇 개인지 세기
    majority_count = int(counts.max())  # 더 많이 등장하는 쪽의 경기 수
    minority_count = int(counts.min())  # 더 적게 등장하는 쪽의 경기 수
    imbalance_ratio = round(majority_count / minority_count, 4)  # 많은 쪽 ÷ 적은 쪽 비율 (1에 가까울수록 공평하게 균형 잡힌 것)

    result = {  # 지표 분석 결과를 담은 묶음
        "test_acc": test_acc,  # 시험 정확도
        "test_f1": test_f1,  # 시험 F1 점수
        "test_f1_diff": diff,  # 정확도와 F1의 차이
        "imbalance_ratio": imbalance_ratio,  # 팀A·팀B 경기 수 불균형 비율
        "label_distribution": {int(k): int(v) for k, v in counts.items()},  # 팀A 승리·팀B 승리 경기 수 분포 (키를 정수로 변환)
        "note": (
            "F1 macro는 소수 클래스에 동등 가중치를 부여, "
            "test 불균형 환경에서 정확한 평가"
        ),  # F1 macro를 쓰는 이유: 경기 수가 치우쳐 있어도 양쪽을 공평하게 평가할 수 있음
    }
    with open(reports_dir / "metric_analysis.json", "w", encoding="utf-8") as f:  # 지표 분석 결과 파일을 쓰기 모드로 열기
        json.dump(result, f, indent=2, ensure_ascii=False)  # 들여쓰기 2칸, 한글이 깨지지 않게 저장

    print(f"[MetricAnalysis] Acc={test_acc:.4f}  F1={test_f1:.4f}  "
          f"diff={diff:.4f}  imbalance_ratio={imbalance_ratio:.2f}")  # 정확도·F1·차이·불균형 비율을 나란히 출력
    return result  # 지표 분석 결과 묶음을 돌려줌


# ── US-2.3 SHAP 상관관계 분석 ─────────────────────────────────────────────────

def shap_analysis(shap_df: pd.DataFrame, reports_dir: Path) -> dict:  # 세 선생님이 중요하게 본 특징의 순서가 서로 얼마나 비슷한지 비교하고, 상위 특징을 게임 관점에서 해설하는 함수
    rf_shap = shap_df["rf_shap"]  # 랜덤 포레스트 선생님의 특징별 SHAP 중요도 점수 열
    xgb_shap = shap_df["xgb_shap"]  # XGBoost 선생님의 특징별 SHAP 중요도 점수 열
    lgbm_shap = shap_df["lgbm_shap"]  # LightGBM 선생님의 특징별 SHAP 중요도 점수 열

    r_rf_xgb, p_rf_xgb   = spearmanr(rf_shap, xgb_shap)  # 랜덤 포레스트와 XGBoost의 SHAP 중요도 순위가 얼마나 비슷한지 점수와 신뢰도 계산
    r_rf_lgbm, _          = spearmanr(rf_shap, lgbm_shap)  # 랜덤 포레스트와 LightGBM의 SHAP 중요도 순위 유사도 계산 (신뢰도 값은 사용 안 함)
    r_xgb_lgbm, _         = spearmanr(xgb_shap, lgbm_shap)  # XGBoost와 LightGBM의 SHAP 중요도 순위 유사도 계산

    top5 = (
        shap_df.nlargest(5, "xgb_shap")[["feature", "xgb_shap"]]  # XGBoost가 가장 중요하게 본 특징 상위 5개 선택
        .rename(columns={"xgb_shap": "shap_value"})  # 열 이름을 "shap_value"로 변경
        .to_dict("records")  # 각 행을 {"feature": ..., "shap_value": ...} 딕셔너리로 변환한 목록 생성
    )

    notes = []  # 상위 5개 특징 각각에 대한 게임 맥락 설명을 담아둘 빈 목록
    for rec in top5:  # 상위 5개 특징을 하나씩 꺼내 게임 설명 추가
        feat = rec["feature"]  # 특징 이름 꺼내기
        for key, desc in _DOMAIN_MAP.items():  # 설명표의 키워드를 특징 이름에서 찾음
            if key in feat:  # 특징 이름 안에 키워드가 포함되어 있으면 해당 설명 사용
                notes.append(f"{feat}: {desc}")  # "특징이름: 게임 설명" 형식으로 목록에 추가
                break  # 첫 번째로 일치하는 키워드 하나로만 설명 결정하고 다음 특징으로 넘어감
        else:
            notes.append(f"{feat}: 역할 조합 균형 지표")  # 설명표에서 키워드를 못 찾으면 일반적인 설명 추가

    result = {  # SHAP 분석 결과를 담은 묶음
        "top5_features_xgb": top5,  # XGBoost 기준으로 가장 중요한 특징 상위 5개와 점수
        "rf_xgb_spearman_r": float(r_rf_xgb),  # 랜덤 포레스트와 XGBoost의 중요도 순위 유사도 (1이면 완전 동일, 0이면 무관)
        "rf_xgb_spearman_p": float(p_rf_xgb),  # 위 유사도의 통계 신뢰도 (0.05 미만이면 믿을 만함)
        "rf_lgbm_spearman_r": float(r_rf_lgbm),  # 랜덤 포레스트와 LightGBM의 중요도 순위 유사도
        "xgb_lgbm_spearman_r": float(r_xgb_lgbm),  # XGBoost와 LightGBM의 중요도 순위 유사도
        "consistency_verdict": (  # 세 선생님이 비슷한 특징을 중요하게 보는지에 대한 결론
            f"높음 (r={r_rf_xgb:.3f} > 0.7)" if r_rf_xgb > 0.7  # 유사도가 0.7 초과면 "세 선생님이 비슷하게 봄"
            else f"중간 (r={r_rf_xgb:.3f})"  # 0.7 이하면 "어느 정도 비슷하게 봄"
        ),
        "domain_alignment_notes": notes,  # 상위 특징별 발로란트 게임 맥락 해설 목록
    }
    with open(reports_dir / "shap_analysis.json", "w", encoding="utf-8") as f:  # SHAP 분석 결과 파일을 쓰기 모드로 열기
        json.dump(result, f, indent=2, ensure_ascii=False)  # 들여쓰기 2칸, 한글이 깨지지 않게 저장

    print(f"[SHAP] RF-XGB Spearman r={r_rf_xgb:.3f}  RF-LGBM r={r_rf_lgbm:.3f}  "
          f"XGB-LGBM r={r_xgb_lgbm:.3f}")  # 선생님 쌍별 중요도 순위 유사도를 나란히 출력
    print(f"  Top5 (XGB): {[r['feature'] for r in top5]}")  # XGBoost 기준 가장 중요한 특징 이름 5개 출력
    return result  # SHAP 분석 결과 묶음을 돌려줌


# ── 메인 ──────────────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> None:  # 터미널에서 받은 옵션들을 보고 전체 검증 과정을 순서대로 실행하는 함수
    rpt = Path(args.reports)  # 리포트를 저장할 폴더 경로를 다루기 쉬운 객체로 바꿈
    rpt.mkdir(parents=True, exist_ok=True)  # 리포트 폴더가 없으면 새로 만듦

    df_test = pd.read_csv(Path(args.input) / "test.csv", low_memory=False)  # 최종 시험 데이터 읽기
    eval_summary = _load_json(rpt, "eval_summary.json")  # 이전 단계에서 저장해 둔 성적 결과 파일 불러오기 (없으면 대안 폴더 탐색)

    print("\n[Validate] US-1.1 Baseline 비교...")  # US-1.1 분석 시작 알림
    baseline_compare(df_test, eval_summary, rpt)  # 동전 던지기·다수 클래스 찍기 대비 앙상블 개선폭 계산

    print("\n[Validate] US-1.2 K-Fold vs Test 일관성...")  # US-1.2 분석 시작 알림
    generalization_check(eval_summary, rpt)  # 교차검증과 시험 성적의 차이로 "외우기(과적합)" 여부 탐지

    print("\n[Validate] US-1.4 F1 vs Accuracy 분리 분석...")  # US-1.4 분석 시작 알림
    metric_analysis(df_test, eval_summary, rpt)  # 정확도와 F1 점수의 차이, 팀A·팀B 경기 수 균형 분석

    if args.roc_curve:  # 터미널에서 --roc-curve 옵션을 붙인 경우에만 ROC 커브 그림 생성
        print("\n[Validate] US-1.3 ROC Curve 시각화...")  # US-1.3 시각화 시작 알림
        models_dir = _find_models_dir(args.models)  # 모델 파일들이 있는 폴더 자동 탐색
        roc_curve_plot(models_dir, df_test, rpt)  # ROC 커브 그림 생성 및 PNG 파일 저장

    if args.shap_analysis:  # 터미널에서 --shap-analysis 옵션을 붙인 경우에만 SHAP 상관관계 분석 실행
        print("\n[Validate] US-2.3 SHAP 상관관계 분석...")  # US-2.3 분석 시작 알림
        shap_df = _load_shap_csv(rpt)  # SHAP 중요도 CSV 파일 불러오기 (없으면 대안 폴더 탐색)
        shap_analysis(shap_df, rpt)  # 선생님 간 SHAP 중요도 순위 유사도와 상위 특징 게임 해설 계산

    print("\n[INFO] 완료 ✅")  # 모든 검증 과정이 끝났다고 화면에 알림


def main() -> None:  # 터미널에서 이 파일을 실행할 때 가장 먼저 호출되는 함수
    parser = argparse.ArgumentParser(description="ValoPredictML 성과 지표 검증")  # 터미널 옵션 안내 설명 파서 생성
    parser.add_argument("--input",         required=True, help="data/processed/ 디렉토리")  # 전처리 데이터 폴더 경로 (반드시 넣어야 함)
    parser.add_argument("--reports",       required=True, help="reports/ 디렉토리 (출력)")  # 리포트 저장 폴더 경로 (반드시 넣어야 함)
    parser.add_argument("--models",        default=None,  help="models/ 디렉토리 (ROC curve용)")  # 모델 폴더 경로 (ROC 커브를 그릴 때만 필요, 선택)
    parser.add_argument("--roc-curve",     action="store_true", dest="roc_curve",
                        help="ROC Curve PNG 생성")  # 이 옵션을 붙이면 ROC 커브 그림을 만들어 저장함 (선택)
    parser.add_argument("--shap-analysis", action="store_true", dest="shap_analysis",
                        help="SHAP Spearman 상관관계 분석")  # 이 옵션을 붙이면 SHAP 상관관계 분석을 실행함 (선택)
    args = parser.parse_args()  # 터미널에서 입력한 옵션들을 읽어서 변수에 담음
    run(args)  # 읽어온 옵션으로 전체 검증 파이프라인 실행


if __name__ == "__main__":  # 이 파일을 직접 실행할 때만 아래 코드가 동작함 (다른 파일에서 불러쓸 때는 동작 안 함)
    main()  # 터미널 옵션 읽기 → 전체 검증 실행
