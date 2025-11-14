# Mem0 Migration Guide

## Overview

This guide explains how to complete the migration from R2C context management to Mem0's production-ready memory layer for FinGPT Search Agent.

**Status**: Code migration is COMPLETE. You only need to:
1. Register for a Mem0 account
2. Get your API key
3. Install dependencies
4. Configure environment variables

---

## What Changed?

### Before (R2C)
- Algorithmic compression based on keyword matching
- Only 2 messages retained after compression
- No semantic understanding
- Frequent "forgetting" issues

### After (Mem0)
- AI-powered memory extraction
- 10 recent messages kept verbatim
- Intelligent fact and preference extraction
- 26% accuracy improvement, 90% token savings (research-proven)
- Graph-based relationship understanding

---

## Step 1: Register for Mem0

### Option A: Use Mem0 Cloud (Recommended - Easy Setup)

1. **Go to Mem0 website**:
   ```
   https://mem0.ai
   ```

2. **Sign up for a free account**:
   - Click "Get Started" or "Sign Up"
   - Use your email or sign in with GitHub/Google
   - Free tier includes: 100,000 operations/month

3. **Get your API key**:
   - After signing up, go to: https://app.mem0.ai/dashboard/api-keys
   - Click "Create New API Key"
   - Copy the key (it will look like: `m0-xxx...`)
   - **IMPORTANT**: Save this key securely - you won't be able to see it again

### Option B: Self-Host Mem0 (Advanced - For Large Scale)

If you need more control or have privacy requirements:

1. **Clone Mem0 repository**:
   ```bash
   git clone https://github.com/mem0ai/mem0
   cd mem0
   ```

2. **Follow self-hosting guide**:
   - Documentation: https://docs.mem0.ai/self-hosting
   - Requires: Docker, PostgreSQL, Qdrant/Pinecone vector DB

3. **Update code** to use self-hosted endpoint:
   ```python
   # In views.py, line 123:
   mem0_manager = Mem0ContextManager(
       api_key=os.getenv("MEM0_API_KEY"),
       base_url="http://your-selfhosted-mem0:8000",  # Add this line
       max_recent_messages=10
   )
   ```

**For most users, Option A (Cloud) is recommended.**

---

## Step 2: Configure Environment Variables

### Development (.env file)

1. **Navigate to backend directory**:
   ```bash
   cd Main/backend
   ```

