# 01. 발로란트 테마 토큰

기존 Streamlit 앱(`app/main.py`)의 팔레트를 그대로 계승해 **프로젝트 전체 시각 일관성**을 맞춘다. Tailwind v4 `@theme` 블록에 CSS 변수로 정의한다.

---

## 1. `src/app/globals.css` — `@theme`

```css
@import "tailwindcss";

@theme {
  /* 배경 (어두운 택티컬) */
  --color-bg:        #07080c;   /* 페이지 최하단 */
  --color-bg-2:      #0d1017;
  --color-panel:     #11151f;   /* 카드/패널 */
  --color-panel-2:   #171c27;   /* 한 단계 밝은 패널 (입력 영역) */
  --color-line:      rgba(255,255,255,0.10);

  /* 텍스트 */
  --color-ink:       #f5f7fb;   /* 본문 (대비 충분) */
  --color-muted:     #9ba3b3;   /* 보조 */

  /* 신호색 (의미 고정 — 00_design_principles §3) */
  --color-red:       #ff4655;   /* 브랜드 · 팀 A · 위험 */
  --color-red-dark:  #b91f2e;
  --color-red-soft:  rgba(255,70,85,0.16);
  --color-cyan:      #29c5e0;   /* 팀 B */
  --color-cyan-soft: rgba(41,197,224,0.12);
  --color-green:     #30d08c;   /* 적합 · 적중 */
  --color-green-soft:rgba(48,208,140,0.14);
  --color-amber:     #ffd166;   /* 주의 · 보통 */

  /* 형태 */
  --radius:          8px;
  --radius-sm:       6px;
  --shadow-card:     0 22px 54px rgba(0,0,0,0.34);

  /* 타이포 */
  --font-sans:    'Pretendard', system-ui, sans-serif;     /* 한국어 본문 */
  --font-display: 'Bebas Neue', 'Pretendard', sans-serif;  /* 큰 숫자/제목 */
}
```

Tailwind v4는 위 변수를 유틸리티로 자동 생성한다 → `bg-panel`, `text-ink`, `text-red`, `border-line` 등.

---

## 2. 타이포그래피 (한국어 가독성 우선)

| 용도 | 폰트 | 크기 | 비고 |
|------|------|------|------|
| 본문/라벨 | Pretendard | 14–16px | 한국어 또렷, 기본 |
| 섹션 제목 | Pretendard 700 | 18–22px | |
| 큰 승률 % | Bebas Neue (tabular) | 48–64px | 숫자만, 한 눈에 |
| 팀명/카드 헤더 | Bebas Neue | 20–28px | 영문 위주 |

> 디스플레이 폰트(Bebas Neue)는 **숫자·짧은 영문 제목에만**. 한국어 문장(근거 카드·경고)은 반드시 Pretendard. 폰트는 `next/font/local` 또는 CDN으로 로드.

```ts
// app/layout.tsx — Pretendard 예 (next/font)
import localFont from "next/font/local";
const pretendard = localFont({ src: "../fonts/PretendardVariable.woff2", variable: "--font-sans" });
```

---

## 3. 발로란트 액센트 — 각진 형태(clip-path), 절제 사용

발로란트 특유의 각진 코너를 **주요 CTA·결과 카드에만** 적용(과용 시 가독성 저하).

```css
/* 주 버튼 / 결과 카드 우상단 모서리 컷 */
.tactical-cut { clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%); }

/* 팀 헤더 좌측 강조 바 */
.team-a-bar { border-left: 3px solid var(--color-red); padding-left: .5rem; }
.team-b-bar { border-left: 3px solid var(--color-cyan); padding-left: .5rem; }
```

| 적용 O | 적용 X |
|--------|--------|
| 예측 버튼, 결과 카드, 승자 배지 | 본문 카드, 표, 입력 필드 |

---

## 4. 대비·접근성 체크 (시연 환경)

- 본문 `--color-ink`(#f5f7fb) on `--color-panel`(#11151f) → 대비 ≈ 14:1 ✅
- 보조 `--color-muted`(#9ba3b3) on panel → ≈ 6:1 ✅ (보조 텍스트 한정)
- 빔프로젝터 대비 저하 대비: 핵심 숫자는 순백 위 레드/시안로 **굵게**.
- 색만으로 구분하지 않기: ✓/△/✗ 배지는 **색 + 기호 + 텍스트** 3중 인코딩(색맹 대응).

---

## 5. 관련 문서

- 디자인 원칙 → [00_design_principles.md](00_design_principles.md)
- 레이아웃 → [02_layout_demo_dashboard.md](02_layout_demo_dashboard.md)
- Tailwind v4 셋업 → [../03_frontend_nextjs/01_setup_and_structure.md](../03_frontend_nextjs/01_setup_and_structure.md)
