# 발로란트 prediction/analysis 도구 경쟁 분석

> 작성일: 2026-05-27
> 목적: 본 프로젝트(ValoPredictML)의 사용자 측면 차별점 강화 방향을 도출하기 위해, 기존 발로란트 prediction·analysis 도구·프로젝트·학술 연구를 한 자리에서 정리한다.

---

## 1. 분석 목적과 범위

### 1.1 왜 이 문서가 필요한가

본 프로젝트 지도교수의 2차 미팅(2026-05-25, `notice/second_interview.md`) 피드백:

> "기술적인 차별점은 그렇게 신경쓰지 않는다. 기존 프로젝트와 비교해서 **사용자 측면에서 보이는 차별점**이 강화되어야 한다."

이 문서는 위 피드백에 답하기 위해, **이미 시장과 학계에 존재하는 발로란트 prediction·analysis 도구가 사용자에게 무엇을 어떻게 제공하는지**를 사실 위주로 정리한다. 본 프로젝트가 어떤 후보 차별점을 채택할지는 이 문서를 토대로 별도 판단한다 — 이 문서 자체는 추천을 담지 않는다.

### 1.2 무엇을 분석하나

- **카테고리 A — 발로란트 전용 상용/커뮤니티 도구**: 일반 유저·코치·팬이 실제로 일상에서 쓰는 웹·앱·오버레이 도구.
- **카테고리 B — 발로란트 학술 연구**: 발로란트 prematch·in-round 예측을 다룬 논문 및 학위논문.
- **카테고리 C — 발로란트 ML 오픈소스 프로젝트**: GitHub에 공개된 학습형 prediction 프로젝트.
- **카테고리 D — 타 e-스포츠 도구 (LoL · Dota 2)**: 발로란트로 옮기면 사용자 측면 차별점이 될 수 있는 기능을 보유한 인접 종목 도구.

### 1.3 무엇은 분석하지 않나

- 인게임 핵·치트성 오버레이 (정책상 제외)
- 베팅 사이트의 odds 계산기 (도박 외 도구로서 비교 의미 낮음)
- 단순 뉴스·일정 사이트로만 기능하는 페이지 (예측·분석 미포함)

---

## 2. 분석 대상 카테고리 요약

| 카테고리 | 대표 사례 | 개수 |
|----------|-----------|------|
| A. 발로란트 전용 상용·커뮤니티 도구 | tracker.gg · blitz.gg · VLR.gg · RIB.GG · Augment.gg · DAK.GG · U.GG Valorant · Riot 공식 Pick'Ems | 8 |
| B. 발로란트 학술 연구 | DraftRec · Hodge 2021 · NCI Pawar 2024 · IJCSMC Park 2026 · arXiv 2502.01250 (VCT 2022 클러스터링) · IEEE CoG 2025 · TechRxiv Wang 2025 · Balance Score 2023 | 8 |
| C. 발로란트 ML 오픈소스 | gupta-v/valorant-performance-predictor · Corosso/ValoAI · kleinaitis/valorant-match-predictor · jasonlow2307/valo-prediction · neilsorkin19/ValLoadoutToWin · DEF4LT-303 · chechna9 · Juniorffonseca | 8 |
| D. 타 e-스포츠 도구 | LoL: U.GG · Mobalytics · Lolalytics · DraftGap · LoLDraftAI / Dota 2: DotaPicker · Dota2.tools · Alien Fusion · Hero Picker Pro | 9 |

---

## 3. 카테고리 A — 발로란트 전용 상용·커뮤니티 도구

### 3.1 tracker.gg (Valorant Tracker)

**한 줄 정체성**: 발로란트 개인 스탯·매치 히스토리·메타 통계의 *de facto* 표준. 전 세계 230M+ 플레이어 추적.

**무엇을 차별점으로 내세우나**:
- 개인 단위 누적 통계 (rank progression, peak rating, accuracy, ace 수, headshot %)
- 맵별·요원별·무기별 개인 성과 분해 (per-act 또는 전체)
- 글로벌 에이전트 인사이트 — 전체 유저 기반 픽률·승률·K/D
- 인게임 오버레이로 agent select 시점에 동료·상대 스탯 자동 표시

**사용자가 어떻게 사용하나** (구체적 워크플로):

1. 라이엇 ID로 검색 → 본인 프로필 페이지 진입
2. "Matches" 탭에서 최근 경기 목록 확인, 클릭 시 라운드별 스코어보드·타임라인 전개
3. "Agents" 탭에서 자기가 어떤 요원을 가장 잘 다루는지 K/D·승률로 정렬
4. 데스크톱 앱 설치 시 발로란트 실행하면 자동으로 agent select 화면에 오버레이 떠서 같이 매칭된 9명의 현재 act 랭크·승률·즐겨쓰는 요원이 노출됨
5. "Insights → Agents" 페이지로 글로벌 메타 확인 (이번 패치에서 어느 요원이 떠올랐는지)

**강점**: 개인 데이터 깊이, 인게임 오버레이의 즉시성, 글로벌 모집단의 크기.

