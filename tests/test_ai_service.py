from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.services.ai_service import AIService


def test_settings_reads_required_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = Settings()
    assert settings.openai_api_key == "test-key"
    assert settings.openai_model == "gpt-4o-mini"


def test_settings_raises_when_openai_key_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_generate_text_uses_openai_responses(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = Settings()

    class FakeResponses:
        @staticmethod
        def create(**kwargs):
            assert kwargs["model"] == settings.openai_model
            return SimpleNamespace(output_text="mocked response")

    class FakeClient:
        responses = FakeResponses()

    service = AIService(settings)
    service.client = FakeClient()

    result = service.generate_text("hello")
    assert result == "mocked response"


def test_verify_connectivity_calls_models_list(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = Settings()
    called = {"value": False}

    class FakeModels:
        @staticmethod
        def list():
            called["value"] = True
            return []

    class FakeClient:
        models = FakeModels()

    service = AIService(settings)
    service.client = FakeClient()

    assert service.verify_connectivity() is True
    assert called["value"] is True
