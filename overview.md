Python 3.14.4, FastAPI (빠른 ML 모델 서빙), MySQL (예측 로그/전적 저장)

Data Source: HenrikDev API v4 (과거 전적), valclient (실시간 픽창), Kaggle VCT Dataset (선수 대회 전적)


## 1주차 회의록

1. 프로젝트 주제: 발로란트 5v5 승률 예측 시뮬레이터

2. 회의 안건:

- 프로젝트 요구사항 분석
- 데이터 수집 전략 수립
- 팀원별 역할 분담 및 차주 개발 로드맵 수립


4. 팀 회의 주요 내용

요구사항 분석:

- HenrikDev API 호출을 통한 최신 경기 데이터 수집 가능 여부 확인
- 사용자가 요원을 선택할 때마다 역할군을 인식하여 즉각적인 승률을 계산 가능 여부 확인
- 신규 요원 출시나 데이터 누락 등 예상치 못한 입력 상황에서도 모델이 오류 없이 작동할 수 있도록 방어적인 데이터 처리 설계
- 48종 이상의 요원을 개별적으로 학습시키기보다 4대 역할군(타격대, 척후병, 전략가, 감시자)의 조합 숫자를 핵심 피처로 사용

팀원 업무 할당 내역:

| 이연주 | 프로젝트 구조 설계 | Git 및 GitHub를 활용한 소스 코드 버전 관리 체계 구축과 효율적인 협업 및 모듈형 개발을 위한 표준 프로젝트 디렉토리 구조 설계 |
| --- | --- | --- |
| 이예인 | 모델 학습 전략 | Random Forest 및 XGBoost 모델 비교 분석을 통한 최적 알고리즘 선정과 F1-Score 및 K-Fold 교차 검증 기반의 성능 평가 기준을 수립 |
| 장정아 | API 응답 여부 테스트 | HenrikDev API를 활용한 경기 데이터 수집, 저장된 CSV 데이터의 정합성 검증 |

5. 다음 주 업무 계획(To Do)
    1. 전체 파이프라인 구동을 위한 모듈 구조 생성
    2. 모델 학습을 위한 데이터셋 분할(Train/Test Split) 기준 확립
    3. 로컬 클라이언트(valclient)를 통한 실시간 픽 정보 수신 테스트


데이터셋 받을 URL
https://www.kaggle.com/datasets/ryanluong1/valorant-champion-tour-2021-2023-data

데이터셋을 받기 위한 코드는 dataload.py에 있음
반드시 .venv에 있는 가상환경 사용
requirements.txt에 필요한 라이브러리 작성하여 pip install -r requirements.txt 명령어로 설치하고 사용