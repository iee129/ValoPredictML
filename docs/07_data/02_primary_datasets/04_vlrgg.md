# 04. VLR.gg — 데이터 분포 탐색 리서치

> 작성일: 2026-05-27
> 출처: VLR.gg 사이트 직접 리서치 (코드·기존 수집 파일 미참조)
> 목적: 본 프로젝트 사용자 측면 차별점 강화의 데이터 기반 확보 — Kaggle 단독으로는 만들기 어려운 차별점 후보를 VLR.gg 데이터로 어떻게 메울지 검토한다.

---

## 1. 분석 목적과 범위

### 1.1 왜 이 문서가 필요한가

본 프로젝트 지도교수 2차 미팅(2026-05-25, `notice/second_interview.md`) 이후 사용자 측면 차별점 강화가 핵심 과제로 자리잡았다. `docs/competitive_analysis.md` 결론 7.1에서 도출한 발로란트 시장의 빈자리는 다음 네 가지였다.

1. prematch 시점 모델 기반 승률 예측
2. What-if 시뮬레이션
3. 자연어 예측 근거
4. 개인화(선수 풀·약점 기반) 추천

이 중 일부는 **현재 Kaggle 단독 데이터로는 직접 만들기 어렵다**. 예를 들어:
- 선수의 최근 30·60·90일 단위 agent pool 시각화 → Kaggle은 매치 단위 통합 통계라 시점별 분해가 약함
- 사이드(공격/수비)별 승률 패널 → Kaggle 일부 데이터에 누락
- 5인 조합 빈도 기반 백업 추천 → Kaggle은 조합 단위 빈도 집계가 분산됨

VLR.gg는 발로란트 prematch·post-match 분석의 *de facto* 데이터 표준으로, **위 빈자리를 메울 수 있는 데이터 그라뉼리티와 최신성**을 갖추고 있는지 본 문서에서 직접 점검한다.

### 1.2 무엇을 분석하나

- VLR.gg의 페이지·섹션·필터·메트릭을 사이트 그대로의 구조로 정리
- 어떤 데이터 그라뉼리티(매치/맵/라운드/킬)까지 추출 가능한지
- 시간·지역·대회·요원·맵별 데이터 분포의 폭과 깊이
- Kaggle 데이터셋(`docs/07_data/02_primary_datasets/01~03`)이 못 갖춘 영역과의 보완 관계

### 1.3 무엇은 분석하지 않나

- 본 프로젝트의 기존 수집 코드(`ml/vlrgg/`) 및 이미 적재된 CSV(`data/raw/vlrgg/`) 내용 — 본 문서는 **사이트 그대로의 잠재력**을 보는 것이 목적이므로 의도적으로 미참조
- 본 프로젝트가 채택할 최종 활용 방안의 우선순위 결정 — 본 문서는 가능성 매핑까지, 채택 결정은 별도

---

## 2. VLR.gg 사이트 구조 — 직접 리서치 결과

### 2.1 Top-level Navigation

다섯 개 주 네비게이션 탭이 노출된다.

| 탭 | 역할 |
|----|------|
| Forums | 커뮤니티 토론 (분석 외) |
| Matches | 일정·결과 목록 + 매치 상세 |
| Events | 토너먼트 목록 + 이벤트 상세 |
| Rankings (BETA2) | 팀 랭킹 |
| Stats | 선수·요원 누적 통계 |

추가로 Login·Live Streams 임베드·Night/Spoiler 토글이 보조 UI로 존재한다.

### 2.2 홈 페이지

- **Upcoming Matches**: 지역·토너먼트별로 그룹핑된 임박 경기. 예시: "Esports World Cup 2026: Americas Qualifier", "Challengers 2026" (LATAM/NA/South Asia/EMEA/Brazil)
- **Completed Matches**: 최근 종료 경기의 스코어·타임스탬프
- **Stickied + Recent Discussion**: 커뮤니티 글
- **Ongoing Events / Upcoming Events**: 활성·예정 토너먼트 (VCL 26 BR Stage 2, China Evolution Series 2026 Act 2, Masters London 2026, Champions 2026, Esports World Cup 2026 등)
- **Live Streams**, **Betting odds 광고**

