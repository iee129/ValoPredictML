# 01. 채택 데이터셋 카탈로그

마지막 업데이트: 2026-05-04

---

## 1. 채택 7개 데이터셋 전체 명세

본 프로젝트는 아래 7개 Kaggle 데이터셋만 사용한다. 외부 API·스크래핑은 방침상 미사용.

| # | 등급 | Kaggle ID | 용량 | 파서 | 소스 가중치 | 행 수 (추정) |
|---|------|-----------|------|------|------------|------------|
| 1 | 핵심 | `ryanluong1/valorant-champion-tour-2021-2023-data` | 1.2GB | ryanluong | 1.0 | ~600K |
| 2 | 핵심 | `ryanluong1/valorant-challengers-league-data` | 1.0GB | ryanluong | **1.8** | ~412K |
| 3 | 핵심 | `qualidea1217/valorant-pro-matches-since-april-2021` | ~35MB | qualidea | 1.0 | ~250K |
| 4 | piyush | `piyush86kumar/valorant-champions-tour-2024-all-events` | ~15MB | piyush | **1.5** | ~30K |
| 5 | piyush | `piyush86kumar/valorant-vct-2025-all-events` | — | piyush | **1.5** | ~15K |
| 6 | 보조 | `ediashtarevin/vct-champions-2023-stats` | — | ediashtarevin | 0.9 | ~6K |
| 7 | 보조 | `kierru/vctpacific-2023` | — | kierru | 0.9 | ~5K |

**총 용량**: 2.3GB / 선수 행 합계 ~1,318K / 중복 제거 후 맵 행 **80~100K** 예상

---

## 2. 소스 가중치 정책

| 가중치 | 소스 | 이유 |
|--------|------|------|
| **1.8** | ryanluong challengers | 컬럼 수 최다, 공수 분리 스탯 보유 |
| **1.5** | piyush 2024/2025 | 최신 메타(2024~2025) 반영 |
| 1.0 | vct_2021_2023, qualidea | 대용량 다년도 소스 |
| 0.9 | ediashtarevin, kierru | 특정 대회·지역 보강, 소규모 |

동일 dedup_key 중 가중치 높은 소스의 행을 보존. 동점이면 컬럼 수가 더 많은 행 보존.

---

## 3. 관련성 종합 평가

| 데이터셋 | 관련성 | 이유 |
|----------|--------|------|
| `vct_2021_2023` | 최고 | 6년치 T1 프로 경기 1.2GB, 핵심 학습 소스 |
| `ryanluong1__challengers` | 최고 | T2 대용량 1.0GB, 공수 점수 분리, 가중치 최고 |
| `qualidea1217__*` | 최고 | 249K행, 공수 분리 스탯 유일 소스, 조인 불필요 |
| `piyush86kumar__2024` | 높음 | 2024 VCT 전 지역, 최신 메타, 레이블 포함 |
| `piyush86kumar__2025` | 높음 | 2025 전체 시즌 통합, 현재 메타 |
| `ediashtarevin__*` | 보통 | 2023 Champions 특화, 교차 검증용 |
| `kierru__vctpacific-2023` | 보통 | Pacific 지역 보강, role_agent 직접 제공 |

---

## 4. 다운로드

```bash
python dataload.py
```

`~/.kaggle/kaggle.json` 필요. 다운로드 완료 후 `data/raw/kaggle/` (2.3GB, git 제외).
