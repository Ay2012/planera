"""Conversation persistence and /chat orchestration tests."""

from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.session import reset_engine_and_session
from app.main import app


@pytest.fixture
def chat_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "chat_test.sqlite"))
    monkeypatch.setenv("REGISTRY_PATH", str(tmp_path / "chat_source_registry.duckdb"))
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    reset_engine_and_session()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()
    reset_engine_and_session()


def _signup(client: TestClient, email: str, password: str = "password123") -> str:
    r = client.post("/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _fake_analysis_state(query: str, source_ids=None) -> dict:  # noqa: ARG001
    return {
        "analysis": "## Demo\nHello from fake analysis.\n",
        "trace": [{"step": "planner_compiled_node", "status": "completed", "details": {}}],
        "executed_steps": [],
        "errors": [],
        "runtime_ms": 42,
    }


def test_chat_creates_conversation_on_first_prompt(chat_client: TestClient) -> None:
    import app.services.analysis_run as analysis_run

    token = _signup(chat_client, "first@example.com")
    original = analysis_run.run_analysis
    analysis_run.run_analysis = _fake_analysis_state
    try:
        r = chat_client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "Why is pipeline velocity changing?"},
        )
    finally:
        analysis_run.run_analysis = original

    assert r.status_code == 200, r.text
    body = r.json()
    assert "conversation" in body
    assert body["conversation"]["id"] >= 1
    assert body["conversation"]["title"] == "Why is pipeline velocity changing?"
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["content"] == "## Demo\nHello from fake analysis.\n"
    assert body["analysis"] == body["assistant_message"]["content"]
    assert body["runtime_ms"] == 42
    assert body["assistant_message"]["metadata_json"]["inspection_id"] == body["inspection_id"]
    assert body["assistant_message"]["metadata_json"]["runtime_ms"] == 42

    lst = chat_client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
    assert lst.status_code == 200
    assert len(lst.json()["conversations"]) == 1
    assert lst.json()["conversations"][0]["last_message_preview"] is not None

    detail = chat_client.get(
        f"/conversations/{body['conversation']['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200
    msgs = detail.json()["messages"]
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Why is pipeline velocity changing?"
    assert msgs[1]["role"] == "assistant"


def test_chat_appends_to_existing_conversation(chat_client: TestClient) -> None:
    import app.services.analysis_run as analysis_run

    token = _signup(chat_client, "second@example.com")
    original = analysis_run.run_analysis
    analysis_run.run_analysis = _fake_analysis_state
    try:
        first = chat_client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "First question here"},
        )
        cid = first.json()["conversation"]["id"]
        second = chat_client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"conversation_id": cid, "query": "Second question here"},
        )
    finally:
        analysis_run.run_analysis = original

    assert second.status_code == 200
    assert second.json()["conversation"]["id"] == cid

    detail = chat_client.get(f"/conversations/{cid}", headers={"Authorization": f"Bearer {token}"})
    assert len(detail.json()["messages"]) == 4