홈 자체는 EDA 가치가 낮으며, 다른 탭으로 진입하기 위한 허브.

### 2.3 /matches/results

| 필드 | 예시 |
|------|------|
| 팀명 + 스코어 | "FlyQuest 2 — 1 Alliance Guardians" |
| 상태 | "Completed" / Live / Upcoming |
| 경과 시간 | "8h 51m" |
| 이벤트명 | "Challengers 2026: North America ACE Stage 3" |
| 스테이지 | "Swiss Stage — Round 1" |
| 보조 자원 | Stats / Maps / VOD (YouTube 또는 Unavailable) |

- **날짜별 그룹핑** (Today, Yesterday, …)
- 페이지네이션: 현재 시점 기준 **648 페이지** → 방대한 히스토리. 페이지당 약 20~30 매치 기준 1.3만+ 매치 추정.
- 매치 카드 클릭 → 상세 페이지 진입

### 2.4 /matches/{match_id} (매치 상세)

매치 상세 페이지는 네 개 탭으로 구성된다.

| 탭 | 내용 |
|----|------|
| Overview | 매치 요약·맵별 스코어·MVP 등 |
| Performance | 선수별 핵심 지표 |
| Economy | 라운드별 경제 (eco/semi-eco/semi-buy/full-buy를 $/$$/$$$/blank로 표기, 잔액 함께) |
| Logs | 라운드별 킬 디스크립션, bomb plant/defuse 타임스탬프, 멀티킬·클러치 라운드 식별 |

추가로 **per-map 또는 entire match** 단위 전환이 가능하다.

→ **본 사이트의 가장 깊은 그라뉼리티**: 라운드 → 킬 단위까지 추출 가능. Kaggle의 매치·맵 단위보다 1~2단계 더 깊다.

### 2.5 /stats

선수·요원 누적 통계 페이지. 컬럼:

| 컬럼 | 의미 |
|------|------|
| R (Rating) | VLR 자체 알고리즘 기반 종합 지표 (kills·deaths·damage·assists·survival 가중합) |
| ACS | Average Combat Score — 전투 기여도 종합 |
| K/D | 킬/데스 비율 |
| KAST | 라운드 중 Kill·Assist·Survive·Trade 중 하나라도 한 비율 (팀플레이 기여도) |
| ADR | Average Damage per Round |
| KPR | Kills per Round |
| APR | Assists per Round |
| FK | First Kills (라운드 첫 킬) |
| FD | First Deaths (라운드 첫 데스) |
| HS% | Headshot Percentage |
| CL% | Clutch 성공률 |

필터 파라미터:

- `event_group_id` (특정 토너먼트 또는 all)
- `region` (Americas·EMEA·Pacific·China·… 또는 all)
- `agent` (29종 또는 all)
- `map_id` (현재 13종 + 미래 맵)
- `timespan` (30d / 60d / 90d / 전체)
- `min_rounds` (예: 200 이상 — 표본 크기 보장)
- `min_rating` (Rating 컷오프)

→ 다축 필터링이 가능해 "Masters Santiago 직전 60일, Astra만, Bind에서, 200라운드 이상" 같은 정밀한 조건 추출이 가능.

### 2.6 /events

| 차원 | 옵션 |
|------|------|
| Tier | VCT · VCL · T3 · Game Changers · Collegiate · Offseason |
| Region | Americas · EMEA · Pacific · China |

페이지네이션 **57 페이지** → 수백 개 이벤트 누적. 시간 커버리지는 현재 시점 기준 2026-10까지 예정(Champions 2026)을 포함하며, 과거 6개월 + 그 이전 시즌까지.

각 이벤트 카드 필드: 토너먼트명, 상태(ongoing/upcoming/completed), prize pool, 날짜 범위, 지역 아이콘.

### 2.7 /event/{event_id} (이벤트 상세)

이벤트 상세는 여섯 개 탭으로 분리된다.

