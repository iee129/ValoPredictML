from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ml.agent_roles import ATK_ADV_MAP
from ml.hypothesis_test import test_hypotheses

VERDICTS = ("CONFIRMED", "CONTRADICTED", "REFINED", "INSUFFICIENT_DATA")
REQUIRED_FACT_FIELDS = (
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
)
ADDITIONAL_DATASETS = (
    ("vlrgg_match_maps", "data/processed/vlrgg_match_maps.csv", "vlr_detail"),
    ("vlrgg_match_players", "data/processed/vlrgg_match_players.csv", "vlr_detail"),
    ("vlrgg_compositions", "data/processed/vlrgg_compositions.csv", "vlr_detail"),
    ("vlrgg_standings", "data/processed/vlrgg_standings.csv", "vlr_team_event"),
    ("vlrgg_team_map_stats", "data/processed/vlrgg_team_map_stats.csv", "vlr_team_event"),
    ("vlrgg_event_matches", "data/processed/vlrgg_event_matches.csv", "vlr_team_event"),
    ("research_pick_ban", "data/processed/research_pick_ban.csv", "local_raw"),
    ("research_economy", "data/processed/research_economy.csv", "local_raw"),
    ("research_clutch_counter", "data/processed/research_clutch_counter.csv", "local_raw"),
    ("research_player_map_stats", "data/processed/research_player_map_stats.csv", "local_raw"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def _hypothesis_verdict(result: dict[str, Any]) -> str:
    status = result.get("status")
    if status in {"missing_columns", "insufficient_data"}:
        return "INSUFFICIENT_DATA"
    supported = result.get("supported")
    p_value = result.get("p_value")
    test_stat = result.get("test_stat")
    direction = result.get("direction", "any")
    if supported is True:
        return "CONFIRMED"
    if p_value is not None and p_value < 0.05:
        if direction == "positive" and test_stat is not None and test_stat < 0:
            return "CONTRADICTED"
        if direction == "negative" and test_stat is not None and test_stat > 0:
            return "CONTRADICTED"
        return "REFINED"
    return "INSUFFICIENT_DATA"


def validate_hypotheses(features_df: pd.DataFrame) -> list[dict[str, Any]]:
    if features_df.empty or "label" not in features_df.columns:
        return [{
            "id": "H-BASE",
            "description": "Feature contract data is available for hypothesis validation",
            "verdict": "INSUFFICIENT_DATA",
            "evidence": "data/processed/features_base.csv missing or empty",
            "sample_size": 0,
        }]
    rows = []
    for result in test_hypotheses(features_df):
        verdict = _hypothesis_verdict(result)
        rows.append({
            **result,
            "verdict": verdict,
            "sample_size": int(len(features_df)),
            "evidence": (
                f"point_biserial r={result.get('test_stat')} p={result.get('p_value')}"
                if result.get("test") else result.get("status", "missing")
            ),
        })
    return rows


def compute_doc_metric_diffs(features_df: pd.DataFrame) -> list[dict[str, Any]]:
    required = {"map", "label", "is_attacker_a"}
    if features_df.empty or not required.issubset(features_df.columns):
        return []
    rows = []
    df = features_df.drop_duplicates("match_key") if "match_key" in features_df.columns else features_df
    for map_name, grp in df.groupby("map"):
        if map_name not in ATK_ADV_MAP:
            continue
        attack_wins = grp.apply(
            lambda row: int(row["label"]) if int(row.get("is_attacker_a", 0)) == 1 else 1 - int(row["label"]),
            axis=1,
        )
        if len(attack_wins) < 20:
            verdict = "INSUFFICIENT_DATA"
        else:
            observed = float(attack_wins.mean())
            expected = 0.5 + float(ATK_ADV_MAP.get(map_name, 0.0))
            delta = observed - expected
            verdict = "CONFIRMED" if abs(delta) <= 0.05 else "REFINED"
        observed = float(attack_wins.mean()) if len(attack_wins) else None
        expected = 0.5 + float(ATK_ADV_MAP.get(map_name, 0.0))
        rows.append({
            "metric": "attacker_win_rate_prior",
            "map": map_name,
            "doc_value": round(expected, 4),
            "observed_value": round(observed, 4) if observed is not None else None,
            "delta": round((observed - expected), 4) if observed is not None else None,
            "sample_size": int(len(attack_wins)),
            "source": "ml.agent_roles.ATK_ADV_MAP",
            "dataset_id": "data/processed/features_base.csv",
            "verdict": verdict,
        })
    return rows


def compare_sources(matches_df: pd.DataFrame, player_df: pd.DataFrame, vlr_matches_df: pd.DataFrame,
                    vlr_players_df: pd.DataFrame) -> dict[str, Any]:
    model_agents: set[str] = set()
    if not matches_df.empty:
        for col in ("agents_a", "agents_b"):
            if col in matches_df.columns:
                for value in matches_df[col].dropna().astype(str):
                    model_agents.update(a for a in value.split("|") if a)
    vlr_agents = set(vlr_players_df.get("agent", pd.Series(dtype=str)).dropna().astype(str)) if not vlr_players_df.empty else set()
    top_vlr_agents = []
    if not vlr_players_df.empty and "agent" in vlr_players_df.columns:
        top_vlr_agents = [
            {"agent": agent, "rows": int(count)}
            for agent, count in Counter(vlr_players_df["agent"].dropna().astype(str)).most_common(15)
            if agent
        ]
    return {
        "model_match_rows": int(len(matches_df)),
        "model_player_cache_rows": int(len(player_df)) if not player_df.empty else 0,
        "vlr_match_rows": int(len(vlr_matches_df)),
        "vlr_player_rows": int(len(vlr_players_df)),
        "shared_agents": sorted(model_agents & vlr_agents),
        "vlr_only_agents": sorted(vlr_agents - model_agents),
        "model_only_agents": sorted(model_agents - vlr_agents),
        "top_vlr_agents": top_vlr_agents,
    }


def _summarize_column_values(df: pd.DataFrame, column: str, limit: int = 5) -> str:
    if df.empty or column not in df.columns:
        return ""
    values = [str(value).strip() for value in df[column].dropna().astype(str) if str(value).strip()]
    return "|".join(sorted(set(values))[:limit])


def _value_counts(df: pd.DataFrame, column: str) -> dict[str, int]:
    if df.empty or column not in df.columns:
        return {}
    return {
        str(value): int(count)
        for value, count in df[column].dropna().astype(str).value_counts().to_dict().items()
        if str(value).strip()
    }


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value


def _representative_row(df: pd.DataFrame, dataset_id: str, path: str) -> dict[str, Any]:
    if df.empty:
        return {
            "dataset_id": dataset_id,
            "source_url": path,
            "retrieval_method": "local_file",
            "fact": "no rows available",
        }
    row = df.iloc[0]
    source_url = (
        str(row.get("source_url", "") or "").strip()
        or str(row.get("source_path", "") or "").strip()
        or path
    )
    retrieval_method = (
        str(row.get("retrieval_method", "") or "").strip()
        or ("local_raw_normalization" if str(dataset_id).startswith("research_") else "local_file")
    )
    fact_keys = [
        "match_id", "game_id", "map", "team", "player", "agent", "event",
        "event_id", "team_id", "comp_key", "action",
    ]
    fact = {
        key: _json_safe(row.get(key))
        for key in fact_keys
        if key in df.columns and str(row.get(key, "")).strip()
    }
    return {
        "dataset_id": dataset_id,
        "source_url": source_url,
        "retrieval_method": retrieval_method,
        "fact": fact or "row present",
    }


def summarize_additional_collection(
    processed_dir: Path,
    reports_dir: Path,
    ingestion: dict[str, Any],
) -> dict[str, Any]:
    inventory = _read_json(reports_dir / "research_source_inventory.json")
    datasets: dict[str, Any] = {}
    for name, rel_path, group in ADDITIONAL_DATASETS:
        path = Path(rel_path)
        df = _read_csv(processed_dir / path.name)
        datasets[name] = {
            "group": group,
            "path": rel_path,
            "rows": int(len(df)),
            "source_coverage": {
                "source": _value_counts(df, "source"),
                "retrieval_method": _value_counts(df, "retrieval_method"),
                "dataset_id": _value_counts(df, "dataset_id"),
                "source_path": _value_counts(df, "source_path"),
            },
            "representative_fact": _representative_row(df, name, rel_path),
        }

    collection_stages = ingestion.get("collection_stages", {}) if isinstance(ingestion, dict) else {}
    degraded_stages = [
        {"stage": name, "failure_reason": row.get("failure_reason", "")}
        for name, row in collection_stages.items()
        if isinstance(row, dict) and row.get("status") == "degraded"
    ]
    source_errors = [
        row for row in inventory.get("source_inventory", [])
        if isinstance(row, dict) and row.get("error")
    ] if isinstance(inventory, dict) else []
    return {
        "generated_at": _utc_now(),
        "datasets": datasets,
        "row_counts": {name: int(info["rows"]) for name, info in datasets.items()},
        "degraded_stages": degraded_stages,
        "local_source_errors": source_errors,
        "local_inventory": inventory,
    }


def _fact(
    *,
    fact_id: str,
    topic: str,
    metric: str,
    value: Any,
    unit: str,
    sample_size: int,
    dataset_id: str,
    source_url: str,
    fetched_at: str,
    retrieval_method: str,
    verdict: str,
    doc_targets: list[str],
    details: Any | None = None,
) -> dict[str, Any]:
    row = {
        "fact_id": fact_id,
        "topic": topic,
        "metric": metric,
        "value": value,
        "unit": unit,
        "sample_size": int(sample_size),
        "dataset_id": dataset_id,
        "source_url": source_url,
        "fetched_at": fetched_at,
        "retrieval_method": retrieval_method,
        "verdict": verdict,
        "doc_targets": doc_targets,
    }
    if details is not None:
        row["details"] = details
    return row


def validate_report_facts(facts: list[dict[str, Any]]) -> None:
    for row in facts:
        missing = [field for field in REQUIRED_FACT_FIELDS if field not in row]
        if missing:
            raise ValueError(f"report fact {row.get('fact_id', '<unknown>')} missing fields: {missing}")
        empty = [
            field for field in REQUIRED_FACT_FIELDS
            if field not in {"value", "sample_size", "doc_targets"}
            and str(row.get(field, "")).strip() == ""
        ]
        if empty:
            raise ValueError(f"report fact {row.get('fact_id', '<unknown>')} has empty fields: {empty}")
        if row["verdict"] not in VERDICTS:
            raise ValueError(f"report fact {row['fact_id']} has invalid verdict: {row['verdict']}")
        if not isinstance(row["doc_targets"], list) or not row["doc_targets"]:
            raise ValueError(f"report fact {row['fact_id']} needs at least one doc target")


def build_report_facts(
    coverage: dict[str, Any],
    ingestion: dict[str, Any],
    comparisons: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    doc_diffs: list[dict[str, Any]],
    vlr_matches_df: pd.DataFrame,
    vlr_players_df: pd.DataFrame,
    additional_collection: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    fetched_at = str(ingestion.get("generated_at") or ingestion.get("robots_checked_at") or _utc_now())
    retrieval_method = ",".join(sorted((ingestion.get("retrieval_methods") or {}).keys())) or "local_report"
    vlr_match_dataset = "data/processed/vlrgg_matches.csv"
    vlr_player_dataset = "data/processed/vlrgg_player_stats.csv"
    features_dataset = "data/processed/features_base.csv"
    match_source_url = _summarize_column_values(vlr_matches_df, "source_url") or "reports/vlrgg_ingestion_summary.json"
    player_source_url = _summarize_column_values(vlr_players_df, "source_url") or "reports/vlrgg_ingestion_summary.json"

    source_rows = coverage.get("sources", {}) if isinstance(coverage, dict) else {}
    model_contract = source_rows.get("processed_model_contract", {}) if isinstance(source_rows, dict) else {}
    active_feature_count = model_contract.get("active_feature_count")

    facts = [
        _fact(
            fact_id="FACT-VLR-INGESTION-MATCHES",
            topic="coverage",
            metric="vlrgg_match_rows",
            value=int(len(vlr_matches_df)),
            unit="rows",
            sample_size=int(len(vlr_matches_df)),
            dataset_id=vlr_match_dataset,
            source_url=match_source_url,
            fetched_at=fetched_at,
            retrieval_method=retrieval_method,
            verdict="CONFIRMED" if len(vlr_matches_df) else "INSUFFICIENT_DATA",
            doc_targets=["docs/10_valorant/sources.md", "docs/10_valorant/scraping_research.md"],
        ),
        _fact(
            fact_id="FACT-VLR-INGESTION-PLAYERS",
            topic="coverage",
            metric="vlrgg_player_stat_rows",
            value=int(len(vlr_players_df)),
            unit="rows",
            sample_size=int(len(vlr_players_df)),
            dataset_id=vlr_player_dataset,
            source_url=player_source_url,
            fetched_at=fetched_at,
            retrieval_method=retrieval_method,
            verdict="CONFIRMED" if len(vlr_players_df) else "INSUFFICIENT_DATA",
            doc_targets=["docs/10_valorant/agents.md", "docs/10_valorant/meta.md"],
        ),
        _fact(
            fact_id="FACT-VLR-COLLECTION-NETWORK",
            topic="collection_policy",
            metric="network_requests",
            value=int(ingestion.get("network_requests", 0)),
            unit="requests",
            sample_size=int(len(vlr_matches_df) + len(vlr_players_df)),
            dataset_id="reports/vlrgg_ingestion_summary.json",
            source_url=str(ingestion.get("robots_url") or "https://www.vlr.gg/robots.txt"),
            fetched_at=fetched_at,
            retrieval_method=str(ingestion.get("mode") or "local_report"),
            verdict="CONFIRMED",
            doc_targets=["docs/10_valorant/scraping_research.md", "docs/10_valorant/sources.md"],
            details={
                "direct_html_allowed": bool(ingestion.get("direct_html_allowed", False)),
                "allowed_paths": ingestion.get("allowed_paths", []),
                "blocked_paths": ingestion.get("blocked_paths", []),
            },
        ),
        _fact(
            fact_id="FACT-MODEL-FEATURE-CONTRACT",
            topic="model_scope",
            metric="active_model_feature_count",
            value=int(active_feature_count) if active_feature_count is not None else 0,
            unit="features",
            sample_size=int(model_contract.get("rows", 0) or 0),
            dataset_id=str(model_contract.get("path") or features_dataset),
            source_url="reports/preprocess_summary.json",
            fetched_at=fetched_at,
            retrieval_method="processed_report",
            verdict="CONFIRMED" if active_feature_count else "INSUFFICIENT_DATA",
            doc_targets=["docs/10_valorant/sources.md", "docs/10_valorant/scraping_research.md"],
        ),
        _fact(
            fact_id="FACT-VLR-SHARED-AGENTS",
            topic="agents",
            metric="shared_agent_count",
            value=len(comparisons.get("shared_agents", [])),
            unit="agents",
            sample_size=int(len(vlr_players_df)),
            dataset_id=vlr_player_dataset,
            source_url=player_source_url,
            fetched_at=fetched_at,
            retrieval_method=retrieval_method,
            verdict="CONFIRMED" if comparisons.get("shared_agents") else "INSUFFICIENT_DATA",
            doc_targets=["docs/10_valorant/agents.md", "docs/10_valorant/meta.md"],
            details={"agents": comparisons.get("shared_agents", [])},
        ),
        _fact(
            fact_id="FACT-VLR-ONLY-AGENTS",
            topic="agents",
            metric="vlr_only_agent_count",
            value=len(comparisons.get("vlr_only_agents", [])),
            unit="agents",
            sample_size=int(len(vlr_players_df)),
            dataset_id=vlr_player_dataset,
            source_url=player_source_url,
            fetched_at=fetched_at,
            retrieval_method=retrieval_method,
            verdict="REFINED" if comparisons.get("vlr_only_agents") else "CONFIRMED",
            doc_targets=["docs/10_valorant/agents.md", "docs/10_valorant/meta.md"],
            details={"agents": comparisons.get("vlr_only_agents", [])},
        ),
    ]

    for idx, row in enumerate(comparisons.get("top_vlr_agents", [])[:5], start=1):
        agent = row.get("agent", "")
        agent_df = vlr_players_df[vlr_players_df["agent"].astype(str) == str(agent)] if "agent" in vlr_players_df.columns else pd.DataFrame()
        facts.append(_fact(
            fact_id=f"FACT-VLR-TOP-AGENT-{idx:02d}",
            topic="agents",
            metric="vlr_player_rows_by_agent",
            value=int(row.get("rows", 0) or 0),
            unit="rows",
            sample_size=int(len(vlr_players_df)),
            dataset_id=vlr_player_dataset,
            source_url=_summarize_column_values(agent_df, "source_url") or player_source_url,
            fetched_at=fetched_at,
            retrieval_method=_summarize_column_values(agent_df, "retrieval_method") or retrieval_method,
            verdict="CONFIRMED",
            doc_targets=["docs/10_valorant/agents.md", "docs/10_valorant/meta.md"],
            details={"agent": agent},
        ))

    for row in hypotheses:
        if row.get("verdict") in {"CONTRADICTED", "REFINED"}:
            facts.append(_fact(
                fact_id=f"FACT-HYP-{row.get('id')}",
                topic="hypotheses",
                metric=str(row.get("id", "hypothesis")),
                value=row.get("test_stat"),
                unit=str(row.get("test") or "test_stat"),
                sample_size=int(row.get("sample_size", 0) or 0),
                dataset_id=features_dataset,
                source_url="reports/research_validation.json",
                fetched_at=fetched_at,
                retrieval_method="processed_report",
                verdict=str(row.get("verdict")),
                doc_targets=["docs/10_valorant/agents.md", "docs/10_valorant/meta.md"],
                details={"description": row.get("description"), "p_value": row.get("p_value")},
            ))

    for idx, row in enumerate(doc_diffs, start=1):
        facts.append(_fact(
            fact_id=f"FACT-DOC-DIFF-{idx:02d}",
            topic="doc_metric_diffs",
            metric=str(row.get("metric", "doc_metric")),
            value=row.get("observed_value"),
            unit="rate",
            sample_size=int(row.get("sample_size", 0) or 0),
            dataset_id=str(row.get("dataset_id") or features_dataset),
            source_url=str(row.get("source") or "reports/research_validation.json"),
            fetched_at=fetched_at,
            retrieval_method="processed_report",
            verdict=str(row.get("verdict")),
            doc_targets=["docs/10_valorant/maps.md"],
            details=row,
        ))

    for name, info in (additional_collection or {}).get("datasets", {}).items():
        representative = info.get("representative_fact", {}) if isinstance(info, dict) else {}
        group = str(info.get("group", "additional_collection")) if isinstance(info, dict) else "additional_collection"
        facts.append(_fact(
            fact_id=f"FACT-ADDITIONAL-{name.upper().replace('_', '-')}",
            topic=group,
            metric=f"{name}_rows",
            value=int(info.get("rows", 0) or 0) if isinstance(info, dict) else 0,
            unit="rows",
            sample_size=int(info.get("rows", 0) or 0) if isinstance(info, dict) else 0,
            dataset_id=str(info.get("path") or f"data/processed/{name}.csv") if isinstance(info, dict) else f"data/processed/{name}.csv",
            source_url=str(representative.get("source_url") or info.get("path") or f"data/processed/{name}.csv"),
            fetched_at=fetched_at,
            retrieval_method=str(representative.get("retrieval_method") or "local_report"),
            verdict="CONFIRMED" if isinstance(info, dict) and int(info.get("rows", 0) or 0) else "INSUFFICIENT_DATA",
            doc_targets=["docs/10_valorant/data_inventory.md", "docs/10_valorant/scraping_research.md"],
            details={
                "group": group,
                "source_coverage": info.get("source_coverage", {}) if isinstance(info, dict) else {},
                "representative_fact": representative,
            },
        ))

    validate_report_facts(facts)
    return facts


def build_report(processed_dir: Path, reports_dir: Path) -> dict[str, Any]:
    features_df = _read_csv(processed_dir / "features_base.csv")
    matches_df = _read_csv(processed_dir / "matches_clean.csv")
    player_stats_json = _read_json(processed_dir / "player_stats.json")
    player_cache_df = pd.DataFrame.from_dict(player_stats_json, orient="index") if player_stats_json else pd.DataFrame()
    vlr_matches_df = _read_csv(processed_dir / "vlrgg_matches.csv")
    vlr_players_df = _read_csv(processed_dir / "vlrgg_player_stats.csv")
    coverage = _read_json(reports_dir / "data_source_coverage.json")
    ingestion = _read_json(reports_dir / "vlrgg_ingestion_summary.json")
    additional_collection = summarize_additional_collection(processed_dir, reports_dir, ingestion)

    hypotheses = validate_hypotheses(features_df)
    doc_diffs = compute_doc_metric_diffs(features_df)
    comparisons = compare_sources(matches_df, player_cache_df, vlr_matches_df, vlr_players_df)
    report_facts = build_report_facts(
        coverage,
        ingestion,
        comparisons,
        hypotheses,
        doc_diffs,
        vlr_matches_df,
        vlr_players_df,
        additional_collection,
    )
    all_verdicts = [row.get("verdict") for row in hypotheses + doc_diffs if row.get("verdict") in VERDICTS]
    fact_verdicts = [row.get("verdict") for row in report_facts if row.get("verdict") in VERDICTS]
    verdict_counts = {verdict: int(all_verdicts.count(verdict)) for verdict in VERDICTS}
    fact_verdict_counts = {verdict: int(fact_verdicts.count(verdict)) for verdict in VERDICTS}

    return {
        "generated_at": _utc_now(),
        "inputs": {
            "features_base": str(processed_dir / "features_base.csv"),
            "matches_clean": str(processed_dir / "matches_clean.csv"),
            "vlrgg_matches": str(processed_dir / "vlrgg_matches.csv"),
            "vlrgg_player_stats": str(processed_dir / "vlrgg_player_stats.csv"),
            "coverage_report": str(reports_dir / "data_source_coverage.json"),
            "ingestion_report": str(reports_dir / "vlrgg_ingestion_summary.json"),
            "local_research_inventory": str(reports_dir / "research_source_inventory.json"),
        },
        "summary": {
            "verdict_counts": verdict_counts,
            "fact_verdict_counts": fact_verdict_counts,
            "feature_contract_unchanged": True,
            "active_model_feature_scope": "P1-P4 current contract",
        },
        "coverage": coverage,
        "vlr_ingestion": ingestion,
        "hypotheses": hypotheses,
        "doc_metric_diffs": doc_diffs,
        "report_facts": report_facts,
        "data_comparisons": comparisons,
        "additional_collection": additional_collection,
    }


def run(args: argparse.Namespace) -> None:
    processed_dir = Path(args.processed)
    reports_dir = Path(args.reports)
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(processed_dir, reports_dir)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        "research_validation written: "
        f"{output} verdicts={report['summary']['verdict_counts']}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Valorant research claims against local reports")
    parser.add_argument("--processed", default="data/processed")
    parser.add_argument("--reports", default="reports")
    parser.add_argument("--output", default="reports/research_validation.json")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
