# 04. Pydantic 스키마 완전 정의

## 1. 스키마 파일 구조

```
backend/schemas/
├── predict.py    ← POST /predict 요청/응답
├── agents.py     ← GET /agents 응답
├── maps.py       ← GET /maps 응답
└── history.py    ← GET /history 응답
```

---

## 2. predict.py — 예측 요청/응답 스키마

```python
# backend/schemas/predict.py
"""POST /predict 요청 및 응답 Pydantic 스키마."""

from typing import List
from pydantic import BaseModel, field_validator, model_validator

# ── 유효한 맵 집합 ────────────────────────────────────────────────────────
VALID_MAPS: frozenset[str] = frozenset({
    "Bind", "Haven", "Split", "Ascent", "Icebox",
    "Breeze", "Fracture", "Pearl", "Lotus", "Sunset", "Abyss",
})


# ── 요청 스키마 ───────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    """팀 조합 승률 예측 요청."""

    map: str
    team_a: List[str]
    team_b: List[str]

    @field_validator("map")
    @classmethod
    def validate_map(cls, v: str) -> str:
        if v not in VALID_MAPS:
            raise ValueError(
                f"알 수 없는 맵: '{v}'. 유효한 맵: {sorted(VALID_MAPS)}"
            )
        return v

    @field_validator("team_a", "team_b")
    @classmethod
    def validate_team_size(cls, v: List[str]) -> List[str]:
        if len(v) != 5:
            raise ValueError(
                f"팀 구성은 정확히 5명이어야 합니다. (입력: {len(v)}명)"
            )
        return v

    @field_validator("team_b")
    @classmethod
    def validate_no_duplicate_agents(cls, v: List[str], info) -> List[str]:
        team_a: List[str] = info.data.get("team_a", [])
        all_agents = team_a + v
        seen: set[str] = set()
        duplicates: list[str] = []
        for agent in all_agents:
            if agent in seen:
                duplicates.append(agent)
            seen.add(agent)
        if duplicates:
            raise ValueError(f"중복 요원이 있습니다: {list(set(duplicates))}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "map": "Ascent",
                "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
                "team_b": ["Reyna", "Breach", "Omen", "Cypher", "Fade"],
            }
        }
    }


# ── 응답 서브스키마 ───────────────────────────────────────────────────────
class RoleCounts(BaseModel):
    """팀의 역할군별 인원수."""

    duelist:    int
    initiator:  int
    controller: int
    sentinel:   int
    unknown:    int = 0


# ── 응답 스키마 ───────────────────────────────────────────────────────────
class PredictResponse(BaseModel):
    """팀 조합 승률 예측 응답."""

    win_probability:     float       # 팀 A 승리 확률 (0.0 ~ 1.0)
    lose_probability:    float       # 팀 A 패배 확률 (= 1 - win_probability)
    confidence:          str         # "high" / "medium" / "low"
    team_a_role_counts:  RoleCounts
    team_b_role_counts:  RoleCounts
    feature_importance:  dict        # 피처명 → 중요도 (상위 5개)
    map:                 str
    model_version:       str

    model_config = {
        "json_schema_extra": {
            "example": {
                "win_probability": 0.673,
                "lose_probability": 0.327,
                "confidence": "medium",
                "team_a_role_counts": {
                    "duelist": 1, "initiator": 2,
                    "controller": 1, "sentinel": 1, "unknown": 0
                },
                "team_b_role_counts": {
                    "duelist": 1, "initiator": 2,
                    "controller": 1, "sentinel": 1, "unknown": 0
                },
                "feature_importance": {
                    "team_a_controller": 0.142,
                    "map_encoded": 0.121,
                },
                "map": "Ascent",
                "model_version": "1.0.0",
            }
        }
    }
```

---

## 3. agents.py — 요원 목록 응답 스키마

```python
# backend/schemas/agents.py
"""GET /agents 응답 Pydantic 스키마."""

from typing import List, Dict
from pydantic import BaseModel


class AgentInfo(BaseModel):
    """단일 요원 정보."""

    name:    str
    role:    str      # "Duelist" / "Initiator" / "Controller" / "Sentinel"
    role_kr: str      # "타격대" / "척후병" / "전략가" / "감시자"


class RoleInfo(BaseModel):
    """역할군 메타데이터."""

    name_kr:     str
    description: str
    count:       int


class AgentsResponse(BaseModel):
    """GET /agents 응답."""

    agents: List[AgentInfo]
    roles:  Dict[str, RoleInfo]
    total:  int

    model_config = {
        "json_schema_extra": {
            "example": {
                "agents": [
                    {"name": "Jett", "role": "Duelist", "role_kr": "타격대"},
                    {"name": "Sova", "role": "Initiator", "role_kr": "척후병"},
                ],
                "roles": {
                    "Duelist": {
                        "name_kr": "타격대",
                        "description": "돌파구를 만드는 공격형 역할",
                        "count": 7
                    }
                },
                "total": 26,
            }
        }
    }
```

---

## 4. maps.py — 맵 목록 응답 스키마

```python
# backend/schemas/maps.py
"""GET /maps 응답 Pydantic 스키마."""

from typing import List
from pydantic import BaseModel


class MapInfo(BaseModel):
    """단일 맵 정보."""

    name:     str         # 영어 이름 (POST /predict에서 사용)
    name_kr:  str         # 한국어 이름
    region:   str         # 지역/배경
    callouts: List[str]   # 주요 콜아웃 목록


class MapsResponse(BaseModel):
    """GET /maps 응답."""

    maps:  List[MapInfo]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "maps": [
                    {
                        "name": "Ascent",
                        "name_kr": "어센트",
                        "region": "Italy",
                        "callouts": ["A Main", "B Main", "Mid", "Catwalk", "Market"]
                    }
                ],
                "total": 11,
            }
        }
    }
```

