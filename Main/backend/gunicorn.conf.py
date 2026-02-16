import os
import multiprocessing

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

workers = int(os.getenv('GUNICORN_WORKERS', '1'))
worker_class = 'gthread'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

timeout = int(os.getenv('GUNICORN_TIMEOUT', '1200'))
graceful_timeout = 30
keepalive = 5

accesslog = '-'
errorlog = '-'
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

proc_name = 'fingpt-backend'

limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

