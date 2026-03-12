from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import AppSettings
from app.services.translation_service import SummaryRequest, TranslationRequest, TranslationService, TranslationServiceError


def test_mock_translation_provider_prefixes_text() -> None:
    service = TranslationService(
        AppSettings(
            APP_ENV="test",
            DATABASE_URL="sqlite+pysqlite:///:memory:",
            DOCS_ENABLED=False,
            TRANSLATION_PROVIDER="mock",
        )
    )

    translated = service.translate(
        TranslationRequest(text="Hello world", source_language="en", target_language="fr")
    )

    assert translated == "[en->fr] Hello world"


def test_disabled_translation_provider_raises() -> None:
    service = TranslationService(
        AppSettings(
            APP_ENV="test",
            DATABASE_URL="sqlite+pysqlite:///:memory:",
            DOCS_ENABLED=False,
            TRANSLATION_PROVIDER="disabled",
        )
    )

    with pytest.raises(TranslationServiceError, match="AI translation is not configured"):
        service.translate(TranslationRequest(text="Hello", target_language="fr"))


def test_disabled_summary_provider_raises_summary_specific_message() -> None:
    service = TranslationService(
        AppSettings(
            APP_ENV="test",
            DATABASE_URL="sqlite+pysqlite:///:memory:",
            DOCS_ENABLED=False,
            TRANSLATION_PROVIDER="disabled",
        )
    )

    with pytest.raises(TranslationServiceError, match="AI summarization is not configured"):
        service.summarize(SummaryRequest(text="Hello", output_language="en"))


def test_groq_api_key_auto_enables_provider() -> None:
    settings = AppSettings(
        APP_ENV="test",
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        DOCS_ENABLED=False,
        GROQ_API_KEY="test-key",
    )

    assert settings.translation_provider == "groq"
    assert settings.translation_api_key == "test-key"


def test_mock_summary_provider_returns_marker() -> None:
    service = TranslationService(
        AppSettings(
            APP_ENV="test",
            DATABASE_URL="sqlite+pysqlite:///:memory:",
            DOCS_ENABLED=False,
            TRANSLATION_PROVIDER="mock",
        )
    )

    summary = service.summarize(
        SummaryRequest(text="A long contract about payment terms.", output_language="en", length="short")
    )

    assert summary.startswith("[summary:short:en]")


def test_groq_provider_uses_chat_completion_api() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Bonjour le monde",
                        }
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://api.groq.com/openai/v1",
        headers={"Authorization": "Bearer test-key", "Content-Type": "application/json"},
    )
    service = TranslationService(
        AppSettings(
            APP_ENV="test",
            DATABASE_URL="sqlite+pysqlite:///:memory:",
            DOCS_ENABLED=False,
            TRANSLATION_PROVIDER="groq",
            GROQ_API_KEY="test-key",
        ),
        http_client=client,
    )

    translated = service.translate(
        TranslationRequest(text="Hello world", source_language="en", target_language="fr")
    )

    assert translated == "Bonjour le monde"
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "llama-3.3-70b-versatile"
