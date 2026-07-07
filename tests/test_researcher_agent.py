from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agents.researcher import ResearchAgent, ResearchAgentError
from app.tools.tavily_search import SearchResponse, SearchResult, TavilySearchError


class FakeSearchClient:
    def __init__(self, responses: dict[str, SearchResponse] | None = None, should_fail: bool = False):
        self.responses = responses or {}
        self.should_fail = should_fail

    def search(self, query: str, *, max_results: int | None = None, include_answer: bool = False) -> SearchResponse:
        if self.should_fail:
            raise TavilySearchError("boom")
        return self.responses.get(query, SearchResponse(query=query, results=[]))


def _response(query: str, results: list[SearchResult]) -> SearchResponse:
    return SearchResponse(query=query, results=results)


def test_generate_search_queries_returns_diverse_queries():
    agent = ResearchAgent(search_client=MagicMock(), max_queries=4)

    queries = agent.generate_search_queries("agentic ai")

    assert len(queries) == 4
    assert queries[0] == "agentic ai"
    assert any("latest developments" in q for q in queries)
    assert all("agentic ai" in q for q in queries)


def test_generate_search_queries_rejects_empty_topic():
    agent = ResearchAgent(search_client=MagicMock())

    with pytest.raises(ValueError, match="must not be empty"):
        agent.generate_search_queries("   ")


def test_process_search_results_deduplicates_and_sorts():
    agent = ResearchAgent(search_client=MagicMock(), min_score=0.5)
    query_a = "q1"
    query_b = "q2"

    response_a = _response(
        query_a,
        [
            SearchResult(
                title="B paper",
                url="https://example.com/paper-b",
                content="content b",
                score=0.8,
                published_date="2025-01-01",
            ),
            SearchResult(
                title="Duplicate",
                url="https://duplicate.com/item",
                content="same",
                score=0.75,
            ),
        ],
    )

    response_b = _response(
        query_b,
        [
            SearchResult(
                title="A paper",
                url="https://example.com/paper-a",
                content="content a",
                score=0.95,
            ),
            SearchResult(
                title="Duplicate should be dropped",
                url="https://duplicate.com/item",
                content="same",
                score=0.99,
            ),
            SearchResult(
                title="Low score",
                url="https://low-score.com/item",
                content="skip",
                score=0.2,
            ),
        ],
    )

    docs = agent.process_search_results([(query_a, response_a), (query_b, response_b)])

    assert len(docs) == 3
    assert docs[0].title == "A paper"
    assert docs[1].title == "B paper"
    assert docs[2].url == "https://duplicate.com/item"
    assert docs[0].domain == "example.com"


def test_run_structures_collected_data():
    topic = "federated learning"
    generated = [
        topic,
        f"{topic} latest developments",
    ]

    responses = {
        generated[0]: _response(
            generated[0],
            [
                SearchResult(
                    title="Paper 1",
                    url="https://site-a.com/paper-1",
                    content="result one",
                    score=0.9,
                )
            ],
        ),
        generated[1]: _response(
            generated[1],
            [
                SearchResult(
                    title="Paper 2",
                    url="https://site-b.com/paper-2",
                    content="result two",
                    score=0.7,
                )
            ],
        ),
    }

    client = FakeSearchClient(responses=responses)
    agent = ResearchAgent(search_client=client, max_queries=2)

    dataset = agent.run(topic)

    assert dataset.topic == topic
    assert dataset.generated_queries == generated
    assert dataset.total_documents == 2
    assert len(dataset.documents) == 2
    assert dataset.sources_by_domain == {"site-a.com": 1, "site-b.com": 1}


def test_run_wraps_tavily_error_as_research_agent_error():
    agent = ResearchAgent(search_client=FakeSearchClient(should_fail=True))

    with pytest.raises(ResearchAgentError, match="Research search failed"):
        agent.run("transformer interpretability")
