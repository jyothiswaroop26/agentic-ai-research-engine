from fastapi.testclient import TestClient

from app.api.routes import get_ai_service
from app.main import app


class FakeService:
    def __init__(self, should_connect=True):
        self.should_connect = should_connect
        self.settings = type("SettingsStub", (), {"openai_model": "gpt-4o-mini"})

    def generate_text(self, prompt: str, model: str | None = None) -> str:
        return f"echo:{prompt}"

    def verify_connectivity(self) -> bool:
        if not self.should_connect:
            raise RuntimeError("network error")
        return True


def test_health_endpoint():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_llm_response_endpoint_success():
    app.dependency_overrides[get_ai_service] = lambda: FakeService()
    client = TestClient(app)

    resp = client.post("/api/llm/respond", json={"prompt": "hello"})
    assert resp.status_code == 200
    assert resp.json()["response"] == "echo:hello"
    assert resp.json()["model"] == "gpt-4o-mini"

    app.dependency_overrides.clear()


def test_openai_connectivity_endpoint_success():
    app.dependency_overrides[get_ai_service] = lambda: FakeService(should_connect=True)
    client = TestClient(app)

    resp = client.get("/api/openai/connectivity")
    assert resp.status_code == 200
    assert resp.json() == {"status": "connected"}

    app.dependency_overrides.clear()


def test_openai_connectivity_endpoint_failure():
    app.dependency_overrides[get_ai_service] = lambda: FakeService(should_connect=False)
    client = TestClient(app)

    resp = client.get("/api/openai/connectivity")
    assert resp.status_code == 503
    assert "OpenAI connectivity failed" in resp.json()["detail"]

    app.dependency_overrides.clear()
