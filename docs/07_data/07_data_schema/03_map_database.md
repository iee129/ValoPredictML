# 03. 맵 데이터베이스 (13개)

마지막 업데이트: 2026-05-04

---

## 1. 전체 맵 목록

| 맵 | 인코딩 | 특성 |
|----|--------|------|
| Ascent | 0 | 개방형 미드, 균형 |
| Bind | 1 | 텔레포터, 공격자 불리 |
| Haven | 2 | 사이트 3개, 수비자 불리 |
| Split | 3 | 수직 구조, Sentinel 유리 |
| Icebox | 4 | 좁은 통로, Sentinel 유리 |
| Breeze | 5 | 장거리 교전, Controller 유리 |
| Fracture | 6 | H자 구조, 공격자 양방향 진입 |
| Pearl | 7 | 해저 도시, 균형 |
| Lotus | 8 | 사이트 3개, Controller 유리 |
| Sunset | 9 | 좁은 골목, 균형 |
| Abyss | 10 | 절벽 추락 지형 |
| Drift | 11 | 2025년 신규 |
| Corrode | 12 | 2025년 신규 (France 테마) |

---

## 2. MAP_ORDER / MAP_TO_INDEX (Python)

```python
MAP_ORDER: list[str] = [
    "Ascent", "Bind", "Haven", "Split", "Icebox", "Breeze",
    "Fracture", "Pearl", "Lotus", "Sunset", "Abyss", "Drift",
    "Corrode",
]
MAP_TO_INDEX: dict[str, int] = {m: i for i, m in enumerate(MAP_ORDER)}
```

---

## 3. 맵 이름 표준화

```python
def normalize_map(raw: str) -> str | None:
    """맵 이름 → 표준 이름 변환. 없으면 None → 품질 검사 탈락."""
    if not raw:
        return None
    s = raw.strip()
    if s in MAP_ORDER:
        return s
    lower = s.lower()
    MAP_LOWER = {m.lower(): m for m in MAP_ORDER}
    if lower in MAP_LOWER:
        return MAP_LOWER[lower]
    titled = s.title()
    if titled in MAP_ORDER:
        return titled
    return None
```

---

## 4. 맵별 역할군 선호도 (메타 참고)

| 맵 | 선호 역할군 | 주요 이유 |
|----|-----------|---------|
| Ascent | Initiator, Controller | 균형 맵 |
| Bind | Controller, Initiator | 텔레포터 활용 |
| Haven | Duelist, Initiator | 사이트 3개, 빠른 이동 |
| Split | Sentinel, Controller | 수직 구조, 수비 중요 |
| Icebox | Sentinel, Controller | 좁은 통로, 디펜스 중요 |
| Breeze | Controller, Duelist | 장거리, 스모크+Operator |
| Fracture | Initiator, Controller | 양방향 진입 대응 |
| Pearl | Controller, Initiator | 균형 맵 |
| Lotus | Controller, Sentinel | 사이트 3개, 수비 중심 |
| Sunset | Duelist, Initiator | 공격적 맵 구조 |
| Abyss | Duelist, Controller | 개방형, 공격 유리 |
| Drift | 미확인 | 2025 신규, 데이터 부족 |
| Corrode | 미확인 | 2025 신규 (France 테마), 데이터 부족 |

> 수치는 데이터 수집 후 `atk_side_advantage` 집계로 업데이트 예정.

---

## 5. 로테이션 이력 (참고)

| 맵 | 제외 기간 | 상태 |
|----|---------|------|
| Split | EP 5 Act 1 ~ EP 7 Act 2 | 복귀 완료 |
| Fracture | EP 7 Act 2~ | 미정 |
| Breeze | EP 7 Act 2~ | 미정 |
