> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 02. 발로란트 테마

---

## 테마 설계 원칙

발로란트 공식 UI에서 영감을 받은 **블랙&레드** 다크 테마:
- **배경**: 순수 블랙 (`#07080c`) — 발로란트 공식 UI의 극단적 어둠, Streamlit 앱과 동일
- **강조색**: 발로란트 레드 (`#ff4655`) — 브랜드 원색, 상호작용·활성 상태에 집중 사용
- **패널**: `#11151f` — 배경보다 한 단계 밝은 카드/사이드바
- **텍스트**: 밝은 화이트 (`#f5f7fb`) — 블랙 배경 고대비 확보

이 파일은 09_web 디자인 토큰의 **단일 진실 공급원(SSOT)** 이다.
나머지 컴포넌트·페이지 문서는 hex를 직접 쓰지 않고 `var(--color-valo-*)` 토큰만 참조한다.

---

## CSS 변수 전체 목록

```css
/* globals.css @theme 블록 */
@theme {
  /* ── 배경 / 레이아웃 (순수 블랙 계열) ── */
  --color-valo-bg:        #07080c;  /* 최상위 페이지 배경 — config.toml backgroundColor */
  --color-valo-panel:     #11151f;  /* 카드, 사이드바 — config.toml secondaryBackgroundColor */
  --color-valo-panel-alt: #171c27;  /* 중첩 패널 (한 단계 밝음) */
  --color-valo-border:    #1f2633;  /* 테두리, 구분선 */

  /* ── 텍스트 ── */
  --color-valo-text:      #f5f7fb;  /* 주 텍스트 — config.toml textColor / app --vp-ink */
  --color-valo-muted:     #9ba3b3;  /* 보조 텍스트, 레이블 — app --vp-muted */

  /* ── 브랜드 강조 (레드 스케일) ── */
  --color-valo-red:       #ff4655;  /* 브랜드 레드 — config.toml primaryColor / app --vp-red */
  --color-valo-red-hover: #ff6675;  /* 호버 상태 (밝기 ↑) */
  --color-valo-red-dim:   rgba(255, 70, 85, 0.16);  /* 배경 틴트/강조 바 — app --vp-red-soft */
  --color-valo-red-end:   #ff8c9a;  /* 그라디언트 끝 (기존 하드코딩 토큰화) */
  --color-valo-gold:      #ffd166;  /* 포인트 컬러 — app --vp-gold */

  /* ── 팀 구분색 ── */
  --color-valo-cyan:      #29c5e0;  /* 팀 B 구분색, recharts 시리즈 */

  /* ── 역할군 색상 (블랙 배경 대비 재조정) ── */
  --color-role-duelist:   #ff4655;  /* 타격대 */
  --color-role-initiator: #29c5e0;  /* 척후대 — 채도↑, 블랙 대비 확보 */
  --color-role-controller:#5ccf6f;  /* 전략가 — 채도↑ */
  --color-role-sentinel:  #ffb02e;  /* 감시자 — 채도↑ */

  /* ── 신뢰도 (블랙 배경 대비 재조정) ── */
  --color-confidence-high:   #5ccf6f;  /* HIGH */
  --color-confidence-medium: #ffb02e;  /* MEDIUM */
  --color-confidence-low:    #9aa3b2;  /* LOW — 7.9:1 (AA 4.5:1 상회) */
}
```

---

## Streamlit 앱 정합성 대조표

`app/main.py`의 `--vp-*` 변수와 `config.toml` 값을 문자 단위로 대조한다.

| 문서 토큰 | 토큰 값 | `app/main.py --vp-*` | `config.toml` |
|---|---|---|---|
| `--color-valo-bg` | `#07080c` | `--vp-bg: #07080c` ✓ | `backgroundColor="#07080c"` ✓ |
| `--color-valo-panel` | `#11151f` | `--vp-panel: #11151f` ✓ | `secondaryBackgroundColor="#11151f"` ✓ |
| `--color-valo-panel-alt` | `#171c27` | `--vp-panel-2: #171c27` ✓ | — |
| `--color-valo-text` | `#f5f7fb` | `--vp-ink: #f5f7fb` ✓ | `textColor="#f5f7fb"` ✓ |
| `--color-valo-muted` | `#9ba3b3` | `--vp-muted: #9ba3b3` ✓ | — |
| `--color-valo-red` | `#ff4655` | `--vp-red: #ff4655` ✓ | `primaryColor="#ff4655"` ✓ |
| `--color-valo-red-dim` | `rgba(255,70,85,0.16)` | `--vp-red-soft: rgba(255,70,85,0.16)` ✓ | — |
| `--color-valo-gold` | `#ffd166` | `--vp-gold: #ffd166` ✓ | — |

