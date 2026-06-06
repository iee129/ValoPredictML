# 웹 시안 → 프론트엔드 구현 계획

> 상태: **pending approval** (계획만 수립. 코드 구현은 승인 후 착수)
> 작성: 2026-06-01 · 기준: Figma 시안 `file_key 68zvzPn4BB9EsWMOKPfW9d` (home `60:2` · replay `32:2` · model `34:2`)
> 대상: `web` (Next.js 16 App Router · React 19 · TS · Tailwind v4), 백엔드 `src/api`(FastAPI, `src/inference/predict.py` 재사용)

---

## 0. 범위 / 비범위

**범위**: Figma 시안을 실제 프론트 코드로 포팅(우선 mock 데이터) + 디자인 스펙 문서 갱신 + 코드-상태 문서의 단계적 동기화.
**비범위(별도 Phase 4)**: 실모델 연동(`model_complete`). **데이터 블로커**(Kaggle→`data/processed/` 변환 스크립트 부재)가 선행 조건.

**문서 갱신 정책(중요)**:
- *디자인 스펙 문서*(`07_styling/*`, mockups README) → **지금 갱신**(전망적 스펙).
- *코드 상태 문서*(`01_overview` 구조·`02_backend`·`03_frontend` 페이지·`04_integration` 계약) → **각 구현 Phase에서 코드와 함께 갱신**(코드보다 앞서가 불일치 만들지 않기).

---

## 1. 요구사항 요약 (시안에서 확정된 변경)

1. **예측 탭 통합**: `/predict` 라우트 제거 → `/`(home) 단일 예측 페이지. nav = 홈/다시보기/모델(3개).
2. **model 페이지 재설계**(설명형 ML 리포트, 세로 확장):
   - 성능평가: TEST AUC · ROC 곡선 · 평가방식(무작위/시간순) · 데이터셋 도넛 / 모델비교 · 전역 피처중요도 · 혼동행렬+지표
   - 일반화 진단: 과적합(train↔test) · CV fold 안정성
   - EDA: 타겟 분포 · 맵 분포 · KD↔승률 · 연도별 역할 메타
   - 학습·검증 방법 요약. **"누수검증 PASS / 신뢰 가능" 판정 배지 제거**
