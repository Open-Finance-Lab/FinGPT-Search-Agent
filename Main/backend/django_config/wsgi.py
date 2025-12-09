"""WSGI config for chat_server."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_config.settings')

application = get_wsgi_application()
