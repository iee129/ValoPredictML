"""GET /health, GET /model — 모델 상태·근거."""
from __future__ import annotations

from fastapi import APIRouter

from app.predict import global_feature_importance, load_model, load_reports
from ml.baseline.preprocess import FEATURE_COLS_ADVANCED
from valo_web_backend.deps import to_http

router = APIRouter()


@router.get("/health")
def health() -> dict:
    try:
        model, _ = load_model()
        n = getattr(model, "n_features_in_", None)
        ok = n == len(FEATURE_COLS_ADVANCED)
        return {"status": "ok" if ok else "degraded",
                "model_loaded": bool(ok), "n_features": n, "contract": "advanced"}
    except Exception as exc:   # 산출물 부재 등 — 서버는 살아있고 상태만 보고
        return {"status": "unavailable", "model_loaded": False,
                "n_features": None, "contract": "advanced", "detail": str(exc)}


@router.get("/model")
def model_info() -> dict:
    try:
        _, meta = load_model()
        reports = load_reports()
        gi = global_feature_importance(limit=20)
    except (FileNotFoundError, ValueError) as exc:
        raise to_http(exc)
    return {
        "algorithm": meta.get("algorithm", "RF+XGB+LGBM_soft_voting"),
        "contract": meta.get("feature_contract", "advanced"),
        "n_features": meta.get("n_features", 125),
        "metrics": reports.get("metrics", {}),
        "validation": reports.get("validation", {}),
        "global_importance": gi,
    }
