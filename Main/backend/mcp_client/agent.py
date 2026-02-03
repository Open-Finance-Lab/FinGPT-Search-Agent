
import os
from typing import Optional, List
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from agents import Agent
from agents.model_settings import ModelSettings
import logging

from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / '.env')

import sys
sys.path.insert(0, str(backend_dir))
from datascraper.models_config import get_model_config

from datascraper.url_tools import get_url_tools
from datascraper.playwright_tools import get_playwright_tools

from .apps import get_global_mcp_manager
from .prompt_builder import PromptBuilder


_mcp_init_lock = None
_prompt_builder = PromptBuilder()

USER_ONLY_MODELS = {"o3-mini", "o1-mini", "o1-preview", "gpt-5-mini", "gpt-5.1-chat-latest"}


@asynccontextmanager
async def create_fin_agent(model: str = "gpt-4o-mini",
                          system_prompt: Optional[str] = None,
                          current_url: Optional[str] = None,
                          user_input: Optional[str] = None,
                          user_timezone: Optional[str] = None,
                          user_time: Optional[str] = None):
    """
    Create a financial agent with tools (URL scraping, SEC-EDGAR, filesystem).

    Args:
        model: The OpenAI model to use (e.g., 'gpt-4o', 'o4-mini')
        system_prompt: Custom system prompt (if None, uses default)
        current_url: Current webpage URL for context
        user_input: User's query
        user_timezone: User's IANA timezone (e.g., "America/New_York")
        user_time: User's current time in ISO format

    Yields:
        Agent instance configured with tools
    """
    instructions = _prompt_builder.build(
        current_url=current_url,
        system_prompt=system_prompt,
        user_timezone=user_timezone,
        user_time=user_time,
    )

    model_config = get_model_config(model)
    if not model_config:
        logging.warning(f"Model ID '{model}' not found in config, using as-is")
        actual_model = model
    else:
        actual_model = model_config["model_name"]
        logging.info(f"Model resolution: {model} -> {actual_model}")

    tools: List = []

    url_tools = get_url_tools()
    tools.extend(url_tools)
    print(f"[AGENT DEBUG] Added {len(url_tools)} URL tools (resolve_url, scrape_url)")

    playwright_tools = get_playwright_tools()
    tools.extend(playwright_tools)
    print(f"[AGENT DEBUG] Added {len(playwright_tools)} Playwright tools (navigate_to_url, click_element, extract_page_content)")

    from .mcp_manager import MCPClientManager
    from .tool_wrapper import convert_mcp_tool_to_python_callable
    import asyncio

    global _mcp_init_lock

    _mcp_manager = get_global_mcp_manager()

    if _mcp_manager is None:
        print("="*60)
        print("[MCP DEBUG] ⚠ Global MCP manager not found!")
        print("[MCP DEBUG] This should have been initialized on backend startup.")
        print("[MCP DEBUG] Creating fallback instance for this request...")
        print("="*60)

        if _mcp_init_lock is None:
            _mcp_init_lock = asyncio.Lock()

        async with _mcp_init_lock:
            _mcp_manager = get_global_mcp_manager()
            if _mcp_manager is None:
                print("[MCP DEBUG] Connecting to MCP servers (fallback mode)...")
                manager = MCPClientManager()
                try:
                    await manager.connect_to_servers()
                    _mcp_manager = manager
                    print("[MCP DEBUG] ✓ Fallback MCP Client Manager connected.")
                    print("="*60)
                except Exception as e:
                    print(f"[MCP DEBUG] ✗ Failed to initialize MCP tools: {e}")
                    print("="*60)
                    logging.error(f"Failed to initialize MCP tools: {e}")
                    _mcp_manager = None
    else:
        print("[MCP DEBUG] ✓ Using pre-initialized global MCP manager")

    if _mcp_manager:
        try:
            print("[MCP DEBUG] Fetching MCP tools...")

            if _mcp_manager._loop:
                import concurrent.futures
                future = asyncio.run_coroutine_threadsafe(
                    _mcp_manager.get_all_tools(),
                    _mcp_manager._loop
                )
                try:
                    mcp_tools = future.result(timeout=10)
                except concurrent.futures.TimeoutError:
                    print("[MCP DEBUG] ✗ Timeout fetching MCP tools")
                    mcp_tools = []
            else:
                print("[MCP DEBUG] Warning: MCP loop not found, trying direct await")
                mcp_tools = await _mcp_manager.get_all_tools()

            if mcp_tools:
                print(f"[MCP DEBUG] ✓ Agent configured with {len(mcp_tools)} MCP tools")
                logging.info(f"Found {len(mcp_tools)} MCP tools from connected servers.")

                for tool in mcp_tools:

                    async def execute_mcp_tool(name, args, mgr=_mcp_manager):
                        if mgr._loop:
                            future = asyncio.run_coroutine_threadsafe(
                                mgr.execute_tool(name, args),
                                mgr._loop
                            )
                            return future.result(timeout=60)
                        else:
                            return await mgr.execute_tool(name, args)

                    agent_tool = convert_mcp_tool_to_python_callable(tool, execute_mcp_tool)
                    tools.append(agent_tool)

            else:
                print("[MCP DEBUG] ⚠ No MCP tools found")

        except Exception as e:
            print(f"[MCP DEBUG] ✗ Error fetching/adding MCP tools: {e}")
            logging.error(f"Error fetching/adding MCP tools: {e}", exc_info=True)

    try:
        # Handle foundation models that don't support "system" roles
        if actual_model in USER_ONLY_MODELS:
            logging.info(f"[AGENT] Foundation model detected ({actual_model}). Moving instructions to message layer.")
            agent_instructions = ""
        else:
            agent_instructions = instructions

        agent = Agent(
            name="FinGPT Search Agent",
            instructions=agent_instructions,
            model=actual_model,
            tools=tools if tools else [],
            model_settings=ModelSettings(
                tool_choice="auto" if tools else None
            )
        )

        # Attach instructions as a property for the runner to use if agent_instructions is empty
        if actual_model in USER_ONLY_MODELS:
            agent._foundation_instructions = instructions

        yield agent

    finally:
        # Clean up agent resources
        try:
            if hasattr(agent, 'close'):
                await agent.close()
            logger.debug("Agent cleanup completed")
        except Exception as e:
            logger.warning(f"Error during agent cleanup: {e}")
