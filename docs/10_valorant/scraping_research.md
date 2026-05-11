# scraping_research.md — VLR.gg 데이터 수집 정책

작성: 2026-05-09  
상태: **보수적 혼합 사용** (Kaggle VLR proxy/기존 cache 우선, self-host API 선택, direct HTML fallback 제한)

이 문서는 VLR.gg 데이터 수집의 가능성, 제약사항, 수집 가드레일을 기술합니다. 현재 모델 학습 피처 계약은 P1-P4 57개 기준을 유지하며, VLR.gg 유래 데이터는 리서치 문서 검증과 UI 근거로만 사용합니다.

---

## 1. VLR.gg 직접 스크래핑 메커니즘

### 1.1 ToS 분석 및 회색 지대

**VLR.gg Terms of Service (조사 기준)**:
- 공식 ToS URL: https://www.vlr.gg/ (대시보드 하단 "Terms" 참조)
- 스크래핑 금지 조항: 명시적 금지 미발견 (많은 esports 사이트와 달리 ToS에서 자동화 도구 사용을 특별히 제한하지 않음)
- **회색 지대**: ToS 부재 = 묵시적 동의 아님. 기술적 접근 가능 ≠ 법적 권리.

### 1.2 Robots.txt 상태

**VLR.gg Robots.txt**: https://www.vlr.gg/robots.txt

```
User-agent: *
Disallow: /search/auto
Disallow: /rr/
```

**해석**:
- 2026-05-10 확인 기준으로 사이트 전체 `Disallow: /`가 아니라 `/search/auto`, `/rr/`만 차단.
- 법률 자문은 아니며, robots.txt 허용 여부와 별개로 ToS·서버 부하·저작권 리스크는 남음.
- **프로젝트 결론**: direct HTML은 기본 비활성. 필요한 경우에도 허용 경로 allowlist, 낮은 페이지 수, 1 req/s 이하 요청률로 제한한다. 현재 확장 수집은 리서치 검증/프론트 차별화용 산출물에 한정하며, 모델 학습 피처 계약은 변경하지 않는다.

### 1.3 비공식 API (axsddlr/vlrggapi) 트레이드오프

**프로젝트**: https://github.com/axsddlr/vlrggapi  
**라이선스**: MIT  
**메커니즘**: FastAPI 기반 비공식 래퍼 (VLR.gg HTML 스크래핑 후 JSON 반환)

| 측면 | 직접 스크래핑 | axsddlr/vlrggapi |
|------|-------------|------------------|
| 법적 리스크 | **중간** (일부 경로 robots 허용이나 ToS·부하 리스크 존재) | **중간** (self-host해도 원천은 VLR.gg HTML) |
| 유지보수 | 구조 변경 시 파서 수정 필요 | API 유지보수자가 담당 |
| 레이트 리밋 | 자체 관리 필요 | README상 600/min 제한이나 본 프로젝트는 1 req/s 보수 운영 |
| 신뢰성 | VLR.gg 서버 의존 | 추가 인프라 레이어 |
| 데이터 신선도 | 실시간 | 캐시 정책에 따라 지연 |

**현재 기본값**: 공개 Vercel URL은 README상 down 상태이므로 self-host/local `http://127.0.0.1:3001` + `/v2` API를 기본으로 둔다. 비공식 API 사용 시에도 법적 리스크는 완전히 제거되지 않으므로 출처와 fetched 시각을 리포트에 남긴다.

---

## 2. 구현 정책 (보수적 혼합)

### 2.1 레이트 리미팅

만약 VLR.gg 스크래핑을 구현한다면:

```python
# 권장 정책
RATE_LIMIT_PER_SECOND = 1.0          # 1 request/sec (VLR.gg 서버 부하 완화)
MAX_REQUESTS_PER_SESSION = 5000       # 세션당 최대 요청 (공정한 사용)
REQUEST_TIMEOUT_SECONDS = 10          # HTTP 타임아웃
RETRY_MAX_ATTEMPTS = 3                # 실패 재시도
RETRY_BACKOFF_FACTOR = 2              # 지수 백오프 (1s → 2s → 4s)
```

**정당성**: 1 req/s는 개인 PC에서 수용 가능한 속도이며, VLR.gg 서버에 미미한 부하를 끼침. 5,000 req/세션은 ~1.4시간 분량 데이터(경기 ~500경기, 각 10 페이지)에 상응.

### 2.2 캐시 전략

```
data/raw/vlrgg_cache/
├── events/
│   ├── vct_2024_masters_madrid.json
│   ├── vct_2024_masters_shanghai.json
│   └── ...
├── agent_stats/
│   └── agents_vct_2025_stage_1.json
├── metadata/
│   └── last_update_timestamp.json
└── .gitignore  # (원본 캐시 커밋 금지)
```

