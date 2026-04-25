# 06. analytics 도메인 컴포넌트

`/analytics` 페이지에서 통계 데이터를 시각화하는 컴포넌트.

> Analytics 페이지는 별도 컴포넌트 폴더 없이 `page.js` 내부에서 인라인 렌더링.
> Recharts 대신 **순수 CSS** 기반 커스텀 바 차트 사용.

---

## 페이지 구조 (인라인 섹션들)

```
AnalyticsPage
├── 통계 요약 (StatCard × 4)
├── 맵별 승률 섹션
│   └── MapWinRateBar × N (인라인)
└── 인기 요원 TOP 10 섹션
    └── AgentUsageBar × N (인라인)
```

---

## MapWinRateBar (인라인 컴포넌트)

**위치:** `analytics/page.js` 내부에서 직접 렌더링

### 역할

각 맵에 대해 공격/수비 승률을 나란히 표시하는 가로 바.

### 데이터 형태

```json
{
  "map": "Ascent",
  "attack_win_rate": 0.54,
  "defense_win_rate": 0.46,
  "total_games": 312
}
```

### 렌더링 로직

```jsx
{mapStats.map(m => (
  <div key={m.map} className={styles.mapRow}>
    <span className={styles.mapName}>{m.map}</span>
    <div className={styles.barGroup}>
      {/* 공격 승률 바 */}
      <div className={styles.barLabel}>공격</div>
      <div className={styles.barTrack}>
        <div
          className={styles.barAttack}
          style={{ width: `${m.attack_win_rate * 100}%` }}
        />
      </div>
      <span className={styles.barValue}>
        {(m.attack_win_rate * 100).toFixed(1)}%
      </span>
      {/* 수비 승률 바 */}
      <div className={styles.barLabel}>수비</div>
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
    <span className={styles.totalGames}>{m.total_games}게임</span>
  </div>
))}
```

---

## AgentUsageBar (인라인 컴포넌트)

### 역할

인기 요원 TOP 10을 사용 빈도 기준 가로 바 차트로 표시.
**핵심:** 첫 번째 요원(최대값)을 기준으로 나머지 바의 너비를 상대적으로 계산.

### 최대값 기준 상대 폭 계산

```js
const maxCount = topAgents[0]?.count ?? 1;

// 각 요원 바의 width 계산
const barWidth = (agent.count / maxCount) * 100 + '%';
```

### 렌더링

```jsx
{topAgents.map((agent, idx) => (
  <div key={agent.name} className={styles.agentRow}>
    {/* 순위 */}
    <span className={styles.rank}>#{idx + 1}</span>
    {/* 요원 이름 */}
    <span className={styles.agentName}>{agent.name}</span>
    {/* 역할군 배지 */}
    <span className={`${styles.roleBadge} ${styles[agent.role.toLowerCase()]}`}>
      {agent.role}
    </span>
    {/* 상대적 바 */}
    <div className={styles.barTrack}>
      <div
        className={styles.barFill}
        style={{ width: (agent.count / maxCount) * 100 + '%' }}
      />
    </div>
    {/* 절대 사용 횟수 */}
    <span className={styles.count}>{agent.count}회</span>
  </div>
))}
```

---

## CSS 전략: Recharts 사용 안 하는 이유

Analytics 페이지 바 차트에 Recharts를 쓰지 않는 이유:

| 항목 | Recharts | 순수 CSS 바 |
|---|---|---|
| 번들 크기 | 무거움 | 0 (추가 없음) |
| 커스터마이징 | 제한적 | 완전 자유 |
| Tailwind 통합 | 어색함 | 자연스러움 |
| 애니메이션 | JS 기반 | CSS transition |
| 간단한 바 차트 | 오버엔지니어링 | 적합 |

> 복잡한 원형(WinRateGauge) 또는 레이더(RoleRadarChart)는 Recharts 사용,
> 단순 가로 바는 CSS로 직접 구현.

---

## 역할군 배지 색상

```css
.duelist   { background: var(--color-role-duelist);   }   /* #ff4655 */
.initiator { background: var(--color-role-initiator); }   /* #00bcd4 */
.controller{ background: var(--color-role-controller);}   /* #4caf50 */
.sentinel  { background: var(--color-role-sentinel);  }   /* #ff9800 */
```
