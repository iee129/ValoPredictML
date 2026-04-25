# 01. 기술 스택

## 스택 요약

| 카테고리 | 도구 / 라이브러리 | 버전 | 역할 |
|---|---|---|---|
| 프레임워크 | Next.js | 16.2.4 | 라우팅, SSR/CSR, 빌드 최적화 |
| UI 런타임 | React | 19.2.4 | 컴포넌트 렌더링, 상태 관리 |
| 스타일링 | Tailwind CSS | v4 | 유틸리티 기반 CSS |
| 차트 | Recharts | 2.x | 게이지, 레이더, 바 차트 |
| 이미지 | next/image | (Next.js 내장) | valorant-api.com 요원 이미지 최적화 |
| 배포 | Vercel | - | Edge Network, CI/CD 내장 |
| 언어 | JavaScript | ES2022+ | TypeScript 미사용 |

---

## 각 도구 선택 이유

### Next.js 16 (App Router)

**선택 이유:**
- App Router(`src/app/`)로 파일 시스템 기반 라우팅 — `/predict`, `/history`, `/analytics` 경로가 폴더 구조 그대로 매핑
- `'use client'` 지시어로 클라이언트/서버 컴포넌트 명확히 구분
- Vercel과의 네이티브 통합으로 배포 설정 최소화
- `next/image`로 외부 이미지(valorant-api.com) 자동 최적화

**대안 검토:**
| 대안 | 미선택 이유 |
|---|---|
| Create React App | 유지보수 종료, 라우팅 별도 설정 필요 |
| Vite + React | 라우팅 직접 구성 필요, Vercel 통합 약함 |
| Remix | 학습 비용, 커뮤니티 자료 상대적으로 적음 |

---

### React 19

**선택 이유:**
- Next.js 16과 자동 페어링
- React Compiler 내장 지원 (`next.config.mjs`의 `reactCompiler: true`)
- 기존 React 18 API와 100% 호환

---

### Tailwind CSS v4

**선택 이유:**
- `@theme {}` 블록으로 CSS 변수를 Tailwind 유틸리티로 직접 사용
  - 예: `--color-valo-red: #ff4655` → `text-valo-red`, `bg-valo-red` 자동 생성
- CSS-first 설정 (별도 `tailwind.config.js` 불필요)
- 발로란트 브랜드 색상 시스템을 CSS 변수로 일원화 가능

**v3 대비 핵심 차이:**
```css
/* v3: tailwind.config.js에서 theme.extend */
/* v4: globals.css @theme 블록에서 바로 정의 */
@theme {
  --color-valo-red: #ff4655;  /* → bg-valo-red, text-valo-red 자동 생성 */
}
```

**주의사항:** CSS 모듈(`.module.css`)에서 `@apply` 사용 시 첫 줄에 반드시 `@reference "tailwindcss";` 필요  
→ 자세한 내용: [06_styling/03_css_modules_strategy.md](../06_styling/03_css_modules_strategy.md)

---

### Recharts 2.x

**선택 이유:**
- React 친화적 API (`<RadialBarChart>`, `<RadarChart>`)
- SVG 기반 → 고해상도 디스플레이에서도 선명
- 발로란트 테마 색상을 `fill` prop으로 직접 주입 가능

**사용 컴포넌트:**
| Recharts 차트 | 사용 위치 |
|---|---|
| `RadialBarChart` | `WinRateGauge` — 팀별 승률 게이지 |
| `RadarChart` | `RoleRadarChart` — 역할군 비교 레이더 |
| `BarChart` (커스텀 CSS) | `Analytics` — 요원 사용률 (Recharts 미사용) |

**Analytics 페이지 바 차트는 Recharts 미사용:**  
→ 자세한 내용: [07_visualization/02_custom_css_charts.md](../07_visualization/02_custom_css_charts.md)

---

### JavaScript (TypeScript 미사용)

**선택 이유:**
- 프로토타입 단계에서 빠른 반복 개발 우선
- Next.js + Tailwind v4의 타입 지원이 아직 불안정한 측면 있음
- API 응답 구조가 ML 모델 개발에 따라 변경될 수 있어 유연성 확보

**향후 마이그레이션 경로:**
- `jsconfig.json` → `tsconfig.json` 전환
- `*.js` → `*.tsx` 확장자 변경
- API 응답 타입 정의 (`types/api.d.ts`)

---

### Vercel 배포

**선택 이유:**
- Next.js 개발사(Vercel)의 플랫폼 → 네이티브 최적화
- `vercel.json`으로 배포 설정 선언적 관리
- Vercel Edge Network로 전세계 어디서든 테스트 가능 (발로란트는 글로벌 게임)
- GitHub 연동 시 PR마다 Preview URL 자동 생성

---

## 개발 환경

```bash
node >= 18.0.0    # Next.js 16 요구사항
npm >= 9.0.0

# 주요 package.json scripts
npm run dev       # 개발 서버 (localhost:3000)
npm run build     # 프로덕션 빌드
npm run start     # 프로덕션 서버 실행
npm run lint      # ESLint
```

---

## `package.json` 주요 의존성

```json
{
  "dependencies": {
    "next": "16.2.4",
    "react": "^19.2.4",
    "react-dom": "^19.2.4",
    "recharts": "^2.x"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4.x",
    "tailwindcss": "^4.x"
  }
}
```
