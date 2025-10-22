# Playwright Browser Automation Integration

## Architecture: Current Website vs External Search

FinGPT has two distinct modes that serve different use cases:

### Normal Mode - Current Website Navigation

**Purpose**: Help user understand the CURRENT website they're visiting.

**Behavior**:
- User is on `finance.yahoo.com` → Agent navigates within `finance.yahoo.com` only
- Always uses Playwright for browser automation
- Domain-restricted: Cannot leave current website
- Agent knows it's helping with "this website"

**Example**:
```
User on: finance.yahoo.com
Question: "What's Apple's P/E ratio?"
→ Agent navigates to finance.yahoo.com/quote/AAPL
→ Extracts P/E ratio from that page
→ Stays within yahoo.com domain
```

### Extensive Mode - External Web Search

**Purpose**: Find information ANYWHERE on the web.

**Behavior**:
- Uses OpenAI Responses API with built-in `web_search` tool
- No domain restrictions
- Searches across multiple sources
- Returns sources for transparency

**Example**:
```
User on: finance.yahoo.com (doesn't matter)
Question: "What's Apple's P/E ratio?"
→ web_search finds info from multiple sources
→ Can use finviz.com, marketwatch.com, etc.
→ No domain restrictions
```

## Tool Usage Philosophy

**Important**: Tools are ALWAYS `tool_choice="auto"` - the model decides when to use them.

- Model won't navigate if answer is already on the page
- Model won't navigate if it knows the answer
- Model will navigate only when it helps answer the question

This is pragmatic: trust the model to make intelligent decisions.

## Implementation Details

### Normal Mode Flow

1. Extract domain from `current_url` → e.g., `finance.yahoo.com`
2. Create agent with Playwright tools + domain restriction
3. Agent prompt emphasizes "You're helping with {domain}"
4. `navigate_to_url` enforces same-origin policy
5. Model navigates within domain to find information

### Extensive Mode Flow

1. No domain extraction needed
2. Uses OpenAI Responses API with `web_search`
3. Model searches broadly across the web
4. Returns sources with response

### Domain Restriction Enforcement

In `playwright_tools.py`, `navigate_to_url` checks domain:

```python
if _RESTRICTED_DOMAIN:
    parsed = urlparse(url)
    target_domain = parsed.netloc

    if target_domain != _RESTRICTED_DOMAIN:
        return "Error: You can only navigate within {_RESTRICTED_DOMAIN}"
```

## Available Playwright Tools

1. **navigate_to_url(url)** - Navigate within current domain
2. **get_page_text()** - Extract visible text
3. **click_element(selector)** - Click using CSS selectors
4. **fill_form_field(selector, value)** - Fill input fields
5. **press_enter()** - Submit forms
6. **get_current_url()** - Get current page URL
7. **wait_for_element(selector, timeout)** - Wait for dynamic content
8. **extract_links()** - Get all links from page

## API Endpoints

### Normal Mode
```
GET /get_chat_response/
  ?question=What's the P/E ratio for AAPL?
  &models=gpt-4o-mini
  &current_url=https://finance.yahoo.com
```

**Automatic behavior:**
- Extracts domain: `finance.yahoo.com`
- Enables Playwright with domain restriction
- Agent navigates within yahoo.com to find answer

### Extensive Mode
```
GET /get_adv_response/
  ?question=What's the P/E ratio for AAPL?
  &models=gpt-4o-mini
  &is_advanced=true
```

**Automatic behavior:**
- Uses web_search (no Playwright for now)
- Searches across entire web
- Returns sources

## Installation

### Requirements

Playwright requires Chromium browser to be installed. The browser is NOT included by default.

### Installation Steps

```bash
cd Main/backend

# Install Python dependencies (if not already done)
uv sync --python 3.12 --frozen

# REQUIRED: Install Chromium browser
uv run playwright install chromium
```

### Troubleshooting Installation

**Error: "Executable doesn't exist at..."**

This means Chromium is not installed. Run:
```bash
uv run playwright install chromium
```

**Error: "Browser closed" or "Target page, context or browser has been closed"**

1. Ensure Chromium is installed: `uv run playwright install chromium`
2. Check system dependencies (Linux only):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install libnss3 libxss1 libasound2

   # For all dependencies:
   playwright install-deps chromium
   ```

**Windows Users:**
- No additional system dependencies needed
- Chromium installs to: `%USERPROFILE%\AppData\Local\ms-playwright`

**macOS Users:**
- No additional system dependencies needed
- Chromium installs to: `~/Library/Caches/ms-playwright`

**Linux Users:**
- May need system dependencies: `playwright install-deps chromium`

### Verifying Installation

```bash
# Check if Chromium is installed
uv run playwright install chromium --dry-run

# Should output: "Browser is already installed"
```

## Testing

```bash
python test_playwright_agent.py
```

## Use Cases

### Normal Mode (Current Website)

**Scenario**: User is browsing finance.yahoo.com homepage

- "What's the current price of TSLA?" → Navigate to /quote/TSLA page
- "Show me earnings calendar" → Navigate to earnings calendar page
- "What are the most actively traded stocks?" → Extract from current page or navigate
- "Compare AAPL and MSFT" → Navigate to both quote pages

### Extensive Mode (External Search)

**Scenario**: User needs information from multiple sources

- "What's the latest Fed interest rate decision?" → Search news across web
- "Compare P/E ratios across sectors" → Aggregate from multiple sources
- "What are analysts saying about inflation?" → Search analyst reports
- "Find the best mortgage rates" → Search lender websites

## Future Enhancements

**Planned**: Add Playwright to Extensive Mode

When implemented, Extensive mode will have BOTH tools:
- `web_search` for broad research
- `playwright` for specific site navigation

Model will intelligently choose:
- web_search → "Find latest inflation data" (multiple sources)
- playwright → "Go to federalreserve.gov and extract rate decision" (specific task)

## Architecture Benefits

1. **Clear Separation**: Current website vs external search
2. **Domain Safety**: Can't accidentally leave current site in Normal mode
3. **Intelligent**: Model decides when to use tools (not forced)
4. **Simple API**: No mode toggles needed
5. **Extensible**: Easy to add Playwright to Extensive mode later

## Additional Endpoints

### Direct Agent Endpoint
```
POST /get_agent_response/
  ?question=What's the P/E ratio for AAPL?
  &models=gpt-4o-mini
  &use_playwright=true
```

**Use case**: Direct access to agent with optional tool control.
- Allows explicit tool toggling via `use_playwright` parameter
- Used for testing and special integrations
- Normal mode endpoint (`/get_chat_response/`) is recommended for standard usage
