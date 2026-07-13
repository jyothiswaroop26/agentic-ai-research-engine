from __future__ import annotations

from typing import Callable, Literal

from langgraph.graph import END, START, StateGraph

from app.agents.researcher import ResearchAgent, create_research_agent
from app.agents.summarizer import SummarizerAgent
from app.config import Settings, get_settings
from app.graph.state import WorkflowState, create_initial_state
from app.services.ai_service import AIService
from app.services.email_service import EmailService
from app.services.report_service import ReportService


class ResearchWorkflow:
	"""LangGraph workflow for research, summarization, report generation, and email."""

	def __init__(
		self,
		*,
		research_agent: ResearchAgent,
		summarizer_agent: SummarizerAgent,
		report_service: ReportService,
		email_sender: Callable[[str, str, str], None],
	) -> None:
		self._research_agent = research_agent
		self._summarizer_agent = summarizer_agent
		self._report_service = report_service
		self._email_sender = email_sender
		self._graph = self._build_graph().compile()

	def run(self, topic: str, recipient_email: str | None = None) -> WorkflowState:
		"""Execute the full LangGraph workflow for a given topic."""
		return self._graph.invoke(create_initial_state(topic=topic, recipient_email=recipient_email))

	# ------------------------------------------------------------------
	# Node definitions
	# ------------------------------------------------------------------

	def _research_node(self, state: WorkflowState) -> WorkflowState:
		topic = (state.get("topic") or "").strip()
		if not topic:
			raise ValueError("Research topic must not be empty.")
		dataset = self._research_agent.run(topic)
		return {"research_dataset": dataset}

	def _summarize_node(self, state: WorkflowState) -> WorkflowState:
		dataset = state.get("research_dataset")
		if dataset is None:
			raise ValueError("research_dataset is required before summarization.")
		synthesis = self._summarizer_agent.synthesize_research(
			topic=dataset.topic,
			documents=dataset.documents,
		)
		return {"synthesis": synthesis}

	def _report_node(self, state: WorkflowState) -> WorkflowState:
		synthesis = state.get("synthesis")
		if synthesis is None:
			raise ValueError("synthesis is required before report generation.")
		report_markdown = self._report_service.generate_markdown_report(synthesis)
		return {"report_markdown": report_markdown}

	def _email_node(self, state: WorkflowState) -> WorkflowState:
		recipient = (state.get("recipient_email") or "").strip()
		if not recipient:
			return {"email_status": "skipped"}

		body = state.get("report_markdown") or ""
		topic = state.get("topic") or "Research Topic"
		self._email_sender(recipient, f"Research Report: {topic}", body)
		return {"email_status": "sent"}

	def _email_route(self, state: WorkflowState) -> Literal["email", "end"]:
		recipient = (state.get("recipient_email") or "").strip()
		return "email" if recipient else "end"

	# ------------------------------------------------------------------
	# Graph assembly
	# ------------------------------------------------------------------

	def _build_graph(self) -> StateGraph:
		graph = StateGraph(WorkflowState)

		graph.add_node("research", self._research_node)
		graph.add_node("summarize", self._summarize_node)
		graph.add_node("report", self._report_node)
		graph.add_node("email", self._email_node)

		graph.add_edge(START, "research")
		graph.add_edge("research", "summarize")
		graph.add_edge("summarize", "report")
		graph.add_conditional_edges(
			"report",
			self._email_route,
			{
				"email": "email",
				"end": END,
			},
		)
		graph.add_edge("email", END)
		return graph


def create_research_workflow(settings: Settings | None = None) -> ResearchWorkflow:
	"""Factory for the default production workflow graph."""
	resolved_settings = settings or get_settings()

	ai_service = AIService(resolved_settings)
	email_service = EmailService()

	return ResearchWorkflow(
		research_agent=create_research_agent(),
		summarizer_agent=SummarizerAgent(ai_service),
		report_service=ReportService(),
		email_sender=email_service.send_report,
	)
