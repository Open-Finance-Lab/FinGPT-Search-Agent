# backend/mcp_client/query_intent_analyzer.py

"""
Query Intent Analyzer for Smart MCP Context Fetching

This module analyzes user queries to determine if they would benefit from
automatic fetching of the current page content via Playwright MCP.

Philosophy:
- If the user is on a valid page, they likely want to ask about it.
- We default to fetching context unless there is a clear signal NOT to (e.g. navigation).
- "Good taste" means eliminating edge cases by making the common case (contextual) the default.
"""

import re
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Patterns that indicate the user explicitly wants to IGNORE the current page
IGNORE_CONTEXT_PATTERNS = [
    r'^ignore\s+(?:this\s+)?(?:page|site|context)\b',
    r'^don\'?t\s+use\s+(?:this\s+)?(?:page|site|context)\b',
]

# Patterns that indicate the user explicitly wants to go somewhere else
NAVIGATION_INTENT_PATTERNS = [
    r'^(?:please\s+)?(?:navigate|go)\s+to\b',
    r'^(?:please\s+)?open\s+(?:url|website|page)\b',
    r'^(?:please\s+)?search\s+(?:for|google|bing|web)\b',
    r'^(?:please\s+)?google\b',
]

# Patterns that strongly suggest we MUST have the context (overrides navigation checks if ambiguous)
CONTEXT_REQUIRED_PATTERNS = [
    r'\bthis\s+(?:page|site|website|article)\b',
    r'\bhere\b',
    r'\bon\s+this\b',
    r'\bsummarize\b',
    r'\bexplain\b',
    r'\bread\b',
    r'\banalyze\b',
    r'\bwhat\s+is\s+this\b',
]

def _has_pattern_match(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the given regex patterns."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def analyze_query_intent(query: str) -> Dict[str, Any]:
    """
    Analyze a user query to determine its intent and context needs.
    
    Args:
        query: The user's question/prompt
        
    Returns:
        Dict with analysis results
    """
    query_lower = query.lower().strip()
    
    # 1. Check for explicit IGNORE intent (highest priority)
    if _has_pattern_match(query_lower, IGNORE_CONTEXT_PATTERNS):
        logger.debug(f"Query '{query[:50]}...' matched IGNORE pattern")
        return {
            'is_vague': False,
            'has_contextual_indicators': False,
            'is_time_sensitive': False,
            'has_specific_entities': False,
            'needs_page_context': False,
            'confidence': 1.0,
            'reasons': ["explicit_ignore"]
        }
    
    # 2. Check for explicit navigation/search intent
    has_navigation_intent = _has_pattern_match(query_lower, NAVIGATION_INTENT_PATTERNS)
    
    # 3. Check for explicit context markers
    has_context_markers = _has_pattern_match(query_lower, CONTEXT_REQUIRED_PATTERNS)
    
    # 4. Determine if we need context
    # Default: YES, unless we are navigating away AND don't have explicit "this page" markers.
    needs_page_context = True
    
    if has_navigation_intent and not has_context_markers:
        needs_page_context = False
        
    # Confidence is high by default in this new model
    confidence = 0.9 if needs_page_context else 0.9
    
    reasons = []
    if has_context_markers:
        reasons.append("explicit_context_markers")
    if has_navigation_intent:
        reasons.append("navigation_intent")
    if needs_page_context and not has_context_markers:
        reasons.append("default_context_assumption")

    logger.debug(
        f"Query intent analysis: query='{query[:50]}...', "
        f"needs_context={needs_page_context}, reasons={reasons}"
    )
    
    return {
        'is_vague': False,
        'has_contextual_indicators': has_context_markers,
        'is_time_sensitive': False,
        'has_specific_entities': False,
        'needs_page_context': needs_page_context,
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
    # 1. Basic Validity Checks
    if not current_url or current_url == "about:blank":
        logger.debug("Not fetching - no valid current URL")
        return False
        
    # 2. Mode Check
    if mode.lower() not in ["thinking", "normal", "agent"]:
        pass

    # 3. Analyze Query
    analysis = analyze_query_intent(query)
    
    should_fetch = analysis['needs_page_context']
    
    if should_fetch:
        logger.info(
            f"Will auto-fetch page context: {current_url} "
            f"(Reasons: {analysis['reasons']})"
        )
    
    return should_fetch
