# 03. 데이터 수집 전략 및 로드맵

## 1. 전략 개요

80% 정확도 목표를 달성하기 위한 데이터 수집 전략은 **볼륨 우선 → 다양성 보완 → 피처 고도화** 3단계로 진행한다.

```
Phase A (볼륨 우선):
  Riot VCT S3 + Kaggle 추가 → 50,000+ 샘플 확보

Phase B (다양성 보완):
  HenrikDev API 일반 유저 데이터 → 랭크별 다양성

Phase C (피처 고도화):
  30+ 피처 구현 → 정확도 5~10%p 향상
```

---

## 2. 소스별 수집 전략

### 2.1 Riot VCT S3 Hackathon 데이터 [최우선 ★★★]

```
설명:  Riot Games가 VCT Hackathon을 위해 공개한 공식 경기 데이터
규모:  2021~2024년 VCT 전 대회 (수십만~수백만 행)
형식:  JSON (게임 이벤트 로그 형식)
접근:  AWS S3 공개 버킷 (인증 불필요)
```

**실행 계획:**
```bash
# 1. boto3 설치
pip install boto3

# 2. S3에서 데이터 다운로드 (상세: ../03_riot_official_data/02_s3_download_guide.md)
python scripts/download_riot_s3.py

# 3. JSON 파싱 및 피처 추출
python scripts/parse_riot_data.py

# 4. 기존 Kaggle 데이터와 병합
python ml/data_pipeline.py --merge
```

**예상 소요 시간:** 다운로드 2-4시간, 파싱 1-2시간

### 2.2 Kaggle 추가 데이터셋 [최우선 ★★★]

```
채택 대상:
  - ryanluong1/valorant-champion-tour-2024-data (VCT 2024)
  - 기타 랭크 매치 데이터셋 (카탈로그 참조)
규모:  소스에 따라 수천~수만 경기
```

**실행 계획:**
```python
# kagglehub로 추가 다운로드
import kagglehub

datasets = [
    "ryanluong1/valorant-champion-tour-2024-data",
    # 카탈로그에서 선정된 추가 데이터셋들
]

for ds in datasets:
    path = kagglehub.dataset_download(ds)
    print(f"Downloaded: {path}")
```

### 2.3 HenrikDev API 자동 수집 [우선 ★★]

```
설명:  일반 유저 랭크 매치 데이터 수집 (지역: ap/kr)
목표:  20,000 경기 수집
제약:  Rate Limit (무료 키: 30 req/min)
```

**수집 대상 플레이어 선정 전략:**
```python
# 전략: 각 랭크 티어별 대표 플레이어 리스트 구성
PLAYER_SEED_LIST = {
    "Radiant": [("TenZ", "NA1"), ("aspas", "BR1")],  # 최상위
    "Immortal": [...],     # 고랭크
    "Diamond": [...],      # 미드 하이
    "Platinum": [...],     # 미드
    "Gold": [...],         # 미드 로우
}

# 각 플레이어의 최근 50경기 수집
# → 연결된 플레이어들로 확산 (BFS 방식)
```

**Rate Limit 처리:**
```python
import time
from functools import wraps

def rate_limited(max_per_minute):
    min_interval = 60.0 / max_per_minute
    def decorator(func):
        last_called = [0.0]
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            wait = min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

@rate_limited(25)  # 분당 25회 (안전 마진)
def fetch_match(name, tag, region):
    ...
```

**예상 수집 기간:** 7일 (무료 키 기준, 하루 ~3,000 경기)

### 2.4 VLR.gg 스크래핑 [선택적 ★]

```
설명:  프로 e스포츠 경기 통계 웹 스크래핑
목표:  최근 1년 프로 경기 커버리지 보완
주의:  robots.txt 준수, 요청 간격 최소 2초
```

**적용 범위:**
- Riot VCT S3로 커버 안 되는 지역 대회 데이터
- 팀별 맵 승률 통계 (피처로 활용 가능)

---

## 3. 단계별 로드맵

### Phase A: 볼륨 확보 (우선 실행)

