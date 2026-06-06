"""각 모델(RF/XGB/LGBM)의 feature_importances_ 기반 막대 그래프를 생성한다.

SHAP 없이 순수 트리 내장 중요도를 사용하므로 실행 속도가 빠르고 의존성이 없다.

출력:
    reports/advanced/figures/feature_importance_rf.png
    reports/advanced/figures/feature_importance_xgb.png
    reports/advanced/figures/feature_importance_lgbm.png
    reports/advanced/feature_importance.json

Usage:
    python -m ml.advanced.feature_importance
    python -m ml.advanced.feature_importance --models models/advanced --output reports/advanced/figures --top-n 20
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_MODELS_DIR = "models/advanced"
DEFAULT_OUTPUT_DIR = "reports/advanced/figures"
DEFAULT_TOP_N = 20

MODEL_LABELS: dict[str, str] = {
    "rf": "Random Forest",
    "xgb": "XGBoost",
    "lgbm": "LightGBM",
}

MODEL_COLORS: dict[str, str] = {
    "rf": "#4CAF50",
    "xgb": "#2196F3",
    "lgbm": "#FF9800",
}


def _load_model(models_dir: Path, name: str) -> Any:
    """joblib 파일을 로드하고 feature_importances_ 속성을 검증한다."""
    path = models_dir / f"{name}.joblib"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} 없음. 먼저 `python -m ml.advanced.ensemble`을 실행하세요."
        )
    model = joblib.load(path)
    if not hasattr(model, "feature_importances_"):
        raise AttributeError(
            f"{name}.joblib 에 feature_importances_ 속성이 없습니다. "
            "VotingClassifier는 rf/xgb/lgbm 개별 모델만 처리합니다."
        )
    return model


def _top_importances(model: Any, top_n: int) -> tuple[list[str], list[float]]:
    """모델의 feature_importances_에서 상위 top_n 피처와 중요도를 반환한다."""
    importances = np.asarray(model.feature_importances_, dtype=float)
    names = (
        list(model.feature_names_in_)
        if hasattr(model, "feature_names_in_")
        else [str(i) for i in range(len(importances))]
    )
    order = np.argsort(importances)[::-1][:top_n]
    return [names[i] for i in order], [float(importances[i]) for i in order]


def _plot_bar(
    features: list[str],
    importances: list[float],
    model_name: str,
    output_path: Path,
    top_n: int,
) -> None:
    """수평 막대 그래프를 생성하고 PNG로 저장한다."""
    labels = [f[:28] + "…" if len(f) > 30 else f for f in features]

    fig, ax = plt.subplots(figsize=(10, max(5, top_n * 0.4)))
    color = MODEL_COLORS.get(model_name, "#607D8B")

    y_pos = np.arange(len(labels))
    ax.barh(y_pos, importances[::-1], color=color, alpha=0.85, edgecolor="white", linewidth=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels[::-1], fontsize=9)

    model_label = MODEL_LABELS.get(model_name, model_name.upper())
    ax.set_title(
        f"{model_label} — Feature Importance (Top {top_n})",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Importance (Gini / Gain)", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)

    for bar, val in zip(ax.patches, importances[::-1]):
        ax.text(
            bar.get_width() + max(importances) * 0.005,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.4f}",
            va="center",
            ha="left",
            fontsize=7.5,
            color="#333333",
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close("all")
    print(f"  저장 → {output_path}")


def run_feature_importance(
    models_dir: str = DEFAULT_MODELS_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    top_n: int = DEFAULT_TOP_N,
) -> dict[str, Any]:
    """RF/XGB/LGBM 세 모델의 피처 중요도 차트를 생성하고 JSON을 반환한다."""
    mdl = Path(models_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    reports_dir = out.parent
    reports_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "feature_contract": "advanced",
        "feature_count": None,
        "n_features": None,
        "generated_at": datetime.now(UTC).isoformat(),
        "importance_scale": "raw per-model feature_importances_",
        "top_n": top_n,
        "models": {},
    }

    for name in ("rf", "xgb", "lgbm"):
        print(f"[{name}] 모델 로드 중 ...")
        model = _load_model(mdl, name)
        model_feature_count = int(getattr(model, "n_features_in_", len(model.feature_importances_)))
        if result["feature_count"] is None:
            result["feature_count"] = model_feature_count
            result["n_features"] = model_feature_count
        elif result["feature_count"] != model_feature_count:
            raise ValueError(
                f"{name}.joblib feature count mismatch: "
                f"{model_feature_count} != {result['feature_count']}"
            )
        features, importances = _top_importances(model, top_n)
        _plot_bar(features, importances, name, out / f"feature_importance_{name}.png", top_n)
        result["models"][name] = [
            {"feature": f, "importance": v} for f, v in zip(features, importances)
        ]

    json_path = reports_dir / "feature_importance.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n피처 중요도 JSON 저장 → {json_path}")
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="RF/XGB/LGBM feature_importances_ 기반 막대 그래프 생성")
    ap.add_argument("--models", default=DEFAULT_MODELS_DIR)
    ap.add_argument("--output", default=DEFAULT_OUTPUT_DIR)
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    args = ap.parse_args()
    run_feature_importance(models_dir=args.models, output_dir=args.output, top_n=args.top_n)


if __name__ == "__main__":
    main()