**한계 (예측 측면)**: prematch 시점에서 "이 조합으로 이길 확률이 얼마인가?"라는 질문에는 직접 답하지 않음 — 통계 나열만 제공하고 종합 판단은 사용자 몫.

---

### 3.2 blitz.gg (Valorant)

**한 줄 정체성**: 인게임 오버레이로 실시간 코칭 정보를 띄워주는 도우미 앱.

**무엇을 차별점으로 내세우나**:
- **Agent Select Overlay**: 매칭 직후 상대 5명·아군 4명의 현재 act 랭크·요원별 스탯·승률을 agent select 화면 위에 자동 표시
- **Combat Overlay (Dynamic Stats)**: 게임 중 Combat Score · Headshot % · 킬 수를 실시간 추적
- **Loading Screen Overlay**: 로딩 중 같은 정보를 다시 한 번 정리
- **Post Match Insights Overlay**: 게임 종료 즉시 in-depth 통계 팝업
- **Lineup Maps**: 각 요원의 스모크·플래시 라인업 가이드 (초보자용 학습 자료)

**사용자가 어떻게 사용하나**:

1. blitz.gg 데스크톱 앱 설치 후 실행
2. 발로란트 게임 시작 → 큐 잡힘 → Agent Select 시점에 blitz 오버레이가 자동 등장, 9명 분의 정보가 화면 한쪽에 떠 있음
3. 그걸 보고 "상대 4번 자리가 이번 act에 Jett 75% 픽" 같은 정보를 읽고 자기 요원 결정
4. 게임 중 화면 구석에 실시간 Combat Score 게이지가 떠 있어, 자기 페이스가 평균 대비 어떤지 즉시 인지
5. 게임 끝나면 Post Match 팝업이 라운드별 핵심 순간·실수·승리 기여도를 자동 분해

**강점**: 인게임 실시간성 — 다른 도구는 게임 끝나고 들어가야 하지만 blitz는 게임 중에 알려줌. 학습용 lineup map 라이브러리.

**한계 (예측 측면)**: "이 9명이 만든 조합이 얼마나 강한지" 종합 승률 예측은 제공하지 않음. 개별 스탯의 나열·강조에 집중.

---

### 3.3 VLR.gg

**한 줄 정체성**: 발로란트 프로씬(VCT·Challengers·Game Changers)의 공식 기록 사이트이자 커뮤니티 게시판.

**무엇을 차별점으로 내세우나**:
- 모든 프로 경기의 일정·결과·라운드별 기록 · 맵별 상세 스코어보드
- 선수·팀 누적 통계 (kills per round, k:d, combat score, econ rating, kills/deaths/assists)
- 팀·선수 랭킹, 메이저 이벤트 기간 동안의 **Pick'Ems** 페이지 (커뮤니티 예측)
- 활성 사용자 커뮤니티 (스레드·댓글·픽 비교)

**사용자가 어떻게 사용하나**:

1. 대회 시즌이 시작되면 첫 페이지에 오늘·내일 경기가 정렬됨
2. 매치를 클릭 → 양 팀 선수 명단, 사용한 맵 1~3개, 라운드별 디테일, 각 선수 ACS·ADR·K/D
3. "Pickems" 페이지로 가서 본인이 다음 라운드 8경기 결과를 직접 선택해 제출, 다른 유저·인플루언서의 픽과 비교
4. "Stats" 페이지로 특정 시기·특정 이벤트의 누적 평균을 필터링 (예: VCT Pacific 2026 Stage 2에서 ACS Top 10)
5. 스레드에서 다른 유저들이 만든 픽·분석을 토론

**강점**: 프로씬 데이터의 정확성·완결성, 커뮤니티 픽 비교의 사회적 동기, 무료 + 접근성.

**한계 (예측 측면)**: Pick'Ems는 **사용자가 직접 예측하는 게임형 기능**이고, 사이트가 모델 기반 승률 예측을 제공하지는 않음. 통계는 누적·과거 지향이고, "다음 경기 이 조합이면 얼마나 이길까"에 자동 답하지 않음.

---

### 3.4 RIB.GG

**한 줄 정체성**: 프로 발로란트 전용 분석 대시보드. 코치·분석가·팬 대상 advanced analytics 플랫폼.

**무엇을 차별점으로 내세우나**:
- 프로 경기의 **라운드 단위 이벤트 타임라인** (킬 위치, 유틸리티 사용 시점, 경제 곡선)
- 팀별·선수별·맵별 advanced 지표 (clutch 성공률, first blood 비율, post-plant 통계)
- 일정·매치 결과·뉴스·하이라이트 통합 페이지
- B2B 트랙 — 프로 팀이 직접 구독해 코칭에 활용

**사용자가 어떻게 사용하나**:

1. 코치·분석가가 다음 상대 팀을 분석할 때 RIB.GG로 진입
2. 상대 팀 페이지 → 최근 N경기의 자주 쓰는 요원 조합·맵별 픽 패턴 확인
3. 특정 맵을 클릭하면 그 맵에서 상대가 어느 사이트를 자주 공격했는지, 어느 라운드에서 경제를 절약했는지 히트맵으로 보여줌
4. 자기 팀의 약점 → "B 사이트 수비 라운드 승률이 평균보다 12%p 낮음" 같은 결론 도출
5. 다음 스크림에서 약점 시나리오를 집중 연습

