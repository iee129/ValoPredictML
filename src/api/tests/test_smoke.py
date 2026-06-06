from pathlib import Path

import pytest

from ml.baseline.reference import metrics_payload

pytestmark = pytest.mark.filterwarnings(
    "ignore:Using `httpx` with `starlette.testclient` is deprecated"
)


def test_baseline_reference_is_locked_to_midterm_pdf() -> None:
    payload = metrics_payload("2026-06-06T00:00:00+00:00")

    assert payload["source_kind"] == "midterm_pdf_reference"
    assert payload["test_auc"] == 0.5943
    assert payload["test_acc"] == 0.5667
    assert payload["test_f1"] == 0.6072
    assert payload["n_features"] == 421
    assert any("중간발표" in path for path in payload["source_artifacts"])


def test_fastapi_core_smoke_with_local_model() -> None:
    required = [
        Path("models/advanced/ensemble.joblib"),
        Path("models/advanced/meta.json"),
        Path("data/processed/matches.csv"),
        Path("data/processed/players.csv"),
        Path("data/processed/advanced/test.csv"),
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        pytest.skip(f"local model/data artifacts are not committed: {missing}")

    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    expected_gets = {
        "/health": 200,
        "/options": 200,
        "/model": 200,
        "/replay/matches": 200,
        "/history": 503,
        "/history/does-not-exist": 503,
    }
    for path, expected_status in expected_gets.items():
        assert client.get(path).status_code == expected_status

    payload = {
        "map": "Ascent",
        "cutoff_year": 2026,
        "team_a": [
            {"player": "something", "agent": "Jett"},
            {"player": "nAts", "agent": "Cypher"},
            {"player": "Boaster", "agent": "Omen"},
            {"player": "Less", "agent": "Viper"},
            {"player": "Chronicle", "agent": "Sova"},
        ],
        "team_b": [
            {"player": "aspas", "agent": "Raze"},
            {"player": "kiNgg", "agent": "Killjoy"},
            {"player": "cauanzin", "agent": "Fade"},
            {"player": "Mako", "agent": "Astra"},
            {"player": "Alfajer", "agent": "KAY/O"},
        ],
    }
    response = client.post("/predict", json=payload)

    assert response.status_code == 200
    assert client.get("/health").json()["model_loaded"] is True
    assert client.get("/model").json()["n_features"] == 179
