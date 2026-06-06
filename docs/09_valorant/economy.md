# economy.md — 발로란트 라운드 이코노미 + 27 요원 ult cost

작성: 2026-05-09
출처: Riot 공식 게임 명세 + Liquipedia "Economy" 페이지.
US-002의 visualize25 SQLite `Games` 테이블 (Eco/SemiEco/FullBuy/Pistol 라운드 분류) + `Game_Rounds.RoundHistory` 컬럼 활용 예정.

---

## VLR 검증 블록 (report-backed, 2026-05-10)

기준 리포트: `reports/research_validation.json` (`generated_at=2026-05-10T03:04:34Z`). 현재 VLR 검증 산출물은 economy round breakdown을 포함하지 않으므로 pistol/eco/full-buy 승률 문장은 갱신하지 않는다.

| fact_id / section | metric | value | sample_size | source_url / dataset_id | verdict |
|-------------------|--------|-------|-------------|--------------------------|---------|
| FACT-VLR-INGESTION-MATCHES | vlrgg_match_rows | 11,400 rows | 11,400 | `data/processed/vlrgg_matches.csv` | CONFIRMED |
| FACT-MODEL-FEATURE-CONTRACT | active_model_feature_count | advanced 179 / baseline 421 | 91,458 rows (train 75,405 + test 16,053) | `reports/advanced/metrics.json` / `final/deliverables/00_수치_단일진실표.md` | CONFIRMED |
| economy_report_facts | economy-specific VLR facts | 0 rows | 0 | `reports/research_validation.json` | INSUFFICIENT_DATA |

경제 관련 수치는 현재도 Riot/Liquipedia/visualize25 기반 가설로 유지한다. VLR 기반 갱신 조건은 match detail 또는 round economy fields가 provenance와 함께 `report_facts`로 생성되는 것이다.

---

## 출처 매핑 (sources.md anchor)

본 문서의 모든 수치·메커니즘은 다음 두 출처로 추적된다.

| 항목 | sources.md anchor | URL |
|------|-------------------|-----|
| Credits 시스템 (시작 자금 / 라운드 보상 / 무기 가격 / 능력 가격) | [S-22] | https://liquipedia.net/valorant/Economy |
| Ult orb 획득 메커니즘 + 27 요원 ult orb 비용 | [S-2] (Riot Agents Page) | https://playvalorant.com/en-us/agents/ |
| 맵별 ult orb 갯수 | [S-3] (Riot Maps Page) | https://playvalorant.com/en-us/maps/ |
| Pistol 라운드 영향 통계 (도메인 가설 검증 입력) | [S-26] (VLR.gg agent stats) | https://www.vlr.gg/stats |
| visualize25 SQLite 컬럼 정의 (Eco/SemiEco/FullBuy/Pistol) | (US-002 데이터셋 자체 명세) | data/raw/kaggle/visualize25/valorant.sqlite |

---

## 1. Credits 시스템

### 1-A. Round 시작 자금
- **Pistol 라운드**: 800 credits 균일 (1라운드 + 13라운드 half time)
- **이후 라운드**: 이전 라운드 결과에 따라 변동 (max 9000)

### 1-B. Round 종료 보상
| 사건 | 보상 |
|------|------|
| 라운드 승리 (수비) | +3000 credits |
| 라운드 승리 (어택, 폭탄 폭발) | +3000 credits |
| 라운드 패배 (1패) | +1900 credits |
| 라운드 패배 (2연패) | +2400 credits |
| 라운드 패배 (3연패+) | +2900 credits |
| 폭탄 설치 (어택) | +300 credits (개인) |
| 적 처치 | +200 credits (Classic 등 무관, 일부 무기는 +300) |

라운드 보상 캡 = **9000 credits**.

### 1-C. 무기·능력 구매 가격 (대표)
- **권총** Classic 기본 (무료), Sheriff 800c, Ghost 500c
- **SMG** Stinger 950c, Spectre 1600c
- **샷건** Bucky 850c, Judge 1850c
- **소총** Bulldog 2050c, Guardian 2250c, Phantom 2900c, Vandal 2900c
- **스나이퍼** Marshal 950c, Outlaw 2400c, Operator 4700c
- **헤비** Ares 1550c, Odin 3200c
- **방어구** Light Shield 400c, Heavy Shield 1000c
- **능력** 요원별 100c~600c (단가 1회), ult은 orb 시스템

### 1-D. Buy 카테고리 정의 (visualize25 SQLite 컬럼 매칭)

