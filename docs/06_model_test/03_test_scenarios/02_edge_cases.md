> ⚠️ 참고/확장 설계: 현재 시연은 웹 스택(FastAPI `src/api` + Next.js `web`) 기준이다. 이 문서의 테스트 설계는 참고용으로 보존한다.

> ⚠️ **참고용**: 본 프로젝트는 웹 스택(FastAPI `src/api` + Next.js `web`)으로 서빙한다. 본문의 상세 테스트 설계는 참고용으로 보존된다.

# 02. 엣지 케이스 테스트 시나리오

## 개요

경계값, 특수 조합, 예외적 입력에 대한 엣지 케이스 20개 이상을 정의합니다.

---

## TC-E-001: 팀 인원 4명 (1명 부족)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett","Sova","Viper","Killjoy"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 422 Unprocessable Entity |
|----------|--------------------------|
| 에러 메시지 | "팀 구성은 정확히 5명이어야 합니다. (입력: 4명)" |
| 위치 | loc: ["body", "team_a"] |

---

## TC-E-002: 팀 인원 6명 (1명 초과)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett","Sova","Viper","Killjoy","Skye","Reyna"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 422 |
|----------|-----|
| 에러 메시지 | "팀 구성은 정확히 5명이어야 합니다. (입력: 6명)" |

---

