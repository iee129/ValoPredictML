> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 04. result 도메인 컴포넌트

`/predict` 페이지에서 예측 결과를 시각화하는 컴포넌트 4개.

---

## WinRateGauge

**파일:** `WinRateGauge.js` + `WinRateGauge.module.css`

### 역할

팀 승률을 Recharts `RadialBarChart`로 원형 게이지 시각화.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `winRate` | number | `0~1` 범위 (e.g. `0.62`) |
| `teamLabel` | string | `"팀 A"` 또는 `"팀 B"` |

### Recharts 구현

```jsx
import { RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts';

const percentage = Math.round(winRate * 100);

const data = [{ name: teamLabel, value: percentage, fill: gaugeColor }];

<RadialBarChart
  width={200}
  height={200}
  innerRadius="60%"
  outerRadius="90%"
  data={data}
  startAngle={90}
  endAngle={-270}
>
  <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
  <RadialBar dataKey="value" cornerRadius={4} background />
  {/* 중앙 텍스트 */}
</RadialBarChart>
```

### 색상 결정 로직

```js
const gaugeColor =
  percentage >= 60 ? '#ff4655' :   // 우세 → 발로란트 레드
  percentage >= 40 ? '#f59e0b' :   // 박빙 → 주황
  '#6b7280';                        // 열세 → 회색
```

### 중앙 퍼센트 표시

Recharts는 SVG 내부에 절대 위치 텍스트를 지원하지 않으므로,
`position: relative` 컨테이너 안에 `position: absolute` 텍스트 오버레이:

```jsx
<div className={styles.wrapper}>
  <RadialBarChart ... />
  <div className={styles.centerLabel}>
    <span className={styles.percentage}>{percentage}%</span>
    <span className={styles.teamLabel}>{teamLabel}</span>
  </div>
</div>
```

---

## ConfidenceBadge

**파일:** `ConfidenceBadge.js` + `ConfidenceBadge.module.css`

### 역할

ML 예측 신뢰도(confidence)를 HIGH / MEDIUM / LOW 배지로 표시.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `confidence` | number | `0~1` 범위 (e.g. `0.78`) |

### 신뢰도 구간

```js
const getLevel = (c) =>
  c >= 0.75 ? 'HIGH' :
  c >= 0.55 ? 'MEDIUM' : 'LOW';
```

### CSS 변수 사용

```css
.high   { color: var(--color-confidence-high);   }   /* #4caf50 */
.medium { color: var(--color-confidence-medium); }   /* #ff9800 */
.low    { color: var(--color-confidence-low);    }   /* #9e9e9e */
```

---

## RoleRadarChart

**파일:** `RoleRadarChart.js` + `RoleRadarChart.module.css`

### 역할

두 팀의 역할군(타격대/척후대/전략가/감시자) 구성 비율을 레이더 차트로 비교.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `teamA` | string[] | 팀 A 요원 이름 배열 |
| `teamB` | string[] | 팀 B 요원 이름 배열 |
| `agents` | Array | 전체 요원 목록 (역할군 조회용) |

### 데이터 변환 로직

```js
const ROLES = ['Duelist', 'Initiator', 'Controller', 'Sentinel'];

const countRoles = (team, agents) => {
  return ROLES.map(role => ({
    role,
    count: team.filter(name =>
      agents.find(a => a.name === name)?.role === role
    ).length
  }));
};

const radarData = ROLES.map((role, i) => ({
  role,
  A: countRoles(teamA, agents)[i].count,
  B: countRoles(teamB, agents)[i].count,
}));
```

### Recharts 구현

```jsx
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend } from 'recharts';

<RadarChart cx={200} cy={200} outerRadius={130} width={400} height={400} data={radarData}>
  <PolarGrid stroke="var(--color-valo-border)" />
  <PolarAngleAxis dataKey="role" tick={{ fill: 'var(--color-valo-muted)' }} />
  <Radar name="팀 A" dataKey="A" stroke="#ff4655" fill="#ff4655" fillOpacity={0.2} />
  <Radar name="팀 B" dataKey="B" stroke="#00bcd4" fill="#00bcd4" fillOpacity={0.2} />
  <Legend />
</RadarChart>
```

---

## FeatureImportanceBar

**파일:** `FeatureImportanceBar.js` + `FeatureImportanceBar.module.css`

### 역할

ML 모델이 예측에 사용한 피처 중요도를 가로 바 차트로 표시.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `features` | Array | `[{ name, importance }]` 배열 |

### 예시 데이터 구조

```json
[
  { "name": "팀 조합 다양성", "importance": 0.34 },
  { "name": "공격/수비 밸런스", "importance": 0.28 },
  { "name": "맵 메타 적합도",  "importance": 0.22 },
  { "name": "역할군 커버리지", "importance": 0.16 }
]
```

### 렌더링

```jsx
{features.map(f => (
  <div key={f.name} className={styles.row}>
    <span className={styles.featureName}>{f.name}</span>
    <div className={styles.barTrack}>
      <div
        className={styles.barFill}
        style={{ width: `${f.importance * 100}%` }}
      />
    </div>
    <span className={styles.featureValue}>
      {(f.importance * 100).toFixed(1)}%
    </span>
  </div>
))}
```

### CSS

```css
.barFill {
  background: linear-gradient(90deg, var(--color-valo-red), #ff8c9a);
  @apply h-full rounded-full transition-all duration-500;
}
```
