"""Build active advanced features with a chronological year-block split.

The active advanced lane uses a chronological holdout and writes
``data/processed/advanced`` plus ``reports/advanced``. It remains Kaggle-only
unless ``--include-vlrgg`` is passed.

Default split inference uses whole-year blocks because a large share of the
Kaggle rows only have year-level dates.  With the current data this resolves to:

    train: years before the inferred boundary
    test:  years at or after the inferred boundary
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ml.baseline.preprocess import (
    EXPECTED_FEATURE_COUNT,
    EXPECTED_FEATURE_COUNT_ADVANCED,
    FEATURE_COLS,
    FEATURE_COLS_ADVANCED,
    FEATURE_ENGINEERING_CONFIG,
    SOURCE_CONTRACT,
    build_features,
    build_xy,
    find_forbidden_feature_names,
    save_splits,
)

DEFAULT_INPUT_DIR = "data/processed"
DEFAULT_OUTPUT_DIR = "data/processed/advanced"
DEFAULT_REPORTS_DIR = "reports/advanced"


def _contract_cols(feature_contract: str) -> list[str]:
    return FEATURE_COLS if feature_contract == "baseline" else FEATURE_COLS_ADVANCED


def _default_dirs(feature_contract: str) -> tuple[str, str]:
    if feature_contract == "baseline":
        return "data/processed/baseline", "reports/baseline"
    return DEFAULT_OUTPUT_DIR, DEFAULT_REPORTS_DIR


def _load_match_date_quality(input_dir: Path) -> pd.DataFrame:
    path = input_dir / "matches.csv"
    cols = ["match_key", "date_raw", "date_quality"]
    frame = pd.read_csv(path, usecols=lambda col: col in cols, low_memory=False)
    for col in cols:
        if col not in frame.columns:
            frame[col] = None
    frame["match_key"] = frame["match_key"].astype(str)
    return frame.drop_duplicates("match_key")


def _infer_test_boundary(
    frame: pd.DataFrame,
    test_ratio: float,
) -> int:
    year_counts = (
        frame.assign(year_num=pd.to_numeric(frame["year"], errors="coerce"))
        .dropna(subset=["year_num"])
        .drop_duplicates("match_key")
        .groupby("year_num")["match_key"]
        .nunique()
        .sort_index()
    )
    years = [int(year) for year in year_counts.index.tolist()]
    if len(years) < 2:
        raise ValueError(f"Chronological split needs at least 2 years, got {years}")

    total = int(year_counts.sum())
    test_target = float(total) * test_ratio

    # 최근 연도부터 test로 누적하되 첫 연도는 train에 남긴다.
    # 각 후보 test_from_year의 test 크기가 target에 가장 가까운 경계를 고른다
    # (연도 단위 이산성 때문에 정확한 비율은 불가).
    candidates: list[tuple[int, int]] = []
    cumulative = 0
    for year in reversed(years[1:]):
        cumulative += int(year_counts.loc[year])
        candidates.append((year, cumulative))
    test_from_year = min(candidates, key=lambda yc: abs(yc[1] - test_target))[0]
    if not (min(years) < test_from_year <= max(years)):
        raise ValueError(
            "Could not infer valid chronological boundary: "
            f"years={years}, test_from_year={test_from_year}"
        )
    return test_from_year


def _assign_year_block_splits(
    frame: pd.DataFrame,
    test_from_year: int | None,
    test_ratio: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    out = frame.copy()
    out["year"] = pd.to_numeric(out["year"], errors="raise").astype(int)

    inferred = test_from_year is None
    if inferred:
        test_from_year = _infer_test_boundary(out, test_ratio)

    if test_from_year is None:
        raise ValueError("test_from_year must be set")

    out["split"] = "train"
    out.loc[out["year"] >= test_from_year, "split"] = "test"

    split_counts = out["split"].value_counts().to_dict()
    missing = [split for split in ("train", "test") if split_counts.get(split, 0) == 0]
    if missing:
        raise ValueError(
            f"Chronological split produced empty split(s): {missing}; "
            f"test_from_year={test_from_year}"
        )

    metadata = {
        "mode": "year_block",
        "boundaries": {
            "train": f"year < {test_from_year}",
            "test": f"year >= {test_from_year}",
            "test_from_year": int(test_from_year),
            "inferred": bool(inferred),
        },
        "requested_ratios": {
            "train": float(max(0.0, 1.0 - test_ratio)),
            "test": float(test_ratio),
        },
    }
    return out, metadata


def _split_overlap_count(frame: pd.DataFrame) -> int:
    keys = {
        split: set(frame.loc[frame["split"] == split, "match_key"].astype(str))
        for split in ("train", "test")
    }
    return int(len(keys["train"] & keys["test"]))


def _summarize_split(frame: pd.DataFrame, date_meta: pd.DataFrame) -> dict[str, Any]:
    work = frame.merge(date_meta, on="match_key", how="left")
    work["_parsed_date"] = pd.to_datetime(work["date"], errors="coerce")
    summary: dict[str, Any] = {}
    for split in ("train", "test"):
        sub = work[work["split"] == split].copy()
        label_mean = float(sub["label"].mean()) if len(sub) else None
        parsed_dates = sub["_parsed_date"].dropna()
        summary[split] = {
            "rows": int(len(sub)),
            "unique_match_keys": int(sub["match_key"].nunique()),
            "year_min": int(sub["year"].min()) if len(sub) else None,
            "year_max": int(sub["year"].max()) if len(sub) else None,
            "date_min": str(parsed_dates.min().date()) if len(parsed_dates) else None,
            "date_max": str(parsed_dates.max().date()) if len(parsed_dates) else None,
            "label_mean": label_mean,
            "date_quality_counts": {
                str(k): int(v)
                for k, v in sub["date_quality"].fillna("<missing>").value_counts().to_dict().items()
            },
            "source_counts": {
                str(k): int(v)
                for k, v in sub["source"].fillna("<missing>").value_counts().to_dict().items()
            },
        }
    return summary


def _chronology_checks(frame: pd.DataFrame) -> dict[str, Any]:
    ranges: dict[str, dict[str, int | None]] = {}
    for split in ("train", "test"):
        sub = frame[frame["split"] == split]
        ranges[split] = {
            "year_min": int(sub["year"].min()) if len(sub) else None,
            "year_max": int(sub["year"].max()) if len(sub) else None,
        }

    train_before_test = bool(ranges["train"]["year_max"] < ranges["test"]["year_min"])
    return {
        "year_ranges": ranges,
        "train_before_test": train_before_test,
        "no_year_crossing_between_splits": bool(train_before_test),
    }


def _build_report(
    frame: pd.DataFrame,
    date_meta: pd.DataFrame,
    split_metadata: dict[str, Any],
    output_dir: Path,
    feature_contract: str = "advanced",
) -> dict[str, Any]:
    feature_cols = _contract_cols(feature_contract)
    expected_count = EXPECTED_FEATURE_COUNT if feature_contract == "baseline" else EXPECTED_FEATURE_COUNT_ADVANCED
    forbidden = find_forbidden_feature_names(feature_cols)
    allowed_prefixes = tuple(SOURCE_CONTRACT.get("allowed_source_prefixes", ["kaggle_", "vlrgg_"]))
    bad_sources = sorted(
        str(source)
        for source in frame.loc[
            ~frame["source"].astype(str).str.startswith(allowed_prefixes),
            "source",
        ].dropna().unique()
    )
    overlap_count = _split_overlap_count(frame)
    chronology = _chronology_checks(frame)
    split_summary = _summarize_split(frame, date_meta)

    trust_failures: list[str] = []
    if len(feature_cols) != expected_count:
        trust_failures.append(f"feature_count={len(feature_cols)} expected {expected_count}")
    if forbidden:
        trust_failures.append(f"forbidden_features={forbidden}")
    if bad_sources:
        trust_failures.append(f"non_allowed_sources={bad_sources}")
    if overlap_count:
        trust_failures.append(f"split_overlap_count={overlap_count}")
    if not chronology["no_year_crossing_between_splits"]:
        trust_failures.append("year ranges overlap or cross split boundaries")

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_contract": feature_contract,
        "feature_count": int(len(feature_cols)),
        "feature_engineering": {
            "same_year_history": FEATURE_ENGINEERING_CONFIG.get("same_year_history"),
            "history_contract": FEATURE_ENGINEERING_CONFIG.get("prior_windows"),
        },
        "source_contract": {
            "active_rule": "all rows must match the configured allowed source prefixes",
            "bad_sources": bad_sources,
        },
        "split_strategy": split_metadata,
        "output_dir": str(output_dir),
        "split_summary": split_summary,
        "chronology_checks": chronology,
        "split_overlap_count": overlap_count,
        "forbidden_feature_count": len(forbidden),
        "forbidden_features": forbidden,
        "trust_failures": trust_failures,
        "trust_verdict": "시간순 분할 정상" if not trust_failures else "문제",
    }


def run_chrono_preprocess(
    feature_contract: str = "advanced",
    input_dir: str = DEFAULT_INPUT_DIR,
    output_dir: str | None = None,
    reports_dir: str | None = None,
    test_from_year: int | None = None,
    test_ratio: float = 0.20,
    include_vlrgg: bool = False,
) -> dict[str, Any]:
    default_out, default_rpt = _default_dirs(feature_contract)
    inp = Path(input_dir)
    out_dir = Path(output_dir or default_out)
    rpt_dir = Path(reports_dir or default_rpt)
    rpt_dir.mkdir(parents=True, exist_ok=True)

    source_label = "Kaggle+VLR.gg" if include_vlrgg else "Kaggle-only"
    print(f"Building {feature_contract} {source_label} features from {inp}/ ...")
    features = build_features(str(inp), feature_contract=feature_contract, include_vlrgg=include_vlrgg)
    features["match_key"] = features["match_key"].astype(str)
    print(f"Assigning chronological year-block split for {len(features):,} rows ...")
    features, split_metadata = _assign_year_block_splits(
        features,
        test_from_year=test_from_year,
        test_ratio=test_ratio,
    )

    date_meta = _load_match_date_quality(inp)
    report = _build_report(features, date_meta, split_metadata, out_dir, feature_contract=feature_contract)

    save_splits(features, processed_dir=str(inp), output_dir=str(out_dir))
    for split in ("train", "test"):
        split_frame = features[features["split"] == split]
        X, y, groups = build_xy(split_frame, feature_contract=feature_contract)
        print(
            f"  {split}: X={X.shape}, y={y.shape}, "
            f"matches={groups.nunique():,}, label_rate={y.mean():.3f}"
        )

    report_path = rpt_dir / "split_metadata.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Saved split metadata: {report_path}")
    print(f"분할 판정: {report['trust_verdict']}")
    if report["trust_failures"]:
        for failure in report["trust_failures"]:
            print(f"  문제 {failure}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-contract", default="advanced", choices=["baseline", "advanced"])
    parser.add_argument("--input", default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", default=None)
    parser.add_argument("--reports", default=None)
    parser.add_argument("--test-from-year", type=int, default=None)
    parser.add_argument("--test-ratio", type=float, default=0.20)
    parser.add_argument("--include-vlrgg", action="store_true", default=False,
                        help="vlrgg_ 소스도 포함 (런 한정, 기본=kaggle-only)")
    args = parser.parse_args()
    run_chrono_preprocess(
        feature_contract=args.feature_contract,
        input_dir=args.input,
        output_dir=args.output,
        reports_dir=args.reports,
        test_from_year=args.test_from_year,
        test_ratio=args.test_ratio,
        include_vlrgg=args.include_vlrgg,
    )
