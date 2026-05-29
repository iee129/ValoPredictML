> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 00. 디자인 원칙 — 블랙&레드 발로란트 컨셉

---

## 컨셉 정의

이 프로젝트의 시각 언어는 발로란트 공식 UI를 기반으로 한다.  
단순 "다크 테마"가 아니라, **전술 FPS 조작판(tactical console)** 의 느낌을 목표로 한다.

| 항목 | 방향 |
|---|---|
| 배경 | 거의 순수 블랙 — 정보가 어둠 속에서 부각되는 구조 |
| 강조 | 발로란트 레드(`#ff4655`)를 포인트로만 사용 |
| 형태 | 각진 모서리(clip-path polygon) + 직선 기하 — 부드러운 라운드 배제 |
| 타이포 | 영문 헤드라인 콘덴스드 대문자(Bebas Neue) + 한글 본문(Pretendard) |
| 정보 밀도 | 높음 — 게임 HUD처럼 한 화면에 많은 정보가 정렬 |

---

## 명도 위계 원칙

화면 안의 요소는 **밝기 = 중요도** 원칙으로 계층을 만든다.

```
레벨 4 (강조)  — var(--color-valo-red)      #ff4655   CTA, 활성 탭, 선택 테두리
레벨 3 (주요)  — var(--color-valo-text)     #f5f7fb   제목, 핵심 수치
레벨 2 (일반)  — var(--color-valo-text)     #f5f7fb   본문 텍스트
레벨 1 (보조)  — var(--color-valo-muted)    #9ba3b3   레이블, 설명, 단위
레벨 0 (배경)  — var(--color-valo-bg)       #07080c   페이지 배경
```

레이아웃 레이어:
```
패널   — var(--color-valo-panel)     #11151f   카드, 사이드바
중첩   — var(--color-valo-panel-alt) #171c27   패널 안의 패널
테두리 — var(--color-valo-border)    #1f2633   구분선, 외곽
```

---

## 레드 사용 원칙

레드는 **희소성이 강조를 만든다.** 자주 쓸수록 힘을 잃는다.

| 사용 OK | 사용 자제 |
|---|---|
| 버튼/CTA 하나 | 텍스트 블록 전체 |
| 활성 탭 배경 | 배경 넓은 면적 |
| 카드 선택 테두리 | 2개 이상 연속 강조 |
| 섹션 좌측 강조 바 (3px) | 일반 설명 텍스트 |
| 프로그레스/게이지 채움 | 에러가 아닌 상태에서 경고 연상 |

역할군·신뢰도 등 **의미 구분이 필요한 색**은 기능색(`--color-role-*`, `--color-confidence-*`)을 별도 사용한다. 레드와 혼용하지 않는다.

---

## 디자인 언어 패턴 3가지

### 1. clip-path 각진 모서리

발로란트 UI 특유의 **우상단 잘린 형태**. 모든 border-radius 대신 polygon을 사용.

```css
/* 기본 — 우상단 8px 잘림 */
clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%);

/* 대형 카드 — 우상단 14px 잘림 */
clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%);
```

clip-path는 **컨테이너 레이어(카드·패널·버튼)** 에만 적용한다. 텍스트나 아이콘에는 사용하지 않는다.

### 2. 콘덴스드 대문자 헤드라인

영문 섹션 제목·레이블에 Bebas Neue를 적용한다. 한글 혼용 텍스트는 Pretendard로 폴백.

```css
.headingDisplay {
  font-family: 'Bebas Neue', 'Pretendard Variable', sans-serif;
  font-size: 1.4rem;
  font-weight: 400;        /* Bebas Neue는 단일 웨이트 */
  text-transform: uppercase;
  letter-spacing: 0.04em;
  line-height: 1.0;
  color: var(--color-valo-text);
}
```

### 3. 기하 구분선 & 강조 바

섹션 경계는 수평선(hr) 대신 **레드 강조 바** 또는 얇은 border-left로 처리한다.

```css
/* 섹션 좌측 강조 바 */
.sectionTitle {
  border-left: 3px solid var(--color-valo-red);
  padding-left: 0.75rem;
}

/* 수평 구분 — 단색 그라디언트로 페이드아웃 */
.divider {
  border: none;
  height: 1px;
  background: linear-gradient(
    90deg,
    var(--color-valo-red)    0%,
    var(--color-valo-border) 40%,
    transparent              100%
  );
  margin: 1.5rem 0;
}
```

---

## 컴포넌트 적용 예시 — Before / After

### AgentCard

**문제 (Before — 기존 네이비 기반 카드에서 전환):**  
둥근 모서리에 단순 레드 테두리만 있어 "선택됨" 피드백이 약하고, 형태가 일반 카드와 구분되지 않는다.