**정책**:
- 캐시 만료: 7일 (시즌 중) / 30일 (시즌 외)
- 중복 요청 방지: 캐시 존재 시 URL 스킵
- 버전 관리: 캐시 파일에 `"fetched_at": "2026-05-09T14:23:45Z"` 메타데이터 포함

### 2.2.1 병렬 shard backfill 고정 정책

`ml.collect_vlrgg --run-backfill-plan`은 `--backfill-shard-count > 1`일 때 shard별 쓰기 경로를 자동 격리한다. 네 개 세션을 동시에 실행해도 각 세션은 동일한 후보 CSV를 읽기 전용으로만 공유하고, 아래 mutable 경로는 shard별로 분리된다.

| 항목 | shard 0 예시 |
|------|--------------|
| cache | `data/raw/vlrgg_cache_shards/shard_0` |
| output | `data/processed/vlrgg_shards/shard_0` |
| reports | `reports/vlrgg_shards/shard_0` |
| state | `.omx/state/vlrgg_shards/shard_0_state.json` |
| stage output | `.omx/state/vlrgg_shards/shard_0_outputs` |

각 세션은 shard index만 다르게 실행한다.

```bash
.venv/bin/python -m ml.collect_vlrgg \
  --run-backfill-plan \
  --api-base-url http://127.0.0.1:3001 \
  --rate-limit 0.25 \
  --max-requests-per-session 3000 \
  --detail-limit 0 \
  --backfill-candidates-file data/processed/vlrgg_match_candidates.csv \
  --backfill-shard-count 4 \
  --backfill-shard-index 0
```

`--backfill-shard-index`는 `0`, `1`, `2`, `3`으로 나누어 실행한다. 기존처럼 shard 경로를 명시해도 되며, 경로에 `shard_N`이 이미 들어 있으면 자동 격리 로직이 덮어쓰지 않는다.

네 shard 완료 후 병합은 기본 shard output 위치를 자동 인식한다.

```bash
.venv/bin/python -m ml.collect_vlrgg \
  --merge-shard-outputs \
  --backfill-shard-count 4 \
  --no-merge-existing-output \
  --output data/processed \
  --reports reports
```

### 2.3 User-Agent 명시

```python
USER_AGENT = "ValoPredictML/1.0 (Research; +https://github.com/USER/ValoPredicML; nskfn02@gmail.com)"
# 또는
USER_AGENT = "Mozilla/5.0 (compatible; ValoPredicML/1.0; +https://github.com/iee129/ValoPredicML)"
```

**목적**:
- VLR.gg 운영자가 요청 출처 추적 가능
- "봇" vs "사람" 식별 회피 금지 (정직한 자신 소개)
- 거부 시 즉시 중단 (Retry-After 헤더 존중)

### 2.4 세션당 요청 한도

```python
class VLRScraperSession:
    def __init__(self, max_requests=5000):
        self.request_count = 0
        self.max_requests = max_requests
    
    def fetch(self, url):
        if self.request_count >= self.max_requests:
            raise Exception(f"세션 한도({self.max_requests}) 도달. 새 세션 시작 필요.")
        # 요청 실행
        self.request_count += 1
```

---

## 3. 공정한 사용(Fair Use) 정당성

### 3.1 학술/포트폴리오 예외

**법적 근거**: 미국 저작권법 § 107 (Fair Use), EU 저작권 지침 (Recital 22), 한국 저작권법 § 29 (인용)

| 요소 | 본 프로젝트 적용 |
|------|----------------|
| 사용 목적 | 비영리 학술 연구 + 포트폴리오 (상용화 아님) |
| 저작물 특성 | 실시간 통계 (사실성 높음, 창작성 낮음) |
| 사용 범위 | 전체 데이터의 0.1%~1% (경기 결과, 요원 승률) |
| 시장 영향 | VLR.gg 수익성 영향 미미 (유료 구독 없음, 광고 의존) |

**결론**: 교육적 ML 프로젝트로서 공정한 사용 범주에 *접근* 가능하나, 법적 명확성 부족. 따라서 **보수적 원칙으로 회피**.

### 3.2 상업화 시 금지

만약 ValoPredictML을 상업 서비스로 전환한다면:
- VLR.gg 데이터 스크래핑 **즉시 중단**
- Riot API, VCT 공식 데이터 라이선싱 검토
- VLR.gg와 명시적 데이터 라이선싱 협상

---

## 4. ToS 위반 위험 평가

