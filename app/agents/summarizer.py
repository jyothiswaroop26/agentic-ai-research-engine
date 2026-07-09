"""Summarization agent for research papers and web content."""
from __future__ import annotations

import textwrap
from dataclasses import dataclass, field

from app.agents.researcher import ResearchDocument
from app.services.ai_service import AIService


class SummarizerAgentError(Exception):
    """Raised when the summarization agent cannot complete a task."""


# ---------------------------------------------------------------------------
# Output data structures
# ---------------------------------------------------------------------------


@dataclass
class PaperSummary:
    title: str
    url: str
    key_findings: list[str]
    methodology: str
    implications: str
    summary: str


@dataclass
class ContentSummary:
    title: str
    url: str
    main_points: list[str]
    summary: str


@dataclass
class ResearchSynthesis:
    topic: str
    overview: str
    key_themes: list[str]
    sources_count: int
    paper_summaries: list[PaperSummary] = field(default_factory=list)
    content_summaries: list[ContentSummary] = field(default_factory=list)
    synthesis: str = ""


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_PAPER_SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert research analyst. When given a research paper's title and content,
    produce a structured summary with:
    - KEY FINDINGS: 3-5 bullet points capturing the main results or claims
    - METHODOLOGY: one sentence describing the research approach
    - IMPLICATIONS: one sentence on real-world impact or future directions
    - SUMMARY: 2-3 sentences combining the above into a cohesive paragraph

    Be precise, avoid jargon where possible, and never invent facts not present in the text.
""")

_WEB_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a concise content analyst. When given a web page title and excerpt,
    produce a structured summary with:
    - MAIN POINTS: 2-4 bullet points capturing the most important ideas
    - SUMMARY: 1-2 sentences distilling the core message

    Be factual and objective. Only include information present in the provided text.
""")

_SYNTHESIS_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a senior research synthesizer. Given a research topic and a set of
    individual source summaries, produce an integrated synthesis with:
    - OVERVIEW: 2-3 sentences describing the current state of the topic
    - KEY THEMES: 3-6 recurring themes or patterns across all sources
    - SYNTHESIS: a 3-5 sentence paragraph that weaves together the evidence,
      highlights consensus and disagreements, and points to future directions

    Draw only from the provided summaries. Do not introduce outside information.
