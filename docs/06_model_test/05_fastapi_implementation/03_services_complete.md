> ⚠️ 참고/확장 설계: 현재 시연은 웹 스택(FastAPI `src/api` + Next.js `web`) 기준이다. 이 문서의 테스트 설계는 참고용으로 보존한다.

> ⚠️ **참고용**: 본 프로젝트는 웹 스택(FastAPI `src/api` + Next.js `web`)으로 서빙한다. 본문의 상세 테스트 설계는 참고용으로 보존된다.

# 03. prediction_service.py 완전 구현

## 1. 파일 위치

```
backend/
└── services/
    └── prediction_service.py
```

---

## 2. 완전 구현 코드

```python
# backend/services/prediction_service.py
"""
발로란트 팀 조합 승률 예측 서비스.

싱글톤 패턴으로 모델을 1회만 로드하고 재사용합니다.
RF + XGBoost + LightGBM 가중 Soft Voting (2.0:3.0:0.1) 앙상블.
"""

import json
import logging
import os
from typing import Optional

import joblib
import numpy as np

logger = logging.getLogger(__name__)


# ── 요원 역할 매핑 ────────────────────────────────────────────────────────
AGENT_ROLE_MAP: dict[str, str] = {
    # Duelist
    "Jett": "duelist", "Reyna": "duelist", "Neon": "duelist",
    "Yoru": "duelist", "Phoenix": "duelist", "Iso": "duelist",
    "Waylay": "duelist",
    # Initiator
    "Sova": "initiator", "Breach": "initiator", "Skye": "initiator",
    "Fade": "initiator", "Gekko": "initiator", "KAY/O": "initiator",
    "Tejo": "initiator",
    # Controller
    "Viper": "controller", "Omen": "controller", "Brimstone": "controller",
    "Astra": "controller", "Harbor": "controller", "Clove": "controller",
    # Sentinel
    "Killjoy": "sentinel", "Cypher": "sentinel", "Sage": "sentinel",
    "Chamber": "sentinel", "Deadlock": "sentinel", "Vyse": "sentinel",
}


def get_role_counts(agents: list[str]) -> dict[str, int]:
    """요원 목록에서 역할군별 인원수를 집계합니다."""
    counts = {"duelist": 0, "initiator": 0, "controller": 0, "sentinel": 0, "unknown": 0}
    for agent in agents:
        role = AGENT_ROLE_MAP.get(agent, "unknown")
        counts[role] += 1
    return counts


def calculate_confidence(prob: float) -> str:
    """예측 확률의 극단성 기반 신뢰도를 분류합니다."""
    distance = abs(prob - 0.5)
    if distance >= 0.2:
        return "high"
    elif distance >= 0.1:
        return "medium"
    else:
        return "low"


# ── 피처 엔지니어링 ───────────────────────────────────────────────────────
class FeatureEngineer:
    """맵 이름과 팀 구성을 ML 피처 벡터로 변환합니다."""

    FEATURE_NAMES = [
        "map_encoded",
        "team_a_duelist", "team_a_initiator", "team_a_controller", "team_a_sentinel", "team_a_unknown",
        "team_b_duelist", "team_b_initiator", "team_b_controller", "team_b_sentinel", "team_b_unknown",
        "duelist_diff", "initiator_diff", "controller_diff", "sentinel_diff",
    ]

    def __init__(self, label_encoder):
        self.le_map = label_encoder

    def transform(self, map_name: str, team_a: list[str], team_b: list[str]) -> np.ndarray:
        """입력 데이터를 15차원 피처 벡터로 변환합니다."""
        map_encoded = self.le_map.transform([map_name])[0]

        rc_a = get_role_counts(team_a)
        rc_b = get_role_counts(team_b)

        features = [
            map_encoded,
            rc_a["duelist"],   rc_a["initiator"],   rc_a["controller"],   rc_a["sentinel"],   rc_a["unknown"],
            rc_b["duelist"],   rc_b["initiator"],   rc_b["controller"],   rc_b["sentinel"],   rc_b["unknown"],
            rc_a["duelist"]   - rc_b["duelist"],
            rc_a["initiator"] - rc_b["initiator"],
            rc_a["controller"]- rc_b["controller"],
            rc_a["sentinel"]  - rc_b["sentinel"],
        ]
        return np.array([features], dtype=np.float32)


# ── 예측 서비스 (싱글톤) ──────────────────────────────────────────────────
class PredictionService:
    """ML 모델을 로드하고 예측을 수행하는 싱글톤 서비스."""

    _instance: Optional["PredictionService"] = None
    _initialized: bool = False

    def __new__(cls) -> "PredictionService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._loaded = False
            self._load_models()
            PredictionService._initialized = True

    # ── 모델 로드 ─────────────────────────────────────────────────────────

    def _load_models(self) -> None:
        model_path = os.environ.get("MODEL_PATH", "./models")
        logger.info(f"모델 로드 시작: {model_path}")

        try:
            self.xgb_model  = joblib.load(f"{model_path}/xgboost_model.joblib")
            self.lgbm_model = joblib.load(f"{model_path}/lgbm_model.joblib")
            self.le_map     = joblib.load(f"{model_path}/label_encoder_map.joblib")

            with open(f"{model_path}/model_metadata.json", encoding="utf-8") as f:
                self.metadata: dict = json.load(f)

            self.engineer = FeatureEngineer(self.le_map)
            self._loaded = True
            logger.info(
                f"모델 로드 완료: version={self.metadata.get('model_version')} "
                f"trained_at={self.metadata.get('trained_at')}"
            )
        except FileNotFoundError as e:
            logger.error(f"모델 파일 없음: {e}")
            self._loaded = False
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}", exc_info=True)
            self._loaded = False

    # ── 예측 ──────────────────────────────────────────────────────────────

    def predict(self, map_name: str, team_a: list[str], team_b: list[str]) -> dict:
        """
        팀 조합으로 승률을 예측합니다.

        Args:
            map_name: 경기 맵 이름 (VALID_MAPS 내 값)
            team_a: 팀 A 요원 목록 (5명)
            team_b: 팀 B 요원 목록 (5명)

        Returns:
            예측 결과 딕셔너리 (PredictResponse 스키마 호환)

        Raises:
            RuntimeError: 모델이 로드되지 않은 경우
        """
        if not self._loaded:
            raise RuntimeError("모델이 로드되지 않았습니다.")

        # 피처 변환
        features = self.engineer.transform(map_name, team_a, team_b)

        # 앙상블 예측 (Soft Voting)
        xgb_prob  = float(self.xgb_model.predict_proba(features)[0, 1])
        lgbm_prob = float(self.lgbm_model.predict_proba(features)[0, 1])
        win_prob  = round(0.6 * xgb_prob + 0.4 * lgbm_prob, 4)

        # 피처 중요도 (XGBoost 기준, 상위 5개)
        importances = self.xgb_model.feature_importances_.tolist()
        feature_names = self.metadata.get("features", FeatureEngineer.FEATURE_NAMES)
        importance_dict = dict(zip(feature_names, importances))
        top_importance = dict(
            sorted(importance_dict.items(), key=lambda x: -x[1])[:5]
        )

        return {
            "win_probability":     win_prob,
            "lose_probability":    round(1 - win_prob, 4),
            "confidence":          calculate_confidence(win_prob),
            "team_a_role_counts":  get_role_counts(team_a),
            "team_b_role_counts":  get_role_counts(team_b),
            "feature_importance":  top_importance,
            "map":                 map_name,
            "model_version":       self.metadata.get("model_version", "unknown"),
        }

    # ── 상태 조회 메서드 ──────────────────────────────────────────────────

    def is_loaded(self) -> bool:
        """모델이 성공적으로 로드되었는지 반환합니다."""
        return self._loaded

    def get_version(self) -> str:
        """모델 버전 문자열을 반환합니다."""
        if not self._loaded:
            return "not_loaded"
        return self.metadata.get("model_version", "unknown")

    def get_trained_at(self) -> Optional[str]:
        """모델 학습 시각을 ISO 8601 문자열로 반환합니다."""
        if not self._loaded:
            return None
        return self.metadata.get("trained_at")

    def reload(self) -> bool:
        """모델을 강제로 다시 로드합니다 (핫 리로드용)."""
        logger.info("모델 강제 재로드 시작")
        PredictionService._initialized = False
        self._initialized = False
        self._load_models()
        PredictionService._initialized = True
        return self._loaded
```