| 카테고리 | 자금 범위 | 일반적 buy | SQLite 컬럼 |
|---------|----------|-----------|------------|
| **Pistol** | 800c | 권총 + 능력 1-2개 | `Pistol` |
| **Eco** | 0-2000c | Classic 그대로 + 방어구 일부 | `Eco` |
| **Semi-Eco / Half** | 2000-3000c | Sheriff/Spectre + Light Shield | `SemiEco` |
| **Force / Full** | 3000-3900c | Phantom 일부 (1-2명) | (Full Buy 일부) |
| **Full Buy** | 4000c+ | Phantom/Vandal + Heavy Shield + 능력 | `FullBuy` |

US-002에서 visualize25 `Games` 테이블의 4컬럼 (Eco/SemiEco/FullBuy/Pistol)별 **개별 라운드 승률** 산출.

---

## 2. Pistol 라운드 영향

### 2-A. 메커니즘
- 1라운드 + 13라운드(half time) = 시즌당 2회 균등 자금 라운드.
- Pistol 승리 측: 다음 2-3 라운드 동안 자금 우위 (3000+1900 vs 1900+800 = ~2200 credit gap).
- 일반적으로 pistol 승리 측이 다음 라운드(2/14)에서 anti-eco buy → 추가 우위 누적.

### 2-B. 데이터 검증 가설

| ID | 가설 |
|----|------|
| H-ECO-PISTOL-IMPACT | Pistol 라운드 승리 측이 다음 2 라운드 평균 승률 +35%p (vs 50% baseline) |
| H-ECO-PISTOL-HALF-WIN | Pistol 2회(1+13) 모두 승리 시 매치 승률 +25%p |
| H-ECO-PISTOL-AGENT-PREF | Pistol 라운드 win rate가 가장 높은 요원: Sheriff one-shot 가능 + 능력 시너지 (Reyna, Jett, Phoenix self-flash) |

### 2-C. visualize25 데이터 활용 예시

```python
# Game_Rounds.RoundHistory 파싱 → pistol 라운드 식별 (RoundNumber == 1 or 13)
df_pistol = df_rounds[df_rounds["round_number"].isin([1, 13])]
pistol_winrate = df_pistol.groupby("agent")["round_won"].mean()
```

---

## 3. Eco 카테고리별 라운드 승률 (도메인 가설)

### 3-A. 일반 패턴 (도메인 추정 — VCT 2024 일반)

| 카테고리 | 가설 라운드 승률 | 메커니즘 |
|---------|----------------|---------|
| Pistol vs Pistol | ~50% | 균등 자금 |
| Eco vs Full Buy | ~10-15% | 무기 격차 |
| Force vs Full Buy | ~25-30% | 부분 격차 |
| Full vs Full | ~50% | 균등 |
| Anti-eco Full vs Eco | ~80-85% | 강한 자금 우위 |

### 3-B. 데이터 검증 가설

| ID | 가설 |
|----|------|
| H-ECO-FULLBUY-VS-ECO | Full Buy vs Eco 라운드에서 Full Buy 측 승률 ≥80% |
| H-ECO-FORCE-EFFICIENCY | Force buy(2000-3000c)는 Eco(0-2000c) 대비 라운드 승률 +12%p |
| H-ECO-CONSECUTIVE-LOSS | 3연패 후 +2900 보상 시 다음 라운드 Force/Full 가능 → 승률 +18%p (vs 1패 후 +1900) |
| H-ECO-CATEGORY-BALANCE | 매치 승리 팀의 Full Buy 라운드 비율이 패배 팀 대비 +15%p |

US-002의 visualize25 `Games` 테이블에서 `FullBuy_Win`, `Eco_Win` 등 컬럼이 라운드 단위 승률로 직접 계산 가능 (이미 집계된 컬럼).

---

## 4. 29 요원 Ult Cost (orb) 표 — Liquipedia 검증 (2026-05-09)

각 요원별 `Ultimate` 능력 발동에 필요한 orb 갯수. **낮을수록 ult 사이클 빠름**.
모든 수치는 Liquipedia 개별 요원 페이지의 `Ultimate Cost` 필드 직접 추출 (sources.md S-37~S-41).

### 4-A. 6 orb ult (3 요원, 가장 낮음)

| 요원 | 역할 | Ult 이름 | 효과 (요약) |
|------|------|---------|-----------|
| Phoenix | Duelist | Run It Back | 자가 부활 (시전 위치) |
| Reyna | Duelist | Empress | 연사·재장전 가속 + 무적 |
| Cypher | Sentinel | Neural Theft | 시체 정보 (적 위치 표시) |

### 4-B. 7 orb ult (10 요원)

