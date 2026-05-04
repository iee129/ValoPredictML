> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 01. Recharts 사용 가이드

---

## 사용 컴포넌트 목록

| 컴포넌트 | Recharts 차트 타입 | 용도 |
|---|---|---|
| `WinRateGauge` | `RadialBarChart` | 팀 승률 원형 게이지 |
| `RoleRadarChart` | `RadarChart` | 역할군 조합 비교 |

> Analytics 페이지의 바 차트는 Recharts 미사용 → `07_visualization/02_custom_css_charts.md` 참조

---

## 설치

```bash
npm install recharts
```

현재 버전: `recharts@2.x`

---

## WinRateGauge — RadialBarChart

### Recharts 컴포넌트 임포트

```js
import {
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
} from 'recharts';
```

### 데이터 구조

```js
const percentage = Math.round(winRate * 100);

const data = [{
  name: teamLabel,
  value: percentage,
  fill: gaugeColor,  // 동적 색상
}];
```

### 차트 설정

```jsx
<RadialBarChart
  width={200}
  height={200}
  innerRadius="60%"    // 내부 반지름 (도넛 구멍 크기)
  outerRadius="90%"    // 외부 반지름
  data={data}
  startAngle={90}      // 12시 방향에서 시작
  endAngle={-270}      // 시계방향으로 360도
>
  {/* 전체 범위 고정 (0~100) */}
  <PolarAngleAxis
    type="number"
    domain={[0, 100]}
    angleAxisId={0}
    tick={false}
  />
  {/* 게이지 바 */}
  <RadialBar
    dataKey="value"
    cornerRadius={4}
    background       // 빈 트랙 배경 표시
  />
</RadialBarChart>
```

### 중앙 텍스트 오버레이

Recharts SVG 내부에 텍스트를 절대 위치로 넣을 수 없으므로:

```css
/* WinRateGauge.module.css */
.wrapper {
  position: relative;
  display: inline-flex;
}

.centerLabel {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
```

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

## RoleRadarChart — RadarChart

### Recharts 컴포넌트 임포트

```js
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  Legend,
  ResponsiveContainer,
} from 'recharts';
```

### 데이터 변환

```js
const ROLES = ['Duelist', 'Initiator', 'Controller', 'Sentinel'];

const getRoleCount = (team, role) =>
  team.filter(name => agents.find(a => a.name === name)?.role === role).length;

const radarData = ROLES.map(role => ({
  role,
  A: getRoleCount(teamA, role),
  B: getRoleCount(teamB, role),
}));

// 예시:
// [
//   { role: 'Duelist', A: 2, B: 1 },
//   { role: 'Initiator', A: 1, B: 2 },
//   { role: 'Controller', A: 1, B: 1 },
//   { role: 'Sentinel', A: 1, B: 1 },
// ]
```

### 차트 설정

```jsx
<ResponsiveContainer width="100%" height={320}>
  <RadarChart data={radarData}>
    <PolarGrid
      stroke="var(--color-valo-border)"
    />
    <PolarAngleAxis
      dataKey="role"
      tick={{ fill: 'var(--color-valo-muted)', fontSize: 12 }}
    />
    <Radar
      name="팀 A"
      dataKey="A"
      stroke="var(--color-valo-red)"
      fill="var(--color-valo-red)"
      fillOpacity={0.25}
    />
    <Radar
      name="팀 B"
      dataKey="B"
      stroke="var(--color-valo-cyan)"
      fill="var(--color-valo-cyan)"
      fillOpacity={0.25}
    />
    <Legend
      formatter={(value) => (
        <span style={{ color: 'var(--color-valo-muted)' }}>{value}</span>
      )}
    />
  </RadarChart>
</ResponsiveContainer>
```

### `ResponsiveContainer` 사용 이유

- `width`, `height`를 고정값 대신 `%`로 지정
- 부모 컨테이너에 맞게 자동 리사이즈
- 반응형 레이아웃에서 필수

---

## Recharts 다크 테마 적용 주의사항

Recharts는 기본적으로 라이트 테마 색상을 사용함.
다크 테마로 맞추려면 각 요소에 명시적으로 색상 지정 필요:

```jsx
// PolarGrid 테두리
<PolarGrid stroke="var(--color-valo-border)" />

// 축 레이블
<PolarAngleAxis tick={{ fill: 'var(--color-valo-muted)' }} />

// Legend
<Legend formatter={(v) => <span style={{ color: 'var(--color-valo-muted)' }}>{v}</span>} />
```
