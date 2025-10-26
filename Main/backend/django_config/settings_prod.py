"""
Production settings for FinGPT Backend

This file contains production-ready settings that override the base settings.py.
To use this file, set the environment variable:
    export DJANGO_SETTINGS_MODULE=django_config.settings_prod

Or when running with gunicorn:
    gunicorn django_config.wsgi:application --env DJANGO_SETTINGS_MODULE=django_config.settings_prod
"""

from django.core.exceptions import ImproperlyConfigured

from .settings import *

# Production-specific overrides
DEBUG = False

# Security settings - default to secure values but allow env overrides
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').strip().lower() in ('true', '1', 't')
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').strip().lower() in ('true', '1', 't')
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True').strip().lower() in ('true', '1', 't')
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').strip().lower() in ('true', '1', 't')
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'True').strip().lower() in ('true', '1', 't')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# CORS - must be explicitly configured in production
# Get from environment variable or fail
cors_origins_env = os.getenv('CORS_ALLOWED_ORIGINS')
if not cors_origins_env:
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS environment variable is required in production. "
        "Set it to a comma-separated list of allowed origins, e.g., "
        "'https://yourdomain.com,chrome-extension://your-extension-id'"
    )

CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
CORS_ALLOW_ALL_ORIGINS = False
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# Allowed hosts must be set
allowed_hosts_env = os.getenv('DJANGO_ALLOWED_HOSTS')
if not allowed_hosts_env or allowed_hosts_env == '*':
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be explicitly set in production. "
        "Set it to a comma-separated list of allowed hostnames, e.g., "
        "'yourdomain.com,api.yourdomain.com'"
    )
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]

# Secret key must be set and not be the default
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY or 'django-insecure' in SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set to a secure random value in production. "
        "Generate one with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
    )

# Database configuration
# Not using a database for this deployment
# Sessions are stored in signed cookies (configured in base settings.py)
DATABASES = {}

# Static files configuration
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Logging configuration for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# Ensure all API keys are set
required_keys = ['OPENAI_API_KEY', 'DEEPSEEK_API_KEY', 'ANTHROPIC_API_KEY']
missing_keys = [key for key in required_keys if not os.getenv(key)]
if len(missing_keys) == len(required_keys):
    raise ImproperlyConfigured(
        f"At least one API key must be set. Missing: {', '.join(missing_keys)}"
    )
