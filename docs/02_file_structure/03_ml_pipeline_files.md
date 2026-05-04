# 03. ML 파이프라인 파일 상세 (`ml/`)

마지막 업데이트: 2026-05-04

## 1. 폴더 전체 구조

```
ml/
├── agent_roles.py          # 요원→역할군 매핑, 맵 목록, 정규화 함수
├── data_pipeline.py        # 전처리 파이프라인 진입점
├── parsers/
│   ├── __init__.py
│   ├── ryanluong.py        # vct_2021_2023 + challengers 파서
│   ├── qualidea.py         # qualidea1217 파서
│   ├── piyush.py           # piyush86kumar 2024/2025 파서
│   ├── ediashtarevin.py    # ediashtarevin 파서
│   └── kierru.py           # kierru 파서
├── train_model.py          # RF + XGBoost + LightGBM 학습
└── evaluate_model.py       # 성능 평가 (Accuracy, ROC-AUC, F1)
```

> `ml/` 폴더는 현재 미존재. Phase 2 진입 시 생성.

---

## 2. 실행 순서

```bash
# Step 1: 데이터 다운로드 (구현 완료)
python dataload.py

# Step 2: 전처리 파이프라인 (구현 예정)
python -m ml.data_pipeline \
  --input data/raw/kaggle \
  --output data/processed \
  --reports reports

# Dry-run (원본 무수정)
python -m ml.data_pipeline \
  --input data/raw/kaggle \
  --output /tmp/valo_out \
  --reports /tmp/valo_reports

# A/B swap 증강 비활성화
python -m ml.data_pipeline ... --no-augment-train

# Step 3: 모델 학습 (구현 예정)
python -m ml.train_model

# Step 4: 성능 평가 (구현 예정)
python -m ml.evaluate_model
```

---

## 3. 파일별 역할 및 구조

### 3.1 `ml/agent_roles.py` — 공통 참조 데이터

**책임:** 파서·정규화·품질 게이트 전 단계에서 공통으로 참조하는 매핑 테이블.

```python
AGENT_ROLE_MAP: dict[str, str] = {
    # Duelist (8종)
    "Jett": "Duelist", "Reyna": "Duelist", "Phoenix": "Duelist",
    "Raze": "Duelist", "Yoru": "Duelist", "Neon": "Duelist",
    "ISO": "Duelist", "Waylay": "Duelist",
    # Initiator (7종)
    "Sova": "Initiator", "Breach": "Initiator", "Skye": "Initiator",
    "KAY/O": "Initiator", "Fade": "Initiator", "Gekko": "Initiator",
    "Tejo": "Initiator",
    # Controller (6종)
    "Viper": "Controller", "Omen": "Controller", "Brimstone": "Controller",
    "Astra": "Controller", "Harbor": "Controller", "Clove": "Controller",
    # Sentinel (6종)
    "Killjoy": "Sentinel", "Cypher": "Sentinel", "Sage": "Sentinel",
    "Chamber": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel",
}

MAP_ORDER: list[str] = [
    "Ascent", "Bind", "Haven", "Split", "Icebox", "Breeze",
    "Fracture", "Pearl", "Lotus", "Sunset", "Abyss", "Drift",
]
MAP_TO_INDEX: dict[str, int] = {m: i for i, m in enumerate(MAP_ORDER)}

def normalize_agent(raw: str) -> str | None: ...
def normalize_map(raw: str) -> str | None: ...
def normalize_team(raw: str) -> str: ...
```

---

### 3.2 `ml/data_pipeline.py` — 전처리 파이프라인 진입점

**입력:** `data/raw/kaggle/**`
**출력:** `data/processed/matches_clean.csv`, `train.csv`, `val.csv`, `test.csv`, `features_base.csv`

파이프라인 단계:
1. **파싱** — 소스별 파서(`ml/parsers/`) 호출 → 공통 스키마 행 리스트 병합
2. **정규화** — 요원명·맵명·컬럼명 통일
3. **품질 게이트** — 팀당 요원 5개, 알려진 요원/맵, 유효 레이블 등 검사
4. **dedup** — `dedup_key` 기준 중복 제거 (소스 가중치 높은 행 우선)
5. **분할** — 70/15/15 train/val/test (match_key 단위 GroupShuffleSplit)
6. **피처 사전 집계** — train.csv 기준으로 atk_side_advantage, agent_map_stats, agent_experience 집계
7. **A/B Swap 증강** — train 한정, `--no-augment-train`으로 비활성화 가능
8. **features_base.csv 저장**

---

### 3.3 `ml/parsers/ryanluong.py` — ryanluong 파서

**대상 소스:** `vct_2021_2023`, `ryanluong1__valorant-challengers-league-data`

- `overview.csv` (선수 스탯) + `maps_scores.csv` (팀 점수) 조인 필수
- 조인 키: `Match Name + Map`
- `maps_scores.csv`의 `Attacker Score / Defender Score` → `atk_side_advantage` 집계 소스
- 연도별 하위 폴더(`vct_2021/`~`vct_2026/`) 재귀 탐색

---

### 3.4 `ml/parsers/qualidea.py` — qualidea 파서

