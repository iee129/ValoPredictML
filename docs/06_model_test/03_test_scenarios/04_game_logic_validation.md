# 04. 발로란트 게임 로직 검증

## 개요

ML 모델이 발로란트 게임 로직에 부합하는 예측을 수행하는지 검증합니다.
수치적 정확성보다 **경향성(tendency)**이 게임 이론과 일치하는지 확인합니다.

---

## 1. 검증 원칙

모델은 역사적 경기 데이터를 학습했으므로, 아래 게임 이론적 경향성이 예측에 반영되어야 합니다.

| 원칙 | 근거 |
|------|------|
| 역할군 균형 팀이 단일 역할군 팀보다 유리 | 프로 메타: 1D1I1C2S 또는 2I1C1S1D 구성 선호 |
| Controller 부재 팀은 불리 | 스모크 없이는 사이트 장악 불가 |
| 맵별 구성 효율 차이 존재 | Bind: Viper 강세 / Breeze: 원거리 요원 선호 |
| Sentinel 전무 팀은 수비력 저하 | 플랭 감시 및 사이트 방어 불가 |

---

## 2. 역할군 균형 vs. 단일 역할군

### TC-GL-001: 균형 팀 vs. 타격대 5명 팀

**검증**: 균형 팀의 승률이 50% 초과해야 함

```bash
# 균형 팀(A) vs 타격대 5명 팀(B)
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Sova", "Viper", "Killjoy", "Skye", "Jett"],
    "team_b": ["Jett", "Reyna", "Neon", "Yoru", "Phoenix"]
  }' | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'팀 A (균형) 승률: {d[\"win_probability\"]:.3f}')
print(f'팀 B (타격대5) 승률: {d[\"lose_probability\"]:.3f}')
print('검증:', '통과' if d['win_probability'] > 0.5 else '실패 (모델 재검토 필요)')
"
```

**기대 결과**
- `win_probability > 0.5` (팀 A 유리)
- `team_b_role_counts.duelist == 4` (Jett 제외, B팀만 집계 기준)

---

### TC-GL-002: 균형 팀 vs. 전략가 5명 팀

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Split",
    "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
    "team_b": ["Viper", "Omen", "Brimstone", "Astra", "Harbor"]
  }' | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'팀 A (균형) 승률: {d[\"win_probability\"]:.3f}')
print('팀 B 역할:', d['team_b_role_counts'])
"
```

**기대 결과**: `team_b_role_counts.controller == 5`, `win_probability > 0.5`

---

### TC-GL-003: 전략가 없는 팀 vs. 전략가 있는 팀

```bash
# 팀 A: 전략가 없음 (타격대 + 척후병 + 감시자)
# 팀 B: 전략가 포함 (표준 구성)
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Bind",
    "team_a": ["Jett", "Reyna", "Sova", "Breach", "Killjoy"],
    "team_b": ["Neon", "Fade", "Viper", "Cypher", "Skye"]
  }' | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'팀 A (전략가 없음) 승률: {d[\"win_probability\"]:.3f}')
print(f'팀 A Controller 수: {d[\"team_a_role_counts\"][\"controller\"]}')
print('검증:', '통과' if d['win_probability'] < 0.5 else '실패')
"
```

**기대 결과**: `team_a_role_counts.controller == 0`, `win_probability < 0.5`

---

## 3. 맵별 구성 효율 차이

### TC-GL-004: 같은 조합, 맵 변경 시 확률 변화

```bash
TEAM_A='["Viper","Omen","Sova","Killjoy","Jett"]'
TEAM_B='["Brimstone","Fade","Breach","Cypher","Reyna"]'

echo "=== 맵별 팀 A 승률 ==="
for MAP in Ascent Bind Breeze Icebox; do
  PROB=$(curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"map\":\"$MAP\",\"team_a\":$TEAM_A,\"team_b\":$TEAM_B}" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['win_probability'])")
  echo "  $MAP: $PROB"
done
```

**기대 결과**: 모든 맵에서 동일 확률이 나오면 버그 (`map_encoded` 피처가 무시됨)

---

### TC-GL-005: Bind — Viper 강세 검증

Bind는 좁은 구도와 텔레포트 맵으로, Viper의 벽/오브/스크린 조합이 특히 강합니다.

```bash
# 팀 A: Viper 포함 구성
# 팀 B: Viper 없는 스모크 구성
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Bind",
    "team_a": ["Viper", "Sova", "Jett", "Killjoy", "Skye"],
    "team_b": ["Omen", "Breach", "Reyna", "Cypher", "Fade"]
  }' | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Bind Viper 포함 팀 A 승률: {d[\"win_probability\"]:.3f}')
"
```

---

### TC-GL-006: Breeze — 원거리 요원 선호 검증

Breeze는 맵이 넓어 긴 교전거리가 형성됩니다.

```bash
# 팀 A: 원거리 특화 (Sova, Chamber, Viper, Jett, KAY/O)
# 팀 B: 근거리 특화 (Breach, Yoru, Neon, Phoenix, Skye)
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Breeze",
    "team_a": ["Sova","Chamber","Viper","Jett","KAY/O"],
    "team_b": ["Breach","Yoru","Neon","Phoenix","Skye"]
  }' | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Breeze 원거리 팀 A 승률: {d[\"win_probability\"]:.3f}')
"
```

---

## 4. 역할군별 승률 경향성 체계적 검증

### TC-GL-007: Controller 수와 승률 상관관계

같은 맵, 같은 팀 B에서 팀 A의 Controller 수를 0→1→2→3으로 증가시켜 승률 변화 확인

```python
# tests/test_game_logic.py
import pytest
from fastapi.testclient import TestClient