def test_chat_serializes_timestamp_values_in_assistant_metadata(chat_client: TestClient) -> None:
    import app.services.analysis_run as analysis_run

    token = _signup(chat_client, "timestamp-chat@example.com")
    original = analysis_run.run_analysis

    def fake_analysis_with_timestamp(query: str, source_ids=None) -> dict:  # noqa: ARG001
        return {
            "analysis": "Monthly totals look stable.",
            "trace": [{"step": "executor_node", "status": "completed", "details": {}}],
            "executed_steps": [
                {
                    "id": "1",
                    "kind": "sql",
                    "purpose": "Aggregate charging activity by month",
                    "code": "select month, total_energy_kwh from monthly_energy",
                    "output_alias": "monthly_energy",
                    "attempt": 1,
                    "status": "success",
                    "artifact": {
                        "alias": "monthly_energy",
                        "artifact_type": "table",
                        "row_count": 1,
                        "columns": ["month", "total_energy_kwh"],
                        "preview_rows": [
                            {
                                "month": pd.Timestamp("2021-11-01 00:00:00"),
                                "total_energy_kwh": 16843.64,
                            }
                        ],
                        "summary": {},
                    },
                    "error": None,
                }
            ],
            "errors": [],
        }

    analysis_run.run_analysis = fake_analysis_with_timestamp
    try:
        response = chat_client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "How much charging happened each month?"},
        )
    finally:
        analysis_run.run_analysis = original

    assert response.status_code == 200, response.text
    metadata = response.json()["assistant_message"]["metadata_json"]
    row = metadata["executed_steps"][0]["artifact"]["preview_rows"][0]
    assert row["month"] == "2021-11-01T00:00:00"
    assert row["total_energy_kwh"] == 16843.64

    conversation_id = response.json()["conversation"]["id"]
    detail = chat_client.get(f"/conversations/{conversation_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.status_code == 200
    persisted_row = detail.json()["messages"][1]["metadata_json"]["executed_steps"][0]["artifact"]["preview_rows"][0]
    assert persisted_row["month"] == "2021-11-01T00:00:00"


def test_conversation_list_scoped_to_user(chat_client: TestClient) -> None:
    import app.services.analysis_run as analysis_run

    original = analysis_run.run_analysis
    analysis_run.run_analysis = _fake_analysis_state
    try:
        a = _signup(chat_client, "a_scoped@example.com")
        b = _signup(chat_client, "b_scoped@example.com")
        ca = chat_client.post(
            "/chat",
            headers={"Authorization": f"Bearer {a}"},
            json={"query": "User A thread"},
        ).json()["conversation"]["id"]
        chat_client.post(
            "/chat",
            headers={"Authorization": f"Bearer {b}"},
            json={"query": "User B thread"},
        )
    finally:
        analysis_run.run_analysis = original

    list_a = chat_client.get("/conversations", headers={"Authorization": f"Bearer {a}"})
    assert list_a.status_code == 200
    ids_a = {c["id"] for c in list_a.json()["conversations"]}
    assert ids_a == {ca}

    list_b = chat_client.get("/conversations", headers={"Authorization": f"Bearer {b}"})
    ids_b = {c["id"] for c in list_b.json()["conversations"]}
    assert ca not in ids_b
    assert len(ids_b) == 1


def test_conversations_require_auth(chat_client: TestClient) -> None:
    r = chat_client.get("/conversations")
    assert r.status_code == 401

    r2 = chat_client.post("/chat", json={"query": "Needs auth and length"})
    assert r2.status_code == 401


def test_cross_user_conversation_forbidden(chat_client: TestClient) -> None:
    import app.services.analysis_run as analysis_run

    original = analysis_run.run_analysis
    analysis_run.run_analysis = _fake_analysis_state
    try:
        owner = _signup(chat_client, "owner@example.com")
        intruder = _signup(chat_client, "intruder@example.com")
        cid = chat_client.post(
            "/chat",
            headers={"Authorization": f"Bearer {owner}"},
            json={"query": "Private thread"},
        ).json()["conversation"]["id"]
    finally:
        analysis_run.run_analysis = original

    forbidden = chat_client.get(f"/conversations/{cid}", headers={"Authorization": f"Bearer {intruder}"})
    assert forbidden.status_code == 403

    post_forbidden = chat_client.post(
        "/chat",
        headers={"Authorization": f"Bearer {intruder}"},
        json={"conversation_id": cid, "query": "Malicious follow-up question here"},
    )
    assert post_forbidden.status_code == 403


def test_unknown_conversation_returns_404(chat_client: TestClient) -> None:
    token = _signup(chat_client, "solo@example.com")
    r = chat_client.get("/conversations/99999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_persisted_inspection_requires_auth_after_memory_clear(chat_client: TestClient) -> None:
    import app.services.analysis_run as analysis_run
    from app.api.workspace import clear_workspace_state

    token = _signup(chat_client, "inspectpersist@example.com")
    original = analysis_run.run_analysis
    analysis_run.run_analysis = _fake_analysis_state
    try:
        r = chat_client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "Why is pipeline velocity changing?"},
        )
    finally:
        analysis_run.run_analysis = original

    assert r.status_code == 200
    inspection_id = r.json()["inspection_id"]
    clear_workspace_state()

    assert chat_client.get(f"/inspections/{inspection_id}").status_code == 401

    loaded = chat_client.get(f"/inspections/{inspection_id}", headers={"Authorization": f"Bearer {token}"})
    assert loaded.status_code == 200
    assert loaded.json()["inspection"]["id"] == inspection_id


def test_persisted_inspection_forbidden_for_other_user(chat_client: TestClient) -> None:
    import app.services.analysis_run as analysis_run
    from app.api.workspace import clear_workspace_state

    owner = _signup(chat_client, "inspectowner@example.com")
    intruder = _signup(chat_client, "inspectintruder@example.com")
    original = analysis_run.run_analysis
    analysis_run.run_analysis = _fake_analysis_state
    try:
        r = chat_client.post(
            "/chat",
            headers={"Authorization": f"Bearer {owner}"},
            json={"query": "Private inspection thread"},
        )
    finally:
        analysis_run.run_analysis = original

    inspection_id = r.json()["inspection_id"]
    clear_workspace_state()

    forbidden = chat_client.get(f"/inspections/{inspection_id}", headers={"Authorization": f"Bearer {intruder}"})
    assert forbidden.status_code == 403


def test_chat_rejects_uploads_owned_by_another_user(chat_client: TestClient) -> None:
    import app.services.analysis_run as analysis_run

    owner = _signup(chat_client, "owner-upload-chat@example.com")
    intruder = _signup(chat_client, "intruder-upload-chat@example.com")
    owner_headers = {"Authorization": f"Bearer {owner}"}
    intruder_headers = {"Authorization": f"Bearer {intruder}"}

    upload_response = chat_client.post(
        "/uploads",
        headers=owner_headers,
        files={"file": ("pipeline.csv", b"stage,amount\nopen,10\nwon,25\n", "text/csv")},
    )
    source_id = upload_response.json()["asset"]["id"]

    called = False
    original = analysis_run.run_analysis

    def fake_run_analysis(query: str, source_ids=None) -> dict:
        nonlocal called
        called = True
        return {"analysis": "", "trace": [], "executed_steps": [], "errors": []}

    analysis_run.run_analysis = fake_run_analysis
    try:
        response = chat_client.post(
            "/chat",
            headers=intruder_headers,
            json={"query": "Use another user's upload", "source_ids": [source_id]},
        )
    finally:
        analysis_run.run_analysis = original

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Attach a valid uploaded data source before running analysis."
    assert called is False
