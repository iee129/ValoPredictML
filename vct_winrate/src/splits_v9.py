"""시간순 비율 분할 (v9)."""
from __future__ import annotations

import pandas as pd


def split_proportional(
    df: pd.DataFrame,
    train_ratio: float = 0.80,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values("year").reset_index(drop=True)
    n = len(df)
    n_train = int(n * train_ratio)
    return df.iloc[:n_train].copy(), df.iloc[n_train:].copy()
