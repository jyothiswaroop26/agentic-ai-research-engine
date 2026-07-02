"""Tests for app/tools/tavily_search.py.

All network calls are mocked so no real Tavily API key is required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.tools.tavily_search import (
    SearchResponse,
    SearchResult,
    TavilySearch,
    TavilySearchError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw_response(
    *,
    results: list[dict] | None = None,
    answer: str | None = None,
) -> dict:
    return {
        "results": results
        or [
            {
                "title": "Result 1",
                "url": "https://example.com/1",
                "content": "Some content",
                "score": 0.95,
                "published_date": "2024-01-01",
            },
            {
                "title": "Result 2",
                "url": "https://example.com/2",
                "content": "More content",
                "score": 0.80,
                "published_date": None,
            },
        ],
        "answer": answer,
    }


def _make_search(api_key: str = "tvly-test-key", max_results: int = 5) -> TavilySearch:
    with patch("app.tools.tavily_search.TavilyClient"):
        instance = TavilySearch(api_key=api_key, max_results=max_results)
    return instance


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_construction_succeeds_with_valid_key():
    with patch("app.tools.tavily_search.TavilyClient") as mock_cls:
        ts = TavilySearch(api_key="tvly-abc", max_results=3, search_depth="advanced")
    mock_cls.assert_called_once_with(api_key="tvly-abc")
    assert ts._max_results == 3
    assert ts._search_depth == "advanced"


def test_construction_raises_on_empty_key():
    with pytest.raises(TavilySearchError, match="API key must not be empty"):
        TavilySearch(api_key="")


# ---------------------------------------------------------------------------
# Successful searches
# ---------------------------------------------------------------------------


def test_search_returns_parsed_results():
    ts = _make_search()
    ts._client.search = MagicMock(return_value=_make_raw_response())

    response = ts.search("AI research")

    assert isinstance(response, SearchResponse)
    assert response.query == "AI research"
    assert len(response.results) == 2
    assert response.answer is None


def test_search_result_fields_are_mapped_correctly():
    ts = _make_search()
    ts._client.search = MagicMock(return_value=_make_raw_response())

    first: SearchResult = ts.search("test").results[0]

    assert first.title == "Result 1"
    assert first.url == "https://example.com/1"
    assert first.content == "Some content"
    assert first.score == pytest.approx(0.95)
    assert first.published_date == "2024-01-01"


def test_search_missing_date_is_none():
    ts = _make_search()
    ts._client.search = MagicMock(return_value=_make_raw_response())

    second: SearchResult = ts.search("test").results[1]
    assert second.published_date is None


def test_search_includes_answer_when_requested():
    ts = _make_search()
    ts._client.search = MagicMock(
        return_value=_make_raw_response(answer="AI stands for artificial intelligence.")
    )

    response = ts.search("What is AI?", include_answer=True)
    assert response.answer == "AI stands for artificial intelligence."


def test_search_passes_max_results_override():
    ts = _make_search(max_results=5)
    ts._client.search = MagicMock(return_value=_make_raw_response())

    ts.search("topic", max_results=2)

    call_kwargs = ts._client.search.call_args.kwargs
    assert call_kwargs["max_results"] == 2


def test_search_uses_instance_max_results_by_default():
    ts = _make_search(max_results=7)
    ts._client.search = MagicMock(return_value=_make_raw_response())

    ts.search("topic")

    call_kwargs = ts._client.search.call_args.kwargs
    assert call_kwargs["max_results"] == 7


def test_search_empty_results_list():
    ts = _make_search()
    ts._client.search = MagicMock(return_value={"results": []})

    response = ts.search("obscure query")
    assert response.results == []


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_search_raises_on_empty_query():
    ts = _make_search()
    with pytest.raises(ValueError, match="must not be empty"):
        ts.search("")


def test_search_raises_on_whitespace_query():
    ts = _make_search()
    with pytest.raises(ValueError, match="must not be empty"):
        ts.search("   ")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_search_wraps_missing_api_key_error():
    from tavily import MissingAPIKeyError

    ts = _make_search()
    ts._client.search = MagicMock(side_effect=MissingAPIKeyError)

    with pytest.raises(TavilySearchError, match="API key is missing"):
        ts.search("query")


def test_search_wraps_invalid_api_key_error():
    from tavily import InvalidAPIKeyError

    ts = _make_search()
    ts._client.search = MagicMock(side_effect=InvalidAPIKeyError)

    with pytest.raises(TavilySearchError, match="API key is invalid"):
        ts.search("query")


def test_search_wraps_usage_limit_error():
    from tavily import UsageLimitExceededError

    ts = _make_search()
    ts._client.search = MagicMock(side_effect=UsageLimitExceededError("quota exceeded"))

    with pytest.raises(TavilySearchError, match="usage limit exceeded"):
        ts.search("query")


def test_search_wraps_generic_exception():
    ts = _make_search()
    ts._client.search = MagicMock(side_effect=ConnectionError("timeout"))

    with pytest.raises(TavilySearchError, match="Tavily search failed"):
        ts.search("query")


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def test_create_tavily_search_uses_settings():
    from app.tools.tavily_search import create_tavily_search

    fake_settings = MagicMock()
    fake_settings.tavily_api_key = "tvly-from-settings"
    fake_settings.tavily_max_results = 10
    fake_settings.tavily_search_depth = "advanced"

    with patch("app.tools.tavily_search.TavilyClient"), patch(
        "app.config.get_settings", return_value=fake_settings
    ):
        ts = create_tavily_search()

    assert ts._max_results == 10
    assert ts._search_depth == "advanced"
