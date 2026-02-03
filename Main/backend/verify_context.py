"""
Diagnostic script to verify conversation context flow
Run this to trace the message duplication issue
"""

def simulate_conversation_flow():
    """Simulate the exact flow from user question to agent prompt"""

    # Step 1: User asks a question
    user_question = "analyze btc on all indicators"
    print("=" * 80)
    print("STEP 1: User question")
    print(f"Question: '{user_question}'")
    print()

    # Step 2: views.py adds user message to context manager
    print("=" * 80)
    print("STEP 2: views.py calls context_mgr.add_user_message()")
    messages_from_context = [
        {"content": "[SYSTEM MESSAGE]: You are FinGPT..."},
        {"content": "[USER MESSAGE]: analyze btc on all indicators"}  # Added by context manager
    ]
    print(f"Messages from get_formatted_messages_for_api():")
    for i, msg in enumerate(messages_from_context):
        print(f"  [{i}] {msg['content'][:80]}...")
    print()

    # Step 3: datascraper._create_agent_response_async receives messages
    print("=" * 80)
    print("STEP 3: datascraper._create_agent_response_async()")
    print(f"  user_input parameter: '{user_question}'")
    print(f"  message_list parameter: (from context manager)")
    for i, msg in enumerate(messages_from_context):
        print(f"    [{i}] {msg['content'][:80]}...")
    print()

    # Step 4: datascraper builds context from message_list
    print("=" * 80)
    print("STEP 4: datascraper builds context string (lines 712-736)")
    context = ""
    for msg in messages_from_context:
        content = msg.get("content", "")
        if content.startswith("[SYSTEM MESSAGE]:"):
            print(f"  Extracting system prompt: '{content[:50]}...'")
            continue
        elif content.startswith("[USER MESSAGE]:"):
            actual_content = content.replace("[USER MESSAGE]: ", "", 1)
            context += f"User: {actual_content}\n"
            print(f"  Adding to context: 'User: {actual_content}'")
        elif content.startswith("[ASSISTANT MESSAGE]:"):
            actual_content = content.replace("[ASSISTANT MESSAGE]: ", "", 1)
            context += f"Assistant: {actual_content}\n"
            print(f"  Adding to context: 'Assistant: {actual_content}'")
    print(f"\nContext string so far:\n{context}")
    print()

    # Step 5: datascraper appends user_input AGAIN (line 738)
    print("=" * 80)
    print("STEP 5: datascraper appends user_input to context (line 738)")
    full_prompt = f"{context}User: {user_question}"
    print(f"full_prompt = f\"{{context}}User: {{user_input}}\"")
    print(f"\nFINAL PROMPT SENT TO AGENT:")
    print(full_prompt)
    print()

    # Analysis
    print("=" * 80)
    print("ANALYSIS: MESSAGE DUPLICATION DETECTED")
    print()
    print("The user message appears TWICE:")
    print("  1. In message_list (line ~728): 'User: analyze btc on all indicators'")
    print("  2. In full_prompt (line 738):   'User: analyze btc on all indicators'")
    print()
    print("Why this happens:")
    print("  - views.py calls add_user_message() which adds to conversation_history")
    print("  - get_formatted_messages_for_api() includes this in returned messages")
    print("  - datascraper extracts it into context variable (lines 726-736)")
    print("  - Then datascraper ALSO appends user_input again (line 738)")
    print()
    print("RESULT: Agent sees the question twice, loses previous context")
    print("=" * 80)

if __name__ == "__main__":
    simulate_conversation_flow()
