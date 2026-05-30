# 03. 기술 스택

## 1. 스택 요약

| 계층 | 도구 | 버전 | 역할 |
|------|------|------|------|
| 프론트 프레임워크 | Next.js | 16.x (App Router) | 라우팅, 빌드, SSR/CSR |
| UI 런타임 | React | 19.x | 컴포넌트 렌더링 |
| **언어(프론트)** | **TypeScript** | **5.x** | **타입 안전 API 계약** ← 09_web과 핵심 차이 |
| 스타일 | Tailwind CSS | v4 | 유틸리티 CSS (선택: CSS Modules 병행) |
| 차트 | Recharts | 2.x | 승률 게이지(RadialBar), 역할군 레이더 |
| 백엔드 | FastAPI | 0.115+ | 모델 서빙 API |
| ASGI 서버 | uvicorn | 0.30+ | FastAPI 실행 |
| 검증 | Pydantic | v2 | 요청/응답 스키마 |
| ML 코어 | scikit-learn / XGBoost / LightGBM | `requirements.txt` 기준 | 앙상블 추론 (기존) |

> 백엔드 ML 의존성은 **이미 `requirements.txt`에 있다**. 추가로 필요한 것은 `fastapi`, `uvicorn`뿐이다(아래 §4).

---

## 2. TypeScript를 쓰는 이유 (09_web은 JS로 확정했었음)

`docs/09_web/01_overview/01_tech_stack.md`는 "JavaScript, TypeScript 미사용"으로 못 박았다. 본 시연은 **TypeScript를 채택**한다. 근거:

- API 응답이 `PredictionResult`라는 **확정된 구조**를 가진다 → 타입으로 고정하면 프론트-백 계약 어긋남을 컴파일 타임에 잡는다.
- `top_features[].feature`, `role_counts`, `confidence` 등 필드명이 모델 코드에 박혀 있어 추측 여지가 없다 → `types/api.ts` 단일 출처로 관리.
- 09_web이 겪은 실패(존재하지 않는 피처명 `"팀 조합 다양성"` 같은 임의 필드)를 타입이 구조적으로 차단한다.

타입 정의 단일 출처: [../03_frontend_nextjs/02_types_and_api_client.md](../03_frontend_nextjs/02_types_and_api_client.md), 계약 SSOT: [../04_integration/01_data_contract.md](../04_integration/01_data_contract.md).

---

## 3. 프론트엔드 의존성 (`package.json` 예시)

```jsonc
{
  "dependencies": {
    "next": "^16",
    "react": "^19",
    "react-dom": "^19",
    "recharts": "^2"
  },
  "devDependencies": {
    "typescript": "^5",
    "@types/react": "^19",
    "@types/node": "^22",
    "tailwindcss": "^4",
    "@tailwindcss/postcss": "^4"
  }
}
```

생성: `npx create-next-app@latest valo_web_frontend --typescript --app --tailwind` (상세 → [../03_frontend_nextjs/01_setup_and_structure.md](../03_frontend_nextjs/01_setup_and_structure.md)).

---

## 4. 백엔드 추가 의존성

`requirements.txt`에 다음 2줄만 추가하면 된다(나머지 ML 스택은 이미 존재):

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
```

`pydantic`은 FastAPI가 끌어온다(v2). 모델 로딩에 쓰는 `joblib`, `pandas`, `numpy`, `scikit-learn`, `xgboost`, `lightgbm`은 이미 설치돼 있다.

---

## 5. 포트·환경

| 항목 | 값 |
|------|-----|
| 프론트 dev | `http://localhost:3000` |
| 백엔드 | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` (FastAPI 자동 생성) |
| 프론트→백 URL | `NEXT_PUBLIC_API_URL` (기본 `http://localhost:8000`) |

CORS·환경변수 상세 → [../02_backend_fastapi/05_run_and_cors.md](../02_backend_fastapi/05_run_and_cors.md).
