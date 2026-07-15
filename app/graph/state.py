from __future__ import annotations

from typing import TypedDict

from app.agents.researcher import ResearchDataset
from app.agents.summarizer import ResearchSynthesis


class WorkflowState(TypedDict, total=False):
	"""Shared state object passed between LangGraph workflow nodes."""

	topic: str
	recipient_email: str | None
	research_dataset: ResearchDataset
	synthesis: ResearchSynthesis
	report_markdown: str
	email_status: str
	execution_trace: list[str]


def create_initial_state(topic: str, recipient_email: str | None = None) -> WorkflowState:
	"""Build an initial workflow state payload for graph invocation."""
	return {
		"topic": topic,
		"recipient_email": recipient_email,
		"execution_trace": [],
	}
