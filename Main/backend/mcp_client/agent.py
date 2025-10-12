# backend/mcp/agent.py

import os
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from agents import Agent
from agents.mcp import MCPServerSse
from agents.model_settings import ModelSettings

# Load .env from the backend root directory
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / '.env')

USER_ONLY_MODELS = {"o3-mini"}
DEFAULT_PROMPT = (
    "You are a helpful financial assistant. "
    "You have access to tools that can help you answer questions. "
    "ALWAYS use the available tools when they are relevant to the user's request. "
)

@asynccontextmanager
async def create_fin_agent(model: str = "gpt-4o", system_prompt: Optional[str] = None):
    """
    Create a financial agent with MCP server integration.
    Uses async context manager for MCP server connection.
    """
    instructions = system_prompt or DEFAULT_PROMPT

    # Get MCP server URL from environment variable
    mcp_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:9000/sse")

    async with MCPServerSse(
        name="FinGPT MCP Server",
        params={
            "url": mcp_url,
        },
    ) as server:
        
        agent = Agent(
            name="FinGPT Search Agent",
            instructions=instructions,
            model=model,
            mcp_servers=[server],
            model_settings=ModelSettings(
                tool_choice="required"
            )
        )
        
        yield agent