""")


def _build_paper_prompt(doc: ResearchDocument) -> str:
    return textwrap.dedent(f"""\
        Title: {doc.title}
        Source: {doc.url}
        Published: {doc.published_date or "unknown"}

        Content:
        {doc.snippet}

        Provide the structured summary using the sections KEY FINDINGS, METHODOLOGY,
        IMPLICATIONS, and SUMMARY.
    """)


def _build_web_content_prompt(doc: ResearchDocument) -> str:
    return textwrap.dedent(f"""\
        Title: {doc.title}
        Source: {doc.url}

        Excerpt:
        {doc.snippet}

        Provide the structured summary using the sections MAIN POINTS and SUMMARY.
    """)


def _build_synthesis_prompt(topic: str, summaries: list[str]) -> str:
    joined = "\n\n---\n\n".join(summaries)
    return textwrap.dedent(f"""\
        Research Topic: {topic}

        Individual Source Summaries:

        {joined}

        Provide the synthesis using the sections OVERVIEW, KEY THEMES, and SYNTHESIS.
    """)


def _build_improved_prompt(base_prompt: str, context: str) -> str:
    return textwrap.dedent(f"""\
        You are a prompt-engineering expert. Improve the following prompt so that it
        yields more accurate, structured, and relevant responses from a language model.
        Preserve the original intent while making it clearer, more specific, and less
        ambiguous. Return only the improved prompt text with no additional commentary.

        Context about the task: {context}

        Original prompt:
        {base_prompt}
    """)


# ---------------------------------------------------------------------------
# Parser helpers
# ---------------------------------------------------------------------------


def _extract_section(text: str, section: str) -> str:
    """Extract a named section from LLM output."""
    upper = text.upper()
    start_marker = section.upper() + ":"
    start = upper.find(start_marker)
    if start == -1:
        return ""
    content_start = start + len(start_marker)
    # Find next known section header or end of text
    next_section = len(text)
    for marker in ("KEY FINDINGS:", "METHODOLOGY:", "IMPLICATIONS:", "SUMMARY:",
                   "MAIN POINTS:", "OVERVIEW:", "KEY THEMES:", "SYNTHESIS:"):
        if marker == start_marker:
            continue
        pos = upper.find(marker, content_start)
        if pos != -1 and pos < next_section:
            next_section = pos
    return text[content_start:next_section].strip()


def _parse_bullet_list(text: str) -> list[str]:
    """Parse bullet points from a section text."""
    bullets: list[str] = []
    for line in text.splitlines():
        line = line.strip().lstrip("-•*").strip()
        if line:
            bullets.append(line)
    return bullets


def _is_research_paper(doc: ResearchDocument) -> bool:
    """Heuristic: treat as research paper if from arxiv/semantic scholar/pubmed."""
    paper_domains = {"arxiv.org", "semanticscholar.org", "pubmed.ncbi.nlm.nih.gov",
                     "scholar.google.com", "researchgate.net", "acm.org", "ieee.org",
                     "springer.com", "nature.com", "sciencedirect.com"}
    return any(pd in doc.domain for pd in paper_domains)


# ---------------------------------------------------------------------------
# Summarizer agent
# ---------------------------------------------------------------------------


class SummarizerAgent:
    """Agent that summarizes research papers and web content using an LLM."""

    def __init__(self, ai_service: AIService) -> None:
        self._ai = ai_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def summarize_paper(self, doc: ResearchDocument) -> PaperSummary:
        """Summarize a single research paper document.

        Args:
            doc: A :class:`ResearchDocument` from the research agent.

        Returns:
            A structured :class:`PaperSummary`.

        Raises:
            SummarizerAgentError: If the document content is missing or the LLM call fails.
        """
        if not doc.snippet:
            raise SummarizerAgentError(f"Document '{doc.title}' has no content to summarize.")

        prompt = f"{_PAPER_SYSTEM_PROMPT}\n\n{_build_paper_prompt(doc)}"
        try:
            raw = self._ai.generate_text(prompt)
        except Exception as exc:
            raise SummarizerAgentError(f"LLM call failed for paper '{doc.title}': {exc}") from exc

        key_findings_text = _extract_section(raw, "KEY FINDINGS")
        return PaperSummary(
            title=doc.title,
            url=doc.url,
            key_findings=_parse_bullet_list(key_findings_text) or [key_findings_text],
            methodology=_extract_section(raw, "METHODOLOGY"),
            implications=_extract_section(raw, "IMPLICATIONS"),
            summary=_extract_section(raw, "SUMMARY"),
        )

    def summarize_web_content(self, doc: ResearchDocument) -> ContentSummary:
        """Summarize a single web content document.

        Args:
            doc: A :class:`ResearchDocument` from the research agent.

        Returns:
            A structured :class:`ContentSummary`.

        Raises:
            SummarizerAgentError: If the document content is missing or the LLM call fails.
        """
        if not doc.snippet:
            raise SummarizerAgentError(f"Document '{doc.title}' has no content to summarize.")

        prompt = f"{_WEB_SYSTEM_PROMPT}\n\n{_build_web_content_prompt(doc)}"
        try:
            raw = self._ai.generate_text(prompt)
        except Exception as exc:
            raise SummarizerAgentError(f"LLM call failed for '{doc.title}': {exc}") from exc

        main_points_text = _extract_section(raw, "MAIN POINTS")
        return ContentSummary(
            title=doc.title,
            url=doc.url,
            main_points=_parse_bullet_list(main_points_text) or [main_points_text],
            summary=_extract_section(raw, "SUMMARY"),
        )

    def synthesize_research(
        self,
        topic: str,
        documents: list[ResearchDocument],
    ) -> ResearchSynthesis:
        """Summarize all documents and synthesize them into a cohesive research brief.

        Documents are automatically classified as research papers or web content based
        on their domain. Each is individually summarized before synthesis.

        Args:
            topic: The overarching research topic.
            documents: List of documents from the research agent.

        Returns:
            A :class:`ResearchSynthesis` containing per-document summaries and an
            integrated synthesis.

        Raises:
            SummarizerAgentError: If ``documents`` is empty or synthesis fails.
        """
        if not topic or not topic.strip():
            raise SummarizerAgentError("Research topic must not be empty.")
        if not documents:
            raise SummarizerAgentError("No documents provided for synthesis.")

        paper_summaries: list[PaperSummary] = []
        content_summaries: list[ContentSummary] = []
        flat_summaries: list[str] = []

        for doc in documents:
            if _is_research_paper(doc):
                ps = self.summarize_paper(doc)
                paper_summaries.append(ps)
                flat_summaries.append(
                    f"[Paper] {ps.title}\n"
                    f"Key Findings: {'; '.join(ps.key_findings)}\n"
                    f"Methodology: {ps.methodology}\n"
                    f"Implications: {ps.implications}"
                )
            else:
                cs = self.summarize_web_content(doc)
                content_summaries.append(cs)
                flat_summaries.append(
                    f"[Web] {cs.title}\n"
                    f"Main Points: {'; '.join(cs.main_points)}\n"
                    f"Summary: {cs.summary}"
                )

        synthesis_prompt = (
            f"{_SYNTHESIS_SYSTEM_PROMPT}\n\n"
            f"{_build_synthesis_prompt(topic, flat_summaries)}"
        )
        try:
            raw_synthesis = self._ai.generate_text(synthesis_prompt)
        except Exception as exc:
            raise SummarizerAgentError(f"LLM synthesis call failed: {exc}") from exc

        key_themes_text = _extract_section(raw_synthesis, "KEY THEMES")
        return ResearchSynthesis(
            topic=topic,
            overview=_extract_section(raw_synthesis, "OVERVIEW"),
            key_themes=_parse_bullet_list(key_themes_text) or [key_themes_text],
            sources_count=len(documents),
            paper_summaries=paper_summaries,
            content_summaries=content_summaries,
            synthesis=_extract_section(raw_synthesis, "SYNTHESIS"),
        )

    def improve_prompt(self, base_prompt: str, context: str = "") -> str:
        """Use the LLM to refine a prompt for higher quality outputs.

        Args:
            base_prompt: The prompt text to improve.
            context: Optional description of the task for guidance.

        Returns:
            An improved version of the prompt.

        Raises:
            SummarizerAgentError: If ``base_prompt`` is empty or the LLM call fails.
        """
        if not base_prompt or not base_prompt.strip():
            raise SummarizerAgentError("base_prompt must not be empty.")

        prompt = _build_improved_prompt(base_prompt, context or "general summarization task")
        try:
            return self._ai.generate_text(prompt)
        except Exception as exc:
            raise SummarizerAgentError(f"LLM call failed during prompt improvement: {exc}") from exc