| 탭 | 내용 |
|----|------|
| Overview | Prize Distribution(placement·prize·team·points) + Bracket 시각화(Knockout/Upper Semifinals/Upper Final/Grand Final/Lower Round) + Latest Results |
| Matches | 이벤트 내 모든 매치 (예시 이벤트는 33개) |
| Pick'em | 커뮤니티 예측 페이지 |
| Stats | 이벤트 한정 선수 통계 |
| Agents | 에이전트 pick rate / 사이드별 승률 (별도 절 2.8) |
| News | 이벤트 관련 뉴스 |

Regular Season / Playoffs 단계 구분, 참가 팀 로스터(5명) 노출, Overall Standings 정렬.

### 2.8 /event/agents/{event_id} (에이전트 조합 페이지) ★

본 프로젝트와 직접 관련성 높음.

- 맵별 탭(예시 이벤트는 7개 맵: Split·Haven·Abyss·Breeze·Pearl·Corrode·Bind)
- 각 맵당 게임 수 표시 (예: Split 11 games, Haven 11 games, …)
- 각 맵에서 에이전트별:
  - **Pick rate %** (예: Split에서 Viper 55% / Omen 100% / Sova 100%)
  - **ATK WIN** (공격 사이드 승률)
  - **DEF WIN** (수비 사이드 승률)
- 29개 에이전트 아이콘 버튼 (전체 메타 한눈)
- 팀별 사용 매치 링크

**한계**: 5-agent **조합 단위 통계는 이 페이지에 없음**. 개별 에이전트 빈도만. 5-조합은 팀 상세(2.10)에서 별도 제공.

### 2.9 /rankings

- 14개 지역: World, North America, Europe, Brazil, Asia-Pacific, Korea, China, Japan, LA-S, LA-N, Oceania, MENA, Collegiate 등
- 각 지역당 Top 10 (전체는 별도 페이지)
- 컬럼: Rank · 팀명/로고 · 국가/지역 · Rating 숫자 (2000점 max로 보임)
- BETA2 단계 — 매치 결과·win/loss·rating change 트렌드는 노출되지 않음

### 2.10 /team/stats/{team_id} (팀 맵 통계) ★

본 프로젝트와 직접 관련성 매우 높음.

| 컬럼 | 의미 |
|------|------|
| Map (count) | 맵명 + 그 맵에서의 매치 수 (예: Bind (91)) |
| Win Rate | 전체 승률 |
| W/L | 승·패 |
| ATK first-half record | 공격 사이드로 시작한 매치들의 결과 |
| ATK RWin% | 공격 사이드 라운드 승률 |
| DEF first-half record | 수비 사이드로 시작한 매치들의 결과 |
| DEF RWin% | 수비 사이드 라운드 승률 |
| Round W/L | 양 사이드 통합 라운드 통계 |

**필터**: event · stage · sub-stage · core_id · date range.

**추가 섹션**:
- **Agent Compositions** — 맵별로 사용한 **5-agent 조합 + 사용 빈도** ← 5-조합 단위 통계는 여기에 있음
- **Recent Match Results** (상세 카드)
- 탭: Overview · Stats · Matches · News · Transactions

### 2.11 /player/{player_id} (선수 상세)

| 섹션 | 내용 |
|------|------|
| Header | 닉네임 + 실명 + 국가 + 소셜(트위터·트위치) |
| Tabs | Overview · Match History |
| Agents | 시점 필터(30d/60d/90d/all)로 본 agent pool |
| Recent Results | 최근 매치 카드 |
| Past Teams | 이전 소속 + 기간 |
| Latest News | 선수 관련 뉴스 |
| Event Placements | Total Winnings + 토너먼트별 placement·상금·연도 |

→ **30/60/90일 시점 필터로 agent pool 분해**가 가능. 이것은 본 프로젝트가 이미 설계한 "직전 1년·2년 통계"보다 더 짧은 시점 단위까지 분해 가능함을 의미.

### 2.12 비공식 API

VLR.gg 공식 API는 부재하나 비공식 REST API가 다수 운영된다.

