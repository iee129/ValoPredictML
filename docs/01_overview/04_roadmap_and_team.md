# 04. 로드맵, 팀 구성, 용어 사전

## 1. 단계별 로드맵

```
Phase 0: 환경 설정
  ├── Python 가상환경 생성 (.venv)
  ├── requirements.txt 작성 및 pip install
  ├── .env 파일 생성 (DB 접속, API Key)
  ├── PostgreSQL 18 DB 생성 및 테이블 초기화
  └── Next.js 의존성 설치 (npm install)

Phase 1: 데이터 수집
  ├── Kaggle VCT 2021-2023 데이터셋 다운로드 (kagglehub)
  ├── CSV 구조 분석 (컬럼, 행 수, 결측값)
  └── HenrikDev API 키 발급 및 수집 스크립트 작성

Phase 2: 데이터 전처리
  ├── 요원-역할군 매핑 딕셔너리 작성 (AGENT_ROLE_MAP)
  ├── 멀티 CSV 로드 및 컬럼 표준화
  ├── 중복 경기 제거 및 결측값 처리
  ├── 플레이어 단위 → 경기 단위 집계
  ├── 피처 엔지니어링 (역할군 카운트, diff, has_controller, 맵 인코딩)
  └── Stratified Split (70/15/15) 및 저장

Phase 3: 모델 학습
  ├── XGBoost + LightGBM 베이스라인 학습
  ├── Optuna 하이퍼파라미터 최적화
  ├── StratifiedKFold 10겹 교차검증
  ├── Soft Voting 앙상블 (60:40 가중치)
  └── 모델 저장 (joblib) 및 메타데이터 기록

Phase 4: FastAPI 백엔드 구축
  ├── POST /predict, GET /agents, /maps, /history 구현
  ├── Pydantic 입력/출력 스키마 정의
  ├── PostgreSQL 연동 (SQLAlchemy, psycopg2)
  ├── CORS 미들웨어 설정
  └── Swagger UI 동작 확인

Phase 5: Next.js 프론트엔드 구축
  ├── 공통 레이아웃, Navbar 구현
  ├── AgentPicker, TeamSlot 컴포넌트
  ├── WinRateGauge (RadialBar), RoleRadarChart
  ├── FeatureImportanceBar, PredictionHistory
  └── 전체 페이지 (/predict, /, /history, /analytics)

Phase 6: 테스트 및 검증
  ├── 정상 케이스 / 에러 케이스 테스트
  ├── 신규 요원 Unknown 처리 확인
  ├── 예측 응답시간 ≤ 200ms 검증
  └── PostgreSQL 기록 저장 및 조회 확인

Phase 7: Vercel 배포
  ├── vercel.json 작성
  ├── Vercel 대시보드 환경변수 등록
  ├── 프로덕션 빌드 확인 (npm run build)
  └── 배포 URL에서 전체 기능 E2E 검증
```

---

## 2. 단계별 완료 기준

| Phase | 완료 기준 |
|---|---|
| Phase 0 | `uvicorn` 시작 정상, `npm run dev` 정상 |
| Phase 1 | `data/raw/`에 5,000건 이상 매치 데이터 |
| Phase 2 | `data/processed/train.csv`에 15개 피처 저장 |
| Phase 3 | Validation Accuracy ≥ 80%, Train-Val 갭 ≤ 3%p |
| Phase 4 | `curl /predict` 정상 JSON 응답, 응답시간 ≤ 200ms |
| Phase 5 | `localhost:3000/predict`에서 요원 선택→예측→결과 정상 동작 |
| Phase 6 | 모든 테스트 시나리오 통과 |
| Phase 7 | Vercel URL에서 외부 네트워크 E2E 정상 |

---

## 3. 팀 구성 및 역할

| 팀원 | 역할 | 담당 영역 |
|---|---|---|
| 이연주 | 프로젝트 리드 | 전체 구조 설계, Git/GitHub 버전 관리, 문서화 |
| 이예인 | ML 엔지니어 | 모델 학습 전략, Random Forest / XGBoost 비교, 성능 평가 |
| 장정아 | 데이터 엔지니어 | HenrikDev API 테스트, CSV 데이터 정합성 검증 |

---

## 4. 용어 사전

### 4.1 발로란트 게임 용어