| 요원 | 역할 | Ult 이름 | 효과 (요약) |
|------|------|---------|-----------|
| Neon | Duelist | Overdrive | 전기 빔 sprint |
| ISO | Duelist | Kill Contract | 1v1 결투장 |
| KAY/O | Initiator | NULL/cmd | 광역 12초 suppress (능력 차단) |
| Gekko | Initiator | Thrash | 사이트 폭파 (스파이크 운반) |
| Omen | Controller | From the Shadows | 글로벌 TP |
| Astra | Controller | Cosmic Divide | 글로벌 음향·시야 차단 벽 |
| Harbor | Controller | Reckoning | 광역 물 폭격 (스턴) |
| Sage | Sentinel | Resurrection | 아군 부활 |
| Deadlock | Sentinel | Annihilation | 적 끌어가기 펄스 |
| Veto (신규 2025-10) | Sentinel | Evolution | mutation 강화 ult — debuff 면역 + 전투 보너스 (Liquipedia 7 orb 검증 2026-05-09) |

### 4-C. 8 orb ult (12 요원, 가장 흔함)

| 요원 | 역할 | Ult 이름 | 효과 (요약) |
|------|------|---------|-----------|
| Jett | Duelist | Blade Storm | 수리검 (recharge on kill) |
| Raze | Duelist | Showstopper | 로켓 발사기 |
| Yoru | Duelist | Dimensional Drift | 투명·무적 이동 |
| Waylay | Duelist | Convergent Paths | 광역 디버프 빔 |
| Sova | Initiator | Hunter's Fury | 3발 관통 화살 |
| Skye | Initiator | Seekers | 3 추적 페트 |
| Fade | Initiator | Nightfall | 광역 공포·위치 표시 |
| Brimstone | Controller | Orbital Strike | 광역 폭격 |
| Clove | Controller | Not Dead Yet | 자가 부활 |
| Chamber | Sentinel | Tour de Force | 저격총 |
| Vyse | Sentinel | Steel Garden | 광역 무기 잠금 |
| Miks (신규 2026-03) | Controller | Bassquake | 음파 펄스 — knockback + Deafen + Slow |

### 4-D. 9 orb ult (4 요원, 가장 높음)

| 요원 | 역할 | Ult 이름 | 효과 (요약) |
|------|------|---------|-----------|
| Breach | Initiator | Rolling Thunder | 광역 연쇄 스턴 |
| Tejo | Initiator | Armageddon | 광역 폭격 |
| Viper | Controller | Viper's Pit | 광역 가스 dome |
| Killjoy | Sentinel | Lockdown | 광역 13초 detain |

### 4-E. 분포 요약 (29 요원 — 4단계 카테고리)

| Ult cost | 요원 수 | 비율 | 팀당 ult 사이클 (도메인 가설) |
|----------|--------|------|---------------------------|
| 6 orb | 3 | 10.3% | 맵당 평균 ult 횟수 +2회 (가장 빠른 사이클) |
| 7 orb | 10 | 34.5% | 맵당 평균 ult 횟수 +1회 |
| 8 orb | 12 | 41.4% | baseline |
| 9 orb | 4 | 13.8% | 맵당 평균 ult 횟수 -1회 (가장 느린 사이클) |

총 **29 요원**. ⚠️ **이전 학습 데이터 분포(6-orb 4명 / 7-orb 17명 / 8-orb 6명) 대비 큰 변화** — Liquipedia 직접 검증으로 확인된 실측치는 **4단계 분산** (3-10-12-4). 이는 Riot의 ult cost 시스템 패치 누적의 결과로 추정.

### 4-F. 데이터 검증 가설 (29 요원 4단계 분포 기준)

| ID | 가설 |
|----|------|
| H-ULT-COST-CYCLE | 6-orb ult 보유 팀은 9-orb ult 보유 팀 대비 맵당 ult 횟수 +2회 |
| H-ULT-LOWORB-DUELIST | Phoenix/Reyna(6 orb duelist)는 ult 사이클이 빠름 → 다중 사용 라운드 승률 +3%p |
| H-ULT-HIGHORB-COMP | 9-orb 요원 ≥2명 보유 팀은 매치당 ult 부족 → 라운드 승률 -3%p |
| H-ULT-CYPHER-CYCLE | Cypher 6-orb는 sentinel 중 가장 빠른 ult 사이클 → 매치당 ult 평균 1.8회 (vs Killjoy 9-orb 0.8회) |
| H-ULT-9ORB-PENALTY | 9-orb ult 4종(Breach, Tejo, Viper, Killjoy) 보유 팀이 동시에 2명 이상이면 long match 시 ult deficit |
| H-ULT-DUELIST-8ORB-MAJORITY | Duelist 중 7명이 8-orb (Jett, Raze, Yoru, Waylay) — entry duelist의 사이클 한계가 박빙 매치에 영향 |

