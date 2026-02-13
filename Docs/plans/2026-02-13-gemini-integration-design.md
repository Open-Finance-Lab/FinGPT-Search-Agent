# Gemini 3 Flash Integration via OpenAI-Compatible Endpoint

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Switch the default FinGPT model to Gemini 3 Flash Preview (low thinking) and promote GPT 5.1 to FinGPT-Light, using Google's OpenAI-compatible endpoint.

**Architecture:** Google provides an OpenAI-compatible API at `https://generativelanguage.googleapis.com/v1beta/openai/`. We reuse the same `OpenAI()` client pattern already used for DeepSeek — no new dependencies. For the Agent SDK path, we use `OpenAIChatCompletionsModel` with an `AsyncOpenAI` client pointing to Google's endpoint.

**Tech Stack:** `openai` (existing), `openai-agents` (existing), Google Gemini OpenAI-compat API

---

### Task 1: Update models_config.py — Add Google provider and update model entries

**Files:**
- Modify: `Main/backend/datascraper/models_config.py`

**Step 1: Update the FinGPT model entry to use Gemini**

Change the `"FinGPT"` entry in `MODELS_CONFIG`:

```python
"FinGPT": {
    "provider": "google",
    "model_name": "gemini-3-flash-preview",
    "supports_mcp": True,
    "supports_advanced": True,
    "max_tokens": 1048576,
    "reasoning_effort": "low",
    "description": "State-of-the-art financial model"
},
```

**Step 2: Update the FinGPT-Light model entry to GPT 5.1**

Change `"FinGPT-Light"` to use the promoted model:

```python
"FinGPT-Light": {
    "provider": "openai",
    "model_name": "gpt-5.1-chat-latest",
    "supports_mcp": True,
    "supports_advanced": True,
    "max_tokens": 128000,
    "description": "Fast and efficient light-weight model"
},
```

**Step 3: Add the Google provider config to PROVIDER_CONFIGS**

Add after the `"anthropic"` entry:

```python
"google": {
    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "env_key": "GOOGLE_API_KEY",
    "client_class": "OpenAI"
},
```

**Step 4: Commit**

```bash
git add Main/backend/datascraper/models_config.py
git commit -m "feat: add Google Gemini provider, switch FinGPT to gemini-3-flash-preview"
```

---

### Task 2: Update datascraper.py — Add Google client and pass reasoning_effort

**Files:**
- Modify: `Main/backend/datascraper/datascraper.py`

**Step 1: Add GOOGLE_API_KEY env var and Google client initialization**

After the existing `BUFFET_AGENT_ENDPOINT` line (~line 38), add:

```python
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
```

After the existing DeepSeek client block (~line 56), add:

```python
if GOOGLE_API_KEY:
    clients["google"] = OpenAI(
        api_key=GOOGLE_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
```

**Step 2: Pass reasoning_effort in `_create_response_sync`**

In `_create_response_sync` (~line 437), in the `else` branch (non-anthropic), before the `client.chat.completions.create` call, add reasoning_effort support:

```python
if "reasoning_effort" in model_config:
    kwargs["reasoning_effort"] = model_config["reasoning_effort"]
```

This goes right after the existing deepseek temperature block.

**Step 3: Pass reasoning_effort in `_create_response_stream`**

In `_create_response_stream` (~line 466), same change in the `else` branch:

```python
if "reasoning_effort" in model_config:
    kwargs["reasoning_effort"] = model_config["reasoning_effort"]
```

**Step 4: Commit**

```bash
git add Main/backend/datascraper/datascraper.py
git commit -m "feat: add Google Gemini client and reasoning_effort passthrough"
```

---

### Task 3: Update agent.py — Support Google provider in Agent creation

**Files:**
- Modify: `Main/backend/mcp_client/agent.py`

**Step 1: Add imports for OpenAIChatCompletionsModel and AsyncOpenAI**

At the top of the file, after the existing `from agents.model_settings import ModelSettings`:

```python
from agents import AsyncOpenAI, OpenAIChatCompletionsModel
```

**Step 2: Add Google model resolution in create_fin_agent**

After the existing model resolution block (~line 59-65), before the tools section, add logic to create an `OpenAIChatCompletionsModel` when the provider is `"google"`:

```python
model_obj = actual_model  # default: pass string (uses OpenAI)

if model_config and model_config.get("provider") == "google":
    google_api_key = os.getenv("GOOGLE_API_KEY", "")
    if google_api_key:
        google_client = AsyncOpenAI(
            api_key=google_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        model_obj = OpenAIChatCompletionsModel(
            model=actual_model,
            openai_client=google_client
        )
        logging.info(f"[AGENT] Using Google OpenAI-compat client for {actual_model}")
    else:
        logging.error("[AGENT] GOOGLE_API_KEY not set but Google model requested")
        raise ValueError("GOOGLE_API_KEY environment variable is required for Google models")
```

**Step 3: Use model_obj instead of actual_model in Agent constructor**

Change the Agent instantiation (~line 166) to use `model_obj`:

```python
agent = Agent(
    name="FinGPT Search Agent",
    instructions=agent_instructions,
    model=model_obj,
    tools=tools if tools else [],
    model_settings=ModelSettings(
        tool_choice="auto" if tools else None
    )
)
```

**Step 4: Update USER_ONLY_MODELS set**

Update the `USER_ONLY_MODELS` set (~line 28) to reflect the new model lineup. Remove `"gpt-5.1-chat-latest"` since it's now FinGPT-Light (not the default), and it still needs to be there. Add `"gemini-3-flash-preview"` if Gemini doesn't support system role via the compat API — but actually, Gemini via OpenAI-compat API DOES support system messages, so `gemini-3-flash-preview` should NOT be in `USER_ONLY_MODELS`.

No change needed here — the existing set already covers the right models.

**Step 5: Add reasoning_effort to ModelSettings**

In the Agent constructor, pass reasoning_effort if present in model_config:

```python
model_settings_kwargs = {"tool_choice": "auto" if tools else None}
if model_config and "reasoning_effort" in model_config:
    model_settings_kwargs["reasoning_effort"] = model_config["reasoning_effort"]

agent = Agent(
    ...
    model_settings=ModelSettings(**model_settings_kwargs)
)
```

**Step 6: Commit**

```bash
git add Main/backend/mcp_client/agent.py
git commit -m "feat: support Google provider in Agent via OpenAIChatCompletionsModel"
```

---

### Task 4: Verify end-to-end

**Step 1: Check .env has GOOGLE_API_KEY**

Ensure `Main/backend/.env` contains:
```
GOOGLE_API_KEY=<your-key>
```

**Step 2: Manual smoke test**

Start the backend and send a request to the chat endpoint with `models=FinGPT`. Verify:
- The logs show `Model resolution: FinGPT -> gemini-3-flash-preview`
- The logs show `[AGENT] Using Google OpenAI-compat client for gemini-3-flash-preview`
- A valid response is returned

**Step 3: Test FinGPT-Light still works**

Send a request with `models=FinGPT-Light`. Verify:
- The logs show `Model resolution: FinGPT-Light -> gpt-5.1-chat-latest`
- A valid response is returned via OpenAI

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete Gemini 3 Flash integration as default FinGPT model"
```
