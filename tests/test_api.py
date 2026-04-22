"""API response structure tests."""

from io import BytesIO
import sqlite3

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
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(tmp_path / "uploads"))
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


def _signup(client: TestClient, email: str, password: str = "password123") -> str:
    response = client.post("/auth/signup", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


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
            "runtime_ms": 7,
        }

    app.dependency_overrides = {}
    import app.services.analysis_run as analysis_run

    original = analysis_run.run_analysis
    analysis_run.run_analysis = fake_run_analysis
    try:
        token = _signup(client, "analyze-structure@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        upload_response = client.post(
            "/uploads",
            files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\nwon,25\n"), "text/csv")},
            headers=headers,
        )
        source_id = upload_response.json()["asset"]["id"]
        response = client.post(
            "/analyze",
            json={"query": "Why did pipeline velocity drop this week?", "source_ids": [source_id]},
            headers=headers,
        )
    finally:
        analysis_run.run_analysis = original
    assert response.status_code == 200
    payload = response.json()
    assert {"analysis", "trace", "executed_steps", "errors", "inspection_id", "runtime_ms"} <= payload.keys()
    assert isinstance(payload["trace"], list)
    assert isinstance(payload["executed_steps"], list)
    assert isinstance(payload["analysis"], str)
    assert isinstance(payload["inspection_id"], str)
    assert payload["runtime_ms"] == 7


def test_analyze_endpoint_returns_http_500_on_failure(client: TestClient) -> None:
    def fake_run_analysis(query: str, source_ids=None) -> dict:  # noqa: ARG001
        raise RuntimeError("planner exploded")

    import app.services.analysis_run as analysis_run

    original = analysis_run.run_analysis
    analysis_run.run_analysis = fake_run_analysis
    try:
        token = _signup(client, "analyze-failure@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        upload_response = client.post(
            "/uploads",
            files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\nwon,25\n"), "text/csv")},
            headers=headers,
        )
        source_id = upload_response.json()["asset"]["id"]
        response = client.post(
            "/analyze",
            json={"query": "Why did pipeline velocity drop this week?", "source_ids": [source_id]},
            headers=headers,
        )
    finally:
        analysis_run.run_analysis = original

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"]["message"] == "The analysis could not complete successfully. Inspect the server logs and retry."
    assert payload["detail"]["error"] == "planner exploded"


def test_upload_endpoint_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/uploads",
        files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\n"), "text/csv")},
    )

    assert response.status_code == 401


