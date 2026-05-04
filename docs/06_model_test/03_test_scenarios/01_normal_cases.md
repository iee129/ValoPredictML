> ⚠️ **범위 외**: FastAPI 미사용. 본 프로젝트는 Streamlit 로컬 도구이며 API 엔드포인트 테스트는 적용되지 않는다. 본문은 참고용으로 보존된다.

# 01. 정상 케이스 테스트 시나리오

## 개요

POST /predict 엔드포인트에 대한 정상 입력 시나리오 15개 이상을 정의합니다.
각 시나리오는 입력, 예상 결과, 검증 방법을 포함합니다.

---

## TC-N-001: 균형 잡힌 조합 — Ascent

**시나리오**: 양 팀 모두 역할군이 고르게 분포된 표준 구성

| 항목 | 내용 |
|------|------|
| 맵 | Ascent |
| 팀 A | Jett (Duelist), Sova (Initiator), Viper (Controller), Killjoy (Sentinel), Skye (Initiator) |
| 팀 B | Reyna (Duelist), Breach (Initiator), Omen (Controller), Cypher (Sentinel), Fade (Initiator) |
| 예상 HTTP | 200 |
| 예상 확률 범위 | 0.40 ~ 0.60 (비슷한 구성이므로 불확실) |
| 예상 confidence | "low" 또는 "medium" |

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
    "team_b": ["Reyna", "Breach", "Omen", "Cypher", "Fade"]
  }'
```

**검증 포인트**
- `win_probability + lose_probability == 1.0` (부동소수점 허용 오차 ±0.001)
- `team_a_role_counts.duelist == 1`
- `team_b_role_counts.initiator == 2`
- `feature_importance` 키가 5개 이하

---

## TC-N-002: 전략가(Controller) 중심 팀 A — Bind

**시나리오**: 팀 A가 Controller 위주로 구성, Bind는 스모크가 중요한 맵

| 항목 | 내용 |
|------|------|
| 맵 | Bind |
| 팀 A | Viper, Omen, Brimstone, Killjoy, Sova |
| 팀 B | Jett, Reyna, Skye, Fade, Cypher |
| 예상 HTTP | 200 |
| 예상 확률 범위 | 0.50 ~ 0.70 (Controller 강세 맵에서 팀 A 유리 가능성) |

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Bind",
    "team_a": ["Viper", "Omen", "Brimstone", "Killjoy", "Sova"],
    "team_b": ["Jett", "Reyna", "Skye", "Fade", "Cypher"]
  }'
```

**검증 포인트**
- `team_a_role_counts.controller == 3`
- `team_b_role_counts.duelist == 2`
- 응답에 `map: "Bind"` 포함

---

## TC-N-003: 타격대(Duelist) 중심 팀 B — Haven

| 항목 | 내용 |
|------|------|
| 맵 | Haven |
| 팀 A | Sova, Skye, Viper, Killjoy, Sage |
| 팀 B | Jett, Reyna, Neon, Yoru, Phoenix |
| 예상 HTTP | 200 |
| 예상 확률 | 0.50 초과 (팀 A가 더 균형) 또는 모델 판단에 따름 |

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Haven",
    "team_a": ["Sova", "Skye", "Viper", "Killjoy", "Sage"],
    "team_b": ["Jett", "Reyna", "Neon", "Yoru", "Phoenix"]
  }'
```

**검증 포인트**
- `team_b_role_counts.duelist == 5`
- `team_b_role_counts.controller == 0`
- `team_b_role_counts.sentinel == 0`

---

## TC-N-004: 11개 맵 전체 순환 — 동일 조합

**시나리오**: 같은 팀 조합으로 모든 맵에서 예측, 맵별 확률 변화 확인

```bash
TEAM_A='["Jett","Sova","Viper","Killjoy","Skye"]'
TEAM_B='["Reyna","Breach","Omen","Cypher","Fade"]'

for MAP in Ascent Bind Haven Split Icebox Breeze Fracture Pearl Lotus Sunset Abyss; do
  PROB=$(curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"map\":\"$MAP\",\"team_a\":$TEAM_A,\"team_b\":$TEAM_B}" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['win_probability'])")
  echo "$MAP: $PROB"
done
```

**검증 포인트**
- 모든 맵에서 200 응답
- 맵별 win_probability 값이 다를 것 (동일하면 맵 피처가 무시되는 버그)
- 모든 값이 0.0 ~ 1.0 범위

---

## TC-N-005: 감시자(Sentinel) 중심 팀 — Split

| 항목 | 내용 |
|------|------|
| 맵 | Split |
| 팀 A | Killjoy, Cypher, Sage, Chamber, Deadlock |
| 팀 B | Jett, Sova, Viper, Skye, Breach |
| 예상 HTTP | 200 |

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Split",
    "team_a": ["Killjoy", "Cypher", "Sage", "Chamber", "Deadlock"],
    "team_b": ["Jett", "Sova", "Viper", "Skye", "Breach"]
  }'
```

**검증 포인트**
- `team_a_role_counts.sentinel == 5`
- `team_a_role_counts.duelist == 0`
- 응답 정상 반환

---

## TC-N-006: 신규 요원 포함 조합 — Icebox

**시나리오**: 알 수 없는(unknown) 요원이 포함되어도 예측이 진행되는지 확인