**강점**: 깊이 — 라운드 단위 이벤트 추적은 tracker.gg·blitz.gg에 없음. B2B 검증된 도구.

**한계 (예측 측면)**: 예측 모델 자체보다는 **post-game 분석**에 무게중심이 있음. prematch에서 "이 조합으로 시작하면" 같은 시뮬레이션 기능은 강조되지 않음.

---

### 3.5 Augment.gg

**한 줄 정체성**: "Initiate Your Win Condition"을 표어로 한 발로란트 분석 플랫폼. 신규 진입 도구 중 분석 깊이를 강조.

**무엇을 차별점으로 내세우나**:
- 팀 plays · win condition 분석을 자동화하려는 시도
- 데이터 기반 코칭 보조 기능 (베타 단계)

**사용자가 어떻게 사용하나**: 공개 정보 한정 — 대시보드에 팀명 입력 후 자동 생성된 win condition 분류 결과 확인.

**강점·한계**: 시장 진입 초기로 사용자 베이스가 작아 평가 단계. 사용 흐름·UI 완성도는 검증 필요.

---

### 3.6 DAK.GG (Valorant)

**한 줄 정체성**: 한국·아시아권 중심으로 운영되는 발로란트 스탯·티어 트래커. 다종목(배그·LoL 등) 트래커 패밀리의 일원.

**무엇을 차별점으로 내세우나**:
- 한국어 UI · 한국 서버 데이터 최적화
- 요원 티어 표 (한국 메타 기준)
- 개인 매치 히스토리·랭크 트래킹

**사용자가 어떻게 사용하나**: 라이엇 ID 검색 → 본인 프로필 → 한국 서버 기준 티어 표·요원별 승률 확인.

**강점**: 한국 사용자 친화적 UX. **한계**: 글로벌 도구(tracker.gg) 대비 데이터 깊이는 얕음, 예측 기능 없음.

---

### 3.7 U.GG (Valorant)

**한 줄 정체성**: LoL로 유명한 U.GG의 발로란트 모듈. 티어 리스트·프로필·맵별 정보 제공.

**무엇을 차별점으로 내세우나**:
- 발로란트 요원 티어 리스트 (랭크별·맵별)
- 프로필 → 본인 스탯 + 글로벌 비교
- "Peek Maps" — 맵별 주요 픽 포인트 시각화

**사용자가 어떻게 사용하나**: 자기 랭크 + 자주 가는 맵을 선택 → "이 조건에서 가장 강한 요원은 X" 라는 직관적 답을 받음.

**강점**: LoL에서 검증된 UX 일관성. **한계**: LoL 만큼 데이터·기능이 풍부하지는 않음, 조합 단위 예측 미제공.

---

### 3.8 Riot 공식 VALORANT Pick'Ems (valorantesports.com)

**한 줄 정체성**: Riot이 직접 운영하는 공식 매치 예측 게임. 정답률에 따라 인게임 보상(buddy·title) 지급.

**무엇을 차별점으로 내세우나**:
- 공식 보상 (게임 내 buddy·title) → 강한 참여 동기
- 인게임 Esports 탭에서 바로 접근 가능, 라이엇 클라이언트 통합
- Swiss 스테이지·플레이오프 등 각 단계별 별도 픽 윈도우

**사용자가 어떻게 사용하나**:

1. 발로란트 클라이언트 실행 → Esports 탭
2. 진행 중인 메이저 이벤트(예: Masters Santiago 2026)의 Pick'Ems 보임
3. 8~16팀의 진출·탈락·우승 후보를 본인이 선택
4. 경기가 끝날 때마다 점수 갱신, 시즌 종료 시 상위 50%·20%·100% 적중자에게 차등 보상
5. 친구·인플루언서의 픽과 본인 픽을 비교

**강점**: 공식성 + 보상 + 게임 내장 접근성. **한계**: **모델 기반 추천 없음** — 순수 사용자 직감 예측, 보조 정보 미제공. "왜 이 팀이 이길까"라는 근거를 시스템이 제시하지 않음.

---

## 4. 카테고리 B — 발로란트 학술 연구

> 출처: 본 프로젝트 `notice/weekly_plan_2026-05-26.md` 6번 절. 이 절은 각 논문의 *접근법*과 *사용자 측면 시사점*(실제 도구로 옮길 때 어떤 UX로 나타날지)을 중점적으로 정리한다.

### 4.1 DraftRec — Lee et al., WWW 2022 ([arXiv:2204.12750](https://arxiv.org/abs/2204.12750))

**접근법**: 전 종목 e-스포츠 드래프트 추천 모델. 선수×챔피언 친화도 + 팀 시너지를 분리해 모델링.

**사용자 측면 시사점**: 도구로 옮기면 "이 선수에게 이번 픽으로 어떤 챔피언이 맞는가"라는 **개인화 추천 패널**로 구현 가능. 사용자가 자기 선수 슬롯을 클릭하면 그 선수의 과거 숙련도 + 현재 팀과의 시너지를 함께 고려한 Top N이 뜨는 구조.

