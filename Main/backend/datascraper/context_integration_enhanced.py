"""
Enhanced Context Integration Module
Supports both UnifiedContextManager and Mem0ContextManager with smart compression
Configurable via environment variable or runtime selection
Author: Linus (pragmatic dual-mode approach)
"""

import os
import logging
from typing import Dict, List, Optional, Any, Literal
from django.http import HttpRequest

logger = logging.getLogger(__name__)


class EnhancedContextIntegration:
    """
    Enhanced integration layer supporting both Unified and Mem0 context managers.
    Mem0 provides smart compression when context exceeds 100k tokens.
    """

    def __init__(self, context_mode: Optional[str] = None):
        """
        Initialize the context integration.

        Args:
            context_mode: "unified" or "mem0" (defaults to env var CONTEXT_MANAGER_MODE or "mem0")
        """
        mode = context_mode or os.getenv("CONTEXT_MANAGER_MODE", "mem0").lower()

        if mode == "unified":
            from .unified_context_manager import get_context_manager, ContextMode
            self.context_manager = get_context_manager()
            self.manager_type = "unified"
            self.ContextMode = ContextMode
            logger.info("Using UnifiedContextManager (no compression)")
        else:
            from .mem0_context_manager import Mem0ContextManager
            self.context_manager = Mem0ContextManager()
            self.manager_type = "mem0"
            from enum import Enum
            self.ContextMode = Enum('ContextMode', {
                'RESEARCH': 'research',
                'THINKING': 'thinking',
                'NORMAL': 'normal'
            })
            logger.info("Using Mem0ContextManager with smart compression (100k token limit)")

    def _get_session_id(self, request: HttpRequest) -> str:
        """Extract or create session ID from request"""
        session_id = request.GET.get('session_id') or request.POST.get('session_id')

        if not session_id:
            if hasattr(request, 'session'):
                if not request.session.session_key:
                    request.session.create()
                session_id = request.session.session_key
            else:
                import uuid
                session_id = str(uuid.uuid4())

        return session_id

    def _determine_mode(self, request: HttpRequest, endpoint: str) -> Any:
        """Determine the context mode based on request and endpoint"""
        mode_param = request.GET.get('mode') or request.POST.get('mode')
        if mode_param:
            try:
                return self.ContextMode(mode_param)
            except (ValueError, KeyError):
                pass

        if 'adv' in endpoint or 'advanced' in endpoint:
            return self.ContextMode.RESEARCH
        elif 'agent' in endpoint or request.GET.get('use_playwright') == 'true':
            return self.ContextMode.THINKING
        else:
            return self.ContextMode.NORMAL

    def prepare_context_for_request(
        self,
        request: HttpRequest,
        question: str,
        current_url: Optional[str] = None,
        endpoint: str = ""
    ) -> tuple[List[Dict[str, str]], str]:
        """
        Prepare context for LLM API call.
        Returns (messages_list, session_id)
        """
        session_id = self._get_session_id(request)
        mode = self._determine_mode(request, endpoint)

        if self.manager_type == "unified":
            self.context_manager.update_metadata(
                session_id=session_id,
                mode=mode,
                current_url=current_url or request.GET.get('current_url'),
                user_timezone=request.GET.get('user_timezone'),
                user_time=request.GET.get('user_time')
            )

            self.context_manager.add_user_message(session_id, question)
            messages = self.context_manager.get_formatted_messages_for_api(session_id)

        else:
            if current_url or request.GET.get('current_url'):
                self.context_manager.update_current_webpage(
                    session_id,
                    current_url or request.GET.get('current_url')
                )

            self.context_manager.update_user_time_info(
                session_id,
                timezone=request.GET.get('user_timezone'),
                current_time=request.GET.get('user_time')
            )

            self.context_manager.add_message(session_id, "user", question)

            context = self.context_manager.get_context(session_id)

            messages = []
            for msg in context:
                messages.append({"content": msg["content"]})

        return messages, session_id

    def add_response_to_context(
        self,
        session_id: str,
        response: str,
        model: Optional[str] = None,
        sources_used: Optional[List[Dict[str, str]]] = None,
        tools_used: Optional[List[str]] = None,
        response_time_ms: Optional[int] = None
    ) -> None:
        """Add assistant response to context"""
        if self.manager_type == "unified":
            self.context_manager.add_assistant_message(
                session_id=session_id,
                content=response,
                model=model,
                sources_used=sources_used,
                tools_used=tools_used,
                response_time_ms=response_time_ms
            )
        else:
            self.context_manager.add_message(session_id, "assistant", response)

    def add_web_content(
        self,
        request: HttpRequest,
        text_content: str,
        current_url: str,
        source_type: Literal["js_scraping", "web_search", "playwright"] = "js_scraping"
    ) -> str:
        """
        Add web content to context.
        Returns session_id
        """
        session_id = self._get_session_id(request)

        MAX_CONTENT_LENGTH = 10000
        if len(text_content) > MAX_CONTENT_LENGTH:
            text_content = text_content[:MAX_CONTENT_LENGTH] + "... (truncated)"

        if self.manager_type == "unified":
            self.context_manager.add_fetched_context(
                session_id=session_id,
                source_type=source_type,
                content=text_content,
                url=current_url
            )
        else:
            self.context_manager.add_fetched_context(
                session_id=session_id,
                source_type=source_type,
                content=text_content,
                url=current_url
            )

        return session_id

    def add_search_results(
        self,
        session_id: str,
        search_results: List[Dict[str, Any]]
    ) -> None:
        """Add web search results to context"""
        for result in search_results:
            content = f"Title: {result.get('title', 'N/A')}\n"
            content += f"Snippet: {result.get('snippet', 'N/A')}\n"
            if result.get('body'):
                content += f"Content: {result['body'][:500]}..."

            metadata = {
                'title': result.get('title'),
                'site_name': result.get('site_name'),
                'published_date': result.get('published_date')
            }

            if self.manager_type == "unified":
                self.context_manager.add_fetched_context(
                    session_id=session_id,
                    source_type="web_search",
                    content=content,
                    url=result.get('url'),
                    extracted_data=metadata
                )
            else:
                self.context_manager.add_fetched_context(
                    session_id=session_id,
                    source_type="web_search",
                    content=content,
                    url=result.get('url'),
                    metadata=metadata
                )

    def add_playwright_content(
        self,
        session_id: str,
        content: str,
        url: str,
        action: Optional[str] = None
    ) -> None:
        """Add content scraped by Playwright"""
        metadata = {}
        if action:
            metadata['action'] = action

        if self.manager_type == "unified":
            self.context_manager.add_fetched_context(
                session_id=session_id,
                source_type="playwright",
                content=content,
                url=url,
                extracted_data=metadata
            )
        else:
            self.context_manager.add_fetched_context(
                session_id=session_id,
                source_type="playwright",
                content=content,
                url=url,
                metadata=metadata
            )

    def clear_messages(
        self,
        request: HttpRequest,
        preserve_web_content: bool = False
    ) -> str:
        """
        Clear conversation history, optionally preserving web content.
        Returns session_id
        """
        session_id = self._get_session_id(request)

        if self.manager_type == "unified":
            if preserve_web_content:
                self.context_manager.clear_conversation_history(session_id)
            else:
                self.context_manager.clear_session(session_id)
        else:
            if preserve_web_content:
                self.context_manager.clear_conversation_only(session_id)
            else:
                self.context_manager.clear_session(session_id)

        return session_id

    def get_context_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics about the context"""
        if self.manager_type == "unified":
            stats = self.context_manager.get_session_stats(session_id)
        else:
            stats = self.context_manager.get_session_stats(session_id)
            stats['smart_compression_enabled'] = True
            stats['max_tokens'] = self.context_manager.max_session_tokens

        stats['context_manager'] = self.manager_type
        return stats

    def get_full_context_json(self, session_id: str) -> str:
        """Get full context as formatted JSON string"""
        if self.manager_type == "unified":
            return self.context_manager.export_session_json(session_id)
        else:
            import json
            context = self.context_manager.get_context(session_id)
            stats = self.context_manager.get_session_stats(session_id)

            result = {
                "session_id": session_id,
                "context_manager": "mem0",
                "stats": stats,
                "context_messages": context,
                "smart_compression": {
                    "enabled": True,
                    "max_tokens": self.context_manager.max_session_tokens,
                    "has_compressed_chunks": stats.get("memory_count", 0) > 0
                }
            }
            return json.dumps(result, indent=2, ensure_ascii=False)


_unified_integration = None
_mem0_integration = None
_enhanced_integration = None

def get_context_integration(use_mem0: bool = None) -> EnhancedContextIntegration:
    """
    Get or create the singleton integration instance.

    Args:
        use_mem0: If True, use Mem0; if False, use Unified; if None, check env var
    """
    global _enhanced_integration

    if use_mem0 is None:
        use_mem0 = os.getenv("CONTEXT_MANAGER_MODE", "mem0").lower() == "mem0"

    mode = "mem0" if use_mem0 else "unified"

    if _enhanced_integration is None or _enhanced_integration.manager_type != mode:
        _enhanced_integration = EnhancedContextIntegration(context_mode=mode)

    return _enhanced_integration
