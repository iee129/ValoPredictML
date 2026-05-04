> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 03. 예측 페이지 (`/predict`)

**파일:** `src/app/predict/page.js` + `src/app/predict/page.module.css`

가장 복잡한 페이지. 요원 선택 → 예측 요청 → 결과 표시 전체 흐름을 담당.

---

## UI 구조

```
┌──────────────────────────────────────────────────────────────┐
│                         Navbar                               │
├──────────────────────────────────────────────────────────────┤
│  🗺️ 맵 선택:  [ Ascent ▼ ]                                   │
├──────────────────────────────────────────────────────────────┤
│  팀 A 슬롯 (5개)              │  팀 B 슬롯 (5개)              │
│  ○ ○ ○ ○ ○                   │  ○ ○ ○ ○ ○                   │
├──────────────────────────────────────────────────────────────┤
│  [전체] [타격대] [척후대] [전략가] [감시자]  (팀 A용)          │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ...                        │
│  │Jett │ │Reyna│ │Neon │ │Yoru │                            │
│  └─────┘ └─────┘ └─────┘ └─────┘                            │
├──────────────────────────────────────────────────────────────┤
│  [전체] [타격대] [척후대] [전략가] [감시자]  (팀 B용)          │
│  ┌─────┐ ┌─────┐ ...                                         │
├──────────────────────────────────────────────────────────────┤
│              [ 승률 예측하기 ]                                │
├──────────────────────────────────────────────────────────────┤
│  (예측 후)                                                    │
│  ┌─────────────┐          ┌─────────────┐                   │
│  │  팀 A 62%   │          │  팀 B 38%   │                   │
│  │  (게이지)   │          │  (게이지)   │                   │
│  └─────────────┘          └─────────────┘                   │
│  신뢰도: [HIGH]                                              │
│  역할군 비교 레이더 차트                                       │
│  피처 중요도 바 차트                                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 상태 변수

```js
const [maps, setMaps] = useState([]);              // 맵 목록 (API)
const [agents, setAgents] = useState([]);           // 요원 목록 (API)
const [selectedMap, setSelectedMap] = useState(''); // 선택된 맵
const [teamA, setTeamA] = useState([]);             // 팀 A 요원 이름 배열
const [teamB, setTeamB] = useState([]);             // 팀 B 요원 이름 배열
const [result, setResult] = useState(null);         // 예측 결과
const [loading, setLoading] = useState(false);      // 예측 로딩 중
const [error, setError] = useState(null);           // 에러 메시지
```

---

## 초기 데이터 로드

```js
useEffect(() => {
  const init = async () => {
    const [mapsData, agentsData] = await Promise.all([
      fetchMaps(),
      fetchAgents(),
    ]);
    setMaps(mapsData.maps ?? mapsData);
    setAgents(agentsData.agents ?? agentsData);
    if (mapsData.maps?.length > 0) {
      setSelectedMap(mapsData.maps[0]);  // 첫 번째 맵 기본 선택
    }
  };
  init();
}, []);
```

---

## 교차 팀 필터링 로직

같은 요원이 팀 A와 팀 B 양쪽에 선택되지 않도록 필터링.

```js
const allSelected = [...teamA, ...teamB];

// 팀 A AgentPicker에 전달되는 요원 목록
// → 팀 B가 선택했거나 팀 A가 이미 5명이면 disabled
const availableForA = agents.filter(
  a => !teamB.includes(a.name)
);

// 팀 B AgentPicker에 전달되는 요원 목록
const availableForB = agents.filter(
  a => !teamA.includes(a.name)
);
```

`AgentPicker`는 `allSelected` prop을 받아 disabled 처리:
```js
const isDisabled = (name) =>
  !isSelected(name) && selectedTeam.length >= 5;
```

---

## 예측 요청 핸들러

```js
const handlePredict = async () => {
  if (teamA.length !== 5 || teamB.length !== 5) {
    setError('양 팀 모두 5명의 요원을 선택해야 합니다.');
    return;
  }
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

## 예측 결과 (`result`) 구조

```js
{
  win_probability: 0.623,       // 팀 A 승률 (0~1)
  lose_probability: 0.377,      // 팀 B 승률 (= 1 - win_probability)
  confidence: "high",           // "high" | "medium" | "low"
  team_a_role_counts: {         // 팀 A 역할군 카운트
    Duelist: 2,
    Initiator: 1,
    Controller: 1,
    Sentinel: 1,
  },
  team_b_role_counts: { ... },
  feature_importance: [         // 상위 5개 피처 중요도
    { feature: "map_Ascent", importance: 0.14 },
    { feature: "team_a_duelist_count", importance: 0.11 },
    // ...
  ]
}
```

---

## 결과 렌더링 조건

```jsx
{result && (
  <div className={styles.resultSection}>
    {/* 승률 게이지 */}
    <div className={styles.gaugeRow}>
      <WinRateGauge winProbability={result.win_probability} teamLabel="팀 A" />
      <WinRateGauge winProbability={result.lose_probability} teamLabel="팀 B" />
    </div>

    {/* 신뢰도 배지 */}
    <ConfidenceBadge confidence={result.confidence} />

    {/* 역할군 레이더 */}
    <RoleRadarChart
      teamA={result.team_a_role_counts}
      teamB={result.team_b_role_counts}
    />

    {/* 피처 중요도 */}
    <FeatureImportanceBar data={result.feature_importance} />
  </div>
)}
```

---

## PredictButton 활성화 조건

```js
disabled={loading || teamA.length !== 5 || teamB.length !== 5}
```

---

## API 명세

| 메서드 | URL | 역할 |
|---|---|---|
| `GET` | `/maps` | 맵 목록 |
| `GET` | `/agents` | 요원 목록 + 역할군 |
| `POST` | `/predict` | 승률 예측 |

**POST /predict 요청 본문:**
```json
{
  "map": "Ascent",
  "team_a": ["Jett", "Sage", "Brimstone", "Sova", "Cypher"],
  "team_b": ["Reyna", "Viper", "Omen", "Fade", "Killjoy"]
}
```

---

## 관련 문서

- 요원 선택 UI 상세: [04_components/03_predict_components.md](../04_components/03_predict_components.md)
- 결과 시각화 컴포넌트: [04_components/04_result_components.md](../04_components/04_result_components.md)
- API 통신 상세: [08_api_integration/01_api_client.md](../08_api_integration/01_api_client.md)