CONTROLLER_AGENTS = ["Viper", "Omen", "Brimstone", "Astra", "Harbor"]
NON_CONTROLLER_FILL = ["Jett", "Reyna", "Neon", "Yoru", "Sova"]

@pytest.mark.integration
def test_more_controllers_generally_better(client):
    """Controller 수가 늘어날수록 승률이 단조 증가하는 경향 확인 (엄격한 단조성 요구 안 함)."""
    team_b = ["Jett", "Sova", "Omen", "Killjoy", "Skye"]
    probs = []

    for n_controllers in range(0, 4):
        controllers = CONTROLLER_AGENTS[:n_controllers]
        fillers = NON_CONTROLLER_FILL[:5 - n_controllers]
        team_a = controllers + fillers

        response = client.post("/predict", json={
            "map": "Bind",
            "team_a": team_a,
            "team_b": team_b,
        })
        assert response.status_code == 200
        probs.append(response.json()["win_probability"])

    print(f"Controller 수별 승률: {probs}")
    # 0개보다 1~2개가 높을 것으로 기대
    assert probs[1] > probs[0] or probs[2] > probs[0], \
        "Controller 1~2명이 0명보다 유리해야 함"
```

---

### TC-GL-008: Sentinel 전무 팀의 승률 패널티

```python
@pytest.mark.integration
def test_no_sentinel_team_is_disadvantaged(client):
    """Sentinel 0명 팀은 균형 팀보다 승률이 낮아야 함."""
    # 팀 B: 표준 균형 구성
    team_b = ["Reyna", "Sova", "Viper", "Killjoy", "Skye"]

    # 팀 A (Sentinel 0명)
    response_no_sentinel = client.post("/predict", json={
        "map": "Split",
        "team_a": ["Jett", "Breach", "Omen", "Fade", "KAY/O"],
        "team_b": team_b,
    })
    prob_no_sentinel = response_no_sentinel.json()["win_probability"]

    # 팀 A (Sentinel 1명 포함)
    response_with_sentinel = client.post("/predict", json={
        "map": "Split",
        "team_a": ["Jett", "Breach", "Omen", "Killjoy", "Fade"],
        "team_b": team_b,
    })
    prob_with_sentinel = response_with_sentinel.json()["win_probability"]

    print(f"Sentinel 없음: {prob_no_sentinel:.3f}")
    print(f"Sentinel 있음: {prob_with_sentinel:.3f}")
    assert prob_with_sentinel >= prob_no_sentinel - 0.05, \
        "Sentinel 포함 팀이 더 높거나 비슷한 승률이어야 함"
```

---

## 5. 모델 안정성 검증

### TC-GL-009: 동일 입력 → 동일 출력 (결정론적 예측)

```bash
PAYLOAD='{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'

P1=$(curl -s -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "$PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin)['win_probability'])")
P2=$(curl -s -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "$PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin)['win_probability'])")

echo "1차: $P1"
echo "2차: $P2"
[ "$P1" = "$P2" ] && echo "결정론적 확인: 통과" || echo "결정론적 확인: 실패 (비결정론적 모델!)"
```

**기대 결과**: P1 == P2 (XGBoost, LightGBM은 결정론적)

---

### TC-GL-010: 팀 A ↔ 팀 B 스왑 시 확률 역전

```python
@pytest.mark.integration
def test_swap_teams_reverses_probability(client):
    """팀 A와 팀 B를 바꾸면 승률이 역전되어야 함."""
    team1 = ["Jett","Sova","Viper","Killjoy","Skye"]
    team2 = ["Reyna","Breach","Omen","Cypher","Fade"]

    r1 = client.post("/predict", json={"map": "Ascent", "team_a": team1, "team_b": team2})
    r2 = client.post("/predict", json={"map": "Ascent", "team_a": team2, "team_b": team1})

    prob_a_first = r1.json()["win_probability"]
    prob_a_second = r2.json()["win_probability"]

    print(f"팀1 공격: {prob_a_first:.3f}, 팀1 수비(스왑): {prob_a_second:.3f}")

    # win_probability + lose_probability = 1이므로
    # 스왑 후 팀1의 승률은 원래의 lose_probability여야 함
    expected = round(1 - prob_a_first, 4)
    actual = round(prob_a_second, 4)
    assert abs(expected - actual) < 0.02, \
        f"스왑 후 확률이 예상값({expected})과 다름: {actual}"
```

---

## 6. 검증 결과 기록 템플릿

각 게임 로직 검증 실행 후 아래 표에 결과를 기록합니다.

| TC ID | 검증 항목 | 실행일 | 결과 | 승률 값 | 비고 |
|-------|---------|--------|------|---------|------|
| TC-GL-001 | 균형 vs 타격대5 | - | - | - | |
| TC-GL-002 | 균형 vs 전략가5 | - | - | - | |
| TC-GL-003 | 전략가 없는 팀 | - | - | - | |
| TC-GL-004 | 맵별 확률 변화 | - | - | - | |
| TC-GL-005 | Bind Viper 강세 | - | - | - | |
| TC-GL-006 | Breeze 원거리 | - | - | - | |
| TC-GL-007 | Controller 수 상관 | - | - | - | |
| TC-GL-008 | Sentinel 패널티 | - | - | - | |
| TC-GL-009 | 결정론적 예측 | - | - | - | |
| TC-GL-010 | 팀 스왑 역전 | - | - | - | |
