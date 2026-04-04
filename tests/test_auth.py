"""Tests for JWT auth endpoints (SQLite isolated per test module via temp DB path)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.session import reset_engine_and_session
from app.main import app


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    """Use a fresh SQLite file so auth tests do not touch the default planera.db."""

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "auth_test.sqlite"))
    get_settings.cache_clear()
    reset_engine_and_session()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()
    reset_engine_and_session()


def test_signup_login_me_flow(auth_client: TestClient) -> None:
    signup = auth_client.post(
        "/auth/signup",
        json={
            "email": "Person@Example.COM",
            "password": "correcthorse",
            "display_name": "  Demo  ",
        },
    )
    assert signup.status_code == 200
    body = signup.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "person@example.com"
    assert body["user"]["display_name"] == "Demo"
    assert "access_token" in body
    token = body["access_token"]

    me = auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "person@example.com"

    login = auth_client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "correcthorse"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == body["user"]["id"]


def test_signup_duplicate_email_conflict(auth_client: TestClient) -> None:
    payload = {"email": "dup@example.com", "password": "password1"}
    assert auth_client.post("/auth/signup", json=payload).status_code == 200
    dup = auth_client.post("/auth/signup", json=payload)
    assert dup.status_code == 409
    assert dup.json()["detail"]["message"] == "Email already registered."


def test_me_requires_bearer_token(auth_client: TestClient) -> None:
    r = auth_client.get("/auth/me")
    assert r.status_code == 401
    assert r.json()["detail"]["message"] == "Not authenticated."


def test_login_invalid_credentials(auth_client: TestClient) -> None:
    auth_client.post("/auth/signup", json={"email": "u@example.com", "password": "password1"})
    bad = auth_client.post("/auth/login", json={"email": "u@example.com", "password": "wrong"})
    assert bad.status_code == 401
    assert bad.json()["detail"]["message"] == "Invalid email or password."