### 4.2 VCT 2022 발로란트 조합 클러스터링 — [arXiv:2502.01250](https://arxiv.org/abs/2502.01250)

**접근법**: VCT 2022 시즌의 팀 조합을 비지도 학습으로 클러스터링, 메타 archetype 분류.

**사용자 측면 시사점**: "당신이 선택한 조합은 → 'Double Controller Slow Default' 아키타입에 속하며, 이 아키타입의 평균 승률은 X%"라는 **조합 분류 라벨링** 기능. 사용자가 자기 픽의 정체성을 한눈에 이해.

### 4.3 IEEE CoG 2025 발로란트 영상 분석 — [arXiv:2510.17199](https://arxiv.org/abs/2510.17199)

**접근법**: 인게임 영상 frame 분석 기반 in-round 승률 예측.

**사용자 측면 시사점**: 실시간 영상 스트림에서 라운드 진행 중 "현재 시점 승리 확률" 게이지를 화면에 띄우는 **방송용 graphic overlay**. blitz의 in-game overlay와 비교하면 영상 분석 기반이라 더 정밀.

### 4.4 한국 IJCSMC Park 2026 Seq2Seq LSTM — 선문대학교

**접근법**: 라운드 단위 시계열 데이터에 Seq2Seq LSTM 적용한 in-game 승률 예측.

**사용자 측면 시사점**: 발로란트 라운드 흐름을 학습해 "다음 라운드 결과 예측"을 제공할 수 있음. 코치 도구로 옮기면 **세트 중간에 다음 라운드 risk meter**.

### 4.5 NCI Dublin Pawar 2024 학위논문

**접근법**: 발로란트 prematch 베팅 어드바이저리 모델.

**사용자 측면 시사점**: "이 매치는 underdog가 이길 확률이 평균보다 N%p 높다"는 **upset alert 배지**. 단, 베팅 맥락이라 일반 사용자 도구로는 그대로 옮기기 까다로움.

### 4.6 TechRxiv Wang 2025 economy 기반 in-round prediction

**접근법**: 라운드별 경제(현재 자금·무기 보유) 기반 in-round 승률 예측.

**사용자 측면 시사점**: 코치 화면에 "이번 라운드는 풀바이 vs 이코 — 모델 추정 승률 73:27" 같은 **이코노미 dashboard**.

### 4.7 IEEE Trans. Games Hodge et al. 2021

**접근법**: 5v5 e-스포츠 multiplayer prediction의 기초 — feature 설계와 검증 방법론 표준화.

**사용자 측면 시사점**: 도구의 신뢰도 메시지("학술적으로 검증된 방법론을 사용") 기반.

### 4.8 Balance Score — [arXiv:2309.06248](https://arxiv.org/abs/2309.06248)

**접근법**: e-스포츠 특화 calibration 지표.

**사용자 측면 시사점**: 도구 출력에 단순 승률 외에 **"예측 신뢰도 등급"**(높음/보통/낮음)을 같이 표시. 사용자가 도구를 얼마나 믿을지 판단할 근거 제공.

---

## 5. 카테고리 C — 발로란트 ML 오픈소스 프로젝트

> 모두 GitHub 공개. 학생·취미 개발자 작품이 대부분이며, 본 프로젝트와 정면 비교 대상.

### 5.1 gupta-v/valorant-performance-predictor

**무엇을 차별점으로 내세우나**: Streamlit 기반 **개인 퍼포먼스 예측** — 본인의 in-game 통계 입력하면 향후 퍼포먼스 추정.

**사용자가 어떻게 사용하나**:
1. Streamlit URL 진입
2. K/D · ADR · 헤드샷% 등 본인 최근 통계 직접 입력
3. 모델이 다음 경기 예상 K/D·승률 수치 출력

**관찰**: **개인 단위** 예측이지 팀 조합 단위가 아님. 본 프로젝트(팀 5v5 조합)와 다른 그라뉼리티.

---

### 5.2 Corosso/ValoAI

**무엇을 차별점으로 내세우나**: 매치 결과 예측 모델. 과거 팀 성과·맵 승률·과거 매치 결과를 피처로 사용.

**사용자가 어떻게 사용하나**: 두 팀명 입력 → 모델이 한 팀의 승률 출력.

**관찰**: **팀명 누적 이력 의존** — 본 프로젝트가 명시적으로 차단한 접근법(`docs/01_overview/01_project_summary.md` 섹션 3 참조). 선수·요원 조합 단위 예측이 아님.

---

### 5.3 kleinaitis/valorant-match-predictor

**무엇을 차별점으로 내세우나**: 맵 · 랭크 · 팀 조합 입력 기반 매치 결과 예측. tracker.gg에서 스크래핑한 수십만 경기로 학습.

**사용자가 어떻게 사용하나**: 맵 + 랭크 + 양 팀 조합 입력 → 승률 출력.

**관찰**: 본 프로젝트와 **가장 유사한 입력 계약**(맵 + 조합). 다만 데이터 규모·검증 깊이·UI 정교함은 학생 프로젝트 수준.

---

### 5.4 jasonlow2307/valo-prediction

