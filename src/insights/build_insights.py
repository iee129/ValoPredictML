"""인사이트 사전 집계: matches.csv → reports/insights/*.json

요원-맵 적합도(N) + 메타 조합(K)을 1회 집계해 JSON으로 저장한다.
모델 추론과 무관하며, FastAPI(valo_web_backend)는 이 JSON만 읽는다.
소스 계약은 모델과 동일하게 kaggle_* 만 사용한다.

Usage:
    python -m ml.insights.build_insights --input data/processed --output reports/insights
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

from ml.agent_roles import AGENT_ROLE_MAP
from ml.valorant import MAP_ORDER, normalize_agent, normalize_map

ROLES = ("duelist", "initiator", "controller", "sentinel")

# 적합도 판정 임계 (튜닝 가능)
P_HI, P_LO, N_MIN = 0.12, 0.03, 20
TOP_K = 5


def _agents(cell: object) -> list[str]:
    if not isinstance(cell, str):
        return []
    out = []
    for part in cell.split("|"):
        n = normalize_agent(part.strip())
        if n:
            out.append(n)
    return out


def _role_vec(agents: list[str]) -> tuple[int, int, int, int]:
    c = {r: 0 for r in ROLES}
    for a in agents:
        role = AGENT_ROLE_MAP.get(a, "").lower()
        if role in c:
            c[role] += 1
    return tuple(c[r] for r in ROLES)  # type: ignore[return-value]


def build(input_dir: str, output_dir: str) -> dict:
    df = pd.read_csv(f"{input_dir}/matches.csv", low_memory=False)
    if "source" in df.columns:
        df = df[df["source"].astype(str).str.startswith("kaggle_")]

    am_games: dict[tuple[str, str], int] = defaultdict(int)
    am_wins: dict[tuple[str, str], int] = defaultdict(int)
    map_matches: dict[str, int] = defaultdict(int)
    comp: dict[str, dict[tuple, int]] = defaultdict(lambda: defaultdict(int))

    for row in df.itertuples(index=False):
        mp = normalize_map(str(getattr(row, "map", "")))
        if not mp:
            continue
        try:
            label = int(getattr(row, "label"))
        except (TypeError, ValueError):
            continue
        a = _agents(getattr(row, "agents_a", None))
        b = _agents(getattr(row, "agents_b", None))
        win, lose = (a, b) if label == 1 else (b, a)
        map_matches[mp] += 1
        for ag in win:
            am_games[(mp, ag)] += 1
            am_wins[(mp, ag)] += 1
        for ag in lose:
            am_games[(mp, ag)] += 1
        comp[mp][_role_vec(win)] += 1

    # (1) agent_map_fit.json
    fit: dict[str, dict] = {}
    for mp in MAP_ORDER:
        if map_matches[mp] == 0:
            continue
        agents_out = []
        for ag in sorted({a for (m, a) in am_games if m == mp}):
            g = am_games[(mp, ag)]
            w = am_wins[(mp, ag)]
            pr = g / (2 * map_matches[mp])
            wr = w / g if g else 0.0
            if g >= N_MIN:
                verdict = "fit" if pr >= P_HI else ("weak" if pr < P_LO else "ok")
                source = "data"
            else:
                verdict, source = "ok", "rule"
            agents_out.append({
                "name": ag, "role": AGENT_ROLE_MAP.get(ag, "").lower(),
                "verdict": verdict, "pick_rate": round(pr, 4), "win_rate": round(wr, 4),
                "sample": g, "source": source,
            })
        fit[mp] = {"map_matches": map_matches[mp], "agents": agents_out}

    # (2) meta_comps.json
    metas: dict[str, dict] = {}
    for mp, dist in comp.items():
        total = sum(dist.values())
        top = sorted(dist.items(), key=lambda kv: -kv[1])[:TOP_K]
        metas[mp] = {
            "total_wins": total,
            "top": [{"comp": list(k), "win_share": round(v / total, 4)} for k, v in top],
        }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "agent_map_fit.json").write_text(
        json.dumps(fit, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "meta_comps.json").write_text(
        json.dumps(metas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  agent_map_fit: {len(fit)} maps")
    print(f"  meta_comps:    {len(metas)} maps")
    print(f"  → {out}")
    return {"fit_maps": len(fit), "meta_maps": len(metas)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/processed")
    ap.add_argument("--output", default="reports/insights")
    args = ap.parse_args()
    build(args.input, args.output)


if __name__ == "__main__":
    main()
