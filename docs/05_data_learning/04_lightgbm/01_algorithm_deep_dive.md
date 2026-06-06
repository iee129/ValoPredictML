# 01. LightGBM 알고리즘 심층 분석

마지막 업데이트: 2026-06-04

## 개요

LightGBM(Light Gradient Boosting Machine)은 Microsoft Research에서 개발한 Gradient Boosting 구현체다. XGBoost 대비 학습 속도 5~10배 향상, 메모리 사용량 절감이 핵심 특징이다. 내부 알고리즘인 GOSS, EFB, Leaf-wise 성장을 수식과 함께 상세히 설명한다.
ValoPredictML에서 LightGBM은 RF + XGBoost + LightGBM 가중 soft voting 앙상블 구성원 중 하나다(가중치 RF 2.0 : XGB 3.0 : LGBM 0.1). 스케일링 불필요.

> 현행 심화 LightGBM 코드 고정 하이퍼파라미터(Optuna 미사용): `n_estimators=1000`, `num_leaves=63`, `learning_rate=0.02`, `min_child_samples=40`, `subsample=0.8`, `colsample_bytree=0.7`. 시간순 split LGBM Test AUC ≈ 0.7015.

---

## 1. XGBoost 대비 핵심 혁신

### 1.1 문제 인식

기존 XGBoost의 병목:
```
1. Pre-sorted 분기점 탐색: 모든 피처 × 모든 샘플 정렬 → O(N log N * d)
2. 대규모 데이터에서 메모리 부족
3. 분산 학습 시 통신 비용 과다
```

LightGBM의 두 가지 혁신:
```
1. GOSS (Gradient-based One-Side Sampling): 샘플 효율적 선택
2. EFB (Exclusive Feature Bundling): 피처 효율적 묶음
3. Histogram-based 분기점 탐색 (XGBoost Approximate와 유사하나 최적화)
4. Leaf-wise 트리 성장 (XGBoost Level-wise 대비 더 낮은 오차)
```

---

## 2. GOSS (Gradient-based One-Side Sampling)

### 2.1 핵심 아이디어

```
관찰: 학습이 잘 된 샘플은 gradient가 작음 (손실이 거의 없음)
      학습이 부족한 샘플은 gradient가 큼 (손실이 많이 남음)

아이디어:
- gradient가 큰 샘플: 정보량 많음 → 전부 사용
- gradient가 작은 샘플: 정보량 적음 → 일부만 랜덤 샘플링
- 단, 분포 편향 방지를 위해 소샘플에 가중치 부여
```

### 2.2 GOSS 알고리즘

```
Input:
    D = {(x_i, y_i)}: 전체 학습 데이터 (N개)
    a: 상위 gradient 샘플 비율 (예: 0.2 → 상위 20%)
    b: 하위 gradient 샘플에서 무작위 선택 비율 (예: 0.1)

Algorithm:
1. 각 샘플의 |gradient| 계산: g_i = |∂L/∂F(x_i)|
2. 상위 a*100% 샘플 집합 A = {i : rank(g_i) ≤ a*N}
3. 나머지 (1-a)*N개 중에서 b*(1-a)*N개 무작위 선택 → 집합 B
4. 편향 보정 가중치 w = (1-a) / b (B의 샘플들에 적용)
5. 학습 데이터 = A ∪ B (|A| + |B| << N)

분기 이득 계산 (GOSS 버전):
Gain_GOSS = (1/2) * [(G_L + w*G_L^B)² / (H_L + w*H_L^B) +
                     (G_R + w*G_R^B)² / (H_R + w*H_R^B) -
                     (G_total + w*G_total^B)² / (H_total + w*H_total^B)]
```

### 2.3 정보 손실 이론적 보장

```
정리 (논문 Theorem 3.2):
GOSS 기반 이득과 정확한 이득의 차이는 다음으로 상한됨:

|Gain_GOSS - Gain_exact| ≤ C * [(1-a)/b] * ||g||₂ / N

- N이 클수록 오차 감소 → 대규모 데이터에서 수렴 보장
- a, b 선택이 오차-속도 트레이드오프 결정
```

### 2.4 Python 시뮬레이션

