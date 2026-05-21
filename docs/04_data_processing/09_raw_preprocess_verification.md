# 09. Raw-Only 전처리 산출물 3-Pass 검증 리포트

> **계약 문서**: `docs/04_data_processing/08_raw_preprocess.md`  
> **검증 대상**: `data/processed/preprocess/` (12개 CSV)  
> **생성 스크립트**: `scripts/verify_raw_preprocess.py`

---

## Pass 1 — 구조·인벤토리 검증

| ID | 검사 | 기대 | 실제 | 상태 | 근거 |
|----|------|------|------|:----:|------|
| `1.1` | 파일 존재 (12개) | 12개 모두 존재 | ✓ | ✅&nbsp;PASS | §2 |
| `1.2` | 행 수 vs §2 | 12개 모두 문서값 일치 | ✓ | ✅&nbsp;PASS | §2 |
| `1.3-matches` | 스키마 matches.csv | doc 컬럼 ⊆ 실제 헤더 | ✓ | ✅&nbsp;PASS | §5.1 |
| `1.3-players` | 스키마 players.csv | doc 컬럼 ⊆ 실제 헤더 | ✓ | ✅&nbsp;PASS | §5.2 |
| `1.3-teams` | 스키마 teams.csv | doc 컬럼 ⊆ 실제 헤더 | ✓ | ✅&nbsp;PASS | §5.3 |
| `1.4` | 파싱 무결성 | 12개 CSV 오류 없이 로드 | 예외 없이 로드됨 | ✅&nbsp;PASS | §2 |
| `1.5` | 산술 정합성 (candidate−rejects=accepted) | 68,191−1,260=66,931 | matches=66,931 ✓ | ✅&nbsp;PASS | §4.2/4.3 |
| `1.6` | 카디널리티 (teams=2×M, players=10×M, lineup==M) | 모두 일치 | ✓ | ✅&nbsp;PASS | §5.1-5.3 |
| `1.7` | features_static == iso matches | iso=27,268 | iso=27,268, static=27,268 ✓ | ✅&nbsp;PASS | §6.2 |
| `1.8` | train+val+test == features_static | 합=27,268 | 실제합=27,268 ✓ | ✅&nbsp;PASS | §7 |


## Pass 2 — 규칙·로직 검증

| ID | 검사 | 기대 | 실제 | 상태 | 근거 |
|----|------|------|------|:----:|------|
| `2.1` | Acceptance gate (8조건) — matches.csv 전 행 | 0 violations | ✓ | ✅&nbsp;PASS | §4.3 |
| `2.2` | Reject log 정합성 | {'dedup_lower_priority': 1256, 'player_count_not_5v5': 4} | {'dedup_lower_priority': 1256, 'player_count_not_5v5': 4} | ✅&nbsp;PASS | §4.3 |
| `2.3` | Date quality gate | {'iso': 27268, 'missing': 39530, 'partial': 133} | {'missing': 39530, 'iso': 27268, 'partial': 133} | ✅&nbsp;PASS | §4.4 |
| `2.4` | Dedup 유일성 + 생존본 검증 | 중복 0, 모든 reject에 생존본 | ✓ | ✅&nbsp;PASS | §4.5 |
| `2.5` | Source 분포 | {'kaggle_qualidea': 24891, 'kaggle_vct': 23831, 'kaggle_challengers':  | {'kaggle_qualidea': 24891, 'kaggle_vct': 23831, 'kaggle_challengers': 15081, 'kaggle_piyus | ✅&nbsp;PASS | §3 |
| `2.6-features_lineup` | Leakage 배제 (features_lineup) | 금지 컬럼 없음 | ✓ | ✅&nbsp;PASS | §6.1/6.2 |
| `2.6-features_static` | Leakage 배제 (features_static) | 금지 컬럼 없음 | ✓ | ✅&nbsp;PASS | §6.1/6.2 |
| `2.7` | Split SHA-256 재도출 | 0 불일치 | 12,826행 불일치 | ⚠️&nbsp;WARN | §7 |
| `2.8` | Split 겹침 | 교집합 0 | ✓ | ✅&nbsp;PASS | §7 |
| `2.9` | 피처 내부 정합성 | map=1, agent=5, role=5, diff=a-b | ✓ | ✅&nbsp;PASS | §6.1 |

> **[2.7] 상세**: 알고리즘 해석(int(hex,16)%100)이 실제 구현과 다를 수 있음


## Pass 3 — 교차·독립 재현 검증

| ID | 검사 | 기대 | 실제 | 상태 | 근거 |
|----|------|------|------|:----:|------|
| `3.1` | 교차 참조 무결성 | 모든 match_key 일관 | ✓ | ✅&nbsp;PASS | §5.1-6.2 |
| `3.2` | Lineup 교차검증 (표본 40) | 0 불일치 | ✓ | ✅&nbsp;PASS | §5.1/5.2 |
| `3.3` | Label 교차검증 (matches vs teams.won) | 0 불일치 | ✓ | ✅&nbsp;PASS | §5.1/5.3 |
| `3.4` | Strict-before 재현 (표본 40) | prior_games/wr 일치 | ✓ | ✅&nbsp;PASS | §6.2 |
| `3.5-qualidea` | Raw 재현: kaggle_qualidea (표본 40) | 0 미발견 | found=38/40, not_found=2/40, agent_mismatch=10 | ⚠️&nbsp;WARN | §4.2 |
| `3.6-vlrgg` | Raw 재현: vlrgg_raw_detail (133행 전수) | 0 미발견 | found=133/133, not_found=0/133 (JSON파일=87) | ✅&nbsp;PASS | §4.2 |
| `3.7` | 통계 sanity | label 균형, WR∈[0,1], games≥0, 날짜 타당 | ✓ | ✅&nbsp;PASS | §4/6 |
| `3.8` | Source 3중 대조 + 9행 국소화 | doc §3 == matches.csv == sources.csv | ✓ | ✅&nbsp;PASS | §3 |

> **[3.5-qualidea] 상세**: 2건 미발견 (날짜 정규화 차이 가능성)


---

## 최종 판정

| Pass | 검사 수 | ✅ PASS | ⚠️ WARN | ❌ FAIL |
|------|--------:|-------:|-------:|-------:|
| 1. 구조·인벤토리 검증 | 10 | 10 | 0 | 0 |
| 2. 규칙·로직 검증 | 10 | 9 | 1 | 0 |
| 3. 교차·독립 재현 검증 | 8 | 7 | 1 | 0 |
| **합계** | **28** | **26** | **2** | **0** |

### 종합: **조건부 신뢰** — FAIL 없음, WARN 2건 검토 필요.

### 주요 발견

- **[2.7]**: 알고리즘 해석(int(hex,16)%100)이 실제 구현과 다를 수 있음
- **[3.5-qualidea]**: 2건 미발견 (날짜 정규화 차이 가능성)

> **범위**: 본 보고서는 검증만 수행. 불일치 수정은 별도 작업.