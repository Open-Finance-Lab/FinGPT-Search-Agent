# Repository Guidelines

## Project Structure & Module Organization
The monorepo centers on `Main/`. `Main/backend` hosts the Django service, with `api/` for HTTP views, `datascraper/` for retrieval and embeddings utilities, and `django_config/` for settings. Chrome-extension code lives in `Main/frontend` (`src/` JSX/CSS, `dist/` built assets). Shared automation sits in `scripts/`, while `Docs/` contains the Sphinx documentation source. Use `FinGPTenv/` as the optional virtual environment created by the installers.

## Build, Test, and Development Commands
- `python scripts/install_all.py` (or `python3` on Unix) installs backend and frontend dependencies end-to-end.
- `make install` mirrors the unified installer on Unix; `make.ps1 install` does the same on Windows PowerShell.
- `make dev` (or `python scripts/dev_setup.py`) launches the Django API plus frontend watcher with the expected environment variables.
- `npm run build:full` inside `Main/frontend` rebuilds the extension bundle and verifies the `dist/` output.
- `make clean` removes caches, the SQLite dev DB, and rebuild artifacts when you need a fresh start.

## Coding Style & Naming Conventions
Target Python 3.10+, four-space indentation, and module-level constants in `UPPER_SNAKE_CASE`. Follow Django conventions: `snake_case` for functions, `PascalCase` classes, and docstrings for public utilities (see `api/views.py`). Run `cd Main/backend && poetry run ruff check .` before submitting. In the extension, stick to ES modules, `camelCase` helpers, and keep user-facing strings centralized in `src/`. Bundle-time assets should remain under 80 characters per line where practical.

## Testing Guidelines
Backend unit tests run with `cd Main/backend && poetry run python manage.py test`; `make test` wraps backend and frontend checks. Use `Main/backend/test_models.py` to validate model registry updates and API key availability before opening a PR (`poetry run python test_models.py`). Place Django tests alongside the feature under `api/tests.py` using descriptive method names like `test_agent_handles_missing_rag_context`. Frontend automation is not yet wired - document manual verification steps (`npm run build:full`, browser smoke tests) in your PR until Jest or equivalent is introduced.

## Commit & Pull Request Guidelines
Commits should be concise and imperative; the history favors Conventional Commit prefixes (e.g., `feat:`, `fix:`, `docs:`). Keep the subject <=72 characters and describe rationale in the body when needed. For pull requests, include: problem statement, summary of backend/frontend changes, setup notes (e.g., required `.env` keys), and screenshots/GIFs if the extension UI changes. Link related issues and list the commands you ran (`make test`, `npm run build:full`, etc.) so reviewers can reproduce your checks.

## Security & Configuration Tips
Never commit `.env` or API keys - `Main/backend/.env.example` should be used for sharing defaults. When testing MCP integrations, rotate keys after public demos. If you create new scripts, ensure they respect the virtual environment and provide cross-platform alternatives (Python + PowerShell). Always confirm new dependencies are added via Poetry or `npm` to keep the lockfiles authoritative.