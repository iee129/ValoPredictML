# 04. 자연어 승부 근거 — 차별점 C

예측 결과를 "팀 A 우세: 직전 1년 경험이 평균 대비 N경기 많음" 같은 한국어 문장으로 풀이한다. 모델의 `top_features` + `feature_values`에서 파생하며, `/predict` 응답에 `explanations[]`를 추가한다.

---

## 1. 원천 데이터 (이미 모델이 줌)

`PredictionResult`(→ [../02_backend_fastapi/02_model_serving.md](../02_backend_fastapi/02_model_serving.md))에서:

| 출처 | 내용 |
|------|------|
| `predicted_label` / `confidence` | 어느 팀 우세인지, 확신도 |
| `top_features[]` | `{feature, value, importance, contribution}` 상위 8 |
| `feature_values` | 125피처 전체 값 (양 팀 비교용) |

핵심: 피처는 **양 팀 대칭**으로 존재한다(`a_*` / `b_*`). 예 — `a_prior_games_mean`, `b_prior_games_mean`이 둘 다 125피처에 포함됨(확인됨: advanced 계약의 `PLAYER_PRIOR_BASES`에 `prior_games` 포함). 따라서 "A가 B보다 N만큼 많다"를 직접 계산할 수 있다.

---

## 2. 문장 생성 — 피처 패밀리별 템플릿

`top_features`를 위에서부터 보며, `feature` 접두/패턴으로 템플릿을 고르고 `feature_values`의 `a_*`/`b_*` 차이를 채운다.

| 피처 패턴 | 비교값 | 한국어 템플릿 |
|-----------|--------|----------------|
| `*_prior_games_mean` | `a-b` (경기 수) | "직전 연도 경험이 {우세팀} 기준 평균 {Δ:.0f}경기 {많음/적음}" |
| `*_prior_kd_mean` | `a-b` | "선수 평균 K/D가 {우세팀}이 {Δ:.2f} {높음/낮음}" |
| `*_prior_adr_mean` | `a-b` | "라운드당 피해량(ADR)이 {우세팀}이 우위" |
| `*_prior_kast_mean` | `a-b` | "KAST(라운드 기여율)가 {우세팀}이 높음" |
| `*_synergy_mean` | `a-b` | "팀 동반 출전 경험(호흡)이 {우세팀}이 많음" |
| `*_map_agent_*_mean` | `a-b` | "이 맵에서의 요원 숙련도가 {우세팀}이 우위" |
| `*_player_agent_*_mean` | `a-b` | "선수-요원 조합 경험이 {우세팀}이 풍부" |
| `a_role_*_count` / `a_agent_*_count` | 구성 | "{역할/요원} 구성이 예측에 기여" |
| `map_*` | 맵 | "{맵} 특성이 반영됨" |

`{우세팀}`은 `value`(또는 `a-b` 부호)로 결정. `Δ`는 `feature_values["a_..."] - feature_values["b_..."]`.

> 라벨 텍스트는 `app/predict.py`의 `feature_label()`과 일관되게. `feature_label`은 이미 `a_prior_kd_mean → "A팀 이전 연도 선수 평균 K/D"`처럼 변환하므로, 문장 템플릿의 기초 명사로 재사용 가능.

---

## 3. 직렬화 (`valo_web_backend/serializers.py`)