3. **새 비주얼 시스템**: 글로우 금지 · 각진 챔퍼(clip-path)+HUD 코너틱 · `//` 슬래시 라벨 · 역할색 코딩(듀얼리스트#ff7d4d/이니시에이터#5b8cff/컨트롤러#b388ff/센티넬#ffd166) · 요원 displayIcon 아바타 · 맵 스플래시 배경+글래스 카드 · 방향성 음영 그라데이션(막대 좌→우, 패널 위→아래) · 웜 본(#ece8e1) 디스플레이 · Bebas Neue/Pretendard.
4. **수치 정합**: 시안 placeholder → 실제값. 현재 active advanced는 `reports/advanced/metrics.json`·`validation.json` 기준 **179피처 시간순 split**이다.

---

## 2. 수용 기준 (testable)

- AC1: 빌드 후 `/predict` 경로 404, nav에 "예측" 없음, `홈/다시보기/모델` 3개만 렌더.
- AC2: home에서 라인업 입력 → 결과(승자·%·신뢰도·모멘텀) → 근거(피처 중요도·역할레이더·조합점검·자연어)가 한 화면(1280×800)에 스크롤 없이 표시.
- AC3: home 로스터 10슬롯이 요원 displayIcon 아바타(팀색 링)로 렌더, 이니셜 텍스트 없음, 역할 아이콘 색이 역할별로 구분.
- AC4: model 페이지에 ROC·혼동행렬·도넛·과적합·CV·EDA(타겟/맵/KD↔승률/연도메타) 차트가 모두 존재, "PASS/신뢰 가능" 텍스트 없음.
- AC5: 모든 카드 모서리 챔퍼 또는 코너틱, 어떤 요소에도 radial glow(box-shadow 발광/blur 헤일로) 없음 — `grep -ri "blur\|glow"` 결과 0(의도된 backdrop 제외).
- AC6: `npx tsc --noEmit` 0 에러, `npm run lint`(max-warnings 0) 통과, `npm run build` 성공.
- AC7: 각 페이지 시안 대비 시각 검수(스크린샷) 통과.
- AC8: Next Route Handler(`/api`)를 통해 FastAPI를 프록시하고, 백엔드 주소는 `VALO_INTERNAL_API_URL`로 설정.

---

## 3. 구현 단계 (file refs)

### Phase 0 · 디자인 시스템 토대
- `src/app/globals.css` `@theme`: 토큰 추가 — `--color-bone`(#ece8e1), 역할색 4종, 그라데이션 헬퍼. ⚠️ 토큰명에 `base/lg/xl` 금지(기존 함정 — `01_valorant_theme.md` §4 충돌 주의).
- clip-path 챔퍼 유틸 + 글래스 backdrop 유틸 클래스.
- 신규 프리미티브 `src/components/ui/`: `TacticalCard.tsx`(챔퍼+코너틱+글래스 옵션), `SectionLabel.tsx`(`//` 레드 슬래시), `TitleTick.tsx`, `Gauge.tsx`(방향성 음영), `RoleIcon.tsx`, `AgentAvatar.tsx`, `Backdrop.tsx`(맵 스플래시+다크 오버레이).

### Phase 0.5 · 에셋 벤더링
- `public/agents/*.png`(요원 displayIcon), `public/maps/*`(스플래시·listicon). 출처 valorant-api.com. 런타임 외부 의존 제거.

### Phase 1 · 라우팅 통합
- `src/app/predict/page.tsx` 삭제, 내용은 `src/app/page.tsx`로 이동. `src/components/Navbar.tsx` → 3항목. `/predict` 참조 링크 정리(`lib`·컴포넌트).

### Phase 2 · 페이지 구현 (mock)
| 페이지 | 파일 | 재사용 | 신규/개조 |
|---|---|---|---|
| home | `app/page.tsx` | `predict/{MapBanner,MapSelect,YearSelect,TeamLineup,LineupSlot,FitBadge}`, `result/{ResultPanel,ConfidenceBadge,FeatureBar,RoleRadar,ReasonCard}`, `insights/{MetaMatchBar,BalanceAlert,Legend}` | `AgentAvatar`·`RoleIcon`색·`Gauge`음영·요원 풀아트·맵 글래스 배너 |
| replay | `app/replay/page.tsx` | `replay/ReplayOutcome`, `result/FeatureBar` | 경기 조합 `AgentAvatar` 행·플랫 체크·`TacticalCard` |
| model | `app/model/page.tsx` | `ui/MetricCard` | 신규 차트: `RocCurve`·`ConfusionMatrix`·`Donut`·`GroupedColumns`·`CVStrip`·`LineChart`·`Histogram` (`src/components/charts/`) |

### Phase 3 · 계약·수치 정합
- `src/types/api.ts` + `src/lib/mock.ts`: model 응답에 ROC점·혼동행렬·per-model AUC·CV folds·EDA 집계·데이터 분할 필드 추가.
- 피처 수: `src/features/preprocess.py`의 `FEATURE_COLS_ADVANCED` 길이 **실측 확인** 후 mock·types·문서·CLAUDE.md 전부 동일 값(179)으로 정합. `04_integration/01_data_contract.md:14`, `02_types_and_api_client.md:104`, `04_pages_and_components.md:59` 등.

### Phase 4 · 실모델 연동 (별도, 데이터 블로커 선행)
- Kaggle→`data/processed/` 변환 스크립트 복원/재작성.
- `reports/advanced/{metrics,validation}.json` + 트리/순열 기반 피처 중요도 + `reports/baseline/eda/`를 백엔드 엔드포인트로 노출(model 페이지 실데이터).
- `model_complete` 스킬: mock 라우트(`src/app/api/*`) 제거, `.env.local` → 실서버(`:8000`), FastAPI(`src/inference/predict.py`) 서빙.

---

## 4. 문서 업데이트 체크리스트

### (A) 지금 갱신 — 디자인 스펙
- [x] `docs/08_web/07_styling/mockups/README.md` — 새 디자인 방향·노드ID·비주얼 시스템 (본 계획과 함께 갱신)
- [ ] `docs/08_web/07_styling/00_design_principles.md` — 글로우 금지·그라데이션(방향성 음영만) 규약 추가
- [ ] `docs/08_web/07_styling/01_valorant_theme.md` — 역할색·본 토큰·챔퍼/글래스/그라데이션 유틸 추가
- [ ] `docs/08_web/07_styling/02_layout_demo_dashboard.md` — home 통합 레이아웃·model 3섹션 리포트 반영
- [ ] `docs/08_web/07_styling/03_component_visual_specs.md` — TacticalCard·AgentAvatar·RoleIcon·차트 컴포넌트 명세 추가

### (B) Phase 1에서 코드와 함께 갱신 — 라우팅/구조
- [ ] `docs/08_web/01_overview/01_goal_and_scope.md:40,42` — 엔드포인트·페이지 목록(/predict→home 통합)
- [ ] `docs/08_web/01_overview/02_architecture.md:9` — 프론트 페이지 트리
- [ ] `docs/08_web/03_frontend_nextjs/01_setup_and_structure.md:33,100~104` — 라우트·페이지 표
- [ ] `docs/08_web/03_frontend_nextjs/03_predict_page.md` — home 통합 페이지로 개편(또는 04로 병합)
- [ ] `docs/08_web/03_frontend_nextjs/04_pages_and_components.md` — 컴포넌트·페이지 매핑
- [ ] `docs/08_web/05_appendix/01_diff_from_08_web.md:13` — 페이지 목록
- [ ] `docs/08_web/04_integration/02_demo_runbook.md:85~104` — 시연 순서(페이지 3개)

### (C) Phase 2~3에서 갱신 — model 재설계·수치
- [ ] `docs/08_web/03_frontend_nextjs/04_pages_and_components.md:59,61` — model 구성·피처수·verdict 제거
- [ ] `docs/08_web/04_integration/01_data_contract.md:14` — 피처 수(확인 완료: 179)
- [ ] `docs/08_web/03_frontend_nextjs/02_types_and_api_client.md:104` — `n_features` 값
- [ ] `docs/08_web/04_integration/02_demo_runbook.md:61,85` — health n_features·model 설명
- [ ] `docs/08_web/01_overview/01_goal_and_scope.md:5,18,24,39`, `02_architecture.md:34,56` — 179피처 표기
- [ ] `CLAUDE.md` — 피처 수·페이지 구조(코드 반영 후)

### (D) 참고만 (수정 안 함)
- `docs/08_web/*` — 이미 폐기(범위 외 배너). 그대로 둠.

---

## 5. 위험 & 완화
| 위험 | 완화 |
|---|---|
| 피처 수 혼란(해소됨) | `FEATURE_COLS_ADVANCED` 실측 완료 → 179개로 일괄 정합. |
| Tailwind v4 토큰명 충돌(`text-base` 등) | 모든 신규 토큰 접두사 사용(`--color-valo-*`), `01_valorant_theme.md §4` 준수 |
| 글래스/배경 이미지 가독성 저하 | 배경 다크 오버레이 ≥0.6, 카드 불투명도 ≥0.78, 본문 대비 ≥4.5:1 검수 |
| 문서가 코드보다 앞서 불일치 | (B)(C) 문서는 해당 Phase 코드 머지와 동일 커밋에서 갱신 |
| model 차트 7종 신규 — 작업량 | 공통 SVG 차트 헬퍼로 추상화(축·막대·곡선), 시안 좌표 재사용 |
| 실모델 데이터 블로커 | Phase 4를 분리, mock으로 1~3 먼저 완성. 블로커는 별도 트랙 |

## 6. 검증 단계
1. Phase별 `npx tsc --noEmit` + `npm run lint` + `npm run build`.
2. mock 모드 각 페이지 스크린샷 → 시안 대조(시각 검수).
3. `grep -ri "box-shadow.*rgba.*0\.[3-9]\|blur(" src` 로 글로우 잔존 0 확인.
4. Phase 4 후: 실서버 `/health` n_features 일치, `/predict`·`/replay` 실추론 응답, `/model` 실수치 표시.

## 7. 확인 필요 (착수 전 1건)
- **피처 수 진실값**: `src/features/preprocess.py` `FEATURE_COLS_ADVANCED` = **179** (실측 완료). mock·types·문서 전반의 기준.

---

## 착수 방법
승인 시 권장 순서: `Phase 0 → 0.5 → 1 → 2(home→replay→model) → 3`. 실행은 git 브랜치 분기 후 진행하며, 각 Phase 종료 시 위 (B)(C) 문서를 같은 커밋에 갱신한다. Phase 4(실모델)는 데이터 블로커 해소 후 `model_complete`로.