---

## 5. history.py — 기록 응답 스키마

```python
# backend/schemas/history.py
"""GET /history 응답 Pydantic 스키마."""

from typing import List, Optional
from pydantic import BaseModel


class HistoryItem(BaseModel):
    """단일 예측 기록 항목."""

    id:              int
    created_at:      str        # ISO 8601 형식 (예: "2024-01-15T18:30:00+00:00")
    map:             str
    team_a_agents:   List[str]  # 5명
    team_b_agents:   List[str]  # 5명
    win_probability: float
    confidence:      str        # "high" / "medium" / "low"


class HistoryResponse(BaseModel):
    """GET /history 응답."""

    total:  int           # 필터 조건 기준 전체 레코드 수
    limit:  int           # 요청한 limit
    offset: int           # 요청한 offset
    items:  List[HistoryItem]

    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 142,
                "limit": 20,
                "offset": 0,
                "items": [
                    {
                        "id": 142,
                        "created_at": "2024-01-15T18:30:00+00:00",
                        "map": "Ascent",
                        "team_a_agents": ["Jett","Sova","Viper","Killjoy","Skye"],
                        "team_b_agents": ["Reyna","Breach","Omen","Cypher","Fade"],
                        "win_probability": 0.673,
                        "confidence": "medium",
                    }
                ],
            }
        }
    }
```

---

## 6. 스키마 단위 테스트

```python
# tests/unit/test_schemas.py
"""Pydantic 스키마 검증 단위 테스트."""

import pytest
from pydantic import ValidationError

from backend.schemas.predict import PredictRequest, PredictResponse, RoleCounts


# ── PredictRequest 검증 ────────────────────────────────────────────────────

class TestPredictRequestValidation:

    VALID = {
        "map": "Ascent",
        "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
        "team_b": ["Reyna","Breach","Omen","Cypher","Fade"],
    }

    def test_valid_request(self):
        req = PredictRequest(**self.VALID)
        assert req.map == "Ascent"
        assert len(req.team_a) == 5
        assert len(req.team_b) == 5

    def test_invalid_map_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PredictRequest(**{**self.VALID, "map": "INVALID_MAP"})
        assert "알 수 없는 맵" in str(exc_info.value)

    def test_team_size_too_small_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PredictRequest(**{**self.VALID, "team_a": ["Jett","Sova"]})
        assert "5명" in str(exc_info.value)

    def test_team_size_too_large_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PredictRequest(**{
                **self.VALID,
                "team_a": ["Jett","Sova","Viper","Killjoy","Skye","Reyna"]
            })
        assert "5명" in str(exc_info.value)

    def test_duplicate_agent_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PredictRequest(**{
                **self.VALID,
                "team_b": ["Jett","Breach","Omen","Cypher","Fade"],  # Jett 중복
            })
        assert "중복" in str(exc_info.value)

    @pytest.mark.parametrize("map_name", [
        "Bind","Haven","Split","Ascent","Icebox",
        "Breeze","Fracture","Pearl","Lotus","Sunset","Abyss"
    ])
    def test_all_valid_maps_accepted(self, map_name):
        req = PredictRequest(**{**self.VALID, "map": map_name})
        assert req.map == map_name

    def test_missing_map_field_raises(self):
        with pytest.raises(ValidationError):
            PredictRequest(team_a=self.VALID["team_a"], team_b=self.VALID["team_b"])

    def test_missing_team_a_raises(self):
        with pytest.raises(ValidationError):
            PredictRequest(map="Ascent", team_b=self.VALID["team_b"])

    def test_empty_team_raises(self):
        with pytest.raises(ValidationError):
            PredictRequest(**{**self.VALID, "team_a": []})


# ── RoleCounts 검증 ────────────────────────────────────────────────────────

class TestRoleCounts:

    def test_valid_role_counts(self):
        rc = RoleCounts(duelist=1, initiator=2, controller=1, sentinel=1)
        assert rc.unknown == 0  # 기본값

    def test_unknown_defaults_to_zero(self):
        rc = RoleCounts(duelist=5, initiator=0, controller=0, sentinel=0)
        assert rc.unknown == 0


# ── PredictResponse 검증 ───────────────────────────────────────────────────

class TestPredictResponse:

    VALID_RESPONSE = {
        "win_probability": 0.673,
        "lose_probability": 0.327,
        "confidence": "medium",
        "team_a_role_counts": {"duelist":1,"initiator":2,"controller":1,"sentinel":1,"unknown":0},
        "team_b_role_counts": {"duelist":1,"initiator":2,"controller":1,"sentinel":1,"unknown":0},
        "feature_importance": {"map_encoded": 0.2},
        "map": "Ascent",
        "model_version": "1.0.0",
    }

    def test_valid_response(self):
        resp = PredictResponse(**self.VALID_RESPONSE)
        assert resp.win_probability == 0.673
        assert resp.confidence == "medium"

    def test_win_lose_sum(self):
        resp = PredictResponse(**self.VALID_RESPONSE)
        assert abs(resp.win_probability + resp.lose_probability - 1.0) < 0.001
```

---

## 7. 스키마 검증 흐름

```
클라이언트 요청 JSON
    ↓
FastAPI 자동 파싱 (request body → dict)
    ↓
Pydantic PredictRequest 검증
    ├── field_validator("map") → VALID_MAPS 체크
    ├── field_validator("team_a") → len == 5 체크
    ├── field_validator("team_b") → len == 5 체크
    └── field_validator("team_b") → 중복 요원 체크
         ↓ 실패 시
         ValidationError → FastAPI가 422 응답으로 변환
         ↓ 성공 시
         PredictRequest 인스턴스 → 라우터 핸들러로 전달
```
