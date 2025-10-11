# Project Structure

This document provides comprehensive details about the FinGPT Search Agents project structure.

---

## 1. Top-Level Layout

```markdown
fingpt_rcos/
├── Main/
│   ├── backend/               # Django backend with RAG and R2C context management
│   └── frontend/              # Browser extension (Webpack-bundled JS)
├── mcp-server/                # Model Context Protocol server
├── scripts/                   # Project-wide installation and setup scripts
├── Requirements/              # Pinned Python dependencies
├── Docs/                      # Sphinx documentation
├── Makefile                   # Build automation for development
└── pyproject.toml             # Project metadata and dependencies
```

---

## 2. Backend (`Main/backend/`)

### 2.1 Directory Structure

```markdown
backend/
├── django_config/              # Django project scaffolding
│   ├── asgi.py                 # ASGI entry-point (WebSockets & async workers)
│   ├── settings.py             # Development Django configuration (INSTALLED_APPS, CORS, etc.)
│   ├── settings_prod.py        # Production Django configuration
│   ├── urls.py                 # Global URL dispatcher
│   └── wsgi.py                 # WSGI entry-point (traditional sync servers)
├── api/                        # Primary Django app (business logic & APIs)
│   ├── admin.py                # Django admin configuration
│   ├── apps.py                 # Django app configuration
│   ├── models.py               # Database models
│   ├── views.py                # API endpoints (chat, RAG, MCP, context management)
│   ├── tests.py                # Unit tests
│   └── questionLog.csv         # Runtime artifact: per-prompt telemetry (git-ignored)
├── datascraper/                # RAG & Context Management utilities
│   ├── cdm_rag.py              # Orchestrates retrieval-augmented generation pipeline
│   ├── create_embeddings.py   # Batch-embeds local docs via OpenAI embeddings
│   ├── datascraper.py         # General helpers: web scraping, source parsing, API calls
│   ├── models_config.py       # Centralized model configuration (OpenAI, DeepSeek, Anthropic)
│   ├── preferred_links_manager.py  # Manages user-curated preferred sources
│   ├── r2c_context_manager.py # R2C Context Manager - hierarchical compression system
│   ├── test/                   # Test files and fixtures
│   ├── embeddings.pkl          # Cached embeddings (git-ignored)
│   ├── faiss_index.idx         # FAISS vector index (git-ignored)
│   └── .gitignore              # Datascraper-specific ignore rules
├── mcp_client/                 # Model Context Protocol integration
│   └── agent.py                # MCP client functionality
├── data/                       # Application data storage
│   └── preferred_links.json   # JSON storage for preferred data sources
├── scripts/                    # Backend utility scripts
│   └── export_requirements.py # Exports dependencies from pyproject.toml to requirements.txt
├── manage.py                   # Django CLI helper
├── pyproject.toml              # Python dependencies and project metadata
├── manage_deps.py              # Dependency management utilities
├── test_models.py              # Model configuration testing script
├── gunicorn.conf.py            # Gunicorn WSGI server configuration for production
├── Procfile                    # Heroku deployment configuration
├── runtime.txt                 # Python version specification for deployment
├── package.json                # npm scripts for auxiliary tooling
├── .env.example                # Environment variable template
├── DEPLOYMENT_GUIDE.md         # A tmp file keeping track of deployment-related stuff
└── MCP_INSTALLATION.md         # MCP server setup guide
```

### 2.2 Key Components

**`api/views.py`** – Bridge between frontend & backend with endpoints:
- `/get_chat_response/` - Standard chat (supports R2C context management)
- `/get_mcp_response/` - MCP-enabled chat
- `/get_adv_response/` - Advanced chat with web search capabilities
- `/clear_messages/` - Clear session conversation context
- `/api/get_r2c_stats/` - Get R2C compression statistics

**`datascraper/r2c_context_manager.py`** – R2C Context Manager:
- Hierarchical compression algorithm (chunk-level → sentence-level)
- Financial-aware importance scoring
- Automatic compression at 4096 tokens
- Session-based context isolation

**`datascraper/cdm_rag.py`** – RAG Pipeline Orchestration:
- FAISS vector similarity search
- OpenAI text-embedding-3-large integration
- Seamless integration with R2C compressed context

**`datascraper/models_config.py`** – Centralized Model Configuration:
- OpenAI API integration
- DeepSeek API integration
- Anthropic Claude integration

---

## 3. Frontend (`Main/frontend/`)

### 3.1 Directory Structure

