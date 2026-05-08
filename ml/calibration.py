"""ml/calibration.py — 확률 보정 래퍼 클래스 (train/evaluate 공유)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression


class _IsotonicCalibratedModel:
    """IsotonicRegression으로 확률을 보정하는 모델 래퍼 (sklearn 1.8+ cv='prefit' 제거 대응)."""

    def __init__(self, base_model, calibrator: IsotonicRegression) -> None:
        self._base = base_model
        self._cal = calibrator

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raw = self._base.predict_proba(X)[:, 1]
        cal_pos = self._cal.predict(raw)
        cal_pos = np.clip(cal_pos, 0.0, 1.0)
        return np.column_stack([1.0 - cal_pos, cal_pos])

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)
