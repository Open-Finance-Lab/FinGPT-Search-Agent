"""
Refactored Datascraper Module for Unified Context Manager
Handles response generation with full conversation context
Author: Linus (simplifying through good taste)
"""

import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
import asyncio

from .unified_context_manager import (
    UnifiedContextManager,
    get_context_manager
)
from .models_config import MODEL_CONFIGS, get_model_config

logger = logging.getLogger(__name__)


class UnifiedDataScraper:
    """
    Datascraper that works with the Unified Context Manager.
    Provides clean interfaces for different response generation modes.
    """

    def __init__(self):
        self.context_manager = get_context_manager()

    def _format_context_for_llm(self, context: Dict[str, Any]) -> str:
        """
        Format the full context into a single string for LLM consumption.
        This creates a comprehensive context that includes everything.
        """
        lines = []

        lines.append("=== SYSTEM ===")
        lines.append(context["system_prompt"])

        metadata = context["metadata"]
        lines.append("\n=== METADATA ===")
        lines.append(f"Session ID: {metadata['session_id']}")
        lines.append(f"Mode: {metadata['mode']}")
        lines.append(f"Timestamp: {metadata['timestamp']}")
        if metadata.get('current_url'):
            lines.append(f"Current URL: {metadata['current_url']}")
        if metadata.get('user_timezone'):
            lines.append(f"User Timezone: {metadata['user_timezone']}")
        if metadata.get('user_time'):
            lines.append(f"User Time: {metadata['user_time']}")

        fetched = context["fetched_context"]
        has_fetched = any(len(items) > 0 for items in fetched.values())

        if has_fetched:
            lines.append("\n=== FETCHED CONTEXT ===")

            if fetched["web_search"]:
                lines.append("\n--- Web Search Results ---")
                for item in fetched["web_search"]:
                    lines.append(f"From: {item.get('url', 'unknown')}")
                    lines.append(item['content'])
                    if item.get('extracted_data'):
                        lines.append(f"Metadata: {json.dumps(item['extracted_data'])}")
                    lines.append("")

            if fetched["playwright"]:
                lines.append("\n--- Playwright Scraped Content ---")
                for item in fetched["playwright"]:
                    lines.append(f"From: {item.get('url', 'current page')}")
                    lines.append(item['content'])
                    if item.get('extracted_data', {}).get('action'):
                        lines.append(f"Action: {item['extracted_data']['action']}")
                    lines.append("")

            if fetched["js_scraping"]:
                lines.append("\n--- JavaScript Scraped Content ---")
                for item in fetched["js_scraping"]:
                    lines.append(f"From: {item.get('url', 'current page')}")
                    lines.append(item['content'])
                    lines.append("")

        lines.append("\n=== CONVERSATION HISTORY ===")
        for msg in context["conversation_history"]:
            timestamp = msg.get('timestamp', '')
            role = msg['role'].upper()

            lines.append(f"\n[{role}] ({timestamp})")
            lines.append(msg['content'])

            if msg.get('metadata'):
                meta = msg['metadata']
                if meta.get('model'):
                    lines.append(f"Model: {meta['model']}")
                if meta.get('sources_used'):
                    lines.append(f"Sources: {len(meta['sources_used'])} used")
                if meta.get('tools_used'):
                    lines.append(f"Tools: {', '.join(meta['tools_used'])}")

        return "\n".join(lines)

    def _build_api_messages(self, context: Dict[str, Any], current_question: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Build messages array for LLM API calls.
        Returns messages in the format expected by OpenAI/Anthropic/etc.
        """
        messages = []

        system_content = context["system_prompt"]

        metadata = context["metadata"]
        if metadata.get('current_url'):
            system_content += f"\n\nYou are currently viewing: {metadata['current_url']}"
        if metadata.get('user_timezone') or metadata.get('user_time'):
            time_parts = []
            if metadata.get('user_timezone'):
                time_parts.append(f"User timezone: {metadata['user_timezone']}")
            if metadata.get('user_time'):
                time_parts.append(f"Current time: {metadata['user_time']}")
            system_content += f"\n\n{' | '.join(time_parts)}"

        fetched = context["fetched_context"]
        context_parts = []

        if fetched["web_search"]:
            search_content = "\n\nWeb Search Results:\n"
            for item in fetched["web_search"]:
                search_content += f"- {item.get('url', 'unknown')}: {item['content'][:200]}...\n"
            context_parts.append(search_content)

        if fetched["playwright"]:
            playwright_content = "\n\nPage Content (via Playwright):\n"
            for item in fetched["playwright"]:
                playwright_content += f"- {item.get('url', 'page')}: {item['content'][:200]}...\n"
            context_parts.append(playwright_content)

        if fetched["js_scraping"]:
            js_content = "\n\nPage Content (via JS):\n"
            for item in fetched["js_scraping"]:
                js_content += f"- {item.get('url', 'page')}: {item['content'][:200]}...\n"
            context_parts.append(js_content)

        if context_parts:
            system_content += "\n\n=== Available Context ===" + "".join(context_parts)

        messages.append({"role": "system", "content": system_content})

        for msg in context["conversation_history"]:
            role = msg['role']
            content = msg['content']

            if role == "user":
                messages.append({"role": "user", "content": content})
            elif role == "assistant":
                messages.append({"role": "assistant", "content": content})

        if current_question:
            if not messages or messages[-1].get('content') != current_question:
                messages.append({"role": "user", "content": current_question})

        return messages

    async def create_response_async(
        self,
        session_id: str,
        model: str = "gpt-4o-mini",
        stream: bool = False
    ) -> str:
        """
        Create a response using the full context from the session.
        """
        try:
            context = self.context_manager.get_full_context(session_id)

            messages = self._build_api_messages(context)

            model_config = get_model_config(model)
            if not model_config:
                raise ValueError(f"Unknown model: {model}")

            provider = model_config['provider']

            if provider in ['openai', 'deepseek']:
                from openai import AsyncOpenAI

                client = AsyncOpenAI(
                    api_key=model_config['api_key'],
                    base_url=model_config.get('base_url')
                )

                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    stream=stream
                )

                if stream:
                    accumulated = ""
                    async for chunk in response:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            accumulated += content
                            yield content
                    return accumulated
                else:
                    return response.choices[0].message.content

            elif provider == 'anthropic':
                from anthropic import AsyncAnthropic

                client = AsyncAnthropic(api_key=model_config['api_key'])

                system_msg = next((m for m in messages if m['role'] == 'system'), None)
                if system_msg:
                    messages = [m for m in messages if m['role'] != 'system']
                    system = system_msg['content']
                else:
                    system = None

                response = await client.messages.create(
                    model=model,
                    messages=messages,
                    system=system,
                    max_tokens=4096,
                    temperature=0.7,
                    stream=stream
                )

                if stream:
                    accumulated = ""
                    async for event in response:
                        if event.type == 'content_block_delta':
                            content = event.delta.text
                            accumulated += content
                            yield content
                    return accumulated
                else:
                    return response.content[0].text

            else:
                raise ValueError(f"Unsupported provider: {provider}")

        except Exception as e:
            logger.error(f"Error creating response: {e}", exc_info=True)
            raise

    def create_response(
        self,
        session_id: str,
        model: str = "gpt-4o-mini",
        stream: bool = False
    ) -> str:
        """
        Synchronous wrapper for create_response_async.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if stream:
                return loop.run_until_complete(
                    self.create_response_async(session_id, model, stream)
                )
            else:
                coro = self.create_response_async(session_id, model, stream)
                return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def create_agent_response_async(
        self,
        session_id: str,
        model: str = "gpt-4o-mini",
        use_playwright: bool = False,
        restricted_domain: Optional[str] = None,
        current_url: Optional[str] = None
    ) -> str:
        """
        Create a response using an agent with tools.
        """
        try:
            context = self.context_manager.get_full_context(session_id)

            context_str = self._format_context_for_llm(context)

            from mcp_client.agent import create_fin_agent

            async with create_fin_agent(
                model=model,
                use_playwright=use_playwright,
                restricted_domain=restricted_domain,
                current_url=current_url
            ) as agent:
                result = await agent.run(context_str)

                if use_playwright and hasattr(result, 'tool_outputs'):
                    for output in result.tool_outputs:
                        if output.tool_name == 'get_page_text':
                            self.context_manager.add_fetched_context(
                                session_id=session_id,
                                source_type="playwright",
                                content=output.content,
                                url=current_url or restricted_domain,
                                extracted_data={'action': 'get_page_text'}
                            )

                return result.final_output

        except Exception as e:
            logger.error(f"Error creating agent response: {e}", exc_info=True)
            raise

    def create_agent_response(
        self,
        session_id: str,
        model: str = "gpt-4o-mini",
        use_playwright: bool = False,
        restricted_domain: Optional[str] = None,
        current_url: Optional[str] = None
    ) -> str:
        """
        Synchronous wrapper for create_agent_response_async.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.create_agent_response_async(
                    session_id, model, use_playwright,
                    restricted_domain, current_url
                )
            )
        finally:
            loop.close()

    async def create_web_search_response_async(
        self,
        session_id: str,
        model: str = "gpt-4o-mini",
        preferred_domains: Optional[List[str]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Create a response using web search capabilities.
        """
        try:
            context = self.context_manager.get_full_context(session_id)

            last_question = ""
            for msg in reversed(context["conversation_history"]):
                if msg["role"] == "user":
                    last_question = msg["content"]
                    break

            if not last_question:
                raise ValueError("No user question found in context")

            from .openai_search import create_responses_api_search_async

            message_history = self._build_api_messages(context)

            response_text, sources = await create_responses_api_search_async(
                user_query=last_question,
                message_history=message_history,
                model=model,
                preferred_links=preferred_domains,
                user_timezone=context["metadata"].get("user_timezone"),
                user_time=context["metadata"].get("user_time")
            )

            for source in sources:
                self.context_manager.add_fetched_context(
                    session_id=session_id,
                    source_type="web_search",
                    content=f"{source.get('title', '')}\n{source.get('snippet', '')}\n{source.get('body', '')}",
                    url=source.get('url'),
                    extracted_data={
                        'title': source.get('title'),
                        'site_name': source.get('site_name'),
                        'published_date': source.get('published_date')
                    }
                )

            return response_text, sources

        except Exception as e:
            logger.error(f"Error creating web search response: {e}", exc_info=True)
            raise

    def create_web_search_response(
        self,
        session_id: str,
        model: str = "gpt-4o-mini",
        preferred_domains: Optional[List[str]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Synchronous wrapper for create_web_search_response_async.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.create_web_search_response_async(
                    session_id, model, preferred_domains
                )
            )
        finally:
            loop.close()


_scraper = None

def get_unified_scraper() -> UnifiedDataScraper:
    """Get or create the singleton scraper instance"""
    global _scraper
    if _scraper is None:
        _scraper = UnifiedDataScraper()
    return _scraper



def create_response(
    user_input: str,
    message_list: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    stream: bool = False
) -> str:
    """
    Backward compatible function for creating responses.
    Creates a temporary session and uses the unified system.
    """
    import uuid
    scraper = get_unified_scraper()
    context_mgr = get_context_manager()

    session_id = f"temp_{uuid.uuid4()}"

    for msg in message_list:
        content = msg.get('content', '')
        if '[USER MESSAGE]:' in content or '[USER QUESTION]:' in content:
            clean_content = content.replace('[USER MESSAGE]:', '').replace('[USER QUESTION]:', '').strip()
            context_mgr.add_user_message(session_id, clean_content)
        elif '[ASSISTANT MESSAGE]:' in content or '[ASSISTANT RESPONSE]:' in content:
            clean_content = content.replace('[ASSISTANT MESSAGE]:', '').replace('[ASSISTANT RESPONSE]:', '').strip()
            context_mgr.add_assistant_message(session_id, clean_content, model=model)

    context_mgr.add_user_message(session_id, user_input)

    response = scraper.create_response(session_id, model, stream)

    context_mgr.clear_session(session_id)

    return response


def create_agent_response(
    user_input: str,
    message_list: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    use_playwright: bool = False,
    restricted_domain: Optional[str] = None,
    current_url: Optional[str] = None
) -> str:
    """
    Backward compatible function for agent responses.
    """
    import uuid
    scraper = get_unified_scraper()
    context_mgr = get_context_manager()

    session_id = f"temp_{uuid.uuid4()}"

    for msg in message_list:
        content = msg.get('content', '')
        if '[USER MESSAGE]:' in content or '[USER QUESTION]:' in content:
            clean_content = content.replace('[USER MESSAGE]:', '').replace('[USER QUESTION]:', '').strip()
            context_mgr.add_user_message(session_id, clean_content)
        elif '[ASSISTANT MESSAGE]:' in content or '[ASSISTANT RESPONSE]:' in content:
            clean_content = content.replace('[ASSISTANT MESSAGE]:', '').replace('[ASSISTANT RESPONSE]:', '').strip()
            context_mgr.add_assistant_message(session_id, clean_content, model=model)

    context_mgr.add_user_message(session_id, user_input)

    from .unified_context_manager import ContextMode
    context_mgr.update_metadata(
        session_id=session_id,
        mode=ContextMode.THINKING,
        current_url=current_url
    )

    response = scraper.create_agent_response(
        session_id, model, use_playwright, restricted_domain, current_url
    )

    context_mgr.clear_session(session_id)

    return response


def create_advanced_response(
    user_input: str,
    message_list: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    preferred_links: Optional[List[str]] = None,
    stream: bool = False,
    user_timezone: Optional[str] = None,
    user_time: Optional[str] = None
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Backward compatible function for web search responses.
    """
    import uuid
    scraper = get_unified_scraper()
    context_mgr = get_context_manager()

    session_id = f"temp_{uuid.uuid4()}"

    for msg in message_list:
        content = msg.get('content', '')
        if '[USER MESSAGE]:' in content or '[USER QUESTION]:' in content:
            clean_content = content.replace('[USER MESSAGE]:', '').replace('[USER QUESTION]:', '').strip()
            context_mgr.add_user_message(session_id, clean_content)
        elif '[ASSISTANT MESSAGE]:' in content or '[ASSISTANT RESPONSE]:' in content:
            clean_content = content.replace('[ASSISTANT MESSAGE]:', '').replace('[ASSISTANT RESPONSE]:', '').strip()
            context_mgr.add_assistant_message(session_id, clean_content, model=model)

    context_mgr.add_user_message(session_id, user_input)

    from .unified_context_manager import ContextMode
    context_mgr.update_metadata(
        session_id=session_id,
        mode=ContextMode.RESEARCH,
        user_timezone=user_timezone,
        user_time=user_time
    )

    preferred_domains = []
    if preferred_links:
        from urllib.parse import urlparse
        for link in preferred_links:
            try:
                parsed = urlparse(link)
                if parsed.netloc:
                    preferred_domains.append(parsed.netloc)
            except:
                pass

    response_text, sources = scraper.create_web_search_response(
        session_id, model, preferred_domains
    )

    context_mgr.clear_session(session_id)

    return response_text, sources
