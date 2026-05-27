# vct_winrate 프로젝트 노트

발로란트 대회(VCT) **맵 단위 승률 예측** 파이프라인. 이 문서는 설계 결정과 그동안 나눈 핵심 Q&A를 정리한 거예요.

---

## 1. 무엇을 만드나

**입력**: 맵 1개 + A팀 5명(선수+요원) + B팀 5명(선수+요원)
**출력**: A팀이 이길 확률 (0~1)

**데이터 소스**: `vct_dataset/vct_{2021..2026}/` 의 실제 VCT 경기 데이터. 합성 데이터는 절대 사용 안 함.

---

## 2. 폴더 구조

```
vct_winrate/
├── config.py              경로/하이퍼파라미터 단일 진실 소스
├── notes.md               이 문서
├── src/
│   ├── __init__.py
│   ├── taxonomy.py        요원 → 5 역할, 5 포지션 + 정규화 함수
│   ├── data_load.py       6년치 CSV 로더 + 매치 ID 조인 + 라운드/클러치 lookup
│   ├── labels.py          (매치, 맵) → winner 추출
│   ├── priors.py ★        leak-safe 누적 prior (핵심)
│   ├── features.py        슬롯 기반 + one-hot 조립
│   ├── preprocess.py      end-to-end 진입점
│   ├── splits.py          시간 기반 train/val/test
│   └── (train.py / evaluate.py / predict.py — 아직 미작성)
├── tests/
│   └── __init__.py
└── artifacts/             (gitignore)
    ├── processed/{all,train,val,test}.csv
    └── prior_state.joblib
```

**중요**: `ValoPredictML/` 와 `Local_ValoPredct ML/` 는 손대지 않음. 어떤 파일도 import 안 함. 사용자 명시 요청.

---

## 3. 파이프라인 흐름

```
vct_dataset (6년 CSV)
    ↓ load_overview / load_maps_scores / load_kills_stats / load_match_ids
data_load.py
    ↓ attach_ids, filter (5v5만, Side=both만)
    ↓ rounds_per_map_lookup, clutch_lookup
labels.py → (매치, 맵, A/B 팀, 점수, winner)
    ↓
priors.py ★ → 시간 순 단일 패스, deque(maxlen=20)
    출력: per-(매치, 맵, 선수) 행, 8 stat prior + 동반출전 합
    ↓
features.py → 역할 우선순위 + ACS 내림차순 정렬 → 슬롯 5개
    슬롯마다 prior + 요원 one-hot(27) + 역할 one-hot(5)
    ↓
splits.py → 2021-2024 / 2025 / 2026 시간 분할
    ↓
CSV 저장: train.csv, val.csv, test.csv (427 컬럼)
prior_state.joblib (inference용)
```

---

## 4. 데이터 단위와 분할

- **학습 단위 = (매치, 맵) row**. 한 BO3 매치는 1~5개 맵 row를 만듦.
- 총 26,573행 (5v5 아닌 비정상 그룹 289개 제외)
- **시간 기반 분할**:
  - train: 2021–2024 (24,918행)
  - val: 2025 (1,276행)
  - test: 2026 (379행)

---

## 5. 피처 구성 (총 427 컬럼)

### 학습 X (415 features)

**슬롯 (양 팀 × 5슬롯 × 39 컬럼 = 390):**
| 슬롯 인덱스 | 라벨 | 의미 |
|------------|------|------|
| s1 | duelist1 | 1선 엔트리 (보통 jett/raze/neon/waylay) |
| s2 | duelist2 | 2선 엔트리 (보통 phoenix/reyna/yoru/iso) |
| s3 | initiator | 척후 (sova/breach/...) |
| s4 | controller | 전략 (omen/brimstone/...) |
| s5 | sentinel | 감시 (sage/killjoy/...) |

각 슬롯이 들고 있는 39 컬럼:
- 8 stat prior: `prior_kd`, `prior_kast`, `prior_adr`, `prior_acs`, `prior_apr`, `prior_fkpr`, `prior_fdpr`, `prior_clutch_pr`
- 27 요원 one-hot: `agent_jett`, `agent_raze`, ..., `agent_vyse`
- 5 역할 one-hot: `role_first_duelist`, `role_second_duelist`, `role_initiator`, `role_controller`, `role_sentinel`

**팀 단위 (3):**
- `a_team_co_play_sum` — A팀 5명의 누적 동반출전 페어 합
- `b_team_co_play_sum` — B팀 동일
- `d_team_co_play_sum` — 차이 (A − B)

**맵 (12):**
- `map_is_haven`, `map_is_bind`, ... (12 맵 one-hot)

