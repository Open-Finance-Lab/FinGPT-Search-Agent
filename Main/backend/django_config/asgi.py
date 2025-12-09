"""ASGI config for chat_server project."""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_config.settings")
application = get_asgi_application()
