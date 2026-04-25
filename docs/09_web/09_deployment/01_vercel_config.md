# 01. Vercel 설정

---

## `vercel.json` 전체

```json
{
  "version": 2,
  "regions": ["icn1"],
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-fastapi-server.com/:path*"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" }
      ]
    }
  ]
}
```

---

## 주요 설정 항목 설명

### `regions`

```json
"regions": ["icn1"]
```

- `icn1` = 서울 리전 (Incheon)
- 한국 사용자 대상이므로 가장 낮은 레이턴시

사용 가능한 리전 코드:
| 코드 | 위치 |
|---|---|
| `icn1` | 서울 (한국) |
| `hnd1` | 도쿄 (일본) |
| `sfo1` | 샌프란시스코 |
| `iad1` | 워싱턴 D.C. |

### `rewrites` (API 프록시)

```json
"rewrites": [
  {
    "source": "/api/:path*",
    "destination": "https://your-fastapi-server.com/:path*"
  }
]
```

- 프론트엔드에서 `/api/predict`로 요청 → FastAPI 서버로 프록시
- CORS 문제 없이 같은 도메인에서 API 호출 가능
- `destination`의 URL을 실제 FastAPI 서버 URL로 교체 필요

### `headers` (보안)

기본 보안 헤더 설정:
- `X-Content-Type-Options: nosniff` — MIME 스니핑 방지
- `X-Frame-Options: DENY` — iframe 임베딩 방지
- `X-XSS-Protection: 1; mode=block` — XSS 기본 차단

---

## Vercel 프로젝트 설정

### 루트 디렉터리

Vercel 대시보드에서 **Root Directory**를 `valo_predict_system`으로 설정:

```
프로젝트 루트: /
Next.js 앱:   valo_predict_system/
              ├── src/
              ├── package.json
              └── next.config.mjs
```

> `valo_predict_system/` 내에 `package.json`이 있으므로 Vercel이 여기서 빌드.

### 빌드 설정

| 항목 | 값 |
|---|---|
| Framework Preset | Next.js |
| Root Directory | `valo_predict_system` |
| Build Command | `npm run build` |
| Output Directory | `.next` |
| Install Command | `npm install` |

---

## vercel.json 위치

```
valo_predict_system/
└── vercel.json   ← Next.js 앱 루트에 위치
```

---

## 배포 도메인

Vercel은 자동으로 다음 도메인 생성:
- `https://valo-predict-ml.vercel.app` (프로젝트명 기반)
- PR마다 preview URL 생성 (`https://valo-predict-ml-{hash}.vercel.app`)

커스텀 도메인은 Vercel 대시보드에서 추가 설정 가능.
