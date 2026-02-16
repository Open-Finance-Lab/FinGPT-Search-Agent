"""Tests for the multi-step research engine."""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ── QueryAnalyzer tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_query_analyzer_simple_query_bypasses():
    """Simple single-ticker queries should not need decomposition."""
    from datascraper.research_engine import QueryAnalyzer

    # Mock the OpenAI Chat Completions call
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "needs_decomposition": False,
        "sub_questions": []
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        analyzer = QueryAnalyzer()
        plan = await analyzer.analyze("What is AAPL stock price?")

    assert plan["needs_decomposition"] is False
    assert plan["sub_questions"] == []


@pytest.mark.asyncio
async def test_query_analyzer_complex_query_decomposes():
    """Multi-part queries should be decomposed into sub-questions."""
    from datascraper.research_engine import QueryAnalyzer

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "needs_decomposition": True,
        "sub_questions": [
            {"question": "AAPL quarterly revenue Q2-Q4 2025", "type": "numerical"},
            {"question": "MSFT quarterly revenue Q2-Q4 2025", "type": "numerical"},
        ]
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        analyzer = QueryAnalyzer()
        plan = await analyzer.analyze("Compare AAPL and MSFT revenue growth over the last 3 quarters")

    assert plan["needs_decomposition"] is True
    assert len(plan["sub_questions"]) == 2
    assert plan["sub_questions"][0]["type"] == "numerical"


@pytest.mark.asyncio
async def test_query_analyzer_caps_sub_questions():
    """Sub-questions should be capped at max_sub_questions."""
    from datascraper.research_engine import QueryAnalyzer

    # Return 8 sub-questions, should be capped to 5
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "needs_decomposition": True,
        "sub_questions": [{"question": f"Q{i}", "type": "qualitative"} for i in range(8)]
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        analyzer = QueryAnalyzer(max_sub_questions=5)
        plan = await analyzer.analyze("Very complex query")

    assert len(plan["sub_questions"]) == 5


@pytest.mark.asyncio
async def test_query_analyzer_handles_malformed_json():
    """If the LLM returns invalid JSON, fall back to no-decomposition."""
    from datascraper.research_engine import QueryAnalyzer

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "not valid json {{"

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        analyzer = QueryAnalyzer()
        plan = await analyzer.analyze("Some query")

    assert plan["needs_decomposition"] is False


# ── ResearchExecutor tests ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_executor_routes_numerical_to_mcp():
    """Numerical sub-questions should attempt MCP first."""
    from datascraper.research_engine import ResearchExecutor

    plan = {
        "sub_questions": [
            {"question": "AAPL current stock price", "type": "numerical"},
        ]
    }

    with patch("datascraper.research_engine._try_mcp_search", new_callable=AsyncMock, return_value="$152.34") as mcp_mock, \
         patch("datascraper.research_engine._web_search", new_callable=AsyncMock) as web_mock:
        executor = ResearchExecutor(model="gpt-5.2-chat-latest", message_list=[], preferred_urls=[])
        results = await executor.execute(plan)

    assert len(results) == 1
    assert results[0]["answer"] == "$152.34"
    assert results[0]["source"] == "mcp"
    mcp_mock.assert_called_once()
    web_mock.assert_not_called()


@pytest.mark.asyncio
async def test_executor_falls_back_to_web_on_mcp_failure():
    """If MCP fails for numerical, fall back to web search."""
    from datascraper.research_engine import ResearchExecutor

    plan = {
        "sub_questions": [
            {"question": "AAPL quarterly revenue", "type": "numerical"},
        ]
    }

    with patch("datascraper.research_engine._try_mcp_search", new_callable=AsyncMock, return_value=None), \
         patch("datascraper.research_engine._web_search", new_callable=AsyncMock, return_value=("Revenue was $94.9B", [{"url": "https://yahoo.com"}])):
        executor = ResearchExecutor(model="gpt-5.2-chat-latest", message_list=[], preferred_urls=[])
        results = await executor.execute(plan)

    assert results[0]["source"] == "web"
    assert "94.9B" in results[0]["answer"]


@pytest.mark.asyncio
async def test_executor_routes_qualitative_to_web():
    """Qualitative sub-questions go straight to web search."""
    from datascraper.research_engine import ResearchExecutor

    plan = {
        "sub_questions": [
            {"question": "Latest AAPL earnings analysis", "type": "qualitative"},
        ]
    }

    with patch("datascraper.research_engine._try_mcp_search", new_callable=AsyncMock) as mcp_mock, \
         patch("datascraper.research_engine._web_search", new_callable=AsyncMock, return_value=("Analysts say...", [{"url": "https://cnbc.com"}])):
        executor = ResearchExecutor(model="gpt-5.2-chat-latest", message_list=[], preferred_urls=[])
        results = await executor.execute(plan)

    mcp_mock.assert_not_called()
    assert results[0]["source"] == "web"


@pytest.mark.asyncio
async def test_executor_skips_analytical():
    """Analytical sub-questions produce a placeholder (no search)."""
    from datascraper.research_engine import ResearchExecutor

    plan = {
        "sub_questions": [
            {"question": "Compare growth rates", "type": "analytical"},
        ]
    }

    with patch("datascraper.research_engine._try_mcp_search", new_callable=AsyncMock) as mcp_mock, \
         patch("datascraper.research_engine._web_search", new_callable=AsyncMock) as web_mock:
        executor = ResearchExecutor(model="gpt-5.2-chat-latest", message_list=[], preferred_urls=[])
        results = await executor.execute(plan)

    mcp_mock.assert_not_called()
    web_mock.assert_not_called()
    assert results[0]["source"] == "deferred"