```python
import numpy as np

def goss_sampling(gradients, a=0.2, b=0.1, random_state=42):
    """
    GOSS 샘플링 시뮬레이션.

    Args:
        gradients: 각 샘플의 gradient 절댓값
        a: 상위 gradient 유지 비율
        b: 하위 gradient에서 샘플링 비율

    Returns:
        sampled_indices: 선택된 샘플 인덱스
        weights: 각 샘플의 가중치
    """
    N = len(gradients)
    rng = np.random.RandomState(random_state)

    # 1. gradient 절댓값으로 정렬
    sorted_idx = np.argsort(np.abs(gradients))[::-1]

    # 2. 상위 a*N개 선택
    top_k = int(a * N)
    top_indices = sorted_idx[:top_k]

    # 3. 나머지에서 b*(1-a)*N개 랜덤 선택
    rest_indices = sorted_idx[top_k:]
    sample_k = int(b * (1 - a) * N)
    sampled_rest = rng.choice(rest_indices, size=sample_k, replace=False)

    # 4. 가중치 설정
    weights = np.ones(N)
    weights[sampled_rest] = (1 - a) / b  # 소샘플에 보정 가중치

    # 5. 최종 인덱스
    sampled_indices = np.concatenate([top_indices, sampled_rest])

    print(f"원본 샘플 수: {N}")
    print(f"GOSS 후 샘플 수: {len(sampled_indices)} ({len(sampled_indices)/N*100:.1f}%)")
    print(f"  상위 gradient: {len(top_indices)}개 (가중치=1)")
    print(f"  하위 gradient 샘플: {len(sampled_rest)}개 (가중치={(1-a)/b:.2f})")

    return sampled_indices, weights
```

---

## 3. EFB (Exclusive Feature Bundling)

### 3.1 핵심 아이디어

```
관찰: 고차원 데이터에서 많은 피처가 희소(sparse)함
      상호 배타적(Mutually Exclusive) 피처: 동시에 0이 아닌 경우가 드문 피처 쌍

아이디어:
- 상호 배타적인 피처들을 하나의 번들(bundle)로 묶음
- 피처 수 d → d' (d' << d) 감소 → 학습 속도 향상
```

### 3.2 EFB 알고리즘

```
1단계: 상호 배타성 그래프 구성
    - 노드: 각 피처
    - 엣지: 두 피처가 동시에 0이 아닌 비율이 γ (conflict rate) 이상이면 연결

2단계: 그래프 컬러링 (Graph Coloring)
    - 같은 색상의 피처들은 한 번들로 묶임
    - NP-hard 문제이므로 greedy 근사 알고리즘 사용

3단계: 번들 내 피처 값 병합
    - 번들 내 피처들의 값 범위를 다르게 오프셋 적용하여 구분
    - 예: feature A: [0, 10], feature B: [0, 5]
          → bundle: A 그대로, B는 +10 → [10, 15]
          → 히스토그램에서 0~10은 A, 10~15는 B

ValoPredictML 적용:
    - 피처 179개 (advanced), 대부분 수치형 카운트 → 희소성 낮음
    - EFB 효과 제한적 (EFB는 희소 데이터에서 최대 효과)
    - 그러나 LightGBM이 자동으로 최적 판단
```

### 3.3 EFB 파라미터

```python
lgb_params = {
    # EFB 관련
    "max_bin": 255,        # 히스토그램 bin 수 (EFB에도 영향)
    "min_data_in_bin": 3,  # bin당 최소 데이터 수
    # max_conflict_rate 내부 파라미터 (직접 설정 불가)
    # LightGBM이 자동으로 bundling 여부 결정
}
```

---

## 4. Leaf-wise 트리 성장

### 4.1 Level-wise vs Leaf-wise 비교

```
XGBoost Level-wise (BFS):
    깊이 0:              [루트]
    깊이 1:          [L1]     [R1]
    깊이 2:       [L2] [L3] [R2] [R3]
    → 모든 리프를 같은 깊이에서 분기
    → 균형 트리 (balanced tree)
    → max_depth로 제어

LightGBM Leaf-wise (Best-First):
    깊이 0:              [루트]
    깊이 1:          [L1]     [R1]
    깊이 2:    [L2]  [L3]          (이득이 큰 L1의 자식만 분기)
    깊이 3:  [L4][L5]              (이득이 큰 L2의 자식만 분기)
    → 이득이 최대인 리프만 분기 → 비균형 트리
    → 동일 트리 수 대비 낮은 손실
    → num_leaves로 제어
```

### 4.2 Leaf-wise 수식

