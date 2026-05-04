> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 02. 발로란트 테마

---

## 테마 설계 원칙

발로란트 공식 UI에서 영감을 받은 다크 테마:
- **배경**: 어두운 네이비 블루 (`#0f1923`)
- **강조색**: 발로란트 레드 (`#ff4655`)
- **패널**: 반투명 레이어 느낌의 어두운 패널
- **텍스트**: 미색/크림 (`#ece8e1`)

---

## CSS 변수 전체 목록

```css
/* globals.css @theme 블록 */
@theme {
  /* ── 배경 / 레이아웃 ── */
  --color-valo-bg:        #0f1923;  /* 최상위 페이지 배경 */
  --color-valo-panel:     #1a2332;  /* 카드, 사이드바 패널 */
  --color-valo-panel-alt: #1e2a3a;  /* 중첩 패널 (약간 밝음) */
  --color-valo-border:    #2a3a4a;  /* 테두리, 구분선 */

  /* ── 텍스트 ── */
  --color-valo-text:      #ece8e1;  /* 주 텍스트 */
  --color-valo-muted:     #8899aa;  /* 보조 텍스트, 레이블 */

  /* ── 강조 ── */
  --color-valo-red:       #ff4655;  /* 브랜드 레드 (버튼, 강조, 활성) */
  --color-valo-cyan:      #00bcd4;  /* 정보, 팀 B 색상 */

  /* ── 역할군 색상 ── */
  --color-role-duelist:   #ff4655;  /* 타격대 */
  --color-role-initiator: #00bcd4;  /* 척후대 */
  --color-role-controller:#4caf50;  /* 전략가 */
  --color-role-sentinel:  #ff9800;  /* 감시자 */

  /* ── 신뢰도 ── */
  --color-confidence-high:   #4caf50;  /* HIGH (초록) */
  --color-confidence-medium: #ff9800;  /* MEDIUM (주황) */
  --color-confidence-low:    #9e9e9e;  /* LOW (회색) */
}
```

---

## 색상 사용 가이드

### 배경 레이어

```
페이지 배경:   --color-valo-bg        (#0f1923)
카드/패널:     --color-valo-panel     (#1a2332)
중첩 요소:     --color-valo-panel-alt (#1e2a3a)
```

### 텍스트 위계

```
제목 / 강조:   --color-valo-text     (#ece8e1)  ← 가장 밝음
일반 텍스트:   --color-valo-text
보조 / 레이블: --color-valo-muted    (#8899aa)  ← 흐림
```

### 상호작용 요소

```
버튼, 링크, 활성 상태: --color-valo-red  (#ff4655)
호버 시: 약간 밝게 (filter: brightness(1.1))
```

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

강조 바, 버튼 호버 등에서 사용:

```css
background: linear-gradient(
  90deg,
  var(--color-valo-red) 0%,
  #ff8c9a 100%
);
```

---

## 글래스모피즘 효과 (선택적)

패널에 미묘한 유리 느낌:

```css
.panel {
  background: rgba(26, 35, 50, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid var(--color-valo-border);
}
```

---

## 색상 접근성

| 조합 | 비율 | 판정 |
|---|---|---|
| `valo-text` on `valo-bg` | 10.5:1 | ✅ AAA |
| `valo-red` on `valo-bg` | 4.8:1 | ✅ AA |
| `valo-muted` on `valo-panel` | 3.2:1 | ⚠️ AA Large only |

`muted` 텍스트는 보조 정보에만 사용 (레이블, 설명). 중요 정보는 `valo-text` 사용.
