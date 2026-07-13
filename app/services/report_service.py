from __future__ import annotations

from app.agents.summarizer import ContentSummary, PaperSummary, ResearchSynthesis


class ReportService:
	"""Builds markdown reports from synthesized research output."""

	def generate_markdown_report(self, synthesis: ResearchSynthesis) -> str:
		lines: list[str] = [
			f"# Research Report: {synthesis.topic}",
			"",
			"## Overview",
			synthesis.overview or "No overview generated.",
			"",
			"## Key Themes",
		]

		if synthesis.key_themes:
			lines.extend(f"- {theme}" for theme in synthesis.key_themes)
		else:
			lines.append("- No key themes generated.")

		lines.extend(["", "## Cross-Source Synthesis", synthesis.synthesis or "No synthesis generated.", ""])

		if synthesis.paper_summaries:
			lines.append("## Paper Summaries")
			lines.extend(self._render_paper_summary(item) for item in synthesis.paper_summaries)
			lines.append("")

		if synthesis.content_summaries:
			lines.append("## Web Content Summaries")
			lines.extend(self._render_content_summary(item) for item in synthesis.content_summaries)
			lines.append("")

		return "\n".join(lines).strip() + "\n"

	@staticmethod
	def _render_paper_summary(summary: PaperSummary) -> str:
		findings = "\n".join(f"- {item}" for item in summary.key_findings if item)
		return (
			f"### {summary.title}\n"
			f"Source: {summary.url}\n\n"
			f"Key Findings:\n{findings or '- None'}\n\n"
			f"Methodology: {summary.methodology or 'Not provided.'}\n\n"
			f"Implications: {summary.implications or 'Not provided.'}\n\n"
			f"Summary: {summary.summary or 'Not provided.'}\n"
		)

	@staticmethod
	def _render_content_summary(summary: ContentSummary) -> str:
		points = "\n".join(f"- {item}" for item in summary.main_points if item)
		return (
			f"### {summary.title}\n"
			f"Source: {summary.url}\n\n"
			f"Main Points:\n{points or '- None'}\n\n"
			f"Summary: {summary.summary or 'Not provided.'}\n"
		)