| 용어 | 설명 |
|---|---|
| **요원 (Agent)** | 플레이어가 선택하는 캐릭터. 현재 48종 이상 |
| **픽창** | 경기 시작 전 요원 선택 단계. 이 프로젝트의 예측 시점 |
| **역할군 (Role)** | 요원의 플레이 스타일 분류: 타격대/척후병/전략가/감시자 |
| **타격대 (Duelist)** | 공격적 진입, 킬 창출. Jett, Reyna, Neon 등 |
| **척후병 (Initiator)** | 정보 수집, 섬광, 팀 진입 보조. Sova, Breach, Fade 등 |
| **전략가 (Controller)** | 스모크로 시야 차단, 지역 통제. Viper, Omen, Astra 등 |
| **감시자 (Sentinel)** | 수비, 사이드 잠금, 힐. Killjoy, Cypher, Sage 등 |
| **VCT** | Valorant Champions Tour. Riot Games 공식 프로 대회 |
| **ACS** | Average Combat Score. 라운드당 평균 전투 점수 |
| **KAST** | Kill/Assist/Survive/Trade. 라운드 기여 지표 (%) |
| **ADR** | Average Damage per Round. 라운드당 평균 피해량 |
| **라운드** | 하나의 공격/수비 사이클. 경기는 최대 25라운드 |
| **맵 (Map)** | 경기 진행 무대. Ascent, Bind, Haven, Icebox, Breeze 등 |

### 4.2 머신러닝 용어

| 용어 | 설명 |
|---|---|
| **K-Fold** | K겹 교차검증. 데이터를 K개로 나눠 순차적으로 검증 |
| **StratifiedKFold** | 클래스 비율을 유지하는 K-Fold |
| **Early Stopping** | 검증 성능이 일정 라운드 이상 개선되지 않으면 학습 조기 종료 |
| **Soft Voting** | 앙상블에서 각 모델의 확률(predict_proba) 평균으로 최종 예측 |
| **TPE** | Tree-structured Parzen Estimator. Optuna의 베이지안 최적화 방법 |
| **XGBoost** | eXtreme Gradient Boosting. 구조화 데이터 분류 최강 모델 |
| **LightGBM** | Light Gradient Boosting Machine. XGBoost 대비 빠른 학습 |
| **Optuna** | 자동 하이퍼파라미터 최적화 프레임워크 |
| **Label Encoding** | 범주형 변수(맵 이름 등)를 정수로 변환 |
| **JSONB** | PostgreSQL의 이진 JSON 타입. 인덱싱 가능하여 JSON보다 효율적 |
| **ROC-AUC** | Receiver Operating Characteristic - Area Under Curve. 이진 분류 종합 성능 |
| **F1-Score** | Precision과 Recall의 조화 평균. 클래스 불균형 시 유용 |
| **Macro F1** | 클래스별 F1을 동등 가중 평균 (클래스 불균형 고려) |

### 4.3 시스템/인프라 용어

| 용어 | 설명 |
|---|---|
| **FastAPI** | Python 기반 고성능 REST API 프레임워크 |
| **uvicorn** | FastAPI의 ASGI 서버 |
| **Pydantic** | Python 타입 힌트 기반 데이터 검증 라이브러리 |
| **SQLAlchemy** | Python ORM (Object-Relational Mapping) |
| **psycopg2** | Python-PostgreSQL 드라이버 |
| **App Router** | Next.js 13+의 파일 기반 라우팅 시스템 (`src/app/`) |
| **SWR** | stale-while-revalidate. 데이터 페칭 캐시 전략 |
| **Vercel Postgres** | Vercel에서 제공하는 PostgreSQL 18 호스팅 서비스 |
| **CORS** | Cross-Origin Resource Sharing. 다른 도메인 API 호출 허용 정책 |
| **환경변수** | `.env` 파일에 저장되는 시크릿 및 설정값 |

---

## 5. 관련 문서

| 문서 | 내용 |
|---|---|
| [01_project_summary.md](01_project_summary.md) | 프로젝트 소개 및 핵심 아이디어 |
| [02_tech_stack.md](02_tech_stack.md) | 기술 스택 상세 |
| [../08_todo_list/todo_list.md](../08_todo_list/todo_list.md) | 전체 작업 Todo List |
| [../10_valorant/valorant.md](../10_valorant/valorant.md) | 발로란트 게임 심층 설명 |
