"""Shared pytest fixtures / import-path fixes.

`tests/mcp_server/__init__.py` is an unused stub package that shadows the
real `mcp_server` when pytest adds `tests/` to sys.path before the backend
root. Force the backend dir to the front, then eagerly import the real
`mcp_server.xbrl.parser` so it's cached before any test module imports
`axioms.resolver`.
"""
import sys
from pathlib import Path

_BACKEND = str(Path(__file__).resolve().parent.parent)
while _BACKEND in sys.path:
    sys.path.remove(_BACKEND)
sys.path.insert(0, _BACKEND)

import mcp_server.xbrl.parser  # noqa: F401,E402 — populate sys.modules
