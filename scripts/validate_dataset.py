#!/usr/bin/env python3
"""scripts/validate_dataset.py — Kaggle 데이터셋 파이프라인 적합성 검증기.

Hard Gate 6개를 전부 통과한 뒤 Soft Score(0~100)로 채택 우선순위를 결정한다.

사용법:
  python scripts/validate_dataset.py --path data/raw/kaggle/vct_2021_2023
  python scripts/validate_dataset.py --path data/raw/kaggle/some_new_dataset --processed data/processed
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from ml.agent_roles import normalize_agent, normalize_map

# ── 판정 상수 ──────────────────────────────────────────────────────────────────

RANKED_KEYWORDS = {
    "ranked", "rank", "unranked", "competitive mm", "deathmatch",
    "spike rush", "escalation", "swiftplay", "teamdeathmatch", "premier",
}

AGENT_COL_HINTS  = {"agent", "agents", "agent_name", "agent_pick", "agent1"}
MAP_COL_HINTS    = {"map", "map_name", "map_played"}
WIN_COL_HINTS    = {"win_lose", "winner", "win", "result", "outcome", "win_loss", "map_winner"}
SCORE_A_HINTS    = {"score_a", "team a score", "team_a_score", "score1", "team1-score"}
SCORE_B_HINTS    = {"score_b", "team b score", "team_b_score", "score2", "team2-score"}

STAT_GROUPS: dict[str, set[str]] = {
    "ACS":  {"acs", "average combat score", "combat_score"},
    "KD":   {"kills", "k", "kd", "kill_death"},
    "KAST": {"kast", "kill, assist, trade, survive %"},
    "ADR":  {"adr", "average damage per round", "average_damage"},
    "FK":   {"fk", "first kills", "first_kills"},
    "FD":   {"fd", "first deaths", "first_deaths"},
    "HS":   {"hs", "headshot %", "hs_pct", "headshot_pct"},
}

SOFT_MAX = {
    "파이프라인 통과율 (추정)": 30,
    "신규 기여율":              25,
    "요원 커버리지":            15,
    "맵 커버리지":              10,
    "연도 다양성 (2024+)":      10,
    "스탯 풍부도":              10,
}


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _find_col(columns: list[str], hints: set[str]) -> str | None:
    lower_map = {c.lower(): c for c in columns}
    for h in hints:
        if h in lower_map:
            return lower_map[h]
    return None


def _detect_schema(df: pd.DataFrame, scores_df: pd.DataFrame | None = None) -> dict:
    cols = list(df.columns)
    # ryanluong 포맷: 스코어 컬럼은 maps_scores.csv에만 존재 — 스코어 탐지 대상에 포함
    score_cols = list(scores_df.columns) if scores_df is not None else []
    win_score_cols = cols + [c for c in score_cols if c not in cols]
    return {
        "agent_col":   _find_col(cols, AGENT_COL_HINTS),
        "map_col":     _find_col(cols, MAP_COL_HINTS),
        "win_col":     _find_col(win_score_cols, WIN_COL_HINTS),
        "score_a_col": _find_col(win_score_cols, SCORE_A_HINTS),
        "score_b_col": _find_col(win_score_cols, SCORE_B_HINTS),
        "stat_cols":   {k: _find_col(cols, v) for k, v in STAT_GROUPS.items()},
    }


def _read_csv_safe(path: Path, nrows: int = 5000) -> pd.DataFrame | None:
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False, nrows=nrows)
        except Exception:
            pass
    return None


# ── 포맷 감지 ─────────────────────────────────────────────────────────────────

def _load_dataset(path: Path) -> tuple[pd.DataFrame | None, pd.DataFrame | None, str]:
    """(main_df, scores_df, format_name) 반환. scores_df는 ryanluong 전용."""
    overview_files = list(path.rglob("overview.csv"))
    if overview_files:
        # ryanluong 멀티폴더 포맷
        dfs, score_dfs = [], []
        for ov in overview_files[:10]:
            tmp = _read_csv_safe(ov)
            if tmp is not None:
                dfs.append(tmp)
            sc_path = ov.parent / "maps_scores.csv"
            if sc_path.exists():
                sc = _read_csv_safe(sc_path)
                if sc is not None:
                    score_dfs.append(sc)
        if not dfs:
            return None, None, "ryanluong"
        main_df   = pd.concat(dfs, ignore_index=True)
        scores_df = pd.concat(score_dfs, ignore_index=True) if score_dfs else None
        return main_df, scores_df, "ryanluong"

    # piyush 포맷: detailed_matches_player_stats.csv (stat_type='map' 행만 사용)
    detailed_files = list(path.rglob("detailed_matches_player_stats.csv"))
    if detailed_files:
        dfs = []
        for f in detailed_files[:30]:
            tmp = _read_csv_safe(f)
            if tmp is not None and "stat_type" in tmp.columns:
                map_rows = tmp[tmp["stat_type"] == "map"]
                if len(map_rows) > 0:
                    dfs.append(map_rows)
        if dfs:
            return pd.concat(dfs, ignore_index=True), None, "piyush"

    # 단일 CSV 포맷
    csv_files = [f for f in path.glob("*.csv") if "description" not in f.name.lower()]
    if not csv_files:
        csv_files = list(path.glob("*/*.csv"))[:5]
    if not csv_files:
        return None, None, "unknown"
    dfs = [_read_csv_safe(f) for f in csv_files[:3]]
    dfs = [d for d in dfs if d is not None]
    if not dfs:
        return None, None, "single-csv"
    main_df = pd.concat(dfs, ignore_index=True)
    return main_df, None, "single-csv"


# ── Hard Gate 검사 함수 ────────────────────────────────────────────────────────

def h1_required_columns(schema: dict) -> tuple[bool, str]:
    missing = []
    if not schema["agent_col"]:
        missing.append("agent")
    if not schema["map_col"]:
        missing.append("map")
    win_ok = bool(schema["win_col"]) or (bool(schema["score_a_col"]) and bool(schema["score_b_col"]))
    if not win_ok:
        missing.append("승패(score 쌍 또는 win 컬럼)")
    if missing:
        return False, "누락: " + ", ".join(missing)
    return True, (f"agent={schema['agent_col']}, map={schema['map_col']}, "
                  f"win={'score 쌍' if schema['score_a_col'] else schema['win_col']}")


def h2_team_reconstruction(
    df: pd.DataFrame, schema: dict, sample_n: int = 2000
) -> tuple[bool, str]:
    agent_col = schema["agent_col"]
    if not agent_col or agent_col not in df.columns:
        return False, "agent 컬럼 없음"

    sample = df.head(sample_n)
    valid_rate = sample[agent_col].apply(lambda x: normalize_agent(str(x)) is not None).mean()

    # 그룹별 5명 구성 확인 시도
    five_ratio = None
    for gcols in [
        ["match_id", "game_id"],
        ["match_id", "map_name", "player_team"],   # piyush
        ["Match Name", "Map", "Team"],
        ["match-datetime", "map", "player-team"],
        ["Match Name", "Map"],
    ]:
        avail = [c for c in gcols if c in sample.columns]
        if len(avail) >= 2:
            try:
                sizes = sample.groupby(avail)[agent_col].count()
                five_ratio = (sizes == 5).mean()
                break
            except Exception:
                pass

    passed = valid_rate >= 0.50
    detail = f"요원 정규화 통과율={valid_rate:.1%}"
    if five_ratio is not None:
        detail += f", 5인 그룹 비율={five_ratio:.1%}"
    return passed, detail


def h3_map_coverage(df: pd.DataFrame, schema: dict) -> tuple[bool, str]:
    map_col = schema["map_col"]
    if not map_col or map_col not in df.columns:
        return False, "map 컬럼 없음"
    normed = df[map_col].dropna().apply(lambda x: normalize_map(str(x)))
    pass_rate   = normed.notna().mean()
    unique_maps = int(normed.dropna().nunique())
    passed = pass_rate >= 0.60 and unique_maps >= 6
    return passed, f"맵 정규화 통과율={pass_rate:.1%}, 고유 맵={unique_maps}종 발견"


def h4_nontie_scores(
    df: pd.DataFrame, schema: dict, scores_df: pd.DataFrame | None
) -> tuple[bool, str]:
    # ryanluong: maps_scores.csv에서 점수 확인
    check_df = scores_df if scores_df is not None else df
    s_a = _find_col(list(check_df.columns), SCORE_A_HINTS) if check_df is not df else schema["score_a_col"]
    s_b = _find_col(list(check_df.columns), SCORE_B_HINTS) if check_df is not df else schema["score_b_col"]

    if s_a and s_b and s_a in check_df.columns and s_b in check_df.columns:
        a = pd.to_numeric(check_df[s_a], errors="coerce")
        b = pd.to_numeric(check_df[s_b], errors="coerce")
        valid = a.notna() & b.notna()
        if valid.any():
            nontie = (a[valid] != b[valid]).mean()
            return nontie >= 0.80, f"비무승부 비율={nontie:.1%}"

    win_col = schema["win_col"]
    if win_col and win_col in df.columns:
        n_unique = df[win_col].dropna().nunique()
        return n_unique >= 2, f"승패 컬럼 존재 (고유값={n_unique}종)"

    return False, "score 쌍 또는 win 컬럼 없음"


def h5_missing_rate(df: pd.DataFrame, schema: dict) -> tuple[bool, str]:
    core_stats = ["ACS", "KD", "KAST", "ADR"]
    results = []
    for stat in core_stats:
        col = schema["stat_cols"].get(stat)
        if col and col in df.columns:
            miss = float(df[col].isna().mean())
            results.append((stat, miss))
        else:
            results.append((stat, 1.0))

    pass_count = sum(1 for _, m in results if m < 0.30)
    detail = "결측률: " + ", ".join(f"{n}={m:.0%}" for n, m in results)
    detail += f" → {pass_count}/4 통과"
    return pass_count >= 2, detail


def h6_pro_match(path: Path, df: pd.DataFrame) -> tuple[bool, str]:
    path_str = str(path).lower()
    for kw in RANKED_KEYWORDS:
        if kw in path_str:
            return False, f"거부 키워드: '{kw}' (경로명)"
    for event_col in ("event", "tournament", "Tournament", "league"):
        if event_col in df.columns:
            vals = df[event_col].dropna().astype(str).str.lower()
            for kw in RANKED_KEYWORDS:
                if vals.str.contains(kw, na=False).any():
                    return False, f"거부 키워드: '{kw}' (컬럼={event_col})"
    return True, "랭크/캐주얼 키워드 미발견"


# ── Soft Score ────────────────────────────────────────────────────────────────

def compute_soft_score(
    df: pd.DataFrame,
    schema: dict,
    hard_results: list[tuple[bool, str]],
    processed_dir: Path | None,
) -> dict[str, float]:
    scores: dict[str, float] = {}

    # S1. 파이프라인 통과율 추정 (30점): Hard Gate H2~H4 통과 비율 기반
    h2_ok, h3_ok, h4_ok = hard_results[1][0], hard_results[2][0], hard_results[3][0]
    scores["파이프라인 통과율 (추정)"] = round((h2_ok + h3_ok + h4_ok) / 3.0 * 30, 1)

    # S2. 신규 기여율 (25점)
    # 정확한 측정은 파이프라인 실행 후 dedup_key 차집합이 필요하므로 여기서는 추정값을 사용한다.
    # processed 데이터가 있으면 기존 소스와 일부 중복 가능 → 보수적으로 12.5점(중간값) 부여.
    # processed 데이터가 없으면 전량 신규 기여로 간주 → 25점 부여.
    if processed_dir and (processed_dir / "matches_clean.csv").exists():
        print("[NOTE] 신규 기여율: 정확한 측정은 파이프라인 실행 후 dedup_key 비교가 필요합니다 — 보수적 추정값(12.5/25) 적용")
        scores["신규 기여율"] = 12.5
    else:
        scores["신규 기여율"] = 25.0

    # S3. 요원 커버리지 (15점)
    agent_col = schema["agent_col"]
    if agent_col and agent_col in df.columns:
        normed = df[agent_col].dropna().apply(lambda x: normalize_agent(str(x)))
        scores["요원 커버리지"] = round(normed.dropna().nunique() / 27 * 15, 1)
    else:
        scores["요원 커버리지"] = 0.0

    # S4. 맵 커버리지 (10점)
    map_col = schema["map_col"]
    if map_col and map_col in df.columns:
        normed_maps = df[map_col].dropna().apply(lambda x: normalize_map(str(x)))
        scores["맵 커버리지"] = round(normed_maps.dropna().nunique() / 12 * 10, 1)
    else:
        scores["맵 커버리지"] = 0.0

    # S5. 연도 다양성 (10점): 2024 이상 날짜 데이터 포함 여부
    has_recent = False
    date_cols = [c for c in df.columns if any(k in c.lower() for k in ("date", "datetime", "year"))]
    for dc in date_cols[:2]:
        try:
            vals = pd.to_datetime(df[dc], errors="coerce").dropna()
            if not vals.empty and (vals.dt.year >= 2024).any():
                has_recent = True
                break
        except Exception:
            pass
    scores["연도 다양성 (2024+)"] = 10.0 if has_recent else 0.0

    # S6. 스탯 풍부도 (10점): 7개 스탯 중 몇 개나 컬럼이 있는지
    found = sum(1 for col in schema["stat_cols"].values() if col is not None)
    scores["스탯 풍부도"] = 10.0 if found >= 6 else (6.0 if found >= 4 else 0.0)

    return scores


# ── 메인 검증 로직 ─────────────────────────────────────────────────────────────

def validate(path: Path, processed_dir: Path | None) -> int:
    print(f"\n{'='*64}")
    print(f"  데이터셋 검증: {path.name}")
    print(f"{'='*64}")

    main_df, scores_df, fmt = _load_dataset(path)
    if main_df is None:
        print("[ERROR] CSV 파일을 찾거나 읽을 수 없습니다.")
        return 1

    print(f"[FORMAT] {fmt}  |  샘플 {len(main_df):,}행 × {len(main_df.columns)}컬럼")

    # 즉시 기각 조건: 행 수 < 1000
    if len(main_df) < 1000:
        print(f"[즉시 거부] 행 수 {len(main_df)} < 1,000 — 너무 적은 데이터")
        return 1

    schema = _detect_schema(main_df, scores_df)
    print(f"[탐지 컬럼] agent={schema['agent_col']} | map={schema['map_col']} | "
          f"scoreA={schema['score_a_col']} | scoreB={schema['score_b_col']} | "
          f"win={schema['win_col']}")

    # ── Hard Gate 검사 ─────────────────────────────────────────────────────────
    print(f"\n{'─'*64}")
    print("  Hard Gate 검사 (6개 모두 PASS 필수)")
    print(f"{'─'*64}")

    gate_funcs = [
        ("H1", "필수 컬럼 존재",   lambda: h1_required_columns(schema)),
        ("H2", "5v5 팀 구성 복원", lambda: h2_team_reconstruction(main_df, schema)),
        ("H3", "공식 맵 커버리지", lambda: h3_map_coverage(main_df, schema)),
        ("H4", "승패 확정 가능",   lambda: h4_nontie_scores(main_df, schema, scores_df)),
        ("H5", "핵심 스탯 결측률", lambda: h5_missing_rate(main_df, schema)),
        ("H6", "프로/준프로 경기", lambda: h6_pro_match(path, main_df)),
    ]

    hard_results: list[tuple[bool, str]] = []
    pass_count = 0
    for code, name, fn in gate_funcs:
        passed, detail = fn()
        hard_results.append((passed, detail))
        icon = "✅ PASS" if passed else "❌ FAIL"
        print(f"  [{code}] {name:20s}  {icon}   {detail}")
        if passed:
            pass_count += 1

    all_passed = pass_count == 6
    print(f"\n  결과: {pass_count}/6 통과  {'✅ ALL PASS' if all_passed else '❌ HARD GATE 실패'}")

    # ── Soft Score ─────────────────────────────────────────────────────────────
    total_soft = 0.0
    if all_passed:
        soft = compute_soft_score(main_df, schema, hard_results, processed_dir)

        print(f"\n{'─'*64}")
        print("  Soft Score (채택 우선순위)")
        print(f"{'─'*64}")
        for item, score in soft.items():
            max_s = SOFT_MAX.get(item, 10)
            filled = int(score / max_s * 12)
            bar = "█" * filled + "░" * (12 - filled)
            print(f"  {item:28s}  {score:5.1f}/{max_s:2d}  [{bar}]")
            total_soft += score
        print(f"\n  합계: {total_soft:.1f}/100")

    # ── 최종 권고 ──────────────────────────────────────────────────────────────
    print(f"\n{'─'*64}")
    if not all_passed:
        print(f"  [권고] ❌ 거부  (Hard Gate {6-pass_count}개 실패)")
        return 1
    elif total_soft >= 50:
        print(f"  [권고] ✅ 채택  (Soft {total_soft:.0f}/100 ≥ 50점)")
        print("          → 파서 추가 후 dataload.py 등록 권장")
        return 0
    elif total_soft >= 30:
        print(f"  [권고] ⚠️  조건부 채택  (Soft {total_soft:.0f}/100, 30~49점)")
        print("          → 파서 작성 공수 대비 효과 검토 필요")
        return 0
    else:
        print(f"  [권고] ❌ 거부  (Soft {total_soft:.0f}/100 < 30점)")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ValoPredictML 신규 데이터셋 파이프라인 적합성 검증기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python scripts/validate_dataset.py --path data/raw/kaggle/vct_2021_2023
  python scripts/validate_dataset.py --path data/raw/kaggle/some_new_dataset --processed data/processed
""",
    )
    parser.add_argument("--path", required=True, help="검증할 데이터셋 폴더 경로")
    parser.add_argument(
        "--processed", default=None,
        help="기존 processed 데이터 폴더 (신규 기여율 계산용, 선택)",
    )
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"[ERROR] 경로가 존재하지 않습니다: {path}")
        sys.exit(1)

    processed = Path(args.processed) if args.processed else None
    sys.exit(validate(path, processed))


if __name__ == "__main__":
    main()
