"""
Validate advanced ensemble against acceptance gates.

Usage:
    python -m ml.advanced.validate [--reports reports/advanced]

Exit codes:
    0 — all gates passed
    1 — one or more gates failed
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GATE_AUC = 0.70


def validate(reports_dir: str = "reports/advanced", models_dir: str = "models/advanced") -> int:
    rpt = Path(reports_dir)
    metrics_path = rpt / "metrics.json"

    if not metrics_path.exists():
        print(f"ERROR: {metrics_path} not found — run evaluate first.")
        return 1

    with open(metrics_path) as f:
        metrics = json.load(f)

    failures: list[str] = []
    passed: list[str] = []

    ens_test_auc = metrics.get("ensemble", {}).get("test", {}).get("auc", 0.0)

    # Gate 1: ensemble test AUC >= GATE_AUC
    if ens_test_auc >= GATE_AUC:
        passed.append(f"ensemble.test_auc={ens_test_auc:.4f} >= {GATE_AUC}")
    else:
        failures.append(
            f"ensemble.test_auc={ens_test_auc:.4f} < {GATE_AUC}  "
            f"(need +{GATE_AUC - ens_test_auc:.4f})"
        )

    # Gate 2: ensemble test AUC >= each individual model
    for name in ["rf", "xgb", "lgbm"]:
        ind_auc = metrics.get(name, {}).get("test", {}).get("auc", 0.0)
        if ens_test_auc >= ind_auc:
            passed.append(f"ensemble({ens_test_auc:.4f}) >= {name}({ind_auc:.4f})")
        else:
            failures.append(
                f"ensemble({ens_test_auc:.4f}) < {name}({ind_auc:.4f})  "
                f"(no ensemble benefit over {name})"
            )

    # Gate 3: val-test gap (skipped when val was used in training)
    meta_path = Path(models_dir) / "meta.json"
    trained_on_val = False
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        trained_on_val = "train+val" in meta.get("algorithm", "") or \
                         meta.get("trained_on_val", False)

    if not trained_on_val:
        ens_val_auc = metrics.get("ensemble", {}).get("val", {}).get("auc", 0.0)
        gap = abs(ens_val_auc - ens_test_auc)
        if gap <= 0.05:
            passed.append(f"|val_auc - test_auc| = {gap:.4f} <= 0.05")
        else:
            failures.append(
                f"|val_auc({ens_val_auc:.4f}) - test_auc({ens_test_auc:.4f})| = {gap:.4f} > 0.05"
            )
    else:
        passed.append("val-test gap check skipped (val used in training)")

    print("\n=== GATE RESULTS ===")
    for msg in passed:
        print(f"  PASS  {msg}")
    for msg in failures:
        print(f"  FAIL  {msg}")

    if failures:
        print(f"\nGATE FAILED ({len(failures)} check(s) failed, {len(passed)} passed)")
        return 1

    print(f"\nGATE PASSED ({len(passed)} checks)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default="reports/advanced")
    ap.add_argument("--models", default="models/advanced")
    args = ap.parse_args()
    sys.exit(validate(args.reports, args.models))