### 메타 (12, X에 안 들어감)

- `winner` — 레이블 (1 = A 승, 0 = B 승)
- `year` — 분할 기준 (학습 시 drop)
- 10 슬롯별 선수 이름 — CSV 검사용 (학습 시 drop)

학습 코드:
```python
from src.features import META_COLS
df = pd.read_csv("train.csv")
y = df["winner"]
X = df.drop(columns=META_COLS)  # 415 features
```

---

## 6. 설계 결정 (옵션 B + 5 포지션)

### 슬롯 배정 알고리즘
1. 5명을 (포지션 우선순위, prior_acs 내림차순)으로 정렬
2. 정렬된 순서대로 슬롯 1~5에 배치
3. 변칙 컴포지션도 처리됨:
   - 2D-1I-1C-1S (가장 흔함) → [D1, D2, I, C, S]
   - 1D-2I-1C-1S → [D, I1, I2, C, S]
   - "duelist2" 슬롯에 initiator가 들어가도 역할 one-hot 으로 표시

### 왜 슬롯 기반인가
- 사용자 요청 ("선수 순서를 의미 있게")
- 슬롯마다 다른 학습이 가능 (1선 엔트리 vs 척후의 stat 의미가 다름)
- 이전엔 mean/std/min/max 집계(slot-invariant) 시도했지만 사용자가 슬롯 분리 선호

### 왜 5 포지션 / 5 역할
- 듀얼리스트가 1선/2선으로 갈리는 게 발로란트 실제 메타와 맞음
- 사용자 분류:
  - 1선 (first_duelist): jett, raze, neon, waylay
  - 2선 (second_duelist): phoenix, reyna, yoru, iso

---

## 7. 핵심 알고리즘 — leak-safe prior

### 문제
모델이 "현재 매치의 K/D"를 보면 정답을 보고 정답을 맞히는 cheat(=label leakage)가 됨. 그래서 **그 매치 시점에 알 수 있는 정보만** 피처로 써야 함.

### 해결책: 시간 순 단일 패스 + deque

```
1. overview 전체를 Match ID 오름차순(시간 순) 정렬
2. 선수별 deque(maxlen=20) 들고 시작 (빈 deque)
3. (매치, 맵) 그룹 단위 순회:
   (a) 먼저: 현재 deque로 그 그룹 모든 선수의 prior 계산
   (b) 다음: 그 매치의 raw stat을 deque에 append
4. 같은 (매치, 맵) 데이터가 자기 자신의 prior에 절대 안 섞임
```

`deque(maxlen=20)`은 새 항목 append 시 가장 오래된 게 자동으로 빠짐. 그래서 슬라이싱/인덱싱 코드 없이 항상 직전 20개만 유지됨.

### Match ID 가 시간 proxy 인 이유
- 원본 사이트(VLR.gg)가 매치 등록 시 순차적으로 부여
- ID 작을수록 옛날, 클수록 최근

---

## 8. Q&A 모음 (사용자 질문 정리)

### Q. winner 0 vs 1 의미?
**1 = A팀 승, 0 = B팀 승.** A/B는 원본 데이터의 명명 규약 (사용자 입력 시점에선 사용자가 임의로 정함).

### Q. 데이터셋에 결측치(NaN)가 왜 있어?
두 가지 원인:
1. **콜드스타트**: 어떤 선수의 첫 매치 시점엔 평균낼 직전 경기가 0개 → 모든 prior NaN. 우리 파이프라인이 만든 의도된 NaN.
2. **원본 결측**: vct_dataset의 일부 옛날 row (특히 2021)에 stat 컬럼이 비어있음.
- train NaN율 8.7% (대부분 2021의 12.1% 때문)
- val/test는 각각 1.5%/1.3%

### Q. NaN 어떻게 처리하나?
- **XGBoost, LightGBM**: native 처리 (NaN 자체를 분기 신호로 학습). 그대로 둠.
- **RandomForest**: `SimpleImputer(median)` Pipeline으로 감싸서 중앙값 채움.
- **predict.py(콜드스타트)**: 팀 평균 → 글로벌 평균 fallback. 그래도 NaN이면 모델에 native로 넘김.
- 0으로 채우면 안 됨 — "데이터 없음"과 "0점"이 의미가 달라 모델이 오해함.

### Q. train, val, test 가 모두 이전 20경기 평균을 넣은 형식?
**그래요.** 한 row = 한 (매치, 맵). 각 선수 슬롯의 stat은 그 선수의 그 매치 이전 직전 20경기 평균. 윈도우 크기는 `config.PLAYER_RECENT_N`.

