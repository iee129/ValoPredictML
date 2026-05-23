import pandas as pd
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

META_COLS = [
    "match_key", "dedup_key", "date", "date_raw", "date_quality",
    "event", "map", "team_a", "team_b", "source", "provenance", "split",
    "strict_before_cutoff",
]


def load_split(name: str, base: str = "data/processed") -> pd.DataFrame:
    return pd.read_csv(f"{base}/{name}.csv", low_memory=False)


def build_xy(df: pd.DataFrame):
    drop_explicit = [c for c in (META_COLS + ["label"]) if c in df.columns]
    X = df.drop(columns=drop_explicit).select_dtypes(include="number").copy()

    wr_cols = [c for c in X.columns if c.endswith("_prior_wr")]
    for col in wr_cols:
        unk = f"{col}_unknown"
        if unk not in X.columns:
            X[unk] = X[col].isna().astype(int)
    X[wr_cols] = X[wr_cols].fillna(0.5)
    X = X.fillna(0)

    y = df["label"]
    groups = df["match_key"]
    return X, y, groups


def make_pipeline() -> VotingClassifier:
    lr = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, C=1.0, random_state=42)),
    ])
    dt = DecisionTreeClassifier(max_depth=8, min_samples_leaf=50, random_state=42)
    return VotingClassifier(
        estimators=[("lr", lr), ("dt", dt)],
        voting="soft",
        n_jobs=1,
    )


if __name__ == "__main__":
    for split in ("train", "val", "test"):
        df = load_split(split)
        X, y, groups = build_xy(df)
        print(f"{split}: X={X.shape}, y={y.shape}, matches={groups.nunique()}")
