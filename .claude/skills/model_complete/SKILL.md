---
name: model_complete
description: >-
  학습된 모델 파일(.pt PyTorch 또는 .joblib/.pkl tree-based)이 준비됐을 때, 실제 모델을 FastAPI 백엔드(valo_web_backend)에
  올리고 프론트엔드(valo_web_frontend)의 mock(src/lib/mock.ts + src/app/api/* 라우트 + .env.local의 /api)을 걷어내
  실제 백엔드와 연동한다. 그 결과 사용자가 맵·선수·요원을 입력하면 mock이 아닌 실제 모델 추론으로 승률·근거를 시각화한다.
  트리거: "model_complete", "모델 완성/실모델 연동", "mock 걷어내", "실제 모델로 띄워", "go live", ".pt 올려서 연동".
---

# model_complete — mock 제거 + 실제 모델 라이브 전환

학습이 끝난 모델을 실서빙으로 띄우고, 프론트의 mock 계층을 제거해 **사용자 입력 → 실제 모델 추론 → 시각화**가 되도록 전환한다.

## 핵심 원칙 (안전)
1. **순서 엄수**: ① 실제 백엔드가 정상 추론하는지 먼저 확인 → ② 그다음에만 프론트 mock 제거. 순서를 뒤집으면 mock도 실모델도 없는 깨진 상태가 된다.
2. **계약 불변**: 입력 = `{map, cutoff_year, team_a:[{player,agent}×5], team_b:[…]}`, 출력 = `PredictResponse`(types/api.ts ↔ valo_web_backend/schemas.py). 모델만 바뀌고 계약은 그대로 → 프론트 코드/타입 수정 불필요.
3. **게이트 통과 못 하면 중단**하고 사용자에게 막힌 지점을 보고한다.

---

## 0. 전제 확인
```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
```
필요 산출물(없으면 먼저 만들 것 — 루트 CLAUDE.md "자주 쓰는 명령어" 참조):
- 모델 파일: 기본 `models/advanced/ensemble.joblib`, 또는 사용자가 준 `*.pt`/`*.joblib`/`*.pkl`
- `data/processed/{matches,players}.csv` (런타임 이전-연도 피처 계산에 필수)
- `data/processed/adv_kaggle_only/test.csv` (`/replay`)
- `reports/adv_kaggle_only/{metrics,validation}.json` (`/model`)
- (선택) `reports/insights/{agent_map_fit,meta_comps}.json` — 없으면 `python -m ml.insights.build_insights --input data/processed --output reports/insights`

`fastapi`/`uvicorn`/`pydantic`은 `requirements.txt`에 있음. `.pt`면 `pip install torch`도 필요.

---

## 1. 모델 아티팩트 탐지 & 로딩 어댑터

서빙 진입점은 `app/predict.py`의 `load_model()` 하나다. FastAPI는 이걸 그대로 호출한다(`valo_web_backend/services/prediction.py`). 추론은 `model.predict_proba(X[FEATURE_COLS_ADVANCED])[:, 1]`로만 일어나므로, **`predict_proba`와 `n_features_in_==125`만 갖추면 어떤 모델이든 꽂힌다.**

### 분기 A — tree-based (`.joblib`/`.pkl`, 이 프로젝트의 기본)
추가 작업 없음. 이미 `load_model`이 `models/advanced/ensemble.joblib`을 로드한다. 검증:
```bash
python -c "from app.predict import load_model; m,meta=load_model(); print('n_features_in_=', getattr(m,'n_features_in_',None), '| algo=', meta.get('algorithm'))"
```
→ `n_features_in_= 125`면 통과. (모델 경로가 다르면 `models/advanced/ensemble.joblib`로 두거나 `load_model(models_dir=...)`.)

### 분기 B — PyTorch (`.pt`)
`load_model`의 `joblib.load`는 `.pt`를 못 읽는다. **계약을 깨지 않고** 끼우려면 `predict_proba`/`n_features_in_`을 흉내내는 어댑터로 감싼다.

1. `pip install torch` (+ requirements.txt에 `torch` 추가).
2. `app/torch_serving.py` 생성 — 아래 래퍼:
   ```python
   from __future__ import annotations
   import numpy as np

   class TorchProbaWrapper:
       """torch nn.Module을 sklearn predict_proba 계약에 맞춘다.
       입력 125피처 → 이진 승률. n_features_in_=125 로 load_model 게이트 통과."""
       n_features_in_ = 125
       def __init__(self, net):
           import torch
           self.torch = torch
           self.net = net.eval()
       def predict_proba(self, X):
           t = self.torch.tensor(np.asarray(X, dtype="float32"))
           with self.torch.no_grad():
               logits = self.net(t).reshape(-1)
               p = self.torch.sigmoid(logits).cpu().numpy()
           return np.column_stack([1.0 - p, p])

   def load_torch_model(pt_path: str):
       import torch
       obj = torch.load(pt_path, map_location="cpu", weights_only=False)
       net = obj if hasattr(obj, "eval") else obj  # state_dict면 모델 클래스 필요(사용자 확인)
       return TorchProbaWrapper(net)
   ```
3. `app/predict.py`의 `load_model`이 `.pt`도 처리하도록 수정: 확장자가 `.pt`면 `load_torch_model(...)`을, 아니면 기존 `joblib.load(...)`을 쓰도록 분기. `meta.json`이 없으면 `{"algorithm":"pytorch","n_features":125,"feature_contract":"advanced"}` 같은 최소 meta를 합성.
4. **반드시 사용자에게 확인할 것**:
   - `.pt`가 통째 `nn.Module`인지 `state_dict`인지(후자면 아키텍처 클래스가 있어야 로드 가능).
   - 입력이 정말 **이 프로젝트의 125피처(`FEATURE_COLS_ADVANCED`) 그대로**인지. 다르면 `ml/baseline/preprocess.py`의 피처 계약 자체를 맞춰야 한다(이 스킬 범위 밖 — 막히면 보고).
   - ⚠️ 한계: 트리 모델의 `feature_importances_`가 없어 `/model` 전역 중요도와 `top_features` 기여도가 0/빈값이 된다. 자연어 근거는 동작하나 피처 바는 의미가 약해진다. 필요 시 SHAP/gradient attribution을 별도 구현(보고).

> ⚠️ 도메인 메모: 이 저장소는 "딥러닝 금지, tree-based만"이 원래 제약(CLAUDE.md). `.pt` 도입은 그 제약을 벗어나므로, 사용자에게 의도를 한 번 확인하고 진행한다.

---

## 2. 모델 업로드(서빙) + 헬스체크 + 규격 가상데이터 스모크 (★ 게이트)

### 2-1. 백엔드 기동 = 모델을 백엔드에 올림
```bash
# 저장소 루트에서, 백그라운드로
uvicorn valo_web_backend.main:app --port 8000
```
서버 startup의 `warmup()`이 `load_model()`을 호출해 모델을 메모리에 적재한다(콜드스타트 흡수).

### 2-2. 헬스체크
```bash
curl -s http://localhost:8000/health
# 기대: {"status":"ok","model_loaded":true,"n_features":125,"contract":"advanced"}
```

### 2-3. 규격 맞춘 가상 데이터 투입 → 결과 수신·검증 (번들 스크립트)
이 스킬에 포함된 `smoke_test.py`가 `/options`에서 실제 요원·맵·선수를 받아 **계약에 맞는 5v5 입력**을 구성해 던지고, `/predict`·`/comp-match`·`/agent-map-fit`·`/replay` 응답이 `PredictResponse` 계약을 지키는지 + 값이 합리적인지(승률합≈1, role 합=5, confidence∈[0,1], top_features 계약) 검증한다. 잘못된 입력(선수 중복)이 422로 막히는지도 확인한다.
```bash
python .claude/skills/model_complete/smoke_test.py            # 기본 http://localhost:8000
```
- **전부 PASS(exit 0)** 여야 다음 단계로 진행. 출력의 `>>> 결과: 승자 .. | A .. / B .. | conf ..`로 실제 결과값을 눈으로 확인한다.
- `/health` `model_loaded=False` 또는 `/predict` **503** → 모델/데이터 산출물 부재. 0번으로 돌아가 산출물부터 만든다. **여기서 통과 못 하면 절대 다음 단계(프론트 mock 제거)로 가지 말 것.**
- `/predict` **422**(선수 중복 케이스)는 입력 검증이 작동한다는 정상 신호.
- 실모델 판별: 라인업을 바꿔 한 번 더 던졌을 때 승률이 달라지면 실제 추론(mock의 결정론적 가짜값이 아님).

---

## 3. 프론트엔드: mock 제거 + 실제 백엔드 연동

게이트(2)를 통과한 뒤에만 수행.

1. **백엔드를 가리키도록 전환** — `valo_web_frontend/.env.local`:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
2. **mock 계층 삭제(걷어내기)**:
   - `valo_web_frontend/src/lib/mock.ts`
   - `valo_web_frontend/src/app/api/` 디렉터리 전체(8개 route handler: options/model/predict/agent-map-fit/comp-match/replay/health)
   - (선택) `valo_web_backend/mock_main.py` — Python mock 서버. 실서빙엔 불필요.
   ```bash
   cd valo_web_frontend
   rm -rf src/app/api src/lib/mock.ts
   ```
3. **`src/lib/api.ts` 기본값 정리** — mock 라우트가 사라졌으니 `?? "/api"` 폴백이 죽은 경로를 가리키지 않도록, 기본값을 실제 백엔드로 바꾼다:
   ```ts
   const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
   ```
   (`.env.local`이 이미 설정돼 있으면 폴백은 안 쓰이지만, 안전하게 정리.)
4. **타입/빌드 검증** — mock 삭제로 끊긴 import가 없는지 확인:
   ```bash
   npx tsc --noEmit      # exit 0 이어야 함 (mock.ts를 쓰던 건 app/api/* 뿐 → 함께 삭제됨)
   ```
5. **프론트 기동**:
   ```bash
   npm run dev           # http://localhost:3000  (.env.local의 백엔드를 호출)
   ```

---

## 4. E2E 검증 (실모델 결과 시각화 확인)

백엔드(:8000) + 프론트(:3000) 둘 다 떠 있는 상태에서:
- Playwright MCP가 있으면 그걸로, 없으면 사용자에게 브라우저 확인 요청.
- 확인 항목:
  - `/model`: 실제 `reports`의 AUC·검증 verdict가 뜬다(mock의 고정값 0.7570/PASS와 다를 수 있음).
  - `/predict`: 맵+선수+요원 입력 → **실제 모델 승률**과 영향 피처·근거 카드가 렌더(입력을 바꾸면 결과가 모델대로 변함).
  - `/replay`: 실제 test split 경기들이 뜨고 예측 vs 실제 적중 표시.
- mock이 제거됐는지 최종 확인: 네트워크 요청이 `localhost:8000`으로 가고 `localhost:3000/api/*`(404)로 가지 않는다.

성공 기준: 사용자 입력값을 바꿀 때마다 결과가 **모델 추론대로** 달라진다(mock의 결정론적 가짜값이 아님).

---

## 5. 막혔을 때 / 롤백
- 산출물 부재(503)로 막히면: 데이터 블로커(Kaggle→processed 변환 스크립트 부재, CLAUDE.md 참조)부터 해결해야 한다고 보고.
- 전환을 되돌리려면: `git checkout -- valo_web_frontend/src/lib/api.ts valo_web_frontend/src/app/api valo_web_frontend/src/lib/mock.ts` 로 mock 복원하고 `.env.local`을 `NEXT_PUBLIC_API_URL=/api`로 되돌린다.
- 작업 후: 떠 있던 dev/uvicorn 프로세스 정리 여부를 사용자에게 확인.
