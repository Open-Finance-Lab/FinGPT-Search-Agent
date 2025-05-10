"""
ASGI config for chat_server project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application
from django_mcp import mount_mcp_server

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chat_server.settings")
django.setup()

django_app = get_asgi_application()
# mount MCP server at “/mcp” and fall back to Django for all other paths
application = mount_mcp_server(
    django_app,
    mcp_base_path="/mcp",    # <-- base path under which MCP lives
)
print("🟢 ASGI.PY loaded, mounting MCP at /mcp")
