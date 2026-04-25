# 04. 반응형 디자인

---

## 브레이크포인트

Tailwind v4 기본 브레이크포인트 사용:

| 이름 | 너비 | 대상 |
|---|---|---|
| (기본) | 0px~ | 모바일 |
| `sm` | 640px~ | 대형 모바일 |
| `md` | 768px~ | 태블릿 |
| `lg` | 1024px~ | 노트북 |
| `xl` | 1280px~ | 데스크톱 |

---

## 페이지별 반응형 레이아웃

### 홈 (/)

```
모바일:     1열 세로 스택
데스크톱:   3열 그리드 (StatCard × 3)
```

```css
.statsGrid {
  @apply grid gap-4;
  grid-template-columns: 1fr;
}

@media (min-width: 768px) {
  .statsGrid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

### 예측 (/predict)

```
모바일:   세로 스택 (MapSelector → 팀A → 팀B → 버튼 → 결과)
데스크톱: 2열 분할 (팀A 선택 | 팀B 선택), 결과는 전체 너비
```

```css
.teamsLayout {
  @apply flex flex-col gap-6;
}

@media (min-width: 1024px) {
  .teamsLayout {
    @apply flex-row;
  }
}
```

### 기록 (/history)

```
모바일:   테이블 가로 스크롤 (overflow-x: auto)
데스크톱: 전체 컬럼 표시
```

```css
.tableWrapper {
  @apply overflow-x-auto;
}

.table {
  @apply min-w-full;
  /* 모바일에서 스크롤, 데스크톱에서 전체 너비 */
}
```

### 분석 (/analytics)

```
모바일:   1열
데스크톱: 2열 (맵 승률 | 인기 요원)
```

```css
.chartsGrid {
  @apply grid gap-6;
  grid-template-columns: 1fr;
}

@media (min-width: 1024px) {
  .chartsGrid {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

---

## Navbar 반응형

```
데스크톱: 로고 + 텍스트 링크 4개
모바일:   로고 + 아이콘만 (텍스트 숨김)
```

```css
/* Navbar.module.css */
.linkText {
  @apply hidden;
}

@media (min-width: 640px) {
  .linkText {
    @apply inline;
  }
}
```

---

## 이미지 반응형

요원 이미지는 `next/image`의 `sizes` prop 활용:

```jsx
<Image
  src={getAgentIconUrl(agent.name)}
  alt={agent.name}
  width={56}
  height={56}
  sizes="(max-width: 768px) 40px, 56px"
/>
```

---

## AgentPicker 그리드

요원 카드 그리드는 `auto-fill`로 뷰포트에 따라 자동 조절:

```css
.agentGrid {
  @apply grid gap-2;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
}

/* 모바일: ~4열 / 데스크톱: ~6-8열 */
```

---

## 주의사항

- 모바일 우선 설계 (`min-width` 미디어쿼리 사용)
- `max-width` 쿼리는 사용하지 않음
- `PageWrapper`의 `max-w-7xl`이 최대 너비를 제한 (1280px)
- 터치 타겟 최소 44×44px 유지 (버튼, 탭)