**무엇을 차별점으로 내세우나**: 발로란트 게임 화면 **스크린샷을 실시간 캡처해서 CNN + 컴퓨터 비전으로 매치 결과 예측**. 96% 정확도 자체 주장.

**사용자가 어떻게 사용하나**:
1. 도구 실행 후 게임 시작
2. 도구가 게임 화면을 주기적으로 스크린샷
3. CNN이 화면에서 라운드 스코어·요원 정보 OCR
4. 실시간 승률 시각화

**관찰**: prematch가 아닌 **in-game 추정**. 입력이 스크린샷이라 매우 다른 유형의 도구. 96%는 후반부 라운드까지 진행된 시점의 자명한 정답을 포함했을 가능성이 높음 (검증 불충분).

---

### 5.5 neilsorkin19/ValLoadoutToWin

**무엇을 차별점으로 내세우나**: 라운드 단위 데이터로 **라운드 승리 확률 + 매치 승률** 예측.

**사용자가 어떻게 사용하나**: 라운드 진행 정보(loadout·생존자 수 등) 입력 → 그 라운드를 이길 확률 출력.

**관찰**: **in-round 그라뉼리티** — prematch 도구가 아님. 본 프로젝트와 풀이 다른 문제.

---

### 5.6 DEF4LT-303/Valorant-Pro-Match-Analysis

**무엇을 차별점으로 내세우나**: CSE422 학부 프로젝트. Random Forest 100 estimators로 ACS·ADR·Econ 기반 매치 승자 예측. 학습 1.0 · 테스트 0.93 정확도 주장.

**사용자가 어떻게 사용하나**: 양 팀의 평균 ACS·ADR·Econ 입력 → 승자 예측.

**관찰**: ACS·ADR·Econ은 **경기 결과 정보 그 자체** — 본 프로젝트가 26개 금지 피처 목록으로 사전에 차단한 항목들. 학습 정확도 1.0과 테스트 0.93의 갭은 전형적인 과적합 시그널.

---

### 5.7 chechna9/valorant_win_prediction_UI

**무엇을 차별점으로 내세우나**: 다른 AI 모델의 **프론트엔드 UI 부분만** 별도 프로젝트로 분리.

**사용자가 어떻게 사용하나**: 웹 UI에서 양 팀 정보 입력 → API 호출 → 결과 표시.

**관찰**: 모델 자체가 아닌 UI만. 프론트엔드 디자인 참고용으로는 가치 있음.

---

### 5.8 Juniorffonseca/valorant-predictor

**무엇을 차별점으로 내세우나**: 프로씬 매치 결과 ML 예측.

**사용자가 어떻게 사용하나**: 두 프로팀 매치업 입력 → 승률 출력.

**관찰**: 5.2 ValoAI와 유사한 팀 누적 이력 기반 접근.

---

### 카테고리 C 종합 관찰

- 8개 중 **prematch + 조합 단위 + 데이터 혼입 방지** 셋을 모두 만족하는 프로젝트는 없음.
- 검증 방법론(GroupKFold·라벨 셔플·금지 피처 목록)을 명시적으로 적용한 사례 없음.
- UI는 대부분 Streamlit 단순 폼 또는 미구현. **What-if 시뮬레이션**(요원 1명 바꿔 승률 변화 즉시 확인) 같은 인터랙티브 기능을 갖춘 사례 없음.
- 모델 출력에 **자연어 설명** 또는 **SHAP 카드** 같은 해석 레이어를 붙인 사례 없음.

---

## 6. 카테고리 D — 타 e-스포츠 도구 벤치마크

> 발로란트로 옮겼을 때 사용자 측면 차별점이 될 만한 기능을 보유한 LoL·Dota 2 도구.

### 6.1 LoL — U.GG

**한 줄 정체성**: LoL 빌드·룬·티어 리스트의 표준. Riot 공인 파트너.

**핵심 사용자 기능**:
- 챔피언 페이지 → 빌드(아이템 트리), 룬, 스킬 빌드 순서
- 카운터 픽 표 (모든 챔피언 × 모든 챔피언 매치업 승률 매트릭스)
- 랭크별 티어 리스트 (Iron부터 Challenger까지 별도)
- 프로빌드 (현재 LCK·LPL 등 프로 선수가 쓰는 빌드 자동 집계)

**사용자 워크플로**: 챔피언 선택 → 자기 랭크 선택 → 가장 승률 높은 빌드·룬을 그대로 따라가기.

**발로란트로 옮길 때**: "내가 이 요원 픽할 때 가장 강한 합성 — 이 4명과 같이 쓰면 승률 N% 높음" 같은 **요원 페어링 가이드**.

---

### 6.2 LoL — Mobalytics

**한 줄 정체성**: U.GG와 유사하지만 **개인 playstyle 분석·코칭** 측면을 더 강조한 도구.

**핵심 사용자 기능**:
- GPI(Gamer Performance Index) — 본인의 8개 스킬(생존·맵 운영·전투력 등) 레이더 차트
- 개인 챔피언 풀 분석 (당신은 어택 챔피언에서 70%, 서포트에서 45% 승률)
- 약점 기반 코칭 추천 ("당신의 경계 라인 컨트롤 점수가 낮으니 X 챔피언으로 연습")

