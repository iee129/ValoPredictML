# 01. 부록 — `docs/09_web` 대비 정정 내역

`docs/09_web`(폐기 선언된 구 웹 설계)를 실제 모델 계약·TypeScript 목표에 맞춰 무엇을 바로잡았는지 기록. `docs/09_web`는 보존하며, 본 `docs_web`가 현행 기준이다.

---

## 1. 상태/목적

| 축 | docs/09_web | docs_web (현행) |
|----|-------------|-----------------|
| 문서 상태 | 전 파일 상단 "⚠️ 범위 외(Streamlit 대체)" | 활성 — 시연 현행 기준 |
| 목적 | (폐기됨) | FastAPI 서빙 + Next.js 16 TS 시연 |

---

## 2. 결정적 정정 (계약)

| # | docs/09_web | 문제 | docs_web 정정 |
|---|-------------|------|----------------|
| 1 | `POST /predict` 요청 = `{team_a:[요원5], team_b:[요원5], map}` | **선수 없음** → advanced 모델 구동 불가 | `{map, cutoff_year, team_a:[{player,agent}×5], team_b:[…]}` |
| 2 | `cutoff_year` 없음 | 이전연도 이력 기준 결정 불가 | `cutoff_year` 필수 |
| 3 | 응답 `features:[{name:"팀 조합 다양성", importance}]` | **존재하지 않는 임의 라벨** | `top_features:[{feature(실제 컬럼명), label, value, importance, contribution}]` |
| 4 | 응답 `win_rate_a/win_rate_b` | 모델 출력 구조와 다른 임의 키 | `team_a.win_probability` 등 `PredictionResult` 직렬화 |
| 5 | `role_counts`/`predicted_label` 없음 | 모델이 주는 정보 누락 | `role_counts`, `predicted_label`, `confidence` 포함 |
| 6 | `GET /maps` 10종 | 맵 누락(Abyss/Drift/Corrode) | **13종** (`MAP_ORDER`) |
| 7 | 요원 수 불명/27~ 언급 | 구버전 | **29종** (`AGENT_ROLE_MAP`) |

---

## 3. 스택 정정

| 축 | docs/09_web | docs_web |
|----|-------------|----------|
| 언어 | JavaScript(“TypeScript 미사용” 명시) | **TypeScript**(strict) |
| 파일 | `*.js` + `jsconfig.json` | `*.tsx` + `tsconfig.json` + `types/api.ts` |
| Next.js/React | 16.2.4 / 19 | ^16 / ^19 (유지 — 부합) |
| 모델 표기 | "RandomForest / XGBoost" | RF+XGB+LGBM soft-voting(advanced 125F, 정확) |

---

## 4. 범위 정정

| 항목 | docs/09_web | docs_web |
|------|-------------|----------|
| `/history`·`/analytics` | PostgreSQL 영속 가정, 정규 엔드포인트 | **범위 외**(README상 DB 제외). 필요 시 선택 구현 |
| `/predict` 콜드스타트 | 언급 없음 | 명시 + 워밍업/ replay 우선 전략 |
| 산출물 준비 | 언급 없음 | 런북에 학습 파이프라인 선행 단계 명시 |
| 배포(Vercel) | 1순위 | 선택(시연은 로컬 우선) |

---

## 5. 재사용 가능한 09_web 자산 (참고용)

계약과 무관한 **시각 디자인**은 참고 가치가 있다:

| 09_web 문서 | 재사용 |
|-------------|--------|
| `06_styling/02_valo_theme.md` | 발로란트 색 토큰(레드 `#ff4655`, 다크 배경) |
| `06_styling/*` | clip-path 각진 카드, 타이포(Bebas Neue) |
| `07_visualization/*` | Recharts 게이지/레이더 사용 패턴 |
| `04_components/*` | 컴포넌트 분해 아이디어(슬롯/배지/카드) |

단, **데이터 바인딩 부분은 본 `docs_web` 계약으로 교체**해야 한다(필드명이 전부 다름).

---

## 6. 한 줄 요약

> 09_web은 "요원만 보내는 가짜 계약 + JS + 폐기"였고, docs_web은 "선수+요원+기준연도의 실제 모델 계약 + TS + 시연 현행"이다.