```python
PRIOR_GAMES = ("a_prior_games_mean", "b_prior_games_mean")

def _delta(fv, base):           # base="prior_games" → a_..._mean - b_..._mean
    return fv.get(f"a_{base}_mean", 0.0) - fv.get(f"b_{base}_mean", 0.0)

# 피처 패밀리 → (명사, 차이 포맷). a_/b_ 접두와 _mean 접미를 떼고 매칭.
_TEMPLATES = [
    ("prior_games",  "직전 연도 경험",        lambda d: f"평균 대비 {abs(d):.0f}경기"),
    ("prior_kd",     "선수 평균 K/D",         lambda d: f"{abs(d):.2f}"),
    ("prior_adr",    "라운드당 피해량(ADR)",  lambda d: f"{abs(d):.1f}"),
    ("prior_kast",   "KAST(라운드 기여율)",   lambda d: f"{abs(d)*100:.0f}%p"),
    ("synergy",      "팀 동반 출전 경험(호흡)", lambda d: ""),
    ("map_agent",    "이 맵에서의 요원 숙련도", lambda d: ""),
    ("player_agent", "선수-요원 조합 경험",    lambda d: ""),
]

def _base_of(feature: str) -> str:          # "a_prior_kd_mean" → "prior_kd"
    f = feature[2:] if feature[:2] in ("a_", "b_") else feature
    return f[:-5] if f.endswith("_mean") else f

def _sentence_for(f: dict, fv: dict, winner: str) -> dict | None:
    base = _base_of(f["feature"])
    for key, noun, fmt in _TEMPLATES:
        if key in base:
            d = fv.get(f"a_{base}_mean", 0.0) - fv.get(f"b_{base}_mean", 0.0)
            if abs(d) < 1e-9:
                return None
            side = "팀 A" if d > 0 else "팀 B"
            tail = fmt(d)
            text = f"{side} 우위: {noun}" + (f"가 {tail} 우세" if tail else "이 더 많음")
            return {"feature": f["feature"], "text": text, "magnitude": abs(d)}
    return None      # 구성(role/agent count)·맵 피처는 문장 생략(바 차트로 충분)

def explanations(r) -> list[dict]:
    fv = r.feature_values or {}
    winner = "팀 A" if r.predicted_label == 1 else "팀 B"
    out: list[dict] = []

    # 대표 문장 1: 경험(prior_games) — 사용자가 예시로 든 문장
    dg = _delta(fv, "prior_games")
    if abs(dg) >= 1:
        side = "팀 A" if dg > 0 else "팀 B"
        out.append({
            "feature": "prior_games",
            "text": f"{side} 우세 요인: 직전 연도 경험이 평균 대비 {abs(dg):.0f}경기 많음",
            "magnitude": abs(dg),
        })

    # top_features 기반 추가 문장 (중복 패밀리 제외)
    for f in r.top_features:
        s = _sentence_for(f, fv, winner)     # 위 §2 템플릿 매칭
        if s: out.append(s)
        if len(out) >= 4: break
    return out
```

응답 확장:
```jsonc
// PredictResponse 에 추가
"explanations": [
  { "feature": "prior_games", "text": "팀 A 우세 요인: 직전 연도 경험이 평균 대비 6경기 많음", "magnitude": 6.0 },
  { "feature": "a_synergy_mean", "text": "팀 동반 출전 경험(호흡)이 팀 A가 많음", "magnitude": 2.1 }
]
```

스키마:
```python
class Explanation(BaseModel):
    feature: str; text: str; magnitude: float
# PredictResponse 에 explanations: list[Explanation] 추가
```

---

## 4. 프론트 표시

```tsx
<section className="reason-card">
  <h3>{result.predicted_winner === "A" ? result.team_a.name : result.team_b.name} 우세</h3>
  <ul>
    {result.explanations.map(e => <li key={e.feature}>{e.text}</li>)}
  </ul>
</section>
```

타입:
```ts
export interface Explanation { feature: string; text: string; magnitude: number }
// PredictResponse 에 explanations: Explanation[]
```

`top_features` 바 차트(수치)와 `explanations` 카드(문장)를 **함께** 보여주면 "근거 카드"가 완성된다.

---

## 5. 정확도 주의 — 현재는 SHAP이 아니라 휴리스틱

`top_features`의 `contribution`은 `app/predict.py`가 **`importance × value`** 로 계산한 근사값이다(진짜 SHAP 아님). 즉 "기여 방향/크기"는 엄밀 인과가 아니라 휴리스틱이다.

- 시연 수준에는 충분하나, 문장에 "**왜냐하면**" 같은 강한 인과 표현은 피하고 "~요인", "~경향"으로 완화.
- 정밀도를 높이려면: `shap`(이미 `requirements.txt`에 있음)으로 앙상블 SHAP 값을 계산해 `contribution`을 대체 → 동일 `explanations` 파이프라인 재사용. 이는 별도 작업(모델 서빙 경로 추가)으로 분리.

---

## 6. 관련 문서

- 모델 출력 구조 → [../02_backend_fastapi/02_model_serving.md](../02_backend_fastapi/02_model_serving.md)
- 스키마 매핑 → [../02_backend_fastapi/04_schemas.md](../02_backend_fastapi/04_schemas.md)
