from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

_VALIDATION_PATH = Path("reports/research_validation.json")
_INGESTION_PATH = Path("reports/vlrgg_ingestion_summary.json")
_COVERAGE_PATH = Path("reports/data_source_coverage.json")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _table(rows: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    return df[[col for col in columns if col in df.columns]]


def _join(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def render() -> None:
    st.title("리서치 검증")

    validation = _load_json(_VALIDATION_PATH)
    ingestion = validation.get("vlr_ingestion") or _load_json(_INGESTION_PATH)
    coverage = validation.get("coverage") or _load_json(_COVERAGE_PATH)

    if not validation:
        st.info("아직 reports/research_validation.json이 없습니다. 리포트가 생성되면 이 화면에 검증 결과가 표시됩니다.")

    st.markdown("### 데이터 소스 상태")
    c1, c2, c3, c4 = st.columns(4)
    row_counts = ingestion.get("rows", {}) if isinstance(ingestion, dict) else {}
    c1.metric("VLR 매치", f"{row_counts.get('vlrgg_matches', 0):,}")
    c2.metric("VLR 선수 스탯", f"{row_counts.get('vlrgg_player_stats', 0):,}")
    c3.metric("요원 집계", f"{row_counts.get('vlrgg_agent_map_stats', 0):,}")
    c4.metric("네트워크 요청", f"{ingestion.get('network_requests', 0) if isinstance(ingestion, dict) else 0:,}")

    if ingestion:
        st.caption(
            " | ".join([
                f"generated_at={ingestion.get('generated_at', '-')}",
                f"mode={ingestion.get('mode', '-')}",
                f"api_base_url={ingestion.get('api_base_url', '-')}",
                f"robots_checked_at={ingestion.get('robots_checked_at', '-')}",
            ])
        )

        st.markdown("### 수집 가드레일")
        guardrail_rows = [{
            "robots_url": ingestion.get("robots_url", ""),
            "allowed_paths": _join(ingestion.get("allowed_paths", [])),
            "blocked_paths": _join(ingestion.get("blocked_paths", ingestion.get("blocked_direct_paths", []))),
            "direct_html_allowed": ingestion.get("direct_html_allowed", False),
            "network_requests": ingestion.get("network_requests", 0),
        }]
        st.dataframe(pd.DataFrame(guardrail_rows), use_container_width=True, hide_index=True)

    sources = (coverage.get("sources", {}) if isinstance(coverage, dict) else {})
    if sources:
        source_rows = []
        for name, info in sources.items():
            source_rows.append({
                "source": name,
                "rows": info.get("rows", 0) if isinstance(info, dict) else 0,
                "path": info.get("path", "") if isinstance(info, dict) else "",
            })
        st.dataframe(pd.DataFrame(source_rows), use_container_width=True, hide_index=True)

    additional = validation.get("additional_collection", {}) if validation else {}
    if additional:
        st.markdown("### 추가 수집 데이터")
        additional_counts = additional.get("row_counts", {}) if isinstance(additional, dict) else {}
        metric_names = [
            ("상세 맵", "vlrgg_match_maps"),
            ("상세 선수", "vlrgg_match_players"),
            ("조합", "vlrgg_compositions"),
            ("스탠딩", "vlrgg_standings"),
            ("팀 맵", "vlrgg_team_map_stats"),
            ("이벤트 매치", "vlrgg_event_matches"),
            ("픽/밴", "research_pick_ban"),
            ("이코노미", "research_economy"),
        ]
        for start in range(0, len(metric_names), 4):
            cols = st.columns(4)
            for col, (label, key) in zip(cols, metric_names[start:start + 4]):
                col.metric(label, f"{additional_counts.get(key, 0):,}")

        datasets = additional.get("datasets", {}) if isinstance(additional, dict) else {}
        dataset_rows = []
        for name, info in datasets.items():
            representative = info.get("representative_fact", {}) if isinstance(info, dict) else {}
            coverage_bits = info.get("source_coverage", {}) if isinstance(info, dict) else {}
            dataset_rows.append({
                "dataset": name,
                "group": info.get("group", "") if isinstance(info, dict) else "",
                "rows": info.get("rows", 0) if isinstance(info, dict) else 0,
                "path": info.get("path", "") if isinstance(info, dict) else "",
                "source_url": representative.get("source_url", "") if isinstance(representative, dict) else "",
                "retrieval_method": representative.get("retrieval_method", "") if isinstance(representative, dict) else "",
                "sources": _join(list((coverage_bits.get("source") or coverage_bits.get("dataset_id") or {}).keys())) if isinstance(coverage_bits, dict) else "",
            })
        if dataset_rows:
            st.dataframe(pd.DataFrame(dataset_rows), use_container_width=True, hide_index=True)

        degraded = additional.get("degraded_stages", []) if isinstance(additional, dict) else []
        source_errors = additional.get("local_source_errors", []) if isinstance(additional, dict) else []
        if degraded or source_errors:
            st.markdown("### 추가 수집 제한")
            limit_rows = [
                {"type": "degraded_stage", **row}
                for row in degraded
                if isinstance(row, dict)
            ] + [
                {
                    "type": "local_source_error",
                    "stage": row.get("path", ""),
                    "failure_reason": row.get("error", ""),
                }
                for row in source_errors
                if isinstance(row, dict)
            ]
            st.dataframe(pd.DataFrame(limit_rows), use_container_width=True, hide_index=True)

    st.markdown("### 가설 검증")
    verdict_counts = validation.get("summary", {}).get("verdict_counts", {}) if validation else {}
    if verdict_counts:
        cols = st.columns(4)
        for col, verdict in zip(cols, ["CONFIRMED", "REFINED", "CONTRADICTED", "INSUFFICIENT_DATA"]):
            col.metric(verdict, verdict_counts.get(verdict, 0))

    hyp_df = _table(
        validation.get("hypotheses", []) if validation else [],
        ["id", "verdict", "description", "test_stat", "p_value", "sample_size", "evidence"],
    )
    if not hyp_df.empty:
        st.dataframe(hyp_df, use_container_width=True, hide_index=True)
    else:
        st.caption("가설 검증 결과가 없습니다.")

    st.markdown("### 문서 수치 대 데이터 차이")
    diff_df = _table(
        validation.get("doc_metric_diffs", []) if validation else [],
        ["metric", "map", "verdict", "doc_value", "observed_value", "delta", "sample_size", "source", "dataset_id"],
    )
    if not diff_df.empty:
        st.dataframe(diff_df, use_container_width=True, hide_index=True)
    else:
        st.caption("비교 가능한 문서 수치가 아직 없습니다.")

    st.markdown("### 문서 갱신 후보 Fact")
    fact_df = _table(
        validation.get("report_facts", []) if validation else [],
        [
            "fact_id",
            "topic",
            "metric",
            "value",
            "unit",
            "sample_size",
            "dataset_id",
            "source_url",
            "fetched_at",
            "retrieval_method",
            "verdict",
            "doc_targets",
        ],
    )
    if not fact_df.empty:
        if "doc_targets" in fact_df.columns:
            fact_df["doc_targets"] = fact_df["doc_targets"].map(_join)
        st.dataframe(fact_df, use_container_width=True, hide_index=True)
    else:
        st.caption("문서 갱신 후보 fact가 아직 없습니다.")

    comparisons = validation.get("data_comparisons", {}) if validation else {}
    if comparisons:
        st.markdown("### 데이터 차별성")
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("모델 학습 매치", f"{comparisons.get('model_match_rows', 0):,}")
        cc2.metric("VLR 매치 후보", f"{comparisons.get('vlr_match_rows', 0):,}")
        cc3.metric("공유 요원", f"{len(comparisons.get('shared_agents', [])):,}")

        top_agents = comparisons.get("top_vlr_agents", [])
        if top_agents:
            st.dataframe(pd.DataFrame(top_agents), use_container_width=True, hide_index=True)
