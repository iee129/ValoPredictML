# 01. 데이터 품질 지표

## 1. 품질 지표 프레임워크

데이터 품질을 **완결성(Completeness)**, **일관성(Consistency)**, **정확성(Accuracy)** 3개 차원으로 측정.

---

## 2. 완결성 (Completeness)

### 2.1 필수 컬럼 존재 여부

```python
import pandas as pd
from typing import Optional

REQUIRED_COLUMNS = [
    "match_id", "map",
    "team_a_agents", "team_b_agents",
    "label",
]

FEATURE_COLUMNS = [
    "a_duelist", "a_initiator", "a_controller", "a_sentinel",
    "b_duelist", "b_initiator", "b_controller", "b_sentinel",
    "duelist_diff", "initiator_diff", "controller_diff", "sentinel_diff",
    "map_encoded", "has_controller_a", "has_controller_b",
]

def check_completeness(df: pd.DataFrame) -> dict:
    """필수 컬럼 및 피처 완결성 검사"""
    results = {}
    
    # 1. 필수 컬럼 존재
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    results["missing_required_cols"] = missing_cols
    
    # 2. NULL 비율 (피처 기준)
    if all(c in df.columns for c in FEATURE_COLUMNS):
        null_rates = df[FEATURE_COLUMNS].isnull().mean()
        results["null_rate"] = null_rates[null_rates > 0].to_dict()
        results["rows_with_null"] = df[FEATURE_COLUMNS].isnull().any(axis=1).sum()
    
    # 3. 전체 완결성 점수 (0~100)
    total_cells = len(df) * len(FEATURE_COLUMNS) if all(c in df.columns for c in FEATURE_COLUMNS) else 0
    null_cells = df[FEATURE_COLUMNS].isnull().sum().sum() if total_cells > 0 else 0
    results["completeness_score"] = round((1 - null_cells / total_cells) * 100, 2) if total_cells > 0 else 0
    
    return results
```

### 2.2 요원 정보 완결성

```python
def check_agent_completeness(df: pd.DataFrame) -> dict:
    """팀별 요원 수 완결성 (5인 여부)"""
    results = {}
    
    def count_agents(agents_str: str) -> int:
        if pd.isna(agents_str):
            return 0
        return len([a.strip() for a in str(agents_str).split(",") if a.strip()])
    
    df = df.copy()
    df["_count_a"] = df["team_a_agents"].apply(count_agents)
    df["_count_b"] = df["team_b_agents"].apply(count_agents)
    
    full_rows = ((df["_count_a"] == 5) & (df["_count_b"] == 5)).sum()
    partial_rows = ((df["_count_a"] < 5) | (df["_count_b"] < 5)).sum()
    
    results["full_5v5_rate"] = round(full_rows / len(df) * 100, 2)
    results["partial_rows"] = partial_rows
    results["agent_count_dist_a"] = df["_count_a"].value_counts().to_dict()
    results["agent_count_dist_b"] = df["_count_b"].value_counts().to_dict()
    
    return results
```

---

## 3. 일관성 (Consistency)

### 3.1 역할군 카운트 합계 검증

```python
def check_consistency(df: pd.DataFrame) -> dict:
    """역할군 카운트 일관성 검사"""
    results = {}
    
    if not all(c in df.columns for c in ["a_duelist", "a_initiator", "a_controller", "a_sentinel"]):
        results["error"] = "피처 컬럼 없음"
        return results
    
    # 1. 역할군 합계 = 5 여부
    sum_a = df["a_duelist"] + df["a_initiator"] + df["a_controller"] + df["a_sentinel"]
    sum_b = df["b_duelist"] + df["b_initiator"] + df["b_controller"] + df["b_sentinel"]
    
    invalid_a = (sum_a != 5).sum()
    invalid_b = (sum_b != 5).sum()
    
    results["role_sum_invalid_a"] = int(invalid_a)
    results["role_sum_invalid_b"] = int(invalid_b)
    results["role_sum_valid_rate"] = round(
        (1 - (invalid_a + invalid_b) / (len(df) * 2)) * 100, 2
    )
    
    # 2. diff 피처 정합성
    diff_errors = {}
    for role in ["duelist", "initiator", "controller", "sentinel"]:
        expected_diff = df[f"a_{role}"] - df[f"b_{role}"]
        actual_diff = df.get(f"{role}_diff", pd.Series([0]*len(df)))
        mismatch = (expected_diff != actual_diff).sum()
        if mismatch > 0:
            diff_errors[f"{role}_diff_mismatch"] = int(mismatch)
    
    results["diff_errors"] = diff_errors
    
    # 3. 레이블 분포 (0/1 여부)
    if "label" in df.columns:
        valid_labels = df["label"].isin([0, 1]).sum()
        results["invalid_labels"] = int(len(df) - valid_labels)
        results["label_balance"] = df["label"].value_counts(normalize=True).round(3).to_dict()
    
    return results
```

