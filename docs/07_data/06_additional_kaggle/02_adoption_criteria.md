# 02. 데이터셋 채택 기준

마지막 업데이트: 2026-05-04

---

## 1. 채택 기준 (확정)

본 프로젝트의 데이터 소스는 Kaggle 7개 데이터셋으로 확정되어 있다.
신규 소스 추가는 방침 외. 아래 기준은 최초 선정 시 적용한 기준이다.

| 기준 | 설명 |
|------|------|
| `agent` + `map` + 승패 레이블 | 3개 필수 컬럼 보유 |
| K·D·A 개별 분리 | 집계 스탯이 아닌 개별 컬럼 |
| 선수-경기-맵 1행 단위 | 경기 단위 집계가 가능한 구조 |
| 핵심 스탯 결측률 < 30% | ACS·KD 기준 |
| 프로·준프로 경기 | VCT / Challengers / 공식 이벤트 |

---

## 2. 소스별 채택 이유

| 소스 | 채택 이유 |
|------|---------|
| `vct_2021_2023` | 6년치 T1 프로 경기, 1.2GB 대용량 |
| `challengers` | T2 대용량, 공수 분리 스탯, 가중치 최고(1.8) |
| `qualidea` | 249K행, 공수 분리 스탯 유일, 조인 불필요 |
| ~~`piyush 2024`~~ | ~~2024 VCT 전 지역, 최신 메타, 레이블 직접 포함~~ | (제거됨) |
| ~~`piyush 2025`~~ | ~~2025 전체 시즌, 현재 메타(Tejo·Waylay·Drift)~~ | (제거됨) |
| `ediashtarevin` | 2023 Champions 특화, 교차 검증 용도 |
| `kierru` | Pacific 지역 보강, `role_agent` 컬럼 직접 제공 → 결국 제거됨 (리젝션율 80%, 26행만 통과) |

---

## 3. 중복 제거 전략

```python
def make_dedup_key(date, event, map_, team_a, team_b, agents_a, agents_b, score_a, score_b):
    canonical = "|".join([
        str(date), event.lower().strip(), map_.lower(),
        team_a.lower(), team_b.lower(),
        ",".join(sorted(agents_a)), ",".join(sorted(agents_b)),
        str(score_a), str(score_b)
    ])
    return hashlib.sha1(canonical.encode()).hexdigest()[:24]
```

동일 dedup_key 중 소스 가중치가 가장 높은 행만 보존. 동점이면 컬럼 수가 더 많은 행 보존.
