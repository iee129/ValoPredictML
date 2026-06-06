# 01. 테스트 전략 (시연 안정성 중심)

배포가 없으므로 목표는 **시연 중 안 깨지는 것**이다. 무거운 자동화보다 ① 계약 일치(타입), ② 직렬화 정확성, ③ 시연 경로 수동 점검에 집중한다.

---

## 1. 백엔드 (pytest)

`requirements.txt`에 `pytest` 추가. 모델 추론 없이 **직렬화·검증 로직**을 작은 고정값으로 테스트한다(무거운 데이터 불필요).

### 1.1 직렬화 단위 테스트
`serialize_prediction`이 `PredictionResult`를 정확히 매핑하는지(가짜 dataclass 입력):
```python
def test_serialize_winner_and_roles():
    r = FakeResult(team_a_win_probability=0.62, predicted_label=1,
                   role_counts={"A팀": {"타격대": 2}, "B팀": {"타격대": 1}}, ...)
    out = serialize_prediction(r)
    assert out["predicted_winner"] == "A"
    assert out["team_a"]["win_probability"] == 0.62
    assert out["role_counts"]["team_a"]["duelist"] == 2     # 한국어→canonical 키
```

### 1.2 인사이트 단위 테스트
- `balance_warnings`: controller=0 → `no_controller` high 포함
- `_sentence_for`: `a_prior_games_mean - b_=6` → "팀 A 우위 … 6경기" 생성
- `build_insights`: 소형 가짜 `matches.csv`(5행) → `agent_map_fit.json`/`meta_comps.json` 키 존재, 합계 일치
- `comp-match`: 동일 구성 → 100%, 한 자리 교체 → 80%

### 1.3 엔드포인트 스모크 (`TestClient`)
산출물이 있을 때만 도는 통합 스모크(없으면 skip):
```python
@pytest.mark.skipif(not Path("models/advanced/ensemble.joblib").exists(), reason="산출물 없음")
def test_predict_endpoint_smoke(client):
    body = {...}  # 유효 5v5
    r = client.post("/predict", json=body)
    assert r.status_code == 200
    assert set(r.json()) >= {"predicted_winner","team_a","explanations","balance"}
```
검증 실패 케이스: 선수 중복 → 422, 모르는 맵 → 422.

---

## 2. 프론트엔드

### 2.1 타입 체크 (1순위 — 계약 일치)
```bash
npx tsc --noEmit
```
`types/api.ts`가 백엔드 응답과 어긋나면 컴파일 실패 → 08_web식 계약 사고를 차단. CI/커밋 전 필수.

### 2.2 빌드·린트
```bash
npm run build && npm run lint
```

### 2.3 스모크 (선택, Playwright)
백엔드 띄운 상태에서 핵심 경로 1개만:
- `/predict` 진입 → 옵션 로드 → 5v5 입력 → 예측 → 결과 카드 노출 확인

> 평가 데모엔 E2E 풀스위트보다 **수동 체크리스트(§3)**가 비용 대비 효과적.

---

## 3. 시연 전 수동 체크리스트

```
[ ] /health 200, n_features":179
[ ] /model: AUC·검증 신뢰 가능 표시
[ ] /replay: 경기 선택 → 적중/불일치 표시 (콜드스타트 없음)
[ ] /predict: 맵 선택 시 ✓/△/✗ 배지 갱신
[ ] /predict: 5v5 입력 → 매칭률 %, 구성 결함 표시
[ ] /predict: 예측 → 승자/게이지/신뢰도/레이더/근거 카드 모두 노출
[ ] 콜드스타트: 데모 직전 /predict 1회 워밍
[ ] 1280×800 전체화면에서 스크롤 없이 한 화면
[ ] 잘못된 입력(선수 중복) → 친절한 한국어 에러
```

---

## 4. 알려진 리스크 → 대비

| 리스크 | 대비 |
|--------|------|
| `/predict` 첫 호출 콜드스타트 | startup 워밍업 / 데모 직전 1회 호출 |
| 산출물 미생성 | `/health`로 사전 점검, 런북 §1 선행 |
| 빔프로젝터 가독성 | 전체화면 + 큰 숫자(clamp) |
| 네트워크/포트 | 전부 localhost, CORS `:3000` 등록 확인 |

---

## 5. 관련 문서

- 시연 런북 → [../04_integration/02_demo_runbook.md](../04_integration/02_demo_runbook.md)
- 실행·CORS → [../02_backend_fastapi/05_run_and_cors.md](../02_backend_fastapi/05_run_and_cors.md)
