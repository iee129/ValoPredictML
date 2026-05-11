from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _run_command(cmd: list[str], *, cwd: Path, log_dir: Path, name: str) -> dict[str, Any]:
    log_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    (log_dir / f"{name}.stdout.log").write_text(result.stdout, encoding="utf-8")
    (log_dir / f"{name}.stderr.log").write_text(result.stderr, encoding="utf-8")
    return {
        "name": name,
        "returncode": result.returncode,
        "command": cmd,
        "stdout_log": str(log_dir / f"{name}.stdout.log"),
        "stderr_log": str(log_dir / f"{name}.stderr.log"),
    }


def _branch(
    *,
    repo: Path,
    root: Path,
    branch: str,
    input_dir: Path,
    include_vlrgg: bool,
    vlrgg_pipeline_matches: Path,
    skip_modeling: bool,
    shap_samples: int,
    close_margin: int,
) -> dict[str, Any]:
    branch_root = root / branch
    processed = branch_root / "processed"
    models = branch_root / "models"
    reports = branch_root / "reports"
    logs = branch_root / "logs"
    for path in [processed, models, reports, logs]:
        path.mkdir(parents=True, exist_ok=True)

    commands: list[dict[str, Any]] = []
    data_cmd = [
        sys.executable, "-m", "ml.data_pipeline",
        "--input", str(input_dir),
        "--output", str(processed),
        "--reports", str(reports),
    ]
    if include_vlrgg:
        data_cmd.extend(["--include-vlrgg-detail", "--vlrgg-pipeline-matches", str(vlrgg_pipeline_matches)])
    commands.append(_run_command(data_cmd, cwd=repo, log_dir=logs, name="data_pipeline"))

    if commands[-1]["returncode"] == 0 and not skip_modeling:
        commands.append(_run_command([
            sys.executable, "-m", "ml.train_model",
            "--input", str(processed),
            "--output", str(models),
            "--reports", str(reports),
        ], cwd=repo, log_dir=logs, name="train_model"))
    if commands[-1]["returncode"] == 0 and not skip_modeling:
        commands.append(_run_command([
            sys.executable, "-m", "ml.evaluate_model",
            "--input", str(processed),
            "--models", str(models),
            "--reports", str(reports),
            "--shap-samples", str(shap_samples),
            "--close-margin", str(close_margin),
        ], cwd=repo, log_dir=logs, name="evaluate_model"))
    if commands[-1]["returncode"] == 0 and not skip_modeling:
        commands.append(_run_command([
            sys.executable, "-m", "ml.validate_metrics",
            "--input", str(processed),
            "--models", str(models),
            "--reports", str(reports),
            "--close-margin", str(close_margin),
        ], cwd=repo, log_dir=logs, name="validate_metrics"))

    preprocess = _read_json(reports / "preprocess_summary.json")
    train = _read_json(reports / "train_summary.json")
    evaluate = _read_json(reports / "eval_summary.json")
    validation = _read_json(reports / "validation_report.json")
    return {
        "branch": branch,
        "include_vlrgg_detail": include_vlrgg,
        "processed_dir": str(processed),
        "models_dir": str(models),
        "reports_dir": str(reports),
        "commands": commands,
        "ok": all(command["returncode"] == 0 for command in commands),
        "preprocess": {
            "total_raw": preprocess.get("total_raw"),
            "total_clean": preprocess.get("total_clean"),
            "active_feature_count": preprocess.get("active_feature_count"),
            "vlrgg_detail_included": preprocess.get("vlrgg_detail_included"),
            "source_clean": preprocess.get("source_clean"),
        },
        "train": {
            "val_metrics": train.get("val_metrics"),
            "test_metrics": train.get("test_metrics"),
        },
        "evaluate": {
            "test": evaluate.get("test"),
            "close_match_multi": evaluate.get("close_match_multi"),
        },
        "validation": validation,
    }


def run(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    root = Path(args.root).resolve()
    input_dir = Path(args.input).resolve()
    vlrgg_pipeline_matches = Path(args.vlrgg_pipeline_matches).resolve()
    root.mkdir(parents=True, exist_ok=True)
    baseline = _branch(
        repo=repo,
        root=root,
        branch="baseline",
        input_dir=input_dir,
        include_vlrgg=False,
        vlrgg_pipeline_matches=vlrgg_pipeline_matches,
        skip_modeling=args.skip_modeling,
        shap_samples=args.shap_samples,
        close_margin=args.close_margin,
    )
    vlr = _branch(
        repo=repo,
        root=root,
        branch="with_vlrgg_detail",
        input_dir=input_dir,
        include_vlrgg=True,
        vlrgg_pipeline_matches=vlrgg_pipeline_matches,
        skip_modeling=args.skip_modeling,
        shap_samples=args.shap_samples,
        close_margin=args.close_margin,
    )
    summary = {
        "generated_at": _utc_now(),
        "input": str(input_dir),
        "vlrgg_pipeline_matches": str(vlrgg_pipeline_matches),
        "skip_modeling": bool(args.skip_modeling),
        "branches": {
            "baseline": baseline,
            "with_vlrgg_detail": vlr,
        },
        "comparison": {
            "active_feature_count_unchanged": (
                baseline["preprocess"].get("active_feature_count")
                == vlr["preprocess"].get("active_feature_count")
            ),
            "vlrgg_clean_rows": (vlr["preprocess"].get("source_clean") or {}).get("vlrgg_direct_detail"),
        },
    }
    out = root / "vlrgg_pipeline_experiment_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"VLR pipeline experiment summary written: {out}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline vs +VLR pipeline experiment in isolated directories")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--input", default="data/raw/kaggle")
    parser.add_argument("--vlrgg-pipeline-matches", default="data/processed/vlrgg_pipeline_matches.csv")
    parser.add_argument("--root", default=".omx/state/vlrgg_pipeline_experiment")
    parser.add_argument("--skip-modeling", action="store_true", help="Only run ml.data_pipeline for both branches")
    parser.add_argument("--shap-samples", type=int, default=500)
    parser.add_argument("--close-margin", type=int, default=2)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
