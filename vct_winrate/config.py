"""경로/하이퍼파라미터 단일 진실 소스."""
from pathlib import Path

# ───────── 경로 ─────────
PROJECT_ROOT = Path(__file__).resolve().parent
VCT_DATASET_ROOT = PROJECT_ROOT.parent / "vct_dataset"

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
PROCESSED_DIR = ARTIFACTS_DIR / "processed"
MODELS_DIR = ARTIFACTS_DIR / "models"
REPORTS_DIR = ARTIFACTS_DIR / "reports"
PRIOR_STATE_PATH = ARTIFACTS_DIR / "prior_state.joblib"

TRAIN_CSV = PROCESSED_DIR / "train.csv"
VAL_CSV = PROCESSED_DIR / "val.csv"
TEST_CSV = PROCESSED_DIR / "test.csv"
ALL_CSV = PROCESSED_DIR / "all.csv"

# ───────── 연도 분할 ─────────
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
TRAIN_YEARS = [2021, 2022, 2023, 2024]
VAL_YEARS = [2025]
TEST_YEARS = [2026]

# ───────── prior 윈도우 크기 ─────────
PLAYER_RECENT_N = 20         # 선수 전체 직전 N개 (매치, 맵)
PLAYER_AGENT_RECENT_N = 10   # 선수+요원 직전 N개
PLAYER_MAP_RECENT_N = 10     # 선수+맵 직전 N개
TEAM_RECENT_N = 10           # 팀 전체 직전 N매치
TEAM_MAP_RECENT_N = 10       # 팀+맵 직전 N개
H2H_RECENT_N = 5             # 양 팀 H2H 직전 N매치

# ───────── 모델 하이퍼파라미터 ─────────
# LightGBM: Gradient Boosting 트리. 결측값 자체 처리, 스케일링 불필요.
LGBM_PARAMS = dict(
    n_estimators=400,
    learning_rate=0.05,
    num_leaves=31,
    random_state=42,
    n_jobs=-1,
    verbose=-1,
)
# XGBoost: 그래디언트 부스팅 트리. 결측값 자체 처리, 스케일링 불필요.
#   hist 방식으로 빠른 학습, L2 정규화로 과적합 억제.
XGB_PARAMS = dict(
    n_estimators=400,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    tree_method="hist",
    eval_metric="logloss",
    n_jobs=-1,
    random_state=42,
    verbosity=0,
)
# SVM: LinearSVC (선형 커널, 빠름) + CalibratedClassifierCV(cv=5) 로 감싸서 predict_proba 활성화.
#   LinearSVC 자체는 확률 미지원이라 sigmoid calibration 으로 0~1 확률을 얻음.
SVM_PARAMS = dict(
    C=1.0,
    max_iter=5000,
    random_state=42,
)
SVM_CALIBRATION_CV = 5
RF_PARAMS = dict(
    n_estimators=400,
    n_jobs=-1,
    random_state=42,
)
# 앙상블 가중치 (soft vote 평균). evaluate.py 에서 val 점수 보고 조정 가능.
# v9 = LGBM + XGB + SVM + RF (4-모델 앙상블, 알고리즘 다양성 확보)
ENSEMBLE_WEIGHTS_V9 = dict(lgbm=0.25, xgb=0.20, svm=0.25, rf=0.30)
# v10 = LGBM + XGB + RF (3-모델 앙상블, SVM 제외)
ENSEMBLE_WEIGHTS_V10 = dict(lgbm=1 / 3, xgb=1 / 3, rf=1 / 3)

# ───────── 평가 ─────────
CLASSIFICATION_THRESHOLD = 0.5
RANDOM_SEED = 42
