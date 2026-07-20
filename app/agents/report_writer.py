from __future__ import annotations

from typing import Literal

from app.agents.summarizer import ResearchSynthesis
from app.services.report_service import ReportService, ReportValidationError


class ReportAgentError(Exception):
	"""Raised when the report agent cannot generate a report."""


class ReportAgent:
	"""Agent responsible for turning synthesis output into a final report."""

	def __init__(self, report_service: ReportService) -> None:
		self._report_service = report_service

	def generate_report(
		self,
		synthesis: ResearchSynthesis,
		format_type: Literal["markdown", "html", "both"] = "markdown",
		validate: bool = True,
	) -> str | dict[str, str]:
		"""Generate a report from a synthesized research payload.
		
		Args:
			synthesis: The research synthesis to report on.
			format_type: Output format - "markdown", "html", or "both".
			validate: Whether to validate the synthesis before generation.
			
		Returns:
			For format_type="markdown" or "html": the report string.
			For format_type="both": dict with "markdown" and "html" keys.
			
		Raises:
			ReportAgentError: If synthesis is invalid or report generation fails.
		"""
		if synthesis is None:
			raise ReportAgentError("synthesis is required before report generation.")

		try:
			# Validate synthesis first if requested
			if validate:
				self._report_service.validate_synthesis(synthesis)

			# Generate the requested format(s)
			if format_type == "markdown":
				return self._report_service.generate_markdown_report(synthesis)
			elif format_type == "html":
				return self._report_service.generate_html_report(synthesis, validate=False)
			elif format_type == "both":
				markdown_report = self._report_service.generate_markdown_report(synthesis)
				html_report = self._report_service.generate_html_report(synthesis, validate=False)
				return {
					"markdown": markdown_report,
					"html": html_report,
				}
			else:
				raise ReportAgentError(f"Unknown format type: {format_type}")

		except ReportValidationError as exc:
			raise ReportAgentError(f"Synthesis validation failed: {exc}") from exc
		except Exception as exc:
			raise ReportAgentError(f"Report generation failed: {exc}") from exc

	def validate_report(self, report: str, format_type: Literal["markdown", "html"] = "markdown") -> dict:
		"""Validate a generated report."""
		return self._report_service.validate_report(report, format_type)

	def convert_format(self, report: str, from_format: Literal["markdown", "html"], to_format: Literal["markdown", "html"]) -> str:
		"""Convert a report between formats.
		
		Note: Conversion from HTML to markdown is not fully supported and may lose formatting.
		"""
		if from_format == to_format:
			return report

		if from_format == "markdown" and to_format == "html":
			# For markdown to HTML, we need the synthesis object, so we'll raise an error
			raise ReportAgentError("Cannot convert markdown to HTML without the original synthesis. Use generate_report() with format='html' instead.")

		if from_format == "html" and to_format == "markdown":
			# HTML to markdown conversion is limited
			raise ReportAgentError("HTML to markdown conversion is not supported. Please generate from the synthesis directly.")

		return report


def create_report_agent(report_service: ReportService | None = None) -> ReportAgent:
	"""Build a :class:`ReportAgent` with a default report service."""
	return ReportAgent(report_service=report_service or ReportService())