---

## 색상 사용 가이드

### 배경 레이어

```
페이지 배경:   --color-valo-bg        (#07080c)
카드/패널:     --color-valo-panel     (#11151f)
중첩 요소:     --color-valo-panel-alt (#171c27)
테두리/구분선: --color-valo-border    (#1f2633)
```

### 텍스트 위계

```
제목 / 주요 텍스트: --color-valo-text   (#f5f7fb)  ← 최고 밝기
보조 / 레이블:      --color-valo-muted  (#9ba3b3)  ← 보조 정보만
```

### 상호작용 요소

```
버튼, 링크, 활성 탭:  --color-valo-red       (#ff4655)
호버:                  --color-valo-red-hover  (#ff6675)
배경 틴트/강조 바:     --color-valo-red-dim    (rgba 16%)
```

### 레드 사용 원칙

1. **포인트만** — CTA 버튼·활성 탭·섹션 좌측 강조 바·선택 테두리에 집중. 텍스트 전체나 큰 면적에 남용 금지.
2. **역할군·신뢰도는 기능색** — 브랜드 레드와 혼용하지 않음. 의미 구분 유지.
3. **그라디언트 끝**: `--color-valo-red` → `--color-valo-red-end` (#ff8c9a). hex 직접 쓰지 않음.

---

## 역할군 색상 활용 예시

```css
/* AgentCard.module.css */
@reference "tailwindcss";

.roleDot {
  @apply w-2 h-2 rounded-full inline-block;
  /* background는 JS에서 style={{ backgroundColor: ROLE_COLORS[role] }} */
}
```

```js
// 컴포넌트 내 매핑
const ROLE_COLORS = {
  'Duelist':    'var(--color-role-duelist)',
  'Initiator':  'var(--color-role-initiator)',
  'Controller': 'var(--color-role-controller)',
  'Sentinel':   'var(--color-role-sentinel)',
};
```

---

## 발로란트 레드 그라디언트

피처 중요도 바, 강조 요소 등에서 사용:

```css
background: linear-gradient(
  90deg,
  var(--color-valo-red)     0%,
  var(--color-valo-red-end) 100%
);
```

---

## 글래스모피즘 효과 (선택적)

패널에 미묘한 깊이감:

```css
.panel {
  background: rgba(17, 21, 31, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid var(--color-valo-border);
}
```

---

## 색상 접근성

배경 `#07080c` 기준 WCAG 2.1 대비비 (구 네이비 계열에서 블랙으로 전환, 전반적 상향):

| 조합 | 비율 | 판정 |
|---|---|---|
| `valo-text` (#f5f7fb) on `valo-bg` | 18.7:1 | ✅ AAA |
| `valo-red` (#ff4655) on `valo-bg` | 6.0:1 | ✅ AA |
| `valo-red-hover` (#ff6675) on `valo-bg` | 7.1:1 | ✅ AAA |
| `valo-muted` (#9ba3b3) on `valo-bg` | 7.9:1 | ✅ AAA |
| `confidence-low` (#9aa3b2) on `valo-bg` | 7.9:1 | ✅ AAA |
| `role-controller` / `confidence-high` (#5ccf6f) on `valo-bg` | 10.1:1 | ✅ AAA |
| `role-initiator` / `valo-cyan` (#29c5e0) on `valo-bg` | 9.7:1 | ✅ AAA |
| `role-sentinel` / `confidence-medium` (#ffb02e) on `valo-bg` | 11.0:1 | ✅ AAA |

`muted` 텍스트는 보조 정보에만 사용 (레이블, 설명). 중요 정보는 `valo-text` 사용.
