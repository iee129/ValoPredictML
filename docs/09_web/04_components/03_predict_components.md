# 03. predict 도메인 컴포넌트

`/predict` 페이지에서 요원 선택 입력 UI를 담당하는 컴포넌트 6개.

---

## AgentPicker

**파일:** `AgentPicker.js` + `AgentPicker.module.css`

### 역할

요원 전체 목록을 그리드로 표시하고, 역할군 탭으로 필터링. 한 팀의 요원 선택 UI 전체를 담당.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `agents` | Array | 이미 교차 팀 필터링된 요원 목록 |
| `selectedTeam` | string[] | 현재 팀에서 선택된 요원 이름 배열 |
| `teamLabel` | string | `"팀 A"` 또는 `"팀 B"` |
| `onAgentSelect` | fn(name) | 요원 선택 콜백 |
| `onAgentRemove` | fn(name) | 요원 선택 해제 콜백 |

### 내부 상태

```js
const [activeRole, setActiveRole] = useState('전체');
```

### 역할군 → 영문 매핑

```js
const ROLE_MAP = {
  '타격대': 'Duelist',
  '척후병': 'Initiator',
  '전략가': 'Controller',
  '감시자': 'Sentinel',
};
```

### 요원 필터링 로직

```js
const filtered = activeRole === '전체'
  ? agents
  : agents.filter(a => a.role === ROLE_MAP[activeRole]);

const isSelected = (name) => selectedTeam.includes(name);
const isDisabled = (name) => !isSelected(name) && selectedTeam.length >= 5;
```

### 구조

```
AgentPicker
├── 팀 레이블 + 선택 카운트 (X/5)
├── RoleFilter (탭)
└── 요원 그리드
    └── AgentCard × N (onClick으로 select/remove)
```

---

## AgentCard

**파일:** `AgentCard.js` + `AgentCard.module.css`

### 역할

개별 요원 카드. 이미지 + 이름 + 역할군 색상 표시. 클릭으로 선택/해제.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `agent` | `{ name, role }` | 요원 데이터 |
| `selected` | boolean | 선택 여부 |
| `disabled` | boolean | 비활성화 여부 |
| `onClick` | fn() | 클릭 콜백 |

### 이미지 소스

```js
import { getAgentIconUrl } from '@/lib/agentImage';
// src={getAgentIconUrl(agent.name)}
// → https://media.valorant-api.com/agents/{uuid}/displayicon.png
```

### 시각적 상태 표현

| 상태 | 표현 |
|---|---|
| 기본 | 어두운 패널 배경, 회색 테두리 |
| selected | 빨간 테두리(`--color-valo-red`) + 체크 오버레이 |
| disabled (5명 초과) | `opacity-40`, `cursor-not-allowed` |
| hover | `scale-105`, 테두리 색상 강조 |

### 역할군 색상 표시

카드 하단에 역할군 색상 도트:
```jsx
<span
  className={styles.roleDot}
  style={{ backgroundColor: ROLE_COLORS[agent.role] }}
/>
```

---

## MapSelector

**파일:** `MapSelector.js` + `MapSelector.module.css`

### 역할

맵 선택 드롭다운.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `maps` | string[] | 맵 이름 목록 |
| `selected` | string | 현재 선택된 맵 |
| `onChange` | fn(map) | 변경 콜백 |

### 구현

```jsx
<select
  className={styles.select}
  value={selected}
  onChange={(e) => onChange(e.target.value)}
>
  {maps.map(map => (
    <option key={map} value={map}>{map}</option>
  ))}
</select>
```

---

## RoleFilter

**파일:** `RoleFilter.js` + `RoleFilter.module.css`

### 역할

역할군 탭 필터. `AgentPicker` 내부에서 사용.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `active` | string | 현재 활성 탭 (`'전체'` 등) |
| `onChange` | fn(role) | 탭 변경 콜백 |

### 탭 구성

```js
const ROLES = ['전체', '타격대', '척후병', '전략가', '감시자'];
```

각 탭 버튼: `active === role` 이면 `styles.tabActive`, 아니면 `styles.tab`.

---

## TeamSlot

**파일:** `TeamSlot.js` + `TeamSlot.module.css`

### 역할

선택된 팀 요원을 슬롯 5개로 미리보기.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `agents` | Array | 전체 요원 목록 (이미지 URL 조회용) |
| `selected` | string[] | 선택된 요원 이름 배열 |
| `label` | string | `"팀 A"` 또는 `"팀 B"` |

### 렌더링 로직

```jsx
{Array.from({ length: 5 }, (_, i) => {
  const agentName = selected[i];
  return agentName ? (
    <Image src={getAgentIconUrl(agentName)} alt={agentName} width={40} height={40} />
  ) : (
    <div className={styles.emptySlot} />  // 빈 원형
  );
})}
```

---

## PredictButton

**파일:** `PredictButton.js` + `PredictButton.module.css`

### 역할

예측 요청 버튼. 로딩 상태 표시 포함.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `onClick` | fn() | 클릭 콜백 |
| `disabled` | boolean | 비활성화 여부 |
| `loading` | boolean | 로딩 상태 |

### 상태별 텍스트

```js
const label = loading ? '예측 중...' : '승률 예측하기';
```

### 활성화 조건 (parent에서 전달)

```js
// predict/page.js
<PredictButton
  onClick={handlePredict}
  disabled={loading || teamA.length !== 5 || teamB.length !== 5}
  loading={loading}
/>
```