**사용자 워크플로**: 본인 ID 검색 → 자동 분석 리포트 → 추천 챔피언·플레이 패턴 학습.

**발로란트로 옮길 때**: "당신의 폼 차트 — 직전 N경기 K/D 추세, 약점 사이트(B 사이트 수비 승률 낮음)" 같은 **개인 폼·약점 카드**.

---

### 6.3 LoL — Lolalytics

**한 줄 정체성**: 데이터 사이언스 측 정확성을 강조하는 티어 리스트 사이트.

**핵심 사용자 기능**: 패치별·랭크별·시간대별 세부 필터링 가능한 정밀한 챔피언 통계.

**사용자 워크플로**: 자기가 관심 있는 챔피언 + 패치 + 랭크 조건을 필터 → 정확한 승률 추출.

**발로란트로 옮길 때**: 패치별 메타 시프트를 시간 슬라이더로 보여주는 **메타 변화 라인 차트**(본 프로젝트 EDA 차트 06와 유사하지만 인터랙티브).

---

### 6.4 LoL — DraftGap

**한 줄 정체성**: **드래프트 단계 도우미** — 5명 픽 중간에 다음 픽을 추천.

**핵심 사용자 기능**:
- 양 팀이 지금까지 픽한 챔피언들 입력
- 다음 픽 후보 챔피언을 추천 (시너지 + 카운터를 모두 고려)
- 각 후보 챔피언별로 "이걸 픽하면 우리 팀 승률은 X% → Y%로 변함"

**사용자 워크플로**:
1. 드래프트 시작
2. 한 픽 픽할 때마다 도구에 입력
3. 다음 픽 차례에 도구가 "지금 가장 강한 픽은 1) Ahri 65% 2) Sett 63% 3) Lulu 62%" 식으로 추천
4. 추천 받은 챔피언 픽

**발로란트로 옮길 때**: 본 프로젝트의 기존 차별점 후보 "5번째 요원 추천"이 정확히 이 형태. **DraftGap의 LoL 사용자 호응도가 매우 높다는 사실은 발로란트에서도 동일한 수요가 있을 가능성을 시사**.

---

### 6.5 LoL — LoLDraftAI

**한 줄 정체성**: 신경망 기반 드래프트 분석. "전체 드래프트를 한 번에 읽는" 모델 광고.

**핵심 사용자 기능**:
- 10명 픽이 모두 끝났을 때 양 팀 승률 + 챔피언 추천 + 룬 추천을 한 번에 출력
- 단순 표 계산이 아닌 **수백만 경기로 학습한 neural network**가 팀 조합 시너지·다중 라인 dynamics·스케일링 패턴을 포착한다고 주장

**사용자 워크플로**:
1. 드래프트 전체 입력
2. AI 분석 버튼 클릭
3. "팀 A 승률 58%, MVP 후보는 Ahri, 추천 룬 트리는 정밀+영감" 같은 종합 보고

**발로란트로 옮길 때**: 본 프로젝트의 What-if 시뮬레이션 + 자연어 설명을 합친 형태에 가까움. 차별점은 **"수백만 경기 학습 → 사람이 못 잡는 패턴 포착"이라는 메시지를 사용자에게 어떻게 전달하느냐**.

---

### 6.6 Dota 2 — DotaPicker

**한 줄 정체성**: Dota 2 드래프트 도우미. all-pick·captains-mode 양쪽 지원.

**핵심 사용자 기능**:
- 상대 5명 픽 입력 → 우리 팀에 가장 강한 카운터 영웅 추천
- "Personal" 프리미엄 — 본인의 최근 성과를 반영해 본인이 편한 영웅 우선 추천
- "Favorite Heroes" — 본인 즐겨쓰는 5영웅을 저장해두고 매 매치마다 어느 게 가장 강한지 비교

**사용자 워크플로**:
1. 매칭 잡힘
2. 상대가 픽할 때마다 도구에 영웅 추가
3. 본인 차례에 본인 즐겨쓰는 5영웅 중 "현재 매치업에서 가장 강한 1순위·2순위" 즉시 확인

**발로란트로 옮길 때**: 본인 **선수 풀(즐겨쓰는 5요원)을 저장해두는 프로필 기능** + 상대 4명 보고 본인이 어떤 걸 골라야 하는지 알려주는 **개인화 추천**.

---

### 6.7 Dota 2 — Dota2.tools Counter Pick

**핵심 사용자 기능**:
- 역할(Carry · Mid · Offlane · Support · Hard Support)별 영웅 추천
- 추천 점수 = 인기도 + 카운터 우위 + 기존 팀 시너지의 가중합
- 각 추천에 "왜 이게 점수 높은지" 분해 설명

**사용자 워크플로**: 본인 역할 선택 → 상대 픽 입력 → 추천 영웅 + 점수 분해 확인.

**발로란트로 옮길 때**: 발로란트의 4대 역할군(타격대·척후대·전략가·감시자) 기반으로 같은 형식의 **역할별 추천 + 점수 분해**.

---

