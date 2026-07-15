from __future__ import annotations

from typing import Callable, Literal

from langgraph.graph import END, START, StateGraph

from app.agents.report_writer import ReportAgent, create_report_agent
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
		report_agent: ReportAgent | None = None,
		report_service: ReportService | None = None,
		email_sender: Callable[[str, str, str], None],
	) -> None:
		self._research_agent = research_agent
		self._summarizer_agent = summarizer_agent
		resolved_report_agent = report_agent
		if resolved_report_agent is None:
			resolved_report_service = report_service or ReportService()
			resolved_report_agent = ReportAgent(resolved_report_service)
		self._report_agent = resolved_report_agent
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
		execution_trace = list(state.get("execution_trace", []))
		execution_trace.append("research")
		return {
			"research_dataset": dataset,
			"execution_trace": execution_trace,
		}

	def _summarize_node(self, state: WorkflowState) -> WorkflowState:
		dataset = state.get("research_dataset")
		if dataset is None:
			raise ValueError("research_dataset is required before summarization.")
		synthesis = self._summarizer_agent.synthesize_research(
			topic=dataset.topic,
			documents=dataset.documents,
		)
		execution_trace = list(state.get("execution_trace", []))
		execution_trace.append("summarize")
		return {
			"synthesis": synthesis,
			"execution_trace": execution_trace,
		}

	def _report_node(self, state: WorkflowState) -> WorkflowState:
		synthesis = state.get("synthesis")
		if synthesis is None:
			raise ValueError("synthesis is required before report generation.")
		report_markdown = self._report_agent.generate_report(synthesis)
		execution_trace = list(state.get("execution_trace", []))
		execution_trace.append("report")
		return {
			"report_markdown": report_markdown,
			"execution_trace": execution_trace,
		}

	def _email_node(self, state: WorkflowState) -> WorkflowState:
		recipient = (state.get("recipient_email") or "").strip()
		execution_trace = list(state.get("execution_trace", []))
		execution_trace.append("email")
		if not recipient:
			return {
				"email_status": "skipped",
				"execution_trace": execution_trace,
			}

		body = state.get("report_markdown") or ""
		topic = state.get("topic") or "Research Topic"
		self._email_sender(recipient, f"Research Report: {topic}", body)
		return {
			"email_status": "sent",
			"execution_trace": execution_trace,
		}

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
		report_agent=create_report_agent(ReportService()),
		email_sender=email_service.send_report,
	)
