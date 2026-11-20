import asyncio
from unittest.mock import AsyncMock

import pytest
from core.state import ResearchState

def test_state_initialization():
    state: ResearchState = {
        "topic": "Test", "document_name": "", "document_context": "",
        "research_questions": ["Q1", "Q2"], "search_results": [],
        "search_errors": [],
        "conflicts": [], "research_draft": None, "critic_score": None,
        "critic_feedback": None, "research_iterations": 0, "max_research_iterations": 2,
        "fact_check_report": None, "sources": []
    }
    assert state["topic"] == "Test"

def test_api_security_import():
    # Check if FastAPI app loads without errors
    from api.app import app
    assert app.title == "Multi-Agent Fact Checker API"


def test_api_stream_reports_graph_failure(monkeypatch, caplog):
    from api.app import ResearchRequest, graph, research_stream

    async def failing_astream(*args, **kwargs):
        if False:
            yield {}
        raise RuntimeError("simulated node failure")

    monkeypatch.setattr(graph, "astream", failing_astream)

    async def collect_events():
        response = await research_stream(ResearchRequest(topic="test topic"))
        return [chunk async for chunk in response.body_iterator]

    body = "".join(asyncio.run(collect_events()))

    assert "event: error" in body
    assert "Research failed. Check the API server logs for details." in body
    assert "simulated node failure" in caplog.text


def test_api_forwards_uploaded_document_context(monkeypatch):
    from api.app import ResearchRequest, graph, research_stream

    captured_state = {}

    async def successful_astream(state, stream_mode):
        captured_state.update(state)
        yield {"planner": {"research_questions": []}}

    monkeypatch.setattr(graph, "astream", successful_astream)

    async def collect_events():
        response = await research_stream(
            ResearchRequest(
                topic="Research this report",
                document_name="company-report.pdf",
                document_context="Revenue increased during the reporting period.",
            )
        )
        return "".join([chunk async for chunk in response.body_iterator])

    body = asyncio.run(collect_events())

    assert "[DONE]" in body
    assert captured_state["document_name"] == "company-report.pdf"
    assert captured_state["document_context"] == (
        "Revenue increased during the reporting period."
    )


def test_search_deduplicates_results_and_reports_partial_failure(monkeypatch):
    from agents import searcher

    class FakeTavilyClient:
        def __init__(self, api_key):
            self.search = AsyncMock(side_effect=[
                {"results": [{"url": "https://example.com/a", "content": "Evidence"}]},
                RuntimeError("temporary search failure"),
            ])

    monkeypatch.setattr(searcher, "AsyncTavilyClient", FakeTavilyClient)
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    state = {
        "topic": "Example topic",
        "research_questions": ["Question one", "Question two"],
        "search_results": [{"url": "https://example.com/a", "content": "Old evidence"}],
        "research_iterations": 0,
    }

    result = asyncio.run(searcher.search_node(state))

    assert result["search_results"] == []
    assert result["search_errors"] == ["RuntimeError: temporary search failure"]


def test_fact_checker_returns_uncertain_for_invalid_tavily_query(monkeypatch):
    from agents import fact_checker
    from tavily.errors import BadRequestError

    class FakeTavilyClient:
        def __init__(self, api_key):
            self.search = AsyncMock(side_effect=BadRequestError("Query is invalid."))

    class FakeExtractionLLM:
        def with_structured_output(self, schema, **kwargs):
            return self

        async def ainvoke(self, prompt):
            return fact_checker.ClaimList(claims=["A sufficiently detailed factual claim."])

    monkeypatch.setattr(fact_checker, "AsyncTavilyClient", FakeTavilyClient)
    monkeypatch.setattr(fact_checker, "ChatGroq", lambda **kwargs: FakeExtractionLLM())
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    result = asyncio.run(
        fact_checker.fact_check_node(
            {
                "research_draft": "A report with evidence-backed claims.",
                "search_results": [
                    {"url": "https://example.com/source", "content": "Some evidence."}
                ],
            }
        )
    )

    assert result["fact_check_report"]["checks"] == [
        {
            "claim": "A sufficiently detailed factual claim.",
            "verdict": "Uncertain",
            "confidence": 0.0,
            "evidence_url": None,
            "reason": "Tavily rejected the verification query: Query is invalid.",
        }
    ]


def test_conflict_detector_rejects_unknown_source_citations(monkeypatch):
    from agents import conflict

    class FakeConflictLLM:
        def invoke(self, prompt):
            return conflict.ConflictReport(
                conflicts=[
                    conflict.ConflictItem(
                        claim="A claim",
                        source_a_says="Yes",
                        source_a_url="https://example.com/known",
                        source_b_says="No",
                        source_b_url="https://example.com/not-retrieved",
                    )
                ]
            )

    monkeypatch.setattr(conflict, "conflict_llm", FakeConflictLLM())
    result = conflict.conflict_node(
        {
            "topic": "Example topic",
            "search_results": [
                {"url": "https://example.com/known", "content": "Evidence"}
            ],
        }
    )

    assert result["conflicts"] == []