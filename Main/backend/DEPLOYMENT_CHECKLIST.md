# Unified Context Manager - Deployment Checklist

## Pre-Deployment Verification ✓

### Files Created/Modified
- ✓ `datascraper/unified_context_manager.py` - Core context management
- ✓ `datascraper/context_integration.py` - API integration layer
- ✓ `datascraper/datascraper_refactored.py` - Refactored response generation
- ✓ `api/views.py` - **REPLACED** with unified context manager integration
- ✓ `api/views_backup.py` - Backup of original views.py
- ✓ `api/views_complete.py` - Source for new views.py
- ✓ `api/views_refactored.py` - Alternative endpoint implementation
- ✓ `test_unified_context.py` - Comprehensive test suite
- ✓ `UNIFIED_CONTEXT_DOCUMENTATION.md` - Complete documentation
- ✓ `ENDPOINT_VERIFICATION.md` - Endpoint mapping verification
- ✓ `DEPLOYMENT_CHECKLIST.md` - This file

### Code Verification
- ✓ All 15 API endpoints mapped and implemented
- ✓ All function signatures verified compatible
- ✓ Python syntax validated (no compilation errors)
- ✓ All imports present and correct
- ✓ Helper functions ported (_get_session_id, _log_interaction, etc.)
- ✓ Datascraper dependencies verified (create_agent_response, create_advanced_response, etc.)

### Test Results
- ✓ UnifiedContextManager tests: ALL PASSED
- ✓ ContextIntegration tests: ALL PASSED
- ✓ JSON structure tests: ALL PASSED

## Deployment Steps

### 1. Review Changes
```bash
# View what was changed in views.py
diff api/views_backup.py api/views.py | head -100
```

### 2. Build Docker Images
```bash
# From repository root
docker-compose build
```

### 3. Start Services
```bash
# Start all services
docker-compose up -d

# Or start backend only for testing
docker-compose up backend
```

### 4. Verify Health Endpoint
```bash
# Check if backend is healthy
curl http://localhost:8000/health/

# Expected response should include:
# {
#   "status": "healthy",
#   "service": "fingpt-backend",
#   "timestamp": "...",
#   "version": "...",
#   "using_unified_context": true
# }
```

### 5. Test Core Endpoints

#### Test Normal Chat Mode
```bash
curl "http://localhost:8000/get_chat_response/?question=What%20is%20Apple%27s%20stock%20price%3F&models=gpt-4o-mini&current_url=https://finance.yahoo.com/quote/AAPL"

# Should return:
# {
#   "resp": {"gpt-4o-mini": "...response..."},
#   "context_stats": {
#     "session_id": "...",
#     "mode": "thinking",
#     "message_count": 2,
#     "token_count": ...,
#     "fetched_context": {...}
#   }
# }
```

#### Test Advanced Search Mode
```bash
curl "http://localhost:8000/get_adv_response/?question=Latest%20AI%20news&models=gpt-4o-mini"

# Should return:
# {
#   "resp": {"gpt-4o-mini": "...response..."},
#   "used_sources": [...],
#   "context_stats": {
#     "mode": "research",
#     ...
#   }
# }
```

#### Test Context Stats
```bash
curl "http://localhost:8000/api/get_memory_stats/"

# Should return:
# {
#   "stats": {
#     "session_id": "...",
#     "mode": "...",
#     "message_count": ...,
#     "token_count": ...",
#     "using_unified_context": true
#   }
# }
```

#### Test Web Content Addition
```bash
curl -X POST http://localhost:8000/input_webtext/ \
  -H "Content-Type: application/json" \
  -d '{"textContent": "Test page content", "currentUrl": "https://example.com"}'

# Should return:
# {
#   "status": "success",
#   "session_id": "...",
#   "context_stats": {
#     "js_scraping_count": 1,
#     ...
#   }
# }
```

#### Test Context Clearing
```bash
curl -X POST "http://localhost:8000/clear_messages/?preserve_web=true"

# Should return:
# {
#   "status": "success",
#   "session_id": "...",
#   "preserved_web_content": true
# }
```

### 6. Test Frontend Integration

1. Load the browser extension
2. Navigate to a financial website (e.g., finance.yahoo.com)
3. Ask a question in normal mode
4. Verify:
   - Response received correctly
   - Follow-up questions work (full conversation history)
   - Context stats appear if enabled
   - Web content scraped and used

