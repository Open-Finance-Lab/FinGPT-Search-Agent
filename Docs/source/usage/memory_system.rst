Memory and Context System
=========================

FinGPT Search Agent employs a sophisticated memory system to handle complex, long-running financial research sessions.

The memory management is handled by the ``Mem0ContextManager`` class in ``Main/backend/datascraper/mem0_context_manager.py``. It uses an LLM-based summarization approach to ensure that the most relevant financial context is always available to the model.

Mem0 Integration
----------------

We use **Mem0** as our production-grade memory layer. Unlike traditional context windows that "forget" older messages, Mem0 allows the agent to maintain a long-term understanding of your objectives.

Smart Compression
-----------------

When a conversation exceeds **100,000 tokens** (approximately 75,000 words), the system triggers **Smart Compression**:

1. **Fact Extraction**: The agent identifies critical pieces of information—financial figures, company names, specific research goals, and important URLs.
2. **Boilerplate Removal**: Redundant text, UI navigation artifacts, and failed search attempts are discarded.
3. **Memory Storage**: Extracted facts are stored in a vectorized memory database.
4. **Context Restoration**: Relevant memories are automatically re-injected into the context when they pertain to your current query.

Session Isolation
-----------------

- **Tab Isolation**: Each browser tab maintains its own unique session.
- **Privacy**: Context is isolated per session and is not shared across different users or tabs unless explicitly configured.
- **Manual Clearing**: Use the **Clear** button to reset the current session's conversation history while optionally preserving scraped web content.
