"""Pydantic v2 요청/응답 스키마. docs_web/02_backend_fastapi/04_schemas.md 기준."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, conlist


# ── POST /predict 요청 ────────────────────────────────
class Slot(BaseModel):
    player: str = Field(min_length=1)   # 선수 식별자 (모델 이전연도 조회 키, 필수)
    agent: str = Field(min_length=1)    # 요원명 (29종)


class PredictRequest(BaseModel):
    map: str
    cutoff_year: int = Field(ge=2000, le=2099)
    team_a: conlist(Slot, min_length=5, max_length=5)  # type: ignore[valid-type]
    team_b: conlist(Slot, min_length=5, max_length=5)  # type: ignore[valid-type]


# ── 예측 응답 ─────────────────────────────────────────
class TeamProb(BaseModel):
    name: str
    win_probability: float


class FeatureContribution(BaseModel):
    feature: str          # 실제 컬럼명 (FEATURE_COLS_ADVANCED)
    label: str            # feature_label(feature) — 한국어
    value: float
    importance: float
    contribution: float


class RoleCounts(BaseModel):
    duelist: float = 0.0
    initiator: float = 0.0
    controller: float = 0.0
    sentinel: float = 0.0


class Explanation(BaseModel):              # 자연어 근거 (C)
    feature: str
    text: str
    magnitude: float


class BalanceWarning(BaseModel):           # 구성 결함 (G)
    code: str
    severity: Literal["high", "medium", "low"]
    message: str


class PredictResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())  # 'model' 필드 허용

    map: str | None = None
    cutoff_year: int | None = None
    predicted_winner: str                 # "A" | "B"
    predicted_label: int
    confidence: float
    team_a: TeamProb
    team_b: TeamProb
    role_counts: dict[str, RoleCounts]    # {"team_a":.., "team_b":..}
    top_features: list[FeatureContribution]
    model: dict                           # {"contract":"advanced","n_features":125}
    explanations: list[Explanation] = []
    balance: dict[str, list[BalanceWarning]] = {}
    # replay 전용
    match_key: str | None = None
    actual_label: int | None = None
    actual_winner: str | None = None
    hit: bool | None = None


# ── /options, /agents, /maps ──────────────────────────
class AgentOut(BaseModel):
    name: str
    role: str


class MapOut(BaseModel):
    name: str
    ko: str


# ── 인사이트 ──────────────────────────────────────────
class CompMatchRequest(BaseModel):
    map: str
    agents: conlist(str, min_length=5, max_length=5)  # type: ignore[valid-type]
