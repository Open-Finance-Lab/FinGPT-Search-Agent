"""
R2C (Reading to Compressing) Context Manager for FinGPT Search Agent
Implements multi-granularity hierarchical compression for conversation context.
"""

import re
import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import tiktoken
from datetime import datetime


class R2CContextManager:
    """
    Manages conversation context using R2C compression algorithm.
    Maintains per-session conversation history with automatic compression.
    """
    
    def __init__(
        self,
        max_tokens: int = 20000,
        compression_ratio: float = 0.5,
        rho: float = 0.5,
        gamma: float = 1.0,
        model: str = "gpt-3.5-turbo"
    ):
        """
        Initialize R2C Context Manager.

        Args:
            max_tokens: Maximum token budget before compression triggers
            compression_ratio: Target compression ratio (0.5 = compress to 50%)
            rho: Hierarchical ratio for chunk vs sentence compression (0-1)
            gamma: Power factor for importance allocation
            model: Model name for tokenizer selection
        """
        self.max_tokens = max_tokens
        self.compression_ratio = compression_ratio
        self.rho = rho
        self.gamma = gamma

        # Initialize tokenizer based on model
        try:
            self.tokenizer = tiktoken.encoding_for_model(model)
        except:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Session storage
        self.sessions = defaultdict(lambda: {
            "messages": [],
            "message_tokens": [],  # Track tokens separately
            "compressed_context": None,
            "token_count": 0,
            "compression_history": [],
            "current_webpage": None,  # Store current webpage info
            "user_timezone": None,  # Store user's timezone
            "user_time": None  # Store user's current time
        })

        # Base system message for financial assistant
        self.base_system_prompt = "You are a helpful financial assistant. Always answer questions to the best of your ability. You are situated inside an agent. The user may asks questions directly related to an active webpage (which you will have context for), or the user may asks questions that requires extensive research."
        
        # Financial keywords for importance scoring
        self.financial_keywords = {
            "high": ["price", "earnings", "revenue", "profit", "loss", "margin", 
                    "ratio", "dividend", "yield", "market", "stock", "bond",
                    "inflation", "gdp", "fed", "rate", "growth"],
            "medium": ["company", "business", "industry", "sector", "share",
                      "invest", "trade", "capital", "asset", "debt", "equity"],
            "low": ["report", "analysis", "forecast", "trend", "data", "information"]
        }

        # logging.info("R2C Context Manager initialized")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using the model's tokenizer."""
        return len(self.tokenizer.encode(text))

    def update_current_webpage(self, session_id: str, url: str) -> None:
        """
        Update the current webpage URL for a session.

        Args:
            session_id: Session identifier
            url: Current webpage URL
        """
        session = self.sessions[session_id]
        session["current_webpage"] = url
        # logging.info(f"[R2C DEBUG] Updated current webpage for session {session_id}: {url}")

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
        # logging.info(f"[R2C DEBUG] Updated time info for session {session_id}: {timezone}, {current_time}")
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to session history.

        Args:
            session_id: Unique session identifier
            role: Message role (user/assistant/system)
            content: Message content
        """
        # logging.info(f"[R2C DEBUG] Adding message to session {session_id}, role: {role}, content_length: {len(content)}")
        session = self.sessions[session_id]

        # Check if this is web content and extract URL
        if role == "user" and "[Web Content from" in content:
            # Extract URL from the web content message
            import re
            url_match = re.search(r'\[Web Content from ([^\]]+)\]:', content)
            if url_match:
                current_url = url_match.group(1)
                self.update_current_webpage(session_id, current_url)

        # Format content with headers to distinguish roles
        if role == "assistant":
            formatted_content = f"[ASSISTANT RESPONSE]: {content}"
        elif role == "user":
            formatted_content = f"[USER QUESTION]: {content}"
        else:  # system or other
            formatted_content = content

        message = {
            "role": "user",  # Always use user role for compatibility
            "content": formatted_content
        }

        tokens = self.count_tokens(formatted_content)
        session["messages"].append(message)
        session["message_tokens"].append(tokens)
        session["token_count"] += tokens

        # Check if compression is needed
        if session["token_count"] > self.max_tokens:
            # logging.info(f"[R2C DEBUG] Token count {session['token_count']} exceeds max {self.max_tokens}, compressing...")
            self._compress_context(session_id)
    
    def get_context(self, session_id: str, include_compressed: bool = True) -> List[Dict]:
        """
        Get conversation context for a session.

        Args:
            session_id: Session identifier
            include_compressed: Whether to include compressed context

        Returns:
            List of messages for the session
        """
        session = self.sessions[session_id]

        # Build system prompt with current webpage info and time/timezone
        system_prompt = self.base_system_prompt

        # Add timezone and time information
        if session.get("user_timezone") or session.get("user_time"):
            from datetime import datetime
            import pytz

            time_info_parts = []
            if session.get("user_timezone") and session.get("user_time"):
                try:
                    # Parse ISO time and convert to user's timezone
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
            system_prompt += f"\n\n[CURRENT CONTEXT]: You are currently viewing the webpage: {session['current_webpage']}. When users ask 'which page am I on' or similar questions about the current page, always confidently tell them they are on: {session['current_webpage']}"

        # Always include system prompt as first message with user role
        context = [{
            "role": "user",
            "content": system_prompt
        }]

        if include_compressed and session["compressed_context"]:
            # Add compressed context with user role
            context.append({
                "role": "user",
                "content": f"[Compressed Context]: {session['compressed_context']}"
            })
            # Add recent messages (last 5 messages uncompressed)
            context.extend(session["messages"][-5:])
        else:
            # Add all messages
            context.extend(session["messages"])

        return context
    
    def clear_session(self, session_id: str) -> None:
        """Clear all messages for a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def clear_conversation_only(self, session_id: str) -> None:
        """Clear conversation messages but preserve web content."""
        if session_id not in self.sessions:
            return
            
        session = self.sessions[session_id]
        preserved_messages = []
        preserved_tokens = []
        preserved_token_count = 0
        
        # Preserve web content messages
        for i, msg in enumerate(session["messages"]):
            if "[Web Content from" in msg.get("content", ""):
                preserved_messages.append(msg)
                preserved_tokens.append(session["message_tokens"][i])
                preserved_token_count += session["message_tokens"][i]
        
        # Reset session with preserved content
        session["messages"] = preserved_messages
        session["message_tokens"] = preserved_tokens
        session["token_count"] = preserved_token_count
        session["compressed_context"] = None
        session["compression_history"] = []

        # logging.info(f"[R2C DEBUG] Cleared conversation for session {session_id}, preserved {len(preserved_messages)} web content messages")
    
    def _sentence_tokenize(self, text: str) -> List[str]:
        """
        Split text into sentences using regex patterns.
        Handles common financial abbreviations.
        """
        # Handle common financial abbreviations
        text = re.sub(r'\b(Mr|Mrs|Dr|Ms|Prof|Sr|Jr)\.$', r'\1<DOT>', text)
        text = re.sub(r'\b(Inc|Ltd|Corp|Co|LLC|LLP)\.$', r'\1<DOT>', text)
        text = re.sub(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.$', r'\1<DOT>', text)
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Restore dots
        sentences = [s.replace('<DOT>', '.') for s in sentences if s.strip()]
        
        return sentences
    
    def _compute_importance(self, text: str, position: int = 0, total: int = 1) -> float:
        """
        Compute importance score for text segment.
        
        Args:
            text: Text to score
            position: Position in conversation (0 = oldest)
            total: Total number of segments
            
        Returns:
            Importance score (0-1)
        """
        score = 0.0
        
        # 1. Length-based score (shorter = more important)
        words = text.split()
        if words:
            length_score = 1.0 / (1.0 + np.log(len(words)))
            score += length_score * 0.2
        
        # 2. Financial keyword score
        text_lower = text.lower()
        keyword_score = 0.0
        for weight, keywords in [
            (1.0, self.financial_keywords["high"]),
            (0.6, self.financial_keywords["medium"]),
            (0.3, self.financial_keywords["low"])
        ]:
            matches = sum(1 for kw in keywords if kw in text_lower)
            keyword_score += matches * weight
        
        keyword_score = min(keyword_score / 5.0, 1.0)  # Normalize
        score += keyword_score * 0.4
        
        # 3. Recency score (newer = more important)
        recency_score = (position + 1) / total
        score += recency_score * 0.2
        
        # 4. Question/Answer pattern score
        if "?" in text:
            score += 0.1  # Questions are important
        if any(word in text_lower for word in ["answer:", "response:", "result:"]):
            score += 0.1  # Answers are important
        
        return min(score, 1.0)
    
    def _compress_context(self, session_id: str) -> None:
        """
        Compress context using R2C algorithm.
        
        Args:
            session_id: Session identifier
        """
        session = self.sessions[session_id]
        messages = session["messages"]
        
        if len(messages) < 3:  # Don't compress if too few messages
            return
        
        # Convert messages to chunks (group by role continuity)
        chunks = []
        current_chunk = []
        current_role = None
        
        for msg in messages[:-2]:  # Keep last 2 messages uncompressed
            if msg["role"] != current_role and current_chunk:
                chunks.append({
                    "role": current_role,
                    "content": " ".join([m["content"] for m in current_chunk]),
                    "messages": current_chunk
                })
                current_chunk = []
            
            current_role = msg["role"]
            current_chunk.append(msg)
        
        if current_chunk:
            chunks.append({
                "role": current_role,
                "content": " ".join([m["content"] for m in current_chunk]),
                "messages": current_chunk
            })
        
        if not chunks:
            return
        
        # Apply R2C compression
        compressed_text = self._r2c_compress(chunks)
        
        # Calculate original token count before updating
        original_token_count = sum(session["message_tokens"][:-2])  # All tokens except last 2
        compressed_tokens = self.count_tokens(compressed_text)
        
        # Update session
        session["compressed_context"] = compressed_text
        session["messages"] = messages[-2:]  # Keep only recent messages
        session["message_tokens"] = session["message_tokens"][-2:]  # Keep corresponding tokens
        session["token_count"] = compressed_tokens + sum(session["message_tokens"])
        
        # Log compression
        session["compression_history"].append({
            "timestamp": datetime.now().isoformat(),
            "original_tokens": original_token_count,
            "compressed_tokens": compressed_tokens,
            "chunks_compressed": len(chunks)
        })

        # logging.info(f"Compressed context for session {session_id}: "
        #             f"{len(messages)} messages -> {len(chunks)} chunks -> "
        #             f"{session['token_count']} tokens")
    
    def _r2c_compress(self, chunks: List[Dict]) -> str:
        """
        Apply R2C compression algorithm to chunks.
        
        Args:
            chunks: List of conversation chunks
            
        Returns:
            Compressed text
        """
        # Calculate tokens to remove
        total_tokens = sum(self.count_tokens(chunk["content"]) for chunk in chunks)
        e_comp = int(total_tokens * self.compression_ratio)
        
        # Step 1: Compute chunk-level importance
        chunk_importances = []
        for i, chunk in enumerate(chunks):
            importance = self._compute_importance(
                chunk["content"], 
                position=i, 
                total=len(chunks)
            )
            chunk_importances.append(importance)
        
        # Sort chunks by importance (descending)
        sorted_indices = sorted(
            range(len(chunks)), 
            key=lambda i: chunk_importances[i], 
            reverse=True
        )
        
        # Step 2: Chunk-level compression
        e_chunk = int(self.rho * e_comp)
        cumulative_removed = 0
        k_prime = len(chunks)
        
        # Remove least important chunks
        for i in range(len(chunks)-1, -1, -1):
            idx = sorted_indices[i]
            chunk_tokens = self.count_tokens(chunks[idx]["content"])
            if cumulative_removed >= e_chunk:
                break
            cumulative_removed += chunk_tokens
            k_prime -= 1
        
        # Keep top k_prime chunks
        remaining_chunks = [chunks[sorted_indices[i]] for i in range(k_prime)]
        remaining_importances = [chunk_importances[sorted_indices[i]] for i in range(k_prime)]
        
        # Step 3: Sentence-level compression
        e_sent = e_comp - cumulative_removed
        compressed_chunks = []
        
        if e_sent > 0 and remaining_chunks:
            # Allocate sentence compression budget
            inv_importances = [1.0 / (imp + 1e-6) for imp in remaining_importances]
            sum_inv = sum(inv_importances)
            
            for i, chunk in enumerate(remaining_chunks):
                # Calculate tokens to remove from this chunk
                e_sent_i = int((inv_importances[i] / sum_inv) ** self.gamma * e_sent)
                
                # Tokenize into sentences
                sentences = self._sentence_tokenize(chunk["content"])
                if not sentences:
                    compressed_chunks.append(chunk["content"])
                    continue
                
                # Compute sentence importance
                sent_importances = []
                for j, sent in enumerate(sentences):
                    importance = self._compute_importance(
                        sent, 
                        position=j, 
                        total=len(sentences)
                    )
                    sent_importances.append(importance)
                
                # Sort sentences by importance
                sorted_sent_indices = sorted(
                    range(len(sentences)),
                    key=lambda j: sent_importances[j],
                    reverse=True
                )
                
                # Remove least important sentences
                sent_cumulative = 0
                m_prime = len(sentences)
                for j in range(len(sentences)-1, -1, -1):
                    idx = sorted_sent_indices[j]
                    sent_tokens = self.count_tokens(sentences[idx])
                    if sent_cumulative >= e_sent_i:
                        break
                    sent_cumulative += sent_tokens
                    m_prime -= 1
                
                # Keep important sentences in original order
                kept_indices = set(sorted_sent_indices[:m_prime])
                kept_sentences = [
                    sentences[j] for j in range(len(sentences)) 
                    if j in kept_indices
                ]
                
                compressed_chunks.append(" ".join(kept_sentences))
        else:
            compressed_chunks = [c['content'] for c in remaining_chunks]
        
        return "\n\n".join(compressed_chunks)
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session."""
        if session_id not in self.sessions:
            return {}
        
        session = self.sessions[session_id]
        return {
            "message_count": len(session["messages"]),
            "token_count": session["token_count"],
            "compressed": session["compressed_context"] is not None,
            "compression_count": len(session["compression_history"]),
            "compression_history": session["compression_history"]
        }