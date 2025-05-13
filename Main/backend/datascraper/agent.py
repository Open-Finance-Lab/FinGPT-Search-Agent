# backend/datascraper/agent.py

import os
from agents import Agent, ModelSettings
from agents.mcp.server import MCPServerSse, MCPServerSseParams

USER_ONLY_MODELS = {"o3-mini"}
DEFAULT_PROMPT = (
    "You are a helpful financial assistant. "
    "Always answer questions to the best of your ability using available tools."
)

def create_fin_agent(model: str, system_prompt: str | None = None) -> Agent:
    """
    Factory for an MCP-enabled Agent.
    Uses `system_prompt` as the agent's instructions and attaches a single SSE-based MCP server.
    """
    # configure the SSE transport for MCP.  Pass a TypedDict to params, as required.
    mcp = MCPServerSse(
        params=MCPServerSseParams(
            url="http://localhost:9000/mcp",                   # where your MCP server is listening
            headers={"Accept": "application/json, text/event-stream"},  # must accept both types
            timeout=60,         # total connect timeout (seconds)
            sse_read_timeout=5  # how long to wait for keep-alive
        ),
        cache_tools_list=True,  # cache the tool list for performance
        name="FinGPT-MCP"
    )

    instructions = DEFAULT_PROMPT

    agent = Agent(
        name="FinGPT Search Agent",
        instructions=instructions,
        model=model,
        mcp_servers=[mcp],
        model_settings=ModelSettings(
            temperature=0.0,
            tool_choice="auto"
        )
    )
    print("Debug: Agent setup successfully")

    return agent
