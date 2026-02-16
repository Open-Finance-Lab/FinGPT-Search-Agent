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