5. Test advanced mode:
   - Ask a question requiring web search
   - Verify sources are cited
   - Check that context carries over between questions

## Monitoring

### Check Logs
```bash
# View backend logs
docker-compose logs -f backend

# Look for:
# - "UnifiedContextManager initialized"
# - "Created new session: ..."
# - "Added user message to session..."
# - "Added assistant message to session..."
# - No import errors or exceptions
```

### Performance Metrics
- Response times should be comparable to before
- Memory usage should be stable
- No memory leaks over extended use

## Rollback Procedure

If issues occur:

### Quick Rollback (5 minutes)
```bash
# 1. Stop services
docker-compose down

# 2. Restore original views.py
cd Main/backend
cp api/views_backup.py api/views.py

# 3. Rebuild and restart
docker-compose build backend
docker-compose up -d

# System now uses original Mem0-based context management
```

### Verify Rollback
```bash
# Health check should no longer show unified context
curl http://localhost:8000/health/

# Should NOT include "using_unified_context": true
```

## Known Differences from Original

### Enhanced Features
1. **Full Conversation History**: Every message preserved across session
2. **Multi-Source Attribution**: Web search, Playwright, JS scraping tracked separately
3. **Enhanced Statistics**: More detailed context stats in responses
4. **Better Debugging**: Export full context as JSON
5. **Temporal Metadata**: Timestamps on all messages and context items

### Response Format Changes
- Added `context_stats` to all chat responses (backward compatible)
- `get_memory_stats` returns richer data structure
- Health endpoint includes `using_unified_context` flag

### Removed Features
- No longer uses Mem0ContextManager (replaced by UnifiedContextManager)
- No longer has global `message_list` (session-based instead)

## Troubleshooting

### Issue: Endpoints return 500 errors
**Solution**: Check logs for import errors, verify all new files present

```bash
docker-compose logs backend | grep -i error
```

### Issue: Context not persisting between requests
**Solution**: Verify session cookies are being sent/received

```bash
# Check if session_id is being used
curl -v "http://localhost:8000/get_chat_response/?..." 2>&1 | grep -i cookie
```

### Issue: Performance degradation
**Solution**: Check token counts, may need to implement compression

```bash
# Monitor context stats
curl "http://localhost:8000/api/get_memory_stats/" | jq '.stats.token_count'
```

### Issue: "Module not found" errors
**Solution**: Rebuild Docker images to ensure new files included

```bash
docker-compose build --no-cache backend
docker-compose up -d
```

## Success Criteria

✅ Backend starts without errors
✅ Health endpoint returns 200 with `using_unified_context: true`
✅ All 15 endpoints respond correctly
✅ Normal mode chat works with Playwright
✅ Advanced mode search works with web_search
✅ Context persists across multiple messages in same session
✅ Different sessions are isolated (no cross-contamination)
✅ Web content addition tracked correctly
✅ Context clearing works with preservation option
✅ Stats endpoint returns comprehensive data
✅ Streaming endpoints work correctly
✅ Frontend shows correct responses
✅ Performance comparable to previous version
✅ No memory leaks during extended use

## Post-Deployment Tasks

1. **Monitor for 24 hours**
   - Check logs for errors
   - Verify no memory leaks
   - Monitor response times
   - Check user feedback

2. **Gather Metrics**
   - Average token counts per session
   - Context compression needs
   - Most common context sources

3. **Iterate**
   - Based on metrics, consider implementing compression
   - Add persistent storage if needed
   - Optimize token management

## Contacts

- **Developer**: Linus (following good taste principles)
- **Documentation**: See UNIFIED_CONTEXT_DOCUMENTATION.md
- **Endpoint Reference**: See ENDPOINT_VERIFICATION.md
- **Tests**: Run `python3 test_unified_context.py`

## Final Notes

The refactored context management system is **production-ready** and **fully backward compatible**. All existing endpoints maintain their contracts while gaining the benefits of full conversation history, multi-source context tracking, and enhanced metadata.

No frontend changes are required. The system is designed to be a drop-in replacement that "just works" while providing significant improvements under the hood.

**Good luck with your deployment! 🚀**