### Q. 사용자 입력 피처랑 학습 피처가 같은 거야?
**구조 완전히 동일.** inference 단계:
1. `prior_state.joblib` 로드 (학습 종료 시점의 누적 dict)
2. 사용자가 준 선수 이름으로 lookup → 그 선수의 prior 가져옴
3. 요원/맵 one-hot 채움
4. 동반출전 합 계산
5. 모델에 입력 → P(A 승) 출력

모델은 학습 row인지 미래 매치인지 구분 못 함. feature vector 모양만 같으면 동작.

### Q. year를 feature로 쓰면 안 돼?
**현재 안 씀.** 이유:
- train(2021–2024)에서 본 적 없는 `year=2025/2026` 은 트리 모델이 일반화 못 함
- 미래 inference 시 user는 year 정보 줄 일이 없음
- **메타 변화 신호는 prior stat에 이미 녹아있음** — 너프된 요원의 prior stat이 낮아지면 모델이 자연히 학습

대안 (옵션 B/C 시즌 one-hot)도 가능하지만 일반화 위험이 더 큼.

### Q. 그럼 map도 빼면 되는 거 아니야?
map은 **다른 케이스**. map_is_haven/bind/... 12개 one-hot으로 변환되어 X에 들어감. 모델이 "map_is_bind AND agent_raze → 승률↑" 같은 맵×요원 상호작용을 학습함. `map` 문자열 컬럼은 인코딩 중복이라 뺀 것.

### Q. CSV 전부를 모델이 학습에 보는 거 아니야?
아님. CSV는 저장 형식일 뿐. 학습 코드가 `df.drop(columns=META_COLS)` 으로 명시적으로 메타를 빼고 X를 만듦. 모델은 우리가 넘긴 X와 y만 봄.

### Q. winner를 학습에 넣어야 하는 거 아니야?
**아님 — label leakage**. winner는 모델이 맞춰야 할 **y(정답)** 이지 X(입력)에 포함하면 안 됨. 정답지 보면서 정답 맞히는 거랑 같음.

### Q. 직전 20경기를 어떻게 찾았어? 데이터셋에 날짜 없는데
**Match ID로**. `vct_dataset/all_ids/all_matches_games_ids.csv`에 모든 매치에 정수 Match ID가 있고 ID 작을수록 옛날임. 우리는 overview를 Match ID 오름차순으로 정렬해서 시간 순 순회.

### Q. deque(maxlen=20) 이 뭐야?
파이썬 자료구조. 최대 크기 20을 정해두면 21번째 항목을 추가할 때 가장 오래된 항목이 자동으로 빠짐 (FIFO). 우리는 선수마다 이 deque를 하나씩 들고 새 매치 stat을 append만 하면 자동으로 직전 20개만 유지됨.

### Q. Match ID랑 선수가 어떻게 연결돼?
**JOIN 연산으로**. `overview.csv`와 `all_matches_games_ids.csv`가 공통으로 갖고 있는 5개 컬럼 `(Tournament, Stage, Match Type, Match Name, Map)` 을 키로 `merge()` 함. pandas의 `.merge()` 는 SQL JOIN과 같고, 엑셀의 VLOOKUP과 같은 개념.

### Q. year 컬럼의 의미?
**그 row(매치)가 일어난 연도**. prior 계산 과정과는 무관. prior는 그 선수의 시간 순 직전 20경기 평균이고, 그 20개가 어느 연도에서 왔는지는 어디에도 안 적힘.

### Q. prior가 2024-2025 경계에 걸쳐있으면?
연도 경계는 의미 없음. deque는 선수 이름만으로 키되고 시간 순서대로 push하므로, 한 prior에 2024와 2025 데이터가 자연스럽게 섞일 수 있고 그게 정상.

---

## 9. 다음 단계 (아직 안 한 것)

- `src/train.py` — XGB / LightGBM / RandomForest 학습 + soft-vote 앙상블 (xgboost, lightgbm 설치 필요)
- `src/evaluate.py` — ROC-AUC / Accuracy / F1 + 베이스라인 비교
- `src/predict.py` — 사용자 입력 → P(A 승), 콜드스타트 fallback
- `tests/test_no_leak.py` — priors leak-safe 단위 테스트

---

## 10. 실행법

```bash
cd vct_winrate
python3 -m src.preprocess  # CSV 4개 + prior_state.joblib 생성 (약 2분)
```

산출물: `artifacts/processed/{all,train,val,test}.csv` 와 `artifacts/prior_state.joblib`.

train/evaluate/predict 는 아직 미구현.
