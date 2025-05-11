# backend/datascraper/agent.py

from agents import Agent
from agents.mcp import MCPServer

USER_ONLY_MODELS = {"o3-mini"}
DEFAULT_PROMPT = (
    "You are a helpful financial assistant. "
    "Always answer questions to the best of your ability using available tools."
)

def create_fin_agent(llm_model: str, system_prompt: str = None) -> Agent:
    """
    Factory for an MCP-enabled Agent that:
      - Uses `system` messages and temperature for chat models
      - Falls back to a single user-message + no temperature for user-only models
    """
    mcp = MCPServer(base_url="http://localhost:8000/mcp")

    instructions = system_prompt or DEFAULT_PROMPT

    if llm_model in USER_ONLY_MODELS:
        # user-only: embed prompt as a single user message, no tempt
        agent = Agent(
            name="FinGPT Search Agent",
            llm_model=llm_model,
            mcp_servers=[mcp],
            function_call="auto",
            max_function_calls=5,
        )

    # chat model: use system prompt + temp
    return Agent(
        name="FinGPT Search Agent",
        instructions=instructions,
        llm_model=llm_model,
        mcp_servers=[mcp],
        function_call="auto",
        max_function_calls=5,
        temperature=0.0,
    )