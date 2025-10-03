# Project Structure

This document provides high-level structure and basic details about the project structure.

---

## 1. Top-Level Layout

```markdown
Main/
├── backend/
│   ├── chat_server/          # Django project – global settings & routing
│   ├── chat_server_app/      # Django app – business logic & APIs
│   └── datascraper/          # Custom Python utilities (RAG, scraping, etc.)
├── frontend/                 # Browser extension (Webpack-bundled JS)
│   ├── dist/                 # Production build artefacts (auto-generated)
│   ├── node_modules/         # Local dependencies (auto-generated)
│   └── src/                  # Authoritative front-end source code
└── Requirements/             # Pinned Python dependencies (pip)
```



---

## 2. Backend (`backend/`)

### 2.1 `chat_server/` – **Django project scaffolding**

| File          | Purpose                                                   |
|---------------|-----------------------------------------------------------|
| `asgi.py`     | ASGI entry-point (web-sockets & async workers)            |
| `settings.py` | Central Django configuration (INSTALLED_APPS, CORS, etc.) |
| `urls.py`     | Global URL dispatcher                                     |
| `wsgi.py`     | WSGI entry-point (traditional sync servers)               |

### 2.2 `chat_server_app/` – **Primary Django app**

| Item                                 | Purpose                                                                                                                                                         |
|--------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `admin.py` / `apps.py` / `models.py` | Conventional Django plumbing                                                                                                                                    |
| `views.py`                           | **Bridge between front-end & back-end**. End-points:<br/>• Chat completion<br/>• RAG trigger<br/>• Question logging<br/>• Preferred-source management           |
| `migrations/`                        | Database schema revisions                                                                                                                                       |
| `manage.py`                          | Django CLI helper                                                                                                                                               |
| `package.json`                       | `npm` scripts for auxiliary JS tooling (e.g., esbuild for HTMX)                                                                                                 |
| **Runtime artefacts**                | *Generated, **git-ignored***<br/>• `questionLog.csv` – per-prompt telemetry<br/>• `preferred_urls.txt` – user-curated sources<br/>• `*.pkl` – embedding indices |

### 2.3 `datascraper/` – **Utility & RAG helpers**

| Script                 | Responsibility                                                       |
|------------------------|----------------------------------------------------------------------|
| `cdm_rag.py`           | Orchestrates retrieval-augmented generation pipeline                 |
| `create_embeddings.py` | Batch-embeds local docs via OpenAI *text-embedding-3-large*          |
| `datascraper.py`       | General helpers: web scraping, source parsing, model API calls, etc. |
| Log / DB files         | `cdm_rag.log`, `db.sqlite3` – local persistence, **git-ignored**     |

---

## 3. Front-End (`frontend/`)

Front-end's file structure:
```markdown
frontend/
├── dist/           # Compiled bundle – served by extension (DO NOT EDIT)
└── src/
├── main.js     # Extension bootstrapper
├── manifest.json  # Required Web-Extension manifest (permissions, icons…)
├── modules/    # Feature-specific JS (each with optional *.css)
├── styles/     # Shared CSS (BEM / Tailwind utilities)
└── textbox.css # LEGACY – kept only for historical reference
```
Webpack information:

| Tooling             | Notes                                          |
|---------------------|------------------------------------------------|
| **Webpack**         | Bundles ES modules, targets modern browsers    |
| **Babel**           | Transpiles experimental JS → ES2018            |
| `webpack.config.js` | Two entry points: background & content scripts |


---
