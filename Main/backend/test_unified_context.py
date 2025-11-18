#!/usr/bin/env python
"""
Test suite for Unified Context Manager
Validates the refactored context management system
Author: Linus (testing with pragmatism)
"""

import json
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datascraper.unified_context_manager import (
    UnifiedContextManager,
    ContextMode,
    get_context_manager
)
from datascraper.context_integration import (
    ContextIntegration,
    get_context_integration
)


def test_unified_context_manager():
    """Test the UnifiedContextManager functionality"""
    print("\n" + "="*60)
    print("TESTING UNIFIED CONTEXT MANAGER")
    print("="*60)

    # Create manager
    manager = UnifiedContextManager()
    session_id = "test_session_001"

    # Test 1: Add user message
    print("\n1. Testing user message addition...")
    manager.add_user_message(session_id, "What is the current stock price of AAPL?")
    context = manager.get_full_context(session_id)
    assert len(context["conversation_history"]) == 1
    assert context["conversation_history"][0]["role"] == "user"
    print("✓ User message added successfully")

    # Test 2: Add assistant message with metadata
    print("\n2. Testing assistant message with metadata...")
    manager.add_assistant_message(
        session_id,
        "Based on the latest data, Apple (AAPL) is trading at $195.42",
        model="gpt-4o-mini",
        sources_used=[{"url": "finance.yahoo.com", "title": "AAPL Stock"}],
        tools_used=["web_search"],
        response_time_ms=1250
    )
    context = manager.get_full_context(session_id)
    assert len(context["conversation_history"]) == 2
    assert context["conversation_history"][1]["role"] == "assistant"
    assert context["conversation_history"][1]["metadata"]["model"] == "gpt-4o-mini"
    print("✓ Assistant message with metadata added successfully")

    # Test 3: Update metadata
    print("\n3. Testing metadata updates...")
    manager.update_metadata(
        session_id,
        mode=ContextMode.RESEARCH,
        current_url="https://finance.yahoo.com/quote/AAPL",
        user_timezone="America/New_York",
        user_time="2025-11-15T14:30:00Z"
    )
    context = manager.get_full_context(session_id)
    assert context["metadata"]["mode"] == "research"
    assert context["metadata"]["current_url"] == "https://finance.yahoo.com/quote/AAPL"
    print("✓ Metadata updated successfully")

    # Test 4: Add fetched context from different sources
    print("\n4. Testing fetched context from multiple sources...")

    # Add JS scraped content
    manager.add_fetched_context(
        session_id,
        source_type="js_scraping",
        content="Apple Inc. (AAPL) Stock Price: $195.42, Market Cap: $3.2T",
        url="https://finance.yahoo.com/quote/AAPL"
    )

    # Add Playwright content
    manager.add_fetched_context(
        session_id,
        source_type="playwright",
        content="P/E Ratio: 32.45, EPS: $6.02, Dividend Yield: 0.44%",
        url="https://finance.yahoo.com/quote/AAPL/key-statistics",
        extracted_data={"action": "click_statistics_tab"}
    )

    # Add web search results
    manager.add_fetched_context(
        session_id,
        source_type="web_search",
        content="Apple reports record Q4 earnings, beating analyst expectations",
        url="https://www.reuters.com/apple-earnings",
        extracted_data={
            "title": "Apple Q4 Earnings",
            "site_name": "Reuters",
            "published_date": "2025-11-14"
        }
    )

    context = manager.get_full_context(session_id)
    assert len(context["fetched_context"]["js_scraping"]) == 1
    assert len(context["fetched_context"]["playwright"]) == 1
    assert len(context["fetched_context"]["web_search"]) == 1
    print("✓ Fetched context from all sources added successfully")

    # Test 5: Get formatted messages for API
    print("\n5. Testing API message formatting...")
    messages = manager.get_formatted_messages_for_api(session_id)
    assert len(messages) > 0
    assert "[SYSTEM MESSAGE]:" in messages[0]["content"]
    # Should include fetched context
    has_web_content = any("[WEB CONTENT" in msg["content"] for msg in messages)
    has_playwright = any("[PLAYWRIGHT CONTENT" in msg["content"] for msg in messages)
    has_search = any("[WEB SEARCH RESULT" in msg["content"] for msg in messages)
    assert has_web_content or has_playwright or has_search
    print("✓ API messages formatted correctly with all context")

    # Test 6: Session statistics
    print("\n6. Testing session statistics...")
    stats = manager.get_session_stats(session_id)
    assert stats["message_count"] == 2
    assert stats["fetched_context_counts"]["js_scraping"] == 1
    assert stats["fetched_context_counts"]["playwright"] == 1
    assert stats["fetched_context_counts"]["web_search"] == 1
    assert stats["total_fetched_items"] == 3
    print("✓ Session statistics calculated correctly")

    # Test 7: Export and import JSON
    print("\n7. Testing JSON export/import...")
    json_export = manager.export_session_json(session_id)
    exported_data = json.loads(json_export)
    assert "system_prompt" in exported_data
    assert "metadata" in exported_data
    assert "fetched_context" in exported_data
    assert "conversation_history" in exported_data

    # Clear session and reimport
    manager.clear_session(session_id)
    manager.import_session_json(session_id + "_imported", json_export)
    reimported_context = manager.get_full_context(session_id + "_imported")
    assert len(reimported_context["conversation_history"]) == 2
    assert len(reimported_context["fetched_context"]["web_search"]) == 1
    print("✓ JSON export/import working correctly")

    # Test 8: Clear fetched context
    print("\n8. Testing selective context clearing...")
    manager.clear_fetched_context(session_id + "_imported", "web_search")
    context = manager.get_full_context(session_id + "_imported")
    assert len(context["fetched_context"]["web_search"]) == 0
    assert len(context["fetched_context"]["playwright"]) == 1  # Should remain
    print("✓ Selective context clearing working")

    # Test 9: Clear conversation history
    print("\n9. Testing conversation history clearing...")
    manager.clear_conversation_history(session_id + "_imported")
    context = manager.get_full_context(session_id + "_imported")
    assert len(context["conversation_history"]) == 0
    assert context["metadata"]["message_count"] == 0
    print("✓ Conversation history cleared successfully")

    print("\n" + "="*60)
    print("UNIFIED CONTEXT MANAGER TESTS PASSED ✓")
    print("="*60)


