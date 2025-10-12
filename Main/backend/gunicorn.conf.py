# Gunicorn configuration file for production deployment
import os
import multiprocessing

# Bind to port from environment variable or default to 8000
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout settings
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'fingpt-backend'

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (not yet having)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'
