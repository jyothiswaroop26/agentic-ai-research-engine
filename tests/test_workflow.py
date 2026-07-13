from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.agents.researcher import ResearchDataset, ResearchDocument
from app.agents.summarizer import ResearchSynthesis
from app.graph.workflow import ResearchWorkflow
from app.services.report_service import ReportService


@dataclass
class FakeResearchAgent:
    calls: int = 0

    def run(self, topic: str) -> ResearchDataset:
        self.calls += 1
        return ResearchDataset(
            topic=topic,
            generated_queries=[topic],
            total_documents=1,
            documents=[
                ResearchDocument(
                    title="Doc 1",
                    url="https://example.com/doc-1",
                    snippet="Important context",
                    score=0.9,
                    source_query=topic,
                    domain="example.com",
                )
            ],
            sources_by_domain={"example.com": 1},
        )


@dataclass
class FakeSummarizerAgent:
    calls: int = 0

    def synthesize_research(self, topic: str, documents: list[ResearchDocument]) -> ResearchSynthesis:
        self.calls += 1
        return ResearchSynthesis(
            topic=topic,
            overview="Overview",
            key_themes=["Theme A", "Theme B"],
            sources_count=len(documents),
            synthesis="Integrated synthesis",
        )


def test_workflow_executes_research_to_report_without_email():
    research_agent = FakeResearchAgent()
    summarizer = FakeSummarizerAgent()
    sent_messages: list[tuple[str, str, str]] = []

    workflow = ResearchWorkflow(
        research_agent=research_agent,
        summarizer_agent=summarizer,
        report_service=ReportService(),
        email_sender=lambda recipient, subject, body: sent_messages.append((recipient, subject, body)),
    )

    result = workflow.run(topic="agentic ai")

    assert research_agent.calls == 1
    assert summarizer.calls == 1
    assert result["research_dataset"].topic == "agentic ai"
    assert result["synthesis"].overview == "Overview"
    assert "# Research Report: agentic ai" in result["report_markdown"]
    assert sent_messages == []


def test_workflow_routes_to_email_when_recipient_provided():
    research_agent = FakeResearchAgent()
    summarizer = FakeSummarizerAgent()
    sent_messages: list[tuple[str, str, str]] = []

    workflow = ResearchWorkflow(
        research_agent=research_agent,
        summarizer_agent=summarizer,
        report_service=ReportService(),
        email_sender=lambda recipient, subject, body: sent_messages.append((recipient, subject, body)),
    )

    result = workflow.run(topic="langgraph", recipient_email="user@example.com")

    assert result["email_status"] == "sent"
    assert len(sent_messages) == 1
    recipient, subject, body = sent_messages[0]
    assert recipient == "user@example.com"
    assert subject == "Research Report: langgraph"
    assert "# Research Report: langgraph" in body


def test_workflow_rejects_empty_topic():
    workflow = ResearchWorkflow(
        research_agent=FakeResearchAgent(),
        summarizer_agent=FakeSummarizerAgent(),
        report_service=ReportService(),
        email_sender=lambda _recipient, _subject, _body: None,
    )

    with pytest.raises(ValueError, match="must not be empty"):
        workflow.run(topic="   ")
