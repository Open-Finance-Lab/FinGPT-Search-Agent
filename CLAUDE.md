# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FinGPT Search Agents is a financial information retrieval and analysis system with advanced context management:
- Django backend with RAG capabilities and R2C context compression
- Browser extension frontend built with Webpack
- MCP (Model Context Protocol) server integration
- Session-based conversation management with automatic compression

## Architecture

### Backend (Main/backend/)
- **Django Project**: `django_config/` contains global settings, URL routing, session management
- **API Layer**: `api/views.py` handles all endpoints with unified R2C context management
- **R2C Context Manager**: `datascraper/r2c_context_manager.py` implements hierarchical compression
- **Data Pipeline**: `datascraper/` provides RAG orchestration, embeddings, web scraping
- **MCP Integration**: `mcp_client/` contains Model Context Protocol client functionality

### Frontend (Main/frontend/)
- **Browser Extension**: Webpack-bundled JavaScript with Babel transpilation
- **Build System**: Uses Webpack with CSS processing and KaTeX support
- **API Integration**: Sends `use_r2c=true` by default for context management

### Context Management System (R2C)
- **Session-based**: Each browser session has isolated context (no cross-user data leakage)
- **Automatic Compression**: Triggers at 4096 tokens using financial-aware importance scoring
- **Hierarchical Algorithm**: Two-level compression (chunk-level then sentence-level)
- **Global Integration**: All response modes (normal, RAG, advanced, MCP) use R2C by default

## Development Commands

### Backend Development
```bash
# From Main/backend/
python manage.py runserver          # Start Django development server
python manage.py migrate           # Apply database migrations
python manage.py makemigrations    # Create new migrations
python test_models.py              # Test model configuration system
```

### Frontend Development
```bash
# From Main/frontend/
npm run build:css                  # Build CSS only
npm run build                      # Build with Webpack
npm run check                      # Verify build artifacts
npm run build:full                 # Complete build pipeline
```

### MCP Server
```bash
# From mcp-server/
python3 server_official.py        # Run official MCP server
# or
uv run server_official.py         # Run with uv
```

### Documentation
```bash
# From Docs/
sphinx-build -M html ./source ./build  # Build HTML documentation
```

## Key Components

### R2C Context Management
- **Helper Functions** in `api/views.py`:
  - `_prepare_context_messages()`: Unified context preparation
  - `_add_response_to_context()`: Response storage
  - `_prepare_response_with_stats()`: JSON response with R2C stats
- **Compression Algorithm**: Financial keyword weighting, recency scoring, Q&A pattern recognition
- **Token Management**: Uses tiktoken for accurate token counting

### Model Configuration System
- `datascraper/models_config.py` centralizes provider settings
- Supports OpenAI, DeepSeek, and Anthropic models
- All models integrate with R2C context management

### RAG Pipeline
- `datascraper/cdm_rag.py` orchestrates retrieval-augmented generation
- Works seamlessly with R2C compressed context
- FAISS indexing for efficient vector search

## Environment Setup

### Required API Keys
- `API_KEY7`: OpenAI API key
- `DEEPSEEK_API_KEY`: DeepSeek API key  
- `ANTHROPIC_API_KEY`: Anthropic API key

### Dependencies
- Backend: Django 4.2.18, OpenAI, FAISS, BeautifulSoup4, tiktoken, numpy
- Frontend: Webpack 5, Babel, KaTeX, Marked
- R2C: tiktoken (token counting), numpy (importance calculations)

## API Endpoints & Parameters

### Core Endpoints
- `/get_chat_response/` - Standard chat (supports `use_r2c=true`)
- `/get_mcp_response/` - MCP-enabled chat
- `/get_adv_response/` - Advanced with web search
- `/clear_messages/` - Clears session context
- `/api/get_r2c_stats/` - Get compression statistics

### Important Parameters
- `use_r2c`: Enable R2C context management (default: "true")
- `models`: Comma-separated model names
- `question`: User query
- Session managed via Django session framework

## Critical Information Flow

1. **Request**: Browser → Django → `_prepare_context_messages()` → R2C/legacy context
2. **Compression**: When tokens > 4096 → Hierarchical compression → Store compressed + recent msgs
3. **API Call**: Context → Model API → Response → `_add_response_to_context()`
4. **Response**: Include R2C stats → Browser

## Security & Best Practices

- **Session Isolation**: R2C uses Django sessions - no cross-user data leakage
- **No Persistent Storage**: Context cleared on session end
- **Token Efficiency**: Automatic compression reduces API costs
- **Error Handling**: Falls back to legacy system if R2C fails

## Development Principles

When planning, writing or editing code, always follow these principles:
1. **Planning First**: Before implementing, verify or devise a clear plan and validate its reasonableness.
2. **Simplicity**: Actively seek simpler, more elegant solutions that avoid over-engineering during both planning and implementation.
3. **Core Principles**:
    - KISS (Keep It Simple, Stupid)
    - YAGNI (You Aren't Gonna Need It)
    - DRY (Don't Repeat Yourself)
    - SOLID principles
4. **Step-by-step Validation**: After implementation, verify if the solution could be simpler while maintaining robustness and adhering to the above principles.

This approach should be applied to all code explanations, comments, and code changes to ensure maintainable, efficient, and clean communication and problem-solving.