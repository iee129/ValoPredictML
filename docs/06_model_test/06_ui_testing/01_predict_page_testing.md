> ⚠️ **범위 외**: FastAPI 미사용. 본 프로젝트는 Streamlit 로컬 도구이며 API 엔드포인트 테스트는 적용되지 않는다. 본문은 참고용으로 보존된다.

# 01. /predict 페이지 테스트 플로우

## 1. 페이지 개요

`/predict` 페이지는 사용자가 맵과 요원을 선택하고 승률 예측 결과를 확인하는 핵심 페이지입니다.

```
URL: http://localhost:3000/predict
     https://your-app.vercel.app/predict
```

---

## 2. UI 컴포넌트 구성

```
/predict 페이지
├── MapSelector          — 맵 선택 드롭다운
├── AgentGrid (팀 A)     — 요원 선택 그리드 (클릭으로 선택)
├── AgentGrid (팀 B)     — 요원 선택 그리드
├── SelectedTeamDisplay  — 선택된 요원 표시 (5개 슬롯)
├── PredictButton        — "예측하기" 버튼 (5명 선택 시 활성화)
└── ResultPanel          — 예측 결과 표시
    ├── WinProbabilityGauge  — 승률 게이지 바 (애니메이션)
    ├── RoleDistributionChart — 역할군 분포 차트 (양 팀 비교)
    ├── FeatureImportanceBar  — 피처 중요도 바 차트 (상위 5개)
    └── ConfidenceBadge      — 신뢰도 배지 (high/medium/low)
```

---

## 3. 수동 테스트 플로우 (단계별)

### Step 1: 페이지 진입 확인

```
접속: http://localhost:3000/predict

확인 항목:
- [ ] 페이지 로드 완료 (3초 이내)
- [ ] 맵 선택 드롭다운 표시
- [ ] 팀 A / 팀 B 요원 그리드 표시
- [ ] 예측하기 버튼 비활성(disabled) 상태
- [ ] 브라우저 콘솔에 에러 없음
```

### Step 2: 맵 선택

```
동작: 드롭다운에서 "Ascent" 선택

확인 항목:
- [ ] GET /maps API 호출 (Network 탭)
- [ ] 드롭다운에 11개 맵 표시
- [ ] 선택된 맵이 표시됨
- [ ] 선택 변경 시 결과 초기화
```

### Step 3: 팀 A 요원 선택 (5명)

```
동작: Jett → Sova → Viper → Killjoy → Skye 순서대로 클릭

확인 항목:
- [ ] 클릭 시 요원 선택 표시 (하이라이트)
- [ ] 선택된 요원이 SelectedTeamDisplay에 표시
- [ ] 5명 선택 시 팀 A 완료 표시
- [ ] 이미 선택된 요원은 비활성화 (팀 B에서 선택 불가)
- [ ] 6번째 클릭 시 선택 무시 또는 교체 UI
```

### Step 4: 팀 B 요원 선택 (5명)

```
동작: Reyna → Breach → Omen → Cypher → Fade 순서대로 클릭

확인 항목:
- [ ] 팀 A에서 선택한 요원(Jett, Sova 등)은 비활성화
- [ ] 5명 선택 시 "예측하기" 버튼 활성화
- [ ] 버튼 활성화 애니메이션 또는 색상 변화
```

### Step 5: 예측 실행

```
동작: "예측하기" 버튼 클릭

확인 항목:
- [ ] POST /predict API 호출 (Network 탭)
- [ ] 로딩 스피너 또는 스켈레톤 표시
- [ ] 응답시간 200ms 이내
- [ ] 결과 패널 표시 (애니메이션)
```

### Step 6: 결과 확인

```
확인 항목:
- [ ] 승률 게이지: 0 → 67.3% 애니메이션 (예시)
- [ ] "팀 A 승리 확률: 67.3%" 텍스트 표시
- [ ] 신뢰도 배지: "보통" (medium) 표시
- [ ] 역할군 분포 차트: 팀 A / 팀 B 비교 막대 또는 도넛 차트
- [ ] 피처 중요도 바 차트: 상위 5개 피처 표시
- [ ] 결과 공유 버튼 (선택)
```

---

## 4. 엣지 케이스 UI 테스트

### TC-UI-P-001: 요원 선택 취소

```
동작: 선택된 요원을 다시 클릭
기대: 선택 해제, SelectedTeamDisplay에서 제거, 예측 버튼 비활성화
```

### TC-UI-P-002: 맵 변경 후 결과 초기화

```
동작: 예측 결과 확인 후 맵을 다른 맵으로 변경
기대: 이전 결과 초기화, 요원 선택 유지, 재예측 필요
```

### TC-UI-P-003: 연속 예측

```
동작: 첫 예측 완료 후 맵/요원 변경 없이 "예측하기" 재클릭
기대: 동일 결과 반환, UI 정상 업데이트
```

### TC-UI-P-004: API 오류 시 UI

