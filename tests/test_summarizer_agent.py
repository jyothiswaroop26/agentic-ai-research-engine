"""Tests for the SummarizerAgent."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agents.researcher import ResearchDocument
from app.agents.summarizer import (
    ContentSummary,
    PaperSummary,
    ResearchSynthesis,
    SummarizerAgent,
    SummarizerAgentError,
    _extract_section,
    _is_research_paper,
    _parse_bullet_list,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc(
    title: str = "Test Paper",
    url: str = "https://example.com/paper",
    snippet: str = "Some content about the topic.",
    score: float = 0.9,
    domain: str = "example.com",
    published_date: str | None = "2025-01-01",
) -> ResearchDocument:
    return ResearchDocument(
        title=title,
        url=url,
        snippet=snippet,
        score=score,
        source_query="test query",
        published_date=published_date,
        domain=domain,
    )


def _make_ai_service(response: str = "") -> MagicMock:
    service = MagicMock()
    service.generate_text.return_value = response
    return service


# ---------------------------------------------------------------------------
# Unit tests: internal helpers
# ---------------------------------------------------------------------------


class TestExtractSection:
    def test_extracts_named_section(self):
        text = "KEY FINDINGS:\n- Finding one\n- Finding two\nMETHODOLOGY:\nSurvey study."
        assert _extract_section(text, "KEY FINDINGS") == "- Finding one\n- Finding two"

    def test_returns_empty_when_section_missing(self):
        assert _extract_section("No sections here.", "SUMMARY") == ""

    def test_extracts_last_section(self):
        text = "OVERVIEW:\nIntro text.\nSYNTHESIS:\nFinal synthesis text."
        result = _extract_section(text, "SYNTHESIS")
        assert "Final synthesis text." in result

    def test_case_insensitive_lookup(self):
        text = "summary:\nThis is the summary text."
        assert _extract_section(text, "SUMMARY") == "This is the summary text."


class TestParseBulletList:
    def test_parses_dash_bullets(self):
        text = "- First point\n- Second point\n- Third point"
        result = _parse_bullet_list(text)
        assert result == ["First point", "Second point", "Third point"]

    def test_parses_asterisk_bullets(self):
        text = "* Alpha\n* Beta"
        result = _parse_bullet_list(text)
        assert result == ["Alpha", "Beta"]

    def test_ignores_blank_lines(self):
        text = "- One\n\n- Two\n\n"
        result = _parse_bullet_list(text)
        assert result == ["One", "Two"]

    def test_plain_text_returned_as_single_item(self):
        text = "No bullets here"
        result = _parse_bullet_list(text)
        assert result == ["No bullets here"]


class TestIsResearchPaper:
    def test_arxiv_domain_is_paper(self):
        doc = _make_doc(domain="arxiv.org")
        assert _is_research_paper(doc) is True

    def test_semanticscholar_domain_is_paper(self):
        doc = _make_doc(domain="semanticscholar.org")
        assert _is_research_paper(doc) is True

    def test_generic_blog_is_not_paper(self):
        doc = _make_doc(domain="medium.com")
        assert _is_research_paper(doc) is False

    def test_ieee_domain_is_paper(self):
        doc = _make_doc(domain="ieee.org")
        assert _is_research_paper(doc) is True


# ---------------------------------------------------------------------------
# Unit tests: summarize_paper
# ---------------------------------------------------------------------------


class TestSummarizePaper:
    _LLM_RESPONSE = (
        "KEY FINDINGS:\n"
        "- LLMs can reason across domains\n"
        "- Fine-tuning improves task accuracy\n"
        "METHODOLOGY:\n"
        "Comparative benchmark study across 10 LLM variants.\n"
        "IMPLICATIONS:\n"
        "Results suggest broader deployment of LLMs in enterprise settings.\n"
        "SUMMARY:\n"
        "This paper benchmarks 10 large language models on reasoning tasks. "
        "Fine-tuning consistently improved scores. The findings support wider adoption."
    )

    def test_returns_paper_summary_dataclass(self):
        doc = _make_doc(domain="arxiv.org")
        agent = SummarizerAgent(_make_ai_service(self._LLM_RESPONSE))
        result = agent.summarize_paper(doc)
        assert isinstance(result, PaperSummary)

    def test_title_and_url_preserved(self):
        doc = _make_doc(title="My Research", url="https://arxiv.org/abs/1234", domain="arxiv.org")
        agent = SummarizerAgent(_make_ai_service(self._LLM_RESPONSE))
        result = agent.summarize_paper(doc)
        assert result.title == "My Research"
        assert result.url == "https://arxiv.org/abs/1234"

    def test_key_findings_parsed_as_list(self):
        doc = _make_doc(domain="arxiv.org")
        agent = SummarizerAgent(_make_ai_service(self._LLM_RESPONSE))
        result = agent.summarize_paper(doc)
        assert len(result.key_findings) == 2
        assert "LLMs can reason across domains" in result.key_findings

    def test_methodology_extracted(self):
        doc = _make_doc(domain="arxiv.org")
        agent = SummarizerAgent(_make_ai_service(self._LLM_RESPONSE))
        result = agent.summarize_paper(doc)
        assert "Comparative benchmark study" in result.methodology

    def test_implications_extracted(self):
        doc = _make_doc(domain="arxiv.org")
        agent = SummarizerAgent(_make_ai_service(self._LLM_RESPONSE))
        result = agent.summarize_paper(doc)
        assert "enterprise settings" in result.implications

    def test_summary_extracted(self):
        doc = _make_doc(domain="arxiv.org")
        agent = SummarizerAgent(_make_ai_service(self._LLM_RESPONSE))
        result = agent.summarize_paper(doc)
        assert "benchmarks 10 large language models" in result.summary

    def test_raises_when_snippet_empty(self):
        doc = _make_doc(snippet="")
        agent = SummarizerAgent(_make_ai_service())
        with pytest.raises(SummarizerAgentError, match="no content to summarize"):
            agent.summarize_paper(doc)

    def test_raises_when_llm_call_fails(self):
        doc = _make_doc(snippet="Some content")
        service = MagicMock()
        service.generate_text.side_effect = RuntimeError("network error")
        agent = SummarizerAgent(service)
        with pytest.raises(SummarizerAgentError, match="LLM call failed"):
            agent.summarize_paper(doc)

    def test_ai_service_called_once(self):
        doc = _make_doc(domain="arxiv.org")
        service = _make_ai_service(self._LLM_RESPONSE)
        agent = SummarizerAgent(service)
        agent.summarize_paper(doc)
        service.generate_text.assert_called_once()

    def test_prompt_contains_title_and_snippet(self):
        doc = _make_doc(title="Unique Title", snippet="Unique snippet text", domain="arxiv.org")
        service = _make_ai_service(self._LLM_RESPONSE)
        agent = SummarizerAgent(service)
        agent.summarize_paper(doc)
        prompt_arg = service.generate_text.call_args[0][0]
        assert "Unique Title" in prompt_arg
        assert "Unique snippet text" in prompt_arg


# ---------------------------------------------------------------------------
# Unit tests: summarize_web_content
# ---------------------------------------------------------------------------


class TestSummarizeWebContent:
    _LLM_RESPONSE = (
        "MAIN POINTS:\n"
        "- AI adoption is accelerating across industries\n"
        "- Cost reduction is a key driver\n"
        "SUMMARY:\n"
        "Organizations are rapidly adopting AI to reduce costs and improve efficiency."
    )

    def test_returns_content_summary_dataclass(self):
        doc = _make_doc(domain="techcrunch.com")
        agent = SummarizerAgent(_make_ai_service(self._LLM_RESPONSE))
        result = agent.summarize_web_content(doc)
        assert isinstance(result, ContentSummary)

    def test_title_and_url_preserved(self):
        doc = _make_doc(title="AI Trends", url="https://techcrunch.com/ai-trends")
        agent = SummarizerAgent(_make_ai_service(self._LLM_RESPONSE))
        result = agent.summarize_web_content(doc)
        assert result.title == "AI Trends"
        assert result.url == "https://techcrunch.com/ai-trends"

    def test_main_points_parsed_as_list(self):
        doc = _make_doc()
        agent = SummarizerAgent(_make_ai_service(self._LLM_RESPONSE))
        result = agent.summarize_web_content(doc)
        assert len(result.main_points) == 2
        assert "AI adoption is accelerating across industries" in result.main_points

    def test_summary_extracted(self):
        doc = _make_doc()
        agent = SummarizerAgent(_make_ai_service(self._LLM_RESPONSE))
        result = agent.summarize_web_content(doc)
        assert "rapidly adopting AI" in result.summary

    def test_raises_when_snippet_empty(self):
        doc = _make_doc(snippet="")
        agent = SummarizerAgent(_make_ai_service())
        with pytest.raises(SummarizerAgentError, match="no content to summarize"):
            agent.summarize_web_content(doc)

    def test_raises_when_llm_call_fails(self):
        doc = _make_doc(snippet="Some content")
        service = MagicMock()
        service.generate_text.side_effect = RuntimeError("timeout")
        agent = SummarizerAgent(service)
        with pytest.raises(SummarizerAgentError, match="LLM call failed"):
            agent.summarize_web_content(doc)

    def test_prompt_contains_url_and_snippet(self):
        doc = _make_doc(url="https://example.com/article", snippet="unique excerpt text")
        service = _make_ai_service(self._LLM_RESPONSE)
        agent = SummarizerAgent(service)
        agent.summarize_web_content(doc)
        prompt_arg = service.generate_text.call_args[0][0]
        assert "https://example.com/article" in prompt_arg
        assert "unique excerpt text" in prompt_arg


# ---------------------------------------------------------------------------
# Unit tests: synthesize_research
# ---------------------------------------------------------------------------


def _make_synthesis_response() -> str:
    return (
        "OVERVIEW:\n"
        "Agentic AI systems are emerging as a transformative paradigm in research and industry.\n"
        "KEY THEMES:\n"
        "- Autonomous decision-making\n"
        "- Multi-agent collaboration\n"
        "- Safety and alignment challenges\n"
        "SYNTHESIS:\n"
        "The reviewed sources collectively highlight that agentic AI systems excel at "
        "autonomous reasoning but raise significant alignment concerns. Multi-agent "
        "frameworks demonstrate strong benchmark performance. Future work should focus "
        "on safety mechanisms and interpretability."
    )


class TestSynthesizeResearch:
    def test_returns_research_synthesis_dataclass(self):
        docs = [_make_doc(domain="arxiv.org"), _make_doc(url="https://blog.com", domain="blog.com")]
        paper_response = (
            "KEY FINDINGS:\n- Finding A\nMETHODOLOGY:\nSurvey.\nIMPLICATIONS:\nBroad impact.\nSUMMARY:\nBrief."
        )
        web_response = "MAIN POINTS:\n- Point A\nSUMMARY:\nBrief web summary."
        synthesis_response = _make_synthesis_response()

        service = MagicMock()
        service.generate_text.side_effect = [paper_response, web_response, synthesis_response]
        agent = SummarizerAgent(service)

        result = agent.synthesize_research("Agentic AI", docs)
        assert isinstance(result, ResearchSynthesis)

    def test_sources_count_matches_documents(self):
        docs = [_make_doc(), _make_doc(url="https://other.com")]
        summary_resp = "MAIN POINTS:\n- P\nSUMMARY:\nS."
        service = MagicMock()
        service.generate_text.side_effect = [summary_resp, summary_resp, _make_synthesis_response()]
        agent = SummarizerAgent(service)

        result = agent.synthesize_research("AI", docs)
        assert result.sources_count == 2

    def test_paper_documents_go_to_paper_summaries(self):
        docs = [_make_doc(domain="arxiv.org")]
        paper_resp = "KEY FINDINGS:\n- F\nMETHODOLOGY:\nM.\nIMPLICATIONS:\nI.\nSUMMARY:\nS."
        service = MagicMock()
        service.generate_text.side_effect = [paper_resp, _make_synthesis_response()]
        agent = SummarizerAgent(service)

        result = agent.synthesize_research("LLMs", docs)
        assert len(result.paper_summaries) == 1
        assert len(result.content_summaries) == 0

    def test_web_documents_go_to_content_summaries(self):
        docs = [_make_doc(domain="medium.com")]
        web_resp = "MAIN POINTS:\n- P\nSUMMARY:\nS."
        service = MagicMock()
        service.generate_text.side_effect = [web_resp, _make_synthesis_response()]
        agent = SummarizerAgent(service)

        result = agent.synthesize_research("AI news", docs)
        assert len(result.content_summaries) == 1
        assert len(result.paper_summaries) == 0

    def test_key_themes_parsed_as_list(self):
        docs = [_make_doc()]
        web_resp = "MAIN POINTS:\n- P\nSUMMARY:\nS."
        service = MagicMock()
        service.generate_text.side_effect = [web_resp, _make_synthesis_response()]
        agent = SummarizerAgent(service)

        result = agent.synthesize_research("Agentic AI", docs)
        assert "Autonomous decision-making" in result.key_themes

    def test_overview_and_synthesis_populated(self):
        docs = [_make_doc()]
        web_resp = "MAIN POINTS:\n- P\nSUMMARY:\nS."
        service = MagicMock()
        service.generate_text.side_effect = [web_resp, _make_synthesis_response()]
        agent = SummarizerAgent(service)

        result = agent.synthesize_research("Agentic AI", docs)
        assert "Agentic AI systems" in result.overview
        assert "alignment concerns" in result.synthesis

    def test_raises_on_empty_topic(self):
        agent = SummarizerAgent(_make_ai_service())
        with pytest.raises(SummarizerAgentError, match="topic must not be empty"):
            agent.synthesize_research("   ", [_make_doc()])

    def test_raises_on_empty_documents(self):
        agent = SummarizerAgent(_make_ai_service())
        with pytest.raises(SummarizerAgentError, match="No documents provided"):
            agent.synthesize_research("AI", [])

    def test_raises_when_synthesis_llm_call_fails(self):
        docs = [_make_doc()]
        web_resp = "MAIN POINTS:\n- P\nSUMMARY:\nS."
        service = MagicMock()
        service.generate_text.side_effect = [web_resp, RuntimeError("synthesis failed")]
        agent = SummarizerAgent(service)

        with pytest.raises(SummarizerAgentError, match="synthesis call failed"):
            agent.synthesize_research("AI", docs)

    def test_llm_called_once_per_document_plus_one_synthesis(self):
        docs = [_make_doc(), _make_doc(url="https://b.com")]
        web_resp = "MAIN POINTS:\n- P\nSUMMARY:\nS."
        service = MagicMock()
        service.generate_text.side_effect = [web_resp, web_resp, _make_synthesis_response()]
        agent = SummarizerAgent(service)

        agent.synthesize_research("AI", docs)
        assert service.generate_text.call_count == 3  # 2 docs + 1 synthesis


# ---------------------------------------------------------------------------
# Unit tests: improve_prompt
# ---------------------------------------------------------------------------


class TestImprovePrompt:
    def test_returns_improved_prompt_string(self):
        service = _make_ai_service("Improved: summarize the following research paper clearly.")
        agent = SummarizerAgent(service)
        result = agent.improve_prompt("summarize this", "research paper summarization")
        assert isinstance(result, str)
        assert "Improved" in result

    def test_raises_on_empty_base_prompt(self):
        agent = SummarizerAgent(_make_ai_service())
        with pytest.raises(SummarizerAgentError, match="base_prompt must not be empty"):
            agent.improve_prompt("   ")

    def test_prompt_sent_to_llm_contains_original_prompt(self):
        service = _make_ai_service("Better prompt.")
        agent = SummarizerAgent(service)
        agent.improve_prompt("original query text", "web summarization")
        call_arg = service.generate_text.call_args[0][0]
        assert "original query text" in call_arg
        assert "web summarization" in call_arg

    def test_raises_when_llm_fails(self):
        service = MagicMock()
        service.generate_text.side_effect = RuntimeError("api error")
        agent = SummarizerAgent(service)
        with pytest.raises(SummarizerAgentError, match="prompt improvement"):
            agent.improve_prompt("some prompt")

    def test_uses_default_context_when_not_provided(self):
        service = _make_ai_service("Better.")
        agent = SummarizerAgent(service)
        agent.improve_prompt("my prompt")
        call_arg = service.generate_text.call_args[0][0]
        assert "general summarization task" in call_arg