- **axsddlr/vlrggapi** — 메이저 비공식 REST API. v2 엔드포인트는 in-memory TTL 캐시 사용 (라이브 스코어 30s, 결과 60s, 업커밍·매치 상세 5min, 랭킹·트랜잭션 1h). 배포: `https://vlrggapi.vercel.app/v2/`
- **liulalemx/vlrgg-api** — 별도 비공식 REST API
- **Orloxx23/vlresports** — Valorant Esports API
- **akhilnarang/vlrgg-scraper** — 스크래퍼 라이브러리
- **derarken/vlr-api** — Go 패키지

비공식 API 공통 커버리지 (axsddlr 기준):

- 매치 / 선수 / 팀 / 이벤트 매치 엔드포인트
- **per-map player stats** (K/D/A · ACS · Rating)
- **round-by-round 데이터**
- **kill matrix** (선수 간 킬 관계)
- **economy breakdown** (라운드별 경제)
- **head-to-head history** (두 팀 간 과거 매치)
- **map veto data** (밴픽)

---

## 3. 데이터 분포 분석

### 3.1 시간 커버리지

| 단위 | 범위 |
|------|------|
| 페이지네이션 (매치 결과) | 648 페이지 → 누적 1.3만+ 매치 추정 |
| 페이지네이션 (이벤트) | 57 페이지 |
| 가시 시간 범위 | 2026.10(Champions Finals)까지 예정 + 과거 6개월 + 그 이전 시즌 누적 |
| 본 프로젝트 Kaggle 데이터 (참고) | 2021~2026 약 66,784 행 |

VLR.gg는 **현 시점까지의 모든 공식 프로 경기**를 누적한다. Kaggle dataset은 dataset 작성자가 기간을 정한 스냅샷이라 최신성이 부족할 수 있는 반면, VLR.gg는 어제 경기까지 포함된다.

### 3.2 지역 분포

| 카테고리 | 지역 |
|----------|------|
| 메이저 4개 | Americas · EMEA · Pacific · China |
| 세부 14개 (랭킹 기준) | World · NA · Europe · Brazil · APAC · Korea · China · Japan · LA-S · LA-N · Oceania · MENA · Collegiate 등 |
| Tier 6개 (이벤트 기준) | VCT · VCL · T3 · Game Changers · Collegiate · Offseason |

→ 본 프로젝트의 현재 Kaggle 출처는 VCT International·Challengers League·Champions Statistics·기타 보조 dataset 통합이라, **VLR.gg의 Game Changers·Collegiate·Offseason·국가별 세분화는 신규 영역**.

### 3.3 데이터 그라뉼리티 비교

| 그라뉼리티 | Kaggle | VLR.gg |
|------------|--------|--------|
| 매치 단위 | ✓ | ✓ |
| 맵 단위 (1 매치 = N 맵) | ✓ | ✓ |
| 라운드 단위 | 부분(스코어만) | ✓ (Logs 탭) |
| 킬 단위 (kill matrix) | ✗ | ✓ (Logs + API) |
| 경제 단위 (라운드별 loadout) | ✗ | ✓ (Economy 탭) |
| Bomb plant/defuse 타임스탬프 | ✗ | ✓ (Logs 탭) |
| 멀티킬·클러치 라운드 식별 | ✗ | ✓ (Logs 탭) |

VLR.gg는 Kaggle보다 **2단계 더 깊은 그라뉼리티**를 갖춘다 — 라운드·킬·이벤트 타임스탬프까지.

### 3.4 측정 가능한 메트릭 — 사이트가 직접 보여주는 것

| 카테고리 | 메트릭 |
|----------|--------|
| Player (스탯 페이지) | Rating · ACS · K/D · KAST · ADR · KPR · APR · FK · FD · HS% · CL% |
| Team (맵 통계 페이지) | 맵별 매치 수 · 전체 승률 · W/L · ATK first-half record · **ATK RWin%** · DEF first-half record · **DEF RWin%** · Round W/L · **5-agent Composition 빈도** |
| Event (agents 페이지) | 맵별 게임 수 · 에이전트별 pick rate · **ATK WIN** · **DEF WIN** |
| Event (overview) | Prize Distribution · Bracket · 팀 standings |
| Player (개인 페이지) | **Agent pool (30d/60d/90d/all)** · Recent Results · Past Teams · Event Placements · Total Winnings |
| Match (매치 상세) | per-map 선수 통계 · **Round-by-round Economy** ($/$$$/blank) · **Logs** (kill · plant · defuse · multikill · clutch) |
| Ranking | Rating 숫자 (지역별 Top N) |

