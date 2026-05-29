> ⚠️ **범위 외**: 외부 API 미사용 방침. 본 프로젝트는 Kaggle 7개 데이터셋만 사용하며 Riot VCT S3 접근은 적용되지 않는다. 본문은 참고용으로 보존된다.

# 01. Riot VCT S3 Hackathon 데이터 개요

## 1. 이 데이터셋이 핵심인 이유

Riot Games는 2023년 VCT Hackathon을 위해 **공식 경기 데이터를 AWS S3에 공개**했다.  
**범위 외 — 현재 프로젝트에서 미사용. 하기 내용은 참고용 기록.** (현재 방침: Kaggle 7개 데이터셋 전용, Riot S3 미적용. 실측 성능: Acc 0.6958·AUC 0.7570)

| 항목 | 값 |
|------|-----|
| 제공 주체 | Riot Games (공식) |
| 호스팅 | AWS S3 (공개 버킷) |
| 커버리지 | VCT 2022, VCT 2023 전 공식 경기 |
| 데이터 형식 | JSON (경기별 원본) |
| 예상 경기 수 | 180,000+ 경기 (시리즈 × 맵 단위) |
| 라이선스 | Riot VCT Hackathon 공개 라이선스 |

---

## 2. 공식 GitHub 및 접근 경로

### 2.1 공식 리포지토리

```
https://github.com/riotgames/vct-esports-manager-data
```

README 구조:
```
vct-esports-manager-data/
├── README.md          # 데이터 구조 설명
├── schema/            # JSON 스키마 정의
├── examples/          # 예제 데이터
└── scripts/           # 다운로드 헬퍼 스크립트
```

### 2.2 S3 버킷 URL

```
s3://vcthackathon-data/
```

직접 접근 URL 구조:
```
https://vcthackathon-data.s3.us-east-1.amazonaws.com/{league}/{year}/games/{game_id}.json
```

### 2.3 리그 목록

| 리그 코드 | 설명 | 연도 |
|----------|------|------|
| `international` | VCT International (챔피언십) | 2022, 2023 |
| `americas` | VCT Americas 리그 | 2023 |
| `emea` | VCT EMEA 리그 | 2023 |
| `pacific` | VCT Pacific 리그 | 2023 |
| `game_changers` | VCT Game Changers | 2022, 2023 |

---

## 3. 데이터 볼륨 추정

| 리그 | 경기 수 | 맵 수 | JSON 파일 수 |
|------|--------|------|------------|
| VCT International 2022 | ~200 | ~500 | ~500 |
| VCT International 2023 | ~200 | ~500 | ~500 |
| VCT Americas 2023 | ~300 | ~700 | ~700 |
| VCT EMEA 2023 | ~300 | ~700 | ~700 |
| VCT Pacific 2023 | ~300 | ~700 | ~700 |
| Game Changers | ~500 | ~1,200 | ~1,200 |
| **총계** | **~1,800** | **~4,300** | **~4,300** |

> **주의:** 위 수치는 추정치. 실제 볼륨은 S3 인덱스 파일을 통해 확인 가능.

---

## 4. JSON 데이터 종류

각 경기에는 여러 종류의 JSON 파일이 존재:

### 4.1 파일 타입별 내용

| 타입 | 내용 | 크기 |
|------|------|------|
| `game_timeline` | 매 라운드별 킬/데스/이벤트 | 크다 (~5MB) |
| `scoreboard` | 최종 스코어보드 | 작다 (~50KB) |
| `mapping` | 경기 메타 (팀명, 날짜, 맵) | 매우 작다 (~5KB) |
| `player_mapping` | 선수 ID ↔ 이름 매핑 | 작다 (~10KB) |

### 4.2 핵심 JSON 구조 (mapping 파일)

```json
{
  "platformGameId": "val:gvp-...",
  "tournamentId": "...",
  "matchId": "...",
  "gameId": "...",
  "map": {
    "id": "...",
    "name": "Ascent"
  },
  "teams": [
    {
      "id": "team_a_id",
      "name": "Sentinels",
      "won": true,
      "players": [
        {
          "playerId": "...",
          "agent": {
            "id": "...",
            "name": "Jett"
          }
        }
      ]
    }
  ]
}
```

---

## 5. 80% 달성에 미치는 영향

> ⚠️ **범위 외 참고용 추정** — 아래 수치는 Riot S3 미사용 전 초기 추정이며, 현재 프로젝트에 적용되지 않는다.  
> 실측 성능(현재 방침 기준): 53K행·125피처·RF+XGB+LGBM → Acc 0.6958·AUC 0.7570

```
[범위 외 참고용 추정]
현재 상태:
- Kaggle VCT 2021-2023만 사용: ~2,000경기 → 예상 정확도 67-72%

Riot S3 추가 후:
- 총 ~4,300+ 맵 단위 경기 (프로 씬 전체)
- 모든 공식 경기 커버
- 피처 확장 + 이 데이터 결합 → 예상 정확도 78-82%

추가로 랭크 매치까지:
- 50,000+ 경기 → 예상 정확도 80-84%
```

---

## 6. 사용 전 확인사항

### 6.1 접근 가능성 확인

```bash
# S3 버킷 접근 테스트 (aws CLI 또는 curl)
curl -s "https://vcthackathon-data.s3.us-east-1.amazonaws.com/" | head -100

# 또는 Python으로
import boto3
from botocore import UNSIGNED
from botocore.client import Config

s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
# 버킷 내용 확인
response = s3.list_objects_v2(Bucket="vcthackathon-data", MaxKeys=10)
```

### 6.2 법적 고려사항

- Riot Games VCT Hackathon 약관 준수 필요
- 상업적 이용 제한 가능성 → 약관 원문 확인
- 비상업적 교육/연구 목적 사용은 일반적으로 허용
- 데이터 재배포 금지 (개인 서버 업로드 등)

---

## 7. 다음 단계

1. [02_s3_download_guide.md](02_s3_download_guide.md) — S3 다운로드 실전 코드
2. [03_data_structure.md](03_data_structure.md) — JSON 파싱 및 피처 추출

---

## 8. 대안: Riot 공식 GitHub 직접 접근

Riot S3 접근이 불가한 경우 GitHub에서 샘플 데이터 확인:

```bash
git clone https://github.com/riotgames/vct-esports-manager-data
ls vct-esports-manager-data/examples/
```