### 4.1 법적 리스크

| 리스크 | 심각도 | 완화 조치 |
|-------|--------|---------|
| CFAA (Computer Fraud and Abuse Act) 위반 | 높음 | robots.txt 준수, 인가받은 접근 확인 |
| DMCA (Digital Millennium Copyright Act) § 1201 | 낮음 | 기술 장벽 우회 금지 (VLR.gg는 없음) |
| 한국 정보통신망법 § 48 | 높음 | robots.txt, 이용약관 명시적 거부 |
| GDPR / 개인정보 보호법 | 낮음 | 프로 선수명·경기 통계는 공개 데이터 |

### 4.2 실제 시행 확률

**현실적 평가**:
- VLR.gg는 **C급 esports 통계 사이트** (Liquipedia 대비)
- 법 집행 가능성: 극히 낮음 (소규모, 무료 서비스, IP 추적 비용 > 이득)
- **하지만**: 법적 리스크가 낮다 ≠ 윤리적으로 문제없다

### 4.3 서버 부하 완화

```python
# 권장 패턴
for match_id in match_list:
    if has_cached_data(match_id):
        data = load_cache(match_id)
    else:
        time.sleep(1.0)  # rate limit: 1 req/sec
        data = fetch_vlrgg(match_id)
        save_cache(match_id, data)
    process(data)
```

**효과**: VLR.gg 서버에 대한 총 요청 수 **95% 감소** (캐시 히트 가정).

---

## 5. 데이터 출처 인용 형식

### 5.1 메타데이터 헤더 (각 캐시 파일)

```json
{
  "source": "VLR.gg",
  "source_url": "https://www.vlr.gg/stats",
  "fetched_at": "2026-05-09T14:23:45Z",
  "fair_use_note": "Non-commercial research; educational portfolio project",
  "legal_disclaimer": "Data sourced from VLR.gg without explicit permission. Fair use claimed under non-commercial education exemption.",
  "data": { ... }
}
```

### 5.2 코드 주석

```python
# VLR.gg scrape (fair use: non-commercial research)
# Source: https://www.vlr.gg/stats
# Note: Direct scraping violates robots.txt; use with caution
# If VLR.gg objects, cease immediately and contact maintainer
df = pd.read_csv("data/raw/vlrgg_cache/agent_stats.json")
```

### 5.3 문서 인용 (sources.md 형식)

```
[S-25] **VLR.gg Main** — https://www.vlr.gg/
    - 발로란트 esports 통계 사이트. 매치, 팀, 선수, 요원, 맵 통계.
    - 주의: robots.txt로 스크래핑 명시 거부. 공정한 사용 원칙 하에서만 접근 권장.
```

---

## 6. 접근 가능한 VLR.gg URL 패턴 (검증됨)

### 6.1 URL 구조

| 엔드포인트 | URL 패턴 | 예시 | 주의사항 |
|-----------|---------|------|--------|
| 메인 | `/` | https://www.vlr.gg/ | 정적 HTML |
| 요원 통계 | `/stats` | https://www.vlr.gg/stats | 쿼리 파라미터: `?event=...&agent=...` |
| 이벤트 인덱스 | `/events` | https://www.vlr.gg/events | 토너먼트 목록 |
| 이벤트 통계 | `/event/stats/{event_id}/{event_slug}` | https://www.vlr.gg/event/stats/2380/vct-2025-emea-stage-1 [S-42] | JSON 응답 미지원 (HTML만 가능) |

### 6.2 검증된 패턴 (2026-05-09)

**GET /event/stats/{event_id}/{slug}**
- 응답: HTML (Client-side React 렌더링)
- 파싱 대상: `<script>window.__data__={...}</script>` 또는 `<table>` DOM
- 테스트: https://www.vlr.gg/event/stats/2380/vct-2025-emea-stage-1
  - ✓ 응답 200 OK
  - ✓ 매치 스코어 표 포함
  - ✓ 요원별 픽률/승률 데이터 포함

**GET /stats**
- 응답: HTML (React SPA, 쿼리 파라미터로 필터링)
- 가능한 파라미터: `?event=...`, `?agent=...`, `?region=...`
- 제한: 페이지 내 JavaScript 로딩 필요 (Selenium/Playwright 권고)

### 6.3 구현 불가능한 패턴

| 패턴 | 이유 |
|------|------|
| JSON API (예: `/api/stats`) | VLR.gg는 공식 REST API 미제공 |
| 직접 GraphQL 쿼리 | CORS 차단, 인증 요구 |
| WebSocket 스트리밍 | 실시간 경기 중계 목적으로 보호됨 |
| CSV 대량 다운로드 | 미지원 |

