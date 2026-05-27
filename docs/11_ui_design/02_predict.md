# 02. 예측 화면 설계

> Streamlit 기반 — FastAPI/Next.js 사용 안 함
> 마지막 업데이트: 2026-05-27

## 현재 구현

진입점: `app/main.py`

런타임 로직: `app/predict.py`

모델: `models/advanced/ensemble.joblib`

데이터 계약: Kaggle-only advanced 125피처, `data/processed/adv_kaggle_only`

## 탭 구성

| 탭 | 역할 |
|---|---|
| `커스텀 5v5` | 맵, cutoff year, Team A/B 선수 5명과 요원 5명을 선택해 승률 예측 |
| `경기 다시보기` | `adv_kaggle_only/test.csv` 실제 holdout row를 선택해 예측과 실제 label 비교 |
| `모델 근거` | feature count, test metric, validation verdict, global feature importance 표시 |

## 입력 계약

| 입력 | 검증 |
|---|---|
| Map | `ml.valorant.MAP_ORDER`와 processed match data에서 생성 |
| Cutoff year | `data/processed/matches.csv`의 year에서 생성, 마지막 다음 해 포함 |
| Team A/B 선수 | `data/processed/players.csv`의 Kaggle source 선수명에서 생성, 10명 중복 불가 |
| Team A/B 요원 | `ml.agent_roles.AGENT_ROLE_MAP`에서 생성, 같은 팀 내 중복 불가 |

사용자는 모델 피처를 직접 입력하지 않는다. `app/predict.py`가 baseline previous-year feature builder를 재사용해 125피처 `DataFrame`을 만든다.

## 출력

| 출력 | 출처 |
|---|---|
| Team A/B 승률 | `ensemble.predict_proba()` |
| Confidence | `abs(p - 0.5) * 2` |
| Top features | RF/XGB/LGBM feature importance와 현재 row 값을 결합 |
| Role counts | 생성된 125피처 중 역할 count |
| Replay actual label | `adv_kaggle_only/test.csv` |
| Model metrics/verdict | `reports/adv_kaggle_only/{metrics,validation}.json` |

## 실행

```bash
python -m streamlit run app/main.py
```
