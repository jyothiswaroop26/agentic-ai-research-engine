from __future__ import annotations

from app.agents.summarizer import ResearchSynthesis
from app.services.report_service import ReportService


class ReportAgentError(Exception):
	"""Raised when the report agent cannot generate a report."""


class ReportAgent:
	"""Agent responsible for turning synthesis output into a final report."""

	def __init__(self, report_service: ReportService) -> None:
		self._report_service = report_service

	def generate_report(self, synthesis: ResearchSynthesis) -> str:
		"""Generate a markdown report from a synthesized research payload."""
		if synthesis is None:
			raise ReportAgentError("synthesis is required before report generation.")

		try:
			return self._report_service.generate_markdown_report(synthesis)
		except Exception as exc:
			raise ReportAgentError(f"Report generation failed: {exc}") from exc


def create_report_agent(report_service: ReportService | None = None) -> ReportAgent:
	"""Build a :class:`ReportAgent` with a default report service."""
	return ReportAgent(report_service=report_service or ReportService())
