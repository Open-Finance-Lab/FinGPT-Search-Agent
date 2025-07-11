# backend/mcp/agent.py

import os
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from agents import Agent
from agents.mcp import MCPServerSse
from agents.model_settings import ModelSettings

load_dotenv()

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
    
    async with MCPServerSse(
        name="FinGPT MCP Server",
        params={
            "url": "http://127.0.0.1:9000/sse",
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