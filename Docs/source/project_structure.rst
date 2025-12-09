Project Structure
=================

Top-Level Layout
----------------

.. code-block:: text

   fingpt/
   ├── Main/
   │   ├── backend/        # Django backend (uv-managed)
   │   └── frontend/       # Browser extension
   ├── Docs/               # Sphinx documentation
   ├── docker-compose.yml  # Run backend with Docker
   └── README.md

Backend Highlights
------------------

* ``pyproject.toml`` + ``uv.lock`` manage Python dependencies.
* ``Dockerfile`` builds a multi-stage image that installs packages with ``uv``.
* ``manage.py`` exposes standard Django management commands.
* ``manage_deps.py`` offers a few helper shortcuts for ``uv`` operations.

Frontend Highlights
-------------------

* ``npm run build:full`` creates the extension bundle in ``dist/``.
* Load ``dist/`` as an unpacked extension in Chromium-based browsers.

Docker Workflow
---------------

.. code-block:: bash

   cp Main/backend/.env.example Main/backend/.env
   docker compose up

Manual Backend Workflow
-----------------------

.. code-block:: bash

   cd Main/backend
   uv sync --python 3.12 --frozen
   uv run playwright install chromium
   uv run python manage.py runserver