---

## 3. model_metadata.json 구조

```json
{
  "model_version": "1.0.0",
  "trained_at": "2024-01-10T12:00:00",
  "algorithm": "RandomForest + XGBoost + LightGBM Weighted Soft Voting (2.0:3.0:0.1)",
  "split": "chronological year-block (train 2020-2025 / test 2026)",
  "features": [
    "diff_prior_kd_mean", "diff_prior_kd_x_history_coverage", "diff_prior_games_mean",
    "diff_max_prior_kd", "diff_player_agent_games_mean", "diff_agent_map_fit",
    "... 외 총 179개 (FEATURE_COLS_ADVANCED)"
  ],
  "n_features": 179,
  "training_samples": 75405,
  "test_auc": 0.7010,
  "test_accuracy": 0.6454,
  "test_f1": 0.6478,
  "weight_selection_val_auc": 0.6682,
  "rf_weight": 2.0,
  "xgb_weight": 3.0,
  "lgbm_weight": 0.1
}
```

---

## 4. 단위 테스트

```python
# tests/unit/test_prediction_service.py
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from backend.services.prediction_service import (
    get_role_counts,
    calculate_confidence,
    FeatureEngineer,
)


class TestGetRoleCounts:
    def test_standard_team(self):
        counts = get_role_counts(["Jett","Sova","Viper","Killjoy","Skye"])
        assert counts["duelist"] == 1
        assert counts["initiator"] == 2
        assert counts["controller"] == 1
        assert counts["sentinel"] == 1
        assert counts["unknown"] == 0

    def test_all_duelist(self):
        counts = get_role_counts(["Jett","Reyna","Neon","Yoru","Phoenix"])
        assert counts["duelist"] == 5
        assert counts["initiator"] == 0

    def test_unknown_agent(self):
        counts = get_role_counts(["Jett","Sova","Viper","Killjoy","NEWAGENT"])
        assert counts["unknown"] == 1

    def test_kayo_with_slash(self):
        counts = get_role_counts(["KAY/O","Sova","Viper","Killjoy","Skye"])
        assert counts["initiator"] == 2  # KAY/O + Sova


class TestCalculateConfidence:
    @pytest.mark.parametrize("prob,expected", [
        (0.73, "high"),
        (0.30, "high"),
        (0.80, "high"),
        (0.20, "high"),
        (0.65, "medium"),
        (0.38, "medium"),
        (0.55, "low"),
        (0.50, "low"),
        (0.45, "low"),
    ])
    def test_confidence_levels(self, prob, expected):
        assert calculate_confidence(prob) == expected
```