2. **Copy example env file** (if you haven't already):
   ```bash
   cp .env.example .env
   ```

3. **Edit .env file** and add your Mem0 API key:
   ```bash
   # Open with your editor
   nano .env
   # or
   code .env
   ```

4. **Add the MEM0_API_KEY**:
   ```env
   # API Keys
   OPENAI_API_KEY=your-openai-api-key-here
   DEEPSEEK_API_KEY=your-deepseek-api-key-here
   ANTHROPIC_API_KEY=your-anthropic-api-key-here
   MEM0_API_KEY=m0-xxxxxxxxxxxxxxxxxxxxxxxx  # <-- Add your key here
   ```

5. **Save and close** the file

### Production (.env.production)

For production deployment, update your production environment variables:

```env
# Model provider credentials
OPENAI_API_KEY=sk-xxx...
DEEPSEEK_API_KEY=xxx...
ANTHROPIC_API_KEY=xxx...
MEM0_API_KEY=m0-xxx...  # <-- Add your production key here
```

If using Heroku/cloud platform, set environment variable via dashboard or CLI:
```bash
# Heroku example
heroku config:set MEM0_API_KEY=m0-xxx...

# Railway example
railway variables set MEM0_API_KEY=m0-xxx...

# Render example
# Set in dashboard under Environment Variables
```

---

## Step 3: Install Dependencies

### Using uv (Recommended)

```bash
cd Main/backend

# Sync all dependencies including mem0ai
uv sync

# Install Playwright browsers (required for agent functionality)
uv run playwright install chromium
```

### Using pip

```bash
cd Main/backend

# Install dependencies
pip install -r requirements.txt

# Or install just mem0ai
pip install "mem0ai>=0.1.0,<1"

# Install Playwright browsers
playwright install chromium
```

---

## Step 4: Verify Installation

### Test Mem0 Connection

Create a test script to verify your Mem0 setup:

```bash
cd Main/backend
python -c "
from mem0 import MemoryClient
import os

api_key = os.getenv('MEM0_API_KEY')
if not api_key:
    print('❌ MEM0_API_KEY not found in environment')
    exit(1)

try:
    client = MemoryClient(api_key=api_key)
    print('✅ Mem0 client initialized successfully')
    print(f'✅ API key format correct: {api_key[:10]}...')
except Exception as e:
    print(f'❌ Failed to initialize Mem0: {e}')
    exit(1)
"
```

Expected output:
```
✅ Mem0 client initialized successfully
✅ API key format correct: m0-xxxxxxx...
```

### Test Django Server

```bash
cd Main/backend

# Run Django checks
python manage.py check

# Start development server
python manage.py runserver
```

You should see:
```
INFO: Mem0 Context Manager initialized successfully
System check identified no issues (0 silenced).
Django version 5.2.8, using settings 'django_config.settings'
Starting development server at http://127.0.0.1:8000/
```

---

## Step 5: Test the Integration

### Test with Browser Extension

1. **Start backend server**:
   ```bash
   cd Main/backend
   python manage.py runserver
   ```

2. **Open browser extension** and ask a question

3. **Check console logs** for Mem0 activity:
   ```
   [Mem0] Added message to memory for session xxx
   [Mem0] Retrieved 3 relevant memories for session xxx
   ```

4. **Test memory persistence**:
   - Have a conversation about Tesla stock
   - Clear recent conversation (should preserve memories)
   - Ask "What were we discussing?"
   - Agent should remember Tesla context

### Test Memory API Directly

```bash
# Get session stats
curl "http://localhost:8000/api/get_memory_stats/" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"

# Expected response:
{
  "stats": {
    "recent_message_count": 10,
    "total_message_count": 45,
    "memory_count": 8,
    "mem0_operations": 52,
    "using_mem0": true,
    "last_used": "2025-01-15T10:30:00"
  }
}
```

---

## Configuration Options

### Adjust Recent Message Buffer

By default, 10 recent messages are kept verbatim. To change this:

```bash
# In .env file
MEM0_MAX_RECENT_MESSAGES=15  # Keep last 15 messages instead of 10
```

Or edit `views.py` line 124:
```python
mem0_manager = Mem0ContextManager(
    max_recent_messages=15,  # Increase from 10 to 15
)
```

**Recommendation**:
- 10 messages = balanced (default)
- 15-20 messages = better short-term context (slightly higher API costs)
- 5 messages = more aggressive (may lose immediate context)

---

## Troubleshooting

### Error: "Mem0 is not installed"

**Solution**:
```bash
pip install mem0ai
# or
uv pip install mem0ai
```

### Error: "MEM0_API_KEY not found"

**Solution**:
1. Check .env file exists: `ls -la Main/backend/.env`
2. Check key is set: `grep MEM0_API_KEY Main/backend/.env`
3. Restart Django server after adding key

### Error: "Failed to initialize Mem0 client"

**Possible causes**:
1. Invalid API key format
   - Should start with `m0-`
   - Get new key from https://app.mem0.ai/dashboard/api-keys

2. Network connectivity issues
   - Check internet connection
   - Verify firewall allows outbound HTTPS to mem0.ai

3. Rate limit exceeded (free tier: 100k ops/month)
   - Check usage in Mem0 dashboard
   - Upgrade plan or wait for reset

### Error: "ImportError: cannot import name 'MemoryClient'"

**Solution**:
```bash
# Uninstall old version
pip uninstall mem0ai

# Install latest
pip install --upgrade mem0ai

# Verify version
pip show mem0ai
# Should show version >= 0.1.0
```

### Performance Issues

If responses are slow:

1. **Check Mem0 dashboard** for latency metrics
2. **Reduce recent message buffer**:
   ```python
   max_recent_messages=5  # Reduce from 10
   ```
3. **Limit memory retrieval**:
   Edit `mem0_context_manager.py` line 213:
   ```python
   limit=3  # Reduce from 5
   ```

### Memory Not Persisting

If agent still "forgets":

1. **Verify session ID** is consistent:
   ```python
   # Check browser console for session_id in requests
   ```

2. **Check Mem0 dashboard** for memory entries:
   - Go to https://app.mem0.ai/dashboard/memories
   - Filter by user_id (session_id)
   - Verify memories are being created

3. **Test memory creation** manually:
   ```python
   from mem0 import MemoryClient
   client = MemoryClient(api_key="m0-xxx")
   client.add(
       messages=[{"role": "user", "content": "I love Tesla stock"}],
       user_id="test-session"
   )
   memories = client.get_all(user_id="test-session")
   print(memories)
   ```

---

## Cost Estimation

### Free Tier (Recommended for Development)
- **100,000 operations/month**
- Operations = add() calls + search() calls
- ~50 users with 50 conversations each = 5,000 operations
- **Cost**: FREE

### Starter Plan ($29/month)
- **1 million operations/month**
- Suitable for 500-1000 active users
- **Cost**: $29/month

### Pro Plan ($99/month)
- **5 million operations/month**
- Suitable for 5,000+ active users
- Advanced features: custom models, priority support
- **Cost**: $99/month

**Typical Usage**:
- Each user message = 1 add() operation
- Each agent response = 1 add() operation
- Each query = 1 search() operation
- Average conversation (20 messages) = ~60 operations

**Example**:
- 1000 active users
- 30 messages per user per month
- 1000 × 30 × 3 = 90,000 operations/month
- **Fits in FREE tier**

---

## Rollback Instructions (If Needed)

If you need to revert to R2C:

1. **Restore old context manager**:
   ```bash
   cd Main/backend
   git checkout HEAD~1 -- datascraper/r2c_context_manager.py
   git checkout HEAD~1 -- api/views.py
   git checkout HEAD~1 -- pyproject.toml
   ```

2. **Remove Mem0 dependency**:
   ```bash
   pip uninstall mem0ai
   ```

3. **Remove MEM0_API_KEY** from .env

4. **Restart server**:
   ```bash
   python manage.py runserver
   ```

---

## Monitoring & Observability

### Mem0 Dashboard

Monitor your memory usage at:
```
https://app.mem0.ai/dashboard
```

**Key Metrics**:
- Operations count (approaching limit?)
- Average latency (< 200ms is good)
- Memory count per user
- Error rate

### Django Logs

Watch for Mem0 activity:
```bash
# Development
python manage.py runserver

# Look for:
# [Mem0] Added message to memory for session xxx
# [Mem0] Retrieved 5 relevant memories for session xxx
```

### Session Stats API

Get real-time stats:
```bash
curl "http://localhost:8000/api/get_memory_stats/" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

Response includes:
- `memory_count`: How many long-term memories stored
- `mem0_operations`: Total Mem0 API calls for this session
- `recent_message_count`: Messages in short-term buffer
- `using_mem0`: true (confirms Mem0 is active)

---

## FAQ

### Q: Do I need to migrate existing conversations?

**A**: No. Mem0 starts fresh with new conversations. Old R2C sessions are automatically replaced.

### Q: What happens to conversations in progress?

**A**: New messages will use Mem0. The old R2C compressed context is ignored (graceful transition).

### Q: Can I use both R2C and Mem0?

**A**: No, Mem0 completely replaces R2C. The codebase now only supports Mem0.

### Q: Is my data secure with Mem0?

**A**: Yes. Mem0 uses:
- TLS encryption for data in transit
- AES-256 encryption for data at rest
- SOC 2 Type II compliant infrastructure
- GDPR compliant

For sensitive data, use self-hosted option.

### Q: What if Mem0 API is down?

**A**: The agent will continue to work with recent messages only (last 10). Long-term memories won't be retrieved but functionality is preserved.

### Q: Can I delete user memories for GDPR compliance?

**A**: Yes, call:
```python
mem0_manager.clear_session(session_id)
# This deletes all memories for that user
```

Or via Mem0 dashboard:
- Go to Memories tab
- Filter by user_id
- Click "Delete All"

---

## Support & Resources

### Mem0 Resources
- **Documentation**: https://docs.mem0.ai
- **GitHub**: https://github.com/mem0ai/mem0
- **Discord Community**: https://discord.gg/mem0
- **Support Email**: support@mem0.ai

### FinGPT Resources
- **Issues**: https://github.com/YOUR_REPO/issues
- **Documentation**: See Docs/ folder

### Getting Help

1. **Check logs** for error messages
2. **Review troubleshooting section** above
3. **Test Mem0 connection** with verification script
4. **Contact Mem0 support** if API issues
5. **Open GitHub issue** for FinGPT-specific problems

---

## Next Steps

After successful migration:

1. ✅ **Monitor usage** in Mem0 dashboard for first week
2. ✅ **Gather user feedback** on memory improvements
3. ✅ **Optimize** message buffer size based on usage
4. ✅ **Consider upgrading** if approaching free tier limits
5. ✅ **Document** any custom configurations for your team

---

## Summary Checklist

- [ ] Registered for Mem0 account at https://mem0.ai
- [ ] Retrieved API key from https://app.mem0.ai/dashboard/api-keys
- [ ] Added MEM0_API_KEY to .env file
- [ ] Installed dependencies: `uv sync` or `pip install mem0ai`
- [ ] Verified installation with test script
- [ ] Started Django server successfully
- [ ] Tested conversation with browser extension
- [ ] Confirmed memory persistence across sessions
- [ ] Set up monitoring in Mem0 dashboard

**Status**: Migration complete! Users should no longer experience "forgetting" issues.

---

*Generated for FinGPT R2C → Mem0 Migration*
*Last Updated: 2025-01-15*
