> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 03. 명명 규칙 및 코드 컨벤션

---

## 파일/폴더 명명 규칙

### 컴포넌트 파일

| 유형 | 규칙 | 예시 |
|---|---|---|
| React 컴포넌트 | PascalCase + `.js` | `AgentCard.js` |
| CSS 모듈 | PascalCase + `.module.css` | `AgentCard.module.css` |
| 페이지 | 소문자 폴더 + `page.js` (Next.js 규칙) | `predict/page.js` |
| 페이지 CSS | `page.module.css` | `predict/page.module.css` |
| 레이아웃 | `layout.js` (Next.js 규칙) | `app/layout.js` |

### 폴더 명명

| 폴더 유형 | 규칙 | 예시 |
|---|---|---|
| 도메인 컴포넌트 | 소문자 단수 | `predict/`, `result/`, `history/` |
| Next.js 라우트 | 소문자 단수 | `app/predict/`, `app/analytics/` |
| 유틸리티 | 소문자 | `lib/` |

---

## Import 별칭

`jsconfig.json`에서 `@/` 별칭을 `src/`로 매핑:

```js
// ✅ 권장 (절대 경로)
import AgentCard from '@/components/predict/AgentCard';
import { fetchAgents } from '@/lib/api';
import styles from './AgentCard.module.css';  // 같은 폴더 CSS는 상대 경로

// ❌ 지양 (상대 경로로 컴포넌트 import)
import AgentCard from '../../components/predict/AgentCard';
```

**규칙:**
- 다른 폴더의 파일 → `@/` 절대 경로
- 같은 폴더의 `.module.css` → 상대 경로 (`./`)

---

## 컴포넌트 코드 컨벤션

### 1. 파일 구조 순서

```js
// 1. 'use client' (클라이언트 컴포넌트인 경우)
'use client';

// 2. React import
import { useState, useEffect } from 'react';

// 3. 외부 라이브러리
import Image from 'next/image';

// 4. 내부 컴포넌트
import AgentCard from '@/components/predict/AgentCard';

// 5. lib 유틸리티
import { fetchAgents } from '@/lib/api';

// 6. CSS 모듈 (마지막)
import styles from './AgentPicker.module.css';

// 7. 상수 (컴포넌트 밖)
const ROLES = ['전체', '타격대', '척후대', '전략가', '감시자'];

// 8. 컴포넌트 함수 (default export)
export default function AgentPicker({ ... }) { ... }
```

### 2. Props 작성 방식

```js
// 구조 분해 할당 사용
export default function AgentCard({ agent, selected, disabled, onClick }) {
  // ...
}

// 기본값은 파라미터에서 직접 설정
export default function StatCard({ label, value, sub = '' }) {
  // ...
}
```

### 3. 이벤트 핸들러 명명

```js
// ✅ handle + 동작 (camelCase)
const handleAgentClick = (name) => { ... };
const handleMapChange = (e) => { ... };
const handlePredict = async () => { ... };
const handlePageChange = (newPage) => { ... };
```

### 4. 상태 변수 명명

```js
// ✅ [명사, set명사] 패턴
const [selectedMap, setSelectedMap] = useState('Ascent');
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
const [result, setResult] = useState(null);
```

---

## CSS 모듈 컨벤션

### 클래스명 규칙

| 패턴 | 사용 상황 | 예시 |
|---|---|---|
| camelCase 단어 | 기본 요소 | `.card`, `.title`, `.wrapper` |
| camelCase 복합어 | 복합 요소 | `.cardSelected`, `.teamLabel` |
| 상태 수식어 | BEM modifier 대신 | `.cardSelected`, `.btnDisabled` |

```css
/* ✅ 좋은 예 */
.card { ... }
.cardSelected { ... }
.cardDisabled { ... }

/* ❌ 지양 (BEM은 사용 안 함) */
.card--selected { ... }
.card__title { ... }
```

### CSS 모듈 파일 구조

```css
/* AgentCard.module.css */

/* 1. 필수 첫 줄: @reference */
@reference "tailwindcss";

/* 2. 기본 스타일 */
.card {
  @apply relative cursor-pointer rounded-lg overflow-hidden;
  border: 1px solid var(--color-valo-border);
  background-color: var(--color-valo-panel);
}

/* 3. 상태 변형 */
.cardSelected {
  border-color: var(--color-valo-red);
}

.cardDisabled {
  @apply opacity-40 cursor-not-allowed;
}

/* 4. 내부 요소 */
.cardImage { ... }
.cardName { ... }
```

---

## 조건부 클래스명 패턴

```js
import styles from './AgentCard.module.css';

// ✅ 템플릿 리터럴로 조건부 클래스 조합
<div className={`${styles.card} ${selected ? styles.cardSelected : ''} ${disabled ? styles.cardDisabled : ''}`}>

// ✅ 배열 + filter + join 패턴
const cls = [
  styles.card,
  selected && styles.cardSelected,
  disabled && styles.cardDisabled,
].filter(Boolean).join(' ');
<div className={cls}>
```

---

## 비동기 처리 패턴

```js
// API 호출 표준 패턴
const handlePredict = async () => {
  setLoading(true);
  setError(null);
  try {
    const data = await predictWinRate(selectedMap, teamA, teamB);
    setResult(data);
  } catch (e) {
    setError(e.message);
  } finally {
    setLoading(false);
  }
};
```

---

## 금지 사항

| 금지 | 이유 |
|---|---|
| JSX에 Tailwind 클래스 직접 사용 | CSS/마크업 분리 원칙 |
| inline `style={{}}` 사용 | CSS 모듈로 대체 |
| `console.log` 프로덕션 코드에 포함 | 디버깅 코드 제거 필수 |
| `any` 타입 (TS 미사용이라 해당 없음) | - |
| 컴포넌트 안에 컴포넌트 중첩 정의 | 리렌더링 성능 문제 |
