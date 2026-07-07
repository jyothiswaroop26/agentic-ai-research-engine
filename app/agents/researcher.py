from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable
from urllib.parse import urlparse

from app.tools.tavily_search import SearchResponse, TavilySearch, TavilySearchError, create_tavily_search


class ResearchAgentError(Exception):
	"""Raised when the research agent cannot complete a research task."""


@dataclass
class ResearchDocument:
	title: str
	url: str
	snippet: str
	score: float
	source_query: str
	published_date: str | None = None
	domain: str = ""


@dataclass
class ResearchDataset:
	topic: str
	generated_queries: list[str] = field(default_factory=list)
	total_documents: int = 0
	documents: list[ResearchDocument] = field(default_factory=list)
	sources_by_domain: dict[str, int] = field(default_factory=dict)


class ResearchAgent:
	"""Agent that performs web research and returns structured findings."""

	def __init__(
		self,
		search_client: TavilySearch,
		*,
		max_queries: int = 5,
		max_results_per_query: int = 5,
		min_score: float = 0.0,
	) -> None:
		self._search_client = search_client
		self._max_queries = max(1, max_queries)
		self._max_results_per_query = max(1, max_results_per_query)
		self._min_score = min_score

	def generate_search_queries(self, topic: str) -> list[str]:
		"""Generate diverse search queries from a single research topic."""
		cleaned_topic = topic.strip()
		if not cleaned_topic:
			raise ValueError("Research topic must not be empty.")

		candidates = [
			cleaned_topic,
			f"{cleaned_topic} latest developments",
			f"{cleaned_topic} key challenges",
			f"{cleaned_topic} real world applications",
			f"{cleaned_topic} best practices",
			f"{cleaned_topic} future trends",
		]

		return self._dedupe_preserve_order(candidates)[: self._max_queries]

	def process_search_results(
		self,
		query_responses: Iterable[tuple[str, SearchResponse]],
	) -> list[ResearchDocument]:
		"""Normalize, deduplicate, and rank search results."""
		documents: list[ResearchDocument] = []
		seen_urls: set[str] = set()

		for query, response in query_responses:
			for result in response.results:
				normalized_url = (result.url or "").strip()
				normalized_title = (result.title or "").strip()
				normalized_content = (result.content or "").strip()
				if not normalized_url or not normalized_title or not normalized_content:
					continue
				if normalized_url in seen_urls:
					continue
				if result.score < self._min_score:
					continue

				seen_urls.add(normalized_url)
				documents.append(
					ResearchDocument(
						title=normalized_title,
						url=normalized_url,
						snippet=normalized_content,
						score=float(result.score),
						source_query=query,
						published_date=result.published_date,
						domain=self._extract_domain(normalized_url),
					)
				)

		documents.sort(key=lambda item: (-item.score, item.title.lower()))
		return documents

	def structure_collected_data(
		self,
		topic: str,
		queries: list[str],
		documents: list[ResearchDocument],
	) -> ResearchDataset:
		"""Build a structured dataset from normalized research documents."""
		sources_by_domain: dict[str, int] = {}
		for document in documents:
			key = document.domain or "unknown"
			sources_by_domain[key] = sources_by_domain.get(key, 0) + 1

		return ResearchDataset(
			topic=topic,
			generated_queries=queries,
			total_documents=len(documents),
			documents=documents,
			sources_by_domain=sources_by_domain,
		)

	def run(self, topic: str) -> ResearchDataset:
		"""Run query generation, search, processing, and data structuring."""
		queries = self.generate_search_queries(topic)

		query_responses: list[tuple[str, SearchResponse]] = []
		try:
			for query in queries:
				response = self._search_client.search(
					query,
					max_results=self._max_results_per_query,
					include_answer=False,
				)
				query_responses.append((query, response))
		except TavilySearchError as exc:
			raise ResearchAgentError(f"Research search failed: {exc}") from exc

		documents = self.process_search_results(query_responses)
		return self.structure_collected_data(topic=topic, queries=queries, documents=documents)

	@staticmethod
	def _dedupe_preserve_order(values: list[str]) -> list[str]:
		seen: set[str] = set()
		output: list[str] = []
		for value in values:
			normalized = value.strip().lower()
			if not normalized or normalized in seen:
				continue
			seen.add(normalized)
			output.append(value.strip())
		return output

	@staticmethod
	def _extract_domain(url: str) -> str:
		parsed = urlparse(url)
		return parsed.netloc.lower()


def create_research_agent() -> ResearchAgent:
	"""Build a :class:`ResearchAgent` from application settings."""
	return ResearchAgent(search_client=create_tavily_search())