**대상 소스:** `qualidea1217__valorant-pro-matches-since-april-2021`

- 단일 파일 `data-since-april-2021.csv` (249,711행) — 조인 불필요
- 공수 분리 컬럼(`acs-t`, `acs-ct`, `kd-t`, `kd-ct`) 포함

---

### 3.5 `ml/parsers/piyush.py` — piyush 파서

**대상 소스:** `piyush86kumar__*2024*`, `piyush86kumar__*2025*`

- 이벤트 폴더 내 `detailed_matches_player_stats.csv` — 조인 불필요
- `*_csvs` 하위 폴더 재귀 탐색
- `map_winner` 컬럼에서 직접 레이블 추출
- KAST 일부 이벤트 결측

---

### 3.6 `ml/parsers/ediashtarevin.py` — ediashtarevin 파서

**대상 소스:** `ediashtarevin__vct-champions-2023-stats`

- 단일 파일 `player_stats.csv` — 조인 불필요
- `win_lose` 컬럼에서 레이블 추출 (`'win'`→1, `'lose'`→0)

---

### 3.7 `ml/parsers/kierru.py` — kierru 파서

**대상 소스:** `kierru__vctpacific-2023`

- `csv/stats.csv` — 조인 불필요
- `role_agent` 컬럼 직접 포함 → AGENT_ROLE_MAP 조회 없이 역할군 파싱 가능

---

### 3.8 `ml/train_model.py` — 모델 학습

**입력:** `data/processed/train.csv`, `val.csv`
**출력:** `models/rf_model.joblib`, `models/xgboost_model.joblib`, `models/lgbm_model.joblib`, `models/model_metadata.json`

```python
import joblib
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import lightgbm as lgb
from sklearn.model_selection import GroupKFold

FEATURE_COLS = [
    # 역할군 카운트 (12)
    "a_duelist", "a_initiator", "a_controller", "a_sentinel",
    "b_duelist", "b_initiator", "b_controller", "b_sentinel",
    "diff_duelist", "diff_initiator", "diff_controller", "diff_sentinel",
    # 역할군 파생 (4)
    "has_controller_a", "has_controller_b",
    "is_double_duelist_a", "is_double_duelist_b",
    # 선수 스탯 (12)
    "a_avg_acs", "b_avg_acs", "a_avg_kd", "b_avg_kd",
    "a_avg_kast", "b_avg_kast", "a_avg_adr", "b_avg_adr",
    "a_max_clutch", "b_max_clutch", "a_avg_hs", "b_avg_hs",
    # 시너지 (6)
    "a_fk_fd_ratio", "b_fk_fd_ratio",
    "a_avg_assists", "b_avg_assists",
    "a_kast_std", "b_kast_std",
    # 요원 조합 (6)
    "a_avg_agent_map_wr", "b_avg_agent_map_wr",
    "a_avg_agent_pick_rate", "b_avg_agent_pick_rate",
    "a_avg_agent_exp", "b_avg_agent_exp",
    # 맵 (3)
    "map_encoded", "atk_side_advantage", "is_attacker_a",
]

# K-Fold (K=5), match_key 단위 GroupKFold
# 앙상블: RF + XGBoost + LightGBM 예측 확률 평균
```

---

### 3.9 `ml/evaluate_model.py` — 모델 평가

**입력:** `models/*.joblib`, `data/processed/test.csv`
**출력:** 터미널 리포트 + `reports/training_report.json`

**출력 내용:**
- Accuracy, F1-Score, ROC-AUC
- Confusion Matrix
- Train-Val 갭 (과적합 여부)
- 피처 중요도 상위 10개
- SHAP 분석 (구현 시)

---

## 4. 파일 간 의존성 그래프

```
dataload.py
    ↓ (data/raw/kaggle/ 저장)
ml/data_pipeline.py
    ├──→ ml/agent_roles.py       (공통 참조)
    ├──→ ml/parsers/*.py         (소스별 파싱)
    └──→ data/processed/ 저장
              ↓
         ml/train_model.py
         └──→ models/ 저장
                   ↓
              ml/evaluate_model.py
              └──→ reports/ 저장
```

---

## 5. 출력 파일

| 경로 | 내용 |
|------|------|
| `data/processed/matches_clean.csv` | 품질 게이트·dedup 통과한 맵 행 전체 |
| `data/processed/features_base.csv` | 피처 테이블 (43개 피처 + 레이블) |
| `data/processed/train.csv` | 학습셋 (A/B swap 증강 포함) |
| `data/processed/val.csv` | 검증셋 |
| `data/processed/test.csv` | 테스트셋 (최종 평가 전용) |
| `reports/preprocess_summary.json` | 소스별 행수·제거율·최종 분포 등 실행 통계 |
| `reports/rejected_matches.csv` | 품질 게이트 탈락 행 및 탈락 사유 |

---

## 6. 관련 문서

| 문서 | 내용 |
|------|------|
| [../docs/preprocessing.md](../preprocessing.md) | 전처리 파이프라인 정전 설계 |
| [../03_architecture/06_ml_pipeline_architecture.md](../03_architecture/06_ml_pipeline_architecture.md) | ML 파이프라인 아키텍처 다이어그램 |
