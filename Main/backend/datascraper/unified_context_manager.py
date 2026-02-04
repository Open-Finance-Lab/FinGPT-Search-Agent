"""
Unified Context Manager for FinGPT - Cache-backed Version
Handles all conversation context with elegant JSON structure.
Sessions stored in Django's cache framework (shared across all workers).
NO compression, NO legacy support - pure session-based context tracking.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, asdict, field
from enum import Enum

from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "ucm:"


class ContextMode(Enum):
    """Modes of operation for context"""
    RESEARCH = "research"
    THINKING = "thinking"
    NORMAL = "normal"


@dataclass
class MessageMetadata:
    """Metadata for individual messages"""
    model: Optional[str] = None
    sources_used: List[Dict[str, str]] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    response_time_ms: Optional[int] = None


@dataclass
class ConversationMessage:
    """Individual message in conversation history"""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str
    metadata: Optional[MessageMetadata] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }
        if self.metadata:
            result["metadata"] = asdict(self.metadata)
        return result


@dataclass
class FetchedContextItem:
    """Item of fetched context from various sources"""
    source_type: Literal["web_search", "js_scraping"]
    content: str
    url: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extracted_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "source_type": self.source_type,
            "content": self.content,
            "timestamp": self.timestamp
        }
        if self.url:
            result["url"] = self.url
        if self.extracted_data:
            result["extracted_data"] = self.extracted_data
        return result


@dataclass
class ContextMetadata:
    """Global metadata for the context"""
    session_id: str
    timestamp: str
    mode: ContextMode
    current_url: Optional[str] = None
    user_timezone: Optional[str] = None
    user_time: Optional[str] = None
    token_count: int = 0
    message_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "mode": self.mode.value,
            "token_count": self.token_count,
            "message_count": self.message_count
        }
        if self.current_url:
            result["current_url"] = self.current_url
        if self.user_timezone:
            result["user_timezone"] = self.user_timezone
        if self.user_time:
            result["user_time"] = self.user_time
        return result


class UnifiedContextManager:
    """
    Manages conversation context with elegant JSON structure.
    Sessions live in Django's cache — shared across all gunicorn workers.
    TTL and eviction handled by the cache backend (settings.CACHES).
    """

    def __init__(self):
        self.session_ttl = 3600
        logger.info("UnifiedContextManager initialized (no compression, cache-backed)")

    def _cache_key(self, session_id: str) -> str:
        return f"{CACHE_KEY_PREFIX}{session_id}"

    def _load_session(self, session_id: str) -> Dict[str, Any]:
        """Load session from cache, create if missing."""
        key = self._cache_key(session_id)
        session = cache.get(key)

        if session is None:
            now = datetime.now(timezone.utc)
            session = {
                "system_prompt": self._get_default_system_prompt(),
                "metadata": ContextMetadata(
                    session_id=session_id,
                    timestamp=now.isoformat(),
                    mode=ContextMode.NORMAL
                ),
                "fetched_context": {
                    "web_search": [],
                    "js_scraping": []
                },
                "conversation_history": [],
            }
            cache.set(key, session, self.session_ttl)
            logger.debug(f"Created new session: {session_id}")
        else:
            # Touch TTL on access
            cache.set(key, session, self.session_ttl)

        return session

    def _save_session(self, session_id: str, session: Dict[str, Any]) -> None:
        """Write session back to cache."""
        cache.set(self._cache_key(session_id), session, self.session_ttl)

    def _get_default_system_prompt(self) -> str:
        # Identity and rules live in prompts/core.md (loaded by PromptBuilder).
        # UCM only stores session-level overrides set via set_system_prompt().
        return ""

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def update_metadata(
        self,
        session_id: str,
        mode: Optional[ContextMode] = None,
        current_url: Optional[str] = None,
        user_timezone: Optional[str] = None,
        user_time: Optional[str] = None
    ) -> None:
        """Update session metadata"""
        session = self._load_session(session_id)
        metadata = session["metadata"]

        if mode:
            metadata.mode = mode
        if current_url:
            metadata.current_url = current_url
        if user_timezone:
            metadata.user_timezone = user_timezone
        if user_time:
            metadata.user_time = user_time

        metadata.timestamp = datetime.now(timezone.utc).isoformat()
        self._save_session(session_id, session)
        logger.debug(f"Updated metadata for session {session_id}")

    def add_user_message(
        self,
        session_id: str,
        content: str,
        timestamp: Optional[str] = None
    ) -> None:
        """Add a user message to conversation history"""
        session = self._load_session(session_id)

        message = ConversationMessage(
            role="user",
            content=content,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat()
        )

        session["conversation_history"].append(message)
        session["metadata"].message_count += 1
        session["metadata"].token_count += self._estimate_tokens(content)
        self._save_session(session_id, session)

        logger.debug(f"Added user message to session {session_id}")

    def add_assistant_message(
        self,
        session_id: str,
        content: str,
        model: Optional[str] = None,
        sources_used: Optional[List[Dict[str, str]]] = None,
        tools_used: Optional[List[str]] = None,
        response_time_ms: Optional[int] = None,
        timestamp: Optional[str] = None
    ) -> None:
        """Add an assistant message to conversation history"""
        session = self._load_session(session_id)

        metadata = MessageMetadata(
            model=model,
            sources_used=sources_used or [],
            tools_used=tools_used or [],
            response_time_ms=response_time_ms
        )

        message = ConversationMessage(
            role="assistant",
            content=content,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            metadata=metadata
        )

        session["conversation_history"].append(message)
        session["metadata"].message_count += 1
        session["metadata"].token_count += self._estimate_tokens(content)
        self._save_session(session_id, session)

        logger.debug(f"Added assistant message to session {session_id}")

    def add_fetched_context(
        self,
        session_id: str,
        source_type: Literal["web_search", "js_scraping"],
        content: str,
        url: Optional[str] = None,
        extracted_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add fetched context from various sources"""
        session = self._load_session(session_id)

        context_item = FetchedContextItem(
            source_type=source_type,
            content=content,
            url=url,
            extracted_data=extracted_data
        )

        session["fetched_context"][source_type].append(context_item)
        session["metadata"].token_count += self._estimate_tokens(content)
        self._save_session(session_id, session)

        logger.debug(f"Added {source_type} context to session {session_id}")

    def get_full_context(self, session_id: str) -> Dict[str, Any]:
        """Get the full context in elegant JSON structure."""
        session = self._load_session(session_id)

        return {
            "system_prompt": session["system_prompt"],
            "metadata": session["metadata"].to_dict() if isinstance(session["metadata"], ContextMetadata) else session["metadata"],
            "fetched_context": {
                "web_search": [item.to_dict() if hasattr(item, 'to_dict') else item for item in session["fetched_context"]["web_search"]],
                "js_scraping": [item.to_dict() if hasattr(item, 'to_dict') else item for item in session["fetched_context"]["js_scraping"]]
            },
            "conversation_history": [
                msg.to_dict() if hasattr(msg, 'to_dict') else msg
                for msg in session["conversation_history"]
            ]
        }

    def get_formatted_messages_for_api(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get messages formatted for datascraper.py compatibility.
        Returns messages with prefixes that datascraper._prepare_messages() expects.

        Time/URL context is NOT injected here — that's handled by:
          - PromptBuilder for the agent path
          - openai_search for the research path
        This method only provides: system prompt override (if any),
        fetched content, and conversation history.
        """
        context = self.get_full_context(session_id)
        messages = []

        parts = []

        # Session-level system prompt override (set via set_system_prompt or API)
        if context["system_prompt"]:
            parts.append(context["system_prompt"])

        # Fetched context (scraped pages, search results)
        fetched = context["fetched_context"]

        if fetched.get("web_search"):
            section = "[WEB SEARCH RESULTS]:"
            for item in fetched["web_search"]:
                section += f"\n- From {item.get('url', 'unknown')}: {item['content'][:500]}"
            parts.append(section)

        if fetched.get("js_scraping"):
            section = "[CURRENT PAGE CONTENT - Already scraped, do NOT re-scrape]:"
            for item in fetched["js_scraping"]:
                section += f"\n- From {item.get('url', 'page')}:\n{item['content']}"
            parts.append(section)

        system_content = "\n\n".join(parts)
        if system_content:
            messages.append({"content": f"[SYSTEM MESSAGE]: {system_content}"})

        for msg in context["conversation_history"]:
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                messages.append({"content": f"[USER MESSAGE]: {content}"})
            elif role == "assistant":
                messages.append({"content": f"[ASSISTANT MESSAGE]: {content}"})

        return messages

    def get_session_metadata(self, session_id: str) -> ContextMetadata:
        """Get the metadata object for a session (read-only snapshot)."""
        session = self._load_session(session_id)
        return session["metadata"]

    def set_system_prompt(self, session_id: str, prompt: str) -> None:
        """Override the system prompt for a session."""
        session = self._load_session(session_id)
        session["system_prompt"] = prompt
        self._save_session(session_id, session)

    def clear_fetched_context(self, session_id: str, source_type: Optional[str] = None) -> None:
        """Clear fetched context"""
        session = self._load_session(session_id)

        if source_type:
            if source_type in session["fetched_context"]:
                for item in session["fetched_context"][source_type]:
                    content = item.content if hasattr(item, 'content') else item.get('content', '')
                    session["metadata"].token_count -= self._estimate_tokens(content)
                session["fetched_context"][source_type] = []
        else:
            for key in session["fetched_context"]:
                for item in session["fetched_context"][key]:
                    content = item.content if hasattr(item, 'content') else item.get('content', '')
                    session["metadata"].token_count -= self._estimate_tokens(content)
                session["fetched_context"][key] = []

        self._save_session(session_id, session)

    def clear_conversation_history(self, session_id: str) -> None:
        """Clear conversation history for a session"""
        session = self._load_session(session_id)

        for msg in session["conversation_history"]:
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            session["metadata"].token_count -= self._estimate_tokens(content)

        session["conversation_history"] = []
        session["metadata"].message_count = 0
        self._save_session(session_id, session)

    def get_scraped_urls(self, session_id: str) -> List[str]:
        """Get list of URLs that have already been scraped/fetched"""
        session = self._load_session(session_id)
        urls = []

        for source_type in ("web_search", "js_scraping"):
            for item in session["fetched_context"][source_type]:
                if hasattr(item, 'url') and item.url:
                    urls.append(item.url)
                elif isinstance(item, dict) and item.get('url'):
                    urls.append(item['url'])

        return urls

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get stats for a session"""
        session = self._load_session(session_id)
        metadata = session["metadata"]

        fetched_counts = {
            k: len(v) for k, v in session["fetched_context"].items()
        }

        return {
            "mode": metadata.mode.value if isinstance(metadata.mode, ContextMode) else metadata.mode,
            "message_count": metadata.message_count if hasattr(metadata, 'message_count') else metadata.get('message_count', 0),
            "token_count": metadata.token_count if hasattr(metadata, 'token_count') else metadata.get('token_count', 0),
            "fetched_context_counts": fetched_counts,
            "total_fetched_items": sum(fetched_counts.values())
        }

    def clear_session(self, session_id: str) -> None:
        """Delete a session entirely from cache"""
        cache.delete(self._cache_key(session_id))
        logger.debug(f"Deleted session: {session_id}")


_context_manager = None

def get_context_manager() -> UnifiedContextManager:
    """Get or create the singleton context manager instance"""
    global _context_manager
    if _context_manager is None:
        _context_manager = UnifiedContextManager()
    return _context_manager
