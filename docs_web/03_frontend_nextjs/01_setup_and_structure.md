# 01. 프론트엔드 셋업 · 디렉터리 구조

## 1. 프로젝트 생성

```bash
# 저장소 루트에서
npx create-next-app@latest valo_web_frontend \
  --typescript --app --tailwind --eslint --src-dir --import-alias "@/*"
cd valo_web_frontend
npm install recharts
```

생성 결과: Next.js 16 App Router + React 19 + **TypeScript** + Tailwind v4. `valo_web_frontend/`는 저장소 안 별도 프론트 루트로 둔다(백엔드 `valo_web_backend/`와 분리).

> `.gitignore` 허용목록에 프론트를 커밋하려면 `/valo_web_frontend/`, `/valo_web_frontend/**`를 추가하되 `valo_web_frontend/node_modules/`·`.next/`는 제외(create-next-app의 `.gitignore`가 처리).

---

## 2. 디렉터리 구조 (TypeScript)

```
valo_web_frontend/
├── package.json
├── tsconfig.json              ← strict: true 권장
├── next.config.ts             ← images.remotePatterns (요원 이미지 CDN, 선택)
├── .env.local                 ← NEXT_PUBLIC_API_URL=http://localhost:8000
│
└── src/
    ├── app/
    │   ├── layout.tsx          공통 레이아웃 (Navbar)
    │   ├── globals.css         Tailwind @theme
    │   ├── page.tsx            / 홈 (시연 안내 + 모델 지표 요약)
    │   ├── predict/
    │   │   └── page.tsx        /predict 커스텀 5v5 (핵심 시연)
    │   ├── replay/
    │   │   └── page.tsx        /replay 경기 다시보기
    │   └── model/
    │       └── page.tsx        /model 모델 근거
    │
    ├── components/
    │   ├── predict/
    │   │   ├── MapSelect.tsx
    │   │   ├── YearSelect.tsx
    │   │   ├── TeamLineup.tsx     팀 1개(5 슬롯) 입력
    │   │   └── LineupSlot.tsx     선수(자동완성) + 요원(셀렉트) 1쌍
    │   ├── result/
    │   │   ├── WinRateGauge.tsx   Recharts RadialBar
    │   │   ├── RoleRadar.tsx      Recharts Radar (team_a vs team_b)
    │   │   ├── FeatureBar.tsx     top_features 수평 바
    │   │   └── ConfidenceBadge.tsx
    │   ├── replay/
    │   │   ├── MatchPicker.tsx
    │   │   └── ReplayOutcome.tsx  예측 vs 실제
    │   └── ui/
    │       ├── ErrorBanner.tsx
    │       └── Spinner.tsx
    │
    ├── lib/
    │   ├── api.ts               타입 안전 fetch 래퍼 (모든 엔드포인트)
    │   └── format.ts            승률 %, 신뢰도 레벨, 라벨 변환
    │
    └── types/
        └── api.ts               ★ 백엔드 Pydantic 스키마의 TS 거울 (SSOT)
```

핵심: `src/types/api.ts`가 **백엔드 `valo_web_backend/schemas.py`와 1:1**이다. 계약이 바뀌면 두 파일을 함께 고친다. → [02_types_and_api_client.md](02_types_and_api_client.md).

---

## 3. `tsconfig.json` 요점

```jsonc
{
  "compilerOptions": {
    "strict": true,                  // 타입 누락을 컴파일 타임에 차단
    "paths": { "@/*": ["./src/*"] }
  }
}
```

`strict: true`로 두는 게 09_web 실패(계약 어긋남)를 막는 핵심 장치다.

---

## 4. `.env.local`

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`NEXT_PUBLIC_` 접두사가 있어야 클라이언트 번들에 노출된다. 모든 페이지가 클라이언트 컴포넌트(`'use client'`)로 실시간 fetch하므로 이 변수로 백엔드를 가리킨다.

---

## 5. 페이지 구성 의도

| 라우트 | 시연 역할 | 콜드스타트 |
|--------|-----------|------------|
| `/` | 홈 — 모델 지표 요약(`/model`), 시연 흐름 안내 | 없음 |
| `/predict` | **핵심** — 임의 5v5 라인업으로 승률 예측 | 첫 호출만 |
| `/replay` | 안정적 데모 — 실제 경기 예측 vs 결과 | 없음 |
| `/model` | 근거 — 125피처, AUC, 검증, 전역 중요도 | 없음 |

시연 시작은 콜드스타트 없는 `/model`·`/replay`로 워밍하고, `/predict`로 마무리하는 순서를 권장.

---

## 6. 관련 문서

- 타입·API 클라이언트 → [02_types_and_api_client.md](02_types_and_api_client.md)
- 예측 페이지 → [03_predict_page.md](03_predict_page.md)
- 페이지·컴포넌트 → [04_pages_and_components.md](04_pages_and_components.md)
- 발로란트 테마·레이아웃·컴포넌트 시각 → [../07_styling/00_design_principles.md](../07_styling/00_design_principles.md)
