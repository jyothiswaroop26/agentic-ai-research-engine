"""Tests for the ReportAgent and ReportService."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agents.report_writer import (
	ReportAgent,
	ReportAgentError,
	create_report_agent,
)
from app.agents.summarizer import ContentSummary, PaperSummary, ResearchSynthesis
from app.services.report_service import ReportService, ReportValidationError


# ---------------------------------------------------------------------------
# Fixtures and Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_synthesis() -> ResearchSynthesis:
	"""Create a mock research synthesis for testing."""
	return ResearchSynthesis(
		topic="Machine Learning in Healthcare",
		overview="Machine learning is transforming healthcare by enabling early disease detection and personalized treatment.",
		key_themes=[
			"Diagnostic accuracy improvements",
			"Clinical decision support systems",
			"Patient outcome predictions",
		],
		sources_count=2,
		synthesis="Multiple research groups have demonstrated that ML algorithms can match or exceed human expert performance in medical imaging analysis and disease prediction.",
		paper_summaries=[
			PaperSummary(
				title="Deep Learning for Medical Image Analysis",
				url="https://example.com/paper1.pdf",
				summary="This paper reviews deep learning applications in medical imaging.",
				key_findings=[
					"CNNs achieve 95% accuracy in tumor detection",
					"Transfer learning improves performance with limited data",
				],
				methodology="Systematic literature review",
				implications="Deep learning models should be validated on diverse datasets before clinical deployment.",
			),
		],
		content_summaries=[
			ContentSummary(
				title="Healthcare AI Trends 2025",
				url="https://example.com/blog/ai-trends",
				summary="A blog discussing current trends in AI healthcare applications.",
				main_points=[
					"Explainability is critical for clinical adoption",
					"Data privacy remains a major concern",
				],
			),
		],
	)


@pytest.fixture
def minimal_synthesis() -> ResearchSynthesis:
	"""Create a minimal synthesis with just required fields."""
	return ResearchSynthesis(
		topic="AI Basics",
		overview="AI is transforming industries.",
		key_themes=["Machine Learning"],
		sources_count=1,
		synthesis="AI systems use data and algorithms.",
		paper_summaries=[],
		content_summaries=[],
	)


@pytest.fixture
def invalid_synthesis() -> ResearchSynthesis:
	"""Create an invalid synthesis missing required content."""
	return ResearchSynthesis(
		topic="",  # Empty topic
		overview=None,
		key_themes=[],
		sources_count=0,
		synthesis=None,
		paper_summaries=[],
		content_summaries=[],
	)


@pytest.fixture
def report_service() -> ReportService:
	"""Create a ReportService instance."""
	return ReportService()


@pytest.fixture
def report_agent(report_service: ReportService) -> ReportAgent:
	"""Create a ReportAgent instance."""
	return ReportAgent(report_service)


# ---------------------------------------------------------------------------
# Unit Tests: ReportService - Markdown Generation
# ---------------------------------------------------------------------------


class TestReportServiceMarkdown:
	def test_generates_basic_markdown(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that markdown report contains expected sections."""
		report = report_service.generate_markdown_report(mock_synthesis)

		assert "# Research Report: Machine Learning in Healthcare" in report
		assert "## Overview" in report
		assert "## Key Themes" in report
		assert "## Cross-Source Synthesis" in report
		assert "## Paper Summaries" in report
		assert "## Web Content Summaries" in report

	def test_markdown_includes_overview(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that markdown includes the overview text."""
		report = report_service.generate_markdown_report(mock_synthesis)
		assert "Machine learning is transforming healthcare" in report

	def test_markdown_includes_key_themes(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that markdown includes all key themes."""
		report = report_service.generate_markdown_report(mock_synthesis)
		for theme in mock_synthesis.key_themes:
			assert theme in report

	def test_markdown_includes_paper_details(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that markdown includes paper summary details."""
		report = report_service.generate_markdown_report(mock_synthesis)
		assert "Deep Learning for Medical Image Analysis" in report
		assert "CNNs achieve 95% accuracy" in report
		assert "Methodology: Systematic literature review" in report

	def test_markdown_includes_content_summaries(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that markdown includes web content summaries."""
		report = report_service.generate_markdown_report(mock_synthesis)
		assert "Healthcare AI Trends 2025" in report
		assert "Explainability is critical" in report

	def test_markdown_ends_with_newline(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that markdown report ends with a newline."""
		report = report_service.generate_markdown_report(mock_synthesis)
		assert report.endswith("\n")


# ---------------------------------------------------------------------------
# Unit Tests: ReportService - HTML Generation
# ---------------------------------------------------------------------------


class TestReportServiceHTML:
	def test_generates_valid_html(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that HTML report has proper structure."""
		html = report_service.generate_html_report(mock_synthesis, validate=False)

		assert html.startswith("<!DOCTYPE html")
		assert "<html" in html
		assert "<head" in html
		assert "<body" in html
		assert "</body>" in html
		assert "</html>" in html

	def test_html_includes_title(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that HTML includes the topic as title."""
		html = report_service.generate_html_report(mock_synthesis, validate=False)
		assert "Machine Learning in Healthcare" in html
		assert "<title>" in html

	def test_html_includes_styling(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that HTML includes CSS styling."""
		html = report_service.generate_html_report(mock_synthesis, validate=False)
		assert "<style>" in html
		assert "font-family" in html
		assert "color:" in html

	def test_html_includes_sections(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that HTML includes all report sections."""
		html = report_service.generate_html_report(mock_synthesis, validate=False)
		assert "Overview" in html
		assert "Key Themes" in html
		assert "Cross-Source Synthesis" in html
		assert "Paper Summaries" in html
		assert "Web Content Summaries" in html

	def test_html_includes_metadata(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that HTML includes generation metadata."""
		html = report_service.generate_html_report(mock_synthesis, validate=False)
		assert "Generated:" in html
		assert "Agentic AI Research Engine" in html

	def test_html_includes_links(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test that HTML includes source links."""
		html = report_service.generate_html_report(mock_synthesis, validate=False)
		assert "https://example.com/paper1.pdf" in html
		assert "https://example.com/blog/ai-trends" in html
		assert 'target="_blank"' in html


# ---------------------------------------------------------------------------
# Unit Tests: ReportService - Validation
# ---------------------------------------------------------------------------


class TestReportServiceValidation:
	def test_validates_complete_synthesis(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test validation of a complete synthesis."""
		result = report_service.validate_synthesis(mock_synthesis)
		assert result["is_valid"] is True
		assert len(result["issues"]) == 0

	def test_rejects_empty_topic(self, report_service: ReportService, invalid_synthesis: ResearchSynthesis):
		"""Test that synthesis with empty topic is invalid."""
		with pytest.raises(ReportValidationError) as exc_info:
			report_service.validate_synthesis(invalid_synthesis)
		assert "topic is required" in str(exc_info.value)

	def test_warns_on_empty_overview(self, report_service: ReportService):
		"""Test warning for missing overview."""
		synthesis = ResearchSynthesis(
			topic="Test",
			overview=None,
			key_themes=["Theme"],
			sources_count=0,
			synthesis="Content",
			paper_summaries=[],
			content_summaries=[],
		)
		result = report_service.validate_synthesis(synthesis)
		assert "overview is empty" in result["warnings"]

	def test_warns_on_short_content(self, report_service: ReportService):
		"""Test warning for very short content."""
		synthesis = ResearchSynthesis(
			topic="Test",
			overview="Too short",  # Less than 10 chars is borderline
			key_themes=["Theme"],
			sources_count=0,
			synthesis="Brief",
			paper_summaries=[],
			content_summaries=[],
		)
		result = report_service.validate_synthesis(synthesis)
		assert len(result["warnings"]) > 0

	def test_validates_markdown_report(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test validation of a markdown report."""
		report = report_service.generate_markdown_report(mock_synthesis)
		result = report_service.validate_report(report, format_type="markdown")

		assert result["is_valid"] is True
		assert result["format"] == "markdown"
		assert result["length"] > 0
		assert len(result["issues"]) == 0

	def test_validates_html_report(self, report_service: ReportService, mock_synthesis: ResearchSynthesis):
		"""Test validation of an HTML report."""
		html = report_service.generate_html_report(mock_synthesis, validate=False)
		result = report_service.validate_report(html, format_type="html")

		assert result["is_valid"] is True
		assert result["format"] == "html"
		assert result["length"] > 0
		assert len(result["issues"]) == 0

	def test_rejects_empty_report(self, report_service: ReportService):
		"""Test that empty report is invalid."""
		result = report_service.validate_report("", format_type="markdown")
		assert result["is_valid"] is False
		assert "empty" in result["issues"][0].lower()

	def test_rejects_report_without_headings(self, report_service: ReportService):
		"""Test that markdown without headings is invalid."""
		result = report_service.validate_report("Some random content", format_type="markdown")
		assert result["is_valid"] is False
		assert any("heading" in issue.lower() for issue in result["issues"])

	def test_rejects_invalid_html_structure(self, report_service: ReportService):
		"""Test that HTML without proper structure is invalid."""
		invalid_html = "<div>Some content</div>"
		result = report_service.validate_report(invalid_html, format_type="html")
		assert result["is_valid"] is False


# ---------------------------------------------------------------------------
# Unit Tests: ReportAgent - Generation
# ---------------------------------------------------------------------------


class TestReportAgentGeneration:
	def test_generates_markdown_report(self, report_agent: ReportAgent, mock_synthesis: ResearchSynthesis):
		"""Test that agent generates markdown report."""
		report = report_agent.generate_report(mock_synthesis, format_type="markdown")

		assert isinstance(report, str)
		assert "# Research Report:" in report
		assert "Machine Learning in Healthcare" in report

	def test_generates_html_report(self, report_agent: ReportAgent, mock_synthesis: ResearchSynthesis):
		"""Test that agent generates HTML report."""
		report = report_agent.generate_report(mock_synthesis, format_type="html")

		assert isinstance(report, str)
		assert "<!DOCTYPE html" in report
		assert "<body" in report

	def test_generates_both_formats(self, report_agent: ReportAgent, mock_synthesis: ResearchSynthesis):
		"""Test that agent generates both markdown and HTML."""
		result = report_agent.generate_report(mock_synthesis, format_type="both")

		assert isinstance(result, dict)
		assert "markdown" in result
		assert "html" in result
		assert isinstance(result["markdown"], str)
		assert isinstance(result["html"], str)
		assert len(result["markdown"]) > 0
		assert len(result["html"]) > 0

	def test_raises_on_none_synthesis(self, report_agent: ReportAgent):
		"""Test that agent raises error for None synthesis."""
		with pytest.raises(ReportAgentError) as exc_info:
			report_agent.generate_report(None)
		assert "synthesis is required" in str(exc_info.value)

	def test_raises_on_invalid_format(self, report_agent: ReportAgent, mock_synthesis: ResearchSynthesis):
		"""Test that agent raises error for invalid format."""
		with pytest.raises(ReportAgentError) as exc_info:
			report_agent.generate_report(mock_synthesis, format_type="invalid")  # type: ignore
		assert "Unknown format type" in str(exc_info.value)

	def test_validates_synthesis_by_default(self, report_agent: ReportAgent, invalid_synthesis: ResearchSynthesis):
		"""Test that validation is performed by default."""
		with pytest.raises(ReportAgentError) as exc_info:
			report_agent.generate_report(invalid_synthesis, validate=True)
		assert "Synthesis validation failed" in str(exc_info.value)

	def test_skips_validation_when_disabled(self, report_agent: ReportAgent, minimal_synthesis: ResearchSynthesis):
		"""Test that validation can be skipped."""
		# This should work even though the synthesis is minimal
		report = report_agent.generate_report(minimal_synthesis, validate=False)
		assert isinstance(report, str)
		assert "AI Basics" in report


# ---------------------------------------------------------------------------
# Unit Tests: ReportAgent - Validation
# ---------------------------------------------------------------------------


class TestReportAgentValidation:
	def test_validates_markdown_report(self, report_agent: ReportAgent, mock_synthesis: ResearchSynthesis):
		"""Test that agent can validate markdown reports."""
		report = report_agent.generate_report(mock_synthesis, format_type="markdown")
		result = report_agent.validate_report(report, format_type="markdown")

		assert result["is_valid"] is True

	def test_validates_html_report(self, report_agent: ReportAgent, mock_synthesis: ResearchSynthesis):
		"""Test that agent can validate HTML reports."""
		report = report_agent.generate_report(mock_synthesis, format_type="html")
		result = report_agent.validate_report(report, format_type="html")

		assert result["is_valid"] is True


# ---------------------------------------------------------------------------
# Unit Tests: ReportAgent - Format Conversion
# ---------------------------------------------------------------------------


class TestReportAgentConversion:
	def test_same_format_returns_unchanged(self, report_agent: ReportAgent):
		"""Test that converting to same format returns unchanged report."""
		original = "# Test Report\n\nContent"
		result = report_agent.convert_format(original, from_format="markdown", to_format="markdown")
		assert result == original

	def test_markdown_to_html_raises_error(self, report_agent: ReportAgent):
		"""Test that markdown to HTML conversion raises error without synthesis."""
		markdown = "# Test\n\nContent"
		with pytest.raises(ReportAgentError) as exc_info:
			report_agent.convert_format(markdown, from_format="markdown", to_format="html")
		assert "Cannot convert markdown to HTML" in str(exc_info.value)

	def test_html_to_markdown_raises_error(self, report_agent: ReportAgent):
		"""Test that HTML to markdown conversion is not supported."""
		html = "<html><body><h1>Test</h1></body></html>"
		with pytest.raises(ReportAgentError) as exc_info:
			report_agent.convert_format(html, from_format="html", to_format="markdown")
		assert "not supported" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestReportAgentIntegration:
	def test_full_report_generation_workflow(self, report_agent: ReportAgent, mock_synthesis: ResearchSynthesis):
		"""Test complete workflow from synthesis to validated report."""
		# Generate both formats
		reports = report_agent.generate_report(mock_synthesis, format_type="both", validate=True)

		# Validate both reports
		markdown_valid = report_agent.validate_report(reports["markdown"], format_type="markdown")
		html_valid = report_agent.validate_report(reports["html"], format_type="html")

		# Check both are valid
		assert markdown_valid["is_valid"] is True
		assert html_valid["is_valid"] is True

	def test_creates_agent_with_factory(self):
		"""Test that create_report_agent factory works."""
		agent = create_report_agent()
		assert isinstance(agent, ReportAgent)
		assert agent._report_service is not None

	def test_creates_agent_with_custom_service(self, report_service: ReportService):
		"""Test that factory accepts custom service."""
		agent = create_report_agent(report_service)
		assert agent._report_service is report_service