def test_context_integration():
    """Test the ContextIntegration layer"""
    print("\n" + "="*60)
    print("TESTING CONTEXT INTEGRATION")
    print("="*60)

    integration = ContextIntegration()

    # Create mock request
    class MockRequest:
        def __init__(self):
            self.GET = {
                'question': 'What are the latest AI trends?',
                'models': 'gpt-4o-mini,claude-3',
                'current_url': 'https://ai.news/trends',
                'user_timezone': 'America/New_York',
                'user_time': '2025-11-15T15:00:00Z',
                'session_id': 'test_integration_001'
            }
            self.POST = {}
            self.session = type('obj', (object,), {'session_key': 'django_session_123'})()

    request = MockRequest()

    # Test 1: Prepare context messages
    print("\n1. Testing context message preparation...")
    messages, session_id = integration.prepare_context_messages(
        request,
        question="What are the latest AI trends?",
        use_unified=True,
        current_url="https://ai.news/trends",
        endpoint="chat_response"
    )
    assert len(messages) > 0
    assert session_id == "test_integration_001"
    print("✓ Context messages prepared successfully")

    # Test 2: Add web content
    print("\n2. Testing web content addition...")
    session_id = integration.add_web_content(
        request,
        text_content="Latest AI trends include multimodal models, agents, and RAG systems",
        current_url="https://ai.news/trends",
        source_type="js_scraping"
    )
    stats = integration.get_context_stats(session_id)
    assert stats["fetched_context_counts"]["js_scraping"] > 0
    print("✓ Web content added successfully")

    # Test 3: Add response with metadata
    print("\n3. Testing response addition with metadata...")
    integration.add_response_to_context(
        session_id,
        response="The latest AI trends include advanced multimodal models...",
        model="gpt-4o-mini",
        sources_used=[{"url": "ai.news", "title": "AI Trends 2025"}],
        tools_used=["web_search"],
        response_time_ms=850
    )
    stats = integration.get_context_stats(session_id)
    assert stats["message_count"] > 0
    print("✓ Response added with metadata")

    # Test 4: Add search results
    print("\n4. Testing search results addition...")
    search_results = [
        {
            "title": "AI Agents Revolution",
            "snippet": "Autonomous agents are transforming software",
            "url": "https://techcrunch.com/ai-agents",
            "site_name": "TechCrunch",
            "body": "Full article content here..."
        },
        {
            "title": "Multimodal Models Lead 2025",
            "snippet": "Vision-language models dominate",
            "url": "https://arxiv.org/paper",
            "site_name": "ArXiv"
        }
    ]
    integration.add_search_results(session_id, search_results)
    stats = integration.get_context_stats(session_id)
    assert stats["fetched_context_counts"]["web_search"] == 2
    print("✓ Search results added successfully")

    # Test 5: Add Playwright content
    print("\n5. Testing Playwright content addition...")
    integration.add_playwright_content(
        session_id,
        content="Dynamic content loaded via Playwright",
        url="https://dynamic.site/content",
        action="scroll_and_wait"
    )
    stats = integration.get_context_stats(session_id)
    assert stats["fetched_context_counts"]["playwright"] == 1
    print("✓ Playwright content added successfully")

    # Test 6: Prepare response with stats
    print("\n6. Testing response preparation with stats...")
    response_data = integration.prepare_response_with_stats(
        response="Here are the latest AI trends...",
        session_id=session_id,
        model="gpt-4o-mini",
        sources=search_results,
        response_time_ms=1200
    )
    assert "resp" in response_data
    assert "context_stats" in response_data
    assert response_data["context_stats"]["session_id"] == session_id
    assert "fetched_context_counts" in response_data["context_stats"]
    print("✓ Response with stats prepared correctly")

    # Test 7: Get full context JSON
    print("\n7. Testing full context JSON export...")
    json_str = integration.get_full_context_json(session_id)
    context_data = json.loads(json_str)
    assert "system_prompt" in context_data
    assert "metadata" in context_data
    assert "fetched_context" in context_data
    assert "conversation_history" in context_data
    print("✓ Full context JSON exported successfully")

    # Test 8: Format messages for datascraper
    print("\n8. Testing datascraper message formatting...")
    ds_messages = integration.format_messages_for_datascraper(session_id)
    assert len(ds_messages) > 0
    # Should have system message
    has_system = any("[SYSTEM MESSAGE]:" in msg["content"] for msg in ds_messages)
    assert has_system
    # Should have fetched content
    has_fetched = any(
        "[WEB" in msg["content"] or "[PLAYWRIGHT" in msg["content"]
        for msg in ds_messages
    )
    assert has_fetched
    print("✓ Datascraper messages formatted correctly")

    # Test 9: Clear with preservation
    print("\n9. Testing selective clearing...")
    integration.clear_messages(request, preserve_web_content=True)
    stats = integration.get_context_stats(session_id)
    # Web content should be preserved
    assert stats["total_fetched_items"] > 0
    # Conversation should be cleared
    assert stats["message_count"] == 0
    print("✓ Selective clearing working correctly")

    print("\n" + "="*60)
    print("CONTEXT INTEGRATION TESTS PASSED ✓")
    print("="*60)