### 3.5 필터 표현력

| 페이지 | 필터 차원 |
|--------|----------|
| /stats | event_group_id · region · agent · map · timespan(30d/60d/90d/all) · min_rounds · min_rating |
| /events | tier(6) × region(4) |
| /event/agents/* | 매치 라운드별 · 맵별 · 에이전트별 |
| /team/stats/* | event · stage · sub-stage · core_id · date range |
| /player/* (Agents) | timespan(30d/60d/90d/all) |

다축 필터링이 풍부하다 — 본 프로젝트가 차별점으로 만들고 싶은 "특정 시점·특정 메타 한정 분석"이 모두 표현 가능.

---

## 4. Kaggle 데이터셋과의 보완 관계

### 4.1 두 데이터의 정체성

| 항목 | Kaggle | VLR.gg |
|------|--------|--------|
| 정체성 | dataset 작성자가 정해진 시점에 캡처한 스냅샷 | 라이브 사이트, 어제 경기까지 누적 |
| 최신성 | dataset 업데이트 주기에 종속 | 실시간 |
| 그라뉼리티 | 매치·맵 단위 | 매치·맵·라운드·킬 단위 |
| 정형도 | CSV — 분석 즉시 가능 | HTML/JSON — 스크래핑 또는 비공식 API 필요 |
| 라이선스 | dataset별로 명시 | robots.txt 준수, 비상업적 연구 허용 |
| 안정성 | 변하지 않음 (재현성 ↑) | 사이트 구조 변경 시 영향 |

### 4.2 VLR.gg에만 존재하는 데이터 (본 프로젝트 관점)

1. **라운드별 경제 데이터** — eco/semi-eco/semi-buy/full-buy 분류
2. **Kill matrix** — 선수 간 킬 관계 (Logs + API)
3. **ATK/DEF 사이드별 승률** — 맵별·이벤트별·팀별 모두 가능
4. **Bomb plant/defuse 타임스탬프** — 라운드 흐름 분석용
5. **Multikill·Clutch 라운드 식별** — 결정적 순간 식별
6. **선수 Agent Pool의 30/60/90일 시점 분해**
7. **팀 Transactions** (영입/방출 기록)
8. **Map Veto data** (밴픽 정보) — 비공식 API 한정
9. **5-agent Composition + 빈도** (팀 상세 페이지)
10. **실시간 최신성** — 오늘 경기까지

### 4.3 Kaggle이 더 우월한 영역

- **재현성**: VLR.gg는 라이브라 어제와 오늘 결과가 다름. 학술 발표·검증에는 고정 스냅샷이 더 안전 → Kaggle 단독 학습이 "검증 가능한 베이스라인" 가치를 가짐.
- **즉시 분석 가능**: CSV로 즉시 pandas 로딩. VLR.gg는 스크래핑·파싱·정제 작업 선행 필요.
- **레이블 확정성**: Kaggle은 dataset 작성자가 미리 정제한 1행 1맵 단위로 깔끔. VLR.gg는 진행 중 경기·취소 경기 등 노이즈 가능.

### 4.4 통합 전략 시사점

- **베이스라인 모델 학습**은 Kaggle 단독 유지 (재현성·학술 검증의 기준선)
- **심화 모델·UI 보강 데이터**로 VLR.gg 추가 (사용자 차별점 강화)
- 두 데이터의 dedup_key는 (대회·맵·팀명·요원셋·스코어) 정규화 후 매칭 가능 (`docs/07_data/07_data_schema/01_unified_schema.md` 참고)

---

## 5. 사용자 차별점 강화 가능성

> `docs/competitive_analysis.md` 결론 7.1의 4가지 빈자리(prematch 모델 / What-if / 자연어 / 개인화)와 매핑해 본다. 본 절은 *가능성 매핑*까지이고 채택 결정은 별도다.

### 5.1 시간 슬라이더 기반 메타 변화 라인

**VLR.gg 활용 데이터**: `/stats` + `/event/agents/*`의 timespan 필터 + 이벤트별 pick rate

**구현 시나리오**:
- 사용자가 입력한 5명 요원 + 맵을 받음
- VLR.gg에서 그 5명 각각의 이벤트별 pick rate 추출
- "당신이 선택한 Jett는 VCT Americas Stage 1에서 픽률 73% → Stage 2에서 41% → Masters Santiago에서 28%로 하락 추세" 같은 메타 변화 라인 표시

**Kaggle 단독으로 어려운 이유**: Kaggle은 연도 단위 집계가 한계. 이벤트·패치 단위 분해는 VLR.gg event 그라뉼리티가 필요.

### 5.2 사이드별(ATK/DEF) 승률 패널

**VLR.gg 활용 데이터**: `/team/stats/{id}`의 ATK RWin% / DEF RWin%, `/event/agents/*`의 ATK WIN / DEF WIN

**구현 시나리오**:
- 사용자가 입력한 조합 + 맵에 대해
- "이 조합은 Bind 공격 사이드에서 평균 62%, 수비 사이드에서 48%로, **공격 시작이 유리**합니다" 패널 표시
- 코치가 사이드 선택 단계에서 즉시 참고

**Kaggle 단독으로 어려운 이유**: Kaggle 일부 dataset에는 사이드별 라운드 결과가 누락되거나 정형화되지 않음.

### 5.3 팀 vs 팀 Head-to-Head 미니 패널

**VLR.gg 활용 데이터**: 비공식 API의 head-to-head 엔드포인트

**구현 시나리오**:
- 입력 단계에서 사용자가 두 팀명도 함께 입력(선택)
- "두 팀 과거 5경기: T1 3승 2패, 최근 매치는 2026-04-15 T1 2-0 승" 같은 보조 패널

**주의**: 본 프로젝트는 모델 피처로 팀명 누적 이력 사용을 차단(`docs/01_overview/01_project_summary.md` 섹션 3.4)했으므로 **모델 피처가 아닌 UI 보조 정보**로만 활용. 피처화하면 미래 정보가 섞일 수 있음.

### 5.4 선수 Agent Pool 시각화 ★

**VLR.gg 활용 데이터**: `/player/{id}` Agent Pool (30d/60d/90d/all 필터)

**구현 시나리오**:
- 입력한 선수 10명 각각의 최근 60일 agent pool을 미니 도넛 차트로 표시
- "이 선수는 평소 Jett 67%·Raze 22%·Neon 11%인데, 이번 경기는 Cypher 픽" 같은 **out-of-pool 알림**
- 사용자가 "이 픽이 평소와 다르다 — 메타 실험인가 트롤인가" 판단

**Kaggle 단독으로 어려운 이유**: Kaggle은 선수 누적이 연도 단위·전체 단위 집계. 30/60/90일 시점 분해는 VLR.gg가 사이트 차원에서 지원.

**`competitive_analysis.md` 결론 7.1 매핑**: "개인화(본인 선수 풀·약점 기반 추천)" 빈자리에 직접 대응.

### 5.5 Composition 빈도 기반 백업 추천

**VLR.gg 활용 데이터**: `/team/stats/{id}`의 Agent Compositions 섹션 (5-agent 조합 + 빈도)

**구현 시나리오**:
- 사용자가 입력한 5-agent 조합이 모델에게 처음 보는 조합일 때
- VLR.gg에서 "이와 가장 유사한 조합 중 과거에 자주 쓰인 Top 3" 자동 검색
- 모델 예측에 더해 "**이 조합은 프로씬에서 12경기 사용, 평균 승률 58%**" 같은 historical reference

**Kaggle 단독으로 어려운 이유**: 5-조합 단위 빈도 집계는 분산되어 있어 매칭 비용이 큼. VLR.gg는 팀 페이지에서 그대로 제공.

### 5.6 Economy-aware 분석 (장기 후보)

**VLR.gg 활용 데이터**: 매치 상세 Economy 탭, 비공식 API의 economy breakdown

**구현 시나리오**:
- "이 조합은 eco 라운드(돈 부족) 승률 21%, full-buy 라운드 승률 59%로 **풀바이 의존도 높음**" 분석
- 코치가 "이 조합은 라운드 1패 후 회복이 어렵다"는 패턴 파악

**기말까지 가능성**: 본 프로젝트 시간 범위 밖일 수 있음. 향후 확장 후보로만 메모.

### 5.7 매핑 요약

| competitive_analysis 빈자리 | VLR.gg 활용 후보 |
|-----------------------------|------------------|
| prematch 모델 기반 승률 예측 | 본 프로젝트 모델 자체 (Kaggle 학습) — VLR.gg는 보조 |
| What-if 시뮬레이션 | 5.2 사이드별 패널 + 5.5 historical reference로 보강 |
| 자연어 예측 근거 | 5.1 메타 변화 + 5.4 agent pool 데이터를 자연어 문장 변수로 활용 |
| 개인화(선수 풀·약점) | **5.4 선수 Agent Pool 시각화 ★ 직접 대응** |

---

## 6. 데이터 품질·한계

### 6.1 강점

| 항목 | 평가 |
|------|------|
| 매치 메타데이터 정확성 | VCT 공식 경기는 거의 모든 정보 완비 |
| 실시간 최신성 | 오늘 경기까지 |
| 그라뉼리티 깊이 | 라운드·킬·이벤트 타임스탬프 |
| 다축 필터 표현력 | 이벤트·지역·맵·요원·시점·통계 컷오프 모두 |
| 비공식 API 생태계 | 5개 이상 운영 중 (axsddlr · liulalemx · Orloxx23 · akhilnarang · derarken) |
| 커뮤니티 검증 | 발로란트 프로씬의 *de facto* 데이터 표준 |

### 6.2 한계

| 항목 | 영향 |
|------|------|
| 비공식 데이터 | 사이트 구조 변경 시 스크래퍼 재작성 필요 |
| robots.txt 준수 | 요청 간격 2~3초 권장, 대량 수집은 시간 소요 큼 |
| 일부 매치 VOD 미존재 | 영상 기반 분석 불가능 |
| 진행 중 경기 데이터 변동성 | 라이브 매치는 결과 확정 전까지 노이즈 |
| 일부 페이지 무한 리다이렉트 | 본 리서치 중 /stats, /event/{id} 일부 페이지에서 WebFetch 실패 사례 발생 — 비공식 API 또는 다른 진입 경로 필요 |
| 5-agent 조합 통계의 비표준성 | /event/agents/*는 개별 에이전트만, /team/stats/*에는 조합 — 페이지마다 데이터 위치 다름 |
| 신규 이벤트 누락 | 막 시작한 토너먼트는 메트릭 미집계 시점 존재 |

### 6.3 라이선스·정책

- **robots.txt 준수 필수** — 본 리서치 시점 정책상 비상업적 연구 허용
- **재배포 금지** — 본 프로젝트는 학내 학습용으로 사용 가능하나 데이터 자체를 다시 외부 공개는 금지
- **상업적 이용 금지** — 본 프로젝트가 졸업 후 상업화 시 사용 정책 재검토 필요
- **크롤링 간격** — 2~3초 이상 delay 권장 (관행)

---

## 7. 다음 단계 제안

### 7.1 즉시 — 중간 발표 직후 (~6/1)

- 별도 컴퓨터에서 진행 중인 VLR.gg 본격 스크래핑 완료 모니터링
- **우선 수집 페이지**:
  - `/stats` (필터별 분해 — 선수 누적 통계의 시점 분해)
  - `/event/agents/{id}` (이벤트별 에이전트 pick rate + 사이드별 승률)
  - `/team/stats/{id}` (팀별 맵 통계 + 5-agent Composition)
  - `/player/{id}` Agents (선수 30/60/90일 agent pool)
- **후순위 수집**:
  - 매치 상세 Economy / Logs — 라운드 단위 데이터, 본 프로젝트 단기 범위 밖이나 자산화 가치
  - Rankings — 보조 신호

### 7.2 통합 작업 — 2주차 (6/2 ~ 6/8)

- Kaggle 데이터와 dedup_key 일치 검증 (`docs/07_data/07_data_schema/01_unified_schema.md` 활용)
- VLR.gg 고유 데이터를 다음 두 트랙으로 분리 적용:
  - **모델 피처 트랙**: 선수 30/60/90일 agent pool 신규 피처 추가 → 베이스라인·심화 모델 재학습 후 AUC 변화 비교
  - **UI 보강 트랙**: 사이드별 승률·메타 변화 라인·composition 빈도 → 웹 시뮬레이터(Next.js `web`)의 보조 패널로 합성
- 두 트랙 모두 데이터가 섞이지 않는지 동일하게 확인해야 함 (`docs/06_model_test/project_differentiation.md` 기준)

### 7.3 발표·보고서 반영

- 본 문서를 기말 발표 보고서의 "데이터 소스 확장" 섹션 근거 자료로 인용
- `notice/weekly_plan_2026-05-26.md`의 차별점 6번(박빙 보강) · 7번(What-if 보강) · 8번(자연어 보강) 각 항목에 VLR.gg 데이터로 메울 부분을 명시
- 모델 성능 비교: Kaggle 단독 vs Kaggle + VLR.gg 통합 → AUC·박빙 정확도·Brier 변화량 보고

---

## 8. 참고 자료

### 본 리서치에서 직접 방문한 VLR.gg 페이지

- [VLR.gg 홈](https://www.vlr.gg/)
- [/matches/results](https://www.vlr.gg/matches/results)
- [/events](https://www.vlr.gg/events)
- [/rankings/world](https://www.vlr.gg/rankings/world)
- [/event/agents/2760 — Masters Santiago 2026](https://www.vlr.gg/event/agents/2760/valorant-masters-santiago-2026)
- [/team/stats/2 — Sentinels Map Stats](https://www.vlr.gg/team/stats/2/sentinels/)
- [/player/9 — TenZ](https://www.vlr.gg/player/9/tenz)

### VLR.gg 관련 외부 자료

- [VLR Rating 설명 (커뮤니티 스레드)](https://www.vlr.gg/160667/vlr-gg-player-rating-explained)
- [Custom Rating System Update](https://www.vlr.gg/481169/custom-rating-system-update)
- [Match page update 공지](https://www.vlr.gg/2069/introducing-the-match-page-update)
- [VLR API discussion thread](https://www.vlr.gg/75529/vlr-api)

### 비공식 API·스크래퍼

- [axsddlr/vlrggapi (REST API + 배포)](https://github.com/axsddlr/vlrggapi)
- [liulalemx/vlrgg-api](https://github.com/liulalemx/vlrgg-api)
- [Orloxx23/vlresports](https://github.com/Orloxx23/vlresports)
- [akhilnarang/vlrgg-scraper](https://github.com/akhilnarang/vlrgg-scraper)
- [derarken/vlr-api (Go)](https://pkg.go.dev/github.com/derarken/vlr-api)

### 본 프로젝트 내부 참조

- `docs/competitive_analysis.md` — 발로란트 도구 시장 빈자리 분석 (5.1~5.5 매핑의 기반)
- `docs/07_data/02_primary_datasets/01_vct_2021_2023.md` · `02_vct_2024.md` · `03_valorant_ranked.md` — Kaggle dataset 분석
- `docs/07_data/05_scraping_sources/01_vlrgg_scraping.md` — 스크래핑 가이드(HOW)
- `docs/07_data/07_data_schema/01_unified_schema.md` — Kaggle ↔ VLR.gg 통합 스키마
- `docs/06_model_test/project_differentiation.md` — 본 프로젝트 데이터 혼입 방지 기준 (VLR.gg 추가 데이터에도 동일 적용 필수)
- `docs/01_overview/01_project_summary.md` 섹션 3 — 팀명 피처화 금지 정책 (5.3 H2H 패널의 피처화 금지 근거)
- `notice/weekly_plan_2026-05-26.md` — VLR.gg 통합 트랙 계획
- `notice/second_interview.md` — 지도교수 사용자 측면 차별점 강화 피드백
