# 02. /history 페이지 테스트

## 1. 페이지 개요

```
URL: http://localhost:3000/history
     https://your-app.vercel.app/history
```

과거 예측 기록을 조회하고 필터링하는 페이지입니다.

---

## 2. UI 컴포넌트 구성

```
/history 페이지
├── PageHeader           — "예측 기록" 제목, 총 건수 표시
├── FilterPanel
│   └── MapFilter        — 맵별 필터 드롭다운
├── HistoryTable         — 예측 기록 테이블
│   ├── HistoryRow       — 각 행: 날짜, 맵, 팀 구성, 승률, 신뢰도
│   └── EmptyState       — 기록 없을 때 표시
└── Pagination           — 이전/다음 페이지 버튼
```

---

## 3. 수동 테스트 플로우

### Step 1: 페이지 진입

```
접속: http://localhost:3000/history

확인 항목:
- [ ] GET /history API 호출 (Network 탭)
- [ ] 기록이 있으면 테이블 표시
- [ ] 기록이 없으면 EmptyState 메시지 표시 ("아직 예측 기록이 없습니다")
- [ ] 총 건수 표시 ("총 142건")
```

### Step 2: 기록 테이블 내용 확인

```
확인 항목:
- [ ] 날짜/시간 형식: "2024-01-15 18:30" (또는 "3시간 전")
- [ ] 맵 이름 표시
- [ ] 팀 A 요원 목록 (5명)
- [ ] 팀 B 요원 목록 (5명)
- [ ] 승률 표시: "67.3%" 또는 게이지 바
- [ ] 신뢰도 배지: high(초록)/medium(노랑)/low(회색)
- [ ] 최신 기록이 상단에 표시 (내림차순)
```

### Step 3: 맵 필터링

```
동작: 필터 드롭다운에서 "Ascent" 선택

확인 항목:
- [ ] GET /history?map=Ascent API 호출
- [ ] 테이블이 Ascent 기록만 표시
- [ ] 총 건수가 필터링된 수로 업데이트
- [ ] "전체" 선택 시 필터 해제, 전체 기록 재조회
```

### Step 4: 페이지네이션

```
동작: "다음 페이지" 버튼 클릭

확인 항목:
- [ ] GET /history?limit=20&offset=20 API 호출
- [ ] 다음 20건 표시
- [ ] 현재 페이지 번호 표시 ("1 / 8 페이지")
- [ ] 첫 페이지에서 "이전" 버튼 비활성화
- [ ] 마지막 페이지에서 "다음" 버튼 비활성화
```

### Step 5: 기록 상세 (선택적)

```
동작: 특정 기록 행 클릭

확인 항목 (기능 구현 시):
- [ ] 상세 모달 또는 페이지로 이동
- [ ] 역할군 분포, 피처 중요도 재표시
```

---

## 4. 엣지 케이스 UI 테스트

### TC-UI-H-001: 빈 기록 상태

```
사전조건: 예측 기록 0건
기대: "아직 예측 기록이 없습니다" 메시지
     "/predict 페이지로 이동" 링크 또는 버튼
```

### TC-UI-H-002: 필터 결과 없음

```
동작: 기록이 없는 맵으로 필터 선택
기대: "해당 맵의 기록이 없습니다" 메시지
```

### TC-UI-H-003: API 오류 처리

```
사전조건: 백엔드 서버 중단
기대: 에러 메시지 표시 ("데이터를 불러올 수 없습니다")
     재시도 버튼
```

### TC-UI-H-004: 대용량 기록 페이지네이션

```
사전조건: 1000건 이상 기록
기대: 페이지네이션 정상 동작
     50페이지 이동 시 올바른 offset 계산
     총 건수 정확 표시
```

---

## 5. Next.js 컴포넌트 테스트

