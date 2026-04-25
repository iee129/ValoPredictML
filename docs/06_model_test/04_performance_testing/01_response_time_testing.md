# 01. 응답시간 측정 방법

## 1. 목표 기준

| 엔드포인트 | 목표 응답시간 | 허용 최대 | 측정 조건 |
|-----------|-------------|---------|---------|
| POST /predict | ≤ 200ms | 500ms | 단일 요청, 모델 이미 로드됨 |
| GET /agents | ≤ 50ms | 100ms | 단일 요청 |
| GET /maps | ≤ 30ms | 100ms | 단일 요청 |
| GET /history | ≤ 100ms | 300ms | 최대 100건 조회 |
| GET /health | ≤ 50ms | 100ms | DB ping 포함 |

> 첫 번째 요청(Cold Start)은 모델 로드로 인해 1~5초가 소요될 수 있습니다. 이 측정은 제외합니다.

---

## 2. curl을 이용한 응답시간 측정

### 2.1 단일 요청 측정

```bash
# 기본 응답시간 측정
curl -s -o /dev/null -w "Total: %{time_total}s | Connect: %{time_connect}s | TTFB: %{time_starttransfer}s\n" \
  -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'
```

**curl 시간 변수 설명**

| 변수 | 의미 |
|------|------|
| `%{time_connect}` | TCP 연결 수립 시간 |
| `%{time_starttransfer}` | 첫 바이트 수신까지 시간 (TTFB) |
| `%{time_total}` | 전체 요청-응답 시간 |
| `%{http_code}` | HTTP 상태 코드 |

### 2.2 10회 반복 측정 스크립트

```bash
#!/bin/bash
# scripts/measure_response_time.sh

URL="${1:-http://localhost:8000/predict}"
COUNT="${2:-10}"
PAYLOAD='{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'

echo "=== 응답시간 측정: $COUNT회 ==="
echo "URL: $URL"
echo ""

TIMES=()
for i in $(seq 1 $COUNT); do
  T=$(curl -s -o /dev/null -w "%{time_total}" \
    -X POST "$URL" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")
  MS=$(python3 -c "print(f'{float(\"$T\")*1000:.1f}')")
  TIMES+=("$MS")
  STATUS=$([ $(echo "$MS < 200" | bc -l) -eq 1 ] && echo "OK" || echo "SLOW")
  echo "  [$i] ${MS}ms [$STATUS]"
done

# 통계 계산
python3 -c "
times = [float(t) for t in '${TIMES[*]}'.split()]
print(f'\n=== 통계 ===')
print(f'최소: {min(times):.1f}ms')
print(f'최대: {max(times):.1f}ms')
print(f'평균: {sum(times)/len(times):.1f}ms')
times.sort()
n = len(times)
p50 = times[n//2]
p95 = times[int(n*0.95)]
p99 = times[int(n*0.99)] if n >= 100 else times[-1]
print(f'P50: {p50:.1f}ms')
print(f'P95: {p95:.1f}ms')
pass_count = sum(1 for t in times if t <= 200)
print(f'200ms 이내: {pass_count}/{n} ({pass_count/n*100:.0f}%)')
"
```

```bash
chmod +x scripts/measure_response_time.sh
./scripts/measure_response_time.sh http://localhost:8000/predict 10
```

### 2.3 모든 엔드포인트 응답시간 일괄 측정

```bash
#!/bin/bash
# scripts/benchmark_all.sh
BASE="${1:-http://localhost:8000}"

measure() {
  local method=$1
  local url=$2
  local payload=$3
  if [ "$method" = "POST" ]; then
    curl -s -o /dev/null -w "%{time_total}" \
      -X POST "$url" -H "Content-Type: application/json" -d "$payload"
  else
    curl -s -o /dev/null -w "%{time_total}" "$url"
  fi
}

echo "=== 전체 엔드포인트 벤치마크 ==="
PAYLOAD='{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'

declare -A TARGETS=(
  ["POST /predict"]="200"
  ["GET /agents"]="50"
  ["GET /maps"]="30"
  ["GET /history"]="100"
  ["GET /health"]="50"
)

for endpoint in "POST /predict" "GET /agents" "GET /maps" "GET /history" "GET /health"; do
  method=$(echo $endpoint | cut -d' ' -f1)
  path=$(echo $endpoint | cut -d' ' -f2)

  if [ "$method" = "POST" ]; then
    T=$(measure POST "$BASE$path" "$PAYLOAD")
  else
    T=$(measure GET "$BASE$path")
  fi

  MS=$(python3 -c "print(f'{float(\"$T\")*1000:.1f}')")
  TARGET=${TARGETS[$endpoint]}
  STATUS=$(python3 -c "print('OK' if $MS <= $TARGET else 'SLOW')")
  echo "  $endpoint: ${MS}ms [목표: ${TARGET}ms] [$STATUS]"
done
```

---

## 3. Python pytest로 응답시간 자동화 검증

