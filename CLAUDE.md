# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FinGPT Search Agents is a financial information retrieval and analysis system consisting of:
- A Django backend with RAG capabilities for processing financial documents
- A browser extension frontend built with Webpack
- MCP (Model Context Protocol) server integration
- Data scraping and embedding utilities for financial information

## Architecture

### Backend (Main/backend/)
- **Django Project**: `django_config/` contains global settings, ASGI/WSGI configuration
- **API Layer**: `api/` handles HTTP endpoints, chat completion, RAG triggers, question logging
- **Data Pipeline**: `datascraper/` provides RAG orchestration, embeddings creation, and web scraping utilities
- **MCP Integration**: `mcp_client/` contains Model Context Protocol client and agent functionality

### Frontend (Main/frontend/)
- **Browser Extension**: Webpack-bundled JavaScript with Babel transpilation
- **Build System**: Uses Webpack with CSS processing and KaTeX support for LaTeX rendering
- **Entry Point**: `src/main.js` bootstraps the extension

### MCP Server (mcp-server/)
- **Official MCP SDK**: Uses the official Model Context Protocol Python SDK
- **Stdio Transport**: Provides subprocess-based communication with OpenAI Agents
- **Python 3.10+**: Compatible with modern Python versions

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

## Key Components

### Model Configuration System
- `datascraper/models_config.py` centralizes model provider settings
- Supports OpenAI, DeepSeek, and Anthropic models
- Feature flags for RAG, MCP, and advanced capabilities

### RAG Pipeline
- `datascraper/cdm_rag.py` orchestrates retrieval-augmented generation
- `datascraper/create_embeddings.py` processes documents with OpenAI embeddings
- FAISS indexing for efficient vector search

### Browser Extension
- Modular architecture in `frontend/src/modules/`
- Component-based structure (chat, header, popup, settings)
- KaTeX support for LaTeX rendering in financial contexts

## Environment Setup

### Required API Keys
- `API_KEY7`: OpenAI API key
- `DEEPSEEK_API_KEY`: DeepSeek API key  
- `ANTHROPIC_API_KEY`: Anthropic API key

### Dependencies
- Backend: Django 4.2.18, OpenAI, FAISS, BeautifulSoup4
- Frontend: Webpack 5, Babel, KaTeX, Marked
- MCP Server: Official MCP Python SDK 1.1.0+

## Testing

**Important**: Claude Code runs in WSL and this project environment is not set up there. 

Regarding testing code, if tests are needed, please directly tell me how to test the code and I will run the test commands manually.

- Use `pytest` for Python tests
- Run `python test_models.py` to verify model configuration
- Frontend testing not currently configured

## Build Artifacts
- `Main/frontend/dist/`: Compiled extension bundle (auto-generated)
- `*.pkl`: Embedding indices (git-ignored)
- `questionLog.csv`: Query telemetry (git-ignored)
- `db.sqlite3`: Local database (git-ignored)

## IDE Configuration

When indexing files on IDE start, do not index any test files.
These include everything under src/test/.

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