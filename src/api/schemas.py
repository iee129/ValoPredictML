"""Pydantic v2 요청/응답 스키마. docs/08_web/02_backend_fastapi/04_schemas.md 기준."""
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


class Lineup(BaseModel):
    team_a: list[Slot]
    team_b: list[Slot]


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
    model: dict                           # {"contract":"advanced","n_features":179}
    explanations: list[Explanation] = []
    balance: dict[str, list[BalanceWarning]] = {}
    lineup: Lineup | None = None
    history_id: str | None = None
    created_at: str | None = None
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


# ── GET /history ─────────────────────────────────────
class HistoryItem(BaseModel):
    id: str
    created_at: str
    map: str
    cutoff_year: int
    predicted_winner: str
    confidence: float
    team_a_name: str
    team_b_name: str
    team_a_win_probability: float
    team_b_win_probability: float
    team_a_players: list[str]
    team_b_players: list[str]
    team_a_agents: list[str]
    team_b_agents: list[str]


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


class HistoryDetailResponse(BaseModel):
    item: HistoryItem
    request: PredictRequest
    result: PredictResponse


# ── 인사이트 ──────────────────────────────────────────
# ── GET /model 확장 스키마 ─────────────────────────────
class PerModelMetrics(BaseModel):
    name: str
    train_auc: float | None = None
    test_auc: float | None = None
    acc: float | None = None
    f1: float | None = None
    confusion_matrix: list[list[int]] | None = None


class ModelEval(BaseModel):
    primary_auc: float | None = None
    primary_label: str | None = None
    secondary_auc: float | None = None
    secondary_label: str | None = None
    random_auc: float | None = None
    chrono_auc: float | None = None
    note: str | None = None


class CVFold(BaseModel):
    name: str
    auc: float


class AgentMetaYear(BaseModel):
    year: int
    agent: str
    agent_key: str
    pick_rate: float
    win_rate: float
    sample: int


class FeatureGroupTopFeature(BaseModel):
    feature: str
    importance: float
    label: str


class FeatureGroupImportance(BaseModel):
    group: str
    label: str
    importance: float
    share: float
    top_features: list[FeatureGroupTopFeature]


class ConfidenceBin(BaseModel):
    bin: str
    lower: float
    upper: float
    count: int
    accuracy: float
    avg_confidence: float


class ModelEda(BaseModel):
    target_dist: list[dict] | None = None
    map_counts: list[dict] | None = None
    kd_winrate: list[dict] | None = None
    role_meta_by_year: list[dict] | None = None
    agent_meta_by_year: list[AgentMetaYear] | None = None


# ── /options, /agents, /maps ──────────────────────────
class CompMatchRequest(BaseModel):
    map: str
    agents: conlist(str, min_length=5, max_length=5)  # type: ignore[valid-type]


class AgentFit(BaseModel):
    name: str
    role: Literal["duelist", "initiator", "controller", "sentinel"]
    verdict: Literal["fit", "ok", "weak"]
    pick_rate: float | None = None
    win_rate: float | None = None
    sample: int = 0
    source: Literal["data", "rule"]


class AgentMapFitResponse(BaseModel):
    map: str
    agents: list[AgentFit]


class CompMatchResponse(BaseModel):
    map: str
    match_pct: float
    weighted_pct: float
    user_comp: RoleCounts
    nearest_comp: RoleCounts
    nearest_win_share: float
    message: str
