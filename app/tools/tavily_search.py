from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tavily import TavilyClient, MissingAPIKeyError, InvalidAPIKeyError, UsageLimitExceededError


@dataclass
class SearchResult:
    title: str
    url: str
    content: str
    score: float = 0.0
    published_date: str | None = None


@dataclass
class SearchResponse:
    query: str
    results: list[SearchResult] = field(default_factory=list)
    answer: str | None = None


class TavilySearchError(Exception):
    """Raised when a Tavily search operation fails."""


class TavilySearch:
    """Wrapper around the Tavily search API."""

    def __init__(self, api_key: str, max_results: int = 5, search_depth: str = "basic") -> None:
        if not api_key:
            raise TavilySearchError("Tavily API key must not be empty.")
        self._client = TavilyClient(api_key=api_key)
        self._max_results = max_results
        self._search_depth = search_depth

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, query: str, *, max_results: int | None = None, include_answer: bool = False) -> SearchResponse:
        """Perform a web search and return parsed results.

        Args:
            query: The search query string.
            max_results: Override the instance-level max results.
            include_answer: Whether to request an AI-generated answer summary.

        Returns:
            A :class:`SearchResponse` containing the parsed results.

        Raises:
            TavilySearchError: On any Tavily API failure.
            ValueError: If *query* is empty.
        """
        if not query or not query.strip():
            raise ValueError("Search query must not be empty.")

        k = max_results if max_results is not None else self._max_results

        try:
            raw: dict[str, Any] = self._client.search(
                query=query,
                search_depth=self._search_depth,
                max_results=k,
                include_answer=include_answer,
            )
        except MissingAPIKeyError as exc:
            raise TavilySearchError("Tavily API key is missing.") from exc
        except InvalidAPIKeyError as exc:
            raise TavilySearchError("Tavily API key is invalid.") from exc
        except UsageLimitExceededError as exc:
            raise TavilySearchError("Tavily usage limit exceeded.") from exc
        except Exception as exc:
            raise TavilySearchError(f"Tavily search failed: {exc}") from exc

        return self._parse_response(query, raw)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_response(self, query: str, raw: dict[str, Any]) -> SearchResponse:
        results: list[SearchResult] = [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=float(item.get("score", 0.0)),
                published_date=item.get("published_date"),
            )
            for item in raw.get("results", [])
        ]

        return SearchResponse(
            query=query,
            results=results,
            answer=raw.get("answer"),
        )


# ---------------------------------------------------------------------------
# Factory function (uses app settings)
# ---------------------------------------------------------------------------

def create_tavily_search() -> TavilySearch:
    """Build a :class:`TavilySearch` instance from the application settings."""
    from app.config import get_settings  # local import to avoid circular deps

    settings = get_settings()
    return TavilySearch(
        api_key=settings.tavily_api_key,
        max_results=settings.tavily_max_results,
        search_depth=settings.tavily_search_depth,
    )