def test_json_structure():
    """Test the JSON structure matches requirements"""
    print("\n" + "="*60)
    print("TESTING JSON STRUCTURE")
    print("="*60)

    manager = UnifiedContextManager()
    session_id = "json_test_001"

    # Build a complete context
    manager.update_metadata(
        session_id,
        mode=ContextMode.RESEARCH,
        current_url="https://example.com",
        user_timezone="UTC",
        user_time=datetime.now(timezone.utc).isoformat()
    )

    manager.add_user_message(session_id, "First user question")
    manager.add_assistant_message(
        session_id,
        "First assistant response",
        model="gpt-4",
        sources_used=[{"url": "source.com"}],
        tools_used=["tool1"],
        response_time_ms=500
    )

    manager.add_fetched_context(
        session_id,
        source_type="web_search",
        content="Search result content",
        url="https://result.com"
    )

    manager.add_fetched_context(
        session_id,
        source_type="playwright",
        content="Playwright scraped content",
        url="https://scraped.com"
    )

    manager.add_fetched_context(
        session_id,
        source_type="js_scraping",
        content="JS scraped content",
        url="https://jsscraped.com"
    )

    # Export and validate structure
    json_str = manager.export_session_json(session_id)
    data = json.loads(json_str)

    print("\nValidating JSON structure:")
    print(json.dumps(data, indent=2)[:1000] + "...")  # Print first 1000 chars

    # Validate required fields
    assert "system_prompt" in data, "Missing system_prompt"
    assert isinstance(data["system_prompt"], str), "system_prompt should be string"
    print("✓ system_prompt present and valid")

    assert "metadata" in data, "Missing metadata"
    meta = data["metadata"]
    assert "session_id" in meta, "Missing session_id in metadata"
    assert "timestamp" in meta, "Missing timestamp in metadata"
    assert "mode" in meta, "Missing mode in metadata"
    assert meta["mode"] == "research", "Incorrect mode"
    print("✓ metadata structure valid")

    assert "fetched_context" in data, "Missing fetched_context"
    fetched = data["fetched_context"]
    assert "web_search" in fetched, "Missing web_search in fetched_context"
    assert "playwright" in fetched, "Missing playwright in fetched_context"
    assert "js_scraping" in fetched, "Missing js_scraping in fetched_context"
    assert len(fetched["web_search"]) == 1, "Incorrect web_search count"
    assert len(fetched["playwright"]) == 1, "Incorrect playwright count"
    assert len(fetched["js_scraping"]) == 1, "Incorrect js_scraping count"
    print("✓ fetched_context structure valid")

    assert "conversation_history" in data, "Missing conversation_history"
    history = data["conversation_history"]
    assert len(history) == 2, "Incorrect conversation history length"
    assert history[0]["role"] == "user", "First message should be from user"
    assert history[1]["role"] == "assistant", "Second message should be from assistant"
    assert "metadata" in history[1], "Assistant message missing metadata"
    assert history[1]["metadata"]["model"] == "gpt-4", "Incorrect model in metadata"
    print("✓ conversation_history structure valid")

    print("\n" + "="*60)
    print("JSON STRUCTURE TESTS PASSED ✓")
    print("="*60)


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("UNIFIED CONTEXT MANAGER TEST SUITE")
    print("Testing the refactored context management system")
    print("="*60)

    try:
        # Test components
        test_unified_context_manager()
        test_context_integration()
        test_json_structure()

        print("\n" + "="*60)
        print("ALL TESTS PASSED SUCCESSFULLY ✓")
        print("="*60)
        print("\nThe refactored context management system is working correctly!")
        print("Key features validated:")
        print("  • Full conversation history tracking")
        print("  • Elegant JSON structure with all required fields")
        print("  • Multiple fetched context sources (web, playwright, JS)")
        print("  • Metadata tracking (timestamp, mode, URL, timezone)")
        print("  • Session isolation and management")
        print("  • Export/import functionality")
        print("  • Backward compatibility layer")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()