```python
# tests/performance/test_response_time.py
import time
import pytest
import statistics
from fastapi.testclient import TestClient

PREDICT_PAYLOAD = {
    "map": "Ascent",
    "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
    "team_b": ["Reyna", "Breach", "Omen", "Cypher", "Fade"],
}

def measure_ms(func) -> float:
    start = time.perf_counter()
    func()
    return (time.perf_counter() - start) * 1000


@pytest.mark.performance
def test_predict_single_request_under_200ms(client):
    elapsed = measure_ms(lambda: client.post("/predict", json=PREDICT_PAYLOAD))
    assert elapsed < 200, f"응답시간 초과: {elapsed:.1f}ms (목표: 200ms)"


@pytest.mark.performance
def test_predict_10_requests_all_under_200ms(client):
    times = []
    for _ in range(10):
        t = measure_ms(lambda: client.post("/predict", json=PREDICT_PAYLOAD))
        times.append(t)

    p95 = sorted(times)[int(len(times) * 0.95)]
    avg = statistics.mean(times)
    max_t = max(times)

    print(f"\n응답시간 통계 (10회):")
    print(f"  평균: {avg:.1f}ms")
    print(f"  최대: {max_t:.1f}ms")
    print(f"  P95: {p95:.1f}ms")

    assert max_t < 200, f"최대 응답시간 초과: {max_t:.1f}ms"


@pytest.mark.performance
def test_agents_under_50ms(client):
    elapsed = measure_ms(lambda: client.get("/agents"))
    assert elapsed < 50, f"응답시간 초과: {elapsed:.1f}ms (목표: 50ms)"


@pytest.mark.performance
def test_maps_under_30ms(client):
    elapsed = measure_ms(lambda: client.get("/maps"))
    assert elapsed < 30, f"응답시간 초과: {elapsed:.1f}ms (목표: 30ms)"


@pytest.mark.performance
def test_history_under_100ms(client):
    elapsed = measure_ms(lambda: client.get("/history"))
    assert elapsed < 100, f"응답시간 초과: {elapsed:.1f}ms (목표: 100ms)"


@pytest.mark.performance
def test_health_under_50ms(client):
    elapsed = measure_ms(lambda: client.get("/health"))
    assert elapsed < 50, f"응답시간 초과: {elapsed:.1f}ms (목표: 50ms)"
```

---

## 4. k6를 이용한 응답시간 측정

### 4.1 k6 설치

```bash
# macOS
brew install k6

# Linux
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6
```

### 4.2 단일 사용자 응답시간 k6 스크립트

```javascript
// tests/performance/k6_scripts/response_time.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

const predictDuration = new Trend('predict_duration', true);

export const options = {
  vus: 1,          // 단일 사용자
  iterations: 20,  // 20회 반복
  thresholds: {
    'predict_duration': ['p(95)<200', 'max<500'],  // P95 < 200ms, 최대 < 500ms
    'http_req_failed': ['rate<0.01'],               // 실패율 1% 미만
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const PAYLOAD = JSON.stringify({
  map: 'Ascent',
  team_a: ['Jett', 'Sova', 'Viper', 'Killjoy', 'Skye'],
  team_b: ['Reyna', 'Breach', 'Omen', 'Cypher', 'Fade'],
});
const HEADERS = { 'Content-Type': 'application/json' };

export default function () {
  const res = http.post(`${BASE_URL}/predict`, PAYLOAD, { headers: HEADERS });

  predictDuration.add(res.timings.duration);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200,
    'has win_probability': (r) => JSON.parse(r.body).win_probability !== undefined,
  });

  sleep(0.1);  // 100ms 대기
}
```

```bash
# 실행
k6 run tests/performance/k6_scripts/response_time.js

# 환경 변수로 URL 지정
BASE_URL=https://your-api.onrender.com k6 run tests/performance/k6_scripts/response_time.js

# 결과를 JSON으로 저장
k6 run --out json=results/response_time.json tests/performance/k6_scripts/response_time.js
```

### 4.3 k6 결과 해석

```
          /\      |‾‾| /‾‾/   /‾‾/
     /\  /  \     |  |/  /   /  /
    /  \/    \    |     (   /   ‾‾\
   /          \   |  |\  \ |  (‾)  |
  / __________ \  |__| \__\ \_____/ .io

  scenarios: (100.00%) 1 scenario, 1 max VUs, 30s max duration
  default: 20 looping VUs for 20 iterations

✓ status is 200
✓ response time < 200ms
✓ has win_probability

predict_duration............: avg=85.2ms  min=72.1ms  med=83.4ms  max=142.3ms p(90)=112.5ms p(95)=128.7ms
http_req_duration...........: avg=85.3ms  min=72.2ms  med=83.5ms  max=142.4ms
http_req_failed.............: 0.00%
```

---

## 5. 응답시간 저하 원인 분석

| 현상 | 가능한 원인 | 확인 방법 |
|------|-----------|---------|
| 첫 요청만 느림 (3~5초) | 모델 Cold Start | /health에서 model_loaded 확인 |
| 모든 요청이 300ms+ | 모델 추론 병목 | cProfile로 predict() 프로파일링 |
| DB 관련 요청만 느림 | DB 인덱스 없음 | EXPLAIN ANALYZE 실행 |
| 간헐적 지연 | GC, 스왑 메모리 | 서버 리소스 모니터링 |
| CORS preflight 추가 | OPTIONS 요청 | 브라우저 DevTools Network 탭 |

### 5.1 모델 추론 프로파일링

```python
# scripts/profile_predict.py
import cProfile
import pstats
import io
import joblib
import numpy as np
import sys
sys.path.insert(0, './backend')

from services.prediction_service import PredictionService

svc = PredictionService()

def run_predict():
    for _ in range(100):
        svc.predict("Ascent", ["Jett","Sova","Viper","Killjoy","Skye"],
                              ["Reyna","Breach","Omen","Cypher","Fade"])

pr = cProfile.Profile()
pr.enable()
run_predict()
pr.disable()

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats(20)
print(s.getvalue())
```

```bash
python scripts/profile_predict.py
```
