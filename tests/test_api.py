"""API response structure tests."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.api.workspace import clear_workspace_state
from app.config import get_settings
from app.db.session import reset_engine_and_session
from app.main import app
from app.schemas import AnalyzeResponse


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "api_test.sqlite"))
    monkeypatch.setenv("REGISTRY_PATH", str(tmp_path / "api_source_registry.duckdb"))
    get_settings.cache_clear()
    reset_engine_and_session()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()
    reset_engine_and_session()


@pytest.fixture(autouse=True)
def reset_workspace_state() -> None:
    clear_workspace_state()
    yield
    clear_workspace_state()


def test_analyze_response_accepts_skipped_trace() -> None:
    """execute_plan_node emits skipped when there is no plan; API must still serialize."""
    resp = AnalyzeResponse(
        analysis="Planner failed; no execution.",
        trace=[
            {
                "step": "execute_plan_node",
                "status": "skipped",
                "details": {"reason": "no compiled plan"},
            }
        ],
        executed_steps=[],
        errors=[],
    )
    assert resp.trace[0].status == "skipped"


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_sample_questions_endpoint(client: TestClient) -> None:
    response = client.get("/sample-questions")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["questions"]) >= 3


def test_analyze_endpoint_structure(client: TestClient) -> None:
    def fake_run_analysis(query: str, source_ids=None) -> dict:  # noqa: ARG001
        return {
            "analysis": "## Summary\nPipeline velocity improved.\n",
            "trace": [{"step": "planner_compiled_node", "status": "completed", "details": {"objective": "x"}}],
            "executed_steps": [
                {
                    "id": "step_1",
                    "kind": "sql",
                    "purpose": "Compare current and previous velocity.",
                    "code": "SELECT 1",
                    "output_alias": "comparison_result",
                    "attempt": 1,
                    "status": "success",
                    "artifact": {
                        "alias": "comparison_result",
                        "artifact_type": "table",
                        "row_count": 1,
                        "columns": ["value"],
                        "preview_rows": [{"value": 1}],
                        "summary": {},
                    },
                    "error": None,
                }
            ],
            "errors": [],
        }

    app.dependency_overrides = {}
    import app.services.analysis_run as analysis_run

    original = analysis_run.run_analysis
    analysis_run.run_analysis = fake_run_analysis
    try:
        upload_response = client.post(
            "/uploads",
            files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\nwon,25\n"), "text/csv")},
        )
        source_id = upload_response.json()["asset"]["id"]
        response = client.post("/analyze", json={"query": "Why did pipeline velocity drop this week?", "source_ids": [source_id]})
    finally:
        analysis_run.run_analysis = original
    assert response.status_code == 200
    payload = response.json()
    assert {"analysis", "trace", "executed_steps", "errors", "inspection_id"} <= payload.keys()
    assert isinstance(payload["trace"], list)
    assert isinstance(payload["executed_steps"], list)
    assert isinstance(payload["analysis"], str)
    assert isinstance(payload["inspection_id"], str)


def test_analyze_endpoint_returns_http_500_on_failure(client: TestClient) -> None:
    def fake_run_analysis(query: str, source_ids=None) -> dict:  # noqa: ARG001
        raise RuntimeError("planner exploded")

    import app.services.analysis_run as analysis_run

    original = analysis_run.run_analysis
    analysis_run.run_analysis = fake_run_analysis
    try:
        upload_response = client.post(
            "/uploads",
            files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\nwon,25\n"), "text/csv")},
        )
        source_id = upload_response.json()["asset"]["id"]
        response = client.post("/analyze", json={"query": "Why did pipeline velocity drop this week?", "source_ids": [source_id]})
    finally:
        analysis_run.run_analysis = original

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"]["message"] == "The analysis could not complete successfully. Inspect the server logs and retry."
    assert payload["detail"]["error"] == "planner exploded"


def test_upload_endpoint_profiles_csv(client: TestClient) -> None:
    response = client.post(
        "/uploads",
        files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\nwon,25\n"), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback"] is False
    assert payload["asset"]["name"] == "pipeline.csv"
    assert payload["asset"]["type"] == "CSV"
    assert payload["asset"]["rows"] == 2
    assert payload["asset"]["columns"] == 2
    assert payload["asset"]["status"] == "verified"
    assert payload["asset"]["relationCount"] == 1
    assert payload["asset"]["primaryRelationName"]


def test_upload_endpoint_profiles_json(client: TestClient) -> None:
    response = client.post(
        "/uploads",
        files={
            "file": (
                "orders.json",
                BytesIO(
                    b'[{"order_id":"o1","customer":{"name":"Ada"},"items":[{"sku":"A1","qty":2}]}]'
                ),
                "application/json",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"]["type"] == "JSON"
    assert payload["asset"]["rows"] == 1
    assert payload["asset"]["relationCount"] == 2
    assert payload["asset"]["primaryRelationName"]


def test_upload_endpoint_rejects_unsupported_file_types(client: TestClient) -> None:
    response = client.post(
        "/uploads",
        files={"file": ("pipeline.tsv", BytesIO(b"stage\tamount\nopen\t10\n"), "text/tab-separated-values")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Only CSV and JSON uploads are currently supported."


def test_inspection_endpoint_returns_stored_inspection(client: TestClient) -> None:
    def fake_run_analysis(query: str, source_ids=None) -> dict:  # noqa: ARG001
        return {
            "analysis": "## Summary\nPipeline velocity improved.\n",
            "trace": [{"step": "planner_compiled_node", "status": "completed", "details": {"objective": "x"}}],
            "executed_steps": [
                {
                    "id": "step_1",
                    "kind": "sql",
                    "purpose": "Compare current and previous velocity.",
                    "code": "SELECT segment, 1 AS value FROM opportunities_enriched",
                    "output_alias": "comparison_result",
                    "attempt": 1,
                    "status": "success",
                    "artifact": {
                        "alias": "comparison_result",
                        "artifact_type": "table",
                        "row_count": 1,
                        "columns": ["segment", "value"],
                        "preview_rows": [{"segment": "SMB", "value": 1}],
                        "summary": {},
                    },
                    "error": None,
                }
            ],
            "errors": [],
        }

    import app.services.analysis_run as analysis_run

    original = analysis_run.run_analysis
    analysis_run.run_analysis = fake_run_analysis
    try:
        upload_response = client.post(
            "/uploads",
            files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\nwon,25\n"), "text/csv")},
        )
        source_id = upload_response.json()["asset"]["id"]
        analyze_response = client.post(
            "/analyze",
            json={"query": "Why did pipeline velocity drop this week?", "source_ids": [source_id]},
        )
    finally:
        analysis_run.run_analysis = original

    inspection_id = analyze_response.json()["inspection_id"]
    response = client.get(f"/inspections/{inspection_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback"] is False
    assert payload["inspection"]["id"] == inspection_id
    assert payload["inspection"]["results"]["columns"] == ["segment", "value"]
    assert payload["inspection"]["trace"][0]["label"] == "Query Planning"


def test_inspection_endpoint_returns_404_for_unknown_id(client: TestClient) -> None:
    response = client.get("/inspections/inspect_missing")
    assert response.status_code == 404
    assert response.json()["detail"]["message"] == "Inspection not found."


def test_analyze_endpoint_forwards_source_ids(client: TestClient) -> None:
    captured: dict[str, object] = {}

    def fake_run_analysis(query: str, source_ids=None) -> dict:
        captured["query"] = query
        captured["source_ids"] = source_ids
        return {
            "analysis": "## Summary\nScoped analysis.\n",
            "trace": [],
            "executed_steps": [],
            "errors": [],
        }

    import app.services.analysis_run as analysis_run

    original = analysis_run.run_analysis
    analysis_run.run_analysis = fake_run_analysis
    try:
        upload_response = client.post(
            "/uploads",
            files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\nwon,25\n"), "text/csv")},
        )
        source_id = upload_response.json()["asset"]["id"]
        response = client.post("/analyze", json={"query": "Use this upload", "source_ids": [source_id]})
    finally:
        analysis_run.run_analysis = original

    assert response.status_code == 200
    assert captured["query"] == "Use this upload"
    assert captured["source_ids"] == [source_id]


def test_analyze_endpoint_requires_uploaded_source_before_run_analysis(client: TestClient) -> None:
    import app.services.analysis_run as analysis_run

    called = False
    original = analysis_run.run_analysis

    def fake_run_analysis(query: str, source_ids=None) -> dict:
        nonlocal called
        called = True
        return {"analysis": "", "trace": [], "executed_steps": [], "errors": []}

    analysis_run.run_analysis = fake_run_analysis
    try:
        response = client.post("/analyze", json={"query": "Why did pipeline velocity drop this week?"})
    finally:
        analysis_run.run_analysis = original

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Upload and attach at least one CSV or JSON data source before running analysis."
    assert called is False
