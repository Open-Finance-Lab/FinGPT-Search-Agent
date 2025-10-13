# Repository Guidelines

## Project Structure & Module Organization
- `Main/backend`: Django API for retrieval and RAG; configs in `django_config/`, agents in `mcp_client/`, scrapers in `datascraper/`.
- `Main/frontend`: Chrome extension (ES modules in `src/modules/`, assets in `src/assets/`, compiled bundle in `dist/`).
- `scripts/`: Installer (`install_all.py`) and dev bootstrap (`dev_setup.py`) used by Make and Poetry.
- `Docs/`: Sphinx sources powering ReadTheDocs. Update alongside workflow or API changes.
- `Requirements/`: Platform exports generated from Poetry; keep `FinGPTenv/` local-only.

## Build, Test, and Development Commands
- `python scripts/install_all.py` or `make install` - provision Poetry env plus npm deps.
- `python scripts/dev_setup.py` or `make dev` - launch backend server and extension watcher.
- `cd Main/backend && python manage.py runserver` - backend only using `.env` keys.
- `cd Main/frontend && npm run build:full` - rebuild extension and run sanity checks.
- `make clean` - purge caches, `dist/`, and temporary Django artifacts.

## Coding Style & Naming Conventions
- Python: 4 spaces, module docstrings when exporting helpers, imports grouped stdlib/third-party/local. Keep app code under `api/` and `datascraper/`.
- Prefer type hints on new functions and guard network calls with explicit timeouts and logging.
- JavaScript: ES modules with 4-space indent, camelCase for functions, PascalCase for factory exports (`createPopup`). Keep styles in `modules/styles/` and reuse helpers from `modules/helpers.js`.
- Run `poetry run ruff check .` in `Main/backend`; add `npm run lint` once configured and keep webpack config formatted.

## Testing Guidelines
- Backend: `cd Main/backend && python manage.py test`; place suites beside the feature (`api/tests.py`, `datascraper/test/`). Use fixtures to isolate network-dependent scrapers.
- Supplement with `poetry run pytest` for utility-heavy modules if you add pytest plugins.
- Frontend: add Jest or Playwright harnesses before enabling `npm test`; until then, document manual DOM checks when opening PRs.

## Commit & Pull Request Guidelines
- Write imperative commit titles; Conventional Commit prefixes (`feat:`, `fix:`, `docs:`) reflect recent history and aid changelog tooling.
- PRs should summarise scope, list verification commands, link issues, and attach extension screenshots or backend logs when behavior shifts.
- Update README snippets, Sphinx docs, and installer scripts whenever commands or config paths change.

## Security & Configuration Notes
- Store API keys only in `Main/backend/.env`; exclude `db.sqlite3`, `.env`, and logs from commits.
- Rotate demo credentials regularly and scrub secrets before sharing benchmark artifacts.
- Validate new entries in `preferred_urls.txt` for terms-of-service compliance and record provenance in the PR body.
