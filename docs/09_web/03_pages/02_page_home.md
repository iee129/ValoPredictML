# 02. 홈 페이지 (`/`)

**파일:** `src/app/page.js` + `src/app/page.module.css`

---

## 목적

- 프로젝트 소개 + ValoPredictML 브랜딩
- `/predict`로 빠르게 진입하는 CTA 버튼
- 최근 예측 3건 미리보기 카드
- 전체 통계 요약 (총 예측 수, 평균 승률)

---

## UI 구조

```
┌──────────────────────────────────────────────────────┐
│                      Navbar                          │
├──────────────────────────────────────────────────────┤
│                                                      │
│              ValoPredictML                           │
│     발로란트 팀 조합 기반 승률 예측 시스템              │
│                                                      │
│           [ → 승률 예측 시작하기 ]                   │
│                                                      │
├──────────────────────────────────────────────────────┤
│   📊 총 예측 수     │  🎯 평균 신뢰도  │  🗺️ 지원 맵  │
│     1,234 회       │     72.4%       │    8개       │
├──────────────────────────────────────────────────────┤
│                  최근 예측 기록                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Ascent   │  │ Bind     │  │ Haven    │           │
│  │ 팀A 62%  │  │ 팀A 48%  │  │ 팀A 55%  │           │
│  └──────────┘  └──────────┘  └──────────┘           │
└──────────────────────────────────────────────────────┘
```

---

## 상태 관리

```js
const [stats, setStats] = useState(null);           // 전체 통계
const [recentPredictions, setRecentPredictions] = useState([]);  // 최근 3건
const [loading, setLoading] = useState(true);
```

---

## 데이터 페칭

```js
useEffect(() => {
  const load = async () => {
    try {
      const [analyticsData, historyData] = await Promise.all([
        fetchAnalytics(),
        fetchHistory(3, 0),   // limit=3, offset=0
      ]);
      setStats(analyticsData);
      setRecentPredictions(historyData.items ?? historyData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };
  load();
}, []);
```

`Promise.all`로 두 API를 병렬 호출해 로딩 시간 최소화.

---

## 컴포넌트 구성

```
HomePage
├── HeroSection (인라인, 별도 컴포넌트 없음)
│   ├── 프로젝트 제목 + 설명
│   └── CTA 버튼 (Link → /predict)
│
├── StatsRow
│   ├── StatCard (총 예측 수)
│   ├── StatCard (평균 신뢰도)
│   └── StatCard (지원 맵 수)
│
└── RecentPredictions
    └── PredictionCard × 3 (인라인 렌더링)
```

---

## CTA 버튼

```jsx
<Link href="/predict" className={styles.ctaButton}>
  → 승률 예측 시작하기
</Link>
```

Next.js `<Link>`를 사용해 클라이언트 사이드 네비게이션.

---

## StatCard 데이터 매핑

```js
// fetchAnalytics() 응답에서 추출
<StatCard label="총 예측 수" value={stats?.total_predictions ?? 0} />
<StatCard label="평균 신뢰도" value={`${stats?.avg_confidence ?? 0}%`} />
<StatCard label="지원 맵" value={stats?.map_count ?? 0} />
```

---

## 최근 예측 카드 렌더링

```jsx
{recentPredictions.map((pred, i) => (
  <div key={i} className={styles.predCard}>
    <p className={styles.predMap}>{pred.map}</p>
    <p className={styles.predResult}>
      팀 A {Math.round(pred.win_probability * 100)}%
    </p>
    <span className={styles.predDate}>
      {new Date(pred.created_at).toLocaleDateString('ko-KR')}
    </span>
  </div>
))}
```

---

## 반응형 처리

| 뷰포트 | StatCard | 최근 예측 카드 |
|---|---|---|
| 모바일 (< 640px) | 1열 세로 나열 | 1열 세로 나열 |
| 태블릿 (640px+) | 3열 가로 배치 | 3열 가로 배치 |

---

## 관련 API

- `GET /analytics` → `fetchAnalytics()` — 통계 데이터
- `GET /history?limit=3` → `fetchHistory(3, 0)` — 최근 3건