| 항목 | 내용 |
|------|------|
| 맵 | Icebox |
| 팀 A | Jett, Sova, Viper, Killjoy, Waylay |
| 팀 B | Reyna, Breach, Omen, Cypher, Tejo |
| 예상 HTTP | 200 |
| 특이사항 | Waylay, Tejo가 신규 요원인 경우 unknown 처리 |

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Icebox",
    "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Waylay"],
    "team_b": ["Reyna", "Breach", "Omen", "Cypher", "Tejo"]
  }'
```

**검증 포인트**
- HTTP 200 응답 (422가 아님)
- unknown 필드가 있을 수 있음

---

## TC-N-007: 척후대(Initiator) 집중 팀 — Breeze

| 항목 | 내용 |
|------|------|
| 맵 | Breeze |
| 팀 A | Sova, Breach, Skye, Fade, Gekko |
| 팀 B | Jett, Reyna, Viper, Killjoy, Cypher |
| 예상 HTTP | 200 |

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Breeze",
    "team_a": ["Sova", "Breach", "Skye", "Fade", "Gekko"],
    "team_b": ["Jett", "Reyna", "Viper", "Killjoy", "Cypher"]
  }'
```

**검증 포인트**
- `team_a_role_counts.initiator == 5`
- `team_b_role_counts` 역할군 분산 확인

---

## TC-N-008: 완전 대칭 조합 — Fracture

**시나리오**: 팀 A와 팀 B가 미러 역할 구성 (다른 요원, 같은 역할 수)

| 항목 | 내용 |
|------|------|
| 맵 | Fracture |
| 팀 A | Jett (D), Sova (I), Viper (C), Killjoy (S), Skye (I) |
| 팀 B | Reyna (D), Breach (I), Omen (C), Cypher (S), Fade (I) |
| 예상 HTTP | 200 |
| 예상 확률 | 0.40 ~ 0.60 (대칭이므로 불확실) |

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Fracture",
    "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

**검증 포인트**
- `team_a_role_counts == team_b_role_counts` (역할 수 동일)
- win_probability가 0.5에 가까울 것으로 예상

---

## TC-N-009: 응답 저장 확인 — /history 연계

**시나리오**: 예측 후 /history에서 기록 확인

```bash
# 1단계: 예측 수행
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Pearl","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'

# 2단계: 기록 확인
curl "http://localhost:8000/history?limit=1&map=Pearl"
```

**검증 포인트**
- /history total 값이 1 증가
- 최신 항목의 map == "Pearl"
- team_a_agents 배열이 요청과 동일

---

## TC-N-010: 높은 신뢰도 조합 (high confidence 유도)

**시나리오**: 팀 구성 차이가 극명하여 high confidence가 기대되는 조합

| 항목 | 내용 |
|------|------|
| 맵 | Lotus |
| 팀 A | Viper, Omen, Brimstone, Killjoy, Sage (전략가 3 + 감시자 2) |
| 팀 B | Jett, Reyna, Neon, Yoru, Phoenix (타격대 5명) |
| 예상 HTTP | 200 |
| 예상 confidence | "medium" 또는 "high" |

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Lotus",
    "team_a": ["Viper","Omen","Brimstone","Killjoy","Sage"],
    "team_b": ["Jett","Reyna","Neon","Yoru","Phoenix"]
  }'
```

---

## TC-N-011: Sunset 맵 예측

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Sunset",
    "team_a": ["Jett","KAY/O","Viper","Cypher","Skye"],
    "team_b": ["Iso","Fade","Astra","Killjoy","Sage"]
  }'
```

**검증 포인트**
- `KAY/O` 슬래시 포함 이름 정상 처리
- 200 응답

---

## TC-N-012: Abyss 맵 예측

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Abyss",
    "team_a": ["Neon","Tejo","Harbor","Chamber","Deadlock"],
    "team_b": ["Jett","Gekko","Clove","Vyse","Sage"]
  }'
```

---

## TC-N-013: 응답시간 10회 연속 측정

```bash
echo "=== 응답시간 10회 측정 ==="
TOTAL=0
for i in $(seq 1 10); do
  T=$(curl -s -o /dev/null -w "%{time_total}" \
    -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}')
  MS=$(python3 -c "print(f'{float(\"$T\")*1000:.1f}ms')")
  echo "  [$i] $MS"
done
echo "목표: 모든 응답 ≤ 200ms"
```

**검증 포인트**
- 10회 모두 200ms 이내
- 첫 번째 요청 이후 응답시간 안정화 (모델 이미 로드됨)

---

## TC-N-014: win_probability 소수점 정밀도 확인

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
wp = d['win_probability']
lp = d['lose_probability']
print(f'win_probability: {wp}')
print(f'lose_probability: {lp}')
print(f'합계: {wp + lp:.6f}')
assert abs(wp + lp - 1.0) < 0.001, '합계가 1.0이 아님!'
print('합계 검증 통과')
"
```

---

## TC-N-015: feature_importance 구조 검증

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
fi = d['feature_importance']
print(f'피처 수: {len(fi)}')
print('피처별 중요도:')
for k, v in sorted(fi.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v:.4f}')
total = sum(fi.values())
print(f'중요도 합계: {total:.4f}')
assert len(fi) <= 5, '상위 5개 초과!'
assert all(v >= 0 for v in fi.values()), '음수 중요도 존재!'
print('검증 통과')
"
```

**검증 포인트**
- feature_importance 키 수 ≤ 5
- 모든 중요도 값 ≥ 0
- 키 이름이 feature 목록에 포함된 이름
