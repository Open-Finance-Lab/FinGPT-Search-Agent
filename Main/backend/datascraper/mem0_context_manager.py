"""
Mem0 Context Manager for FinGPT Search Agent
Implements production-ready memory layer using Mem0 for conversation context.
"""

import logging
import os
from typing import List, Dict, Optional
from datetime import datetime, UTC
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from collections import defaultdict

# Mem0 will be imported conditionally to handle cases where it's not installed yet
try:
    from mem0 import MemoryClient
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logging.warning("Mem0 not installed. Install with: pip install mem0ai")


class Mem0ContextManager:
    """
    Manages conversation context using Mem0's production memory layer.
    Automatically extracts facts, preferences, and relationships from conversations.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_recent_messages: int = 10,
    ):
        """
        Initialize Mem0 Context Manager.

        Args:
            api_key: Mem0 API key (defaults to MEM0_API_KEY env var)
            max_recent_messages: Number of recent messages to keep verbatim
        """
        if not MEM0_AVAILABLE:
            raise ImportError(
                "Mem0 is not installed. Install with: pip install mem0ai\n"
                "Visit https://mem0.ai to get an API key."
            )

        self.api_key = api_key or os.getenv("MEM0_API_KEY")
        if not self.api_key:
            raise ValueError(
                "MEM0_API_KEY not found. Set it in environment variables or pass it to the constructor.\n"
                "Get your API key at: https://app.mem0.ai/dashboard/api-keys"
            )

        self.max_recent_messages = max_recent_messages
        self.max_session_tokens = max(
            int(os.getenv("MEM0_CONTEXT_TOKEN_LIMIT", "50000")),
            2000,
        )
        target_ratio = float(os.getenv("MEM0_COMPRESSION_TARGET_RATIO", "0.7"))
        self.compression_target_ratio = min(max(target_ratio, 0.4), 0.9)
        self.max_compression_chars = max(int(os.getenv("MEM0_COMPRESSION_MAX_CHARS", "4000")), 500)
        self.min_messages_before_compress = max(int(os.getenv("MEM0_MIN_MESSAGES_BEFORE_COMPRESS", "6")), 2)

        # Initialize Mem0 client
        try:
            self.client = MemoryClient(api_key=self.api_key)
        except Exception as e:
            logging.error(f"Failed to initialize Mem0 client: {e}")
            raise

        # Local session storage for per-worker short-term buffers and metadata
        self.sessions = defaultdict(self._session_factory)

        # Base system message for financial assistant
        self.base_system_prompt = (
            "You are a helpful financial assistant. Always answer questions to the best of your ability. "
            "You are situated inside an agent. The user may ask questions directly related to an active webpage "
            "(which you will have context for), or the user may ask questions that require extensive research."
        )

    def _session_factory(self) -> dict:
        """Create new session storage."""
        return {
            "recent_messages": [],
            "message_count": 0,
            "token_count": 0,
            "current_webpage": None,
            "user_timezone": None,
            "user_time": None,
            "last_used": datetime.now(UTC),
            "mem0_operations": 0,
            "compressed_chunk_count": 0,
            "has_compressed_chunks": False,
        }

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to session history and Mem0 memory.

        Args:
            session_id: Unique session identifier
            role: Message role (user/assistant/system)
            content: Message content
        """
        session = self.sessions[session_id]
        session["last_used"] = datetime.now(UTC)

        # Check if this is web content and extract URL
        if role == "user" and "[Web Content from" in content:
            import re
            url_match = re.search(r'\[Web Content from ([^\]]+)\]:', content)
            if url_match:
                current_url = url_match.group(1)
                self.update_current_webpage(session_id, current_url)

        timestamp = datetime.now(UTC)
        formatted_content = self._format_message_content(role, content)
        token_estimate = self.count_tokens(content)

        message = {
            "role": role,
            "content": content,
            "formatted": formatted_content,
            "timestamp": timestamp,
            "token_estimate": token_estimate,
        }

        session["recent_messages"].append(message)
        session["message_count"] += 1
        session["token_count"] += token_estimate

        self._check_context_limits(session_id)

    def get_context(self, session_id: str, query: Optional[str] = None) -> List[Dict]:
        """
        Get conversation context for a session.

        Args:
            session_id: Session identifier
            query: Optional query for retrieving relevant memories

        Returns:
            List of messages for the session (system prompt + relevant memories + recent messages)
        """
        session = self.sessions[session_id]
        session["last_used"] = datetime.now(UTC)

        # Build system prompt with current webpage info and time/timezone
        system_prompt = self.base_system_prompt

        # Add timezone and time information
        if session.get("user_timezone") or session.get("user_time"):
            time_info_parts = []
            user_timezone = session.get("user_timezone")
            user_time_str = session.get("user_time")

            if user_time_str:
                try:
                    utc_time = datetime.fromisoformat(user_time_str.replace('Z', '+00:00'))
                except ValueError as exc:
                    logging.warning(f"Error parsing user time '{user_time_str}': {exc}")
                    utc_time = None

                if utc_time and user_timezone:
                    try:
                        local_time = utc_time.astimezone(ZoneInfo(user_timezone))
                        time_info_parts.append(f"User's timezone: {user_timezone}")
                        time_info_parts.append(
                            f"Current local time for user: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                        )
                    except ZoneInfoNotFoundError:
                        logging.warning(f"Unknown timezone '{user_timezone}', using UTC time reference")
                        time_info_parts.append(f"User's timezone: {user_timezone} (unrecognized)")
                        time_info_parts.append(
                            f"User provided time (UTC): {utc_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                        )
                elif utc_time:
                    time_info_parts.append(
                        f"User provided time (UTC): {utc_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )
            elif user_timezone:
                time_info_parts.append(f"User's timezone: {user_timezone}")

            if time_info_parts:
                system_prompt += f"\n\n[TIME CONTEXT]: {' | '.join(time_info_parts)}"

        if session.get("current_webpage"):
            system_prompt += (
                f"\n\n[CURRENT CONTEXT]: You are currently viewing the webpage: {session['current_webpage']}. "
                f"When users ask 'which page am I on' or similar questions about the current page, "
                f"always confidently tell them they are on: {session['current_webpage']}"
            )

        # Start with system prompt
        context = [{
            "role": "user",
            "content": system_prompt
        }]

        # Include compressed chunks only when they exist
        if session.get("has_compressed_chunks"):
            for chunk in self._get_compressed_chunks(session_id, query=query):
                context.append(chunk)

        # Retrieve recent conversation entries from local buffer
        for msg in self._get_recent_conversation_entries(session_id):
            context.append({
                "role": "user",
                "content": msg["formatted"],
            })

        return context

    def update_current_webpage(self, session_id: str, url: str) -> None:
        """
        Update the current webpage URL for a session.

        Args:
            session_id: Session identifier
            url: Current webpage URL
        """
        session = self.sessions[session_id]
        session["current_webpage"] = url
        session["last_used"] = datetime.now(UTC)
        logging.debug(f"[Mem0] Updated current webpage for session {session_id}: {url}")

    def update_user_time_info(self, session_id: str, timezone: str = None, current_time: str = None) -> None:
        """
        Update the user's timezone and current time for a session.

        Args:
            session_id: Session identifier
            timezone: User's IANA timezone (e.g., "America/New_York")
            current_time: User's current time in ISO format
        """
        session = self.sessions[session_id]
        if timezone:
            session["user_timezone"] = timezone
        if current_time:
            session["user_time"] = current_time
        session["last_used"] = datetime.now(UTC)
        logging.debug(f"[Mem0] Updated time info for session {session_id}: {timezone}, {current_time}")

    def clear_session(self, session_id: str) -> None:
        """
        Clear all messages and memories for a session.

        Args:
            session_id: Session identifier
        """
        session = self.sessions.get(session_id)
        if session:
            session["recent_messages"].clear()
            session["message_count"] = 0
            session["token_count"] = 0
            session["compressed_chunk_count"] = 0
            session["has_compressed_chunks"] = False

        # Clear Mem0 memories for this user
        try:
            self.client.delete_all(user_id=session_id)
            if session:
                session["mem0_operations"] += 1
            logging.info(f"[Mem0] Cleared all memories for session {session_id}")
        except Exception as e:
            logging.error(f"[Mem0] Failed to clear memories: {e}")

        if session_id in self.sessions:
            del self.sessions[session_id]

    def clear_conversation_only(self, session_id: str) -> None:
        """
        Clear recent conversation messages but preserve long-term memories and web content.

        Args:
            session_id: Session identifier
        """
        session = self.sessions.get(session_id)
        if not session:
            return

        preserved_messages = []
        for msg in session["recent_messages"]:
            if "[Web Content from" in msg.get("content", ""):
                preserved_messages.append(msg)

        session["recent_messages"] = preserved_messages
        session["message_count"] = len(preserved_messages)
        session["token_count"] = sum(
            m.get("token_estimate", self.count_tokens(m.get("content", ""))) for m in preserved_messages
        )
        session["compressed_chunk_count"] = 0
        session["has_compressed_chunks"] = False
        session["last_used"] = datetime.now(UTC)

        try:
            self.client.delete_all(user_id=session_id)
            session["mem0_operations"] += 1
        except Exception as e:
            logging.error(f"[Mem0] Failed to clear compressed chunks: {e}")

        logging.info(f"[Mem0] Cleared conversation for session {session_id}, preserved {len(preserved_messages)} web content messages")

    def get_session_stats(self, session_id: str) -> Dict:
        """
        Get statistics for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session statistics
        """
        session = self.sessions.get(session_id)
        if not session:
            return {}

        last_used = session.get("last_used")
        return {
            "recent_message_count": len(session["recent_messages"]),
            "total_message_count": session.get("message_count", 0),
            "compressed_chunk_count": session.get("compressed_chunk_count", 0),
            "memory_count": session.get("compressed_chunk_count", 0),
            "token_estimate": session.get("token_count", 0),
            "mem0_operations": session.get("mem0_operations", 0),
            "current_webpage": session.get("current_webpage"),
            "last_used": last_used.isoformat() if last_used else None,
            "active_sessions": len(self.sessions),
            "using_mem0": True,
        }

    def _format_message_content(self, role: str, content: str) -> str:
        if role == "assistant":
            return f"[ASSISTANT RESPONSE]: {content}"
        if role == "user":
            return f"[USER QUESTION]: {content}"
        return content

    def _check_context_limits(self, session_id: str) -> None:
        session = self.sessions[session_id]
        if session["token_count"] <= self.max_session_tokens:
            return
        if len(session["recent_messages"]) < self.min_messages_before_compress:
            return
        self._compress_session_history(session_id)

    def _compress_session_history(self, session_id: str) -> None:
        session = self.sessions[session_id]
        target_tokens = int(self.max_session_tokens * self.compression_target_ratio)
        target_tokens = max(target_tokens, int(self.max_session_tokens * 0.5))

        removed_messages = []
        while session["token_count"] > target_tokens and session["recent_messages"]:
            oldest = session["recent_messages"].pop(0)
            session["token_count"] -= oldest.get("token_estimate", self.count_tokens(oldest.get("content", "")))
            removed_messages.append(oldest)

        if not removed_messages:
            return

        chunk_index = session.get("compressed_chunk_count", 0) + 1
        chunk_text = self._summarize_messages_for_mem0(removed_messages, chunk_index)
        try:
            self._store_compressed_chunk(session_id, chunk_text, chunk_index, removed_messages[-1]["timestamp"])
            session["compressed_chunk_count"] = chunk_index
            session["has_compressed_chunks"] = True
            logging.info(f"[Mem0] Stored compressed chunk #{chunk_index} for session {session_id}")
        except Exception as e:
            logging.error(f"[Mem0] Failed to store compressed chunk: {e}")
            # If storing fails, push removed messages back to preserve context
            session["recent_messages"] = removed_messages + session["recent_messages"]
            session["token_count"] += sum(m.get("token_estimate", self.count_tokens(m.get("content", ""))) for m in removed_messages)

    def _summarize_messages_for_mem0(self, messages: List[Dict], chunk_index: int) -> str:
        summary_lines = [f"[COMPRESSED CHUNK #{chunk_index}] Earlier conversation context:"]
        for msg in messages:
            role_label = "Assistant" if msg.get("role") == "assistant" else "User"
            formatted = msg.get("formatted") or msg.get("content", "")
            summary_lines.append(f"{role_label}: {formatted}")
            if sum(len(line) for line in summary_lines) > self.max_compression_chars:
                summary_lines.append("... (truncated)")
                break

        summary = "\n".join(summary_lines)
        if len(summary) > self.max_compression_chars:
            summary = summary[: self.max_compression_chars] + "..."
        return summary

    def _store_compressed_chunk(self, session_id: str, chunk_text: str, chunk_index: int, timestamp: datetime) -> None:
        metadata = {
            "session_id": session_id,
            "memory_type": "compressed_chunk",
            "chunk_sequence": chunk_index,
            "timestamp": timestamp.isoformat(),
        }
        self.client.add(
            messages=[{"role": "user", "content": chunk_text}],
            user_id=session_id,
            metadata=metadata,
        )
        session = self.sessions[session_id]
        session["mem0_operations"] += 1

    def _get_recent_conversation_entries(self, session_id: str) -> List[Dict]:
        session = self.sessions[session_id]
        return list(session["recent_messages"])

    def _get_compressed_chunks(self, session_id: str, query: Optional[str] = None) -> List[Dict]:
        session = self.sessions[session_id]
        try:
            if query:
                search_result = self.client.search(query=query, user_id=session_id, limit=5)
                memories = search_result.get('results', []) if isinstance(search_result, dict) else search_result
            else:
                get_all_result = self.client.get_all(user_id=session_id)
                memories = get_all_result.get('results', []) if isinstance(get_all_result, dict) else get_all_result
            session["mem0_operations"] += 1
        except Exception as e:
            logging.error(f"[Mem0] Failed to load compressed chunks: {e}")
            return []

        chunks: List[Dict] = []
        for memory in memories or []:
            metadata = memory.get('metadata') or {}
            if metadata.get('memory_type') != 'compressed_chunk':
                continue
            chunk_text = memory.get('memory') or memory.get('text') or memory.get('content')
            if not chunk_text:
                continue
            sequence = metadata.get('chunk_sequence', 0)
            chunks.append({
                "role": "user",
                "content": chunk_text,
                "sequence": sequence,
            })

        chunks.sort(key=lambda item: item.get('sequence', 0))
        return chunks

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        Note: Mem0 handles token management internally, but this is kept for compatibility.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token
        return len(text) // 4
