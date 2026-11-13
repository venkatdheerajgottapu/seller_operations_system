import os
import multiprocessing

# Network Binding
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '5000')}"

# Worker Concurrency
# Default to 4 workers or calculated from CPU cores
workers = int(os.getenv('WORKERS', '4'))
worker_class = 'sync'
threads = int(os.getenv('THREADS', '2'))

# Worker Lifecycle & Memory Protection
max_requests = 1000
max_requests_jitter = 50
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" (%(D)s µs)'

# Process Identification
proc_name = 'seller_ops_platform'