---

## 7. 현재 프로젝트 정책

### 7.1 왜 direct HTML을 기본 비활성화하는가?

1. **Legal Clarity**: 일부 경로 허용과 별개로 ToS·저작권·서버 부하 리스크가 남음
2. **Data Availability**: Kaggle VLR proxy + 기존 cache + Riot 공식 소스로 리서치 검증 baseline 구성 가능
3. **Maintenance Burden**: VLR.gg HTML 구조 변경 시 파서 재작업
4. **Ethics Priority**: "가능하다" ≠ "해야 한다"

### 7.2 대신 사용 중인 소스

- **[S-16] VCT 2024** — Liquipedia
- **[S-17] VCT 2025** — Liquipedia
- **Kaggle VLR proxy/기존 cache** — `ml.collect_vlrgg --from-cache-only`의 1차 입력
- **self-host vlrggapi v2** — fetch가 필요할 때만 `http://127.0.0.1:3001/v2`
- **direct HTML fallback** — 기본 비활성, `/matches/results`, match detail, `/team/stats/`, `/event/matches/`, `/vct-{year}/standings` allowlist 한정
- **[S-25] VLR.gg Main / [S-26] VLR.gg Agent Stats** — 출처 표기 및 수동 확인 reference
- **[S-42]~[S-51]** — Liquipedia + Riot 공식 (데이터 기반)

### 7.3 확장 수집 실행 계획

현재 실행 가능한 확장 수집은 VLR.gg 상세/팀/이벤트/스탠딩과 로컬 raw 연구 데이터를 리서치 검증용으로 정규화하는 단계까지로 제한한다. `ml.data_pipeline`의 P1-P4 57개 학습 피처 계약과 Streamlit 예측 입력/추론 로직은 이 단계에서 변경하지 않는다.

VLR 확장 수집:

```bash
python -m ml.collect_vlrgg --run-expanded-plan --detail-limit 250 --event-limit 20 --team-limit 50 --standing-years 2024,2025,2026
```

운영 규칙:
- 기존 `.omx/state/vlrgg_collection_state.json`와 `.omx/state/vlrgg_collection_outputs/`를 사용해 stage 단위 resume 가능.
- 429와 `Retry-After`를 존중하고, wait 지시가 없으면 5시간 fallback wait를 기록한다.
- stage별 3회 실패 후 degraded 처리하며, 가능한 산출물은 계속 생성한다.
- `/search/auto`, `/rr/`는 계속 접근하지 않는다.

VLR 확장 산출물:

| output | 주요 컬럼 |
|--------|-----------|
| `data/processed/vlrgg_match_maps.csv` | `match_id`, `game_id`, `map`, `team`, `opponent`, `side_first_half`, `atk_rounds`, `def_rounds`, `ot_rounds`, `score`, `opponent_score`, `map_winner`, `agents`, provenance fields |
| `data/processed/vlrgg_match_players.csv` | `match_id`, `game_id`, `map`, `team`, `opponent`, `player`, `agent`, `rating`, `acs`, `kills`, `deaths`, `assists`, `kast`, `adr`, `hs_pct`, `fb`, `fd`, attack/defense split fields, provenance fields |
| `data/processed/vlrgg_compositions.csv` | `match_id`, `game_id`, `map`, `team`, `agents`, `comp_key`, role count fields, provenance fields |
| `data/processed/vlrgg_standings.csv` | `year`, `region`, `rank`, `team`, `team_id`, `points`, `country`, provenance fields |
| `data/processed/vlrgg_team_map_stats.csv` | `team_id`, `team`, `map`, `games`, `win_rate`, `wins`, `losses`, attack/defense split fields, provenance fields |
| `data/processed/vlrgg_event_matches.csv` | `event_id`, `event`, `match_id`, teams, scores, `date`, provenance fields |

로컬 raw 연구 데이터 정규화:

```bash
python -m ml.collect_local_research --input data/raw/kaggle --output data/processed --reports reports
```

로컬 정규화 산출물:
- `data/processed/research_pick_ban.csv`
- `data/processed/research_economy.csv`
- `data/processed/research_clutch_counter.csv`
- `data/processed/research_player_map_stats.csv`
- `reports/research_source_inventory.json`

### 7.4 미래 개선

만약 VLR.gg와 공식 데이터 라이선싱 계약을 체결한다면:
- 이 문서를 "[라이선스: VLR.gg 공식 동의]" 수준으로 상향 등록
- 스크래핑 코드 추가
- 캐시 갱신 자동화

---

## 8. VLR 검증 baseline (report-backed)