### 6.8 Dota 2 — Alien Fusion Counter Picker

**핵심 사용자 기능**: OpenDota 공식 API와 직접 연결해 **실시간 데이터** 기반 카운터 픽.

**사용자 워크플로**: 매치 중 자동으로 OpenDota에서 최신 매치업 통계를 끌어옴.

**발로란트로 옮길 때**: VLR.gg·tracker.gg API 또는 스크래핑으로 **최신 데이터 자동 갱신** — 본 프로젝트의 VLR.gg 수집 트랙과 연결 가능.

---

### 6.9 Dota 2 — Hero Picker Pro (모바일 앱)

**핵심 사용자 기능**:
- "Ally Hero" — 우리 팀과 시너지가 좋은 영웅 찾기
- CC · 데미지 · 유틸리티의 밸런스를 자동 분석해 균형 잡힌 조합 추천

**사용자 워크플로**: 본인 팀 4명 입력 → 5번째에 가장 균형 잡힌 영웅 자동 추천.

**발로란트로 옮길 때**: 본 프로젝트의 "5번째 요원 추천"이 정확히 이 형태. **단, "균형"이라는 개념을 발로란트 역할군에 어떻게 매핑할지가 차별점 포인트** (예: Controller 없음 alert).

---

## 7. 결론 — 시장에서 관찰된 패턴

> 아래는 분석으로 드러난 사실 위주의 정리. 채택 권장은 별도 판단의 영역이며 이 문서 범위 밖이다.

### 7.1 발로란트 시장에서 비어 있는 영역

1. **prematch 시점에 모델 기반 승률 예측을 제공하는 도구가 사실상 없다**
   - tracker.gg · blitz.gg · VLR.gg는 **통계 나열 + 사용자의 직감 판단**에 의존.
   - Riot 공식 Pick'Ems는 **사용자 직접 예측 게임**으로, 모델이 보조하지 않음.
   - RIB.GG도 prematch 시뮬레이션보다 **post-game 분석**에 무게.
   - GitHub ML 프로젝트 8개 중 prematch + 조합 단위 + 데이터 혼입 방지를 모두 만족하는 것 없음.

2. **What-if 시뮬레이션을 제공하는 발로란트 도구가 없다**
   - LoL DraftGap·LoLDraftAI에는 있지만, 발로란트에는 비교 가능한 도구가 관찰되지 않음.

3. **자연어로 예측 근거를 설명하는 발로란트 도구가 없다**
   - tracker.gg·blitz.gg는 통계 숫자, RIB.GG는 차트, GitHub 프로젝트는 확률 숫자만 출력.
   - LoLDraftAI가 가장 가까우나 자연어 변환 깊이는 제한적.

4. **개인화(본인 선수 풀·약점 기반 추천)는 LoL Mobalytics·Dota 2 DotaPicker Personal에서 검증됐지만 발로란트는 비어 있음**

### 7.2 발로란트 시장에서 이미 포화된 영역

1. **개인 매치 히스토리·랭크 트래킹**: tracker.gg + blitz.gg + DAK.GG + U.GG + VLR.gg가 모두 제공.
2. **인게임 오버레이의 단순 스탯 표시**: blitz.gg가 표준화. 새로 진입하기엔 사용자 베이스 격차 큼.
3. **프로씬 통계 데이터베이스**: VLR.gg · RIB.GG가 사실상 독점.
4. **요원 티어 리스트**: tracker.gg · DAK.GG · U.GG 등이 다 제공, 차별화 어려움.

### 7.3 사용자 측면에서 관찰된 워크플로 패턴

| 사용자 유형 | 가장 자주 쓰는 도구 | 주 워크플로 |
|-------------|---------------------|-------------|
| 일반 랭크 유저 | blitz.gg + tracker.gg | 매칭 잡히면 오버레이로 동료·상대 정보 확인 → 게임 끝나면 본인 스탯 분석 |
| 프로씬 팬 | VLR.gg + Riot Pick'Ems | 일정 확인 → 직접 예측 → 친구와 비교 |
| 코치·분석가 | RIB.GG (B2B) | 다음 상대 라운드 단위 분석 → 약점 진단 → 스크림 시나리오 설계 |
| 한국 유저 | DAK.GG + 한국 인플루언서 콘텐츠 | 한국어 UX로 본인 스탯·티어 표 확인 |

### 7.4 학술 연구와 상용 도구의 격차

- 학술 측에는 **DraftRec(개인×챔피언 친화도) · 조합 클러스터링 · in-round LSTM · Balance Score(신뢰도)** 같은 흥미로운 결과들이 누적되어 있다.
- 그러나 이들이 **사용자에게 직접 닿는 발로란트 상용 도구로 옮겨진 사례는 관찰되지 않았다**.
- 즉 학술과 상용 사이에 큰 공백이 있으며, 학술 결과를 사용자 측면 기능으로 번역하는 작업 자체가 새로운 가치가 될 수 있다.

### 7.5 카테고리별 데이터 검증·신뢰도 수준