```typescript
// frontend/__tests__/history-page.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { rest } from "msw";
import { setupServer } from "msw/node";
import HistoryPage from "@/app/history/page";

const MOCK_HISTORY_RESPONSE = {
  total: 3,
  limit: 20,
  offset: 0,
  items: [
    {
      id: 3,
      created_at: "2024-01-15T18:30:00+00:00",
      map: "Ascent",
      team_a_agents: ["Jett","Sova","Viper","Killjoy","Skye"],
      team_b_agents: ["Reyna","Breach","Omen","Cypher","Fade"],
      win_probability: 0.673,
      confidence: "medium",
    },
    {
      id: 2,
      created_at: "2024-01-15T17:00:00+00:00",
      map: "Bind",
      team_a_agents: ["Neon","Fade","Viper","Sage","Cypher"],
      team_b_agents: ["Jett","Sova","Omen","Killjoy","Skye"],
      win_probability: 0.42,
      confidence: "low",
    },
    {
      id: 1,
      created_at: "2024-01-15T16:00:00+00:00",
      map: "Ascent",
      team_a_agents: ["Iso","Gekko","Astra","Chamber","KAY/O"],
      team_b_agents: ["Yoru","Breach","Harbor","Deadlock","Tejo"],
      win_probability: 0.78,
      confidence: "high",
    },
  ],
};

const server = setupServer(
  rest.get("/history", (req, res, ctx) => {
    const map = req.url.searchParams.get("map");
    if (map) {
      const filtered = {
        ...MOCK_HISTORY_RESPONSE,
        items: MOCK_HISTORY_RESPONSE.items.filter(i => i.map === map),
        total: MOCK_HISTORY_RESPONSE.items.filter(i => i.map === map).length,
      };
      return res(ctx.json(filtered));
    }
    return res(ctx.json(MOCK_HISTORY_RESPONSE));
  }),
  rest.get("/maps", (req, res, ctx) =>
    res(ctx.json({
      maps: [
        { name: "Ascent", name_kr: "어센트", region: "Italy", callouts: [] },
        { name: "Bind", name_kr: "바인드", region: "Morocco", callouts: [] },
      ],
      total: 2,
    }))
  )
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("/history 페이지", () => {
  it("기록 목록이 렌더링됨", async () => {
    render(<HistoryPage />);
    expect(await screen.findByText("Ascent")).toBeInTheDocument();
    expect(await screen.findByText("Bind")).toBeInTheDocument();
  });

  it("총 건수가 표시됨", async () => {
    render(<HistoryPage />);
    expect(await screen.findByText(/총 3건/)).toBeInTheDocument();
  });

  it("맵 필터 선택 시 API 재호출", async () => {
    const user = userEvent.setup();
    render(<HistoryPage />);

    await waitFor(() => screen.getByRole("combobox", { name: /맵 필터/ }));
    await user.selectOptions(
      screen.getByRole("combobox", { name: /맵 필터/ }),
      "Ascent"
    );

    // Ascent 기록만 표시 (2건)
    await waitFor(() => {
      expect(screen.queryAllByText("Bind").length).toBe(0);
    });
  });

  it("빈 기록 시 EmptyState 표시", async () => {
    server.use(
      rest.get("/history", (req, res, ctx) =>
        res(ctx.json({ total: 0, limit: 20, offset: 0, items: [] }))
      )
    );
    render(<HistoryPage />);
    expect(await screen.findByText(/기록이 없습니다/)).toBeInTheDocument();
  });

  it("API 오류 시 에러 메시지 표시", async () => {
    server.use(
      rest.get("/history", (req, res, ctx) =>
        res(ctx.status(500), ctx.json({ detail: "서버 오류" }))
      )
    );
    render(<HistoryPage />);
    expect(await screen.findByText(/불러올 수 없습니다/)).toBeInTheDocument();
  });
});
```

---

## 6. Playwright E2E 테스트

```typescript
// tests/e2e/history.spec.ts
import { test, expect } from "@playwright/test";

test.describe("/history 페이지", () => {
  test.beforeEach(async ({ page }) => {
    // 사전: /predict에서 예측 1건 수행
    await page.goto("/predict");
    // (요원 선택 및 예측 수행 생략 — beforeAll에서 처리)
    await page.goto("/history");
  });

  test("기록 페이지 제목 표시", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("예측 기록");
  });

  test("맵 필터 동작", async ({ page }) => {
    await page.selectOption("[data-testid=map-filter]", "Ascent");
    await expect(page.locator("[data-testid=history-row]").first())
      .toContainText("Ascent");
  });

  test("페이지네이션 next 버튼", async ({ page }) => {
    const nextBtn = page.getByRole("button", { name: "다음" });
    if (await nextBtn.isEnabled()) {
      await nextBtn.click();
      await expect(page.locator("[data-testid=current-page]")).toContainText("2");
    }
  });
});
```

---

## 7. 체크리스트 요약

| 항목 | 수동 | 자동 (RTL) | 자동 (E2E) |
|------|------|-----------|-----------|
| 기록 목록 표시 | Step 2 | test 1 | test 1 |
| 총 건수 | Step 1 | test 2 | - |
| 맵 필터링 | Step 3 | test 3 | test 2 |
| 페이지네이션 | Step 4 | - | test 3 |
| 빈 상태 | TC-UI-H-001 | test 4 | - |
| API 오류 | TC-UI-H-003 | test 5 | - |
| 최신 기록 상단 | Step 2 | - | - |
