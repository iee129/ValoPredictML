import argparse
import json
import os
from datetime import date

import joblib

from ml.baseline.preprocess import load_split, build_xy, make_pipeline


def train(input_dir: str = "data/processed", output_dir: str = "models/baseline") -> None:
    df = load_split("train", base=input_dir)
    X, y, _ = build_xy(df)

    pipe = make_pipeline()
    pipe.fit(X, y)

    os.makedirs(output_dir, exist_ok=True)
    joblib.dump(pipe, os.path.join(output_dir, "model.joblib"))

    meta = {
        "algorithm": "LR+DT_soft_voting",
        "n_features": int(X.shape[1]),
        "n_rows": int(X.shape[0]),
        "date": str(date.today()),
        "hyperparams": {
            "lr": {"scaler": "StandardScaler", "C": 1.0, "max_iter": 1000},
            "dt": {"max_depth": 8, "min_samples_leaf": 50},
        },
    }
    with open(os.path.join(output_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Model → {output_dir}/model.joblib  ({X.shape[1]} features, {X.shape[0]} rows)")
    print(f"Meta  → {output_dir}/meta.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed")
    parser.add_argument("--output", default="models/baseline")
    args = parser.parse_args()
    train(args.input, args.output)