## TC-E-003: 팀 A와 팀 B 간 중복 요원

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
    "team_b": ["Jett","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 422 |
|----------|-----|
| 에러 메시지 | "중복 요원이 있습니다: ['Jett']" |

---

## TC-E-004: 팀 A 내부 중복 요원

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett","Jett","Viper","Killjoy","Skye"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 422 (Pydantic validator가 전체 10명 합산 체크) |
|----------|------|

---

## TC-E-005: 유효하지 않은 맵 이름 (오타)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Icebox2",
    "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 422 |
|----------|-----|
| 에러 메시지 | "알 수 없는 맵: 'Icebox2'." |

---

## TC-E-006: 맵 이름 대소문자 오류

```bash
# "ascent" (소문자) → 422 기대
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'

# "ASCENT" (대문자) → 422 기대
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"ASCENT","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'
```

| 기대 결과 | 422 (대소문자 정확히 일치 필요) |
|----------|------|
| 참고 | 프론트엔드에서 드롭다운으로 선택하므로 일반적으로 발생 안 함 |

---

## TC-E-007: 빈 팀 배열

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":[],"team_b":[]}'
```

| 기대 결과 | 422 |
|----------|-----|
| 에러 메시지 | "팀 구성은 정확히 5명이어야 합니다. (입력: 0명)" |

---

## TC-E-008: 요청 본문 없음

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json"
```

| 기대 결과 | 422 (body 파싱 실패) |
|----------|------|

---

## TC-E-009: 필드 누락 — map 없음

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'
```

| 기대 결과 | 422 |
|----------|-----|
| 에러 위치 | loc: ["body", "map"] |
| 에러 타입 | "missing" |

---

## TC-E-010: 필드 누락 — team_b 없음

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"]}'
```

| 기대 결과 | 422 |
|----------|-----|
| 에러 위치 | loc: ["body", "team_b"] |

---

## TC-E-011: 요원 이름에 숫자/특수문자

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett","123","Viper","Killjoy","Skye"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 200 (unknown 처리) — 스키마에 요원명 검증 없으면 통과 |
|----------|------|
| 대안 | unknown 카운트에 포함, 예측은 계속 진행 |
| 검증 | `team_a_role_counts.unknown >= 1` |

---

## TC-E-012: 매우 긴 요원 이름 (문자열 길이 경계)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett","Sova","Viper","Killjoy","AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 200 (unknown 처리) 또는 422 (길이 제한 있는 경우) |
|----------|------|

---

## TC-E-013: null 값 포함

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": null,
    "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 422 (map은 string이어야 함) |
|----------|------|

---

## TC-E-014: 팀 배열에 null 값 포함

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett","Sova",null,"Killjoy","Skye"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 422 (배열 요소가 string이어야 함) |
|----------|------|

---

## TC-E-015: Content-Type 헤더 없음

```bash
curl -X POST http://localhost:8000/predict \
  -d '{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'
```

| 기대 결과 | 422 또는 415 (Content-Type 미지정) |
|----------|------|

---

## TC-E-016: KAY/O 슬래시 포함 이름 처리

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["KAY/O","Sova","Viper","Killjoy","Skye"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 200 (특수문자 슬래시 포함 요원명 정상 처리) |
|----------|------|
| 검증 | `team_a_role_counts.initiator >= 1` (KAY/O는 Initiator) |

---

## TC-E-017: 팀 A = 팀 B (완전 동일 — 중복 에러)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
    "team_b": ["Jett","Sova","Viper","Killjoy","Skye"]
  }'
```

| 기대 결과 | 422 (모든 요원이 중복) |
|----------|------|
| 에러 메시지 | "중복 요원이 있습니다: ['Jett', 'Sova', 'Viper', 'Killjoy', 'Skye']" |

---

## TC-E-018: 공백 문자열 요원 이름

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett"," ","Viper","Killjoy","Skye"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 200 (unknown 처리) 또는 422 (공백 검증 추가 시) |
|----------|------|

---

## TC-E-019: 정수형 요원 이름

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": [1, "Sova", "Viper", "Killjoy", "Skye"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

| 기대 결과 | 422 (배열 요소 타입 오류) 또는 200 (Pydantic이 문자열로 강제 변환) |
|----------|------|
| 참고 | Pydantic v2 기본 동작: 정수를 문자열 "1"로 강제 변환 후 unknown 처리 |

---

## TC-E-020: limit=0 (경계값)

```bash
curl "http://localhost:8000/history?limit=0"
```

| 기대 결과 | 422 (ge=1 조건 위반) |
|----------|------|

---

## TC-E-021: limit=101 (최대 초과)

```bash
curl "http://localhost:8000/history?limit=101"
```

| 기대 결과 | 422 (le=100 조건 위반) |
|----------|------|

---

## TC-E-022: 존재하지 않는 엔드포인트 접근

```bash
curl http://localhost:8000/predict2
curl http://localhost:8000/nonexistent
```

| 기대 결과 | 404 Not Found |
|----------|------|

```json
{"detail": "Not Found"}
```

---

## 엣지 케이스 요약표

| TC ID | 시나리오 | 기대 상태코드 | 검증 핵심 |
|-------|---------|-------------|---------|
| TC-E-001 | 팀 인원 4명 | 422 | 인원 부족 메시지 |
| TC-E-002 | 팀 인원 6명 | 422 | 인원 초과 메시지 |
| TC-E-003 | 팀 간 중복 요원 | 422 | 중복 요원 목록 |
| TC-E-004 | 팀 내부 중복 | 422 | 검증 순서 확인 |
| TC-E-005 | 오타 맵 이름 | 422 | 에러 메시지 내 맵명 |
| TC-E-006 | 대소문자 오류 | 422 | 정확 일치 검증 |
| TC-E-007 | 빈 배열 | 422 | 0명 메시지 |
| TC-E-008 | 본문 없음 | 422 | 파싱 실패 |
| TC-E-009 | map 필드 누락 | 422 | missing 타입 |
| TC-E-010 | team_b 누락 | 422 | missing 타입 |
| TC-E-011 | 특수문자 이름 | 200 | unknown 처리 |
| TC-E-012 | 긴 이름 문자열 | 200/422 | 정책 결정 필요 |
| TC-E-013 | map=null | 422 | 타입 오류 |
| TC-E-014 | 배열에 null | 422 | 타입 오류 |
| TC-E-015 | Content-Type 없음 | 422/415 | 헤더 검증 |
| TC-E-016 | KAY/O 슬래시 | 200 | 특수문자 처리 |
| TC-E-017 | 팀 완전 동일 | 422 | 중복 전체 목록 |
| TC-E-018 | 공백 이름 | 200/422 | 정책 결정 필요 |
| TC-E-019 | 정수형 이름 | 200/422 | Pydantic 강제 변환 |
| TC-E-020 | limit=0 | 422 | ge=1 검증 |
| TC-E-021 | limit=101 | 422 | le=100 검증 |
| TC-E-022 | 없는 엔드포인트 | 404 | Not Found |
