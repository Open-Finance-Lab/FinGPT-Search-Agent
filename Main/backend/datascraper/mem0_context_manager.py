"""
Mem0 Context Manager for FinGPT Search Agent
Implements production-ready memory layer using Mem0 for conversation context.
"""

import logging
import os
from typing import List, Dict, Optional
from datetime import datetime
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

        # Initialize Mem0 client with minimal parameters
        try:
            self.client = MemoryClient(api_key=self.api_key)
            logging.info("Mem0 Context Manager initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize Mem0 client: {e}")
            raise

        # Local session storage for recent messages and metadata
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
            "recent_messages": [],  # Last N messages verbatim
            "message_count": 0,
            "current_webpage": None,
            "user_timezone": None,
            "user_time": None,
            "last_used": datetime.utcnow(),
            "mem0_operations": 0,
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
        session["last_used"] = datetime.utcnow()

        # Check if this is web content and extract URL
        if role == "user" and "[Web Content from" in content:
            import re
            url_match = re.search(r'\[Web Content from ([^\]]+)\]:', content)
            if url_match:
                current_url = url_match.group(1)
                self.update_current_webpage(session_id, current_url)

        # Format message with role headers for clarity
        if role == "assistant":
            formatted_content = f"[ASSISTANT RESPONSE]: {content}"
        elif role == "user":
            formatted_content = f"[USER QUESTION]: {content}"
        else:
            formatted_content = content

        # Store in recent messages (sliding window)
        message = {
            "role": role,
            "content": formatted_content,
            "timestamp": datetime.utcnow().isoformat()
        }

        session["recent_messages"].append(message)
        session["message_count"] += 1

        # Keep only last N messages
        if len(session["recent_messages"]) > self.max_recent_messages:
            session["recent_messages"].pop(0)

        # Add to Mem0 for long-term memory extraction
        try:
            # Mem0 automatically extracts facts, preferences, and entities
            self.client.add(
                messages=[{"role": role, "content": content}],
                user_id=session_id,
                metadata={
                    "session_id": session_id,
                    "timestamp": message["timestamp"],
                    "webpage": session.get("current_webpage"),
                    "timezone": session.get("user_timezone"),
                }
            )
            session["mem0_operations"] += 1
            logging.debug(f"[Mem0] Added message to memory for session {session_id}")
        except Exception as e:
            logging.error(f"[Mem0] Failed to add message: {e}")
            # Continue execution - recent messages still available

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
        session["last_used"] = datetime.utcnow()

        # Build system prompt with current webpage info and time/timezone
        system_prompt = self.base_system_prompt

        # Add timezone and time information
        if session.get("user_timezone") or session.get("user_time"):
            from datetime import datetime
            import pytz

            time_info_parts = []
            if session.get("user_timezone") and session.get("user_time"):
                try:
                    utc_time = datetime.fromisoformat(session["user_time"].replace('Z', '+00:00'))
                    user_tz = pytz.timezone(session["user_timezone"])
                    local_time = utc_time.astimezone(user_tz)

                    time_info_parts.append(f"User's timezone: {session['user_timezone']}")
                    time_info_parts.append(f"Current local time for user: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                except Exception as e:
                    logging.warning(f"Error formatting time info: {e}")
                    if session.get("user_timezone"):
                        time_info_parts.append(f"User's timezone: {session['user_timezone']}")
            elif session.get("user_timezone"):
                time_info_parts.append(f"User's timezone: {session['user_timezone']}")

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

        # Retrieve relevant memories from Mem0
        try:
            if query:
                # Search for relevant memories based on the query
                search_result = self.client.search(
                    query=query,
                    user_id=session_id,
                    limit=5  # Get top 5 relevant memories
                )
                session["mem0_operations"] += 1

                # Extract results from the response dict
                memories = search_result.get('results', []) if isinstance(search_result, dict) else search_result

                if memories and len(memories) > 0:
                    # Format retrieved memories
                    memory_text = "[RELEVANT CONTEXT FROM PREVIOUS CONVERSATIONS]:\n"
                    for idx, memory in enumerate(memories, 1):
                        memory_content = memory.get('memory', memory.get('text', ''))
                        if memory_content:
                            memory_text += f"{idx}. {memory_content}\n"

                    context.append({
                        "role": "user",
                        "content": memory_text
                    })
                    logging.debug(f"[Mem0] Retrieved {len(memories)} relevant memories for session {session_id}")
            else:
                # If no specific query, get all memories for this session
                get_all_result = self.client.get_all(user_id=session_id)
                session["mem0_operations"] += 1

                # Extract results from the response dict
                all_memories = get_all_result.get('results', []) if isinstance(get_all_result, dict) else get_all_result

                if all_memories and len(all_memories) > 0:
                    memory_text = "[CONTEXT FROM PREVIOUS CONVERSATIONS]:\n"
                    for idx, memory in enumerate(all_memories[:10], 1):  # Limit to 10 most relevant
                        memory_content = memory.get('memory', memory.get('text', ''))
                        if memory_content:
                            memory_text += f"{idx}. {memory_content}\n"

                    context.append({
                        "role": "user",
                        "content": memory_text
                    })
                    logging.debug(f"[Mem0] Retrieved {len(all_memories)} total memories for session {session_id}")

        except Exception as e:
            logging.error(f"[Mem0] Failed to retrieve memories: {e}")
            # Continue without memories - recent messages still available

        # Add recent messages verbatim (last N exchanges)
        for msg in session["recent_messages"]:
            context.append({
                "role": "user",  # Use "user" role for compatibility
                "content": msg["content"]
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
        session["last_used"] = datetime.utcnow()
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
        session["last_used"] = datetime.utcnow()
        logging.debug(f"[Mem0] Updated time info for session {session_id}: {timezone}, {current_time}")

    def clear_session(self, session_id: str) -> None:
        """
        Clear all messages and memories for a session.

        Args:
            session_id: Session identifier
        """
        # Clear local session data
        if session_id in self.sessions:
            del self.sessions[session_id]

        # Clear Mem0 memories for this user
        try:
            self.client.delete_all(user_id=session_id)
            logging.info(f"[Mem0] Cleared all memories for session {session_id}")
        except Exception as e:
            logging.error(f"[Mem0] Failed to clear memories: {e}")

    def clear_conversation_only(self, session_id: str) -> None:
        """
        Clear recent conversation messages but preserve long-term memories and web content.

        Args:
            session_id: Session identifier
        """
        session = self.sessions.get(session_id)
        if not session:
            return

        # Preserve web content messages
        preserved_messages = []
        for msg in session["recent_messages"]:
            if "[Web Content from" in msg.get("content", ""):
                preserved_messages.append(msg)

        # Reset session but keep metadata and preserved messages
        session["recent_messages"] = preserved_messages
        session["message_count"] = len(preserved_messages)
        session["last_used"] = datetime.utcnow()

        # Note: Long-term memories in Mem0 are preserved automatically
        logging.info(f"[Mem0] Cleared recent conversation for session {session_id}, preserved {len(preserved_messages)} web content messages")

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

        # Get memory count from Mem0
        memory_count = 0
        try:
            get_all_result = self.client.get_all(user_id=session_id)
            # Extract results from the response dict
            memories = get_all_result.get('results', []) if isinstance(get_all_result, dict) else get_all_result
            memory_count = len(memories) if memories else 0
        except Exception as e:
            logging.error(f"[Mem0] Failed to get memory count: {e}")

        last_used = session.get("last_used")
        return {
            "recent_message_count": len(session["recent_messages"]),
            "total_message_count": session["message_count"],
            "memory_count": memory_count,
            "mem0_operations": session.get("mem0_operations", 0),
            "current_webpage": session.get("current_webpage"),
            "last_used": last_used.isoformat() if last_used else None,
            "active_sessions": len(self.sessions),
            "using_mem0": True,
        }

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
