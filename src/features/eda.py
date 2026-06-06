"""
EDA + 모델 성능 시각화: data/processed/matches.csv → reports/baseline/eda/*.png

Usage:
    python -m features.eda
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

from domain.valorant import AGENTS_SORTED, ROLES, _AGENT_KEY_TO_ROLE, _agent_col_key, normalize_agent

OUTPUT_DIR = Path("reports/baseline/eda")
INPUT_CSV = Path("data/processed/matches.csv")

# ── 한글 폰트 설정 ──────────────────────────────────────────────────────────
def _setup_korean_font() -> None:
    candidates = [
        "Apple SD Gothic Neo", "AppleGothic",
        "Nanum Gothic", "NanumGothic", "Malgun Gothic", "gulim",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


# ── 요원 파싱 ────────────────────────────────────────────────────────────────
def _parse_agents(s: str | None) -> list[str]:
    if not s or not isinstance(s, str):
        return []
    result = []
    for part in s.split("|"):
        part = part.strip()
        if not part:
            continue
        norm = normalize_agent(part)
        if norm:
            result.append(norm)
    return result


def _save(fig: plt.Figure, name: str) -> None:
    path = OUTPUT_DIR / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {path}")


def _save_slide(fig: plt.Figure, name: str) -> None:
    """슬라이드 고정 크기 저장 — figsize 그대로 유지 (bbox_inches 없음, dpi=100)."""
    path = OUTPUT_DIR / f"{name}.png"
    fig.savefig(path, dpi=100)
    plt.close(fig)
    print(f"  → {path}")


# ── 차트 0: 데이터 정제 흐름 (모던 카드 스타일, 836×638 px) ─────────────────
def plot_data_pipeline(_df_unused: pd.DataFrame) -> None:
    """모던 카드+배지 스타일 파이프라인 다이어그램 (836×638 px)."""
    import matplotlib.patches as mpatches

    dpi = 100
    fig, ax = plt.subplots(figsize=(8.36, 6.38))
    fig.patch.set_facecolor("#f4f6f9")
    ax.set_facecolor("#f4f6f9")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7.6)
    ax.axis("off")

    # ── 헬퍼 ────────────────────────────────────────────────────────────
    def card(x, y, w, h, count, subtitle, bg, tc="white", radius=0.18):
        shadow = mpatches.FancyBboxPatch(
            (x + 0.06, y - 0.06), w, h,
            boxstyle=f"round,pad={radius}",
            facecolor="#c8ccd4", edgecolor="none", zorder=2, alpha=0.5,
        )
        ax.add_patch(shadow)
        body = mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle=f"round,pad={radius}",
            facecolor=bg, edgecolor="none", zorder=3,
        )
        ax.add_patch(body)
        ax.text(x + w / 2, y + h * 0.62, count,
                ha="center", va="center", fontsize=28, fontweight="bold",
                color=tc, zorder=4)
        ax.text(x + w / 2, y + h * 0.22, subtitle,
                ha="center", va="center", fontsize=13, color=tc,
                alpha=0.92, zorder=4)

    def down_arrow(cx, y_top, y_bot):
        ax.annotate("", xy=(cx, y_bot + 0.04), xytext=(cx, y_top - 0.04),
                    arrowprops=dict(arrowstyle="-|>", lw=2.0,
                                   color="#9aa5b4", mutation_scale=16),
                    zorder=2)

    def badge(x, y, txt, color):
        """제거 건수 배지."""
        bp = mpatches.FancyBboxPatch(
            (x - 0.02, y - 0.18), 2.5, 0.44,
            boxstyle="round,pad=0.07",
            facecolor=color, edgecolor="none", alpha=0.88, zorder=5,
        )
        ax.add_patch(bp)
        ax.text(x + 1.23, y + 0.04, txt,
                ha="center", va="center", fontsize=11,
                color="white", fontweight="bold", zorder=6)

    # ── 카드 ─────────────────────────────────────────────────────────────
    CX, CW, CH = 3.0, 4.0, 0.98   # 중앙 카드 공통 x·w·h
    MID = CX + CW / 2              # 화살표 중심 x

    card(CX, 6.40, CW, CH, "66,798 행", "Kaggle 단독 필터 적용", bg="#4c72b0")
    down_arrow(MID, 6.40, 5.62)
    badge(MID - 1.25, 5.95, "▼  결측·중복·이상치 14행 제거", "#e57373")

    card(CX, 4.65, CW, CH, "66,784 행", "정제 완료 ✓", bg="#43a86e")
    down_arrow(MID, 4.65, 4.03)
    ax.text(MID + 0.32, 4.34, "GroupKFold  70 / 15 / 15 분할",
            ha="left", va="center", fontsize=12, color="black", style="italic", zorder=4)

    # ── 분기선 ───────────────────────────────────────────────────────────
    ax.plot([1.75, 8.25], [4.03, 4.03], color="#9aa5b4", lw=1.8, zorder=2)
    ax.plot([MID, MID], [4.03, 4.65], color="#9aa5b4", lw=1.8, zorder=2)
    for cx2 in (1.75, MID, 8.25):
        ax.annotate("", xy=(cx2, 3.47), xytext=(cx2, 4.03),
                    arrowprops=dict(arrowstyle="-|>", lw=1.7,
                                   color="#9aa5b4", mutation_scale=14),
                    zorder=2)

    # ── 하단 3 카드 ──────────────────────────────────────────────────────
    for bx, cnt, lbl in [(0.4, "46,748", "train  70%"),
                          (3.7, "10,019", "val  15%"),
                          (6.9, "10,017", "test  15%")]:
        card(bx, 1.97, 2.6, 1.32, cnt, lbl, bg="#e07b3c")

    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    out = OUTPUT_DIR / "00_data_pipeline.png"
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
    print(f"  → {out}")


# ── 차트 1: 결측치·중복·이상치 실제 분포 시각화 (836×638 px) ─────────────────
def plot_missing(df: pd.DataFrame) -> None:
    """결측치·중복·이상치 사전 분석 결과 — 3패널 실제 데이터 분포 (836×638 px, dpi=100).

    패널 구성:
      ① 왼쪽(전체 높이): 컬럼별 결측률 가로 막대
      ② 오른쪽 위       : 중복 데이터 원본 vs 정제 후 막대
      ③ 오른쪽 아래      : 스코어 합산 분포 (이상치 체크)
    """
    import matplotlib.ticker as mticker

    dpi = 100
    fig = plt.figure(figsize=(8.36, 6.38))
    fig.patch.set_facecolor("#f8f9fb")

    gs = fig.add_gridspec(
        2, 2,
        left=0.15, right=0.97,
        top=0.89, bottom=0.10,
        wspace=0.48, hspace=0.58,
        width_ratios=[1.35, 1],
    )
    ax_miss = fig.add_subplot(gs[:, 0])
    ax_dup  = fig.add_subplot(gs[0, 1])
    ax_out  = fig.add_subplot(gs[1, 1])

    fig.suptitle("데이터 품질 검사 결과", fontsize=12, fontweight="bold", y=0.97)

    # ── ① 결측치: 컬럼별 결측률 ─────────────────────────────────────────
    miss_rates = df.isnull().mean() * 100
    miss_sorted = miss_rates.sort_values(ascending=True)
    max_miss = miss_sorted.max() if miss_sorted.max() > 0 else 1.0

    bar_colors = ["#e57373" if v > 0 else "#a8d8ae" for v in miss_sorted.values]
    ax_miss.barh(range(len(miss_sorted)), miss_sorted.values,
                 color=bar_colors, edgecolor="white", height=0.62)
    ax_miss.set_yticks(range(len(miss_sorted)))
    ax_miss.set_yticklabels(miss_sorted.index, fontsize=8)
    ax_miss.set_xlabel("결측률 (%)", fontsize=9)
    ax_miss.set_title("① 결측치 — 컬럼별 결측률", fontsize=10, fontweight="bold", pad=6)
    ax_miss.grid(axis="x", alpha=0.3)
    ax_miss.set_xlim(0, max_miss * 1.38)

    for i, v in enumerate(miss_sorted.values):
        if v > 0:
            ax_miss.text(v + max_miss * 0.03, i, f"{v:.1f}%",
                        va="center", fontsize=9, color="#c0392b", fontweight="bold")

    # 0% 컬럼 수 요약 annotation
    zero_cols = int((miss_rates == 0).sum())
    ax_miss.text(0.98, 0.02, f"나머지 {zero_cols}개 컬럼: 결측 0%",
                transform=ax_miss.transAxes, ha="right", va="bottom",
                fontsize=8, color="#27ae60",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0fff4",
                          edgecolor="#27ae60", alpha=0.85))

    # ── ② 중복 데이터: 원본 vs 정제 후 ─────────────────────────────────
    _rejects_path = Path("data/processed/rejects.csv")
    dup_count = 1_187
    miss_count = 4
    if _rejects_path.exists():
        _r = pd.read_csv(_rejects_path)
        _rk = _r[_r["source"].str.startswith("kaggle", na=False)]
        dup_count = int(_rk[_rk["reason"] == "dedup_lower_priority"].shape[0])
        miss_count = int(_rk[_rk["reason"] == "player_count_not_5v5"].shape[0])

    total_before = len(df) + dup_count + miss_count
    cats = ["Kaggle 원본\n(정제 전)", "정제 후"]
    vals = [total_before, len(df)]
    bar2 = ax_dup.bar(cats, vals, color=["#e57373", "#4c72b0"],
                      edgecolor="white", width=0.52)
    ax_dup.set_ylabel("경기 수", fontsize=8)
    ax_dup.set_title(f"② 중복 — {dup_count:,}건 탐지·제거",
                    fontsize=10, fontweight="bold", pad=6)
    ax_dup.set_ylim(0, max(vals) * 1.22)
    ax_dup.grid(axis="y", alpha=0.3)
    ax_dup.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{int(x/1000)}k" if x >= 1000 else str(int(x)))
    )
    for b, v in zip(bar2, vals):
        ax_dup.text(b.get_x() + b.get_width() / 2,
                   b.get_height() + max(vals) * 0.012,
                   f"{v:,}", ha="center", fontsize=8.5, fontweight="bold")
    # 감소량 표시
    diff = total_before - len(df)
    mid_x = (bar2[0].get_x() + bar2[0].get_width() / 2
             + bar2[1].get_x() + bar2[1].get_width() / 2) / 2
    ax_dup.text(mid_x, (vals[0] + vals[1]) / 2 * 0.88,
               f"-{diff:,}",
               ha="center", fontsize=9, color="#c0392b", fontweight="bold",
               bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                         edgecolor="#e57373", alpha=0.92))

    # ── ③ 이상치: 스코어 합산 분포 ──────────────────────────────────────
    if "score_a" in df.columns and "score_b" in df.columns:
        score_sum = (df["score_a"].fillna(0) + df["score_b"].fillna(0)).astype(int)
        zero_count = int((score_sum == 0).sum())

        ax_out.hist(score_sum, bins=22, color="#4c72b0",
                   edgecolor="white", linewidth=0.5)
        ax_out.axvline(0, color="#e05c5c", linestyle="--", lw=1.8,
                      label="합산 0 기준선")
        # 이상치 0건 annotation
        label_txt = f"이상치 {zero_count}건 ✓" if zero_count == 0 else f"이상치 {zero_count:,}건 !"
        label_color = "#27ae60" if zero_count == 0 else "#c0392b"
        ax_out.text(0.97, 0.93, label_txt,
                   transform=ax_out.transAxes, ha="right", va="top",
                   fontsize=9, color=label_color, fontweight="bold",
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                             edgecolor=label_color, alpha=0.9))
        ax_out.set_xlabel("스코어 합산", fontsize=8.5)
        ax_out.set_ylabel("경기 수", fontsize=8.5)
        ax_out.set_title("③ 이상치 — 스코어 합산 분포",
                        fontsize=10, fontweight="bold", pad=6)
        ax_out.legend(fontsize=8, loc="upper left")
        ax_out.grid(axis="y", alpha=0.3)
        ax_out.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: f"{int(x/1000)}k" if x >= 1000 else str(int(x)))
        )

    out = OUTPUT_DIR / "01_missing_values.png"
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
    print(f"  → {out}")


# ── 차트 4: 레이블 분포 ─────────────────────────────────────────────────────
def plot_label_dist(df: pd.DataFrame) -> None:
    counts = df["label"].value_counts().sort_index()
    labels = ["패배 (0)", "승리 (1)"]
    colors = ["#e05c5c", "#55a868"]

    fig, ax = plt.subplots(figsize=(8.30, 3.75))
    wedges, texts, autotexts = ax.pie(
        counts.values, labels=labels, autopct="%1.1f%%",
        colors=colors, startangle=90,
    )
    ax.set_title(f"승/패 레이블 분포 (총 {len(df):,}경기)")
    fig.tight_layout()
    _save_slide(fig, "04_label_distribution")


# ── 차트 5: 맵별 경기 수 ────────────────────────────────────────────────────
def plot_map_dist(df: pd.DataFrame) -> None:
    counts = df["map"].value_counts().sort_values()
    fig, ax = plt.subplots(figsize=(8.30, 3.75))
    bars = ax.barh(counts.index, counts.values, color="#4c72b0")
    ax.set_xlabel("경기 수")
    ax.set_title("맵별 경기 수")
    for bar, v in zip(bars, counts.values):
        ax.text(v + 50, bar.get_y() + bar.get_height() / 2,
                f"{v:,}", va="center", fontsize=9)
    fig.tight_layout()
    _save_slide(fig, "05_map_distribution")


# ── 차트 6: 연도별 요원 메타 시프트 (Top 10 히트맵) ─────────────────────────
def plot_meta_shift(df: pd.DataFrame) -> None:
    if "year" not in df.columns:
        return

    years = sorted(int(y) for y in df["year"].dropna().unique())
    if not years:
        return

    # 연도 × 요원 픽 카운트
    counts: dict[tuple[int, str], int] = {}
    yearly_totals: dict[int, int] = {}
    for _, row in df[["year", "agents_a", "agents_b"]].dropna(subset=["year"]).iterrows():
        y = int(row["year"])
        yearly_totals[y] = yearly_totals.get(y, 0) + 2  # 맵당 2팀
        for col in ("agents_a", "agents_b"):
            for agent in _parse_agents(row[col]):
                counts[(y, agent)] = counts.get((y, agent), 0) + 1

    # 전체 픽률 Top 10 요원 선정
    overall: dict[str, int] = {}
    for (_, agent), c in counts.items():
        overall[agent] = overall.get(agent, 0) + c
    top_agents = [a for a, _ in sorted(overall.items(), key=lambda x: -x[1])[:10]]

    # 픽률 매트릭스
    matrix = []
    for agent in top_agents:
        row = []
        for y in years:
            total = yearly_totals.get(y, 1)
            row.append(counts.get((y, agent), 0) / total * 100)
        matrix.append(row)

    fig, ax = plt.subplots(figsize=(8.30, 3.75))
    im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", interpolation="nearest")
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years)
    ax.set_yticks(range(len(top_agents)))
    ax.set_yticklabels(top_agents, fontsize=10)
    ax.set_xlabel("연도")
    ax.set_title("연도별 요원 메타 시프트 (Top 10 픽률 %)")
    for i, agent in enumerate(top_agents):
        for j, y in enumerate(years):
            v = matrix[i][j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                    fontsize=8, color="white" if v > 40 else "black")
    fig.colorbar(im, ax=ax, label="픽률 (%)")
    fig.tight_layout()
    _save_slide(fig, "06_meta_shift_by_year")


# ── 차트 7: 역할군 비율 시간 변화 (특성 EDA) ─────────────────────────────────
def plot_role_shift(df: pd.DataFrame) -> None:
    """역할군 비율 시간 변화 — 선 그래프 (슬라이드 6 특성 EDA)."""
    if "year" not in df.columns:
        return

    years = sorted(int(y) for y in df["year"].dropna().unique())
    role_kr = {
        "duelist": "타격대", "Duelist": "타격대",
        "initiator": "척후대", "Initiator": "척후대",
        "controller": "전략가", "Controller": "전략가",
        "sentinel": "감시자", "Sentinel": "감시자",
    }
    yearly_role: dict[tuple[int, str], int] = {}
    yearly_total: dict[int, int] = {}

    for _, row in df[["year", "agents_a", "agents_b"]].dropna(subset=["year"]).iterrows():
        y = int(row["year"])
        for col in ("agents_a", "agents_b"):
            for agent in _parse_agents(row[col]):
                key = _agent_col_key(agent)
                role = _AGENT_KEY_TO_ROLE.get(key)
                if not role:
                    continue
                yearly_role[(y, role)] = yearly_role.get((y, role), 0) + 1
                yearly_total[y] = yearly_total.get(y, 0) + 1

    roles_unique = sorted({r for (_, r) in yearly_role.keys()})
    colors_map = {
        "initiator": "#4c72b0", "Initiator": "#4c72b0",
        "duelist":   "#e05c5c", "Duelist":   "#e05c5c",
        "controller":"#55a868", "Controller":"#55a868",
        "sentinel":  "#ffa500", "Sentinel":  "#ffa500",
    }

    fig, ax = plt.subplots(figsize=(8.30, 3.75))
    for role in roles_unique:
        ys = [yearly_role.get((y, role), 0) / yearly_total.get(y, 1) * 100 for y in years]
        ax.plot(years, ys, marker="o", linewidth=2.2,
                label=role_kr.get(role, role), color=colors_map.get(role, "#888"))

    ax.set_xlabel("연도", fontsize=10)
    ax.set_ylabel("역할군 비율 (%)", fontsize=10)
    ax.set_title("역할군 비율 시간 변화 — 연도별 메타 특성", fontsize=11, fontweight="bold")
    ax.set_xticks(years)
    ax.set_ylim(0, 40)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    _save_slide(fig, "07_role_shift_by_year")


# ── 차트 8: 출전 경험 차이 vs 승률 (1위 피처 사전 검증) ──────────────────────
def plot_prior_games_vs_winrate(_df_unused: pd.DataFrame) -> None:
    train = pd.read_csv("data/processed/train.csv", low_memory=False)
    col = "diff_prior_games_mean"
    if col not in train.columns:
        print(f"  [skip] {col} 컬럼 없음")
        return

    bins = pd.cut(train[col], bins=10)
    grouped = train.groupby(bins, observed=True)["label"].agg(["mean", "count"]).reset_index()
    grouped.columns = ["bin", "mean", "count"]

    fig, ax = plt.subplots(figsize=(8.30, 3.75))
    bars = ax.bar(range(len(grouped)), grouped["mean"] * 100,
                  color=["#a8c4d8" if c < 1000 else "#4c72b0" for c in grouped["count"]],
                  edgecolor="black", linewidth=0.5)
    ax.axhline(50, color="gray", linestyle="--", alpha=0.7, label="기준 50%")
    ax.set_xticks(range(len(grouped)))
    ax.set_xticklabels([f"{int(b.left)}~{int(b.right)}" for b in grouped["bin"]],
                       rotation=30, ha="right", fontsize=9)
    ax.set_xlabel("`diff_prior_games_mean` 구간 (출전 경험 차이)")
    ax.set_ylabel("승률 (%)")
    ax.set_title("출전 경험 차이 vs 승률 — 베이스라인 1위 피처 사전 검증")
    ax.set_ylim(0, 105)

    for bar, mean, count in zip(bars, grouped["mean"], grouped["count"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                f"{mean*100:.1f}%\n(n={count:,})", ha="center", fontsize=7.5)

    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    _save_slide(fig, "08_prior_games_vs_winrate")


# ── 차트 9: KD 비율 차이 vs 승률 (관계 EDA) ─────────────────────────────────
def plot_kd_vs_winrate(_df_unused: pd.DataFrame) -> None:
    """직전 KD 비율 차이 vs 승률 — 관계 EDA 두 번째 피처 검증 (슬라이드 7)."""
    train = pd.read_csv("data/processed/train.csv", low_memory=False)
    col = "diff_prior_kd_mean"
    if col not in train.columns:
        print(f"  [skip] {col} 컬럼 없음")
        return

    bins = pd.cut(train[col], bins=10)
    grouped = (
        train.groupby(bins, observed=True)["label"]
        .agg(["mean", "count"])
        .reset_index()
    )
    grouped.columns = ["bin", "mean", "count"]

    fig, ax = plt.subplots(figsize=(8.30, 3.75))
    bar_colors = ["#a8c4d8" if c < 1000 else "#4c72b0" for c in grouped["count"]]
    bars = ax.bar(range(len(grouped)), grouped["mean"] * 100,
                  color=bar_colors, edgecolor="black", linewidth=0.5)
    ax.axhline(50, color="gray", linestyle="--", alpha=0.7, label="기준 50%")
    ax.set_xticks(range(len(grouped)))
    ax.set_xticklabels(
        [f"{b.left:.2f}~{b.right:.2f}" for b in grouped["bin"]],
        rotation=30, ha="right", fontsize=8.5,
    )
    ax.set_xlabel("`diff_prior_kd_mean` 구간 (직전 KD 비율 차이)", fontsize=9)
    ax.set_ylabel("승률 (%)", fontsize=9)
    ax.set_title("KD 비율 차이 vs 승률 — Permutation 중요도 1위 피처 사전 검증",
                fontsize=10, fontweight="bold")
    ax.set_ylim(0, 105)

    for bar, mean, count in zip(bars, grouped["mean"], grouped["count"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                f"{mean * 100:.1f}%\n(n={count:,})", ha="center", fontsize=7.5)

    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    _save_slide(fig, "09_kd_vs_winrate")


# ── 차트 14: 선형 vs 비선형 결정 경계 개념도 (슬라이드 6 — 알고리즘 선택 근거) ──
def plot_linear_vs_nonlinear() -> None:
    """선형(로지스틱 회귀)과 비선형(RF·XGBoost·LightGBM) 결정 경계 비교 개념도."""
    np.random.seed(7)
    n = 80

    # 동심원 패턴: 승리(내부 원), 패배(외부 링)
    r_win = np.random.uniform(0, 1.3, n)
    th_win = np.random.uniform(0, 2 * np.pi, n)
    win = np.column_stack([r_win * np.cos(th_win), r_win * np.sin(th_win)])

    r_lose = np.random.uniform(2.0, 3.2, n)
    th_lose = np.random.uniform(0, 2 * np.pi, n)
    lose = np.column_stack([r_lose * np.cos(th_lose), r_lose * np.sin(th_lose)])

    c_win, c_lose = "#4c72b0", "#e05c5c"
    lim = 3.5

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 6.61))

    panels = [
        ("베이스라인 — 로지스틱 회귀\n직선 하나로만 구분 → 많은 패턴을 놓침", "linear"),
        ("심화 모델 — RF · XGBoost · LightGBM\n복잡한 경계로 숨겨진 패턴까지 학습", "nonlinear"),
    ]

    xx, yy = np.meshgrid(np.linspace(-lim, lim, 300), np.linspace(-lim, lim, 300))

    for ax, (title, mode) in zip(axes, panels):
        # 결정 영역 배경
        Z = np.sign(xx) if mode == "linear" else np.sign(1.6 - np.sqrt(xx**2 + yy**2))
        ax.contourf(xx, yy, Z, levels=[-2, 0, 2],
                    colors=[c_lose, c_win], alpha=0.13, zorder=1)

        # 데이터 포인트
        ax.scatter(win[:, 0], win[:, 1], c=c_win, s=22, alpha=0.85,
                   label="승리", zorder=3, edgecolors="white", linewidth=0.4)
        ax.scatter(lose[:, 0], lose[:, 1], c=c_lose, s=22, alpha=0.85,
                   marker="X", label="패배", zorder=3, edgecolors="white", linewidth=0.4)

        # 결정 경계선
        if mode == "linear":
            ax.axvline(0, color="black", lw=2.5, zorder=4, label="결정 경계")
        else:
            th = np.linspace(0, 2 * np.pi, 400)
            ax.plot(1.6 * np.cos(th), 1.6 * np.sin(th),
                    color="black", lw=2.5, zorder=4, label="결정 경계")

        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(title, fontsize=9.5, fontweight="bold", pad=8)
        ax.legend(loc="lower right", fontsize=8, framealpha=0.9)
        for sp in ax.spines.values():
            sp.set_linewidth(0.8)
            sp.set_color("#bbb")

    fig.text(0.5, 0.01,
             "※ 실제 데이터가 아닌 알고리즘 선택 근거를 설명하기 위한 개념도입니다",
             ha="center", fontsize=7.5, color="#999", style="italic")

    fig.tight_layout(pad=1.2, rect=[0, 0.05, 1, 1])
    _out = OUTPUT_DIR / "14_linear_vs_nonlinear.png"
    fig.savefig(_out, dpi=100)
    plt.close(fig)
    print(f"  → {_out}")


# ── 헬퍼: JSON 로드 ──────────────────────────────────────────────────────────
def _load_validation() -> dict:
    path = Path("reports/baseline/validation.json")
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


# ── 차트 10: Permutation Importance (AUC Drop, 상위 20개) ───────────────────
def plot_feature_importance_permutation(validation: dict) -> None:
    top = validation.get("permutation_top_features", [])[:20]
    if not top:
        print("  [skip] permutation_top_features 없음")
        return

    names = [f["feature"] for f in reversed(top)]
    means = [f["auc_drop_mean"] for f in reversed(top)]
    stds = [f["auc_drop_std"] for f in reversed(top)]

    fig, ax = plt.subplots(figsize=(8.38, 4.76))
    colors = ["#55a868" if i >= len(names) - 3 else "#a8d4b0" for i in range(len(names))]
    ax.barh(range(len(names)), means, xerr=stds,
            color=colors, ecolor="#333", capsize=3,
            edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=7.5)
    ax.set_xlabel("AUC 감소량 (평균 ± 표준편차) — 클수록 중요한 항목", fontsize=9)
    ax.set_title("항목별 실제 기여도 (제거 실험) — 상위 20개", fontsize=10)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    _out = OUTPUT_DIR / "10_feature_importance_permutation.png"
    fig.savefig(_out, dpi=100)
    plt.close(fig)
    print(f"  → {_out}")


# ── 차트 13: ROC Curve (모델 + test.csv 직접 로드) ───────────────────────────
def plot_roc_curve() -> None:
    model_path = Path("models/baseline/model.joblib")
    test_csv = Path("data/processed/test.csv")

    if not model_path.exists():
        print(f"  [skip] {model_path} 없음")
        return
    if not test_csv.exists():
        print(f"  [skip] {test_csv} 없음")
        return

    try:
        import joblib
        from sklearn.metrics import roc_curve, auc as sk_auc

        from features.preprocess import build_xy

        pipe = joblib.load(model_path)
        df_test = pd.read_csv(test_csv, low_memory=False)
        X_te, y_te, _ = build_xy(df_test)
        y_prob = pipe.predict_proba(X_te)[:, 1]

        fpr, tpr, _ = roc_curve(y_te, y_prob)
        roc_auc = sk_auc(fpr, tpr)

        # 무작위 기준: Youden J 최대 임계점
        j_scores = tpr - fpr
        best_idx = int(np.argmax(j_scores))

        fig, ax = plt.subplots(figsize=(8.38, 4.76))
        ax.plot(fpr, tpr, color="#4c72b0", lw=2.2,
                label=f"ROC 곡선  (AUC = {roc_auc:.4f})")
        ax.plot([0, 1], [0, 1], color="#aaa", linestyle="--", lw=1.5,
                label="무작위 기준선 — 동전 던지기 수준 (AUC = 0.5)")
        ax.scatter(fpr[best_idx], tpr[best_idx], color="#e05c5c", s=60, zorder=5,
                   label=f"최적 판정 기준점  (틀린 비율={fpr[best_idx]:.3f}, 맞힌 비율={tpr[best_idx]:.3f})")

        ax.set_xlabel("틀리게 예측한 비율", fontsize=11)
        ax.set_ylabel("제대로 맞힌 비율", fontsize=11)
        ax.set_title("ROC Curve — 베이스라인 모델", fontsize=12)
        ax.legend(loc="lower right", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        # 음영 처리
        ax.fill_between(fpr, tpr, alpha=0.08, color="#4c72b0")

        fig.tight_layout()
        _out = OUTPUT_DIR / "13_roc_curve.png"
        fig.savefig(_out, dpi=100)
        plt.close(fig)
        print(f"  → {_out}")

    except Exception as e:
        print(f"  [skip] ROC curve 생성 실패: {e}")


def main() -> None:
    _setup_korean_font()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading {INPUT_CSV}...")
    df = pd.read_csv(INPUT_CSV, low_memory=False)
    print(f"  {len(df):,}행 × {len(df.columns)}열 (raw)")

    df = df[df["source"].str.startswith("kaggle_")].reset_index(drop=True)
    print(f"  {len(df):,}행 (kaggle 단독; VLR.gg 등 제외)")

    print("\n[1/3] 데이터 탐색 차트 생성 중...")
    plot_data_pipeline(df)
    plot_missing(df)
    plot_label_dist(df)
    plot_map_dist(df)
    plot_meta_shift(df)
    plot_role_shift(df)
    plot_prior_games_vs_winrate(df)
    plot_kd_vs_winrate(df)

    print("\n[2/3] 알고리즘 선택 개념도 생성 중...")
    plot_linear_vs_nonlinear()

    print("\n[3/3] 모델 성능 시각화 차트 생성 중...")
    validation = _load_validation()

    if not validation:
        print("  ⚠️  reports/baseline/validation.json 없음 — 먼저 validate 실행 필요")

    plot_feature_importance_permutation(validation)
    plot_roc_curve()

    print(f"\n완료: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
