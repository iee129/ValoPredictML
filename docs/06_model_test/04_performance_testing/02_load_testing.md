# 02. 부하 테스트

## 1. 부하 테스트 목표

| 시나리오 | 동시 사용자 | 목표 | 실패 허용 |
|---------|-----------|------|---------|
| 정상 부하 | 10 VU | P95 < 200ms, 에러율 0% | 없음 |
| 중간 부하 | 50 VU | P95 < 500ms, 에러율 < 1% | 5% 미만 |
| 최대 부하 | 100 VU | 에러율 < 5% | 10% 미만 |
| 스파이크 | 0→100 VU (10초) | 서버 다운 없음 | 일시적 지연 허용 |

---

## 2. k6 부하 테스트 시나리오

### 2.1 표준 부하 테스트 (Ramp-up → Steady → Ramp-down)

```javascript
// tests/performance/k6_scripts/load_test.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

const errorRate = new Rate('error_rate');
const predictDuration = new Trend('predict_duration', true);
const requestCount = new Counter('request_count');

export const options = {
  stages: [
    { duration: '30s', target: 10 },   // 0 → 10 VU (워밍업)
    { duration: '1m',  target: 10 },   // 10 VU 유지 (정상 부하)
    { duration: '30s', target: 50 },   // 10 → 50 VU (중간 부하)
    { duration: '1m',  target: 50 },   // 50 VU 유지
    { duration: '30s', target: 100 },  // 50 → 100 VU (최대 부하)
    { duration: '1m',  target: 100 },  // 100 VU 유지
    { duration: '30s', target: 0 },    // 100 → 0 VU (종료)
  ],
  thresholds: {
    'predict_duration': [
      'p(95)<500',   // P95 500ms 이내
      'p(99)<1000',  // P99 1초 이내
    ],
    'error_rate': ['rate<0.05'],       // 에러율 5% 미만
    'http_req_failed': ['rate<0.05'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const PAYLOADS = [
  {
    map: 'Ascent',
    team_a: ['Jett','Sova','Viper','Killjoy','Skye'],
    team_b: ['Reyna','Breach','Omen','Cypher','Fade'],
  },
  {
    map: 'Bind',
    team_a: ['Neon','Fade','Viper','Sage','Cypher'],
    team_b: ['Jett','Sova','Omen','Killjoy','Skye'],
  },
  {
    map: 'Haven',
    team_a: ['Iso','Gekko','Astra','Chamber','KAY/O'],
    team_b: ['Yoru','Breach','Harbor','Deadlock','Tejo'],
  },
];

export default function () {
  // 랜덤 페이로드 선택
  const payload = PAYLOADS[Math.floor(Math.random() * PAYLOADS.length)];

  const res = http.post(
    `${BASE_URL}/predict`,
    JSON.stringify(payload),
    { headers: { 'Content-Type': 'application/json' } }
  );

  requestCount.add(1);
  predictDuration.add(res.timings.duration);

  const success = check(res, {
    'status 200': (r) => r.status === 200,
    'has win_probability': (r) => {
      try {
        return JSON.parse(r.body).win_probability !== undefined;
      } catch {
        return false;
      }
    },
  });

  errorRate.add(!success);

  sleep(Math.random() * 2 + 0.5);  // 0.5 ~ 2.5초 랜덤 대기 (실제 사용 패턴 모사)
}
```

```bash
# 실행
k6 run tests/performance/k6_scripts/load_test.js

# 결과를 InfluxDB로 전송 (선택)
k6 run --out influxdb=http://localhost:8086/k6 tests/performance/k6_scripts/load_test.js

# HTML 리포트 생성
k6 run --out json=results/load_test.json tests/performance/k6_scripts/load_test.js
```

---

### 2.2 스파이크 테스트

```javascript
// tests/performance/k6_scripts/spike_test.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 0 },    // 초기 안정
    { duration: '10s', target: 100 },  // 급격한 스파이크
    { duration: '1m',  target: 100 },  // 고부하 유지
    { duration: '10s', target: 0 },    // 급격한 감소
    { duration: '30s', target: 0 },    // 회복 확인
  ],
  thresholds: {
    'http_req_failed': ['rate<0.10'],   // 스파이크 중 실패율 10% 미만
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const res = http.post(
    `${BASE_URL}/predict`,
    JSON.stringify({
      map: 'Ascent',
      team_a: ['Jett','Sova','Viper','Killjoy','Skye'],
      team_b: ['Reyna','Breach','Omen','Cypher','Fade'],
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(res, { 'not server error': (r) => r.status < 500 });
}
```