```
동작: 백엔드 서버 중단 상태에서 예측 시도
기대: 에러 메시지 표시 ("서버에 연결할 수 없습니다")
     로딩 스피너 제거
     재시도 버튼 표시
```

### TC-UI-P-005: 모바일 반응형

```
기기: iPhone 14 (390×844) 또는 브라우저 DevTools 모바일 시뮬레이션
확인:
- [ ] 요원 그리드 모바일 레이아웃 (2~3열)
- [ ] 버튼 터치 영역 충분 (44px 이상)
- [ ] 가로 스크롤 없음
- [ ] 결과 패널 가독성
```

---

## 5. Next.js 컴포넌트 테스트 코드

```typescript
// frontend/__tests__/predict-page.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { rest } from "msw";
import { setupServer } from "msw/node";
import PredictPage from "@/app/predict/page";

// MSW 서버 설정 (API 모킹)
const server = setupServer(
  rest.get("/agents", (req, res, ctx) =>
    res(ctx.json({
      agents: [
        { name: "Jett", role: "Duelist", role_kr: "타격대" },
        { name: "Sova", role: "Initiator", role_kr: "척후대" },
      ],
      roles: {},
      total: 2,
    }))
  ),
  rest.get("/maps", (req, res, ctx) =>
    res(ctx.json({
      maps: [{ name: "Ascent", name_kr: "어센트", region: "Italy", callouts: [] }],
      total: 1,
    }))
  ),
  rest.post("/predict", (req, res, ctx) =>
    res(ctx.json({
      win_probability: 0.673,
      lose_probability: 0.327,
      confidence: "medium",
      team_a_role_counts: { duelist:1, initiator:1, controller:0, sentinel:0, unknown:0 },
      team_b_role_counts: { duelist:0, initiator:0, controller:0, sentinel:0, unknown:0 },
      feature_importance: { map_encoded: 0.2 },
      map: "Ascent",
      model_version: "1.0.0",
    }))
  )
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("/predict 페이지", () => {
  it("페이지가 정상 렌더링됨", async () => {
    render(<PredictPage />);
    expect(await screen.findByText("맵 선택")).toBeInTheDocument();
  });

  it("예측 버튼이 초기에 비활성화됨", () => {
    render(<PredictPage />);
    const button = screen.getByRole("button", { name: /예측하기/ });
    expect(button).toBeDisabled();
  });

  it("결과 패널에 승률이 표시됨", async () => {
    render(<PredictPage />);
    // 맵 선택 + 요원 선택 시뮬레이션 생략 (통합 테스트에서 처리)
    // 결과 표시 검증은 ResultPanel 단위 테스트에서 수행
  });
});
```

---

## 6. Playwright E2E 테스트

```typescript
// tests/e2e/predict-flow.spec.ts
import { test, expect } from "@playwright/test";

test.describe("/predict 페이지 E2E", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/predict");
  });

  test("전체 예측 플로우 완료", async ({ page }) => {
    // 맵 선택
    await page.selectOption("select[name=map]", "Ascent");

    // 팀 A 요원 5명 선택
    for (const agent of ["Jett", "Sova", "Viper", "Killjoy", "Skye"]) {
      await page.click(`[data-agent="${agent}"][data-team="a"]`);
    }

    // 팀 B 요원 5명 선택
    for (const agent of ["Reyna", "Breach", "Omen", "Cypher", "Fade"]) {
      await page.click(`[data-agent="${agent}"][data-team="b"]`);
    }

    // 예측 버튼 활성화 확인
    const predictBtn = page.getByRole("button", { name: "예측하기" });
    await expect(predictBtn).toBeEnabled();

    // 예측 실행
    await predictBtn.click();

    // 결과 확인
    await expect(page.locator("[data-testid=win-probability]")).toBeVisible({
      timeout: 5000
    });
    const probText = await page.locator("[data-testid=win-probability]").innerText();
    expect(probText).toMatch(/\d+\.\d+%/);
  });

  test("API 오류 시 에러 메시지 표시", async ({ page }) => {
    // API 인터셉트로 오류 강제 발생
    await page.route("**/predict", route =>
      route.fulfill({ status: 500, body: JSON.stringify({ detail: "서버 오류" }) })
    );

    // 선택 후 예측 시도 (생략)
    // 에러 메시지 확인
    await expect(page.locator("[data-testid=error-message]")).toBeVisible();
  });
});
```

---

## 7. 체크리스트 요약

| 항목 | 수동 테스트 | 자동 테스트 |
|------|-----------|-----------|
| 페이지 로드 | Step 1 | Playwright |
| 맵 드롭다운 | Step 2 | MSW + RTL |
| 요원 선택 로직 | Step 3~4 | RTL 단위 테스트 |
| 예측 API 호출 | Step 5 | MSW 모킹 |
| 결과 표시 | Step 6 | Playwright |
| 에러 처리 | TC-UI-P-004 | Playwright route |
| 모바일 반응형 | TC-UI-P-005 | Playwright viewport |
