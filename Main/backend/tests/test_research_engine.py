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


# ── GapDetector tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gap_detector_complete():
    """When all data is present, gap detector returns complete=True."""
    from datascraper.research_engine import GapDetector

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "complete": True,
        "gaps": [],
        "follow_up_queries": []
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        detector = GapDetector()
        result = await detector.detect(
            original_query="What is AAPL price?",
            plan={"sub_questions": [{"question": "AAPL price", "type": "numerical"}]},
            results=[{"question": "AAPL price", "answer": "$152.34", "source": "mcp"}],
        )

    assert result["complete"] is True
    assert result["follow_up_queries"] == []


@pytest.mark.asyncio
async def test_gap_detector_finds_gaps():
    """When data is missing, gap detector returns follow-up queries."""
    from datascraper.research_engine import GapDetector

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "complete": False,
        "gaps": ["Missing MSFT Q3 revenue"],
        "follow_up_queries": [
            {"question": "MSFT Q3 2025 revenue", "type": "qualitative"}
        ]
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=mock_response):
        detector = GapDetector()
        result = await detector.detect(
            original_query="Compare AAPL and MSFT revenue",
            plan={"sub_questions": []},
            results=[{"question": "AAPL revenue", "answer": "$94.9B"}],
        )

    assert result["complete"] is False
    assert len(result["follow_up_queries"]) == 1


# ── Synthesizer tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_synthesizer_combines_results():
    """Synthesizer should produce a final response from collected results."""
    from datascraper.research_engine import Synthesizer

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "AAPL revenue was $94.9B, MSFT was $64.7B. AAPL grew 8% vs MSFT 12%."

    with patch("datascraper.research_engine._call_synthesis", new_callable=AsyncMock, return_value=mock_response):
        synth = Synthesizer(model="gpt-5.2-chat-latest")
        text = await synth.synthesize(
            original_query="Compare AAPL and MSFT revenue",
            results=[
                {"question": "AAPL revenue", "answer": "$94.9B", "sources": []},
                {"question": "MSFT revenue", "answer": "$64.7B", "sources": []},
            ],
        )

    assert "AAPL" in text
    assert "MSFT" in text


# ── Full orchestration tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_iterative_simple_query_bypasses():
    """Simple queries should bypass the research engine entirely."""
    from datascraper.research_engine import run_iterative_research

    analyzer_response = MagicMock()
    analyzer_response.choices = [MagicMock()]
    analyzer_response.choices[0].message.content = json.dumps({
        "needs_decomposition": False, "sub_questions": []
    })

    with patch("datascraper.research_engine._call_planner", new_callable=AsyncMock, return_value=analyzer_response):
        result = await run_iterative_research(
            user_input="What is AAPL price?",
            message_list=[],
            model="gpt-5.2-chat-latest",
        )

    # Should return None to signal "use existing single-search path"
    assert result is None


@pytest.mark.asyncio
async def test_run_iterative_full_loop():
    """Complex query runs full loop: analyze -> execute -> gap detect -> synthesize."""
    from datascraper.research_engine import run_iterative_research

    # 1. Analyzer returns decomposition
    analyzer_resp = MagicMock()
    analyzer_resp.choices = [MagicMock()]
    analyzer_resp.choices[0].message.content = json.dumps({
        "needs_decomposition": True,
        "sub_questions": [
            {"question": "AAPL price", "type": "numerical"},
            {"question": "MSFT price", "type": "numerical"},
        ]
    })

    # 2. Gap detector says complete
    gap_resp = MagicMock()
    gap_resp.choices = [MagicMock()]
    gap_resp.choices[0].message.content = json.dumps({
        "complete": True, "gaps": [], "follow_up_queries": []
    })

    # 3. Synthesizer returns final answer
    synth_resp = MagicMock()
    synth_resp.choices = [MagicMock()]
    synth_resp.choices[0].message.content = "AAPL is $150, MSFT is $420."

    planner_calls = [analyzer_resp, gap_resp]
    planner_call_idx = {"i": 0}

    async def mock_planner(*args, **kwargs):
        idx = planner_call_idx["i"]
        planner_call_idx["i"] += 1
        return planner_calls[idx]

    with patch("datascraper.research_engine._call_planner", side_effect=mock_planner), \
         patch("datascraper.research_engine._try_mcp_search", new_callable=AsyncMock, side_effect=["$150", "$420"]), \
         patch("datascraper.research_engine._call_synthesis", new_callable=AsyncMock, return_value=synth_resp):
        result = await run_iterative_research(
            user_input="Compare AAPL and MSFT prices",
            message_list=[],
            model="gpt-5.2-chat-latest",
        )

    assert result is not None
    text, sources, metadata = result
    assert "AAPL" in text
    assert metadata["iterations_used"] == 1
    assert metadata["sub_questions_count"] == 2