---

### 2.3 지구력 테스트 (Soak Test)

```javascript
// tests/performance/k6_scripts/soak_test.js
// 낮은 부하로 장시간 실행 → 메모리 누수, 커넥션 풀 고갈 확인
export const options = {
  stages: [
    { duration: '5m',  target: 20 },   // 워밍업
    { duration: '30m', target: 20 },   // 30분 유지
    { duration: '5m',  target: 0 },    // 종료
  ],
  thresholds: {
    'http_req_duration': ['p(95)<300'],
    'http_req_failed': ['rate<0.01'],
  },
};
```

---

## 3. 동시 요청 처리 — Python 병렬 테스트

```python
# tests/performance/test_concurrent_requests.py
import concurrent.futures
import time
import pytest
import requests

BASE_URL = "http://localhost:8000"
PAYLOAD = {
    "map": "Ascent",
    "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
    "team_b": ["Reyna", "Breach", "Omen", "Cypher", "Fade"],
}

def send_request(i: int) -> dict:
    start = time.perf_counter()
    response = requests.post(f"{BASE_URL}/predict", json=PAYLOAD, timeout=5)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {
        "index": i,
        "status_code": response.status_code,
        "elapsed_ms": elapsed_ms,
        "success": response.status_code == 200,
    }

@pytest.mark.performance
@pytest.mark.slow
def test_10_concurrent_requests():
    """10개 동시 요청 처리 — 모두 성공해야 함."""
    n = 10
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        futures = [executor.submit(send_request, i) for i in range(n)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    success_count = sum(1 for r in results if r["success"])
    avg_ms = sum(r["elapsed_ms"] for r in results) / len(results)
    max_ms = max(r["elapsed_ms"] for r in results)

    print(f"\n동시 {n}개 요청 결과:")
    print(f"  성공: {success_count}/{n}")
    print(f"  평균 응답시간: {avg_ms:.1f}ms")
    print(f"  최대 응답시간: {max_ms:.1f}ms")

    assert success_count == n, f"{n - success_count}개 요청 실패"
    assert max_ms < 1000, f"최대 응답시간 초과: {max_ms:.1f}ms"


@pytest.mark.performance
@pytest.mark.slow
def test_50_concurrent_requests():
    """50개 동시 요청 처리 — 에러율 5% 미만."""
    n = 50
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        futures = [executor.submit(send_request, i) for i in range(n)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    success_count = sum(1 for r in results if r["success"])
    error_rate = (n - success_count) / n

    print(f"\n동시 {n}개 요청 에러율: {error_rate*100:.1f}%")
    assert error_rate < 0.05, f"에러율 초과: {error_rate*100:.1f}%"
```

---

## 4. FastAPI 워커 설정 최적화

```bash
# Uvicorn 단일 워커 (개발)
uvicorn main:app --reload --port 8000

# Uvicorn 멀티 워커 (프로덕션 — CPU 코어 수 기반)
uvicorn main:app --workers 4 --port 8000

# Gunicorn + Uvicorn 워커 (프로덕션 권장)
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 30 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100
```

### 워커 수 계산 공식

```
워커 수 = (CPU 코어 수 × 2) + 1

예시:
- 2코어 서버: 5 워커
- 4코어 서버: 9 워커
- Render Free (0.1 CPU): 2 워커
```

---

## 5. 부하 테스트 결과 해석 기준

| 지표 | 양호 | 주의 | 위험 |
|------|------|------|------|
| P50 응답시간 | < 100ms | 100~300ms | > 300ms |
| P95 응답시간 | < 200ms | 200~500ms | > 500ms |
| P99 응답시간 | < 500ms | 500ms~1s | > 1s |
| 에러율 | 0% | 0.1~1% | > 1% |
| 처리량 (RPS) | > 50 | 10~50 | < 10 |

---

## 6. 부하 테스트 실행 절차

```bash
# 1. 서버 기동 (멀티 워커)
cd backend
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 &

# 2. 서버 준비 대기
sleep 3
curl http://localhost:8000/health

# 3. 단계별 부하 테스트 실행
mkdir -p results

# 응답시간 테스트
k6 run --out json=results/response_time.json \
  tests/performance/k6_scripts/response_time.js

# 부하 테스트
k6 run --out json=results/load_test.json \
  tests/performance/k6_scripts/load_test.js

# 스파이크 테스트
k6 run --out json=results/spike_test.json \
  tests/performance/k6_scripts/spike_test.js

# 4. 결과 요약
echo "=== 부하 테스트 완료 ==="
ls -la results/
```
