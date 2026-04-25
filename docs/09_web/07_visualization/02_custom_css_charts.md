# 02. 커스텀 CSS 바 차트

---

## 개요

Analytics 페이지의 바 차트는 Recharts 없이 **순수 CSS**로 구현.
`width` 스타일 속성에 동적 퍼센트 값을 주입하는 방식.

---

## 인기 요원 차트 구현

### 핵심 로직

```js
// 최대값 기준 상대적 너비 계산
const maxCount = topAgents[0]?.count ?? 1;

// 각 바의 width = (해당 요원 사용 횟수 / 최대 사용 횟수) × 100%
```

### 전체 렌더링 코드

```jsx
<div className={styles.agentChart}>
  {topAgents.map((agent, idx) => {
    const widthPct = (agent.count / maxCount) * 100;

    return (
      <div key={agent.name} className={styles.agentRow}>
        {/* 순위 번호 */}
        <span className={styles.rank}>#{idx + 1}</span>

        {/* 요원 이름 */}
        <span className={styles.agentName}>{agent.name}</span>

        {/* 역할군 배지 */}
        <span
          className={`${styles.roleBadge} ${styles[agent.role.toLowerCase()]}`}
        >
          {agent.role}
        </span>

        {/* 바 트랙 + 채워진 바 */}
        <div className={styles.barTrack}>
          <div
            className={styles.barFill}
            style={{ width: `${widthPct}%` }}
          />
        </div>

        {/* 절대 사용 횟수 */}
        <span className={styles.count}>{agent.count}회</span>
      </div>
    );
  })}
</div>
```

### CSS

```css
@reference "tailwindcss";

.agentChart {
  @apply flex flex-col gap-2;
}

.agentRow {
  @apply flex items-center gap-3;
}

.rank {
  @apply text-xs font-bold w-6 text-right;
  color: var(--color-valo-muted);
}

.agentName {
  @apply text-sm font-medium w-24;
  color: var(--color-valo-text);
}

.roleBadge {
  @apply text-xs px-1.5 py-0.5 rounded font-medium w-20 text-center;
  color: white;
}

/* 역할군별 색상 */
.duelist    { background: var(--color-role-duelist); }
.initiator  { background: var(--color-role-initiator); }
.controller { background: var(--color-role-controller); }
.sentinel   { background: var(--color-role-sentinel); }

/* 바 트랙 (회색 배경) */
.barTrack {
  @apply flex-1 h-5 rounded-full overflow-hidden;
  background: var(--color-valo-border);
}

/* 실제 채워지는 바 */
.barFill {
  @apply h-full rounded-full;
  background: linear-gradient(90deg, var(--color-valo-red), #ff8c9a);
  transition: width 0.6s ease-out;  /* 마운트 시 애니메이션 */
}

.count {
  @apply text-xs w-12 text-right;
  color: var(--color-valo-muted);
}
```

---

## 맵 승률 차트 구현

### 데이터 구조

```json
{
  "map": "Ascent",
  "attack_win_rate": 0.54,
  "defense_win_rate": 0.46,
  "total_games": 312
}
```

### 렌더링 코드

```jsx
{mapStats.map(m => (
  <div key={m.map} className={styles.mapRow}>
    {/* 맵 이름 */}
    <span className={styles.mapName}>{m.map}</span>

    <div className={styles.barGroup}>
      {/* 공격 승률 */}
      <div className={styles.barLine}>
        <span className={styles.barLabel}>공격</span>
        <div className={styles.barTrack}>
          <div
            className={styles.barAttack}
            style={{ width: `${m.attack_win_rate * 100}%` }}
          />
        </div>
        <span className={styles.barValue}>
          {(m.attack_win_rate * 100).toFixed(1)}%
        </span>
      </div>

      {/* 수비 승률 */}
      <div className={styles.barLine}>
        <span className={styles.barLabel}>수비</span>
        <div className={styles.barTrack}>
          <div
            className={styles.barDefense}
            style={{ width: `${m.defense_win_rate * 100}%` }}
          />
        </div>
        <span className={styles.barValue}>
          {(m.defense_win_rate * 100).toFixed(1)}%
        </span>
      </div>
    </div>

    <span className={styles.totalGames}>{m.total_games}게임</span>
  </div>
))}
```

---

## CSS 바 차트 vs Recharts 선택 기준

| 상황 | 권장 |
|---|---|
| 단순 가로 바 | CSS 바 차트 |
| 퍼센트 비교 | CSS 바 차트 |
| 원형/방사형 | Recharts (RadialBar) |
| 다각형/레이더 | Recharts (Radar) |
| 라인 차트, 영역 차트 | Recharts |
| 인터랙티브 툴팁 필요 | Recharts |

---

## 바 채우기 애니메이션

CSS `transition`을 사용해 마운트 시 바가 채워지는 효과:

```css
.barFill {
  transition: width 0.6s ease-out;
}
```

단, **초기값이 0이어야 애니메이션이 작동**. 데이터가 로드된 후 width가 설정되므로 자연스럽게 애니메이션이 발생.
