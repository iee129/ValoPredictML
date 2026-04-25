# 01. 데이터 전처리 파이프라인 개요

## 1. 파이프라인 전체 흐름

```
[외부 데이터 소스]
       │
       ├── Kaggle Datasets (주 데이터)
       │       ├── VCT 2021 경기 데이터
       │       ├── VCT 2022 경기 데이터
       │       └── VCT 2023 경기 데이터
       │
       └── HenrikDev API (보조 데이터, 선택)
               └── 최근 프로 경기 데이터
                         │
                         ↓
              [Step 1: 데이터 수집]
                dataload.py → data/raw/
                         │
                         ↓
              [Step 2: 데이터 로드]
                멀티 CSV glob 로드
                컬럼 표준화
                         │
                         ↓
              [Step 3: 데이터 클리닝]
                중복 제거
                결측값 처리
                이상치 제거
                         │
                         ↓
              [Step 4: 경기 단위 집계]
                플레이어 행 → 경기 행
                팀별 요원 리스트 구성
                         │
                         ↓
              [Step 5: 피처 엔지니어링]
                역할군 카운트 (8개)
                diff 피처 (4개)
                has_controller (2개)
                맵 인코딩 (1개)
                → 총 15개 피처
                         │
                         ↓
              [Step 6: 데이터 분할 및 저장]
                Stratified Split (70/15/15)
                → data/processed/train.csv
                → data/processed/val.csv
                → data/processed/test.csv
```

---

## 2. 각 단계 목적

| 단계 | 스크립트 | 목적 | 주요 출력 |
|---|---|---|---|
| 수집 | `dataload.py` | Kaggle 데이터 다운로드 | `data/raw/*.csv` |
| 로드 | `ml/data_pipeline.py:load()` | CSV 병합, 컬럼 통일 | DataFrame |
| 클리닝 | `ml/data_pipeline.py:clean()` | 노이즈 제거 | 클린 DataFrame |
| 집계 | `ml/data_pipeline.py:aggregate()` | 플레이어→경기 | 경기 단위 DataFrame |
| 피처 | `ml/feature_engineering.py` | 15개 피처 생성 | 피처 DataFrame |
| 분할 | `ml/data_pipeline.py:split()` | 학습/검증/테스트 | 3개 CSV |

---

## 3. 데이터 볼륨 목표

| 데이터셋 | 예상 경기 수 | 우선순위 |
|---|---|---|
| VCT 2021 Kaggle | ~800경기 | 높음 |
| VCT 2022 Kaggle | ~1,000경기 | 높음 |
| VCT 2023 Kaggle | ~1,200경기 | 높음 |
| HenrikDev API | 300~500경기 | 중간 |
| **합계** | **~3,500경기** | — |

- 최소 2,000경기 이상 확보 목표
- 경기별 2행 (팀 A 승리/팀 B 승리 레이블)으로 생성 시 4,000~7,000행 학습 데이터

---

## 4. 품질 기준

| 항목 | 기준 | 실패 시 처리 |
|---|---|---|
| 팀당 요원 수 | 정확히 5명 | 해당 경기 제외 |
| 결측 요원 이름 | 0개 허용 | 행 제거 |
| 라벨 분포 | 0.45~0.55 (승/패 균형) | 경고 로그 출력 |
| 맵 목록 | 알려진 9개 맵 중 하나 | "Other"로 대체 후 제외 |
| 중복 경기 | 0개 | 자동 제거 |

---

## 5. 스크립트 실행 가이드

```bash
# 1. Kaggle 인증 설정 (최초 1회)
pip install kagglehub
# ~/.kaggle/kaggle.json 파일 생성 필요

# 2. 데이터 다운로드
python dataload.py

# 3. 전처리 파이프라인 실행
python ml/data_pipeline.py

# 4. 결과 확인
ls data/processed/
# → train.csv, val.csv, test.csv
```

---

## 6. 관련 문서

| 문서 | 내용 |
|---|---|
| [02_data_collection.md](02_data_collection.md) | Kaggle, HenrikDev 수집 방법 |
| [03_data_loading.md](03_data_loading.md) | 멀티 CSV 로드 및 컬럼 매핑 |
| [04_data_cleaning.md](04_data_cleaning.md) | 중복/결측값 처리 |
| [05_aggregation.md](05_aggregation.md) | 플레이어→경기 집계 |
| [06_feature_engineering.md](06_feature_engineering.md) | 15개 피처 생성 상세 |
| [07_split_and_validation.md](07_split_and_validation.md) | 데이터 분할 및 검증 |
