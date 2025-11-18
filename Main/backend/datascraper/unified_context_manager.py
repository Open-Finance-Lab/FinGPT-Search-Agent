"""
Unified Context Manager for FinGPT - Clean Version
Handles all conversation context with elegant JSON structure
NO compression, NO legacy support - pure session-based context tracking
Author: Linus (following good taste principles)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)


class ContextMode(Enum):
    """Modes of operation for context"""
    RESEARCH = "research"    # Web search mode
    THINKING = "thinking"    # Agent with tools mode
    NORMAL = "normal"        # Standard chat mode


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
    source_type: Literal["web_search", "playwright", "js_scraping"]
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
    No compression, no legacy support - just pure context tracking.
    """

    def __init__(self):
        """Initialize the unified context manager"""
        self.sessions: Dict[str, Dict[str, Any]] = {}
        logger.info("UnifiedContextManager initialized (no compression, no legacy support)")

    def _get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "system_prompt": self._get_default_system_prompt(),
                "metadata": ContextMetadata(
                    session_id=session_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    mode=ContextMode.NORMAL
                ),
                "fetched_context": {
                    "web_search": [],
                    "playwright": [],
                    "js_scraping": []
                },
                "conversation_history": []
            }
            logger.debug(f"Created new session: {session_id}")
        return self.sessions[session_id]

    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt"""
        return (
            "You are FinGPT, an advanced financial assistant with web search capabilities. "
            "You provide accurate, up-to-date financial information and analysis. "
            "Always cite your sources when providing market data or news. "
            "Be concise, professional, and focus on factual information."
        )

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (~4 chars per token)"""
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
        session = self._get_or_create_session(session_id)
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
        logger.debug(f"Updated metadata for session {session_id}")

    def add_user_message(
        self,
        session_id: str,
        content: str,
        timestamp: Optional[str] = None
    ) -> None:
        """Add a user message to conversation history"""
        session = self._get_or_create_session(session_id)

        message = ConversationMessage(
            role="user",
            content=content,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat()
        )

        session["conversation_history"].append(message)
        session["metadata"].message_count += 1
        session["metadata"].token_count += self._estimate_tokens(content)

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
        session = self._get_or_create_session(session_id)

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

        logger.debug(f"Added assistant message to session {session_id}")

    def add_fetched_context(
        self,
        session_id: str,
        source_type: Literal["web_search", "playwright", "js_scraping"],
        content: str,
        url: Optional[str] = None,
        extracted_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add fetched context from various sources"""
        session = self._get_or_create_session(session_id)

        context_item = FetchedContextItem(
            source_type=source_type,
            content=content,
            url=url,
            extracted_data=extracted_data
        )

        session["fetched_context"][source_type].append(context_item)
        session["metadata"].token_count += self._estimate_tokens(content)

        logger.debug(f"Added {source_type} context to session {session_id}")

    def get_full_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get the full context in elegant JSON structure.
        """
        session = self._get_or_create_session(session_id)

        context = {
            "system_prompt": session["system_prompt"],
            "metadata": session["metadata"].to_dict() if isinstance(session["metadata"], ContextMetadata) else session["metadata"],
            "fetched_context": {
                "web_search": [item.to_dict() if hasattr(item, 'to_dict') else item for item in session["fetched_context"]["web_search"]],
                "playwright": [item.to_dict() if hasattr(item, 'to_dict') else item for item in session["fetched_context"]["playwright"]],
                "js_scraping": [item.to_dict() if hasattr(item, 'to_dict') else item for item in session["fetched_context"]["js_scraping"]]
            },
            "conversation_history": [
                msg.to_dict() if hasattr(msg, 'to_dict') else msg
                for msg in session["conversation_history"]
            ]
        }

        return context

    def get_formatted_messages_for_api(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get messages formatted for datascraper.py compatibility.
        Returns messages with prefixes that datascraper._prepare_messages() expects.
        """
        context = self.get_full_context(session_id)
        messages = []

        # 1. Build system message with all context
        system_content = context["system_prompt"]

        # Add metadata context
        metadata = context["metadata"]
        if metadata.get("current_url"):
            system_content += f"\n\n[CURRENT CONTEXT]: You are viewing: {metadata['current_url']}"
        if metadata.get("user_timezone") or metadata.get("user_time"):
            time_parts = []
            if metadata.get("user_timezone"):
                time_parts.append(f"Timezone: {metadata['user_timezone']}")
            if metadata.get("user_time"):
                time_parts.append(f"Time: {metadata['user_time']}")
            system_content += f"\n\n[TIME CONTEXT]: {' | '.join(time_parts)}"

        # Add fetched context
        fetched = context["fetched_context"]

        if fetched.get("web_search"):
            system_content += "\n\n[WEB SEARCH RESULTS]:"
            for item in fetched["web_search"]:
                system_content += f"\n- From {item.get('url', 'unknown')}: {item['content'][:200]}"

        if fetched.get("playwright"):
            system_content += "\n\n[PLAYWRIGHT SCRAPED CONTENT]:"
            for item in fetched["playwright"]:
                system_content += f"\n- From {item.get('url', 'page')}: {item['content'][:200]}"

        if fetched.get("js_scraping"):
            system_content += "\n\n[WEB PAGE CONTENT]:"
            for item in fetched["js_scraping"]:
                system_content += f"\n- From {item.get('url', 'page')}: {item['content'][:200]}"

        # System message with prefix for datascraper.py compatibility
        messages.append({"content": f"[SYSTEM MESSAGE]: {system_content}"})

        # 2. Add full conversation history with prefixes
        for msg in context["conversation_history"]:
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                messages.append({"content": f"[USER MESSAGE]: {content}"})
            elif role == "assistant":
                messages.append({"content": f"[ASSISTANT MESSAGE]: {content}"})

        return messages

    def clear_fetched_context(self, session_id: str, source_type: Optional[str] = None) -> None:
        """Clear fetched context"""
        session = self._get_or_create_session(session_id)

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

    def clear_conversation_history(self, session_id: str) -> None:
        """Clear conversation history for a session"""
        session = self._get_or_create_session(session_id)

        for msg in session["conversation_history"]:
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            session["metadata"].token_count -= self._estimate_tokens(content)

        session["conversation_history"] = []
        session["metadata"].message_count = 0
        logger.info(f"Cleared conversation history for session {session_id}")

    def clear_session(self, session_id: str) -> None:
        """Completely clear a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared session {session_id}")

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics about a session"""
        session = self._get_or_create_session(session_id)
        metadata = session["metadata"]

        fetched_counts = {
            source: len(items)
            for source, items in session["fetched_context"].items()
        }

        stats = {
            "session_id": session_id,
            "mode": metadata.mode.value if hasattr(metadata.mode, 'value') else metadata.get("mode", "normal"),
            "message_count": metadata.message_count if hasattr(metadata, 'message_count') else metadata.get("message_count", 0),
            "token_count": metadata.token_count if hasattr(metadata, 'token_count') else metadata.get("token_count", 0),
            "fetched_context_counts": fetched_counts,
            "total_fetched_items": sum(fetched_counts.values()),
            "current_url": metadata.current_url if hasattr(metadata, 'current_url') else metadata.get("current_url"),
            "last_updated": metadata.timestamp if hasattr(metadata, 'timestamp') else metadata.get("timestamp")
        }

        return stats

    def export_session_json(self, session_id: str) -> str:
        """Export session as formatted JSON string"""
        context = self.get_full_context(session_id)
        return json.dumps(context, indent=2, ensure_ascii=False)


# Singleton instance
_context_manager = None

def get_context_manager() -> UnifiedContextManager:
    """Get or create the singleton context manager instance"""
    global _context_manager
    if _context_manager is None:
        _context_manager = UnifiedContextManager()
    return _context_manager