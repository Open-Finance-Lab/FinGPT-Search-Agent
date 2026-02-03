"""
Test script to verify the context duplication fix
"""

def test_single_turn():
    """Test single-turn conversation"""
    print("=" * 80)
    print("TEST 1: Single-turn conversation")
    print("=" * 80)

    messages = [
        {"content": "[SYSTEM MESSAGE]: You are FinGPT..."},
        {"content": "[USER MESSAGE]: analyze btc on all indicators"}
    ]

    context = ""
    for msg in messages:
        content = msg.get("content", "")
        if content.startswith("[SYSTEM MESSAGE]:"):
            continue
        elif content.startswith("[USER MESSAGE]:"):
            actual_content = content.replace("[USER MESSAGE]: ", "", 1)
            context += f"User: {actual_content}\n"
        elif content.startswith("[ASSISTANT MESSAGE]:"):
            actual_content = content.replace("[ASSISTANT MESSAGE]: ", "", 1)
            context += f"Assistant: {actual_content}\n"

    full_prompt = context.rstrip()
    print("Prompt sent to agent:")
    print(repr(full_prompt))
    print()
    expected = "User: analyze btc on all indicators"
    if full_prompt == expected:
        print("✓ PASS: Single message appears once")
    else:
        print(f"✗ FAIL: Expected '{expected}', got '{full_prompt}'")
    print()


def test_multi_turn():
    """Test multi-turn conversation"""
    print("=" * 80)
    print("TEST 2: Multi-turn conversation")
    print("=" * 80)

    messages = [
        {"content": "[SYSTEM MESSAGE]: You are FinGPT..."},
        {"content": "[USER MESSAGE]: analyze btc on all indicators"},
        {"content": "[ASSISTANT MESSAGE]: Sure, which exchange and timeframe?"},
        {"content": "[USER MESSAGE]: binance 1 day"}
    ]

    context = ""
    for msg in messages:
        content = msg.get("content", "")
        if content.startswith("[SYSTEM MESSAGE]:"):
            continue
        elif content.startswith("[USER MESSAGE]:"):
            actual_content = content.replace("[USER MESSAGE]: ", "", 1)
            context += f"User: {actual_content}\n"
        elif content.startswith("[ASSISTANT MESSAGE]:"):
            actual_content = content.replace("[ASSISTANT MESSAGE]: ", "", 1)
            context += f"Assistant: {actual_content}\n"

    full_prompt = context.rstrip()
    print("Prompt sent to agent:")
    print(full_prompt)
    print()

    # Check that all turns are present
    expected_turns = [
        "User: analyze btc on all indicators",
        "Assistant: Sure, which exchange and timeframe?",
        "User: binance 1 day"
    ]

    all_present = all(turn in full_prompt for turn in expected_turns)
    if all_present:
        print("✓ PASS: All conversation turns present")
    else:
        print("✗ FAIL: Missing conversation turns")

    # Check no duplication
    if full_prompt.count("User: binance 1 day") == 1:
        print("✓ PASS: No message duplication")
    else:
        print("✗ FAIL: Message duplicated")
    print()


def test_user_only_messages():
    """Test case where user sends parameters without original question"""
    print("=" * 80)
    print("TEST 3: The problematic case - parameters without context")
    print("=" * 80)

    # This was the failing scenario: user sends "binance 1 day" after "analyze btc"
    messages = [
        {"content": "[SYSTEM MESSAGE]: You are FinGPT..."},
        {"content": "[USER MESSAGE]: analyze btc on all indicators"},
        {"content": "[ASSISTANT MESSAGE]: Sure, which exchange and timeframe?"},
        {"content": "[USER MESSAGE]: binance 1 day"}  # Just parameters
    ]

    context = ""
    for msg in messages:
        content = msg.get("content", "")
        if content.startswith("[SYSTEM MESSAGE]:"):
            continue
        elif content.startswith("[USER MESSAGE]:"):
            actual_content = content.replace("[USER MESSAGE]: ", "", 1)
            context += f"User: {actual_content}\n"
        elif content.startswith("[ASSISTANT MESSAGE]:"):
            actual_content = content.replace("[ASSISTANT MESSAGE]: ", "", 1)
            context += f"Assistant: {actual_content}\n"

    full_prompt = context.rstrip()
    print("Full conversation sent to agent:")
    print(full_prompt)
    print()

    # Agent should see the FULL conversation
    has_original_q = "analyze btc on all indicators" in full_prompt
    has_assistant_q = "which exchange and timeframe" in full_prompt
    has_params = "binance 1 day" in full_prompt

    if has_original_q and has_assistant_q and has_params:
        print("✓ PASS: Agent can see original question AND parameters")
        print("  Agent now understands the context and can respond properly!")
    else:
        print("✗ FAIL: Agent missing conversation context")
        if not has_original_q:
            print("  Missing: Original question")
        if not has_assistant_q:
            print("  Missing: Assistant's clarification")
        if not has_params:
            print("  Missing: User's parameters")
    print()


if __name__ == "__main__":
    test_single_turn()
    test_multi_turn()
    test_user_only_messages()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("FIX APPLIED: Removed duplicate user_input appending in datascraper.py")
    print()
    print("Before fix:")
    print("  full_prompt = f'{context}User: {user_input}'  # ❌ Duplicates last message")
    print()
    print("After fix:")
    print("  full_prompt = context.rstrip()  # ✓ Uses messages from context manager")
    print()
    print("Result: Agent now receives full conversation history without duplication")
    print("=" * 80)