```markdown
frontend/
├── dist/              # Compiled bundle – served by extension (DO NOT EDIT)
├── node_modules/      # Local dependencies (auto-generated)
└── src/               # Authoritative frontend source code
    ├── main.js        # Extension bootstrapper
    ├── manifest.json  # Web Extension manifest (permissions, icons)
    ├── assets/        # Static assets (icons, images)
    └── modules/       # Feature-specific modules
        ├── api.js              # Backend API integration
        ├── config.js           # Configuration management
        ├── handlers.js         # Event handlers
        ├── helpers.js          # Utility functions
        ├── sourcesCache.js     # Source data caching
        ├── ui.js               # UI state management
        ├── components/         # UI Components
        │   ├── chat.js         # Chat interface
        │   ├── header.js       # Header component
        │   ├── link_manager.js # Preferred links management
        │   ├── popup.js        # Extension popup
        │   └── settings_window.js # Settings interface
        └── styles/             # CSS modules
            ├── chat.css        # Chat styling
            ├── header.css      # Header styling
            ├── popup.css       # Popup styling
            ├── theme.css       # Theme variables and base styles
            └── windows.css     # Window/modal styling
```

### 3.2 Build System

| File                | Purpose                                          |
|---------------------|--------------------------------------------------|
| `webpack.config.js` | Webpack configuration - bundles ES modules       |
| `babel.config.json` | Babel transpilation configuration                |
| `build-css.js`      | CSS build script                                 |
| `check-dist.js`     | Build artifact verification                      |
| `package.json`      | npm scripts and dependencies                     |

**Build Commands:**
```bash
npm run build:css      # Build CSS only
npm run build          # Build with Webpack
npm run check          # Verify build artifacts
npm run build:full     # Complete build pipeline
```

---

## 4. MCP Server (`mcp-server/`)

Model Context Protocol server implementation located at project root.

| File              | Purpose                              |
|-------------------|--------------------------------------|
| `server.py`       | MCP server implementation            |
| `pyproject.toml`  | MCP server dependencies              |
| `.python-version` | Python version specification         |
| `.venv/`          | Virtual environment (auto-generated) |

**Run MCP Server:**
```bash
cd mcp-server
python server.py
```

---

## 5. Additional Components

### 5.1 Project-Wide Scripts (`scripts/`)

| Script           | Purpose                                            |
|------------------|----------------------------------------------------|
| `install_all.py` | Automated installation for all project components  |
| `dev_setup.py`   | Development environment setup                      |

### 5.2 Python Dependencies (`Requirements/`)

| File                   | Purpose                                    |
|------------------------|--------------------------------------------|
| `requirements_mac.txt` | Pinned dependencies for macOS              |
| `requirements_win.txt` | Pinned dependencies for Windows            |

### 5.3 Documentation (`Docs/`)

Sphinx - ReadtheDocs:
- `source/` – reStructuredText documentation source files
- `build/` – Generated HTML documentation (auto-generated)
- `Makefile` – Documentation build commands
- `make.bat` – Windows documentation build script

**Build Documentation:**
```bash
cd Docs
make html
# Output: build/html/index.html
```

---

## 6. Tech stack

### Backend Stack
- **Django 4.2.18** – Web framework
- **OpenAI API** – LLM integration
- **DeepSeek API** – Alternative LLM provider
- **Anthropic API** – Claude integration
- **FAISS** – Vector similarity search
- **BeautifulSoup4** – Web scraping
- **tiktoken** – Token counting for R2C context management
- **numpy** – Numerical operations for importance scoring

### Frontend Stack
- **Webpack 5** – Module bundler
- **Babel** – JavaScript transpiler
- **KaTeX** – Mathematical notation rendering
- **Marked** – Markdown parsing

### Context Management
- **R2C (Read-to-Compress)** – Hierarchical context compression
  - Session-based isolation
  - Automatic compression at 4096 tokens
  - Financial-aware importance scoring
  - Two-level compression algorithm

---

## 7. Development Workflow

### Backend Development
```bash
cd Main/backend
python manage.py runserver          # Start development server
```

### Frontend Development
```bash
cd Main/frontend
npm install                         # Install dependencies
npm run build:full                  # Complete build
```

---

## 8. API Endpoints

### Core Endpoints (in `api/views.py`)

| Endpoint               | Method | Purpose                                           |
|------------------------|--------|---------------------------------------------------|
| `/get_chat_response/`  | POST   | Standard chat (supports R2C context management)   |
| `/get_mcp_response/`   | POST   | MCP-enabled chat                                  |
| `/get_adv_response/`   | POST   | Advanced chat with web search capabilities        |
| `/clear_messages/`     | POST   | Clear session conversation context                |
| `/api/get_r2c_stats/`  | GET    | Get R2C compression statistics                    |

**Important Parameters:**
- `use_r2c` – Enable R2C context management (default: "true")
- `models` – Comma-separated model names
- `question` – User query

---

## 9. Environment Configuration

### Required API Keys (in `.env`)
- `OPENAI_API_KEY` – OpenAI API key
- `DEEPSEEK_API_KEY` – DeepSeek API key
- `ANTHROPIC_API_KEY` – Anthropic API key

See `Main/backend/.env.example` for full configuration template.

---

*For more detailed documentation, see `Docs/build/html/index.html` after building the Sphinx documentation.*