```
각 라운드에서:
1. 현재 모든 리프의 분기 이득 계산
2. 이득이 최대인 단일 리프 선택하여 분기
3. 리프 수 = num_leaves에 도달할 때까지 반복

이득 최대 리프 선택:
leaf* = argmax_{j ∈ leaves} Gain(j)

Gain(j) = (1/2) * [G_Lj²/(H_Lj+λ) + G_Rj²/(H_Rj+λ) - G_j²/(H_j+λ)] - γ
```

### 4.3 과적합 위험과 대응

```
Leaf-wise의 과적합 위험:
- 비균형 트리가 깊어질수록 특정 패턴 과적합
- 소규모 데이터에서 특히 위험 (advanced train N~75K, min_child_samples=40으로 대응)

대응 파라미터:
num_leaves: 트리당 최대 리프 수 제한 (Level-wise의 max_depth 대응)
min_child_samples: 리프 최소 샘플 수 (과적합 방지)
min_child_weight: 리프 최소 hessian 합

권장 관계식:
num_leaves ≤ 2^(max_depth - 1)
예: max_depth=6 → num_leaves ≤ 31 (기본값 31이 이에 맞음)
```

---

## 5. Histogram-based 분기점 탐색

### 5.1 히스토그램 구축

```
연속형 피처 값을 bin으로 양자화:

원본: [0.12, 1.35, 2.78, 1.21, 0.89, ...]
bin 기준: [0~0.5, 0.5~1.0, 1.0~1.5, 1.5~2.0, ...]
히스토그램: [bin0: {G:0.12, H:0.08, count:1},
            bin1: {G:0.35, H:0.22, count:2},
            bin2: {G:0.89, H:0.45, count:3}, ...]

이점:
- 분기점 후보 수: N → b (b: bin 수, 기본 255)
- 메모리: float64 → uint8 (8배 감소)
- 캐시 지역성 향상
```

### 5.2 히스토그램 빼기 최적화

```
부모 히스토그램 = 좌측 자식 히스토그램 + 우측 자식 히스토그램

→ 두 자식 중 하나만 계산하면 나머지는 빼기로 구함:
hist_right = hist_parent - hist_left

→ 더 작은 자식만 계산 → 학습 시간 절반
→ XGBoost Approximate 대비 추가 속도 향상
```

---

## 6. 알고리즘 복잡도 비교

| 알고리즘 | XGBoost (Pre-sorted) | XGBoost (Approximate) | LightGBM |
|---------|--------------------|--------------------|----------|
| 분기점 탐색 | O(N log N * d) | O(N * b) | O(N * b) |
| GOSS 적용 후 | - | - | O(aN * b) (a<1) |
| EFB 적용 후 | - | - | O(aN * b') (b'<b) |
| 메모리 | O(N * d) | O(N * d) | O(N * d') (d'<d) |

ValoPredictML advanced (N~75K train, d=179, b=255, a=0.2):
```
XGBoost: 75000 * 255 * 179 ≈ 3.4B 연산/트리
LightGBM: 0.2 * 75000 * 255 * d' ≈ 3.8M * d' 연산/트리 (d'≤179)
속도비: ~5배 향상
```

---

## 7. ValoPredictML에서의 적용 특성

```python
# ValoPredictML 데이터 특성 분석
feature_analysis = {
    "n_samples": "91,458 맵 단위 승패 샘플",  # BO 시리즈 수가 아니라 모델 학습·평가 행 수
    "n_features": 179,           # advanced 179피처 (역할군·스탯·시너지·요원조합·맵 피처)
    "feature_types": "numeric",  # 모두 정수형/수치형
    "sparsity": "low",           # 역할군 카운트는 항상 0~5 사이값
    "class_balance": "near 50/50",  # match_key 단위 분할로 train/test 분리 후 자연 균형 확보
}

# LightGBM 현행 고정 설정 (ValoPredictML, Optuna 미사용)
lgb_valorant_params = {
    "num_leaves": 63,            # 현행 코드 고정값
    "min_child_samples": 40,     # 과적합 방지 (현행 고정값)
    "learning_rate": 0.02,       # 낮은 학습률
    "n_estimators": 1000,
    "subsample": 0.8,
    "colsample_bytree": 0.7,
}

# 참고: 역할군 카운트는 값 범위가 작아(0~5) max_bin을 줄이면 정규화·속도 이점이 있다.
# (현행 코드는 max_bin 기본값을 사용한다.)
```
