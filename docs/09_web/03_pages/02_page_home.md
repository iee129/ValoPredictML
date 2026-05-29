> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

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

## 비주얼 스펙

### 배경 레이아웃

| 영역 | 토큰 | 비고 |
|------|------|------|
| 페이지 전체 | `var(--color-valo-bg)` | 순수 블랙 — body/main 배경 |
| StatCard | `var(--color-valo-panel)` | 1px `var(--color-valo-border)` 테두리 |
| 최근 예측 카드 | `var(--color-valo-panel)` | hover 시 상단 레드 강조선 전환 |

---

### 히어로 섹션 타이포그래피

```css
/* page.module.css */
.heroTitle {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(3rem, 8vw, 6rem);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-valo-text);
}

.heroSub {
  font-family: Pretendard, sans-serif;
  font-size: 1rem;
  color: var(--color-valo-muted);
}
```

---

### clip-path 적용 지점

발로란트 UI의 정체성인 우상단 모서리 잘림을 핵심 요소 두 곳에 적용한다.

| 컴포넌트 | clip-path 사용 이유 |
|----------|---------------------|
| CTA 버튼 (`→ 승률 예측 시작하기`) | 주 행동 유도 요소 — 택티컬 UI 정체성 강조 |
| StatCard | 수치 강조 카드 — 위계 시각화 |

```css
/* CTA 버튼 — 우상단 10px 잘림 */
.ctaButton {
  clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%);
  background: var(--color-valo-red);
  color: var(--color-valo-text);
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.1rem;
  letter-spacing: 0.08em;
  padding: 0.75rem 2rem;
  transition: background 0.2s ease;
}
.ctaButton:hover {
  background: var(--color-valo-red-hover);
}

/* StatCard — 우상단 8px 잘림 */
.statCard {
  clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%);
  background: var(--color-valo-panel);
  border: 1px solid var(--color-valo-border);
  padding: 1.25rem 1.5rem;
}
.statValue {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2rem;
  color: var(--color-valo-red);
}
.statLabel {
  font-family: Pretendard, sans-serif;
  font-size: 0.75rem;
  color: var(--color-valo-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```

---

### 레드 강조 포인트

| 요소 | 강조 방식 | 토큰 |
|------|-----------|------|
| CTA 버튼 | 배경 + clip-path | `--color-valo-red` · `--color-valo-red-hover` |
| 섹션 헤더 (`최근 예측 기록`) | 좌측 3px 세로 강조 바 | `--color-valo-red` |
| StatCard 수치 | 텍스트 강조색 | `--color-valo-red` |
| 최근 예측 카드 (hover) | 상단 2px `border-top` | `--color-valo-red` |

```css
/* 섹션 헤더 강조 바 패턴 */
.sectionHeader {
  border-left: 3px solid var(--color-valo-red);
  padding-left: 0.75rem;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.4rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-valo-text);
}

/* 최근 예측 카드 상태 */
.predCard {
  background: var(--color-valo-panel);
  border: 1px solid var(--color-valo-border);
  border-top: 2px solid var(--color-valo-border);
  transition: border-top-color 0.2s ease;
}
.predCard:hover {
  border-top-color: var(--color-valo-red);
}
.predMap {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.2rem;
  letter-spacing: 0.04em;
  color: var(--color-valo-text);
}
.predResult {
  font-family: Pretendard, sans-serif;
  color: var(--color-valo-muted);
}
.predDate {
  font-family: Pretendard, sans-serif;
  font-size: 0.7rem;
  color: var(--color-valo-muted);
}
```

---

## 관련 API

- `GET /analytics` → `fetchAnalytics()` — 통계 데이터
- `GET /history?limit=3` → `fetchHistory(3, 0)` — 최근 3건
