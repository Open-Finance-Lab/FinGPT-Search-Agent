"""
Tests for the tool-filtering capability in create_fin_agent.
Uses mocking to avoid needing actual MCP servers or API keys.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


class TestToolFiltering:
    """Test that create_fin_agent respects allowed_tools parameter."""

    @pytest.fixture
    def mock_env(self):
        """Provide minimal env for agent creation."""
        env = {
            "OPENAI_API_KEY": "test-key",
            "GOOGLE_API_KEY": "",
        }
        with patch.dict("os.environ", env, clear=False):
            yield

    @pytest.fixture
    def mock_mcp(self):
        """Mock the global MCP manager to return no MCP tools."""
        with patch("mcp_client.agent.get_global_mcp_manager", return_value=None):
            yield

    def test_all_tools_when_none(self, mock_env, mock_mcp):
        """allowed_tools=None gives all direct tools (default behavior)."""
        from mcp_client.agent import create_fin_agent

        async def run():
            async with create_fin_agent(
                model="gpt-4o-mini",
                allowed_tools=None,
            ) as agent:
                # Without MCP, we get 6 direct tools: 2 url + 3 playwright + 1 calculator
                assert len(agent.tools) == 6
                names = {t.name for t in agent.tools}
                assert "scrape_url" in names
                assert "navigate_to_url" in names
                assert "calculate" in names

        asyncio.run(run())

    def test_no_tools_when_empty(self, mock_env, mock_mcp):
        """allowed_tools=[] gives zero tools."""
        from mcp_client.agent import create_fin_agent

        async def run():
            async with create_fin_agent(
                model="gpt-4o-mini",
                allowed_tools=[],
            ) as agent:
                assert agent.tools == []

        asyncio.run(run())

    def test_filtered_tools(self, mock_env, mock_mcp):
        """allowed_tools=['calculate', 'scrape_url'] gives exactly those tools."""
        from mcp_client.agent import create_fin_agent

        async def run():
            async with create_fin_agent(
                model="gpt-4o-mini",
                allowed_tools=["calculate", "scrape_url"],
            ) as agent:
                assert len(agent.tools) == 2
                names = {t.name for t in agent.tools}
                assert names == {"calculate", "scrape_url"}

        asyncio.run(run())

    def test_instructions_override_bypasses_prompt_builder(self, mock_env, mock_mcp):
        """instructions_override skips PromptBuilder and uses the override directly."""
        from mcp_client.agent import create_fin_agent

        override = "You are a test agent. Only summarize."

        async def run():
            async with create_fin_agent(
                model="gpt-4o-mini",
                instructions_override=override,
                allowed_tools=[],
            ) as agent:
                assert agent.instructions == override

        asyncio.run(run())

    def test_no_override_uses_prompt_builder(self, mock_env, mock_mcp):
        """Without instructions_override, PromptBuilder is used normally."""
        from mcp_client.agent import create_fin_agent

        async def run():
            async with create_fin_agent(
                model="gpt-4o-mini",
            ) as agent:
                # Should contain core.md content
                assert "FinGPT" in agent.instructions

        asyncio.run(run())