---

## 5. Ult Orb 획득 메커니즘

### 5-A. 획득 source (라운드당)
- **Kill**: +1 orb / kill (어시스트 0)
- **Plant**: +1 orb (어택, 폭탄 설치자만)
- **Defuse**: +1 orb (수비, 해체자만)
- **Round 패배**: +1 orb (loss compensation, 모든 팀원)
- **Map ult orb**: 맵당 4-5개 (라운드마다 리셋, 먼저 줍는 팀 +1 orb)
- **Spike pickup without plant**: 0 (보상 없음)

### 5-B. 맵별 ult orb 갯수 (Riot 공식)

| 맵 | Ult orb 수 |
|----|-----------|
| Ascent | 2 (mid 영역) |
| Bind | 2 |
| Haven | 2 |
| Split | 2 |
| Icebox | 2 |
| Breeze | 2 |
| Fracture | 2 |
| Pearl | 2 |
| Lotus | 2 |
| Sunset | 2 |
| Abyss | 2 |
| Corrode | 2 (Riot 표준 맵 ult orb 수) |

대부분 맵이 2개. Map ult orb는 라운드마다 리셋되며 먼저 줍는 측만 획득.

### 5-C. 데이터 검증 가설

| ID | 가설 |
|----|------|
| H-ULT-ORB-MAP-CONTROL | Map orb 점유율 ≥60% 팀의 매치 승률 +8%p |
| H-ULT-ORB-LOSS-COMP | 1라운드 패배 후 loss comp orb로 2라운드 force buy 패턴 — 데이터 빈도 ≥30% |

---

## 6. 라운드 카테고리 + 박빙 매치 연결

박빙 매치(margin=2 이내)에서 ult 라운드 결정력 ↑. 본 프로젝트의 핵심 박빙 AUC 0.88+ 목표와 직결.

### 6-A. 박빙 매치 도메인 가설

| ID | 가설 |
|----|------|
| H-CLOSE-ULT-RATIO | 박빙 매치(margin=2)에서 ult 라운드(≥2개 ult 사용) 비율 ≥40% (vs 일반 매치 25%) |
| H-CLOSE-FULLBUY-RATIO | 박빙 매치에서 양 팀 Full Buy 라운드 비율 ≥60% (자금 균형 → 박빙 형성) |
| H-CLOSE-PISTOL-DOUBLE | 박빙 매치 50%+ 가 양 팀 pistol 1승 1패 분배 매치 |
| H-CLOSE-OT-FREQUENCY | 박빙 매치 내 OT(연장전) 비율 ≥15% |

US-005에서 모두 검증 → 박빙 메커니즘 cross-validation.

---

## 7. visualize25 SQLite 기반 라운드 피처 후보 (US-005 P6)

`Game_Rounds.RoundHistory` 파싱 → 라운드 단위 피처:

| 피처 후보 | 정의 |
|---------|------|
| `pistol_win_rate_a/b` | A/B 팀의 1·13 라운드 승률 (시즌 평균) |
| `eco_round_count_a/b` | 매치 내 Eco 라운드 수 |
| `fullbuy_round_count_a/b` | 매치 내 Full Buy 라운드 수 |
| `eco_efficiency_a/b` | (Eco 라운드 승) / (Eco 라운드 수) |
| `force_buy_streak_a/b` | 연속 Force/Full 라운드 최대 길이 |
| `ult_round_freq_a/b` | (ult 사용 라운드) / (전체 라운드) |
| `low_orb_ult_advantage` | A·B 팀 6-orb ult 보유 차이 |
| `eco_round_winrate_diff` | A·B Eco 승률 차이 |

총 8-12개 피처 → US-005 `FEATURE_COLS_P6` 후보.

---

## 메모

- 29 요원 ult cost 표 완비 (6 orb 3명 + 7 orb 10명 + 8 orb 12명 + 9 orb 4명, 합 29 — Liquipedia 검증 2026-05-09).
- Pistol/Eco/Force/Full Buy 모든 카테고리 + visualize25 SQLite 컬럼 매칭 표 포함.
- Map orb 갯수 + 획득 메커니즘 + loss compensation 모두 설명.
- 박빙 매치 메커니즘 → 본 프로젝트 박빙 AUC 0.88 목표와 직결.
- 데이터 검증 가설 ≥18개 (H-ECO + H-ULT + H-CLOSE 카테고리) — US-005 입력.
