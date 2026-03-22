"""API response structure tests."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_sample_questions_endpoint() -> None:
    response = client.get("/sample-questions")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["questions"]) >= 3


def test_analyze_endpoint_structure() -> None:
    def fake_run_analysis(query: str) -> dict:  # noqa: ARG001
        return {
            "summary": "Pipeline velocity improved from 69.77 to 66.14 days week over week.",
            "root_cause": "Enterprise remains the slowest segment and Stage 2 remains the main bottleneck.",
            "recommendation": "Focus managers on Enterprise Stage 2 opportunities first.",
            "evidence": [{"label": "current_velocity", "value": 66.14}],
            "trace": [{"step": "planner_node", "status": "completed", "details": {"action": "finish"}}],
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
            "verified": True,
            "errors": [],
        }

    app.dependency_overrides = {}
    import app.api.routes as routes

    original = routes.run_analysis
    routes.run_analysis = fake_run_analysis
    response = client.post("/analyze", json={"query": "Why did pipeline velocity drop this week?"})
    routes.run_analysis = original
    assert response.status_code == 200
    payload = response.json()
    assert {"summary", "root_cause", "recommendation", "evidence", "trace", "executed_steps", "verified", "errors"} <= payload.keys()
    assert isinstance(payload["trace"], list)
    assert isinstance(payload["evidence"], list)
    assert isinstance(payload["executed_steps"], list)