def test_upload_endpoint_profiles_csv(client: TestClient, tmp_path) -> None:
    token = _signup(client, "upload-csv@example.com")
    response = client.post(
        "/uploads",
        files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\nwon,25\n"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
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
    assert any((tmp_path / "uploads").rglob("original.csv"))

    uploads_response = client.get("/uploads", headers={"Authorization": f"Bearer {token}"})
    assert uploads_response.status_code == 200
    assert [asset["id"] for asset in uploads_response.json()] == [payload["asset"]["id"]]


def test_upload_endpoint_profiles_json(client: TestClient) -> None:
    token = _signup(client, "upload-json@example.com")
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
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"]["type"] == "JSON"
    assert payload["asset"]["rows"] == 1
    assert payload["asset"]["relationCount"] == 2
    assert payload["asset"]["primaryRelationName"]


def test_upload_endpoint_profiles_tsv(client: TestClient) -> None:
    token = _signup(client, "upload-tsv@example.com")
    response = client.post(
        "/uploads",
        files={"file": ("pipeline.tsv", BytesIO(b"stage\tamount\nopen\t10\nwon\t25\n"), "text/tab-separated-values")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"]["type"] == "TSV"
    assert payload["asset"]["rows"] == 2
    assert payload["asset"]["columns"] == 2
    assert payload["asset"]["relationCount"] == 1


def test_upload_endpoint_rejects_unsupported_file_types(client: TestClient) -> None:
    token = _signup(client, "upload-unsupported@example.com")
    response = client.post(
        "/uploads",
        files={"file": ("pipeline.txt", BytesIO(b"stage amount\nopen 10\n"), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Only CSV, TSV, and JSON uploads are currently supported."


def test_upload_endpoint_migrates_legacy_uploads_table(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "legacy_uploads.sqlite"
    registry_path = tmp_path / "legacy_registry.duckdb"
    upload_dir = tmp_path / "uploads"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE uploads (
            id INTEGER NOT NULL PRIMARY KEY,
            upload_id VARCHAR(64) NOT NULL,
            user_id INTEGER NOT NULL,
            source_id VARCHAR(64) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            file_type VARCHAR(32) NOT NULL,
            storage_path VARCHAR(1024) NOT NULL,
            content_type VARCHAR(255),
            size_bytes BIGINT NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL,
            rows INTEGER,
            columns INTEGER,
            relation_count INTEGER,
            primary_relation_name VARCHAR(255),
            summary TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO uploads (
            id, upload_id, user_id, source_id, original_filename, file_type, storage_path, content_type,
            size_bytes, content_hash, status, rows, columns, relation_count, primary_relation_name, summary,
            created_at, updated_at
        ) VALUES (
            1, 'legacy_upload_1', 999, 'legacy_source_1', 'legacy.csv', 'CSV', '/tmp/legacy.csv', 'text/csv',
            12, 'abc123', 'verified', 1, 2, 1, 'legacy_relation', 'legacy summary',
            '2026-04-01 12:00:00', '2026-04-01 12:00:00'
        )
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(upload_dir))
    get_settings.cache_clear()
    reset_engine_and_session()

    try:
        with TestClient(app) as legacy_client:
            token = _signup(legacy_client, "legacy-migration@example.com")
            response = legacy_client.post(
                "/uploads",
                files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\n"), "text/csv")},
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200, response.text

            uploads_response = legacy_client.get("/uploads", headers={"Authorization": f"Bearer {token}"})
            assert uploads_response.status_code == 200
            assert len(uploads_response.json()) == 1
    finally:
        get_settings.cache_clear()
        reset_engine_and_session()

    migrated_conn = sqlite3.connect(db_path)
    columns = [row[1] for row in migrated_conn.execute("PRAGMA table_info(uploads)").fetchall()]
    source_ids = [row[0] for row in migrated_conn.execute("SELECT source_id FROM uploads ORDER BY source_id").fetchall()]
    migrated_conn.close()

    assert "upload_id" not in columns
    assert "file_type" not in columns
    assert "source_id" in columns
    assert source_ids == ["legacy_source_1", uploads_response.json()[0]["id"]]


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
        token = _signup(client, "inspection@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        upload_response = client.post(
            "/uploads",
            files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\nwon,25\n"), "text/csv")},
            headers=headers,
        )
        source_id = upload_response.json()["asset"]["id"]
        analyze_response = client.post(
            "/analyze",
            json={"query": "Why did pipeline velocity drop this week?", "source_ids": [source_id]},
            headers=headers,
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
        token = _signup(client, "analyze-forward@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        upload_response = client.post(
            "/uploads",
            files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\nwon,25\n"), "text/csv")},
            headers=headers,
        )
        source_id = upload_response.json()["asset"]["id"]
        response = client.post("/analyze", json={"query": "Use this upload", "source_ids": [source_id]}, headers=headers)
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
        token = _signup(client, "analyze-requires-upload@example.com")
        response = client.post(
            "/analyze",
            json={"query": "Why did pipeline velocity drop this week?"},
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        analysis_run.run_analysis = original

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Upload and attach at least one CSV or JSON data source before running analysis."
    assert called is False


def test_uploads_and_analysis_are_scoped_to_the_signed_in_user(client: TestClient) -> None:
    owner = _signup(client, "owner-uploads@example.com")
    intruder = _signup(client, "intruder-uploads@example.com")
    owner_headers = {"Authorization": f"Bearer {owner}"}
    intruder_headers = {"Authorization": f"Bearer {intruder}"}

    upload_response = client.post(
        "/uploads",
        files={"file": ("pipeline.csv", BytesIO(b"stage,amount\nopen,10\nwon,25\n"), "text/csv")},
        headers=owner_headers,
    )
    source_id = upload_response.json()["asset"]["id"]

    owner_list = client.get("/uploads", headers=owner_headers)
    intruder_list = client.get("/uploads", headers=intruder_headers)

    assert [asset["id"] for asset in owner_list.json()] == [source_id]
    assert intruder_list.json() == []

    import app.services.analysis_run as analysis_run

    called = False
    original = analysis_run.run_analysis

    def fake_run_analysis(query: str, source_ids=None) -> dict:
        nonlocal called
        called = True
        return {"analysis": "", "trace": [], "executed_steps": [], "errors": []}

    analysis_run.run_analysis = fake_run_analysis
    try:
        forbidden = client.post(
            "/analyze",
            json={"query": "Use someone else's upload", "source_ids": [source_id]},
            headers=intruder_headers,
        )
    finally:
        analysis_run.run_analysis = original

    assert forbidden.status_code == 400
    assert forbidden.json()["detail"]["message"] == "Attach a valid uploaded data source before running analysis."
    assert called is False


def test_delete_upload_removes_file_and_listing(client: TestClient, tmp_path) -> None:
    owner = _signup(client, "delete-owner@example.com")
    intruder = _signup(client, "delete-intruder@example.com")
    owner_headers = {"Authorization": f"Bearer {owner}"}
    intruder_headers = {"Authorization": f"Bearer {intruder}"}

    upload_response = client.post(
        "/uploads",
        files={"file": ("orders.json", BytesIO(b'[{"order_id":"o1"}]'), "application/json")},
        headers=owner_headers,
    )
    source_id = upload_response.json()["asset"]["id"]

    forbidden = client.delete(f"/uploads/{source_id}", headers=intruder_headers)
    assert forbidden.status_code == 404

    delete_response = client.delete(f"/uploads/{source_id}", headers=owner_headers)
    assert delete_response.status_code == 204
    assert client.get("/uploads", headers=owner_headers).json() == []
    assert not any((tmp_path / "uploads").rglob("original.json"))