```
목표: 총 50,000+ 경기 확보
기간: 1-2주

Step 1: Riot VCT S3 다운로드
  - scripts/download_riot_s3.py 실행
  - 예상 확보: 50,000+ 경기 (매우 보수적 추정)

Step 2: Kaggle 추가 다운로드
  - VCT 2024 데이터셋 추가
  - 랭크 매치 데이터셋 조사 및 채택
  - 예상 확보: 수천~수만 경기 추가

Step 3: 데이터 병합 및 전처리
  - ml/data_pipeline.py 수정 (멀티소스 지원)
  - 통합 스키마 적용
  - 중복 제거 및 검증
```

### Phase B: 다양성 보완

```
목표: 프로/일반 비율 균형화
기간: 2-3주 (API 수집 포함)

Step 4: HenrikDev 자동 수집 실행
  - scripts/collect_henrik.py 실행 (백그라운드)
  - 일반 유저 20,000 경기 목표
  - 랭크별 비율 맞추기 (다이아+ 50%, 그 이하 50%)

Step 5: 데이터 편향 검사
  - 역할군 분포 비교 (프로 vs 일반)
  - 클래스 균형 재검증
```

### Phase C: 피처 고도화

```
목표: 15개 → 30+ 피처 확장
기간: 1-2주

Step 6: 추가 피처 구현
  - ml/feature_engineering.py 확장
  - 맵별 요원 픽률 통계 피처
  - 개별 요원 원-핫 인코딩 (선택적)

Step 7: 재학습 및 검증
  - Optuna 하이퍼파라미터 재탐색
  - K-Fold 10겹 교차검증
  - 목표: 80%+ 달성 확인
```

---

## 4. 데이터 통합 파이프라인

```python
# ml/data_pipeline.py (확장 버전)
# 멀티소스 데이터를 로드하고 통합 스키마로 변환

DATA_SOURCES = {
    "kaggle_vct_2021_2023": {
        "path": "data/raw/kaggle/vct_2021_2023/",
        "parser": parse_kaggle_vct,
        "weight": 1.0,
    },
    "kaggle_vct_2024": {
        "path": "data/raw/kaggle/vct_2024/",
        "parser": parse_kaggle_vct,   # 동일 포맷
        "weight": 1.0,
    },
    "riot_s3": {
        "path": "data/raw/riot_s3/",
        "parser": parse_riot_json,    # JSON 파서
        "weight": 1.0,
    },
    "henrik_api": {
        "path": "data/raw/henrik/",
        "parser": parse_henrik_csv,
        "weight": 1.0,
    },
}

def load_all_sources() -> pd.DataFrame:
    all_dfs = []
    for source_name, config in DATA_SOURCES.items():
        try:
            df = config["parser"](config["path"])
            df["data_source"] = source_name
            all_dfs.append(df)
            print(f"[INFO] {source_name}: {len(df)} 경기 로드")
        except FileNotFoundError:
            print(f"[WARN] {source_name}: 데이터 없음 (스킵)")
    
    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"[INFO] 전체 합계: {len(combined)} 경기")
    return combined
```

---

## 5. 수집 금지 사항 및 법적 고려

| 소스 | 허용 | 주의사항 |
|------|------|---------|
| Riot VCT S3 | ✅ 공개 버킷 | Riot ToS 준수 필수 |
| Kaggle 데이터셋 | ✅ 다운로드 허용 | 라이선스 확인 (대부분 CC0) |
| HenrikDev API | ✅ 허용 | Rate Limit 준수, 상업적 사용 제한 |
| VLR.gg 스크래핑 | ⚠️ 조건부 | robots.txt 준수, 과도한 요청 금지 |
| Riot 공식 API | ⚠️ 조건부 | Riot Developer Terms 준수 |
| 개인정보 (플레이어 ID) | ⚠️ 주의 | 모델 학습에 직접 사용 금지, 익명화 필요 |

---

## 6. 참고 문서

- [../03_riot_official_data/01_vct_hackathon_overview.md](../03_riot_official_data/01_vct_hackathon_overview.md)
- [../04_api_sources/01_henrikdev_api.md](../04_api_sources/01_henrikdev_api.md)
- [../06_additional_kaggle/01_dataset_catalog.md](../06_additional_kaggle/01_dataset_catalog.md)