기준 리포트: `reports/vlrgg_ingestion_summary.json` (`generated_at=2026-05-10T08:28:59Z`) + `reports/research_validation.json` (`generated_at=2026-05-10T08:30:03Z`).

| fact_id | metric | value | sample_size | source_url / dataset_id | verdict |
|---------|--------|-------|-------------|--------------------------|---------|
| FACT-VLR-COLLECTION-NETWORK | network_requests | 27 requests | 16,250 rows | https://www.vlr.gg/robots.txt / `reports/vlrgg_ingestion_summary.json` | CONFIRMED |
| FACT-VLR-INGESTION-MATCHES | vlrgg_match_rows | 11,500 rows | 11,500 | `data/processed/vlrgg_matches.csv` | CONFIRMED |
| FACT-VLR-INGESTION-PLAYERS | vlrgg_player_stat_rows | 4,157 rows | 4,157 | `data/processed/vlrgg_player_stats.csv` | CONFIRMED |
| FACT-VLR-DETAIL-MAPS | vlrgg_match_maps_rows | 48 rows | 48 | `data/processed/vlrgg_match_maps.csv` | CONFIRMED |
| FACT-VLR-DETAIL-PLAYERS | vlrgg_match_players_rows | 240 rows | 240 | `data/processed/vlrgg_match_players.csv` | CONFIRMED |
| FACT-VLR-COMPOSITIONS | vlrgg_compositions_rows | 48 rows | 48 | `data/processed/vlrgg_compositions.csv` | CONFIRMED |
| FACT-VLR-STANDINGS | vlrgg_standings_rows | 119 rows | 119 | `data/processed/vlrgg_standings.csv` | CONFIRMED |
| FACT-VLR-TEAM-MAPS | vlrgg_team_map_stats_rows | 60 rows | 60 | `data/processed/vlrgg_team_map_stats.csv` | CONFIRMED |
| FACT-VLR-EVENT-MATCHES | vlrgg_event_matches_rows | 102 rows | 102 | `data/processed/vlrgg_event_matches.csv` | CONFIRMED |
| FACT-LOCAL-PICK-BAN | research_pick_ban_rows | 528 rows | 528 | `data/processed/research_pick_ban.csv` | CONFIRMED |
| FACT-LOCAL-ECONOMY | research_economy_rows | 39,164 rows | 39,164 | `data/processed/research_economy.csv` | CONFIRMED |
| FACT-LOCAL-CLUTCH-COUNTER | research_clutch_counter_rows | 178,605 rows | 178,605 | `data/processed/research_clutch_counter.csv` | CONFIRMED |
| FACT-LOCAL-PLAYER-MAP-STATS | research_player_map_stats_rows | 216,425 rows | 216,425 | `data/processed/research_player_map_stats.csv` | CONFIRMED |
| FACT-MODEL-FEATURE-CONTRACT | active_model_feature_count | 57 features | 66,711 rows | `reports/preprocess_summary.json` / `data/processed/matches_clean.csv` | CONFIRMED |

수집 조건:
- `mode=expanded_collection_plan`, `api_base_url=http://127.0.0.1:3001`, `api_version=v2`
- `direct_html_allowed=true` for allowlisted research paths only
- `robots_checked_at=2026-05-10T03:34:04Z`
- `allowed_paths=/,/stats,/events,/event/,/event/stats/,/event/matches/,/matches/results,/team/stats/,/vct-2024/standings,/vct-2025/standings,/vct-2026/standings`
- `blocked_paths=/search/auto,/rr/`
- `feature_contract_unchanged=true`, `active_model_feature_scope=P1-P4 current contract`

---

## 참고

- **Robots.txt RFC**: https://datatracker.ietf.org/doc/html/draft-koster-robotstxt
- **Fair Use 판례**: *Harper & Row v. Nation Enterprises* (1985), *Google LLC v. Oracle America, Inc.* (2021)
- **한국 저작권법**: 제29조 (인용), 정보통신망법 제48조
- **axsddlr/vlrggapi**: https://github.com/axsddlr/vlrggapi (MIT License, rate limit: 1 req/s, ≤5,000 req/session)
- **프로젝트 sources.md**: 본 문서와 함께 참고 ([S-25] ~ [S-27] VLR.gg 항목, [S-28] 비공식 API)

---

## 메모

- **작성일**: 2026-05-09 (US-001 사후 정책 명확화)
- **상태**: 보수적 혼합 사용 (리서치 검증/프론트 차별화용 산출물, 학습 피처 계약 변경 없음)
- **유지보수**: robots.txt 변경, VLR.gg ToS 업데이트, 법적 선례 변화 시 갱신