```css
/* Before: AgentCard.module.css */
.card {
  background: var(--color-valo-panel);
  border: 1px solid var(--color-valo-border);
  border-radius: 8px;           /* 둥근 모서리 — 발로란트 스타일 아님 */
  overflow: hidden;
  /* 전환 효과 없음, hover/disabled 상태 미정의 */
}

.selected {
  border-color: var(--color-valo-red);  /* 테두리만 변경 — 약한 피드백 */
}
```

**개선 (After — 블랙&레드 + 발로란트 디자인 언어):**  
각진 clip-path로 발로란트 무드를 확보하고, 선택 시 테두리+그림자 복합 피드백으로 명확성 상승.

```css
/* After: AgentCard.module.css */
@reference "tailwindcss";

.card {
  background: var(--color-valo-panel);
  border: 1px solid var(--color-valo-border);
  /* 우상단 8px 잘림 — 발로란트 각진 형태 */
  clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%);
  transition: border-color 150ms ease, box-shadow 150ms ease;
  cursor: pointer;
}

.card:hover {
  border-color: var(--color-valo-red-hover);
}

.card.selected {
  border-color: var(--color-valo-red);
  /* 테두리 + 내부 광원 — "선택됨" 시각 강화 */
  box-shadow:
    0 0 0 1px var(--color-valo-red),
    inset 0 0 12px var(--color-valo-red-dim);
}

.card.disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* 선택 체크 오버레이 */
.checkmark {
  position: absolute;
  top: 4px;
  right: 10px;   /* clip-path 잘림 고려해 우측 여백 확보 */
  color: var(--color-valo-red);
  font-size: 0.75rem;
  font-weight: 900;
}
```

**근거:** clip-path 적용으로 둥근 모서리를 제거해 발로란트 UI 정체성이 생긴다. selected 상태에서 border+inset shadow 조합은 빛이 카드 안으로 스며드는 느낌을 줘 "활성화"를 직관적으로 전달한다. checkmark는 clip-path 잘림 직전 영역에 배치해 형태와 내용이 자연스럽게 연결된다.

---

### PageSectionHeader

**문제 (Before):**  
일반 굵은 텍스트로만 섹션 구분 → 긴 페이지에서 위계가 명확하지 않음. 발로란트 무드도 없음.

```css
/* Before: PageSectionHeader.module.css */
.header {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-valo-text);
  margin-bottom: 1rem;
  /* Bebas Neue 없음, 레드 강조 바 없음, 위계 구분 약함 */
}
```

**개선 (After — 콘덴스드 헤드라인 + 레드 강조 바):**  
Bebas Neue 헤드라인과 레드 좌측 바로 섹션 진입을 명확히 알린다.

```css
/* After: PageSectionHeader.module.css */
@reference "tailwindcss";

.header {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  border-left: 3px solid var(--color-valo-red);
  padding-left: 0.75rem;
  /* 우하단 6px 잘림 — AgentCard와 같은 각진 디자인 언어 공유 */
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%);
  margin-bottom: 1.25rem;
}

.title {
  font-family: 'Bebas Neue', 'Pretendard Variable', sans-serif;
  font-size: 1.35rem;
  font-weight: 400;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  line-height: 1.0;
  color: var(--color-valo-text);
}

.meta {
  font-size: 0.82rem;
  color: var(--color-valo-muted);
  line-height: 1.4;
}
```

**근거:** 좌측 3px 레드 바는 발로란트 UI에서 자주 쓰이는 섹션 진입 패턴이다. 헤더 컨테이너 우하단에도 clip-path 잘림을 적용해 AgentCard와 동일한 각진 디자인 언어를 공유하므로, 페이지 전반에서 형태 일관성이 유지된다. Bebas Neue는 한글 fallback 없이도 영문 레이블에서 즉시 발로란트 분위기를 만든다. meta 서브라인은 muted 색으로 계층을 명확히 유지한다.

---

## 일관성 체크리스트

컴포넌트를 새로 추가하거나 수정할 때 확인:

- [ ] 배경/패널 색이 토큰 참조인가 (`var(--color-valo-*)`)? hex 직접 사용 없는가?
- [ ] 각진 형태가 필요한 카드·패널에 clip-path가 적용됐는가?
- [ ] 레드는 한 화면에서 가장 강조할 1~2개 포인트에만 사용됐는가?
- [ ] 영문 헤드라인/레이블에 Bebas Neue가 적용됐는가?
- [ ] hover/selected/disabled 세 상태가 토큰 기반으로 정의됐는가?
