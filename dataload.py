"""
ValoPredictML 데이터셋 일괄 다운로드 스크립트

사용법:
  python dataload.py

요구사항:
  ~/.kaggle/kaggle.json 에 Kaggle API 키 필요
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import kagglehub

OUTPUT_DIR = Path("data/raw/kaggle")

# (kaggle_id, 로컬 폴더명)
# 수집 기준: agent + map + winner 필수 / K·D·A 개별 분리 / 선수-경기-맵 1행 단위
# 결측률 < 30%(핵심 스탯) / 전체 학습셋 비중 < 20% / 프로·준프로 경기만
DATASETS: list[tuple[str, str]] = [
    # ── 핵심 소스 (대용량, 다년도) ──────────────────────────────────────────
    ("ryanluong1/valorant-champion-tour-2021-2023-data",      "vct_2021_2023"),
    ("ryanluong1/valorant-challengers-league-data",           "ryanluong1__valorant-challengers-league-data"),
    ("qualidea1217/valorant-pro-matches-since-april-2021",    "qualidea1217__valorant-pro-matches-since-april-2021"),

    # ── piyush86kumar 계열 (이벤트별 상세 스탯) ─────────────────────────────
    # vct-2025-all-events 가 하위 이벤트(kickoff/stage/masters/champions)를 포함
    ("piyush86kumar/valorant-champions-tour-2024-all-events", "piyush86kumar__valorant-champions-tour-2024-all-events"),
    ("piyush86kumar/valorant-vct-2025-all-events",            "piyush86kumar__valorant-vct-2025-all-events"),

    # ── 보조 소스 (이벤트 특화) ─────────────────────────────────────────────
    ("ediashtarevin/vct-champions-2023-stats",                "ediashtarevin__vct-champions-2023-stats"),
    ("kierru/vctpacific-2023",                                "kierru__vctpacific-2023"),
]


def download_all() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total = len(DATASETS)
    skipped, success, failed = 0, 0, []

    for i, (kaggle_id, folder_name) in enumerate(DATASETS, 1):
        dest = OUTPUT_DIR / folder_name
        prefix = f"[{i:2d}/{total}]"

        if dest.exists():
            print(f"{prefix} SKIP  {folder_name}")
            skipped += 1
            continue

        print(f"{prefix} DOWN  {kaggle_id} ...", flush=True)
        try:
            cache_path = kagglehub.dataset_download(kaggle_id)
            shutil.copytree(cache_path, dest)
            print(f"{prefix} OK    → {dest}")
            success += 1
        except Exception as exc:
            print(f"{prefix} FAIL  {kaggle_id}: {exc}", file=sys.stderr)
            failed.append((kaggle_id, str(exc)))

    print(f"\n완료: {success}개 다운로드, {skipped}개 스킵", end="")
    if failed:
        print(f", {len(failed)}개 실패")
        for kid, err in failed:
            print(f"  - {kid}: {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print()


if __name__ == "__main__":
    download_all()
