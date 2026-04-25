# 03. 맵 데이터베이스

## 1. 전체 맵 목록 (2025년 기준, 12개)

| 맵 코드 | 한국어 이름 | 출시 에피소드 | 특성 | 인코딩 |
|--------|----------|------------|------|--------|
| Ascent | 어센트 | EP 1 | 개방형, 균형 맵 | 0 |
| Bind | 바인드 | EP 1 | 텔레포터, 공격자 불리 | 1 |
| Haven | 헤이븐 | EP 1 | 사이트 3개, 수비자 불리 | 2 |
| Split | 스플릿 | EP 1 (한 번 제외됨) | 수직 구조 | 3 |
| Icebox | 아이스박스 | EP 1 Act 3 | 좁은 통로, Sentinel 유리 | 4 |
| Breeze | 브리즈 | EP 2 Act 3 | 장거리 교전, Operator 유리 | 5 |
| Fracture | 프랙처 | EP 3 Act 2 | 공격자 양방향 진입 | 6 |
| Pearl | 펄 | EP 5 Act 1 | 해저 도시, 균형 | 7 |
| Lotus | 로터스 | EP 6 Act 1 | 인도 사원, 사이트 3개 | 8 |
| Sunset | 선셋 | EP 7 Act 2 | 미국 거리, 균형 | 9 |
| Abyss | 어비스 | EP 9 Act 1 | 절벽 맵, 추락 존재 | 10 |
| Drift | 드리프트 | EP 10 Act 1 | 2025년 신규 | 11 |

---

## 2. 맵 표준화 코드

```python
# 유효한 맵 목록
VALID_MAPS: list[str] = [
    "Ascent", "Bind", "Haven", "Split", "Icebox", "Breeze",
    "Fracture", "Pearl", "Lotus", "Sunset", "Abyss", "Drift",
]

# 맵 인코딩 딕셔너리
MAP_TO_INDEX: dict[str, int] = {m: i for i, m in enumerate(VALID_MAPS)}
INDEX_TO_MAP: dict[int, str] = {i: m for i, m in enumerate(VALID_MAPS)}

# 맵 이름 변형 표준화
MAP_ALIASES: dict[str, str] = {
    "ascent":    "Ascent",
    "bind":      "Bind",
    "haven":     "Haven",
    "split":     "Split",
    "icebox":    "Icebox",
    "breeze":    "Breeze",
    "fracture":  "Fracture",
    "pearl":     "Pearl",
    "lotus":     "Lotus",
    "sunset":    "Sunset",
    "abyss":     "Abyss",
    "drift":     "Drift",
    # UUID/경로 형식 (Riot API)
    "/game/maps/ascent/ascent":        "Ascent",
    "/game/maps/port/duality":         "Bind",
    "/game/maps/triad/triad":          "Haven",
    "/game/maps/bonsai/bonsai":        "Split",
    "/game/maps/foxtrot/foxtrot":      "Icebox",
    "/game/maps/canyon/canyon":        "Breeze",
    "/game/maps/err/juliett":          "Fracture",
    "/game/maps/pitt/pitt":            "Pearl",
    "/game/maps/jam/jam":              "Lotus",
    "/game/maps/juliett/juliett":      "Sunset",
    "/game/maps/infinity/infinity":    "Abyss",
    "/game/maps/drift/drift":          "Drift",
}

def normalize_map(raw: str) -> str | None:
    """맵 이름/UUID → 표준 이름 변환"""
    if not raw:
        return None
    
    s = raw.strip()
    
    # 정확히 알려진 이름
    if s in VALID_MAPS:
        return s
    
    # 별칭 확인 (소문자 키)
    lower = s.lower()
    if lower in MAP_ALIASES:
        return MAP_ALIASES[lower]
    
    # Title case 시도
    titled = s.title()
    if titled in VALID_MAPS:
        return titled
    
    return None  # 알 수 없는 맵


def encode_map(map_name: str) -> int | None:
    """맵 이름 → 정수 인코딩"""
    normalized = normalize_map(map_name)
    if normalized is None:
        return None
    return MAP_TO_INDEX.get(normalized)
```

---

## 3. 맵별 역할군 선호도 (메타 통계)