---

## 4. 정확성 (Accuracy)

### 4.1 알려진 요원 목록과 대조

```python
from docs_context import AGENT_ROLE_MAP  # 실제 임포트 경로

VALID_AGENTS = set(AGENT_ROLE_MAP.keys())

def check_accuracy(df: pd.DataFrame) -> dict:
    """알려진 요원 목록 기반 정확성 검사"""
    results = {}
    
    unknown_agents = set()
    
    for col in ["team_a_agents", "team_b_agents"]:
        if col not in df.columns:
            continue
        all_agents = df[col].apply(
            lambda x: [a.strip() for a in str(x).split(",") if a.strip()]
        ).explode()
        
        unknown = set(all_agents) - VALID_AGENTS - {"", "nan", "None"}
        unknown_agents.update(unknown)
    
    results["unknown_agents"] = sorted(unknown_agents)
    results["unknown_agent_count"] = len(unknown_agents)
    
    # 맵 유효성
    VALID_MAPS = {
        "Ascent", "Bind", "Breeze", "Drift", "Fracture", "Haven",
        "Icebox", "Lotus", "Pearl", "Split", "Sunset", "Abyss",
    }
    if "map" in df.columns:
        invalid_maps = set(df["map"].unique()) - VALID_MAPS
        results["invalid_maps"] = sorted(invalid_maps)
    
    return results
```

---

## 5. 통합 품질 리포트

```python
def generate_quality_report(df: pd.DataFrame, source_name: str = "unknown") -> None:
    """전체 데이터 품질 리포트 출력"""
    print(f"\n{'='*60}")
    print(f" 데이터 품질 리포트: {source_name}")
    print(f"{'='*60}")
    print(f"전체 행 수: {len(df):,}")
    
    completeness = check_completeness(df)
    consistency = check_consistency(df)
    accuracy = check_accuracy(df)
    
    print(f"\n[완결성] 점수: {completeness.get('completeness_score', 0):.1f}%")
    print(f"  NULL 있는 행: {completeness.get('rows_with_null', 0):,}개")
    print(f"  5v5 완전 행: {check_agent_completeness(df).get('full_5v5_rate', 0):.1f}%")
    
    print(f"\n[일관성]")
    print(f"  역할군 합계=5 비율: {consistency.get('role_sum_valid_rate', 0):.1f}%")
    print(f"  레이블 균형: {consistency.get('label_balance', {})}")
    
    print(f"\n[정확성]")
    print(f"  미인식 요원: {accuracy.get('unknown_agent_count', 0)}개 → {accuracy.get('unknown_agents', [])}")
    print(f"  미인식 맵: {accuracy.get('invalid_maps', [])}")
    
    # 최종 점수
    completeness_score = completeness.get("completeness_score", 0)
    consistency_score = consistency.get("role_sum_valid_rate", 0)
    accuracy_score = 100.0 if accuracy.get("unknown_agent_count", 0) == 0 else 70.0
    overall = (completeness_score + consistency_score + accuracy_score) / 3
    
    print(f"\n[종합 품질 점수] {overall:.1f}/100")
    print(f"{'='*60}")
```

---

## 6. 품질 목표 기준

| 지표 | 최소 기준 | 권장 기준 |
|------|---------|--------|
| 완결성 점수 | 95% | 99% |
| 역할군 합계=5 비율 | 95% | 99% |
| 미인식 요원 | 0개 | 0개 |
| 미인식 맵 | 0개 | 0개 |
| 레이블 균형 (0:1) | 45:55 ~ 55:45 | 48:52 ~ 52:48 |
| 최소 경기 수 | 10,000 | 50,000 |