| 카테고리 | 모델 검증 수준 | 데이터 혼입 방지 명시 | 메모 |
|----------|---------------|----------------|------|
| 상용 도구 | 해당 사항 적음 (모델 없음) | — | 통계 나열·랭킹 위주 |
| 학술 연구 | 높음 (peer review 통과) | 일부 명시 | 그러나 사용자 도구로의 이식은 미실현 |
| GitHub ML | 낮음 — 과적합 의심 사례 다수 | 명시 사례 없음 | 학습 정확도 1.0 vs 테스트 0.93 같은 갭 빈번 |

---

## 부록 — 분석 외 추가 도구 메모

- **bo3.gg** — 발로란트 라이브 스코어 + 통계, VLR.gg 유사 포지션
- **wecoach.gg** — "Best Valorant Trackers in 2026" 같은 비교 리뷰 콘텐츠 운영, 자체 도구는 미검증
- **valorant.fandom.com** — 게임 메타·요원·맵 위키
- **henrikdev API** — VLR.gg 데이터 비공식 API 래퍼, 다수 오픈소스 도구의 백엔드로 쓰임 (본 프로젝트 최종 평가 범위에서는 제외된 소스)

이 도구들은 위 본문 카테고리 A의 보조·인접 카테고리로, 사용자 측면 기능에서 별도의 신호를 추가로 제공하지 않아 본 분석의 본문에서는 제외했다.

---

## 참고 자료

### 발로란트 전용 도구
- [Valorant Tracker (tracker.gg)](https://tracker.gg/valorant)
- [Blitz.gg Valorant](https://blitz.gg/valorant) · [Blitz Combat Overlay (Medium)](https://medium.com/blitz-press/blitz-launches-combat-overlay-to-help-players-improve-in-valorant-ecbdd8bd14d7)
- [VLR.gg](https://www.vlr.gg/) · [VLR Pickems](https://www.vlr.gg/19501/pickems) · [VLR Stats](https://www.vlr.gg/stats)
- [RIB.GG](https://www.rib.gg/) · [RIB.GG Analytics](https://www.rib.gg/analytics)
- [Augment.gg](https://augment.gg/)
- [DAK.GG Valorant](https://dak.gg/valorant)
- [U.GG Valorant](https://u.gg/val)
- [Valorant Esports Pick'Ems](https://valorantesports.com/en-US/pickems) · [Fandom Pick'Ems wiki](https://valorant.fandom.com/wiki/Pick'Ems)

### 학술 연구 (재인용: `notice/weekly_plan_2026-05-26.md`)
- DraftRec — [arXiv:2204.12750](https://arxiv.org/abs/2204.12750)
- Balance Score — [arXiv:2309.06248](https://arxiv.org/abs/2309.06248)
- VCT 2022 클러스터링 — [arXiv:2502.01250](https://arxiv.org/abs/2502.01250)
- IEEE CoG 2025 영상 분석 — [arXiv:2510.17199](https://arxiv.org/abs/2510.17199)
- 한국 IJCSMC 2026 Seq2Seq LSTM — Park et al., 선문대학교
- NCI Dublin Pawar 2024 학위논문
- TechRxiv Wang 2025
- IEEE Trans. Games — Hodge et al. 2021

### GitHub ML 오픈소스
- [gupta-v/valorant-performance-predictor](https://github.com/gupta-v/valorant-performance-predictor)
- [Corosso/ValoAI](https://github.com/Corosso/ValoAI)
- [kleinaitis/valorant-match-predictor](https://github.com/kleinaitis/valorant-match-predictor)
- [jasonlow2307/valo-prediction](https://github.com/jasonlow2307/valo-prediction)
- [neilsorkin19/ValLoadoutToWin](https://github.com/neilsorkin19/ValLoadoutToWin)
- [DEF4LT-303/Valorant-Pro-Match-Analysis](https://github.com/DEF4LT-303/Valorant-Pro-Match-Analysis)
- [chechna9/valorant_win_prediction_UI](https://github.com/chechna9/valorant_win_prediction_UI)
- [Juniorffonseca/valorant-predictor](https://github.com/Juniorffonseca/valorant-predictor)

### 타 e-스포츠 도구
- LoL: [U.GG](https://u.gg/) · [Mobalytics](https://mobalytics.gg/) · [Lolalytics (Mobalytics 비교)](https://mobalytics.gg/ugg/) · [DraftGap](https://draftgap.com/) · [LoLDraftAI](https://loldraftai.com/)
- Dota 2: [DotaPicker](http://dotapicker.com/) · [Dota2.tools](https://dota2.tools/tools/dota2-counter-pick) · [Alien Fusion](https://alienfusiongenerator.com/dota-2-counter-picker/) · [Hero Picker Pro](https://play.google.com/store/apps/details?id=com.allattentionhere.heropickerpro&hl=en_US)

### 본 프로젝트 내부 참조
- 기존 차별점 비교: `docs/06_model_test/project_differentiation.md`
- 현재 차별점 요약: `docs/01_overview/01_project_summary.md` 섹션 6
- UI/시연 화면 설계: `docs/08_web/07_styling/`
- 학술 참고문헌 원본 목록: `notice/weekly_plan_2026-05-26.md` 6번 절
- 지도교수 피드백: `notice/second_interview.md`
