# 01. 프로젝트 소개 및 핵심 아이디어

## 1. ValoPredictML이란?

**ValoPredictML**은 FPS 게임 Valorant의 **5v5 팀 조합**을 입력받아 **승률을 예측**하는 머신러닝 기반 예측 시스템입니다.  
픽 단계(경기 시작 전 요원 선택 단계)에서 실시간으로 각 팀의 역할군 구성을 분석하고,  
웹 기반 대시보드에서 직관적으로 결과를 시각화합니다.

---

## 2. 문제 정의

### 2.1 배경

Valorant는 48종 이상의 요원(캐릭터) 중 각 플레이어가 1명씩 선택하여 5v5로 대결하는 게임입니다.  
요원 선택 단계(픽창)에서 팀 구성은 승패에 중요한 영향을 미치지만,  
초보 플레이어나 분석 경험이 없는 유저는 직관에만 의존하게 됩니다.

### 2.2 해결하려는 것

> **"지금 이 팀 조합으로 싸우면 이길 가능성이 얼마나 될까?"**

픽창에서 양 팀의 요원 구성을 입력하면, 머신러닝 모델이 승률을 계산해주는 시스템을 구축합니다.

---

## 3. 핵심 아이디어: 역할군 기반 피처 추상화

### 3.1 개별 요원 접근법의 문제

48종 요원을 각각 One-Hot Encoding으로 피처화하면:
- 피처 수: 48 × 2팀 = **96개** (고차원, 과적합 위험)
- 신규 요원 출시 시: **모델 재학습 필수** (운영 부담)
- 데이터 부족: 최근 출시 요원은 경기 수가 적어 **학습 신뢰도 저하**

### 3.2 역할군 카운트 접근법

모든 요원을 4대 역할군으로 분류합니다:

| 역할군 | 영어 | 역할 | 예시 요원 |
|---|---|---|---|
| 타격대 | Duelist | 공격적 진입, 킬 창출 | Jett, Reyna, Neon |
| 척후병 | Initiator | 정보 수집, 팀 진입 보조 | Sova, Breach, Fade |
| 전략가 | Controller | 스모크로 시야 차단, 지역 통제 | Viper, Omen, Astra |
| 감시자 | Sentinel | 수비, 사이드 잠금, 힐 | Killjoy, Cypher, Sage |

**피처 추출 방식:**
```
팀 A: [Jett(D), Sova(I), Viper(C), Killjoy(S), Skye(I)]
→ team_a_duelist=1, team_a_initiator=2, team_a_controller=1, team_a_sentinel=1

팀 B: [Reyna(D), Breach(I), Omen(C), Cypher(S), Fade(I)]
→ team_b_duelist=1, team_b_initiator=2, team_b_controller=1, team_b_sentinel=1
```

### 3.3 핵심 피처 15개

| 피처 | 설명 | 수 |
|---|---|---|
| `team_a_{role}_count` | 팀 A의 각 역할군 카운트 | 4개 |
| `team_b_{role}_count` | 팀 B의 각 역할군 카운트 | 4개 |
| `{role}_diff` | 팀 A - 팀 B 역할군 수 차이 | 4개 |
| `team_a_has_controller` | 팀 A에 전략가 1명 이상 존재 | 1개 |
| `team_b_has_controller` | 팀 B에 전략가 1명 이상 존재 | 1개 |
| `map_encoded` | 맵 이름 Label Encoding | 1개 |
| **합계** | | **15개** |

### 3.4 이 방식의 장점

| 항목 | 개별 요원 방식 | **역할군 방식** |
|---|---|---|
| 피처 수 | 96개+ | **15개** |
| 신규 요원 대응 | 재학습 필요 | **자동 일반화** |
| 과적합 위험 | 높음 | **낮음** |
| 해석 가능성 | 낮음 | **높음** |
| 데이터 요구량 | 매우 많음 | **적어도 가능** |

---

## 4. 성능 목표

| 지표 | 목표값 | 설명 |
|---|---|---|
| **Accuracy** | ≥ 80% | 전체 정확도 |
| **F1-Score (Macro)** | ≥ 0.78 | 클래스 불균형 고려 |
| **ROC-AUC** | ≥ 0.82 | 이진 분류 성능 |
| **Train-Val 격차** | ≤ 3%p | 과적합 기준 |
| **API 응답시간** | ≤ 200ms | 모델 추론 엔드포인트 |

### 과적합 판단 및 대응 전략

```
판단: Train Accuracy - Validation Accuracy > 3%p
대응:
  1. max_depth 1~2 감소
  2. subsample / colsample_bytree 0.1 감소
  3. Early Stopping rounds 10 감소
  4. 피처 중요도 하위 피처 제거
  5. 학습 데이터 증가 (추가 데이터 수집 후 재학습)
```

---

## 5. 주요 기능 요약

| 기능 | 설명 |
|---|---|
| **팀 조합 입력** | 양 팀 각 5명 요원 선택 UI |
| **실시간 승률 예측** | 요원 선택 시 즉각 승률 계산 |
| **역할군 시각화** | 양 팀 역할군 분포 레이더 차트 |
| **피처 중요도 표시** | 어떤 역할군 구성이 예측에 영향을 미쳤는지 바 차트 |
| **예측 기록 조회** | PostgreSQL에 저장된 과거 예측 이력 테이블 |
| **Vercel 배포** | 어떤 환경에서도 브라우저로 테스트 가능 |

---

## 6. 관련 문서

| 문서 | 내용 |
|---|---|
| [02_tech_stack.md](02_tech_stack.md) | 기술 스택 상세, 버전, 선택 이유 |
| [03_design_principles.md](03_design_principles.md) | 방어적 처리, 모듈형 아키텍처 등 설계 원칙 |
| [04_roadmap_and_team.md](04_roadmap_and_team.md) | 단계별 로드맵, 팀 구성, 용어 사전 |
| [../03_architecture/01_system_overview.md](../03_architecture/01_system_overview.md) | 시스템 3계층 아키텍처 전체 |