> 아래 수치는 VCT 2022-2023 프로 씬 픽률 추정치. 실제 데이터 수집 후 업데이트 필요.

| 맵 | 선호 역할군 | 비선호 역할군 | 주요 이유 |
|----|-----------|-----------|---------|
| Ascent | Initiator, Controller | - | 균형 맵, 모든 역할군 적합 |
| Bind | Controller, Initiator | Duelist | 텔레포터 활용, 좁은 라인 |
| Haven | Duelist, Initiator | Sentinel | 사이트 3개, 빠른 이동 중요 |
| Split | Sentinel, Controller | Duelist | 수직 구조, 수비 설정 중요 |
| Icebox | Sentinel, Controller | Duelist | 좁은 통로, 디펜스 중요 |
| Breeze | Controller, Duelist | Sentinel | 장거리, 스모크+Operator |
| Fracture | Initiator, Controller | Sentinel | 양방향 진입 대응 필요 |
| Pearl | Controller, Initiator | - | 균형 맵 |
| Lotus | Controller, Sentinel | Duelist | 사이트 3개, 수비 중심 |
| Sunset | Duelist, Initiator | Sentinel | 공격적 맵 구조 |
| Abyss | Duelist, Controller | Sentinel | 개방형, 공격 유리 |
| Drift | 미확인 (2025 신규) | 미확인 | 데이터 부족 |

---

## 4. 맵별 피처 활용

```python
# 맵별 선호 역할군 가중치 (추후 피처로 활용 가능)
MAP_ROLE_WEIGHTS: dict[str, dict[str, float]] = {
    "Ascent":   {"Duelist": 1.0, "Initiator": 1.2, "Controller": 1.2, "Sentinel": 1.0},
    "Bind":     {"Duelist": 0.9, "Initiator": 1.2, "Controller": 1.3, "Sentinel": 1.0},
    "Haven":    {"Duelist": 1.2, "Initiator": 1.2, "Controller": 1.0, "Sentinel": 0.9},
    "Split":    {"Duelist": 0.9, "Initiator": 1.0, "Controller": 1.2, "Sentinel": 1.3},
    "Icebox":   {"Duelist": 0.8, "Initiator": 1.0, "Controller": 1.2, "Sentinel": 1.3},
    "Breeze":   {"Duelist": 1.1, "Initiator": 0.9, "Controller": 1.3, "Sentinel": 0.8},
    "Fracture": {"Duelist": 1.0, "Initiator": 1.3, "Controller": 1.2, "Sentinel": 0.8},
    "Pearl":    {"Duelist": 1.0, "Initiator": 1.1, "Controller": 1.2, "Sentinel": 1.0},
    "Lotus":    {"Duelist": 0.9, "Initiator": 1.0, "Controller": 1.2, "Sentinel": 1.2},
    "Sunset":   {"Duelist": 1.2, "Initiator": 1.2, "Controller": 1.0, "Sentinel": 0.9},
    "Abyss":    {"Duelist": 1.2, "Initiator": 1.0, "Controller": 1.1, "Sentinel": 0.8},
    "Drift":    {"Duelist": 1.0, "Initiator": 1.0, "Controller": 1.0, "Sentinel": 1.0},
}

def get_map_weighted_role_score(map_name: str, role_counts: dict, team: str = "a") -> float:
    """맵 메타에 따른 팀 역할군 조합 점수 계산"""
    weights = MAP_ROLE_WEIGHTS.get(map_name, {})
    score = 0.0
    for role, count in role_counts.items():
        weight = weights.get(role, 1.0)
        score += count * weight
    return score
```

---

## 5. 로테이션 맵 (현재 사용 불가)

| 맵 | 제외 기간 | 복귀 여부 |
|----|---------|---------|
| Split | EP 5 Act 1 ~ EP 7 Act 2 | ✅ 복귀 (EP 7 Act 2) |
| Fracture | EP 7 Act 2 ~ 미정 | ❓ 미정 |
| Breeze | EP 7 Act 2 ~ 미정 | ❓ 미정 |

> 제외된 맵의 경기 데이터는 유효하지만, 현재 서비스 예측에서는 제외 처리 가능.
