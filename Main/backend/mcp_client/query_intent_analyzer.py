# backend/mcp_client/query_intent_analyzer.py

"""
Query Intent Analyzer for Smart MCP Context Fetching

This module analyzes user queries to determine if they would benefit from
automatic fetching of the current page content via Playwright MCP.

Key detection patterns:
1. Vague queries lacking specific entities
2. Contextual indicators (pronouns, demonstratives)
3. Time-sensitive language
4. Questions without clear scope
"""

import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Patterns for detecting queries that likely need page context
VAGUE_TIME_PATTERNS = [
    r'\btoday\'?s?\b',
    r'\bcurrent\b',
    r'\bnow\b',
    r'\blatest\b',
    r'\brecent\b',
    r'\bthis\s+(week|month|year|morning|afternoon)\b',
]

# Contextual indicators suggesting user is referring to current page
CONTEXTUAL_INDICATORS = [
    r'\bthis\s+(page|site|website|article)\b',
    r'\bhere\b',
    r'\bon\s+this\b',
    r'\bwhat\'?s\s+this\b',
    r'\bwhat\s+does\s+this\b',
    r'\bsummarize\s+(this|it)\b',
    r'\bexplain\s+(this|it)\b',
    r'\btell\s+me\s+about\s+this\b',
]

# Vague question starters without clear entities
VAGUE_QUESTION_PATTERNS = [
    r'^how\'?s\s+(the\s+)?\w+\s*$',  # "how's the market", "how's stock"
    r'^what\'?s\s+(the\s+)?\w+\s*$',  # "what's this", "what's the news"
    r'^show\s+me\b',
    r'^give\s+me\b',
]

# Specific entities that indicate a focused query (shouldn't auto-fetch)
SPECIFIC_ENTITY_PATTERNS = [
    r'\b[A-Z]{2,5}\b',  # Stock tickers (AAPL, TSLA, etc)
    r'\$[\d,]+',  # Dollar amounts
    r'\b\d+\.?\d*%',  # Percentages
    r'\b(Apple|Microsoft|Google|Amazon|Tesla|Meta|Netflix)\b',  # Major companies
    r'\bP/E\s+ratio\b',
    r'\bmarket\s+cap\b',
    r'\bEPS\b',
    r'\bROI\b',
]

def _has_pattern_match(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the given regex patterns."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def _is_very_short_query(text: str) -> bool:
    """Determine if query is very short (likely vague)."""
    # Remove punctuation and whitespace
    cleaned = re.sub(r'[^\w\s]', '', text).strip()
    word_count = len(cleaned.split())
    return word_count <= 4

def _has_specific_entities(text: str) -> bool:
    """Check if query contains specific financial entities."""
    return _has_pattern_match(text, SPECIFIC_ENTITY_PATTERNS)

def analyze_query_intent(query: str) -> dict:
    """
    Analyze a user query to determine its intent and context needs.
    
    Args:
        query: The user's question/prompt
        
    Returns:
        Dict with analysis results:
        {
            'is_vague': bool,
            'has_contextual_indicators': bool,
            'is_time_sensitive': bool,
            'has_specific_entities': bool,
            'needs_page_context': bool,
            'confidence': float (0-1)
        }
    """
    query_lower = query.lower().strip()
    
    # Analyze different aspects
    is_vague_time = _has_pattern_match(query_lower, VAGUE_TIME_PATTERNS)
    has_contextual = _has_pattern_match(query_lower, CONTEXTUAL_INDICATORS)
    is_vague_question = _has_pattern_match(query_lower, VAGUE_QUESTION_PATTERNS)
    is_short = _is_very_short_query(query)
    has_entities = _has_specific_entities(query)
    
    # Determine if vague overall
    is_vague = (is_vague_question or is_short) and not has_entities
    
    # Calculate confidence score
    confidence = 0.0
    reasons = []
    
    if has_contextual:
        confidence += 0.5
        reasons.append("contextual_indicators")
    
    if is_vague_time:
        confidence += 0.3
        reasons.append("time_sensitive")
    
    if is_vague:
        confidence += 0.3
        reasons.append("vague_query")
    
    # Reduce confidence if specific entities present
    if has_entities:
        confidence *= 0.3
        reasons.append("has_specific_entities (reducing)")
    
    # Normalize confidence to 0-1
    confidence = min(confidence, 1.0)
    
    # Decision: needs page context if confidence > 0.4
    needs_context = confidence > 0.4
    
    logger.debug(
        f"Query intent analysis: query='{query[:50]}...', "
        f"needs_context={needs_context}, confidence={confidence:.2f}, "
        f"reasons={reasons}"
    )
    
    return {
        'is_vague': is_vague,
        'has_contextual_indicators': has_contextual,
        'is_time_sensitive': is_vague_time,
        'has_specific_entities': has_entities,
        'needs_page_context': needs_context,
        'confidence': confidence,
        'reasons': reasons
    }

def should_fetch_page_context(
    query: str,
    current_url: Optional[str],
    mode: str = "thinking"
) -> bool:
    """
    Determine if we should auto-fetch current page content for this query.
    
    Args:
        query: User's question
        current_url: URL of current browser tab
        mode: Interaction mode ("thinking", "research", etc.)
        
    Returns:
        True if we should auto-fetch the current page via Playwright MCP
    """
    # Only auto-fetch in thinking mode with a valid URL
    if mode.lower() != "thinking":
        logger.debug(f"Not fetching - mode is {mode}, not thinking")
        return False
    
    if not current_url or current_url == "about:blank":
        logger.debug("Not fetching - no valid current URL")
        return False
    
    # Analyze the query
    analysis = analyze_query_intent(query)
    
    should_fetch = analysis['needs_page_context']
    
    if should_fetch:
        logger.info(
            f"Will auto-fetch page context: confidence={analysis['confidence']:.2f}, "
            f"reasons={analysis['reasons']}"
        )
    else:
        logger.debug(
            f"Will NOT auto-fetch: confidence={analysis['confidence']:.2f}, "
            f"reasons={analysis['reasons']}"
        )
    
    return should_fetch
